#!/usr/bin/env python3
"""Test the linked 0417 scheduler, motion and display drain bodies on the host."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, sha


scope = import_module('prepare-frame417')
between = import_module('check-frame416-display-drain').between


def check():
    receipt = scope.native()
    source = Path(receipt['source'])
    device = source / 'bsd/dev'
    fb = (source / 'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    board = (device / 'gauguin_ui_trace_board.c').read_text()
    touch = (device / 'sweet_touch.c').read_text()
    with TemporaryDirectory(prefix='gauguin-sustain417-') as path:
        temporary = Path(path)
        (temporary / 'display_drain416.inc').write_text(between(
            fb, 'bool\nAppleCLCD::flip382EndingLocked()', '\nuintptr_t\nAppleCLCD::flip382Begin'))
        (temporary / 'scan_worker_drain416.inc').write_text(
            between(board, 'bool sweet_frame351_window(void)', '\nstatic bool scan351_position') +
            between(board, 'unsigned sweet_frame382_copy_limit(void)', '\nuintptr_t sweet_frame382_buffer') +
            between(board, 'static struct {\n    const char *reason;', '\nstatic void scan_poll('))
        (temporary / 'sustain_motion417.inc').write_text(between(
            touch, 'static bool sweet_continuous_mode;', '\nstatic void\nsweet_script_abort'))
        counts = []
        fixtures = (('clang++', 'c++17', 'gauguin_display_drain_host.cpp'),
                    ('clang', 'c11', 'gauguin_scan_worker_drain_host.c'),
                    ('clang', 'c11', 'gauguin_sustain_motion_host.c'))
        for compiler, standard, fixture in fixtures:
            executable = temporary / fixture.split('.')[0]
            subprocess.run(['xcrun', compiler, '-std=' + standard, '-DSUSTAINED417', '-g', '-O1',
                '-Wall', '-Wextra', '-Werror', '-fsanitize=address,undefined', '-fno-sanitize-recover=all',
                '-I' + str(device), '-I' + str(temporary), str(WORK / 'tests/fixtures' / fixture),
                '-o', str(executable)], check=True, timeout=60)
            counts.append(int(subprocess.check_output([executable], text=True, timeout=10)))
    framebuffer, worker, motion = counts
    return dict(framebuffer_cases=framebuffer, scan_worker_cases=worker, motion_cases=motion,
                patch_sha256=sha(scope.PATCH), kernel_sha256=receipt['kernel_sha256'], device_commands=0)


if __name__ == '__main__':
    result = check()
    scope.save(scope.HOST, result)
    print(json.dumps(result))
