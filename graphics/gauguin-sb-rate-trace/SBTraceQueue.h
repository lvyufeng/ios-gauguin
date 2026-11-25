/* Include after struct rate_row. One permanent queue, multiple producers,
 * one logger consumer. No producer lock, allocation, I/O or retry loop. */
#ifndef GAUGUIN_SB_TRACE_QUEUE_H
#define GAUGUIN_SB_TRACE_QUEUE_H
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>

#define SB_TRACE_ROWS 1024u
struct sb_trace_queue {
    _Atomic int occupied;
    _Atomic uint64_t head;
    uint64_t tail; /* consumer only */
    _Atomic bool exhausted;
    _Atomic uint64_t lost;
    _Atomic uint64_t published[SB_TRACE_ROWS];
    struct rate_row rows[SB_TRACE_ROWS];
};
#define SB_TRACE_QUEUE_INIT { 0 }

static bool sb_trace_push(struct sb_trace_queue *q,const struct rate_row *row)
{
    if(atomic_load_explicit(&q->exhausted,memory_order_acquire)) {
        atomic_fetch_add_explicit(&q->lost,1,memory_order_relaxed);return false;
    }
    int occupied=atomic_fetch_add_explicit(&q->occupied,1,memory_order_acquire);
    if(occupied>=(int)SB_TRACE_ROWS) {
        atomic_fetch_sub_explicit(&q->occupied,1,memory_order_relaxed);
        atomic_fetch_add_explicit(&q->lost,1,memory_order_relaxed);return false;
    }
    if(atomic_load_explicit(&q->exhausted,memory_order_acquire)) {
        atomic_fetch_sub_explicit(&q->occupied,1,memory_order_release);
        atomic_fetch_add_explicit(&q->lost,1,memory_order_relaxed);return false;
    }
    uint64_t ticket=atomic_fetch_add_explicit(&q->head,1,memory_order_relaxed);
    /* Reserve a whole ring before UINT64_MAX: at most ROWS ticket holders
     * passed the initial gate. They cannot wrap even if interrupted here. */
    if(ticket>=UINT64_MAX-SB_TRACE_ROWS) {
        atomic_store_explicit(&q->exhausted,true,memory_order_release);
        atomic_fetch_sub_explicit(&q->occupied,1,memory_order_release);
        atomic_fetch_add_explicit(&q->lost,1,memory_order_relaxed);return false;
    }
    unsigned slot=(unsigned)(ticket%SB_TRACE_ROWS);
    q->rows[slot]=*row;
    atomic_store_explicit(&q->published[slot],ticket+1,memory_order_release);
    return true;
}

static unsigned sb_trace_take(struct sb_trace_queue *q,struct rate_row *out,unsigned limit)
{
    unsigned count=0;
    while(count<limit) {
        unsigned slot=(unsigned)(q->tail%SB_TRACE_ROWS);
        if(atomic_load_explicit(&q->published[slot],memory_order_acquire)!=q->tail+1)break;
        out[count++]=q->rows[slot];
        atomic_store_explicit(&q->published[slot],0,memory_order_relaxed);
        ++q->tail;
        /* The payload copy and slot clear precede reuse of the credit. */
        atomic_fetch_sub_explicit(&q->occupied,1,memory_order_release);
    }
    return count;
}
#endif
