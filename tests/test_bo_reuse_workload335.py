#!/usr/bin/env python3
"""Compare actual parent/candidate API observations and resource churn on one workload."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-335'
PARENT = WORK.parent / 'gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    qualified = BASE / 'cache-host-v3'
    assert json.loads((qualified / 'result.json').read_text())['state'] == 'BC335-actual-completed-owned-cache-host-passed'
    fixture = WORK / 'tests/fixtures/bo_reuse335_workload.inc'
    source = BASE / 'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp'
    old_source = PARENT / 'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp'
    strip = lambda p: re.sub(r'^#include .*\n', '', p.read_text(), flags=re.M).replace(
        '__asm__ volatile("dsb sy" ::: "memory")', '__atomic_thread_fence(__ATOMIC_SEQ_CST)')
    actual = strip(source).replace('class GauguinGPUUserClient : public IOUserClient {',
                                   'class GauguinGPUUserClient : public IOUserClient {\n    friend struct BC335Host;')
    before = (qualified / 'actual-cache.cpp').read_text().split('// The peer exposes observations')[0]
    assert before.count(actual) == 1
    pins = {str(p.resolve()): sha(p) for p in [Path(__file__), fixture, source, old_source,
                                             qualified / 'actual-cache.cpp', qualified / 'runtime.o', qualified / 'result.json']}
    out = BASE / 'workload-host-v2'
    out.mkdir()
    observations, counts, steps = {}, {}, []
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
    for name in ('baseline', 'candidate'):
        code = before if name == 'candidate' else before.replace(actual, strip(old_source))
        unit = out / (name + '.cpp')
        unit.write_text(code + fixture.read_text())
        binary = out / name
        compile_ = ['clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-DGAUGUIN_GPU_REQUEST_LOCKS=2', '-DGAUGUIN_GPU_PILOT_HOST=1',
                    '-I' + str(BASE / 'kernel-source/bsd/dev'), str(unit), str(qualified / 'runtime.o'), '-o', str(binary)]
        for label, argv in [('compile', compile_), ('run', [str(binary)])]:
            proc = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120)
            (out / (name + '-' + label + '.log')).write_text(proc.stdout + proc.stderr)
            steps.append(dict(variant=name, label=label, exit=proc.returncode))
            assert proc.returncode == 0, (name, label, proc.stderr)
            if label == 'run':
                observations[name] = [line for line in proc.stdout.splitlines() if line.startswith('OBS ')]
                rows = re.findall(r'^COUNTS backing=(\d+) sync=(\d+)$', proc.stdout, re.M)
                assert len(rows) == 1
                counts[name] = dict(zip(('backing', 'sync'), map(int, rows[0])))
    assert observations['baseline'] == observations['candidate'] and len(observations['baseline']) == 512
    assert counts == dict(baseline=dict(backing=512, sync=1024), candidate=dict(backing=6, sync=12)), counts
    assert all(sha(Path(p)) == digest for p, digest in pins.items())
    result = dict(state='BC335-actual-request-workload-observations-identical-churn-reduced',
                  requests=512, counts=counts, identical_handles_sizes_flags_and_zeroed_contents=True,
                  final_ownership_balanced=True, synthetic_host_workload_only=True,
                  performance_FPS_claimed=False, sanitizer='ASan+UBSan', steps=steps, input_pins=pins, device_commands=0)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
