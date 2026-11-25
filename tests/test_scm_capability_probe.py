#!/usr/bin/env python3
"""Actual SCM probe flow with one mocked SMC boundary; no secure call execution."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile
HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'tools/mkpayload.py').is_file())
DEFAULT_ROOT = Path(os.environ.get('XNU_SOURCE', str(HERE if (HERE / 'bsd/dev/gauguin_scm_probe.c').is_file()
                                                        else REPO / '.deps-cache/xnu-patched-0082-2')))
FIXTURE = HERE / 'test_scm_probe_host.c'
if not FIXTURE.is_file(): FIXTURE = HERE / 'fixtures/gauguin_scm_probe_host.c'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=DEFAULT_ROOT / 'bsd/dev/gauguin_scm_probe.c')
parser.add_argument('--fixture', type=Path, default=FIXTURE)
args = parser.parse_args()
source = args.source.read_text()
root = args.source.resolve().parents[2]
assert (root / 'bsd/conf/files').read_text().count('bsd/dev/gauguin_scm_probe.c\t\tstandard') == 1
init = (root / 'bsd/kern/bsd_init.c').read_text()
declarations = re.search(r'#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
assert declarations and 'extern void sweet_scm_probe_init(void);\n' in declarations.group(1)
assert '\tif (mountroot_post_hook != NULL) {\n\t\tmountroot_post_hook();\n\t}\n#endif' in init
old_hook = '\tif (mountroot_post_hook != NULL) {\n\t\tmountroot_post_hook();\n\t}\n#endif'
calls = re.match(r'\s*#if defined\(GAUGUIN\)\n([^#]+)#endif', init.split(old_hook)[1])
assert calls and re.search(r'^\s*sweet_scm_probe_init\(\);\s*$', calls.group(1), re.M)
assert init.count('sweet_scm_probe_init();') == 1
signature = 'static void\nscmp_invoke(struct scmp_registers *r)\n{'
start = source.index(signature); end = source.index('\n}', start) + 2
boundary = source[start:end]
assert boundary.count('"smc #0"') == 1
for i in range(7):
    assert f'__asm__("x{i}") = r->x[{i}]' in boundary
    assert f'"+r"(x{i})' in boundary
    assert f'r->x[{i}] = x{i};' in boundary
for i in range(7,18): assert f'"x{i}"' in boundary
assert '"cc", "memory"' in boundary
source = source[:start] + 'static void\nscmp_invoke(struct scmp_registers *r) { fake_smc(r); }' + source[end:]
source = re.sub(r'^#include .*\n', '', source, flags=re.MULTILINE)
assert '__asm__' not in source and 'smc #0' not in source
assert 'ml_io_map' not in source and 'volatile' not in source and '%p' not in source
assert 'panic(' not in source and 'ml_set_interrupts_enabled(' not in source
fixture = args.fixture.read_text(); assert fixture.count('@SOURCE@') == 1
with tempfile.TemporaryDirectory(prefix='scm-cap-probe-') as temporary:
    directory=Path(temporary); (directory/'test.c').write_text(fixture.replace('@SOURCE@',source))
    subprocess.run([os.environ.get('CC','clang'),'-std=c11','-Wall','-Wextra','-Werror','-pedantic',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer','-g','-O1',
                    str(directory/'test.c'),'-o',str(directory/'test')],check=True)
    subprocess.run([str(directory/'test')],check=True)
