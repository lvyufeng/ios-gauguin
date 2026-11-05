#!/usr/bin/env python3
"""Actual runtime/protocol + real XNU SHA; bus/bootstrap/HID are orchestration mocks."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
REPO = next(p for p in (HERE, *HERE.parents) if (p / 'tools/mkpayload.py').is_file())
DEFAULT_XNU = REPO / '.deps-cache/p0-20261105/source104'
PIN = '007143e7d0a816e4ef228b5a08bf3132285230a5cd16164e8086696115d60f88'
SHA_FILES = ['ccdigest_init.c', 'ccdigest_update.c', 'ccdigest_final_64be.c',
             'ccsha256_ltc_di.c', 'ccsha256_ltc_compress.c', 'ccsha256_initial_state.c',
             'ccsha256_K.c', 'cc_clear.c']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xnu-source', type=Path, default=Path(os.environ.get('XNU_SOURCE', DEFAULT_XNU)))
    default_source = (Path(os.environ['XNU_SOURCE']) / 'bsd/dev/gauguin_nvt/runtime/nvt_runtime.c'
                      if 'XNU_SOURCE' in os.environ else HERE / 'nvt_runtime.c')
    parser.add_argument('--source', type=Path, default=default_source)
    parser.add_argument('--fixtures', type=Path, default=HERE if (HERE / 'test_runtime.c').is_file() else HERE / 'fixtures')
    parser.add_argument('--hid-header', type=Path)
    parser.add_argument('--firmware', type=Path, help='optional actual pinned local file; default uses a transparent temporary synthetic-pin test variant')
    args = parser.parse_args()
    xnu, source = args.xnu_source.resolve(), args.source.resolve()
    if not source.is_file():
        parser.error(f'coordinator missing: {source}')
    module = source.parent.parent
    hid = args.hid_header or xnu / 'iokit/IOKit/SweetHIDTouchFrame.h'
    if not hid.is_file():
        parser.error('provide --hid-header pointing to the canonical IOKit shared header')
    production = source.read_text()
    digest_pattern = re.compile(r'(static const uint8_t expected\[SHA256_DIGEST_LENGTH\] = \{)(.*?)(\n    \};)', re.S)
    matches = list(digest_pattern.finditer(production))
    assert len(matches) == 1
    digest_bytes = bytes(int(v, 16) for v in re.findall(r'0x([0-9a-fA-F]{2})', matches[0].group(2)))
    assert digest_bytes.hex() == PIN, 'production digest pin unexpectedly changed'
    sha = (xnu / 'libkern/crypto/corecrypto_sha2.c').read_text()
    wrapper = '''#include <stdlib.h>
#include <libkern/crypto/sha2.h>
#include <corecrypto/ccdigest.h>
#define panic(...) abort()
#define SHA256_DI() (&ccsha256_ltc_di)
#define SHA256_INIT(di,ctx) ccdigest_init(di,ctx)
#define SHA256_UPDATE(di,ctx,len,d) ccdigest_update(di,ctx,len,d)
'''
    for name in ('SHA256_Init', 'SHA256_Update', 'SHA256_Final'):
        begin = sha.index('void\n' + name + '(')
        wrapper += sha[begin:sha.index('\n}\n', begin) + 3] + '\n'
    with tempfile.TemporaryDirectory(prefix='nvt-runtime-') as temporary:
        out = Path(temporary)
        include = out / 'include'; include.mkdir()
        (include / 'corecrypto').symlink_to(xnu / 'EXTERNAL_HEADERS/corecrypto', target_is_directory=True)
        (include / 'libkern').symlink_to(xnu / 'libkern/libkern', target_is_directory=True)
        (include / 'IOKit').mkdir()
        (include / 'IOKit/SweetHIDTouchFrame.h').symlink_to(hid.resolve())
        (out / 'sha256_actual.c').write_text(wrapper)
        def build(selected, name):
            command = [os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra', '-Werror',
                       '-D__STDC_WANT_LIB_EXT1__=1', '-U__ARM_ARCH_8_4__',
                       '-fsanitize=address,undefined', '-O1', '-g',
                       '-I', str(include), '-I', str(args.fixtures.resolve()), '-I', str(module),
                       '-I', str(module / 'kernel-bus'), '-I', str(module / 'bootstrap'),
                       '-DNRT_SOURCE_PATH="' + str(selected) + '"',
                       str(args.fixtures / 'test_runtime.c'), str(module / 'nvt_protocol.c'),
                       str(out / 'sha256_actual.c')]
            command += [str(xnu / 'osfmk/corecrypto' / item) for item in SHA_FILES]
            command += ['-o', str(out / name)]
            # XNU omits the host-only cc_disable_dit helper. Disable that HOST
            # feature, as CC_KERNEL also does; the full digest algorithm is real.
            subprocess.run(command, check=True)
            return out / name
        if args.firmware:
            firmware = args.firmware.resolve()
            data = firmware.read_bytes()
            assert len(data) == 139264 and hashlib.sha256(data).hexdigest() == PIN
            binary = build(source, 'real-file-test')
            subprocess.run([str(binary), str(firmware)], check=True, timeout=30)
            print('MODE: unmodified production coordinator + actual pinned local firmware')
        else:
            data = bytes(range(256)) * (139264 // 256)
            firmware = out / 'synthetic-firmware'; firmware.write_bytes(data)
            binary = build(source, 'production-pin-negative')
            subprocess.run([str(binary), str(firmware), 'reject-synthetic'], check=True, timeout=30)
            # Test-only source copy changes EXACTLY the already-verified digest
            # bytes. No production switch or success/digest stub exists.
            tree = out / 'module'; tree.mkdir()
            for item in module.iterdir():
                if item.name != 'runtime':
                    (tree / item.name).symlink_to(item, target_is_directory=item.is_dir())
            variant_dir = tree / 'runtime'; variant_dir.mkdir()
            (variant_dir / 'nvt_runtime.h').symlink_to(source.parent / 'nvt_runtime.h')
            synthetic_digest = hashlib.sha256(data).digest()
            replacement = '\n        ' + ','.join(f'0x{byte:02x}' for byte in synthetic_digest)
            variant_text = digest_pattern.sub(lambda m: m.group(1) + replacement + m.group(3), production)
            variant = variant_dir / 'nvt_runtime.c'; variant.write_text(variant_text)
            binary = build(variant, 'synthetic-flow-test')
            subprocess.run([str(binary), str(firmware)], check=True, timeout=30)
            print('MODE: CI temporary synthetic-pin variant; production negative control passed; SHA algorithm unmodified')
        assert source.read_text() == production, 'production source changed during fixture'


if __name__ == '__main__':
    main()
