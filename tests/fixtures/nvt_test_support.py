"""Public synthetic format fixture; contains no downloaded firmware payload.

Only tests use this builder. Production accepts no hash override. Synthetic
payload CRC values are protocol-model metadata, not computed hardware CRCs.
"""
import hashlib
import os
from pathlib import Path
import struct

FIRMWARE_BYTES = 139264
REAL_SHA256 = '007143e7d0a816e4ef228b5a08bf3132285230a5cd16164e8086696115d60f88'


def synthetic_image():
    data = bytearray(((i * 73) ^ (i >> 7) ^ 0xa5) & 0xff for i in range(FIRMWARE_BYTES))
    data[:256] = bytes(256)
    struct.pack_into('<6I', data, 0, 0x100, 0, 0x13607, 0x18100, 0x27140, 0x439f)
    struct.pack_into('<2I', data, 0x18, 0x15fe9c6d, 0x90fe20f8)
    struct.pack_into('<4I', data, 0xf0, 0x27040, 0xff, 0, 0xb0183db6)
    for end in range(4096, FIRMWARE_BYTES + 1, 4096):
        data[end - 3:end] = bytes(3)
    data[0x1f000:0x1f002] = bytes((0x10, 0xef))
    data[0x20000 - 3:0x20000] = b'NVT'
    return bytes(data)


def add_arguments(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--source-root', type=Path, help='staged XNU containing bsd/dev/gauguin_nvt')
    group.add_argument('--nvt-root', type=Path, help='standalone gauguin_nvt module directory')
    parser.add_argument('--firmware', type=Path, help='optional local real binary; exact pinned SHA256 required')


def module_root(args, here):
    source = args.source_root
    if source is None and args.nvt_root is None and os.environ.get('XNU_SOURCE'):
        source = Path(os.environ['XNU_SOURCE'])
    root = (source / 'bsd/dev/gauguin_nvt') if source else (args.nvt_root or here.parent)
    root = root.resolve()
    if not (root / 'nvt_protocol.c').is_file() or not (root / 'firmware/nvt_firmware.c').is_file():
        raise ValueError(f'missing staged modules: {root}; set --source-root or --nvt-root')
    return root


def fixture(here, name):
    for path in (here / name, here / 'fixtures' / name):
        if path.is_file():
            return path
    raise ValueError(f'missing host fixture {name}')


def input_image(real, scratch):
    if real is not None:
        path = real.resolve()
        data = path.read_bytes()
        if len(data) != FIRMWARE_BYTES or hashlib.sha256(data).hexdigest() != REAL_SHA256:
            raise ValueError('local firmware does not match pinned size/SHA256')
        label = 'local real binary (hash pinned); model is still not hardware qualification'
    else:
        path = scratch / 'synthetic-format.bin'
        data = synthetic_image()
        path.write_bytes(data)
        label = 'synthetic public format fixture; no real firmware required'
    return path, hashlib.sha256(data).hexdigest(), label


def unchanged(path, expected):
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('test input image changed during fixture execution')
