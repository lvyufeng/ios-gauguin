#ifdef GUT_BOARD_HOST_TEST
#include "test_ui_trace_board_shim.h"
#else
#include <pexpert/arm64/board_config.h>
#endif
#if defined(GAUGUIN)
#ifndef GUT_BOARD_HOST_TEST
#include <sys/param.h>
#include <sys/systm.h>
#include <pexpert/pexpert.h>
#include <kern/clock.h>
#include <kern/kalloc.h>
#include <mach/mach_time.h>
#include "../kern/sweet_eagl_diagnostics.h"
#endif
#include "gauguin_ui_trace.h"

static struct gut_core trace;
static mach_timebase_info_data_t timebase;
static bool header,footer;
static uint64_t now(void *unused)
{(void)unused;return mach_absolute_time();}
void sweet_ui_trace_init(void)
{
    uint32_t which=0;
    if(!PE_parse_boot_argn("sweettrace",&which,sizeof(which))||!which)return;
    if(which>16||!sweet_metal_desktop_enabled()) {
        printf("SWEET UI254: refused selector=%u; requires exact desktop profile\n",which);return;
    }
    uint64_t window;nanoseconds_to_absolutetime(UINT64_C(4)*NSEC_PER_SEC,&window);
    clock_timebase_info(&timebase);
    if(!window||!timebase.numer||!timebase.denom)return;
    struct gut_event *events=kalloc_data(4096*sizeof(*events),Z_WAITOK|Z_ZERO);
    if(!events){printf("SWEET UI254: allocation failed; disabled\n");return;}
    if(!gut_init(&trace,events,4096,which,window,now,NULL)) {
        kfree_data(events,4096*sizeof(*events));return;
    }
    printf("SWEET UI254: armed gesture=%u window=4s capacity=4096 CPU-clock; no panel or GPU hardware time\n",which);
}
uint64_t sweet_ui_trace_clock(void)
{return gut_enabled(&trace)?mach_absolute_time():0;}
uint64_t sweet_ui_trace_report(uint64_t begin,uint64_t end,uint32_t status,uint32_t mask)
{return gut_report(&trace,begin,end,status,mask);}
void sweet_ui_trace_record(uint32_t kind,uint64_t id,uint32_t pid,uint32_t flags,uint64_t a,uint64_t b,uint64_t c)
{gut_record(&trace,kind,id,pid,flags,a,b,c);}
void sweet_ui_trace_stop(uint32_t reason)
{gut_stop(&trace,reason);}
void sweet_ui_trace_drain(void)
{
    /* Called only by the existing single log worker. No UFS or console work
     * until the capture is immutable; at most 16 records per existing tick. */
    if(footer)return;
    struct gut_event batch[16];struct gut_meta m;uint32_t count;
    if(!gut_read(&trace,batch,16,&count,&m))return;
    if(!header) {
        header=true;
        printf("SWEET UI254 H: version=2 count=%u reason=%u lost=%llu start=%llu end=%llu numer=%u denom=%u which=%u gestures=%u\n",
            m.count,m.reason,(unsigned long long)m.lost,(unsigned long long)m.start,
            (unsigned long long)m.end,timebase.numer,timebase.denom,m.which,m.gestures);
    }
    for(uint32_t i=0;i<count;i++) {
        const struct gut_event *e=batch+i;
        printf("SWEET UI254 E: seq=%llu tick=%llu kind=%u id=%llu pid=%u flags=%u a=%llu b=%llu c=%llu\n",
            (unsigned long long)e->seq,(unsigned long long)e->tick,e->kind,(unsigned long long)e->id,e->pid,e->flags,
            (unsigned long long)e->a,(unsigned long long)e->b,(unsigned long long)e->c);
    }
    if(m.state==GUT_DRAINED) {
        footer=true;
        printf("SWEET UI254 F: count=%u lost=%llu; CPU-clock capture only\n",m.count,(unsigned long long)m.lost);
    }
}
#endif
