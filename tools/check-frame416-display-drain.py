#!/usr/bin/env python3
"""Exercise the linked native display drain bodies with simulated latch outcomes."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, load, require, sha


build = import_module('build-frame416')


def between(text, start, end):
    first = text.index(start)
    return text[first:text.index(end, first)]


def check():
    receipt = load(build.MANIFEST)
    require(receipt['inputs_unchanged'] and receipt['kernel_sha256'] == sha(receipt['kernel'])
            and receipt['input_pins'][str(build.PATCH)] == sha(build.PATCH), 'linked display drain differs')
    source = Path(receipt['source'])
    device = source / 'bsd/dev'
    fb = (source / 'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
    board = (device / 'gauguin_ui_trace_board.c').read_text()
    with TemporaryDirectory(prefix='gauguin-display-drain-') as path:
        temporary = Path(path)
        (temporary / 'display_drain416.inc').write_text(between(
            fb, 'bool\nAppleCLCD::flip382EndingLocked()', '\nuintptr_t\nAppleCLCD::flip382Begin'))
        (temporary / 'scan_worker_drain416.inc').write_text(
            between(board, 'bool sweet_frame382_ending(void)', '\nuintptr_t sweet_frame382_buffer') +
            between(board, 'static struct {\n    const char *reason;', '\nstatic void scan_poll('))
        counts = []
        fixtures = (('clang++', 'c++17', 'gauguin_display_drain_host.cpp'),
                    ('clang', 'c11', 'gauguin_scan_worker_drain_host.c'))
        for compiler, standard, fixture in fixtures:
            executable = temporary / fixture.split('.')[0]
            subprocess.run(['xcrun', compiler, '-std=' + standard, '-g', '-O1', '-Wall', '-Wextra', '-Werror',
                '-fsanitize=address,undefined', '-fno-sanitize-recover=all', '-I' + str(device),
                '-I' + str(temporary), str(WORK / 'tests/fixtures' / fixture), '-o', str(executable)],
                check=True, timeout=60)
            counts.append(int(subprocess.check_output([executable], text=True, timeout=10)))
    framebuffer, worker = counts
    return dict(framebuffer_cases=framebuffer, scan_worker_cases=worker,
                patch_sha256=sha(build.PATCH), kernel_sha256=receipt['kernel_sha256'], device_commands=0)


if __name__ == '__main__':
    result = check()
    with (build.BASE / 'display-drain-host.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result))
