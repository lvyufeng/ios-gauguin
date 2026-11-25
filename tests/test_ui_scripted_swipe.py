#!/usr/bin/env python3
"""Run the actual unattended stroke callbacks with timer/HID/trace seams."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HARNESS=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <IOKit/SweetHIDTouchFrame.h>
#include "gauguin_ui_trace.h"
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define NSEC_PER_SEC 1000000000u
#define NSEC_PER_MSEC 1000000u
typedef void *thread_call_param_t;
typedef void (*callback_t)(void *,void *);
struct timer {callback_t fire;bool pending;uint64_t due;};
typedef struct timer *thread_call_t;
static struct timer timer;
static uint64_t now;
static unsigned sent,releases,markers,returns,fail_at,checks;
static bool fail_alloc;
static uint32_t display_state;
static unsigned key_count;
static bool key_held,wake_on_release;
static struct sweet_hid_touch_snapshot events[442];
static unsigned strokes[442],steps[442];
#define CHECK(v) do {++checks;assert(v);} while(0)
static uint64_t mach_absolute_time(void){return now;}
uint32_t sweet_fb_display_state(void){return display_state;}
void sweet_hid_key(int key,int down){
    assert(key==0&&key_count<2&&down==(key_count==0));
    key_held=down;++key_count;
    if(!down&&wake_on_release)display_state=1;
}
static void clock_interval_to_deadline(unsigned n,unsigned scale,uint64_t *out){*out=now+(uint64_t)n*scale;}
static thread_call_t thread_call_allocate(callback_t fire,void *p){assert(!p);timer.fire=fire;return fail_alloc?NULL:&timer;}
static bool thread_call_enter_delayed(thread_call_t t,uint64_t due){
    assert(t==&timer&&!t->pending&&due>now);t->pending=true;t->due=due;return false;
}
uint64_t sweet_ui_trace_report(uint64_t begin,uint64_t end,uint32_t status,uint32_t mask){
    assert(begin==now&&end==now&&!status&&mask<=1);return sent+1;
}
void sweet_ui_trace_record(uint32_t kind,uint64_t id,uint32_t pid,uint32_t flags,uint64_t a,uint64_t b,uint64_t c){
    assert(!pid);
    if(kind==GUT_SYNTHETIC){
        assert(id==sent+1&&markers==sent&&flags<13&&a<=33&&b<1080&&c<2400);
        strokes[sent]=flags;steps[sent]=a;++markers;
    }else {assert(kind==GUT_HID_RETURN&&id==sent&&a<=1&&!b&&!c);++returns;}
}
int sweet_hid_touch_frame_traced(const struct sweet_hid_touch_snapshot *s,uint64_t id){
    assert(sent<442&&id==sent+1&&markers==sent+1);events[sent++]=*s;
    return sent==fail_at?7:0;
}
int sweet_hid_touch_frame(const struct sweet_hid_touch_snapshot *s){assert(!s->active_mask);++releases;return 0;}
static int quiet(const char *fmt,...){(void)fmt;return 0;}
#define printf quiet
@METHODS@
#undef printf
static void reset(void){
    memset(&timer,0,sizeof(timer));sweet_script_call=NULL;sweet_script_stroke=sweet_script_step=0;
    sweet_script_due=sweet_script_end=sweet_script_start=0;
    now=1000;sent=releases=markers=returns=fail_at=0;fail_alloc=false;
    display_state=1;key_count=0;key_held=wake_on_release=false;
    sweet_script_wake_mode=false;sweet_script_wake_phase=sweet_script_wake_polls=0;
}
static void fire(void){assert(timer.pending);timer.pending=false;now=timer.due;timer.fire(NULL,NULL);}
int main(void){
    reset();sweet_script_fire(NULL,NULL);CHECK(!sent);
    fail_alloc=true;sweet_script_arm();CHECK(!timer.pending&&!sent);
    reset();sweet_script_arm();sweet_script_arm();CHECK(timer.due==1000+180ull*NSEC_PER_SEC);
    unsigned callbacks=0;while(timer.pending){CHECK(++callbacks<=442);fire();}
    CHECK(sent==442&&markers==442&&returns==442&&!releases&&sweet_script_stroke==13);
    CHECK(now<1000+220ull*NSEC_PER_SEC);
    for(unsigned i=0;i<442;i++){
        unsigned stroke=i/34,step=i%34,pos=step<33?step:32;
        CHECK(strokes[i]==stroke&&steps[i]==step&&events[i].active_mask==(step<33));
        CHECK(events[i].x[0]==(stroke?(stroke&1?900-(720*(int)pos)/32:180+(720*(int)pos)/32):540));
        CHECK(events[i].y[0]==(stroke?1200:2390-(1490*(int)pos)/32));
        for(unsigned finger=1;finger<10;finger++)CHECK(!events[i].x[finger]&&!events[i].y[finger]);
    }
    sweet_script_fire(NULL,NULL);sweet_script_arm();CHECK(sent==442&&!timer.pending);
    /* Every possible HID failure terminates the sequence and attempts release. */
    for(unsigned i=1;i<=442;i++){
        reset();fail_at=i;sweet_script_arm();while(timer.pending)fire();
        CHECK(sent==i&&releases==1&&sweet_script_stroke==13);
        sweet_script_fire(NULL,NULL);CHECK(sent==i&&releases==1);
    }
    for(unsigned i=0;i<34;i++){
        reset();sweet_script_arm();for(unsigned j=0;j<i;j++)fire();
        timer.pending=false;now=sweet_script_end;sweet_script_fire(NULL,NULL);
        CHECK(sent==i&&releases==1&&!timer.pending&&sweet_script_stroke==13);
    }
    reset();sweet_script_arm();fire();timer.pending=false;now=sweet_script_start-1;
    sweet_script_fire(NULL,NULL);CHECK(releases==1&&sent==1&&!timer.pending);

    /* Already-on display: settle and run without touching the power button. */
    reset();sweet_script_wake_mode=true;sweet_script_arm();fire();
    CHECK(!sent&&!key_count&&timer.pending);
    while(timer.pending)fire();CHECK(sent==442&&!key_count&&!releases);
    CHECK(sweet_script_wake_phase==SWEET_WAKE_READY);

    /* Off -> one inline press/release -> observed on -> settle -> workload. */
    reset();sweet_script_wake_mode=true;display_state=2;wake_on_release=true;
    sweet_script_arm();fire();CHECK(key_count==2&&!key_held&&!sent&&timer.pending);
    fire();CHECK(!sent&&sweet_script_wake_phase==SWEET_WAKE_SETTLE);
    while(timer.pending)fire();CHECK(sent==442&&key_count==2&&!key_held&&!releases);

    /* A button pair is not success: no display-on means bounded refusal. */
    reset();sweet_script_wake_mode=true;display_state=2;sweet_script_arm();
    callbacks=0;while(timer.pending){CHECK(++callbacks<=102);fire();}
    CHECK(!sent&&releases==1&&key_count==2&&!key_held);
    sweet_script_fire(NULL,NULL);CHECK(!sent&&key_count==2);

    reset();sweet_script_wake_mode=true;display_state=0;sweet_script_arm();fire();
    CHECK(!sent&&!key_count&&releases==1&&!timer.pending);

    /* Display loss during settle or a stroke stops input; no repeated wake. */
    reset();sweet_script_wake_mode=true;display_state=2;wake_on_release=true;
    sweet_script_arm();fire();fire();display_state=2;fire();
    CHECK(!sent&&releases==1&&key_count==2&&!timer.pending);
    reset();sweet_script_wake_mode=true;sweet_script_arm();fire();fire();
    CHECK(sent==1&&events[0].active_mask==1);display_state=2;fire();
    CHECK(sent==1&&releases==1&&!key_count&&!timer.pending);

    /* Late callback after the wake deadline cannot leave a held key. */
    reset();sweet_script_wake_mode=true;display_state=2;sweet_script_arm();fire();
    timer.pending=false;now=sweet_script_end;sweet_script_fire(NULL,NULL);
    CHECK(key_count==2&&!key_held&&!sent&&releases==1&&!timer.pending);

    /* Count bound also terminates if a host clock does not advance. */
    reset();sweet_script_wake_mode=true;display_state=2;sweet_script_arm();fire();
    for(unsigned i=0;i<100;i++){
        timer.pending=false;CHECK(!sweet_script_display_ready(now));
        if(sweet_script_stroke==13)break;
    }
    CHECK(sweet_script_stroke==13&&!sent&&!key_held&&key_count==2&&releases==1);
    printf("PASS %u actual scripted stroke/marker/failure/deadline/release checks; CPU seams only\n",checks);
}
'''

def main():
    source_root=Path(os.environ['XNU_SOURCE'])
    source=(source_root/'bsd/dev/sweet_touch.c').read_text()
    start=source.index('static thread_call_t sweet_script_call;')
    fragment=source[start:source.index('\n#endif',start)]
    assert 'physical == 0 && swipe == 2' in source
    with tempfile.TemporaryDirectory(prefix='ui-script-') as tmp:
        tmp=Path(tmp);unit=tmp/'host.c';unit.write_text(HARNESS.replace('@METHODS@',fragment))
        env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
        subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g',
                        '-fsanitize=address,undefined','-fno-omit-frame-pointer',
                        '-I'+str(source_root/'iokit'),'-I'+str(source_root/'bsd/dev'),
                        str(unit),'-o',str(tmp/'host')],env=env,check=True)
        subprocess.run([str(tmp/'host')],env=env,check=True,timeout=30)

if __name__=='__main__':main()
