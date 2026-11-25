#!/usr/bin/env python3
"""Test native deadline hooks and re-score the exact archived 0417 control."""

from importlib import import_module
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import frame419_log as timeline
from frame366_scope import WORK, load, require, sha


scope = import_module('prepare-frame419')
sustained = import_module('run-frame417-trial')
between = import_module('check-frame416-display-drain').between


def ordered(source, pieces):
    positions = [source.index(piece) for piece in pieces]
    require(positions == sorted(set(positions)), 'native timeline moved across an ownership boundary')


def native_checks(link):
    source = Path(link['source'])
    device = source / 'bsd/dev'
    kernel = source / 'iokit/Kernel/arm'
    board = (device / 'gauguin_ui_trace_board.c').read_text()
    fb = (kernel / 'SweetFramebuffer.cpp').read_text()
    gpu = (kernel / 'GauguinGPU.cpp').read_text()
    completion = between(gpu, 'const uint64_t observedEop', 'if(reap&&!reapClosed())')
    ordered(completion, ('sweet_frame419_clock()', 'flush_dcache64', 'setSurfaceGPUState(b->surface,0)',
                         'sweet_frame419_record(F419_GPU', 'sweet_fb357_finish_writer('))
    promotion = between(fb, 'AppleCLCD::collectIssuedLocked', 'AppleCLCD::observePendingReady')
    ordered(promotion, ('scan354_can_promote', 'sweet_fb_frame_move(&fHeldReady',
                        'sweet_frame419_record(F419_PROMOTE'))
    ordered(fb, ('*privateCopyBegin = sweet_frame419_clock()', 'if (ordered) __asm__ volatile("dsb sy"',
                 '*verifiedFullCopy = frameCopyEnd'))
    with TemporaryDirectory(prefix='gauguin-deadline-host-') as directory:
        tmp = Path(directory)
        (tmp / 'frame419-timeline.inc').write_text(
            between(board, 'uint64_t sweet_frame419_clock', 'void sweet_frame344_record'))
        (tmp / 'frame419-drain.inc').write_text(
            between(board, 'static void frame419_drain', 'static void frame_drain'))
        exe = tmp / 'deadline-test'
        subprocess.run(['xcrun', 'clang', '-std=c11', '-O1', '-Wall', '-Wextra', '-Werror',
                        '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-I', str(device),
                        '-I', str(tmp), str(WORK / 'tests/fixtures/gauguin_deadline_timeline_host.c'),
                        str(device / 'gauguin_ui_trace.c'), '-o', str(exe)], check=True, timeout=60)
        output = subprocess.check_output([str(exe)], text=True, timeout=10)
        require(output.endswith('native deadline timeline verified\n'), 'native timeline fixture failed')


def analysis_checks():
    cases = (
        ((115, 116, 117, 120), 'GPU completion observed late'),
        ((80, 116, 117, 120), 'GPU visibility late'),
        ((80, 92, 116, 120), 'copy started late after GPU visibility'),
        ((80, 92, 98, 120), 'copy crossed cutoff'),
        ((80, 92, 105, 120), 'copy start overlaps cutoff'),
        ((80, 92, 95, 100), 'copy finished before cutoff'),
        ((80, 105, 110, 120), 'timing overlaps cutoff'),
    )
    for clocks, expected in cases:
        require(timeline.where_late(*clocks, 100, 110) == expected, 'deadline attribution fixture differs')

    rows = ['F419E 1 64 1 1 0 0 64 64 1', 'F419E 2 68 40 200000001 2 3 65 66 0']
    stamp = sum(len(row) + 2 for row in rows)
    header = f'SWEET F419 H: count=2 reason=1 lost=0 start=100 end={100 + 45 * timeline.SECOND}\n'
    footer = f'SWEET F419 F: count=2 lost=0 bytes={stamp} overflow=0\n'
    limits = dict(rows=scope.ROW_LIMIT, wire_bytes=scope.WIRE_BYTES, duration_seconds=45)
    wire = header + '\n'.join(rows) + '\n' + footer
    parsed, meta = timeline.read_timeline(wire, limits)
    require(parsed[0].id == 0x200000001 and meta['wire_bytes'] == stamp, 'deadline wire fixture differs')
    for invalid in (wire.replace('overflow=0', 'overflow=1'), wire.replace('reason=1', 'reason=2'),
                    wire.replace('F419E 2', 'F419E 3')):
        try:
            timeline.read_timeline(invalid, limits)
        except ValueError:
            continue
        raise ValueError('corrupted timeline was accepted')
    return len(cases) + 4


def replay_control():
    raw = (scope.LAST / 'kernel.log').read_text()
    plan = load(scope.P417 / 'trial-plan.json')
    saved = load(scope.LAST / 'sustained-scanout.json')
    decoded = sustained.measure(raw, plan)
    require(all(saved[key] == value for key, value in decoded.items())
            and timeline.whole_interval(raw, decoded, plan) == {'confirmed_new': 1768, 'maximum_new': 1768},
            'archived 0417 count changed')


if __name__ == '__main__':
    link = scope.build.native()
    native_checks(link)
    cases = analysis_checks()
    replay_control()
    scope.save(scope.HOST, dict(cases=cases, native_hooks_validated=True, archived_0417_score_matches=True,
                                kernel_sha256=link['kernel_sha256'], patch_sha256=sha(scope.PATCH),
                                device_commands=0))
