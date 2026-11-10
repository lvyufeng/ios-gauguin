"""Independent CPU comparison of the real CARenderer probe's synthetic pixels.

This module does not accept screenshots, UI correctness or GPU timing as proven.
Its caller must bind the new log tail, installed binary, kernel/service evidence
and device capture to the same trial.
"""
import re

PREFIX = 'GAUGUIN METAL230 '
SCENES = ('opaque', 'image', 'alpha', 'mask', 'updated-image')


def require(ok, why):
    if not ok:
        raise ValueError(why)


def cpu_image(scene):
    require(scene in SCENES, 'unknown scene')
    row = bytearray()
    for x in range(64):
        red = (x // 16) * 64
        green, blue = 192 - red, 192 if scene == 'updated-image' else 64
        if scene == 'opaque':
            green = blue = red
        if scene == 'alpha':
            red, green, blue = red // 2, green // 2, blue // 2
        if scene == 'mask' and not 16 <= x < 48:
            red = green = blue = 0
        row.extend((blue, green, red, 255))
    return bytes(row) * 64


def fnv64(data):
    value = 14695981039346656037
    for byte in data:
        value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f'{value:016x}'


def qualify_pixels(text, prefix=PREFIX):
    raw = {name: [] for name in SCENES}
    checks = {}
    row_order = []
    for line in text.splitlines():
        if line.startswith(prefix + 'CA-readback '):
            match = re.fullmatch(re.escape(prefix) + r'CA-readback scene=([a-z-]+) row=(\d+) hex=([0-9a-f]{512})', line)
            require(match is not None, 'malformed pixel row')
            name, row, data = match.groups()
            require(name in raw and int(row) == len(raw[name]) < 64, 'missing/duplicate/reordered row')
            raw[name].append(bytes.fromhex(data))
            row_order.append((name, int(row)))
        if line.startswith(prefix + 'CA-pixels '):
            match = re.fullmatch(re.escape(prefix) + r'CA-pixels scene=([a-z-]+) pixels=4096 tolerance=([12]) max_error=(\d+) hash=([0-9a-f]{16}) PASS', line)
            require(match is not None, 'malformed pixel summary')
            name, tolerance, maximum, digest = match.groups()
            require(name in raw and name not in checks, 'unknown/duplicate summary')
            checks[name] = (int(tolerance), int(maximum), digest)
    require(row_order == [(name, y) for name in SCENES for y in range(64)], 'incomplete/reordered scene readbacks')
    require(tuple(checks) == SCENES, 'incomplete/reordered pixel summaries')
    results = {}
    for name in SCENES:
        data = b''.join(raw[name])
        want = cpu_image(name)
        require(len(data) == len(want) == 16384, 'wrong readback length')
        tolerance, maximum, digest = checks[name]
        allowed = 2 if name == 'alpha' else 1
        require(tolerance == allowed, 'changed pixel tolerance')
        actual_max = max(abs(a - b) for a, b in zip(data, want))
        require(actual_max <= allowed and maximum == actual_max, 'CPU pixel oracle mismatch')
        require(digest == fnv64(data), 'pixel summary hash mismatch')
        results[name] = dict(pixels=4096, bytes=16384, tolerance=allowed,
                             max_error=actual_max, hash=digest)
    return dict(scenes=results, compared_pixels=20480, compared_channels=81920,
                every_channel_independently_compared=True)


def qualify_ca_log(stdout, stderr, build):
    require(re.fullmatch('[0-9a-f]{24}', build) is not None, 'invalid build identity')
    require('GAUGUIN METAL230 FAIL' not in stdout + stderr, 'probe failed')
    lines = stdout.splitlines()
    begin = PREFIX + f'begin build={build} delay=90 scope=root-offscreen-real-CARenderer-not-desktop'
    require(lines.count(begin) == 1, 'missing/duplicate current CA begin')
    require(lines.count(PREFIX + 'CA-ABI OS=20H392 class_methods=1 instance_methods=6 PASS') == 1, 'CA runtime ABI not accepted')
    memories = []
    for line in lines:
        if line.startswith(PREFIX + 'memory '):
            match = re.fullmatch(re.escape(PREFIX) + r'memory phase=([A-Za-z-]+) active=128 inactive=128 hard=1 footprint=(\d+)', line)
            require(match is not None, 'memory contract missing')
            phase, footprint = match.groups()
            require(0 < int(footprint) <= 128 << 20, 'footprint outside hard limit')
            memories.append((phase, int(footprint)))
    require([name for name, _ in memories] == ['before-delay', 'opened', *SCENES, 'CA-scenes-completed', 'after-resource-release'], 'missing/reordered memory checkpoints')
    result = qualify_pixels(stdout)
    draws = []
    previous = 0
    for line in lines:
        if line.startswith(PREFIX + 'CA-draws '):
            match = re.fullmatch(re.escape(PREFIX) + r'CA-draws scene=([a-z-]+) before=(\d+) after=(\d+) omitted=0 PASS', line)
            require(match is not None, 'invalid draw receipt')
            scene, before, after = match.groups()
            require(int(before) == previous < int(after), 'CA did not encode real draws continuously')
            draws.append(scene)
            previous = int(after)
    require(tuple(draws) == SCENES, 'missing/reordered actual CA draws')
    require(lines.count(PREFIX + 'ownership reacquired=1 closed=1 PASS') == 1, 'GPU owner not released')
    matches = [re.fullmatch(re.escape(PREFIX) + rf'RESULT PASS build={build} seed=(\d+) scenes=5 pixels=20480 explicit_jobs=10 exact_CA=1 discovery=0 UI=0', line) for line in lines if line.startswith(PREFIX + 'RESULT ')]
    require(len(matches) == 1 and matches[0] is not None, 'missing/duplicate exact CA result')
    devices = [re.fullmatch(re.escape(PREFIX) + r'device=.+ seed=(\d+) maxBO=67108864 queueSlots=4', line)
               for line in lines if line.startswith(PREFIX + 'device=')]
    require(len(devices) == 1 and devices[0] is not None and
            devices[0][1] == matches[0][1] and 0 <= int(matches[0][1]) < 1 << 32,
            'device/result seed or cap mismatch')
    result.update(build=build, accepted_CA_draws=previous, explicit_poison_readback_jobs=10,
                  memory_checkpoints=memories, owner_release_qualified=True,
                  desktop_qualified=False, high_refresh_qualified=False, daily_use_qualified=False)
    return result
