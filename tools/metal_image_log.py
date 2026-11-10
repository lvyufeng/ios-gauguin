#!/usr/bin/env python3
"""Independently check raw IMAGE232 rows; driver/service evidence is separate."""
import re

PREFIX = 'GAUGUIN IMAGE232 '
WIDTH = HEIGHT = 64
MASK = (1 << 32) - 1


def need(ok, why):
    if not ok:
        raise ValueError(why)


def _hash(words):
    value = 14695981039346656037
    for word in words:
        for byte in word.to_bytes(4, 'little'):
            value = ((value ^ byte) * 1099511628211) & ((1 << 64) - 1)
    return f'{value:016x}'


def qualify_image_log(stdout, stderr, *, build, core, library):
    """Require all nine jobs and exact raw pixels, without claiming GPU origin."""
    need(re.fullmatch(r'[0-9a-f]{24}', build), 'bad expected build')
    need(all(re.fullmatch(r'[0-9a-f]{64}', h) for h in (core, library)),
         'bad expected artifact hash')
    need('GAUGUIN IMAGE232 FAIL' not in stdout + stderr, 'probe failure')
    need(PREFIX not in stderr, 'protocol records in stderr')
    lines = []
    for line in stdout.splitlines():
        if PREFIX in line:
            need(line.startswith(PREFIX), 'interleaved image record')
            lines.append(line[len(PREFIX):])
    need(len(lines) == 1194, 'missing/extra image records')
    need(lines[0] == f'begin build={build} core={core} library={library} '
         'jobs=9 draws=27 scope=root-core-not-MTLDevice', 'wrong begin identity')
    end = re.fullmatch(r'RESULT PASS build=([0-9a-f]{24}) seed=(\d+) '
                       r'jobs=9 draws=27 compared=110592 raw_pixels=73728 '
                       r'connection_closed=1', lines[-1])
    need(end and end[1] == build, 'missing/mismatched result')
    seed = int(end[2])
    need(seed <= MASK, 'seed overflow')
    at = 1

    def take(pattern, why):
        nonlocal at
        need(at < len(lines) - 1, 'truncated ' + why)
        result = re.fullmatch(pattern, lines[at])
        need(result is not None, 'malformed/reordered ' + why)
        at += 1
        return result

    def memory(phase):
        row = take(r'memory phase=' + phase + r' active=128 inactive=128 '
                   r'hard=1/1 footprint=(\d+)', phase + ' memory')
        need(0 < int(row[1]) <= 128 * 1024 * 1024, 'memory limit/footprint')

    memory('before-delay')
    memory('compiled')
    expected = [0xa5a5a5a5] * (WIDTH * HEIGHT)
    phases = []
    for phase in range(9):
        value = seed ^ ((phase * 0x9e3779b9) & MASK)
        xor = 0x5a17c3e9 ^ (phase * 0x01010101)
        bits = (seed ^ (phase * 5)) & 7
        x0, y0, w, h = (8, 8, 40, 32) if phase % 2 else (0, 0, WIDTH, HEIGHT)
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                expected[y * WIDTH + x] = value ^ (x * 17) ^ (y * 29) ^ bits ^ xor
        colors = [0xff000000 | (255 if v & 1 else 0)
                  | (0xff00 if v & 2 else 0) | (0xff0000 if v & 4 else 0)
                  for v in expected]
        hashes = {}
        for plane, wanted in [('image', expected), ('sample', colors)]:
            actual = []
            for y in range(HEIGHT):
                row = take(rf'row phase={phase} plane={plane} y={y} '
                           r'data=([0-9a-f]{512})', f'{phase}/{plane}/{y} row')
                actual.extend(int(row[1][x:x + 8], 16) for x in range(0, 512, 8))
            need(actual == wanted, f'wrong raw {phase}/{plane} pixels')
            summary = take(rf'pixels phase={phase} plane={plane} compared=4096 '
                           r'hash=([0-9a-f]{16}) PASS', f'{phase}/{plane} summary')
            hashes[plane] = _hash(actual)
            need(summary[1] == hashes[plane], 'raw row hash differs')
        timing = take(rf'phase={phase} mode={phase % 3} seed={value} xor={xor} '
                      rf'bits={bits} draws=3 completed=1 gpu_ns=(-?\d+)', 'phase completion')
        need(-1 <= int(timing[1]) < 1 << 63, 'invalid optional GPU timing')
        phases.append(dict(phase=phase, mode=phase % 3, image_hash=hashes['image'],
                           sample_hash=hashes['sample']))
    fences = []
    for _ in range(9):
        row = take(r'fence queue=(\d+) value=(\d+) complete=1', 'fence')
        queue, fence = map(int, row.groups())
        need(0 < queue <= MASK and 0 < fence <= MASK, 'invalid fence identity')
        fences.append((queue, fence))
    need(len(set(fences)) == 9 and len({q for q, _ in fences}) == 1,
         'missing/duplicate/different-queue fences')
    memory('completed')
    memory('released')
    need(at == len(lines) - 1, 'unconsumed image records')
    return dict(state='qualified232-raw-image-and-sample-rows-only', build=build,
                core_sha256=core, library_sha256=library, seed=seed, jobs=9, draws=27,
                independently_compared_pixels=73728, internal_reported_checks=110592,
                coverage_raw_pixels_available=False, raw_row_hashes=phases,
                fences=fences, memory_hard_MiB=128, connection_closed=True,
                native_service_correlated=False, physical_GPU_qualified=False,
                MTLDevice_qualified=False, desktop_qualified=False)
