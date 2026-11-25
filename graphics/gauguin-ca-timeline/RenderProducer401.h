/* Associate an actual frontend color target with a native render scope.
 * The caller serializes access and authenticates the native begin/end sites.
 * This identity is not a completion or permission to read the surface. */
#ifndef GAUGUIN_RENDER_PRODUCER_401_H
#define GAUGUIN_RENDER_PRODUCER_401_H

#include <stdbool.h>
#include <stdint.h>

struct render401_producer {
    uint64_t renderer, thread, begin;
    uint64_t object, created;
    uint32_t epoch, depth, surface, cookie;
    bool ambiguous;
};

static inline void
render401_begin(struct render401_producer *scope, uint64_t renderer,
    uint64_t thread, uint64_t tick, uint32_t epoch)
{
    if (!renderer || !thread || !tick || !epoch) return;
    if (scope->depth) {
        if (renderer != scope->renderer || thread != scope->thread || tick < scope->begin) return;
        scope->ambiguous = true;
        if (scope->depth < UINT32_MAX) ++scope->depth;
        return;
    }
    *scope = (struct render401_producer){
        .renderer = renderer, .thread = thread, .begin = tick, .epoch = epoch, .depth = 1
    };
}

static inline void
render401_end(struct render401_producer *scope, uint64_t renderer, uint64_t thread,
    uint64_t tick)
{
    if (renderer == scope->renderer && thread == scope->thread && tick >= scope->begin && scope->depth) {
        if (scope->depth == UINT32_MAX) return;
        if (--scope->depth == 0) *scope = (struct render401_producer){0};
    }
}

static inline bool
render401_current(const struct render401_producer *scope, uint64_t renderer,
    uint64_t thread, uint64_t tick, uint64_t capture_end)
{
    return scope->depth == 1 && !scope->ambiguous && scope->renderer == renderer &&
           scope->thread == thread && tick >= scope->begin && tick < capture_end;
}

/* The caller assigns a fresh nonzero cookie and carries it on the exact
 * command buffer. Duplicate reports for the same buffer coalesce. */
static inline uint32_t
render401_declare(struct render401_producer *scope, uint64_t renderer,
    uint64_t thread, uint64_t tick, uint64_t capture_end, uint64_t object,
    uint64_t created, uint32_t surface, uint32_t cookie)
{
    if (!render401_current(scope, renderer, thread, tick, capture_end) ||
        !object || created < scope->begin || created > tick || !surface || !cookie) {
        return 0;
    }
    if (scope->cookie) {
        if (scope->object == object && scope->created == created && scope->surface == surface) {
            return scope->cookie;
        }
        scope->ambiguous = true;
        return 0;
    }
    scope->object = object;
    scope->created = created;
    scope->surface = surface;
    scope->cookie = cookie;
    return cookie;
}

static inline uint32_t
render401_lookup(const struct render401_producer *scope, uint64_t renderer,
    uint64_t thread, uint64_t tick, uint64_t capture_end, uint32_t surface)
{
    if (render401_current(scope, renderer, thread, tick, capture_end) &&
        surface && scope->surface == surface) {
        return scope->cookie;
    }
    return 0;
}
#endif
