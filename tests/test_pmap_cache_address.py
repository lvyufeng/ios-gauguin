#!/usr/bin/env python3
"""Exercise the real cache-attribute flush function with pages above 4 GiB."""
from pathlib import Path
import hashlib
import os
import re
import subprocess
import tempfile

R = Path(__file__).resolve().parent.parent
S = Path(os.environ.get('XNU_SOURCE', str(R / '.deps-cache/p0-20261105/source176-codex')))
pmap = S / 'osfmk/arm/pmap/pmap.c'
types = S / 'osfmk/mach/vm_types.h'
param = S / 'osfmk/mach/vm_param.h'
pins = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (pmap, types, param)}
function = re.search(r'void\npmap_sync_page_attributes_phys\(\n\s*ppnum_t pp\)\n\{.*?\n\}', pmap.read_text(), re.S)
assert function, 'actual pmap cache-attribute function missing'
page_type = re.search(r'typedef uint32_t ppnum_t[^;]*;', types.read_text())
conversion = re.search(r'^#define ptoa_64\(x\) \(\(uint64_t\)\(x\) << PAGE_SHIFT\)$', param.read_text(), re.M)
assert page_type and conversion, 'unexpected native page-number ABI'
harness = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
typedef uint64_t vm_offset_t;
typedef uint64_t vm_size_t;
#define __kernel_ptr_semantics
#define PAGE_SIZE (UINT64_C(1) << PAGE_SHIFT)
#define TRUE 1
@TYPE@
@CONVERSION@
static uint64_t received;
static void flush_dcache(vm_offset_t address, unsigned bytes, int physical) {
    if (bytes != PAGE_SIZE || physical != TRUE) abort();
    received = address;
}
@FUNCTION@
int main(void) {
    const uint64_t addresses[] = {
        0, 0x1000, 0xffffc000, 0x100000000, 0x180000000,
        0x27c55c000, 0x27fff0000, 0xfffffc000,
        (uint64_t)UINT32_MAX << PAGE_SHIFT
    };
    for (unsigned i = 0; i < sizeof(addresses)/sizeof(addresses[0]); ++i) {
        uint32_t page = (uint32_t)(addresses[i] >> PAGE_SHIFT);
        uint64_t expected = (uint64_t)page * PAGE_SIZE;
        pmap_sync_page_attributes_phys(page);
        if (received != expected) {
            fprintf(stderr, "PA truncated: expected=0x%llx actual=0x%llx shift=%d\n",
                (unsigned long long)expected, (unsigned long long)received, PAGE_SHIFT);
            return 1;
        }
    }
    puts("physical cache flush retains all address bits (9 cases)");
    return 0;
}
'''
harness = harness.replace('@TYPE@', page_type[0]).replace('@CONVERSION@', conversion[0]).replace('@FUNCTION@', function[0])
with tempfile.TemporaryDirectory(prefix='pmap-cache-address-') as tmp:
    tmp = Path(tmp)
    unit = tmp / 'test.c'
    unit.write_text(harness)
    for shift in (12, 14):
        binary = tmp / f'test-{shift}'
        subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-O1',
                        '-fsanitize=address,undefined', f'-DPAGE_SHIFT={shift}',
                        str(unit), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
assert pins == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in pins}, 'native inputs changed'
