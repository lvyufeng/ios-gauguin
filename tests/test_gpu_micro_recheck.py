#!/usr/bin/env python3
"""Reproduce205's recheck rejection and execute a single shared wait budget."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

import test_gpu_micro_settle as original

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source206-codex'))
REFERENCE = Path(os.environ.get('XNU_REFERENCE', ROOT / '.deps-cache/p0-20261105/source205-codex'))
BASELINE = ROOT / '.deps-cache/p0-20261105/source200-codex'
NAME = 'bsd/dev/gauguin_gmu_board.c'


def extract(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start) + 3]


TRANSFORM = r'''
/* Ordered read inputs model a racing observed control word, not GPU execution. */
static unsigned runtime_flip,runtime_micro_reads,runtime_flip_limit;
static uint64_t fake_ns,runtime_io_ns;
static uint32_t runtime_micro_value(uint32_t value){
    if(!runtime_flip)return value;
    ++runtime_micro_reads;
    if((!runtime_flip_limit||runtime_micro_reads<=runtime_flip_limit)&&(runtime_micro_reads&1))
        return 0x2270;
    return 0x2370;
}
'''

CASES = r'''
static void repeated_cases(void){
    /* Actual205 helper/body reproduce its recovered2370/cache2270 signature. */
    runtime_setup();recover_after=1;recovery_word=0x2370;mutate_at=7;mutation=0x100;
    CHECK(!legacy_faults(false));CHECK(delays==1&&calls==7);
    CHECK(gfw_micro_sample.attempts==1&&gfw_micro_sample.recovered==1);
    CHECK(gfw_micro_sample.current==0x2370&&gfw_read_sample.offset==0x6000&&gfw_read_sample.value==0x2270);
    runtime_setup();recover_after=1;recovery_word=0x2370;mutate_at=7;mutation=0x100;
    CHECK(gfw_faults(false));CHECK(delays==2&&calls==39);
    CHECK(gfw_micro_sample.attempts==2&&gfw_micro_sample.recovered==2);
    CHECK(gfw_micro_sample.rechecks==1&&!gfw_micro_sample.expired);
    CHECK(gfw_micro_sample.elapsed_us==20&&gfw_read_sample.offset==0x2c14);

    runtime_setup();runtime_flip=1;
    CHECK(!gfw_faults(false));CHECK(delays==2000&&fake_ns==20001000);
    CHECK(gfw_micro_sample.attempts==2000&&gfw_micro_sample.recovered==1999);
    CHECK(gfw_micro_sample.polls==1999&&gfw_micro_sample.rechecks==1999);
    CHECK(gfw_micro_sample.expired==1&&gfw_micro_sample.elapsed_us==20000);
    CHECK(calls==7999); /* Repeated success never starts a fresh20ms budget. */

    runtime_setup();runtime_flip=1;ggrb_context.operation_end_ns=fake_ns+25000;
    CHECK(!gfw_faults(false));CHECK(delays==3&&calls==11);
    CHECK(gfw_micro_sample.recovered==2&&gfw_micro_sample.expired==1);
    runtime_setup();runtime_flip=1;ggrb_end=fake_ns+15000;
    CHECK(!gfw_faults(false));CHECK(delays==2&&calls==7);
    CHECK(gfw_micro_sample.recovered==1&&gfw_micro_sample.expired==1);
    runtime_setup();runtime_flip=1;expire_after=2;
    CHECK(!gfw_faults(false));CHECK(delays==2&&calls==7);
    CHECK(gfw_micro_sample.recovered==1&&!gfw_micro_sample.expired);

    /* Two recoveries must still re-read every original fault/control/TTBR. */
    runtime_setup();runtime_flip=1;runtime_flip_limit=3;
    CHECK(gfw_faults(false));CHECK(delays==2&&calls==39);
    unsigned full_count=calls-8,ttbr_index=0;
    for(unsigned i=8;i<calls;i++)if(trace[i].kind==2&&trace[i].offset==0x8020)ttbr_index=i+1;
    CHECK(ttbr_index>8);
    for(unsigned i=1;i<=full_count;i++){
        runtime_setup();runtime_flip=1;runtime_flip_limit=3;fail_at=8+i;
        CHECK(!gfw_faults(false));CHECK(calls==8+i);
        CHECK(gfw_micro_sample.recovered==2);
    }
    for(unsigned which=0;which<3;which++){
        runtime_setup();runtime_flip=1;runtime_flip_limit=3;
        mutate_at=which==0?9:(which==1?10:ttbr_index);mutation=1;
        CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.recovered==2);
    }
    runtime_setup();recover_after=1;runtime_io_ns=1000000;
    CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.recovered==1);
    CHECK(gfw_micro_sample.expired==1); /* A late full recheck cannot pass. */

    /* Each new guard gets its own budget; no state leaks from a failed one. */
    runtime_setup();recover_after=1;
    CHECK(gfw_faults(false));CHECK(delays==1&&gfw_micro_sample.recovered==1);
    CHECK(!gfw_micro_sample.rechecks&&!gfw_micro_sample.expired);
    puts("Shared MICRO budget: actual205 failure reproduced; repeated exact recovery,2000 total delays,20ms/op/service deadlines,authority/fault/TTBR rejection passed");
}
'''


def main():
    fixture_path = ROOT / 'tests/fixtures/gpu-user/gfw_cached_reads_host.c'
    inputs = [Path(__file__), Path(original.__file__), fixture_path,
              SOURCE / NAME, REFERENCE / NAME, BASELINE / NAME]
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    source, legacy, baseline = ((p / NAME).read_text() for p in [SOURCE, REFERENCE, BASELINE])
    fixture = fixture_path.read_text().replace('trace[64]', 'trace[8192]').replace('calls<64', 'calls<8192')
    fixture = fixture.replace('static uint64_t record(', TRANSFORM + '\nstatic uint64_t record(', 1)
    fixture = fixture.replace('if(calls==mutate_at)value^=mutation;',
                              'fake_ns+=runtime_io_ns;\n    if(calls==mutate_at)value^=mutation;\n    if(kind==1&&off==0x6000)value=runtime_micro_value((uint32_t)value);', 1)
    runtime = original.RUNTIME.replace('static uint64_t fake_ns,ggrb_end;', 'static uint64_t ggrb_end;')
    helpers = source[source.index('struct gfw_read_sample {'):source.index('static bool gfw_faults(')]
    wait = extract(source, 'static bool ggrb_micro_settle(bool gpu_probe,uint32_t expected,uint32_t mask,uint32_t current,struct gfw_micro_wait *wait)\n{')
    old_wait = extract(legacy, 'static bool ggrb_micro_settle(bool gpu_probe,uint32_t expected,uint32_t mask,uint32_t current)\n{').replace('ggrb_micro_settle(', 'legacy_settle(', 1)
    old_faults = extract(legacy, 'static bool gfw_faults(').replace('gfw_faults(', 'legacy_faults(', 1).replace('ggrb_micro_settle(', 'legacy_settle(')
    fixture = fixture.replace('@HELPERS@', runtime + helpers + wait + old_wait + old_faults)
    fixture = fixture.replace('@BASELINE@', extract(baseline, 'static bool gfw_faults(').replace('gfw_faults(', 'baseline_faults(', 1))
    fixture = fixture.replace('@CURRENT@', extract(source, 'static bool gfw_faults('))
    cases = original.CASES.replace('    setup(3,0,0,0);',
        '    runtime_flip=runtime_micro_reads=runtime_flip_limit=0;runtime_io_ns=0;\n    setup(3,0,0,0);', 1)
    old_case = '''    CHECK(!gfw_faults(false));CHECK(gfw_micro_sample.attempts==1);
    CHECK(calls==7&&delays==1); /* A second mismatch does not renew the wait. */'''
    new_case = '''    CHECK(gfw_faults(false));CHECK(gfw_micro_sample.attempts==2);
    CHECK(calls==39&&delays==2);CHECK(gfw_micro_sample.rechecks==1);'''
    assert old_case in cases
    cases = cases.replace(old_case, new_case, 1)
    fixture = fixture.replace('int main(void) {', cases + CASES + '\nint main(void) {', 1)
    fixture = fixture.replace('    printf("GFW cache:',
                              '    runtime_cases();repeated_cases();\n    printf("Shared-budget MICRO + GFW cache:', 1)
    with tempfile.TemporaryDirectory(prefix='gpu-micro-recheck-') as directory:
        directory = Path(directory)
        unit = directory / 'recheck.c'
        unit.write_text(fixture)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(unit), '-o', str(directory / 'recheck')],
                       env=env, check=True)
        subprocess.run([str(directory / 'recheck')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
