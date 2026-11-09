#!/usr/bin/env python3
"""Execute the real bounded runtime wait and full SMMU guard, with IO seams."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
NAME = 'bsd/dev/gauguin_gmu_board.c'
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source201-codex')) / NAME
REFERENCE = Path(os.environ.get('XNU_REFERENCE', ROOT / '.deps-cache/p0-20261105/source200-codex')) / NAME
FIXTURE = ROOT / 'tests/fixtures/gpu-user/gfw_cached_reads_host.c'

RUNTIME = r'''
enum { GGR_READY=1,GGR_BUSY=2,GMB_READY=2,GMB_MIN=3 };
static unsigned ggrb_started,board_state=GMB_READY;
static struct { unsigned state;uint64_t operation_end_ns; } ggrb_context;
static uint64_t fake_ns,ggrb_end;
static unsigned delays,recover_after,expire_after;
static uint32_t recovery_word,recovery_gfsr,recovery_cr0;
static bool thread_ok=true,budget_ok=true;
static bool gmb_thread(void){return thread_ok;}
static unsigned sweet_gmu_board_state(void){return board_state;}
static bool gauguin_wdt_lease_check_budget(unsigned min){assert(min==GMB_MIN);return budget_ok;}
static uint64_t mach_absolute_time(void){return fake_ns;}
static uint64_t ggrb_ns(void *cookie){assert(!cookie);return fake_ns;}
static void IODelay(unsigned us){
    assert(us==10);fake_ns+=1000*us;++delays;
    if(delays==recover_after){
        memcpy(mmio+0x6000,&recovery_word,4);
        memcpy(mmio+0x48,&recovery_gfsr,4);
        if(recovery_cr0)memcpy(mmio,&recovery_cr0,4);
    }
    if(delays==expire_after)board_state=0;
}
'''

CASES = r'''
static void runtime_setup(void){
    setup(3,0,0,0);memset(&gfw_read_sample,0,sizeof(gfw_read_sample));
    memset(&gfw_micro_sample,0,sizeof(gfw_micro_sample));
    ggrb_started=1;ggrb_context.state=GGR_BUSY;
    fake_ns=1000;ggrb_context.operation_end_ns=fake_ns+2000000000;
    ggrb_end=UINT64_MAX;thread_ok=budget_ok=true;board_state=GMB_READY;
    delays=recover_after=expire_after=recovery_gfsr=recovery_cr0=0;
    recovery_word=0x2378;put32(0x6000,0x2270);
}
static void runtime_cases(void){
    runtime_setup();recover_after=3;
    CHECK(gfw_faults(false));CHECK(gfw_micro_sample.attempts==1);
    CHECK(gfw_micro_sample.recovered==1);CHECK(gfw_micro_sample.polls==3);
    CHECK(gfw_micro_sample.initial==0x2270);CHECK(gfw_micro_sample.current==0x2378);
    CHECK(gfw_micro_sample.expected==0x2378);CHECK(gfw_micro_sample.elapsed_us==30);
    CHECK(trace[0].offset==0x48&&trace[1].offset==0&&trace[2].offset==0x6000);
    CHECK(trace[6].offset==0x48&&trace[7].offset==0&&trace[8].offset==0x6000);
    CHECK(calls>30); /* Full bank/TTBR/GMU checks after recovery. */

    runtime_setup();CHECK(!gfw_faults(false));
    CHECK(gfw_micro_sample.attempts==1&&gfw_micro_sample.recovered==0);
    CHECK(gfw_micro_sample.elapsed_us==20000&&delays==2000);
    CHECK(calls==2002&&gfw_micro_sample.polls==1999);
    CHECK(gfw_micro_sample.current==0x2270); /* Never accepted by timeout. */

    for(unsigned route=0;route<7;++route){
        runtime_setup();
        switch(route){
        case 0:ggrb_started=0;break;
        case 1:ggrb_context.state=GGR_READY;break;
        case 2:thread_ok=false;break;
        case 3:board_state=0;break;
        case 4:break; /* gpu_probe must never gain this runtime wait. */
        case 5:put32(0x6000,UINT32_MAX);break;
        case 6:gmb_work.smmu.micro_after=0x3378;break;
        }
        CHECK(!gfw_faults(route==4));CHECK(!delays&&calls==3);
        CHECK(!gfw_micro_sample.attempts);
    }
    for(unsigned bit=0;bit<32;++bit){
        if(bit==3||bit==8)continue;
        runtime_setup();put32(0x6000,0x2270u^(1u<<bit));
        CHECK(!gfw_faults(false));CHECK(!delays&&calls==3);
        CHECK(!gfw_micro_sample.attempts);
    }
    for(unsigned word=0;word<3;++word){
        runtime_setup();recover_after=1;
        recovery_word=word==0?0x237c:(word==1?UINT32_MAX:0x3378);
        CHECK(!gfw_faults(false));CHECK(delays==1&&calls==4);
        CHECK(!gfw_micro_sample.recovered);
    }
    runtime_setup();fail_at=4;CHECK(!gfw_faults(false));
    CHECK(calls==4&&gfw_read_sample.ok==0&&!gfw_micro_sample.recovered);

    runtime_setup();recover_after=1;recovery_gfsr=1;
    CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.recovered==1);
    CHECK(calls==5&&trace[4].offset==0x48); /* Recheck faults, no stale pass. */
    runtime_setup();recover_after=1;recovery_cr0=0xdead;
    CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.recovered==1);
    CHECK(calls==6&&trace[5].offset==0); /* Recheck controls too. */
    runtime_setup();recover_after=1;put32(0x8058,2);
    CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.recovered==1);
    CHECK(trace[calls-1].offset==0x8058);

    runtime_setup();recover_after=1;mutate_at=7;mutation=0x100;
    CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.attempts==1);
    CHECK(calls==7&&delays==1); /* A second mismatch does not renew the wait. */
    runtime_setup();ggrb_context.operation_end_ns=fake_ns+25000;
    CHECK(!gfw_faults(false));CHECK(calls==5&&delays==3);
    CHECK(gfw_micro_sample.elapsed_us==30); /* No read at/after deadline. */
    runtime_setup();ggrb_end=fake_ns+15000;
    CHECK(!gfw_faults(false));CHECK(calls==4&&delays==2);
    runtime_setup();budget_ok=false;
    CHECK(!gfw_faults(false));CHECK(calls==3&&!delays);
    runtime_setup();fake_ns=UINT64_MAX-1000;
    CHECK(!gfw_faults(false));CHECK(calls==3&&!delays);
    CHECK(!gfw_micro_sample.attempts);
    runtime_setup();expire_after=1;
    CHECK(!gfw_faults(false));CHECK(calls==3&&delays==1);
}
'''


def main():
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, REFERENCE, FIXTURE)}
    source, old = SOURCE.read_text(), REFERENCE.read_text()

    def extract(text, signature):
        start = text.index(signature)
        return text[start:text.index('\n}\n', start) + 3]

    fixture = FIXTURE.read_text().replace('trace[64]', 'trace[4096]').replace('calls<64', 'calls<4096')
    helpers = source[source.index('struct gfw_read_sample {'):source.index('static bool gfw_faults(')]
    fixture = fixture.replace('@HELPERS@', RUNTIME + helpers + extract(source, 'static bool ggrb_micro_settle(bool gpu_probe,uint32_t expected,uint32_t mask,uint32_t current)\n{'))
    fixture = fixture.replace('@BASELINE@', extract(old, 'static bool gfw_faults(').replace('gfw_faults(', 'baseline_faults(', 1))
    fixture = fixture.replace('@CURRENT@', extract(source, 'static bool gfw_faults('))
    fixture = fixture.replace('int main(void) {', CASES + '\nint main(void) {')
    fixture = fixture.replace('    printf("GFW cache:', '    runtime_cases();\n    printf("Exact micro settle + GFW cache:')
    with tempfile.TemporaryDirectory(prefix='gpu-micro-settle-') as directory:
        directory = Path(directory)
        unit = directory / 'test.c'
        unit.write_text(fixture)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(unit), '-o', str(directory / 'test')],
                       env=env, check=True)
        subprocess.run([str(directory / 'test')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
