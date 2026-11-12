#!/usr/bin/env python3
"""Strict 0298 bootstrap lifecycle tests; synthetic logs are not GPU results."""
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from metal_bootstrap_log import qualify_bootstrap_log
from metal_probe_log import PHASES, PREFIX, qualify_probe_log

BUILD = '9b9f99e2627808207562eee0'
CORE = '8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1'
SEED = 1312282496
# Independent C++ CPU-oracle vector for SEED, computed through
# userland/metal/probe_pixels.hpp with the emission pattern of
# tests/fixtures/metal_probe_log_hashes.cpp.
HASHES = {
    'clear-A': '6927fac75e74a325',
    'clear-B': '0d65b7532d396325',
    'compute': '2b3f09731d071293',
    'triangle': '1d13029ee3799225',
    'texture-A': 'fc8967d8bfa70325',
    'texture-B': 'a5469e63bfa70325',
    'additive': '14a0420cba6ba325',
    'premultiplied-half': '3aa68aabc28c2325',
}
MEM_START = 'GAUGUIN METAL223 memory phase=bootstrap-start active_mb=128 inactive_mb=128 active_attr=1 inactive_attr=1 footprint=819480'
MEM_COMPILED = 'GAUGUIN METAL223 memory phase=compiled active_mb=128 inactive_mb=128 active_attr=1 inactive_attr=1 footprint=1212736'
MEM_COMPLETED = 'GAUGUIN METAL223 memory phase=completed active_mb=128 inactive_mb=128 active_attr=1 inactive_attr=1 footprint=1769792'
IDENTITY = f'{PREFIX}identity gpu=619 chip=06010900 gmem=524288 base=100000 seed={SEED}'
BEGIN245 = f'GAUGUIN METAL245 begin build={BUILD} startup_budget=180 work_deadline=30'
STARTUP279 = 'GAUGUIN METAL279 startup-open reason=0 attempts=271 elapsed_ns=44460868178 connected=1'
ARMED245 = 'GAUGUIN METAL245 armed epoch=1 jobs=8 fence=8 ready=0'
RESULT245 = f'GAUGUIN METAL245 RESULT PASS build={BUILD} seed={SEED} arm=1 teardown-requested=1 stages=8 ready=kernel-close-required'
RESULT223 = f'{PREFIX}RESULT PASS build={BUILD} seed={SEED} connection-teardown-requested=1 stages=8'
NATIVE_ARMED = 'SWEET METAL245: root armed jobs=8 fence=8 epoch=1 ready=0'
NATIVE_CLOSE = 'SWEET METAL245: root close ready=1 jobs=8 fence=8 epoch=1 clean=1'
NATIVE_PROXY = 'SWEET GPU AUTH: recorded launchd compositor proxy pid=57'
NATIVE_OPEN = 'SWEET GPU AUTH: compositor opened pid=57 root_fence=8'

checks = 0


def check(ok):
    global checks
    checks += 1
    assert ok


def make_stdout(*, memory='bootstrap-start', lifecycle=True):
    rows = [f'{PREFIX}begin build={BUILD} core={CORE} scope=offscreen-core-not-MTLDevice',
            MEM_START.replace('bootstrap-start', memory)]
    if lifecycle:
        rows.extend([BEGIN245, STARTUP279])
    rows.extend([IDENTITY, MEM_COMPILED])
    for i, phase in enumerate(PHASES):
        rows.extend([
            f'{PREFIX}submit phase={phase}',
            f'{PREFIX}completed phase={phase} gpu_ns=1000000 fences={i+1}',
            f'{PREFIX}pixels phase={phase} compared={256 if phase == "compute" else 4096} '
            f'hash={HASHES[phase]} PASS',
        ])
    rows.extend(f'{PREFIX}fence queue=1 value={i} complete=1' for i in range(1, 9))
    rows.append(MEM_COMPLETED)
    if lifecycle:
        rows.extend([ARMED245, RESULT245])
    rows.append(RESULT223)
    return '\n'.join(rows) + '\n'


def make_native():
    rows = [NATIVE_PROXY]
    rows.extend(f'SWEET GPU USER: submit rc=0 ibs=1 submitted={i} completed={i} '
                f'shadow={20+12*i} polls={i}' for i in range(1, 9))
    rows.extend([NATIVE_ARMED, NATIVE_CLOSE, NATIVE_OPEN])
    return '\n'.join(rows) + '\n'


def _rows(text):
    return text.splitlines()


def _join(rows):
    return '\n'.join(rows) + '\n'


def _find(rows, needle):
    hits = [i for i, line in enumerate(rows) if needle in line]
    check(len(hits) == 1)
    return hits[0]


def _drop(rows, needle):
    del rows[_find(rows, needle)]


def _replace(text, old, new):
    check(text.count(old) == 1)
    return text.replace(old, new)


def reject(stdout=None, stderr='', native=None, **kwargs):
    if stdout is None:
        stdout = make_stdout()
    if native is None:
        native = make_native()
    try:
        qualify_bootstrap_log(stdout, stderr, native,
                              build=kwargs.get('build', BUILD),
                              core=kwargs.get('core', CORE))
    except ValueError:
        check(True)
        return
    raise AssertionError('invalid bootstrap receipt accepted')


def reject_legacy(stdout, native):
    try:
        qualify_probe_log(stdout, '', native, build=BUILD, core=CORE)
    except ValueError:
        check(True)
        return
    raise AssertionError('legacy probe parser accepted bootstrap lifecycle')


def accept():
    result = qualify_bootstrap_log(make_stdout(), '', make_native(),
                                   build=BUILD, core=CORE)
    check(result['state'] == 'qualified298-bootstrap-offscreen-readback-and-native-owner-handoff')
    check(result['memory_profile'] == 'bootstrap-start')
    check(result['build'] == BUILD and result['core'] == CORE and result['seed'] == SEED)
    check(result['output_words'] == 28928 and result['completed_root_fences'] == 8)
    check(result['compositor_opens'] == 1 and result['hashes'] == HASHES)
    check(result['startup'] == {
        'reason': 0, 'attempts': 271, 'elapsed_ns': 44460868178,
        'budget_ns': 180000000000, 'connected': 1,
        'clock': 'userspace-bootstrap-recorded-interval-not-total-boot-wall-time'})
    check(result['arming'] == {'epoch': 1, 'jobs': 8, 'fence': 8, 'ready': 0})
    check(result['native_root'] == {'armed': True, 'close_clean': True})
    for key in ('MTLDevice_qualified', 'desktop_qualified', 'FPS_qualified',
                'high_refresh_qualified', 'daily_use_qualified'):
        check(result[key] is False)
    return result


def synthetic_checks():
    accept()
    valid = make_stdout()
    native = make_native()

    # Legacy keeps its before-delay lifecycle; the new entry is a strict,
    # separate current-lifecycle requirement in both directions.
    legacy = make_stdout(memory='before-delay', lifecycle=False)
    legacy_result = qualify_probe_log(legacy, '', native, build=BUILD, core=CORE)
    check(legacy_result['output_words'] == 28928)
    reject_legacy(valid, native)
    reject(legacy)

    rows = _rows(valid)
    _drop(rows, BEGIN245)
    reject(_join(rows))
    reject(valid + BEGIN245 + '\n')
    rows = _rows(valid)
    _drop(rows, STARTUP279)
    reject(_join(rows))
    reject(valid + STARTUP279 + '\n')
    rows = _rows(valid)
    _drop(rows, ARMED245)
    reject(_join(rows))
    reject(valid + ARMED245 + '\n')
    rows = _rows(valid)
    _drop(rows, RESULT245)
    reject(_join(rows))
    reject(valid + RESULT245 + '\n')

    # Missing, duplicated, malformed and unknown lifecycle lines.
    reject(valid + 'GAUGUIN METAL245 truncated lifecycle\n')
    reject(valid + 'GAUGUIN METAL245 unknown lifecycle record\n')
    reject(valid + 'GAUGUIN METAL279 unknown startup record\n')
    reject(_replace(valid, BEGIN245, BEGIN245.replace(' startup_budget=180', '')))
    reject(_replace(valid, BEGIN245, BEGIN245 + ' extra=1'))
    reject(_replace(valid, STARTUP279, STARTUP279 + ' extra=1'))
    reject(_replace(valid, ARMED245, ARMED245 + ' extra=1'))
    reject(_replace(valid, RESULT245, RESULT245 + ' extra=1'))
    reject(_replace(valid, STARTUP279, STARTUP279.replace('startup-open', 'startup')))
    reject(valid, stderr=STARTUP279 + '\n')

    # Startup-prefix ordering and values.
    rows = _rows(valid)
    startup = rows.pop(_find(rows, STARTUP279))
    rows.insert(_find(rows, IDENTITY) + 1, startup)
    reject(_join(rows))
    rows = _rows(valid)
    begin = rows.pop(_find(rows, BEGIN245))
    rows.insert(_find(rows, STARTUP279) + 1, begin)
    reject(_join(rows))
    reject(_replace(valid, STARTUP279, STARTUP279.replace('reason=0', 'reason=1')))
    reject(_replace(valid, STARTUP279, STARTUP279.replace('connected=1', 'connected=0')))
    reject(_replace(valid, STARTUP279, STARTUP279.replace('attempts=271', 'attempts=0')))
    reject(_replace(valid, STARTUP279, STARTUP279.replace(
        'elapsed_ns=44460868178', 'elapsed_ns=180000000001')))
    reject(_replace(valid, STARTUP279, STARTUP279.replace(
        'elapsed_ns=44460868178', 'elapsed_ns=0')))
    reject(_replace(valid, BEGIN245, BEGIN245.replace('startup_budget=180', 'startup_budget=181')))
    reject(_replace(valid, BEGIN245, BEGIN245.replace('work_deadline=30', 'work_deadline=31')))

    # Arming and result identity, counters and ordering.
    for old, new in [('epoch=1', 'epoch=2'), ('jobs=8', 'jobs=7'),
                     ('fence=8', 'fence=7'), ('ready=0', 'ready=1')]:
        reject(_replace(valid, ARMED245, ARMED245.replace(old, new)))
    for old, new in [('arm=1', 'arm=0'), ('teardown-requested=1', 'teardown-requested=0'),
                     ('stages=8', 'stages=7'),
                     ('ready=kernel-close-required', 'ready=kernel-close-pending')]:
        reject(_replace(valid, RESULT245, RESULT245.replace(old, new)))
    reject(_replace(valid, RESULT245, RESULT245.replace(
        f'build={BUILD}', 'build=' + 'f' * 24)))
    reject(_replace(valid, RESULT245, RESULT245.replace(
        f'seed={SEED}', f'seed={SEED + 1}')))
    rows = _rows(valid)
    armed = rows.pop(_find(rows, ARMED245))
    rows.insert(_find(rows, MEM_COMPLETED), armed)
    reject(_join(rows))
    rows = _rows(valid)
    result = rows.pop(_find(rows, RESULT245))
    rows.append(result)
    reject(_join(rows))
    reject(_replace(valid, BEGIN245, BEGIN245.replace(
        f'build={BUILD}', 'build=' + 'e' * 24)))
    reject(valid, build='f' * 24)
    reject(valid, core='b' * 64)

    # Probe memory policy and pixel oracle stay strict for bootstrap-start.
    reject(_replace(valid, MEM_START, MEM_START.replace('active_mb=128', 'active_mb=6')))
    reject(_replace(valid, MEM_START, MEM_START.replace('inactive_mb=128', 'inactive_mb=6')))
    reject(_replace(valid, MEM_START, MEM_START.replace('active_attr=1', 'active_attr=0')))
    reject(_replace(valid, MEM_COMPLETED, MEM_COMPLETED.replace(
        'footprint=1769792', 'footprint=134217729')))
    reject(_replace(valid, HASHES['triangle'], '0' * 16))

    # Native first-eight completion and the METAL245/owner handoff lifecycle.
    reject(native='')
    reject(native=native.replace('submitted=8 completed=8', 'submitted=8 completed=7'))
    reject(native=native.replace('rc=0', 'rc=5', 1))
    reject(native=native.replace('shadow=32', 'shadow=33'))
    reject(native=native.replace('polls=1', 'polls=0'))
    rows = _rows(native)
    _drop(rows, 'submitted=1 completed=1')
    reject(native=_join(rows))
    rows = _rows(native)
    _drop(rows, NATIVE_ARMED)
    reject(native=_join(rows))
    reject(native=native + NATIVE_ARMED + '\n')
    rows = _rows(native)
    _drop(rows, NATIVE_CLOSE)
    reject(native=_join(rows))
    reject(native=native + NATIVE_CLOSE + '\n')
    for old, new in [('jobs=8', 'jobs=7'), ('fence=8', 'fence=7'),
                     ('epoch=1', 'epoch=2'), ('ready=0', 'ready=1')]:
        reject(native=_replace(native, NATIVE_ARMED, NATIVE_ARMED.replace(old, new)))
    for old, new in [('ready=1', 'ready=0'), ('jobs=8', 'jobs=7'),
                     ('fence=8', 'fence=7'), ('epoch=1', 'epoch=2'),
                     ('clean=1', 'clean=0')]:
        reject(native=_replace(native, NATIVE_CLOSE, NATIVE_CLOSE.replace(old, new)))
    reject(native=native + 'SWEET METAL245: root unknown ready=1\n')
    reject(native=native + 'SWEET METAL245 truncated\n')
    rows = _rows(native)
    armed = rows.pop(_find(rows, NATIVE_ARMED))
    close = rows.pop(_find(rows, NATIVE_CLOSE))
    insert = _find(rows, NATIVE_OPEN)
    rows[insert:insert] = [close, armed]
    reject(native=_join(rows))
    rows = _rows(native)
    opened = rows.pop(_find(rows, NATIVE_OPEN))
    rows.insert(_find(rows, NATIVE_CLOSE), opened)
    reject(native=_join(rows))

    # Compositor handoff must follow native eighth submission and the same
    # earlier launchd proxy, with the exact eight-fence root release.
    reject(native=_replace(native, NATIVE_OPEN, NATIVE_OPEN.replace('root_fence=8', 'root_fence=7')))
    reject(native=_replace(native, NATIVE_OPEN, NATIVE_OPEN.replace('pid=57', 'pid=0')))
    reject(native=_replace(native, NATIVE_OPEN, NATIVE_OPEN.replace('pid=57', 'pid=58')))
    rows = _rows(native)
    opened = rows.pop(_find(rows, NATIVE_OPEN))
    rows.insert(_find(rows, 'submitted=8 completed=8'), opened)
    reject(native=_join(rows))
    rows = _rows(native)
    _drop(rows, NATIVE_PROXY)
    reject(native=_join(rows))
    reject(native=native + NATIVE_PROXY + '\n')
    reject(native=native + NATIVE_OPEN + '\n')
    reject(native=native.replace('pid=57', 'pid=4294967296'))
    reject(native=native.replace('pid=57', 'pid=18446744073709551616'))
    rows = _rows(native)
    proxy = rows.pop(_find(rows, NATIVE_PROXY))
    rows.append(proxy)
    reject(native=_join(rows))


def current_checks(args):
    check(args.current_stdout and args.current_stderr and args.observer and
          args.build and args.core)
    stdout = args.current_stdout.read_text()
    stderr = args.current_stderr.read_text()
    native = args.observer.read_text()
    result = qualify_bootstrap_log(stdout, stderr, native,
                                   build=args.build, core=args.core)
    check(result['memory_profile'] == 'bootstrap-start')
    check(result['output_words'] == 28928 and result['completed_root_fences'] == 8)
    check(result['compositor_opens'] == 1)
    check(result['startup']['elapsed_ns'] == 44460868178)
    check(result['startup']['clock'] ==
          'userspace-bootstrap-recorded-interval-not-total-boot-wall-time')
    for key in ('MTLDevice_qualified', 'desktop_qualified', 'FPS_qualified',
                'high_refresh_qualified', 'daily_use_qualified'):
        check(result[key] is False)
    print(f'PASS current 0298 raw logs: build={result["build"]} '
          f'seed={result["seed"]} startup_elapsed_ns={result["startup"]["elapsed_ns"]}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--current-stdout', type=Path)
    parser.add_argument('--current-stderr', type=Path)
    parser.add_argument('--observer', type=Path)
    parser.add_argument('--build')
    parser.add_argument('--core')
    args = parser.parse_args()
    synthetic_checks()
    synthetic_count = checks
    if args.current_stdout is not None:
        current_checks(args)
    print(f'PASS {synthetic_count} synthetic bootstrap/lifecycle checks'
          + (f' and {checks - synthetic_count} current raw-log checks'
             if args.current_stdout else ''))


if __name__ == '__main__':
    main()
