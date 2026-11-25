#!/usr/bin/env python3
"""Run actual held-frame methods against deferred-frame and lifetime scenarios."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

WORK = Path(__file__).resolve().parents[1]
STATE = WORK / 'research/tmp/present-retry-332'
PARENT = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331')
REL = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
FIXTURE = WORK / 'tests/fixtures/present_retry_host.cpp'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def method(source, signature):
    start = source.index(signature)
    return source[start:source.index('\n}\n', start) + 3]


def unit(framebuffer, surface, retry):
    surface_methods = [method(surface, name) for name in (
        'static void\nsweet_surface_put(', 'SweetSurface *\nsweet_surface_copy(',
        'SweetSurface *\nsweet_surface_hold(', 'void\nsweet_surface_drop(')]
    start = framebuffer.index('struct sweet_fb_frame {')
    frame_type = framebuffer[start:framebuffer.index('\n};', start) + 4]
    names = ['static void\nsweet_fb_frame_release(', 'static void\nsweet_fb_frame_move(',
        'static bool\nsweet_fb_frame_prepare(', 'static SweetSurface *\nsweet_fb_present_surface(',
        'bool\nAppleCLCD::takeHeldFrameLocked(', 'void\nAppleCLCD::cancelHeldFrameLocked(',
        'void\nAppleCLCD::finishHeldFrame(', 'void\nAppleCLCD::removeClient(']
    if retry:
        names.append('void\nAppleCLCD::invalidateHeldRetryLocked(')
        timer = method(framebuffer, 'void\nAppleCLCD::vsyncFired(')
        assert 'bool ready = fb->present(rec, fb->fHoldPresent ? frame.surfaces : NULL);' in timer
        assert 'if (fb->fHoldPresent) fb->finishHeldFrame(&frame, !ready);' in timer
        assert 'if (off) fFB->invalidateHeldRetryLocked();' in framebuffer
    else:
        assert 'if (fb->fHoldPresent) fb->finishHeldFrame(&frame);' in framebuffer
    replacements = {'@SURFACE_METHODS@': '\n'.join(surface_methods), '@FRAME_TYPE@': frame_type,
        '@GET32@': method(framebuffer, 'static uint32_t\nget32('),
        '@FRAME_METHODS@': '\n'.join(method(framebuffer, name) for name in names),
        '@SWAP_METHOD@': method(framebuffer, 'bool\nAppleCLCD::swap(')}
    text = FIXTURE.read_text()
    for token, replacement in replacements.items():
        assert text.count(token) == 1
        text = text.replace(token, replacement)
    return '#define HAS_HELD 1\n#define HAS_RETRY ' + str(int(retry)) + '\n' + text


def main():
    manifest_path = PARENT / 'local-link/build-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    base = Path(manifest['source_union']['base'])
    before_path = base / REL
    after_path = STATE / 'kernel-source' / REL
    surface_path = base / 'iokit/Kernel/arm/SweetSurface.cpp'
    before, after = before_path.read_text(), after_path.read_text()
    # Pixel-copy implementation is identical apart from reporting guard failure.
    original_present = method(before, 'void\nAppleCLCD::present(')
    candidate_present = method(after, 'bool\nAppleCLCD::present(')
    normalized = candidate_present.replace('bool\nAppleCLCD::present(', 'void\nAppleCLCD::present(')
    normalized = normalized.replace('    bool ready = true;\n', '').replace('    return ready;\n', '')
    normalized = normalized.replace('if(!gpuRead.valid()){ready=false;s->release();continue;}',
                                    'if(!gpuRead.valid()){s->release();continue;}')
    normalized = normalized.replace('0,ready ? 0 : 1,mask,0,0);', '0,0,mask,0,0);')
    assert normalized == original_present
    pins = {str(p):sha(p) for p in (Path(__file__), FIXTURE, manifest_path, before_path, after_path, surface_path)}
    out = STATE / 'retry-host-v1'
    out.mkdir(exist_ok=False)
    steps = []
    env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
               UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    for variant, source, retry in (('baseline', before, False), ('candidate', after, True)):
        cpp = out / (variant + '.cpp')
        cpp.write_text(unit(source, surface_path.read_text(), retry))
        executable = out / variant
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
        if not retry:
            assert run.returncode == 42
            assert run.stderr == 'FAIL busy last frame retired instead of retained for next refresh\n'
        else:
            assert run.returncode == 0 and not run.stderr, (run.returncode, run.stderr)
            assert 'PASS pending retry: bound8' in run.stdout and 'PASS held presentation checks=' in run.stdout
    assert all(sha(p) == digest for p, digest in pins.items())
    result = dict(state='PRESENT332-actual-method-lifetime-and-retry-checks-passed',
        baseline_functional_failure_reproduced=True, original_lifetime_scenarios_passed=True,
        bounded_retries_and_epoch_cancellation_passed=True, concurrent_producer_consumer_passed=True,
        actual_present_copy_body_unchanged_except_guard_result=True, sanitizers=['address', 'undefined'],
        input_pins=pins, inputs_unchanged=True, steps=steps, device_commands=0, physical_FPS_qualified=False)
    with (out / 'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
