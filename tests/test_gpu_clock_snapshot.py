#!/usr/bin/env python3
"""Execute real clock predicates, legacy traces and bounded runtime snapshots."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source205-codex'))
REFERENCE = Path(os.environ.get('XNU_REFERENCE', ROOT / '.deps-cache/p0-20261105/source204-codex'))
NAME = 'bsd/dev/gauguin_cx_power.c'


def extract(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end] + '\n'


HOST = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uintptr_t vm_offset_t;
enum {GCX_COMPLETE=2,GCR_COMPLETE=3,GBCMT_COMPLETE=4,GCX_STEP_TICKS=98295,NSEC_PER_MSEC=1000000};
static unsigned checks,reads,budgets,fail_budget,poison_read,mode,clock_state,cx_state,rail_state,bcm_state;
static bool context_ok,budget_live,parse_ok;
static uint64_t now,read_ns,deadline_delta,post_budget_ns;
static vm_offset_t gmc_pll,gmc_axi,gcx_gpucc,gcx_gcc;
static uint32_t values[14];
static struct {uintptr_t mapping;uint32_t off;} trace[14];
static char order[64];static unsigned order_count;
#define CHECK(x) do {++checks;assert(x);} while(0)
static void event(char c){assert(order_count<sizeof(order));order[order_count++]=c;}
static bool gcx_context(void){return context_ok;}
static unsigned sweet_gmu_clock_state(void){return clock_state;}
static unsigned sweet_cx_power_state(void){return cx_state;}
static unsigned sweet_cx_rail_state(void){return rail_state;}
static unsigned sweet_bcm_transport_state(void){return bcm_state;}
static bool gauguin_wdt_lease_check_budget(unsigned n){
    CHECK(n==GCX_STEP_TICKS);event('B');++budgets;
    if(budgets==2)now+=post_budget_ns;
    return budget_live&&budgets!=fail_budget;
}
static uint32_t gmc_read(vm_offset_t mapping,uint32_t off){
    assert(reads<14);event('R');trace[reads].mapping=mapping;trace[reads].off=off;
    now+=read_ns;++reads;if(reads==poison_read)budget_live=false;
    return values[reads-1];
}
static uint64_t mach_absolute_time(void){return now;}
static void clock_interval_to_deadline(unsigned n,unsigned scale,uint64_t *end){
    CHECK(n==5&&scale==NSEC_PER_MSEC);*end=now+deadline_delta;
}
static bool PE_parse_boot_argn(const char *key,void *out,unsigned bytes){
    CHECK(!strcmp(key,"sweetgpuzap")&&bytes==sizeof(int));
    if(parse_ok)*(int *)out=(int)mode;return parse_ok;
}
@FUNCTIONS@
static void setup(void){
    static const uint32_t good[]={0xc0100000,31,0x4000,1,1,0x80008000,0,0x602,0xff1,1,1,1,0,0xf8222800};
    memcpy(values,good,sizeof(values));reads=budgets=fail_budget=poison_read=order_count=0;
    memset(trace,0,sizeof(trace));memset(order,0,sizeof(order));
    mode=12;parse_ok=context_ok=budget_live=true;
    clock_state=cx_state=GCX_COMPLETE;rail_state=GCR_COMPLETE;bcm_state=GBCMT_COMPLETE;
    gmc_pll=0x10000;gmc_axi=0x20000;gcx_gpucc=0x30000;gcx_gcc=0x40000;
    now=1000;read_ns=100;deadline_delta=5000000;post_budget_ns=0;
}
static void change(unsigned reg,unsigned bit,bool allones){
    if(reg<14){if(allones)values[reg]=UINT32_MAX;else values[reg]^=1u<<bit;}
}
static void compare(unsigned reg,unsigned bit,bool allones,bool allow_gx){
    setup();change(reg,bit,allones);uint32_t expected=0x12345678;
    bool ok=baseline_live(allow_gx,&expected);unsigned old_reads=reads;
    unsigned old_budgets=budgets,old_count=order_count;
    char old_order[64];memcpy(old_order,order,sizeof(order));
    unsigned char old_trace[sizeof(trace)];memcpy(old_trace,trace,sizeof(trace));
    setup();change(reg,bit,allones);uint32_t actual=0x12345678;
    CHECK(sweet_gmu_clock_live(allow_gx,&actual)==ok);CHECK(actual==expected);
    CHECK(reads==old_reads&&budgets==old_budgets&&order_count==old_count);
    CHECK(!memcmp(trace,old_trace,sizeof(trace))&&!memcmp(order,old_order,sizeof(order)));
    if(!allow_gx)return;
    setup();change(reg,bit,allones);actual=0x12345678;
    CHECK(sweet_gmu_clock_live_snapshot(&actual)==ok);CHECK(actual==expected);
    CHECK(reads==old_reads);CHECK(!memcmp(trace,old_trace,sizeof(trace)));
    CHECK(budgets==2&&order[0]=='B'&&order[order_count-1]=='B');
    for(unsigned i=1;i+1<order_count;i++)CHECK(order[i]=='R');
    if(!ok)CHECK(actual==0x12345678);
}
static void invalid_context(unsigned which){
    switch(which){case 0:context_ok=false;break;case 1:clock_state=0;break;
    case 2:cx_state=0;break;case 3:rail_state=0;break;case 4:bcm_state=0;break;
    case 5:gmc_pll=0;break;case 6:gmc_axi=0;break;case 7:gcx_gpucc=0;break;case 8:gcx_gcc=0;break;}
}
int main(void){
    compare(14,0,false,true);compare(14,0,false,false);
    for(unsigned reg=0;reg<14;reg++){
        for(unsigned bit=0;bit<32;bit++){
            compare(reg,bit,false,true);compare(reg,bit,false,false);
        }
        compare(reg,0,true,true);compare(reg,0,true,false);
    }
    /* Original cold path retains every budget/read short circuit. */
    for(unsigned fail=1;fail<=28;fail++){
        setup();fail_budget=fail;uint32_t a=7;
        bool ok=baseline_live(true,&a);CHECK(!ok&&a==7);
        unsigned n=reads,b=budgets,c=order_count;char saved[64];memcpy(saved,order,sizeof(saved));
        setup();fail_budget=fail;a=7;
        CHECK(!sweet_gmu_clock_live(true,&a)&&a==7);
        CHECK(reads==n&&budgets==b&&order_count==c&&!memcmp(order,saved,sizeof(saved)));
    }
    for(unsigned fail=1;fail<=2;fail++){
        setup();fail_budget=fail;uint32_t out=7;
        CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);
        CHECK(budgets==fail&&reads==(fail==1?0:14));
    }
    for(unsigned poison=1;poison<=14;poison++){
        setup();poison_read=poison;uint32_t out=7;
        CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);
        CHECK(reads==14&&budgets==2); /* Post-sample rejects a lost lease. */
    }
    for(unsigned which=0;which<9;which++){
        setup();invalid_context(which);uint32_t out=7;
        CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);CHECK(!reads&&!budgets);
    }
    setup();CHECK(!sweet_gmu_clock_live_snapshot(NULL));CHECK(!reads&&!budgets);
    for(unsigned m=0;m<=13;m++)if(m!=12){
        setup();mode=m;uint32_t out=7;
        CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);CHECK(!reads&&!budgets);
    }
    setup();parse_ok=false;uint32_t out=7;
    CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);CHECK(!reads&&!budgets);
    setup();deadline_delta=0;out=7;
    CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);CHECK(!reads&&budgets==2);
    for(unsigned count=1;count<=14;count++){
        setup();deadline_delta=count*100;out=7;
        CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);CHECK(reads==count&&budgets==2);
    }
    setup();post_budget_ns=5000000;out=7;
    CHECK(!sweet_gmu_clock_live_snapshot(&out)&&out==7);CHECK(reads==14&&budgets==2);
    setup();CHECK(sweet_gmu_clock_live_snapshot(&out));CHECK(reads==14&&budgets==2&&out==0xf8222800);
    CHECK(trace[0].mapping==gmc_pll&&trace[0].off==0);
    CHECK(trace[13].mapping==gcx_gpucc&&trace[13].off==0x100c);
    printf("Clock snapshot: %u assertions; actual stable-value predicates, legacy traces,28->2 live budget samples, all-ones/epoch/deadline/mode rejection passed\n",checks);
}
'''


def main():
    inputs = [Path(__file__), SOURCE / NAME, REFERENCE / NAME]
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    source, reference = (SOURCE / NAME).read_text(), (REFERENCE / NAME).read_text()
    old_read = extract(reference, 'static bool gmq_read(').replace('gmq_read(', 'baseline_read(', 1)
    old_live = extract(reference, 'bool sweet_gmu_clock_live(').replace('sweet_gmu_clock_live(', 'baseline_live(', 1).replace('gmq_read(', 'baseline_read(')
    functions = old_read + old_live + ''.join(extract(source, n) for n in [
        'static bool gmq_read(', 'static bool gmq_live(',
        'bool sweet_gmu_clock_live(', 'bool sweet_gmu_clock_live_snapshot('])
    with tempfile.TemporaryDirectory(prefix='gpu-clock-snapshot-') as directory:
        directory = Path(directory)
        unit = directory / 'snapshot.c'
        unit.write_text(HOST.replace('@FUNCTIONS@', functions))
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(unit), '-o', str(directory / 'snapshot')],
                       env=env, check=True)
        subprocess.run([str(directory / 'snapshot')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
