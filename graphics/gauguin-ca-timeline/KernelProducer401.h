/* Included by kdebug.c beside the native CA observer. Identity-only records
 * hold no pointers to caller objects, IOSurfaces, or native buffer storage. */
#ifndef GAUGUIN_KERNEL_PRODUCER_401_H
#define GAUGUIN_KERNEL_PRODUCER_401_H

#include "gauguin_render_producer401.h"

enum { F401_PRODUCER_CAP = 64 };
static LCK_GRP_DECLARE(f401_producer_group, "display producer");
static LCK_SPIN_DECLARE(f401_producer_lock, &f401_producer_group);
static struct render401_producer f401_scope[F376_DISPLAY_THREADS];
static struct {
    uint64_t renderer, expires;
    uint32_t cookie, surface;
} f401_producers[F401_PRODUCER_CAP];
static uint32_t f401_next_epoch, f401_next_cookie;

uint32_t sweet_ca401_declare_target(task_t, uint64_t, uint64_t, uint32_t);
uint32_t sweet_ca401_swap_cookie(uint32_t);
uint32_t sweet_ca401_writer_target(task_t, uint32_t);

static struct render401_producer *
f401_find_scope(uint64_t renderer, uint64_t tid, bool create)
{
    struct render401_producer *available = NULL;
    for (unsigned i = 0; i < F376_DISPLAY_THREADS; ++i) {
        struct render401_producer *scope = &f401_scope[i];
        if (scope->depth && scope->renderer == renderer && scope->thread == tid) {
            return scope;
        }
        if (!scope->depth && !available) available = scope;
    }
    return create ? available : NULL;
}

static void
f401_native_render(uint64_t identity, unsigned kind, uint64_t tick)
{
    if ((kind != F374_RENDER_BEGIN && kind != F374_RENDER_END) ||
        tick < f374_start || tick >= f374_end) return;

    const uint64_t tid = thread_tid(current_thread());
    struct arm_saved_state *ss = get_user_regs(current_thread());
    const uint64_t native_pc = UINT64_C(0x1c261ec58);
    const uint64_t expected = kind == F374_RENDER_BEGIN ?
        UINT64_C(0x1884f4f3c) : UINT64_C(0x1884f6b7c);
    bool certified = false;
    if (ss && is_saved_state64(ss) && get_saved_state_pc(ss) >= native_pc) {
        const uint64_t slide = get_saved_state_pc(ss) - native_pc;
        certified = f385_cache(slide, &f385_receiver_slide) && get_saved_state_lr(ss) == expected + slide;
    }

    lck_spin_lock(&f401_producer_lock);
    struct render401_producer *scope = f401_find_scope(identity, tid, certified && kind == F374_RENDER_BEGIN);
    if (scope && !certified) {
        scope->ambiguous = true;
        const unsigned slot = scope->cookie % F401_PRODUCER_CAP;
        if (scope->cookie && f401_producers[slot].cookie == scope->cookie) f401_producers[slot].expires = 0;
    } else if (scope && kind == F374_RENDER_BEGIN && f401_next_epoch < UINT32_MAX) {
        render401_begin(scope, identity, tid, tick, ++f401_next_epoch);
    } else if (scope && kind == F374_RENDER_END) {
        render401_end(scope, identity, tid, tick);
    }
    lck_spin_unlock(&f401_producer_lock);
}

/* The GPU user's task identity and this frame's native render thread
 * must agree before the frontend can obtain a one-capture cookie. */
uint32_t
sweet_ca401_declare_target(task_t task, uint64_t object, uint64_t made, uint32_t surface)
{
    if (task != current_task() || !f375_enter()) return 0;
    const uint64_t tick = mach_absolute_time();
    const uint64_t who = f385_identity(task);
    const uint64_t tid = thread_tid(current_thread());
    const unsigned lane = f385_stroke(tick);
    uint32_t cookie = 0;
    if (who && who == f374_receiver && lane && surface) {
        lck_spin_lock(&f401_producer_lock);
        struct render401_producer *scope = f401_find_scope(who, tid, false);
        if (scope && f401_next_cookie < UINT32_MAX) {
            const uint32_t previous = scope->cookie;
            const uint32_t next = f401_next_cookie + 1;
            const unsigned slot = next % F401_PRODUCER_CAP;
            if (previous || f401_producers[slot].expires <= tick) {
                cookie = render401_declare(scope, who, tid, tick, f374_end, object, made, surface, next);
                if (cookie == next) {
                    f401_next_cookie = next;
                    f401_producers[slot].cookie = cookie;
                    f401_producers[slot].surface = surface;
                    f401_producers[slot].renderer = who;
                    f401_producers[slot].expires = f385_gestures[lane - 1].until;
                } else if (!cookie && previous && scope->ambiguous) {
                    const unsigned old = previous % F401_PRODUCER_CAP;
                    if (f401_producers[old].cookie == previous) f401_producers[old].expires = 0;
                }
            }
        }
        lck_spin_unlock(&f401_producer_lock);
    }
    __atomic_fetch_sub(&f374_gate, 1, __ATOMIC_RELEASE);
    return cookie;
}

uint32_t
sweet_ca401_swap_cookie(uint32_t surface)
{
    if (!surface || !f375_enter()) return 0;
    const uint64_t now = mach_absolute_time();
    const uint64_t who = f385_identity(current_task());
    const uint64_t tid = thread_tid(current_thread());
    uint32_t cookie = 0;
    if (who && who == f374_receiver && f385_stroke(now)) {
        lck_spin_lock(&f401_producer_lock);
        const struct render401_producer *scope = f401_find_scope(who, tid, false);
        if (scope) cookie = render401_lookup(scope, who, tid, now, f374_end, surface);
        lck_spin_unlock(&f401_producer_lock);
    }
    __atomic_fetch_sub(&f374_gate, 1, __ATOMIC_RELEASE);
    return cookie;
}

uint32_t
sweet_ca401_writer_target(task_t task, uint32_t cookie)
{
    if (!cookie || task != current_task() || !f375_enter()) return 0;
    const uint64_t tick = mach_absolute_time();
    const uint64_t who = f385_identity(task);
    uint32_t target = 0;
    if (who && who == f374_receiver && f385_stroke(tick)) {
        lck_spin_lock(&f401_producer_lock);
        const unsigned index = cookie % F401_PRODUCER_CAP;
        if (f401_producers[index].cookie == cookie && f401_producers[index].renderer == who &&
            tick < f401_producers[index].expires) {
            target = f401_producers[index].surface;
        }
        lck_spin_unlock(&f401_producer_lock);
    }
    __atomic_fetch_sub(&f374_gate, 1, __ATOMIC_RELEASE);
    return target;
}
#endif
