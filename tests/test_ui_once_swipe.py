#!/usr/bin/env python3
"""Execute production finite synthetic swipe callbacks with clock/timer seams."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
TREE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source219-codex'))
SOURCE = TREE / 'bsd/dev/sweet_touch.c'

HARNESS = r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define NSEC_PER_SEC 1000000000u
#define NSEC_PER_MSEC 1000000u
typedef void *thread_call_param_t;
typedef void (*callback_t)(thread_call_param_t,thread_call_param_t);
struct timer { callback_t fire; bool pending; uint64_t deadline; };
typedef struct timer *thread_call_t;
static struct timer timer;
static uint64_t now;
static unsigned allocations,arms,event_count,assertions;
static bool fail_allocate;
struct event { int finger,down,x,y; uint64_t time; };
static struct event events[40];
static void check(bool b){++assertions;assert(b);}
static uint64_t mach_absolute_time(void){return now;}
static void clock_interval_to_deadline(uint32_t n,uint32_t scale,uint64_t *out){
    check(scale==NSEC_PER_SEC||scale==NSEC_PER_MSEC);*out=now+(uint64_t)n*scale;
}
static thread_call_t thread_call_allocate(callback_t callback,void *param){
    check(param==NULL);++allocations;if(fail_allocate)return NULL;timer.fire=callback;return &timer;
}
static bool thread_call_enter_delayed(thread_call_t call,uint64_t deadline){
    check(call==&timer&&!timer.pending&&deadline>now);++arms;
    timer.pending=true;timer.deadline=deadline;return false;
}
static void sweet_hid_touch(int finger,int down,int x,int y){
    check(event_count<40);events[event_count++]=(struct event){finger,down,x,y,now};
}
static int quiet_printf(const char *fmt,...){(void)fmt;return 0;}
#define printf quiet_printf
@METHODS@
#undef printf

static void reset(void){
    memset(&timer,0,sizeof(timer));memset(events,0,sizeof(events));
    sweet_swipe_call=NULL;sweet_swipe_step=0;
    sweet_swipe_due=sweet_swipe_start=sweet_swipe_end=0;
    now=123456789;allocations=arms=event_count=0;fail_allocate=false;
}
static void fire(void){
    check(timer.pending&&timer.fire==sweet_swipe_fire);
    timer.pending=false;now=timer.deadline;timer.fire(NULL,NULL);
}
int main(void){
    reset();sweet_swipe_fire(NULL,NULL);check(!event_count&&!arms);
    fail_allocate=true;sweet_swipe_arm();check(allocations==1&&!arms&&!event_count);
    sweet_swipe_fire(NULL,NULL);check(!event_count);
    reset();uint64_t initial=now;sweet_swipe_arm();sweet_swipe_arm();
    check(allocations==1&&arms==1&&timer.deadline==initial+180ull*NSEC_PER_SEC);
    check(sweet_swipe_end==initial+182ull*NSEC_PER_SEC);
    unsigned callbacks=0;
    while(timer.pending){check(++callbacks<=34);fire();}
    check(callbacks==34&&arms==34&&event_count==34&&sweet_swipe_step==34);
    for(unsigned i=0;i<34;i++){
        check(events[i].finger==0&&events[i].x==540);
        check(events[i].time==initial+180ull*NSEC_PER_SEC+i*10ull*NSEC_PER_MSEC);
        check(events[i].down==(i<=32));
        check(events[i].y==(i<=32?2390-(1490*(int)i)/32:900));
        check(events[i].y>=0&&events[i].y<=2399);
        if(i&&i<=32)check(events[i].y<events[i-1].y);
    }
    sweet_swipe_fire(NULL,NULL);sweet_swipe_arm();check(!timer.pending&&event_count==34&&allocations==1);
    // Missing the initial bounded window emits no press or follow-up.
    reset();sweet_swipe_arm();timer.pending=false;now=sweet_swipe_end;
    sweet_swipe_fire(NULL,NULL);check(!event_count&&!timer.pending&&sweet_swipe_step==34);
    // Every delayed move ends a held contact once, without another timer.
    for(unsigned at=1;at<=33;at++){
        reset();sweet_swipe_arm();for(unsigned i=0;i<at;i++)fire();
        check(timer.pending&&event_count==at);
        timer.pending=false;now=sweet_swipe_end;sweet_swipe_fire(NULL,NULL);
        check(!timer.pending&&event_count==at+1&&events[at].down==0&&sweet_swipe_step==34);
        sweet_swipe_fire(NULL,NULL);check(event_count==at+1);
    }
    reset();sweet_swipe_arm();fire();timer.pending=false;now=sweet_swipe_start-1;
    sweet_swipe_fire(NULL,NULL);check(event_count==2&&events[1].down==0&&!timer.pending);
    reset();sweet_swipe_arm();timer.pending=false;now=sweet_swipe_due-1;
    sweet_swipe_fire(NULL,NULL);check(!event_count&&!timer.pending);
    printf("PASS %u production finite swipe, deadlines, release and allocation assertions\n",assertions);
}
'''


def main():
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__), SOURCE)}
    source = SOURCE.read_text()
    begin = source.index('static thread_call_t sweet_swipe_call;')
    end = source.index('\n#endif', begin)
    fragment = source[begin:end]
    assert 'sweet_hid_touch_frame' not in fragment
    assert 'IOSleep' not in fragment and 'ml_io_map' not in fragment
    unit = HARNESS.replace('@METHODS@', fragment)
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    with tempfile.TemporaryDirectory(prefix='gauguin-once-swipe-') as tmp:
        tmp = Path(tmp)
        (tmp / 'test.c').write_text(unit)
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                        str(tmp / 'test.c'), '-o', str(tmp / 'test')], env=env, check=True)
        subprocess.run([str(tmp / 'test')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
