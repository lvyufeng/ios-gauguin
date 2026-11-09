#!/usr/bin/env python3
"""Compare the timed production guard body with202 and execute its wrapper."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
NAME = 'bsd/dev/gauguin_gmu_board.c'
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source203-codex')) / NAME
REFERENCE = Path(os.environ.get('XNU_REFERENCE', ROOT / '.deps-cache/p0-20261105/source202-codex')) / NAME
FIXTURE = ROOT / 'tests/fixtures/gpu-user/runtime_diagnostics_host.c'


def main():
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, REFERENCE, FIXTURE)}
    source, old = SOURCE.read_text(), REFERENCE.read_text()

    def extract(text, signature):
        start = text.index(signature)
        return text[start:text.index('\n}\n', start) + 3]

    helpers = source[source.index('struct ggrb_live_sample {'):source.index('bool sweet_gpu_runtime_requested(void)')]
    fixture = FIXTURE.read_text()
    for marker, value in (
            ('@HELPERS@', helpers),
            ('@LIVE@', extract(source, 'static bool ggrb_live_check(').replace('ggrb_live_check(', 'ggrb_live(', 1)),
            ('@BASELINE@', extract(old, 'static bool ggrb_live(').replace('ggrb_live(', 'baseline_live(', 1))):
        assert fixture.count(marker) == 1
        fixture = fixture.replace(marker, value)
    if 'sweet_gmu_clock_live_snapshot(' in source:
        # The separate clock-snapshot test executes actual clock/WDT sampling.
        # This fixture compares the top-level gate and identical value result.
        marker = 'static bool gfw_faults('
        fixture = fixture.replace(marker, 'static bool sweet_gmu_clock_live_snapshot(uint32_t *gx) { return sweet_gmu_clock_live(true,gx); }\n' + marker, 1)
    start = source.index('struct ggrb_perf_sample {')
    perf = source[start:source.index('static bool ggrb_micro_settle(', start)]
    wrapper = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
static uint64_t samples[2];
static unsigned reads,bodies;
static bool healthy;
static uint64_t mach_absolute_time(void){assert(reads<2);return samples[reads++];}
static bool ggrb_live_check(void *cookie){assert(cookie==(void *)(uintptr_t)7);++bodies;return healthy;}
@PERF@
@WRAPPER@
static void sample(uint64_t start,uint64_t end,bool ok){
    reads=0;samples[0]=start;samples[1]=end;healthy=ok;
    assert(ggrb_live((void *)(uintptr_t)7)==ok);assert(reads==2);
}
int main(void){
    sample(10,30,true);assert(bodies==1&&ggrb_perf.checks==1);
    assert(ggrb_perf.check_ticks==20&&ggrb_perf.max_check_ticks==20);
    sample(50,100,false);assert(bodies==2&&ggrb_perf.checks==2);
    assert(ggrb_perf.check_ticks==70&&ggrb_perf.max_check_ticks==50);
    sample(200,200,true);assert(bodies==3&&ggrb_perf.check_ticks==70);
    sample(300,299,false);assert(bodies==4&&ggrb_perf.check_ticks==70);
    assert(ggrb_perf.checks==4&&ggrb_perf.max_check_ticks==50);
    assert(!ggrb_perf.submits&&!ggrb_perf.pending);
    puts("Timed guard wrapper: actual source, true/false/same/backward clock results preserved");
}
'''.replace('@PERF@', perf).replace('@WRAPPER@', extract(source, 'static bool ggrb_live('))
    with tempfile.TemporaryDirectory(prefix='gpu-guard-perf-') as directory:
        directory = Path(directory)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        for name, body in [('guard', fixture), ('timer', wrapper)]:
            unit = directory / (name + '.c')
            unit.write_text(body)
            binary = directory / name
            subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-O1', '-g', '-fsanitize=address,undefined',
                            '-fno-omit-frame-pointer', str(unit), '-o', str(binary)],
                           env=env, check=True)
            subprocess.run([str(binary)], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
