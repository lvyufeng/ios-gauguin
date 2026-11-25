#ifndef GAUGUIN_C4_QUEUE_TRACE_H
#define GAUGUIN_C4_QUEUE_TRACE_H
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* CPU clock only. This does not enable Metal profiling or add GPU commands.
 * The caller owns object throughout the call; the tracer never dereferences it.
 * A CB is identified by (object, createdAt), not the reusable pointer alone.
 * Compiler spans use their call-start time instead of a CB creation time. */
#define GCQ_LIMIT 32768u
#define GCQ_LINE_MAX 128u
static int gcq_scope = -1;
static unsigned gcq_records;

static __attribute__((noinline)) void
gauguin_c4_queue_trace(unsigned phase, const void *object, double start,
                       double end, unsigned value)
{
    /* Ordered comparisons reject NaN and infinities without a new libm call. */
    if (phase > 9 || !object || !(start >= 220 && start < 270) ||
        !(end >= start && end < 900)) return;
    int scope = __atomic_load_n(&gcq_scope, __ATOMIC_ACQUIRE);
    if (scope < 0) {
        const char *name = getprogname(), *mode = getenv("GAUGUIN_EAGL_MODE");
        scope = name && !strcmp(name, "backboardd") && getuid() == 501 &&
                geteuid() == 501 && mode && !strcmp(mode, "edr-default318");
        __atomic_store_n(&gcq_scope, scope, __ATOMIC_RELEASE);
    }
    if (!scope) return;
    /* Saturating CAS: an arbitrarily long run cannot wrap and reopen the log.
     * Exactly one racing caller emits the exhaustion marker. */
    unsigned n = __atomic_load_n(&gcq_records, __ATOMIC_RELAXED);
    do {
        if (n > GCQ_LIMIT) return;
    } while (!__atomic_compare_exchange_n(&gcq_records, &n, n + 1, 1,
                                         __ATOMIC_RELAXED, __ATOMIC_RELAXED));
    if (n == GCQ_LIMIT) {
        fprintf(stderr, "GAUGUIN C4Q321: limit=32768 coverage=incomplete\n");
        return;
    }
    /* With the bounds above, 64-bit pointers and unsigned 32-bit value, each
     * row is under GCQ_LINE_MAX bytes, including its newline. One stdio call
     * keeps concurrent callers' rows intact. No per-frame fflush. */
    fprintf(stderr, "GAUGUIN C4Q321: phase=%u object=%p start_us=%.0f end_us=%.0f value=%u\n",
            phase, object, start * 1e6, end * 1e6, value);
}
#endif
