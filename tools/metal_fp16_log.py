"""Independently derive and compare every binary16 prelude channel.

The caller must bind these rows to the actual installed probe/kernel/GPU trial.
Matching pixels alone do not certify a complete Metal device or GPU family.
"""
import re
import struct

PREFIX = 'GAUGUIN FP16 '


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def half(value):
    return struct.unpack('<e', struct.pack('<e', value))[0]


def cpu_image(seed):
    # Derive from the actual workload's input expressions, rather than consuming
    # its C expected-bit table, hash helper or embedded shader result.
    colors = ((.5, .25, .75, 1), (1, -.5, .5, 1), (-.5, 1, .25, 1), (.75, .75, 1, 1))
    scale, bias = (.5, 1, 2, .5), (.125, .25, -.125, .5)
    row = bytearray()
    for x in range(64):
        color = colors[((x // 16) + (seed & 3)) & 3]
        for c in range(4):
            vertex = half(half(color[c]) * half(.5))
            fragment = half(half(vertex * half(scale[c])) + half(bias[c]))
            row.extend(struct.pack('<e', fragment))
    return bytes(row) * 64


def fnv64(data):
    result = 14695981039346656037
    for byte in data:
        result = ((result ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f'{result:016x}'


def qualify_fp16_log(stdout, stderr='', expected_seeds=None, activation=True):
    require('FP16-' not in '\n'.join(x for x in stderr.splitlines() if ' FAIL ' in x), 'FP16 probe failed')
    blocks, current, activated = [], None, []
    for line in stdout.splitlines():
        if not line.startswith(PREFIX):
            continue
        value = line[len(PREFIX):]
        begin = re.fullmatch(r'begin seed=(\d+) width=64 height=64 format=115 GPU_jobs=1', value)
        row = re.fullmatch(r'row=(\d+) hex=([0-9a-f]{1024})', value)
        end = re.fullmatch(r'pixels=4096 half_channels=16384 hash=([0-9a-f]{16}) PASS', value)
        enable = re.fullmatch(r'activated=1 seed=(\d+) hash=([0-9a-f]{16}) public_families=0 root_only=1 PASS', value)
        if begin:
            require(current is None and not activated and len(blocks) < 4, 'duplicate/interleaved prelude')
            seed = int(begin[1]); require(0 <= seed < 1 << 32, 'invalid prelude seed')
            current = dict(seed=seed, rows=[])
        elif row:
            require(current is not None and int(row[1]) == len(current['rows']) < 64, 'missing/duplicate/reordered half row')
            current['rows'].append(bytes.fromhex(row[2]))
        elif end:
            require(current is not None and len(current['rows']) == 64, 'incomplete half image')
            raw = b''.join(current['rows']); want = cpu_image(current['seed'])
            require(raw == want and len(raw) == 32768, 'independent binary16 pixel mismatch')
            require(end[1] == fnv64(raw), 'half summary digest mismatch')
            blocks.append(dict(seed=current['seed'],hash=end[1],pixels=4096,channels=16384,bytes=32768,GPU_jobs=1,render_draws=4))
            current = None
        elif enable:
            require(activation and current is None and len(blocks) == 1 and not activated, 'activation before readback or duplicated')
            require(int(enable[1]) == blocks[0]['seed'] and enable[2] == blocks[0]['hash'], 'activation receipt mismatch')
            activated.append(line)
        else:
            raise ValueError('unknown or malformed native half receipt')
    require(current is None and blocks, 'missing/incomplete half prelude')
    if expected_seeds is not None:
        require([r['seed'] for r in blocks] == list(expected_seeds), 'unexpected/repeated prelude seeds')
    if activation:
        require(len(blocks) == len(activated) == 1, 'scoped activation missing')
        block = blocks[0]
        marker = (f"GAUGUIN METAL235 nativeFP16 enabled seed={block['seed']} pixels=4096 "
                  f"hash={block['hash']} root-only families=0")
        require(sum(line.endswith(marker) for line in stderr.splitlines()) == 1, 'driver activation missing/duplicate')
    else:
        require(not activated, 'unexpected activation in Mac oracle')
    return dict(state='independent-native-half-pixels-compared',blocks=blocks,
                compared_pixels=4096*len(blocks),compared_channels=16384*len(blocks),
                capability_activated=activation,public_family_certified=False,UI_qualified=False)
