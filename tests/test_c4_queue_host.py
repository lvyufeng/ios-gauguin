#!/usr/bin/env python3
"""Exercise the production CPU tracer: identity, numerical bounds, concurrent cap."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess

WORK = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    out.mkdir(parents=True)
    source = WORK/'tests/fixtures/c4_queue_host.c'
    header = WORK/'graphics/gauguin-c4-queue/GauguinC4QueueTrace.h'
    pins = {str(p): sha(p) for p in (source, header, Path(__file__).resolve())}
    argv = ['xcrun', 'clang', '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
            '-fsanitize=address,undefined', str(source), '-o', str(out/'check')]
    compile = subprocess.run(argv, capture_output=True, text=True)
    (out/'compile.log').write_text(compile.stdout+compile.stderr)
    assert compile.returncode == 0
    rows = []
    for case in ('scope', 'boundaries', 'concurrent'):
        with (out/(case+'.stderr')).open('x') as err:
            proc = subprocess.run([str(out/'check'), case], stdout=subprocess.PIPE,
                                  stderr=err, text=True, timeout=40)
        (out/(case+'.stdout')).write_text(proc.stdout)
        assert proc.returncode == 0, case
        result = json.loads(proc.stdout)
        lines = (out/(case+'.stderr')).read_text().splitlines(keepends=True)
        marker = 'GAUGUIN C4Q321: limit=32768 coverage=incomplete\n'
        actual = [line for line in lines if line != marker]
        assert len(actual) == result['records']
        assert lines.count(marker) == result.get('markers', 0)
        assert all(re.fullmatch(r'GAUGUIN C4Q321: phase=[0-9] object=0x[0-9a-f]+ start_us=[0-9]+ end_us=[0-9]+ value=[0-9]+\n', line) for line in actual)
        assert all(len(line.encode()) <= 128 for line in lines)
        result.update(log_bytes=sum(len(line.encode()) for line in lines),
                      max_line_bytes=max(map(len, lines), default=0))
        rows.append(result)
    assert rows[-1]['log_bytes'] <= 32769*128
    assert all(sha(name) == digest for name, digest in pins.items())
    result = dict(state='passed-production-C4Q321-scope-bounds-concurrent-cap',
                  input_pins=pins, compiler_argv=argv, cases=rows,
                  trace_max_bytes=32769*128, device_commands=0, sanitizer_errors=False)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'compiler_argv')}, indent=2))


if __name__ == '__main__':
    main()
