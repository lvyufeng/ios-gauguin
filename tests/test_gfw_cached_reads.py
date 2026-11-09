#!/usr/bin/env python3
"""Compare real old/new SMMU+GMU guard IO and results under read corruption."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent.parent
NAME = 'bsd/dev/gauguin_gmu_board.c'
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/p0-20261105/source200-codex')) / NAME
REFERENCE = Path(os.environ.get('XNU_REFERENCE', ROOT / '.deps-cache/p0-20261105/source199-codex')) / NAME
FIXTURE = ROOT / 'tests/fixtures/gpu-user/gfw_cached_reads_host.c'


def main():
    pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (SOURCE, REFERENCE, FIXTURE)}
    source, old = SOURCE.read_text(), REFERENCE.read_text()

    def extract(text, signature):
        start = text.index(signature)
        return text[start:text.index('\n}\n', start) + 3]

    helpers = source[source.index('struct gfw_read_sample {'):source.index('static bool gfw_faults(')]
    fixture = FIXTURE.read_text()
    for marker, value in (
            ('@HELPERS@', helpers),
            ('@BASELINE@', extract(old, 'static bool gfw_faults(').replace('gfw_faults(', 'baseline_faults(', 1)),
            ('@CURRENT@', extract(source, 'static bool gfw_faults('))):
        assert fixture.count(marker) == 1
        fixture = fixture.replace(marker, value)
    with tempfile.TemporaryDirectory(prefix='gfw-cached-reads-') as directory:
        directory = Path(directory)
        unit = directory / 'test.c'
        unit.write_text(fixture)
        env = dict(os.environ, ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                   UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror',
                        '-O1', '-g', '-fsanitize=address,undefined',
                        '-fno-omit-frame-pointer', str(unit), '-o', str(directory / 'test')],
                       env=env, check=True)
        subprocess.run([str(directory / 'test')], env=env, check=True, timeout=30)
    assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}


if __name__ == '__main__':
    main()
