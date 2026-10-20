#!/usr/bin/env python3
"""Wrap a SWEET-only source in #if defined(ARM64_BOARD_CONFIG_SWEET).

xnu's makefile builds every `standard` file for every machine config, and
dxb's bootstrap VMAPPLE kernel cannot link SWEET-only code. The guard goes
after the leading comment block so the file's description stays readable.
"""
import sys

for path in sys.argv[1:]:
    text = open(path).read()
    if 'ARM64_BOARD_CONFIG_SWEET' in text:
        continue
    lines = text.split('\n')
    i = 0
    while i < len(lines) and (lines[i].startswith('/*') or lines[i].startswith(' *')
                              or lines[i].startswith('//') or lines[i] == ''):
        if lines[i].rstrip().endswith('*/') and i > 0:
            i += 1
            break
        i += 1
    lines.insert(i, '#if defined(ARM64_BOARD_CONFIG_SWEET)')
    out = '\n'.join(lines).rstrip('\n') + '\n#endif /* ARM64_BOARD_CONFIG_SWEET */\n'
    open(path, 'w').write(out)
    print(f'guarded {path}')
