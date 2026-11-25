#!/usr/bin/env python3
"""Run actual present and timer bodies over pixel, GPU-guard and clock seams."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
from test_present_retry import WORK, STATE, PARENT, REL, method

FIXTURE = WORK / 'tests/fixtures/present_retry_pixels_host.cpp'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    manifest_path = PARENT / 'local-link/build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    base = Path(manifest['source_union']['base'])
    before_path, after_path = base / REL, STATE / 'kernel-source' / REL
    header = base / 'iokit/Kernel/arm/SweetPresentStats.h'
    files = [Path(__file__), WORK / 'tests/test_present_retry.py', FIXTURE,
             manifest_path, before_path, after_path, header]
    pins = {str(p):sha(p) for p in files}
    out = STATE / 'pixels-host-v1'
    out.mkdir(exist_ok=False)
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    steps = []
    for variant, path, retry in (('baseline', before_path, False), ('candidate', after_path, True)):
        source = path.read_text()
        result_type = 'bool' if retry else 'void'
        text = FIXTURE.read_text()
        replacements = {
            '@PRESENT_RETURN@': result_type,
            '@RETRY_DECL@': ', bool retry=false' if retry else '',
            '@RETRY_DEF@': ', bool retry' if retry else '',
            '@STATS_HEADER@': header.read_text(),
            '@GET32@': method(source, 'static uint32_t\nget32('),
            '@PRESENT_METHOD@': method(source, result_type + '\nAppleCLCD::present('),
            '@VSYNC_METHOD@': method(source, 'void\nAppleCLCD::vsyncFired('),
        }
        for token, value in replacements.items():
            assert token in text, token
            text = text.replace(token, value)
        cpp, executable = out / (variant + '.cpp'), out / variant
        cpp.write_text('#define HAS_RETRY ' + str(int(retry)) + '\n' + text)
        argv = ['xcrun', 'clang++', '-std=c++17', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-Wno-unused-function', '-Wno-unused-variable', '-pedantic', '-fsanitize=address,undefined',
            '-fno-omit-frame-pointer', str(cpp), '-pthread', '-o', str(executable)]
        with (out / (variant + '-compile.log')).open('x') as stream:
            compiled = subprocess.run(argv, env=env, stdout=stream, stderr=subprocess.STDOUT)
        steps.append(dict(variant=variant, compiler_argv=argv, compile_exit=compiled.returncode))
        assert compiled.returncode == 0, variant + ' compile'
        run = subprocess.run([str(executable)], env=env, capture_output=True, text=True, timeout=30)
        (out / (variant + '-stdout.log')).write_text(run.stdout)
        (out / (variant + '-stderr.log')).write_text(run.stderr)
        steps[-1]['run_exit'] = run.returncode
        assert run.returncode == 0 and not run.stderr, (variant, run.returncode, run.stderr)
        assert 'PASS actual GPU-read result and timer handoff; retry=' + str(int(retry)) in run.stdout
        assert 'PASS present-stats integration checks=' in run.stdout
    assert all(sha(p) == digest for p, digest in pins.items())
    result = dict(state='PRESENT332-actual-present-timer-pixels-and-guard-result-passed',
        source_bodies_extracted=True, pixel_and_reference_checks_passed=True,
        partial_multilayer_refusal_deferred=True, ready_and_refused_timer_result_forwarded=True,
        real_frame_ownership_test='retry-host-v1/result.json',
        sanitizers=['address', 'undefined'], input_pins=pins, inputs_unchanged=True, steps=steps,
        device_commands=0, physical_FPS_qualified=False)
    with (out / 'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
