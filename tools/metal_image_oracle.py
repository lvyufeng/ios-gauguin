"""Check actual public-Metal oracle rows without trusting the native probe."""
import re


def qualify_image_oracle(text, seed):
    prefix = 'GAUGUIN IMAGE ORACLE '
    def need(ok, why):
        if not ok:
            raise ValueError(why)
    need(type(seed) is int and 0 <= seed < 1 << 32, 'seed bounds')
    lines = text.splitlines()
    need(len(lines) == 1739 and all(r.startswith(prefix) for r in lines), 'oracle framing')
    lines = [r[len(prefix):] for r in lines]
    need(lines[0] == f'begin seed={seed} jobs=9 draws=27 scope=macos-public-Metal', 'oracle identity')
    need(lines[-1] == f'RESULT COMPLETE seed={seed} jobs=9 draws=27 raw_pixels=110592', 'oracle completion')
    at, previous = 1, [0xa5a5a5a5] * 4096
    for phase in range(9):
        image, sample, coverage = [], [], []
        value = seed ^ ((phase * 0x9e3779b9) & 0xffffffff)
        xor = 0x5a17c3e9 ^ (phase * 0x01010101)
        bits = (seed ^ (phase * 5)) & 7
        for i, old in enumerate(previous):
            y, x = divmod(i, 64)
            inside = not phase % 2 or (8 <= x < 48 and 8 <= y < 40)
            word = value ^ (x * 17) ^ (y * 29) ^ bits ^ xor if inside else old
            image.append(word)
            sample.append(0xff000000 | (255 if word & 1 else 0)
                          | (0xff00 if word & 2 else 0) | (0xff0000 if word & 4 else 0))
            coverage.append(0xff000000 if inside else 0xffff0000)
        previous = image
        for name, expected in [('image', image), ('sample', sample), ('coverage', coverage)]:
            actual = []
            for y in range(64):
                row = re.fullmatch(rf'row phase={phase} plane={name} y={y} data=([0-9a-f]{{512}})', lines[at])
                need(row, 'missing/reordered oracle row'); at += 1
                actual.extend(int(row[1][i:i+8], 16) for i in range(0, 512, 8))
            need(actual == expected, f'oracle raw pixels differ: {phase}/{name}')
        need(lines[at] == f'phase={phase} completed=1', 'oracle phase completion'); at += 1
    need(at == len(lines) - 1, 'oracle trailing records')
    return dict(seed=seed, raw_pixels=110592, jobs=9, draws=27,
                scope='public-macOS-Metal-own-MSL-only', A619_qualified=False,
                phone_GPU_qualified=False, desktop_qualified=False)
