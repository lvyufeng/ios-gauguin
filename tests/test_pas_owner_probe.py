#!/usr/bin/env python3
"""Execute the actual kernel PAS owner consumer with the actual shim producer."""
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
XNU = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SOURCE = Path(os.environ.get('PAS_PROBE_SOURCE', XNU / 'bsd/dev/gauguin_pas_probe.c'))


def main():
    if not SOURCE.is_file():
        if 'XNU_SOURCE' in os.environ or 'PAS_PROBE_SOURCE' in os.environ:
            raise SystemExit(f'PAS probe missing: {SOURCE}')
        print(f'skip PAS owner probe: not staged at {SOURCE}')
        return
    source = SOURCE.read_text()
    source_root = SOURCE.resolve().parents[2]
    if (source_root / 'bsd/conf/files').is_file():
        entries = (source_root / 'bsd/conf/files').read_text()
        assert entries.count('bsd/dev/gauguin_pas_probe.c\t\tstandard') == 1
        init = (source_root / 'bsd/kern/bsd_init.c').read_text()
        declarations = re.search(r'#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
        assert declarations and 'extern void sweet_pas_probe_init(void);\n' in declarations.group(1)
        hook = '\tif (mountroot_post_hook != NULL) {\n\t\tmountroot_post_hook();\n\t}\n#endif'
        calls = re.match(r'\s*#if defined\(GAUGUIN\)\n([^#]+)#endif', init.split(hook)[1])
        assert calls and re.search(r'^\s*sweet_pas_probe_init\(\);\s*$', calls.group(1), re.M)
        assert init.count('sweet_pas_probe_init();') == 1
    assert not re.search(r'ml_io_map|ml_static_ptovirt|pmap_enter|smc #|volatile', source)
    source = re.sub(r'^#include .*\n', '', source, flags=re.M)
    fixture = (ROOT / 'tests/fixtures/gauguin_pas_probe_host.c').read_text()
    assert fixture.count('@SOURCE@') == 1
    with tempfile.TemporaryDirectory(prefix='pas-consumer-') as temporary:
        out = Path(temporary)
        env = dict(os.environ, PAS_TEST_OUT=str(out))
        subprocess.run([sys.executable, str(ROOT / 'tests/pas_reservation/make_cases.py')],
                       env=env, check=True, timeout=60)
        import json
        cases = json.loads((out / 'cases.json').read_text())
        ready = next(c['path'] for c in cases if c['name'] == 'ready')
        (out / 'test.c').write_text(fixture.replace('@SOURCE@', source))
        subprocess.run(shlex.split(os.environ.get('CC', 'cc')) + [
            '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic', '-O1', '-g',
            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
            '-I' + str(ROOT / 'shim'), str(out / 'test.c'),
            str(ROOT / 'shim/pas_reservation.c'), '-o', str(out / 'test')],
            check=True, timeout=60)
        subprocess.run([str(out / 'test'), ready], check=True, timeout=30)


if __name__ == '__main__':
    main()
