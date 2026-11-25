#!/usr/bin/env python3
"""Host execution of the actual GCC-only probe; never hardware qualification."""
import argparse
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REPO = next(p for p in HERE.parents if (p / 'tools/mkpayload.py').is_file())
DEFAULT_ROOT = Path(os.environ.get('XNU_SOURCE', str(HERE if (HERE / 'bsd/dev/gauguin_gpu_probe.c').is_file()
                                                        else REPO / '.deps-cache/xnu-patched-0082-2')))
DEFAULT_FIXTURE = HERE / 'test_gpu_probe_host.c'
if not DEFAULT_FIXTURE.is_file():
    DEFAULT_FIXTURE = HERE / 'fixtures/gauguin_gpu_probe_host.c'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=DEFAULT_ROOT / 'bsd/dev/gauguin_gpu_probe.c')
parser.add_argument('--fixture', type=Path, default=DEFAULT_FIXTURE)
args = parser.parse_args()
source = args.source.read_text()
source_root = args.source.resolve().parents[2]
entries = (source_root / 'bsd/conf/files').read_text()
assert entries.count('bsd/dev/gauguin_gpu_probe.c\t\tstandard') == 1
init = (source_root / 'bsd/kern/bsd_init.c').read_text()
declarations = re.search(r'void \(\*unmountroot_pre_hook\)\(void\);\n#endif\n#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
assert declarations and 'extern void sweet_gpu_probe_init(void);\n' in declarations.group(1)
old_hook = '\tif (mountroot_post_hook != NULL) {\n\t\tmountroot_post_hook();\n\t}\n#endif\n'
assert init.count(old_hook) == 1
after = init.split(old_hook)[1]
guarded_calls = re.match(r'\s*#if defined\(GAUGUIN\)\n([^#]+)#endif', after)
assert guarded_calls and re.search(r'^\s*sweet_gpu_probe_init\(\);\s*$', guarded_calls.group(1), re.M)
assert init.count('sweet_gpu_probe_init();') == 1
old = 'uint32_t value = *(volatile uint32_t *)(base + offset);'
assert source.count(old) == 1
source = source.replace(old, 'uint32_t value = fake_read(base, offset);')
barrier = '__asm__ volatile("dmb oshld" ::: "memory");'
assert source.count(barrier) == 1
source = source.replace(barrier, '')
source = re.sub(r'^#include .*\n', '', source, flags=re.MULTILINE)
assert 'volatile' not in source and '__asm__' not in source and '%p' not in source
assert 'panic(' not in source and 'ml_set_interrupts_enabled(' not in source
assert 'write32(' not in source and 'sweet_spmi_' not in source
fixture = args.fixture.read_text()
assert fixture.count('@SOURCE@') == 1
with tempfile.TemporaryDirectory(prefix='gpu-gcc-probe-') as temporary:
    directory = Path(temporary)
    (directory / 'test.c').write_text(fixture.replace('@SOURCE@', source))
    subprocess.run([os.environ.get('CC', 'clang'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-pedantic', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-g', '-O1', str(directory / 'test.c'), '-o', str(directory / 'test')], check=True)
    subprocess.run([str(directory / 'test')], check=True)
