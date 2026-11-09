#!/usr/bin/env python3
"""Exercise the real exec argument copy and alignment with the inert opt-in."""
import argparse
import errno
import os
from pathlib import Path
import re
import subprocess
import tempfile


def test(source, output):
    fixture = Path(__file__).with_name('fixtures') / 'eagl_inject_host.c'
    kern = source / 'bsd/kern'
    originals = {name: (kern / name).read_bytes() for name in ('kern_exec.c', 'sweet_amfi.c', 'kern_memorystatus.c')}
    text = originals['kern_exec.c'].decode()
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
    for name, file, marker in (
        ('diagnostic-caller', 'sweet_amfi.c', 'SWEET_EAGL_DIAGNOSTIC_CALLER'),
        ('memory', 'kern_memorystatus.c', 'SWEET_EAGL_DENIED_GET8'),
        ('pilot', 'kern_exec.c', 'SWEET_EAGL_GPU_PILOT'),
    ):
        body = originals[file].decode()
        start = body.index('\n', body.index(f'/* {marker}_BEGIN */')) + 1
        end = body.index(f'/* {marker}_END */', start)
        (output / f'production-{name}.h').write_text(body[start:end])
    memory = originals['kern_memorystatus.c'].decode()
    start = memory.index('\tif (!kauth_cred_issuser', memory.index('\nmemorystatus_control('))
    end = memory.index('\n\t}\n', start) + 4
    auth = memory[start:end]
    assert '\t\tsweet_eagl_log_denied_get8(p, args);\n#endif\n\t\terror = EPERM;\n\t\tgoto out;' in auth
    (output / 'production-auth.h').write_text(auth)

    cases = (
        'mobile root exact-fit one-short partial-copy disabled bad-flag trace-off other-path null-context '
        'mode-absent mode-duplicate mode-other already conflicting duplicate other-proc script addr32 '
        'missing-vnode no-cred setuid other-uid no-target wrong-target target-mount no-attributes '
        'getattr-error target-acl no-library library-mode library-owner library-type library-acl-error null-thread '
        'shadow shadow-no-exec shadow-not-marked shadow-wrong-pid shadow-wrong-id shadow-wrong-version '
        'memory-self memory-disabled memory-other-proc memory-other-uid memory-root memory-entitled '
        'memory-other-pid memory-wrong-size memory-wrong-command memory-flags memory-no-buffer'
        ' pilot-good pilot-mode-off pilot-argv0-only pilot-wrong-parent pilot-reparented pilot-exec-not-spawn'
        ' pilot-other-vnode pilot-writable-proxy pilot-thread-mismatch pilot-pid-reused pilot-wrong-uid pilot-foreign-task'
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
        if case.startswith('pilot-'):
            recorded = case in ('pilot-good', 'pilot-pid-reused', 'pilot-wrong-uid', 'pilot-foreign-task')
            trace = 'SWEET DYLD EXEC: pid=57 image=2 argc=2 envc=0 job=1 insert=0 expected=0 mode=0 admission=0'
            want = [trace]
            if recorded:
                want.append('SWEET GPU AUTH: recorded launchd compositor proxy pid=57')
            want.append(f'PILOT PASS recorded={int(recorded)} allowed={int(case == "pilot-good")}')
            assert lines == want, (case, lines)
            continue
        if case.startswith('memory-'):
            expected = []
            if case == 'memory-self':
                expected.append('SWEET EAGL MEMLIMIT: pid=57 active_mb=64 active_attr=1 inactive_mb=-1 inactive_attr=0')
            error = 0 if case in ('memory-root', 'memory-entitled') else errno.EPERM
            expected.append(f'MEMORY PASS error={error} snapshots={int(case == "memory-self")}')
            assert lines == expected, (case, lines)
            continue
        model = re.fullmatch(r'MODEL PASS outcome=(\d+) reason=(\d+) event=([01])', lines[-1])
        assert model is not None, (case, lines)
        outcome, reason, event = map(int, model.groups())
        appended = int(outcome == 1)
        assert len(lines) == 1 + event + appended, (case, lines)
        if event:
            error = errno.EFAULT if case == 'partial-copy' else 0
            pid = 58 if case in ('other-proc', 'shadow-wrong-pid') else 57
            expected = (fr'SWEET EAGL INJECT: pid={pid} outcome={outcome} reason={reason} error={error} '
                        fr'added={appended} envc=\d+ uid=\d+ ruid=\d+')
            assert re.fullmatch(expected, lines[0]), (case, lines)
        if appended:
            assert lines[1] == ('SWEET DYLD EXEC: pid=57 image=1 argc=1 envc=3 job=0 '
                                'insert=1 expected=1 mode=1 admission=1'), (case, lines)
    assert all((kern / name).read_bytes() == original for name, original in originals.items())
    print(f'PASS {len(cases)} production exec and GET8 diagnostic cases (ASAN + UBSAN)')


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
