#!/usr/bin/env python3
"""Independently compare raw immutable-task sampler pixels, never infer GPU execution."""
import argparse, json, re, struct
from pathlib import Path

PREFIX = 'GAUGUIN SURFACE237 '
CASES = [('R8', 1, 64), ('RG8', 2, 4032), ('BGRA8', 4, 16448),
         ('RGBA16F', 8, 0), ('RGBA32F', 16, 8192)]

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def fnv(data):
    h = 14695981039346656037
    for b in data:
        h = ((h ^ b) * 1099511628211) & ((1 << 64) - 1)
    return f'{h:016x}'

def expected(seed, index):
    name, bpe, bias = CASES[index]
    pitch = 64*bpe + 64
    source = bytearray((seed + (i+bias)*29 + index*17) & 255 for i in range(64*pitch+13))
    rgba = bytearray()
    for y in range(64):
        for x in range(64):
            bits = (seed ^ (x*13) ^ (y*7) ^ (index*5)) & 15
            channels = [0, 0, 0, 255]
            for c in range(1 if bpe == 1 else 2 if bpe == 2 else 4):
                channels[c] = 255 if bits & (1 << c) else 0
            rgba.extend(channels)
            if bpe <= 2:
                pixel = bytes(channels[:bpe])
            elif bpe == 4:
                pixel = bytes([channels[2], channels[1], channels[0], channels[3]])
            elif bpe == 8:
                pixel = struct.pack('<4H', *(0x3c00 if v else 0 for v in channels))
            else:
                pixel = struct.pack('<4f', *(1.0 if v else 0.0 for v in channels))
            at = y*pitch + x*bpe
            source[at:at+bpe] = pixel
    return bytes(rgba), bytes(source)

def qualify_task_surface_log(stdout, stderr, *, build, seed=None):
    lines = [line[len(PREFIX):] for line in stdout.splitlines() if line.startswith(PREFIX)]
    require(not any(PREFIX in line and 'FAIL' in line for line in stderr.splitlines()), 'native task failure')
    require(len(lines) == 338, 'one complete task block with 320 raw rows required')
    begin = re.fullmatch(r'begin build=([a-f0-9]{24}) seed=(\d+) cases=5', lines[0])
    require(begin and begin[1] == build, 'exact task build identity')
    actual_seed = int(begin[2]); require(0 <= actual_seed <= 0xffffffff, 'seed range')
    require(seed is None or seed == actual_seed, 'same device seed')
    at = 1; compared = 0; results = {}; ids = set()
    for index, (name, bpe, bias) in enumerate(CASES):
        permissions = re.fullmatch(r'permissions case=(\w+) handle=(\d+) gpu_bias=(\d+) bytes=(\d+) flags=(\d+) cpu_write=(\d+) gpu_write=(\d+) fence=(\d+) close=(\d+) uncertain=(\d+) phase=(\w+)', lines[at]); at += 1
        pitch = 64*bpe + 64; size = 64*pitch+13; early = int(index >= 3)
        require(permissions is not None, f'{name} permissions record')
        require(permissions[1] == name and int(permissions[2]) > 0 and
                int(permissions[3]) == bias % 4096 and int(permissions[4]) == size and
                int(permissions[5]) & 2 and list(map(int, permissions.group(6, 7, 8, 9, 10))) == [22, 22, 0, 0, 0] and
                permissions[11] == 'passed', f'{name} exact write refusal/no uncertain DMA')
        case = re.fullmatch(r'case name=(\w+) index=(\d+) id=(\d+) bpe=(\d+) bias=(\d+) pitch=(\d+) bytes=(\d+) early=(\d+)', lines[at]); at += 1
        require(case and case[1] == name and list(map(int, case.group(2, 4, 5, 6, 7, 8))) ==
                [index, bpe, bias, pitch, size, early], f'{name} original layout and lifetime')
        surface = int(case[3]); require(surface > 0 and surface not in ids, 'distinct real surface identities'); ids.add(surface)
        raw = bytearray()
        for y in range(64):
            row = re.fullmatch(r'row case=(\w+) y=(\d+) rgba=([0-9a-f]{512})', lines[at]); at += 1
            require(row and row[1] == name and int(row[2]) == y, f'{name} exact row order {y}')
            raw.extend(bytes.fromhex(row[3]))
        want, source = expected(actual_seed, index)
        require(raw == want, f'{name} actual raw sampler pixels')
        result = re.fullmatch(r'pixels case=(\w+) pixels=4096 hash=([0-9a-f]{16}) source_before=([0-9a-f]{16}) source_after=([0-9a-f]{16}) early=(\d+) full_guard=(\d+) PASS', lines[at]); at += 1
        require(result and result[1] == name and result[2] == fnv(raw) and
                result[3] == result[4] == fnv(source) and int(result[5]) == early and
                int(result[6]) == 1-early, f'{name} source/padding/tail hash and lifetime checks')
        results[name] = dict(pixels=4096, max_error=0, raw_hash=result[2], source_hash=result[3],
                             source_bytes=size, original_task_VA_dropped_before_draw=bool(early))
        compared += 4096
    memory = re.fullmatch(r'memory phase=task-surfaces-completed active=128 inactive=128 hard=1 footprint=(\d+)', lines[at]); at += 1
    require(memory and 0 < int(memory[1]) <= 128 << 20, 'bounded memory checkpoint')
    require(lines[at] == 'end cases=5 pixels=20480 jobs=5 direct=1 immutable=1 PASS', 'task suite completion')
    return dict(state='independent-raw-task-sampler-pixels-compared-not-hardware-correlation', build=build,
                seed=actual_seed, cases=results, compared_pixels=compared, compared_channels=compared*4,
                own_positive_jobs=5, deliberate_write_rejections=5, native_GPU_correlation_required=True,
                hardware_qualified=False, desktop_qualified=False, high_refresh_qualified=False, daily_use_qualified=False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stdout', type=Path); parser.add_argument('stderr', type=Path)
    parser.add_argument('--build', required=True); args = parser.parse_args()
    print(json.dumps(qualify_task_surface_log(args.stdout.read_text(), args.stderr.read_text(), build=args.build), indent=2))
