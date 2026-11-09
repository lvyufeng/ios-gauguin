#!/usr/bin/env python3
"""Exercise the real exec argument copy and alignment with the inert opt-in."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile


def test(source, output):
    fixture = Path(__file__).with_name('fixtures') / 'eagl_inject_host.c'
    source_path = source / 'bsd/kern/kern_exec.c'
    original = source_path.read_bytes()
    text = original.decode()
    assert 'static TUNABLE(uint32_t, sweet_eagl_inject_requested, "sweeteagl", 0);' in text
    assert text.count('sweet_eagl_exec_inject(imgp);\n#endif\n\n\t/* Save space for envv[] NULL terminator */') == 1
    output.mkdir(parents=True)
    for name, marker in [('env', 'SWEET_DYLD_EXEC_PROBE'), ('inject', 'SWEET_EAGL_INJECT')]:
        start = text.index('\n', text.index(f'/* {marker}_BEGIN:')) + 1
        end = text.index(f'/* {marker}_END */', start)
        (output / f'production-{name}.h').write_text(text[start:end])
    for name, symbol in [('add', 'exec_add_user_string'), ('extract', 'exec_extract_strings')]:
        start = text.index(f'static int\n{symbol}(')
        end = text.index('\n}\n', start) + 3
        (output / f'production-{name}.h').write_text(text[start:end])

    cases = (
        'mobile root exact-fit one-short partial-copy disabled bad-flag trace-off other-path null-context '
        'mode-absent mode-duplicate mode-other already conflicting duplicate other-proc script addr32 '
        'missing-vnode no-cred setuid other-uid no-target wrong-target target-mount no-attributes '
        'getattr-error target-acl no-library library-mode library-owner library-type library-acl-error'
    ).split()
    binary = output / 'eagl-inject-model'
    compiler = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--find', 'clang'], text=True).strip()
    sdk = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
    build = [compiler, '-isysroot', sdk, '-std=gnu11', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
             '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-I', str(output), str(fixture), '-o', str(binary)]
    subprocess.run(build, check=True)
    for case in cases:
        result = subprocess.run([binary, case], capture_output=True, text=True)
        (output / f'{case}.stdout').write_text(result.stdout)
        (output / f'{case}.stderr').write_text(result.stderr)
        assert result.returncode == 0 and not result.stderr, (case, result.returncode, result.stderr)
        lines = result.stdout.splitlines()
        model = re.fullmatch(r'MODEL PASS outcome=(\d+) reason=(\d+) event=([01])', lines[-1])
        assert model is not None, (case, lines)
        outcome, reason, event = map(int, model.groups())
        appended = int(outcome == 1)
        assert len(lines) == 1 + event + appended, (case, lines)
        if event:
            error = 14 if case == 'partial-copy' else 0
            pid = 58 if case == 'other-proc' else 57
            expected = (fr'SWEET EAGL INJECT: pid={pid} outcome={outcome} reason={reason} error={error} '
                        fr'added={appended} envc=\d+ uid=\d+ ruid=\d+')
            assert re.fullmatch(expected, lines[0]), (case, lines)
        if appended:
            assert lines[1] == ('SWEET DYLD EXEC: pid=57 image=1 argc=1 envc=3 job=0 '
                                'insert=1 expected=1 mode=1 admission=1'), (case, lines)
    assert source_path.read_bytes() == original
    print(f'PASS {len(cases)} production exec extraction and insertion cases (ASAN + UBSAN)')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=os.environ.get('XNU_SOURCE'))
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    if args.source is None:
        print('SKIP EAGL exec insertion model: set XNU_SOURCE or pass --source')
    elif args.out is not None:
        test(args.source, args.out.resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='eagl-inject-host-') as directory:
            test(args.source, Path(directory) / 'result')
