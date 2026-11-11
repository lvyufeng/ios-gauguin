/* Host-only health-callback counter for the exact ggr_submit runtime.
 *
 * The real bsd/dev/gauguin_gpu_runtime.c is compiled unchanged next to this
 * fixture. The fixture implements only the typed struct ggr_ops seams and
 * models the register/RAM values the runtime reads and writes. It executes no
 * IB and no command stream; it neither emulates a GPU nor touches a device,
 * and it measures no hardware time or frame rate. Every callback is traced so
 * healthy counts can be attributed to named submit phases and every reached
 * health boundary can be failed in isolation.
 *
 * The fake ring_span below models only GGR_BUSY state, operation_end_ns, and
 * CPU RAM words. It is not the production ggrb_ring_span board callback and
 * does not perform the full ggrb_live checks. The production board adds
 * board-state (GMB_READY) and global ggrb_end deadline predicates per word.
 * These counts therefore describe the runtime's callback sequence against
 * this host seam, not board behavior, GPU progress, or device timing.
 */
#include <errno.h>
#include <inttypes.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "gauguin_gpu_runtime.h"

#define MAX_EVENTS 8192
#define MAX_HEALTH 4096
#define FENCE_SENTINEL 0xdeadbeefu
#define BASE_NS UINT64_C(1700000000000000000)

static unsigned long assertions;

#define CHECK(x) do { \
    ++assertions; \
    if(!(x)) { \
        fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #x); \
        exit(2); \
    } \
} while(0)

enum phase {
    PH_INITIAL = 0,
    PH_RING,
    PH_FENCE,
    PH_POLL,
    PH_COMPLETE,
    PH_N
};
static const char *const phase_name[PH_N] = {
    "initial_idle_validation",
    "ring_writes_readback",
    "fence_off",
    "completion_polling",
    "complete"
};

enum site { SITE_OPEN = 0, SITE_IDLE, SITE_SUBMIT, SITE_N };
static const char *const site_name[SITE_N] = {
    "ggr_open", "ggr_check_idle", "ggr_submit"
};

enum evkind {
    EV_HEALTHY = 0,
    EV_READ_REG,
    EV_WRITE_REG,
    EV_READ_MEM,
    EV_WRITE_RING,
    EV_RING_SPAN,
    EV_BARRIER,
    EV_DELAY,
    EV_QUARANTINE,
    EV_SUCCESS,
    EV_CLOCK_JUMP,
    EV_N
};
static const char *const evkind_name[EV_N] = {
    "healthy", "read_reg", "write_reg", "read_memory", "write_ring",
    "ring_span", "barrier", "delay_us", "quarantine", "success", "clock_jump"
};

struct ev {
    int kind;
    int phase;
    uint32_t a, b, c;
    uint64_t n;
};

struct model {
    struct ggr_context *ctx;
    uint32_t ring[8192];
    uint32_t wptr, shadow, eop;
    uint32_t status_busy;
    uint32_t pending_total, pending_left, polls_done;
    bool completion_started;
    bool ring_span_enabled;
    bool stopped;
    bool failed_here;
    enum site site;
    int phase;
    int next_healthy_phase;  /* apply before logging the next healthy callback */
    int after_healthy_phase; /* apply after logging the next healthy callback */
    uint64_t ns;
    uint32_t healthy_calls;
    uint32_t fail_at;
    uint64_t jump_at;
    uint64_t jump_ns;
    int jump_mode; /* 0 absolute, 1 exact deadline, 2 deadline-1 */
    bool jumped;
    uint32_t quarantines;
    uint32_t writes;
    uint32_t ring_words;
    uint32_t ring_span_calls;
    uint32_t legacy_write_ring_calls;
    uint32_t legacy_read_ring_calls;
    uint32_t phase_healthy[PH_N];
    enum site health_site[MAX_HEALTH];
    int health_phase[MAX_HEALTH];
};

static struct ev events[MAX_EVENTS];
static size_t event_count;

static void log_ev(int kind, int phase, uint32_t a, uint32_t b, uint32_t c, uint64_t n)
{
    CHECK(event_count < MAX_EVENTS);
    events[event_count++] = (struct ev){kind, phase, a, b, c, n};
}

static const char *rc_name(enum ggr_error rc)
{
    switch(rc) {
    case GGR_OK: return "GGR_OK";
    case GGR_ARGUMENT: return "GGR_ARGUMENT";
    case GGR_UNAVAILABLE: return "GGR_UNAVAILABLE";
    case GGR_IO: return "GGR_IO";
    case GGR_TIMEOUT: return "GGR_TIMEOUT";
    }
    return "UNKNOWN";
}

static const char *state_name(uint32_t s)
{
    switch(s) {
    case GGR_COLD: return "GGR_COLD";
    case GGR_READY: return "GGR_READY";
    case GGR_BUSY: return "GGR_BUSY";
    case GGR_FAILED: return "GGR_FAILED";
    }
    return "UNKNOWN";
}

static const char *mem_name(enum ggr_memory m)
{
    switch(m) {
    case GGR_RING: return "GGR_RING";
    case GGR_SHADOW: return "GGR_SHADOW";
    case GGR_COMPLETION: return "GGR_COMPLETION";
    }
    return "UNKNOWN";
}

static bool healthy(void *p)
{
    struct model *m = p;
    ++m->healthy_calls;
    if(m->next_healthy_phase >= 0) {
        m->phase = m->next_healthy_phase;
        m->next_healthy_phase = -1;
    }
    if(m->site == SITE_SUBMIT && m->phase >= 0 && m->phase < PH_N)
        ++m->phase_healthy[m->phase];
    if(m->healthy_calls < MAX_HEALTH) {
        m->health_site[m->healthy_calls] = m->site;
        m->health_phase[m->healthy_calls] = m->phase;
    }
    log_ev(EV_HEALTHY, m->phase, m->healthy_calls, 0, 0, 0);
    if(m->after_healthy_phase >= 0) {
        m->phase = m->after_healthy_phase;
        m->after_healthy_phase = -1;
    }
    if(m->fail_at && m->healthy_calls == m->fail_at) {
        m->failed_here = true;
        return false;
    }
    if(m->jump_at && !m->jumped && (uint64_t)m->healthy_calls == m->jump_at) {
        m->jumped = true;
        if(m->jump_mode == 1)
            m->ns = m->ctx->operation_end_ns;
        else if(m->jump_mode == 2)
            m->ns = m->ctx->operation_end_ns - 1;
        else
            m->ns = m->jump_ns;
        log_ev(EV_CLOCK_JUMP, m->phase, 0, 0, 0, m->ns);
    }
    return !m->stopped;
}

static uint64_t nanoseconds(void *p)
{
    return ((struct model *)p)->ns;
}

static bool read_reg(void *p, uint32_t reg, uint32_t *value)
{
    struct model *m = p;
    CHECK(!m->stopped);
    switch(reg) {
    case 0x807: *value = m->wptr; break;
    case 0x201: *value = 0; break;
    case 0x823: *value = 0; break;
    case 0x23b0c:
        *value = 0;
        if(m->site == SITE_SUBMIT && m->phase == PH_INITIAL)
            m->after_healthy_phase = PH_RING;
        break;
    case 0x23b13:
        if(m->status_busy) {
            *value = 1;
            --m->status_busy;
        } else {
            *value = 0;
        }
        break;
    default:
        fprintf(stderr, "unexpected read reg 0x%x\n", reg);
        exit(2);
    }
    log_ev(EV_READ_REG, m->phase, reg, *value, 0, 0);
    return true;
}

static bool write_reg(void *p, uint32_t reg, uint32_t value)
{
    struct model *m = p;
    CHECK(!m->stopped);
    ++m->writes;
    if(reg == 0x1f8c3) {
        CHECK(value <= 1);
        /* Fence enable stays in the ring publish phase; clearing it starts the
         * completion polling/confirmation phase. */
        if(!value) {
            m->completion_started = true;
            m->phase = (m->pending_total == 0) ? PH_COMPLETE : PH_POLL;
        }
    } else {
        CHECK(reg == 0x807);
        if(m->phase == PH_RING)
            m->after_healthy_phase = PH_FENCE; /* switch after the publish guard */
        m->wptr = value;
        m->shadow = value;
        m->eop = 1;
    }
    log_ev(EV_WRITE_REG, m->phase, reg, value, 0, 0);
    return true;
}

static bool read_memory(void *p, enum ggr_memory mem, uint32_t off, uint32_t *value)
{
    struct model *m = p;
    CHECK(!m->stopped);
    if(mem == GGR_RING) {
        CHECK(off < 32768 && !(off & 3));
        ++m->legacy_read_ring_calls;
        *value = m->ring[off / 4];
    } else if(mem == GGR_SHADOW) {
        CHECK(!off);
        *value = m->shadow;
    } else {
        CHECK(mem == GGR_COMPLETION && !off);
        if(m->completion_started && m->pending_left) {
            --m->pending_left;
            *value = 0;
        } else {
            *value = m->eop;
        }
    }
    log_ev(EV_READ_MEM, m->phase, (uint32_t)mem, off, *value, 0);
    return true;
}

static bool write_ring(void *p, uint32_t off, uint32_t value)
{
    struct model *m = p;
    CHECK(!m->stopped && off < 32768 && !(off & 3));
    ++m->writes;
    ++m->legacy_write_ring_calls;
    m->phase = PH_RING;
    m->ring[off / 4] = value;
    log_ev(EV_WRITE_RING, m->phase, off, value, 0, 0);
    return true;
}

static bool ring_span(void *p, uint32_t off, const uint32_t *words, uint32_t count, bool verify)
{
    struct model *m = p;
    CHECK(!m->stopped && words && count && count <= GGR_RING_PACKET_WORDS);
    CHECK((off & 3) == 0 && off < 32768);
    m->phase = PH_RING;
    ++m->ring_span_calls;
    log_ev(EV_RING_SPAN, m->phase, off, count, verify ? 1 : 0, 0);
    for(uint32_t i = 0; i < count; ++i) {
        uint32_t at = (off + 4 * i) % 32768;
        /* This fake span rechecks only GGR_BUSY, operation_end_ns, and the CPU
         * RAM word. It omits the board callback's board-state and ggrb_end
         * predicates and reports failure rather than asserting on expiry. */
        if(m->ctx->state != GGR_BUSY || m->ns >= m->ctx->operation_end_ns)
            return false;
        if(verify) {
            if(m->ring[at / 4] != words[i])
                return false;
        } else {
            m->ring[at / 4] = words[i];
        }
        ++m->ring_words;
    }
    return true;
}

static bool barrier(void *p)
{
    struct model *m = p;
    CHECK(!m->stopped);
    log_ev(EV_BARRIER, m->phase, 0, 0, 0, 0);
    return true;
}

static bool delay_us(void *p, uint32_t us)
{
    struct model *m = p;
    CHECK(!m->stopped && us == 10);
    m->ns += 10000;
    log_ev(EV_DELAY, m->phase, us, 0, 0, m->ns);
    if(m->phase == PH_POLL) {
        ++m->polls_done;
        if(m->polls_done >= m->pending_total)
            m->phase = PH_COMPLETE;
    }
    return true;
}

static void quarantine(void *p)
{
    struct model *m = p;
    CHECK(!m->stopped);
    m->stopped = true;
    ++m->quarantines;
    log_ev(EV_QUARANTINE, m->phase, 0, 0, 0, 0);
}

static struct ggr_ops make_ops(struct model *m, bool use_ring_span)
{
    struct ggr_ops o = {
        .cookie = m,
        .healthy = healthy,
        .nanoseconds = nanoseconds,
        .read_reg = read_reg,
        .write_reg = write_reg,
        .read_memory = read_memory,
        .write_ring = write_ring,
        .barrier = barrier,
        .delay_us = delay_us,
        .quarantine = quarantine,
        .ring_span = use_ring_span ? ring_span : NULL
    };
    return o;
}

static void reset_model(struct model *m, struct ggr_context *c, bool use_ring_span, uint64_t ns)
{
    memset(m, 0, sizeof(*m));
    memset(c, 0, sizeof(*c));
    m->ctx = c;
    m->ring_span_enabled = use_ring_span;
    m->wptr = 20;
    m->shadow = 20;
    m->eop = 0;
    m->ns = ns;
    m->phase = PH_INITIAL;
    m->next_healthy_phase = -1;
    m->after_healthy_phase = -1;
    m->site = SITE_OPEN;
    event_count = 0;
}

static enum ggr_error do_open(struct model *m, struct ggr_context *c, bool use_ring_span)
{
    struct ggr_ops o = make_ops(m, use_ring_span);
    m->site = SITE_OPEN;
    m->phase = PH_INITIAL;
    return ggr_open(c, &o, 0xfc010000u, 0xfc018000u);
}

static enum ggr_error do_idle(struct model *m, struct ggr_context *c)
{
    m->site = SITE_IDLE;
    m->phase = PH_INITIAL;
    return ggr_check_idle(c);
}

static enum ggr_error do_submit(struct model *m, struct ggr_context *c, uint32_t *fence)
{
    uint64_t address[1] = {GGR_VA_START + 0x10000};
    uint32_t words[1] = {4};
    m->site = SITE_SUBMIT;
    m->phase = PH_INITIAL;
    return ggr_submit(c, address, words, 1, fence);
}

static void validate_packet(struct model *m)
{
    const uint32_t *p = &m->ring[20];
    CHECK(p[0] == 0x70bf8003u);
    CHECK(p[1] == GGR_VA_START + 0x10000);
    CHECK(p[2] == 0 && p[3] == 4);
    CHECK(p[4] == 0x70460004u && p[5] == 4);
    CHECK(p[6] == 0xfc018000u && p[7] == 0);
    CHECK(p[8] == 1);
    CHECK(p[9] == 0x70620002u && p[10] == 0xfc010000u && p[11] == 0);
}

struct adjacency {
    uint32_t pairs;
    uint32_t adjacent;
    uint32_t separated;
    uint32_t max_gap;
    uint32_t gap_kinds[EV_N];
    uint32_t adjacent_by_phase[PH_N];
};

static struct adjacency analyse_adjacency(void)
{
    struct adjacency a;
    memset(&a, 0, sizeof(a));
    for(size_t i = 0; i < event_count; ++i) {
        if(events[i].kind != EV_HEALTHY)
            continue;
        for(size_t j = i + 1; j < event_count; ++j) {
            if(events[j].kind != EV_HEALTHY)
                continue;
            uint32_t gap = (uint32_t)(j - i - 1);
            ++a.pairs;
            if(gap) {
                ++a.separated;
                if(gap > a.max_gap)
                    a.max_gap = gap;
                for(size_t k = i + 1; k < j; ++k)
                    ++a.gap_kinds[events[k].kind];
            } else {
                ++a.adjacent;
                ++a.adjacent_by_phase[events[i].phase];
            }
            break; /* next healthy after i */
        }
    }
    return a;
}

static void write_trace(const char *path)
{
    FILE *f = fopen(path, "w");
    if(!f) {
        fprintf(stderr, "cannot write %s: %s\n", path, strerror(errno));
        exit(2);
    }
    for(size_t i = 0; i < event_count; ++i) {
        const struct ev *e = &events[i];
        fprintf(f, "{\"seq\":%zu,\"phase\":\"%s\",\"event\":\"%s\"",
            i + 1, phase_name[e->phase], evkind_name[e->kind]);
        switch(e->kind) {
        case EV_HEALTHY:
            fprintf(f, ",\"healthy_index\":%u", e->a);
            break;
        case EV_READ_REG:
        case EV_WRITE_REG:
            fprintf(f, ",\"reg\":\"0x%x\",\"value\":%u", e->a, e->b);
            break;
        case EV_READ_MEM:
            fprintf(f, ",\"memory\":\"%s\",\"offset\":%u,\"value\":%u",
                mem_name((enum ggr_memory)e->a), e->b, e->c);
            break;
        case EV_WRITE_RING:
            fprintf(f, ",\"offset\":%u,\"value\":%u", e->a, e->b);
            break;
        case EV_RING_SPAN:
            fprintf(f, ",\"offset\":%u,\"words\":%u,\"mode\":\"%s\"",
                e->a, e->b, e->c ? "verify" : "write");
            break;
        case EV_DELAY:
            fprintf(f, ",\"us\":%u,\"clock_ns\":%" PRIu64, e->a, e->n);
            break;
        case EV_SUCCESS:
            fprintf(f, ",\"fence\":%u", e->a);
            break;
        case EV_CLOCK_JUMP:
            fprintf(f, ",\"clock_ns\":%" PRIu64, e->n);
            break;
        default:
            break;
        }
        fputs("}\n", f);
    }
    CHECK(fclose(f) == 0);
}

struct run_result {
    enum ggr_error rc;
    uint32_t fence;
    uint32_t polls;
    uint32_t state;
    uint32_t healthy_total;
    uint32_t healthy_by_phase[PH_N];
    uint32_t event_total;
    uint32_t open_healthy;
    uint32_t idle_healthy;
    uint32_t submit_healthy;
    uint64_t clock_ns;
    uint64_t operation_end_ns;
    struct adjacency adjacency;
};

struct scenario {
    const char *id;
    const char *description;
    uint32_t pending;
    uint32_t status_busy;
};

static void primary_run(const struct scenario *s, bool use_ring_span,
    const char *trace_path, struct model *out_m, struct run_result *r)
{
    struct model m;
    struct ggr_context c;
    uint32_t fence = FENCE_SENTINEL;

    reset_model(&m, &c, use_ring_span, BASE_NS);
    m.pending_total = m.pending_left = s->pending;
    m.status_busy = s->status_busy;
    CHECK(do_open(&m, &c, use_ring_span) == GGR_OK);
    CHECK(c.operation_end_ns == BASE_NS + UINT64_C(2000000000));
    uint32_t after_open = m.healthy_calls;
    CHECK(do_idle(&m, &c) == GGR_OK);
    uint32_t after_idle = m.healthy_calls;

    event_count = 0;
    memset(m.phase_healthy, 0, sizeof(m.phase_healthy));
    m.site = SITE_SUBMIT;
    m.phase = PH_INITIAL;
    r->rc = do_submit(&m, &c, &fence);
    r->fence = fence;
    if(r->rc == GGR_OK)
        log_ev(EV_SUCCESS, m.phase, fence, 0, 0, 0);

    CHECK(r->rc == GGR_OK);
    CHECK(fence == 1);
    CHECK(c.state == GGR_READY);
    CHECK(c.completed == 1 && c.submitted == 1 && c.wptr == 32);
    CHECK(m.quarantines == 0);
    CHECK(m.pending_left == 0);
    validate_packet(&m);

    r->polls = c.polls;
    r->state = c.state;
    r->healthy_total = m.healthy_calls - after_idle;
    memcpy(r->healthy_by_phase, m.phase_healthy, sizeof(r->healthy_by_phase));
    r->event_total = (uint32_t)event_count;
    r->open_healthy = after_open;
    r->idle_healthy = after_idle - after_open;
    r->submit_healthy = r->healthy_total;
    r->clock_ns = m.ns;
    r->operation_end_ns = c.operation_end_ns;
    CHECK(r->healthy_total ==
        r->healthy_by_phase[PH_INITIAL] + r->healthy_by_phase[PH_RING] +
        r->healthy_by_phase[PH_FENCE] + r->healthy_by_phase[PH_POLL] +
        r->healthy_by_phase[PH_COMPLETE]);
    r->adjacency = analyse_adjacency();
    write_trace(trace_path);
    *out_m = m;
}

struct injection_totals {
    uint32_t cases;
    struct { uint32_t boundaries; uint32_t submit_boundaries; } per[2][4]; /* cfg, scenario */
    uint32_t by_site_phase[3][PH_N];
};

static void injection_case(const struct scenario *s, bool use_ring_span, uint32_t index,
    enum site expected_site, int expected_phase, struct model *clean)
{
    struct model m;
    struct ggr_context c;
    uint32_t fence = FENCE_SENTINEL;

    reset_model(&m, &c, use_ring_span, BASE_NS);
    m.pending_total = m.pending_left = s->pending;
    m.status_busy = s->status_busy;
    m.fail_at = index;

    if(do_open(&m, &c, use_ring_span) == GGR_OK)
        do_idle(&m, &c);
    enum ggr_error src = do_submit(&m, &c, &fence);

    CHECK(m.failed_here);
    CHECK(src != GGR_OK);
    CHECK(m.quarantines == 1);
    CHECK(c.state == GGR_FAILED);
    CHECK(fence == FENCE_SENTINEL);
    CHECK(event_count >= 1);
    CHECK(events[event_count - 1].kind == EV_QUARANTINE);
    for(size_t i = 0; i < event_count; ++i)
        CHECK(events[i].kind != EV_SUCCESS);
    CHECK(clean->health_site[index] == expected_site);
    CHECK(clean->health_phase[index] == expected_phase);

    /* A second entry after quarantine must not reach any operation callback. */
    uint32_t before_events = (uint32_t)event_count;
    uint32_t before_healthy = m.healthy_calls;
    uint32_t before_writes = m.writes;
    CHECK(do_submit(&m, &c, &fence) == GGR_UNAVAILABLE);
    CHECK((uint32_t)event_count == before_events);
    CHECK(m.healthy_calls == before_healthy);
    CHECK(m.writes == before_writes);
    CHECK(m.quarantines == 1);
    CHECK(fence == FENCE_SENTINEL);
}

static void run_injection(const struct scenario *s, bool use_ring_span, int cfg_index,
    int scenario_index, struct injection_totals *tot)
{
    struct model clean;
    struct ggr_context c;
    uint32_t fence = FENCE_SENTINEL;

    reset_model(&clean, &c, use_ring_span, BASE_NS);
    clean.pending_total = clean.pending_left = s->pending;
    clean.status_busy = s->status_busy;
    CHECK(do_open(&clean, &c, use_ring_span) == GGR_OK);
    CHECK(do_idle(&clean, &c) == GGR_OK);
    CHECK(do_submit(&clean, &c, &fence) == GGR_OK);
    CHECK(fence == 1);
    uint32_t total = clean.healthy_calls;

    tot->per[cfg_index][scenario_index].boundaries = total;
    for(uint32_t i = 1; i <= total; ++i) {
        injection_case(s, use_ring_span, i, clean.health_site[i], clean.health_phase[i], &clean);
        ++tot->cases;
        ++tot->by_site_phase[clean.health_site[i]][clean.health_phase[i]];
        if(clean.health_site[i] == SITE_SUBMIT)
            ++tot->per[cfg_index][scenario_index].submit_boundaries;
    }
}

static void edge_case(const char *id, const char *expected, const char *phase,
    enum ggr_error rc, struct model *m, struct ggr_context *c, uint32_t fence,
    bool want_success, const char *detail)
{
    if(want_success) {
        CHECK(rc == GGR_OK);
        if(fence)
            CHECK(fence == 1);
        CHECK(c->state == GGR_READY);
        CHECK(m->quarantines == 0);
    } else {
        CHECK(rc != GGR_OK);
        CHECK(fence == FENCE_SENTINEL);
        CHECK(c->state == GGR_FAILED);
        CHECK(m->quarantines == 1);
        CHECK(event_count >= 1 && events[event_count - 1].kind == EV_QUARANTINE);
        for(size_t i = 0; i < event_count; ++i)
            CHECK(events[i].kind != EV_SUCCESS);
    }
    fprintf(stderr, "EDGE %s expected=%s rc=%s phase=%s fence=%u quarantines=%u clock=%" PRIu64
        " deadline=%" PRIu64 " detail=%s\n",
        id, expected, rc_name(rc), phase, fence, m->quarantines, m->ns,
        c->operation_end_ns, detail);
}

static int run_edges(void)
{
    struct model m;
    struct ggr_context c;
    uint32_t fence;
    int passed = 0;

    /* Nonzero clock is accepted and the deadline is exactly now + 2s. */
    reset_model(&m, &c, true, BASE_NS);
    CHECK(do_open(&m, &c, true) == GGR_OK);
    CHECK(c.operation_end_ns == BASE_NS + UINT64_C(2000000000));
    CHECK(do_idle(&m, &c) == GGR_OK);
    edge_case("nonzero_clock_open_idle", "success", "initial_idle_validation",
        GGR_OK, &m, &c, 0, true, "nonzero base clock accepted");
    ++passed;

    /* Exact deadline equality at the first health guard of each submit phase. */
    for(int cfg = 0; cfg < 2; ++cfg) {
        bool span = cfg == 0;
        for(int p = 0; p < PH_N; ++p) {
            /* Locate the first submit boundary in this phase from a clean run. */
            reset_model(&m, &c, span, BASE_NS);
            CHECK(do_open(&m, &c, span) == GGR_OK);
            CHECK(do_idle(&m, &c) == GGR_OK);
            event_count = 0;
            memset(m.phase_healthy, 0, sizeof(m.phase_healthy));
            m.site = SITE_SUBMIT;
            m.phase = PH_INITIAL;
            fence = FENCE_SENTINEL;
            CHECK(do_submit(&m, &c, &fence) == GGR_OK);
            uint32_t first = 0;
            for(uint32_t i = 1; i <= m.healthy_calls; ++i) {
                if(m.health_site[i] == SITE_SUBMIT && m.health_phase[i] == p) {
                    first = i;
                    break;
                }
            }
            if(first == 0)
                continue; /* immediate completion has no incomplete poll phase */

            char id[160];
            snprintf(id, sizeof(id), "deadline_exact_%s_%s",
                span ? "production" : "legacy", phase_name[p]);
            reset_model(&m, &c, span, BASE_NS);
            m.pending_total = m.pending_left = 0;
            CHECK(do_open(&m, &c, span) == GGR_OK);
            CHECK(do_idle(&m, &c) == GGR_OK);
            m.jump_at = first;
            m.jump_mode = 1;
            fence = FENCE_SENTINEL;
            enum ggr_error rc = do_submit(&m, &c, &fence);
            CHECK(m.jumped);
            edge_case(id, "failure", phase_name[p], rc, &m, &c, fence, false,
                "clock reaches operation_end_ns exactly");
            ++passed;
        }
    }

    /* One nanosecond inside the deadline remains acceptable for immediate. */
    for(int cfg = 0; cfg < 2; ++cfg) {
        bool span = cfg == 0;
        for(int p = 0; p < PH_N; ++p) {
            reset_model(&m, &c, span, BASE_NS);
            CHECK(do_open(&m, &c, span) == GGR_OK);
            CHECK(do_idle(&m, &c) == GGR_OK);
            event_count = 0;
            m.site = SITE_SUBMIT;
            m.phase = PH_INITIAL;
            fence = FENCE_SENTINEL;
            CHECK(do_submit(&m, &c, &fence) == GGR_OK);
            uint32_t first = 0;
            for(uint32_t i = 1; i <= m.healthy_calls; ++i) {
                if(m.health_site[i] == SITE_SUBMIT && m.health_phase[i] == p) {
                    first = i;
                    break;
                }
            }
            if(first == 0)
                continue;
            char id[160];
            snprintf(id, sizeof(id), "deadline_minus_one_%s_%s",
                span ? "production" : "legacy", phase_name[p]);
            reset_model(&m, &c, span, BASE_NS);
            CHECK(do_open(&m, &c, span) == GGR_OK);
            CHECK(do_idle(&m, &c) == GGR_OK);
            m.jump_at = first;
            m.jump_mode = 2;
            fence = FENCE_SENTINEL;
            enum ggr_error rc = do_submit(&m, &c, &fence);
            CHECK(m.jumped);
            edge_case(id, "success", phase_name[p], rc, &m, &c, fence, true,
                "clock remains at operation_end_ns - 1");
            ++passed;
        }
    }

    /* Unsigned deadline overflow is rejected before any ring write. */
    reset_model(&m, &c, true, UINT64_MAX - UINT64_C(1000000000));
    enum ggr_error rc = do_open(&m, &c, true);
    fence = FENCE_SENTINEL;
    edge_case("deadline_overflow_open", "failure", "ggr_open", rc, &m, &c, fence, false,
        "now + 2s overflows uint64");
    ++passed;

    reset_model(&m, &c, true, BASE_NS);
    CHECK(do_open(&m, &c, true) == GGR_OK);
    CHECK(do_idle(&m, &c) == GGR_OK);
    m.ns = UINT64_MAX - UINT64_C(1000000000);
    uint32_t writes_before = m.writes;
    fence = FENCE_SENTINEL;
    rc = do_submit(&m, &c, &fence);
    CHECK(m.writes == writes_before);
    CHECK(m.ring_span_calls == 0 && m.legacy_write_ring_calls == 0);
    edge_case("deadline_overflow_submit", "failure", "ggr_submit", rc, &m, &c, fence, false,
        "rejected before state BUSY and ring writes");
    ++passed;

    /* The exact arithmetic boundary now = UINT64_MAX - 2s is still accepted. */
    reset_model(&m, &c, true, UINT64_MAX - UINT64_C(2000000000));
    rc = do_open(&m, &c, true);
    CHECK(rc == GGR_OK);
    CHECK(c.operation_end_ns == UINT64_MAX);
    CHECK(do_idle(&m, &c) == GGR_OK);
    edge_case("deadline_max_boundary_open_idle", "success", "ggr_open+idle", rc, &m, &c, 0,
        true, "now = UINT64_MAX - 2s exactly");
    ++passed;

    reset_model(&m, &c, true, UINT64_MAX - UINT64_C(2000000000) + 1);
    rc = do_open(&m, &c, true);
    fence = FENCE_SENTINEL;
    edge_case("deadline_max_boundary_plus_one", "failure", "ggr_open", rc, &m, &c, fence,
        false, "one nanosecond past the safe arithmetic boundary");
    ++passed;

    return passed;
}

static void print_phase_counts(const uint32_t counts[PH_N])
{
    putchar('{');
    for(int p = 0; p < PH_N; ++p)
        printf("%s\"%s\":%u", p ? "," : "", phase_name[p], counts[p]);
    putchar('}');
}

static void print_adjacency(const struct adjacency *a)
{
    printf("{\"healthy_pairs\":%u,\"directly_adjacent_pairs\":%u,"
        "\"separated_pairs\":%u,\"max_intervening_events\":%u,"
        "\"adjacent_by_phase\":{",
        a->pairs, a->adjacent, a->separated, a->max_gap);
    bool first = true;
    for(int p = 0; p < PH_N; ++p) {
        if(!a->adjacent_by_phase[p])
            continue;
        printf("%s\"%s\":%u", first ? "" : ",", phase_name[p], a->adjacent_by_phase[p]);
        first = false;
    }
    printf("},\"intervening_event_occurrences\":{");
    first = true;
    for(int k = 0; k < EV_N; ++k) {
        if(!a->gap_kinds[k])
            continue;
        printf("%s\"%s\":%u", first ? "" : ",", evkind_name[k], a->gap_kinds[k]);
        first = false;
    }
    printf("}}");
}

int main(int argc, char **argv)
{
    if(argc != 2) {
        fprintf(stderr, "usage: %s TRACE_DIR\n", argv[0]);
        return 2;
    }
    const char *trace_dir = argv[1];
    struct stat st;
    if(stat(trace_dir, &st) != 0 || !S_ISDIR(st.st_mode)) {
        fprintf(stderr, "trace directory missing: %s\n", trace_dir);
        return 2;
    }

    const struct scenario scenarios[4] = {
        {"valid_ib_immediate", "one valid IB, completion visible on first poll", 0, 0},
        {"pending_completion_1", "one completion poll observes not-ready", 1, 0},
        {"pending_completion_3", "three completion polls observe not-ready", 3, 0},
        {"delayed_fence", "fence status stays busy for two status polls", 0, 2}
    };

    struct model primary[2][4];
    struct run_result results[2][4];
    char trace_path[512];
    for(int cfg = 0; cfg < 2; ++cfg) {
        bool span = cfg == 0;
        for(int s = 0; s < 4; ++s) {
            snprintf(trace_path, sizeof(trace_path), "%s/%s_%s.jsonl",
                trace_dir, span ? "production" : "legacy", scenarios[s].id);
            primary_run(&scenarios[s], span, trace_path, &primary[cfg][s], &results[cfg][s]);
        }
    }

    struct injection_totals inj;
    memset(&inj, 0, sizeof(inj));
    for(int cfg = 0; cfg < 2; ++cfg)
        for(int s = 0; s < 4; ++s)
            run_injection(&scenarios[s], cfg == 0, cfg, s, &inj);

    int edge_count = run_edges();

    printf("{\n");
    printf("\"schema\":\"ggr-submit-healthy-counts/v1\",\n");
    printf("\"scope\":\"host-only callback counts against a register/RAM model; no GPU or IB execution, no device operation, no hardware timing, and no frame rate or FPS measurement\",\n");
    printf("\"base_clock_ns\":%" PRIu64 ",\n", BASE_NS);
    printf("\"phases\":[");
    for(int p = 0; p < PH_N; ++p)
        printf("%s\"%s\"", p ? "," : "", phase_name[p]);
    printf("],\n");
    printf("\"configs\":[{\"id\":\"production_ring_span\",\"ring_span\":true},"
        "{\"id\":\"legacy_fallback\",\"ring_span\":false}],\n");
    printf("\"startup\":{\"ggr_open_healthy_per_run\":%u,"
        "\"ggr_check_idle_healthy_per_run\":%u},\n",
        results[0][0].open_healthy, results[0][0].idle_healthy);
    printf("\"scenarios\":[\n");
    bool first_scenario = true;
    for(int cfg = 0; cfg < 2; ++cfg) {
        for(int s = 0; s < 4; ++s) {
            const struct run_result *r = &results[cfg][s];
            printf("%s", first_scenario ? "" : ",\n");
            first_scenario = false;
            printf("{\"id\":\"%s_%s\",\"scenario\":\"%s\",\"config\":\"%s\","
                "\"ring_span\":%s,\"pending_completion_polls\":%u,"
                "\"fence_status_busy_polls\":%u,\"description\":\"%s\","
                "\"result\":{\"rc\":\"%s\",\"fence\":%u,\"state\":\"%s\","
                "\"polls\":%u,\"quarantines\":0,\"writes\":%u,"
                "\"ring_words\":%u,\"ring_span_calls\":%u,"
                "\"legacy_write_ring_calls\":%u,\"legacy_read_ring_calls\":%u,"
                "\"start_clock_ns\":%" PRIu64 ",\"final_clock_ns\":%" PRIu64 ","
                "\"operation_end_ns\":%" PRIu64 "},"
                "\"healthy_total\":%u,\n\"healthy_by_phase\":",
                cfg == 0 ? "production" : "legacy", scenarios[s].id,
                scenarios[s].id, cfg == 0 ? "production_ring_span" : "legacy_fallback",
                cfg == 0 ? "true" : "false", scenarios[s].pending,
                scenarios[s].status_busy, scenarios[s].description,
                rc_name(r->rc), r->fence, state_name(r->state), r->polls,
                primary[cfg][s].writes, primary[cfg][s].ring_words,
                primary[cfg][s].ring_span_calls,
                primary[cfg][s].legacy_write_ring_calls,
                primary[cfg][s].legacy_read_ring_calls,
                BASE_NS, r->clock_ns, r->operation_end_ns, r->healthy_total);
            print_phase_counts(r->healthy_by_phase);
            printf(",\n\"events_total\":%u,\"trace\":\"traces/%s_%s.jsonl\","
                "\"adjacency\":",
                r->event_total, cfg == 0 ? "production" : "legacy", scenarios[s].id);
            print_adjacency(&r->adjacency);
            printf("}");
        }
    }
    printf("\n],\n");

    printf("\"injection\":{\"cases\":%u,\"all_passed\":true,"
        "\"assertions_per_case\":[\"failure boundary reached\",\"quarantine once\","
        "\"state FAILED\",\"no success fence\",\"quarantine is final callback\","
        "\"no success event\",\"second entry performs zero callbacks\","
        "\"second entry stays UNAVAILABLE\"],\n", inj.cases);
    printf("\"by_site_phase\":{");
    bool first_site = true;
    for(int g = 0; g < SITE_N; ++g) {
        for(int p = 0; p < PH_N; ++p) {
            if(!inj.by_site_phase[g][p])
                continue;
            printf("%s\"%s/%s\":%u", first_site ? "" : ",", site_name[g],
                phase_name[p], inj.by_site_phase[g][p]);
            first_site = false;
        }
    }
    printf("},\n\"per_run\":[");
    bool first_inj = true;
    for(int cfg = 0; cfg < 2; ++cfg) {
        for(int s = 0; s < 4; ++s) {
            printf("%s{\"scenario\":\"%s_%s\",\"config\":\"%s\","
                "\"boundaries\":%u,\"submit_boundaries\":%u,\"passed\":%u}",
                first_inj ? "" : ",", cfg == 0 ? "production" : "legacy",
                scenarios[s].id, cfg == 0 ? "production_ring_span" : "legacy_fallback",
                inj.per[cfg][s].boundaries, inj.per[cfg][s].submit_boundaries,
                inj.per[cfg][s].boundaries);
            first_inj = false;
        }
    }
    printf("]},\n");

    printf("\"deadline_checks\":{\"passed\":%d,\"base_clock_nonzero\":true,"
        "\"exact_deadline_fails_closed\":true,\"deadline_minus_one_passes\":true,"
        "\"overflow_rejected_before_ring_write\":true,"
        "\"max_arithmetic_boundary_accepted\":true},\n", edge_count);
    printf("\"assertions\":%lu\n", assertions);
    printf("}\n");
    return 0;
}
