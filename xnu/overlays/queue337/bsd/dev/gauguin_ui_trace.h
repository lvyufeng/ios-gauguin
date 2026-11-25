/* Bounded CPU-clock UI evidence. No allocation, MMIO or wait in producers. */
#ifndef GAUGUIN_UI_TRACE_H
#define GAUGUIN_UI_TRACE_H
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

enum gut_state { GUT_OFF, GUT_ARMED, GUT_CAPTURE, GUT_FROZEN, GUT_DRAINED };
enum gut_reason { GUT_DEADLINE=1, GUT_CAPACITY, GUT_CLOCK, GUT_GPU_STOP };
enum gut_kind {
    GUT_REPORT=1, GUT_HID_BEGIN, GUT_HID_END, GUT_HID_RETURN,
    GUT_HID_ENQUEUE, GUT_HID_NO_QUEUE,
    GUT_API_BEGIN=10, GUT_API_END, GUT_SUBMIT_BEGIN, GUT_SUBMIT_END, GUT_SURFACE,
    GUT_SWAP=20, GUT_PRESENT_BEGIN, GUT_PRESENT_END, GUT_LAYER, GUT_READ_LOCK, GUT_READ_END,
    GUT_SYNTHETIC=30 /* explicit origin marker for a generated report ID */
};
struct gut_event {
    uint64_t seq, tick, id;
    uint32_t kind, pid, flags, reserved;
    uint64_t a,b,c;
};
struct gut_meta {
    uint64_t start,end,lost;
    uint32_t state,reason,count,cursor,which,gestures;
};
struct gut_core {
    uint32_t initialized,state,busy,stop;
    uint64_t gate; /* high bit closes admission; low bits count active writers */
    uint32_t reserved,close_reason,close_flags;
    uint64_t lost,lost_final,window,start,end;
    uint32_t count,cursor,capacity,which,gestures,mask,reason;
    struct gut_event *events;
    uint64_t (*clock)(void *);
    void *cookie;
};
#ifdef __cplusplus
static_assert(sizeof(gut_event)==64,"UI trace wire record");
extern "C" {
#else
_Static_assert(sizeof(struct gut_event)==64,"UI trace wire record");
#endif
bool gut_init(struct gut_core *,struct gut_event *,uint32_t,uint32_t,uint64_t,
              uint64_t (*)(void *),void *);
bool gut_enabled(const struct gut_core *);
uint64_t gut_report(struct gut_core *,uint64_t,uint64_t,uint32_t,uint32_t);
void gut_record(struct gut_core *,uint32_t,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t);
void gut_stop(struct gut_core *,uint32_t);
/* Single logger consumer. Copies a bounded immutable prefix; never waits.
 * False means busy or still armed/capturing; output and cursor unchanged. */
bool gut_read(struct gut_core *,struct gut_event *,uint32_t,uint32_t *,struct gut_meta *);

void sweet_ui_trace_init(void);
uint64_t sweet_ui_trace_clock(void);
uint64_t sweet_ui_trace_report(uint64_t,uint64_t,uint32_t,uint32_t);
void sweet_ui_trace_record(uint32_t,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t);
void sweet_ui_trace_stop(uint32_t);
void sweet_ui_trace_drain(void);
#ifdef __cplusplus
}
#endif
#endif
