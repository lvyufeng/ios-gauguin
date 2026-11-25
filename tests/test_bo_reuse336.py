#!/usr/bin/env python3
"""Compare actual 0335/0336 reclaim code under cold-to-hot working-set changes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess

WORK = Path(__file__).resolve().parents[1]
PARENT = WORK / 'research/tmp/bo-reuse-335'
BASE = WORK / 'research/tmp/bo-reuse-336'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    budget = json.loads((PARENT / 'storage-next-cache-policy-host.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes'] == 10000000
    patch = WORK / 'tools/bo_reuse336_patch.py'
    spec = importlib.util.spec_from_file_location('cache336', patch)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = PARENT / 'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp'
    original = source.read_text()
    changed = module.transform(original)
    assert changed != original and module.transform(changed, reverse=True) == original
    fixture = WORK / 'tests/fixtures/bo_reuse335_main.inc'
    modes = WORK / 'tests/fixtures/bo_reuse336_modes.inc'
    harness = (PARENT / 'cache-host-v3/actual-cache.cpp').read_text().split('// The peer exposes observations')[0]
    strip = lambda s: re.sub(r'^#include .*\n', '', s, flags=re.M).replace(
        '__asm__ volatile("dsb sy" ::: "memory")', '__atomic_thread_fence(__ATOMIC_SEQ_CST)').replace(
        'class GauguinGPUUserClient : public IOUserClient {',
        'class GauguinGPUUserClient : public IOUserClient {\n    friend struct BC335Host;')
    assert harness.count(strip(original)) == 1
    candidate = harness.replace(strip(original), strip(changed))
    main_ = fixture.read_text()
    assert main_.count('    if(mode=="basic"){') == 1
    main_ = main_.replace('    if(mode=="basic"){', modes.read_text() + '    if(mode=="basic"){')
    inputs = [Path(__file__), patch, fixture, modes, source, PARENT / 'cache-host-v3/actual-cache.cpp',
              PARENT / 'cache-host-v3/runtime.o', PARENT / 'cache-host-v3/result.json',
              PARENT / 'storage-next-cache-policy-host.json', PARENT / 'execution/results-review.json']
    pins = {str(p.resolve()): sha(p) for p in inputs}
    out = BASE / 'host-v1'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'candidate-GauguinGPU.cpp').write_text(changed)
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0', UBSAN_OPTIONS='halt_on_error=1')
    original_modes = ['basic', 'flags', 'aliases', 'pending', 'fault', 'caps', 'quota', 'pressure',
                      'oom', 'wrap', 'evict-fault', 'surface', 'concurrent']
    new_modes = ['policy-single', 'policy-wave', 'policy-alias', 'policy-fault', 'policy-bytes']
    steps, observations, metrics = [], {}, {}
    for variant, prefix in [('baseline', harness), ('candidate', candidate)]:
        unit = out / (variant + '.cpp')
        unit.write_text('#define BC336_POLICY ' + ('1' if variant == 'candidate' else '0') + '\n' + prefix + main_)
        binary = out / variant
        argv = ['clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-DGAUGUIN_GPU_REQUEST_LOCKS=2',
                '-DGAUGUIN_GPU_PILOT_HOST=1', '-I' + str(PARENT / 'kernel-source/bsd/dev'),
                str(unit), str(PARENT / 'cache-host-v3/runtime.o'), '-o', str(binary)]
        commands = [('compile', argv)] + [(name, [str(binary), name]) for name in original_modes + new_modes]
        for name, command in commands:
            result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=180)
            (out / (variant + '-' + name + '.log')).write_text(result.stdout + result.stderr)
            steps.append(dict(variant=variant, scenario=name, exit=result.returncode))
            assert result.returncode == 0, (variant, name, result.stderr)
            if name in ('policy-single', 'policy-wave'):
                observations[variant, name] = [s for s in result.stdout.splitlines() if s.startswith('OBS ')]
                matches = re.findall(r'^HOT backing=(\d+) sync=(\d+) hits=(\d+)$', result.stdout, re.M)
                assert len(matches) == 1
                metrics.setdefault(name, {})[variant] = dict(zip(('backing', 'sync', 'hits'), map(int, matches[0])))
    for name in ('policy-single', 'policy-wave'):
        assert observations['baseline', name] == observations['candidate', name]
        assert len(observations['baseline', name]) == 512
    assert all(sha(p) == digest for p, digest in pins.items())
    report = dict(state='BC336-actual-cache-replacement-and-working-set-host-passed',
                  original_scenarios=original_modes, new_scenarios=new_modes, steps=steps,
                  hot_request_counts=metrics, paired_hot_observations_identical=1024,
                  replacement_removals_per_return_max=1, original_byte_pressure_fallback_preserved=True,
                  aliases_pending_fault_zeroing_and_caps_preserved=True, sanitizer='ASan+UBSan',
                  device_commands=0, device_writes=0, boot_attempts=0, physical_FPS_qualified=False,
                  scope='Hot counts exclude the same 32-class seed and final teardown. Synthetic host working sets do not identify every real-phone miss or establish FPS improvement.',
                  input_pins=pins, inputs_unchanged=True)
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
