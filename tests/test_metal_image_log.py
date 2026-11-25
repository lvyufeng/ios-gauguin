"""Synthetic protocol controls, explicitly not GPU-execution evidence."""
import hashlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from metal_image_log import qualify_image_log

BUILD, CORE, LIBRARY = 'f' * 24, 'a' * 64, 'b' * 64
P = 'GAUGUIN IMAGE232 '


def fixture(seed=0xdeadbeef):
    lines = [f'begin build={BUILD} core={CORE} library={LIBRARY} jobs=9 draws=27 '
             'scope=root-core-not-MTLDevice']
    def memory(phase):
        lines.append(f'memory phase={phase} active=128 inactive=128 hard=1/1 footprint=4194304')
    memory('before-delay'); memory('compiled')
    previous = [0xa5a5a5a5] * 4096
    for phase in range(9):
        a = seed ^ ((phase * 0x9e3779b9) % (1 << 32))
        b = 0x5a17c3e9 ^ (phase * 0x01010101)
        bits = (seed ^ (5 * phase)) & 7
        current = []
        for i, old in enumerate(previous):
            y, x = divmod(i, 64)
            inside = not phase % 2 or (8 <= x < 48 and 8 <= y < 40)
            current.append(a ^ (17 * x) ^ (29 * y) ^ bits ^ b if inside else old)
        previous = current
        sampled = [sum((255 << (8 * c)) if c == 3 or v & (1 << c) else 0
                       for c in range(4)) for v in current]
        for plane, words in [('image', current), ('sample', sampled)]:
            raw = b''.join(v.to_bytes(4, 'little') for v in words)
            fnv = 14695981039346656037
            for byte in raw:
                fnv = ((fnv ^ byte) * 1099511628211) % (1 << 64)
            for y in range(64):
                data = ''.join(f'{v:08x}' for v in words[y * 64:(y + 1) * 64])
                lines.append(f'row phase={phase} plane={plane} y={y} data={data}')
            lines.append(f'pixels phase={phase} plane={plane} compared=4096 hash={fnv:016x} PASS')
        lines.append(f'phase={phase} mode={phase % 3} seed={a} xor={b} bits={bits} '
                     'draws=3 completed=1 gpu_ns=-1')
    lines.extend(f'fence queue=1 value={i} complete=1' for i in range(1, 10))
    memory('completed'); memory('released')
    lines.append(f'RESULT PASS build={BUILD} seed={seed} jobs=9 draws=27 '
                 'compared=110592 raw_pixels=73728 connection_closed=1')
    return '\n'.join(P + line for line in lines) + '\n'


class ImageRows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.good = fixture()

    def qualify(self, text, stderr=''):
        return qualify_image_log(text, stderr, build=BUILD, core=CORE, library=LIBRARY)

    def test_complete_seed_extremes_and_scope(self):
        for seed in (0, 0xffffffff, 0xdeadbeef, 0x12345678):
            r = self.qualify(fixture(seed))
            self.assertEqual(r['seed'], seed)
            self.assertEqual(r['independently_compared_pixels'], 73728)
            self.assertFalse(r['physical_GPU_qualified'])
            self.assertFalse(r['coverage_raw_pixels_available'])

    def test_mutations_are_rejected(self):
        rows = self.good.splitlines()
        variants = [
            '\n'.join(rows[:-1]), '\n'.join(rows[1:]),
            self.good + rows[-1] + '\n', self.good + self.good,
            '\n'.join(rows[:5] + rows[6:]),
            '\n'.join(rows[:5] + [rows[5]] + rows[5:]),
            self.good.replace('active=128', 'active=6', 1),
            self.good.replace('hard=1/1', 'hard=0/0', 1),
            self.good.replace('footprint=4194304', 'footprint=134217729', 1),
            self.good.replace('footprint=4194304', 'footprint=0', 1),
            self.good.replace('phase=1 mode=1', 'phase=1 mode=0', 1),
            self.good.replace('gpu_ns=-1', 'gpu_ns=-2', 1),
            self.good.replace('fence queue=1 value=2', 'fence queue=1 value=1', 1),
            self.good.replace('fence queue=1 value=2', 'fence queue=2 value=2', 1),
            self.good.replace('fence queue=1 value=2', 'fence queue=1 value=0', 1),
            self.good.replace('connection_closed=1', 'connection_closed=0', 1),
            self.good.replace('RESULT PASS build=' + BUILD, 'RESULT PASS build=' + '0' * 24, 1),
            self.good.replace('seed=3735928559 jobs=9', 'seed=4294967296 jobs=9', 1),
            self.good.replace('y=0 data=', 'y=1 data=', 1),
            self.good.replace('data=', 'data=0', 1),
            self.good.replace('data=', 'data=g', 1),
            self.good.replace(P, 'prefix ' + P, 1),
            self.good.replace('raw_pixels=73728', 'raw_pixels=110592', 1),
        ]
        for i, bad in enumerate(variants):
            with self.subTest(mutation=i), self.assertRaises(ValueError):
                self.qualify(bad)

    def test_wrong_pixel_rejects_despite_matching_hash(self):
        rows = self.good.splitlines()
        index = next(i for i, r in enumerate(rows) if 'row phase=0 plane=image y=0 ' in r)
        prefix, data = rows[index].split('data=')
        rows[index] = prefix + 'data=' + f'{int(data[:8], 16) ^ 1:08x}' + data[8:]
        words = [int(r.split('data=')[1][x:x + 8], 16)
                 for r in rows[index:index + 64] for x in range(0, 512, 8)]
        h = 14695981039346656037
        for word in words:
            for b in word.to_bytes(4, 'little'):
                h = ((h ^ b) * 1099511628211) % (1 << 64)
        rows[index + 64] = P + f'pixels phase=0 plane=image compared=4096 hash={h:016x} PASS'
        with self.assertRaisesRegex(ValueError, 'wrong raw'):
            self.qualify('\n'.join(rows))

    def test_failure_and_stderr_protocol_reject(self):
        for error in (P + 'FAIL stage=foo why=bar', P + 'fence queue=1 value=1 complete=1'):
            with self.assertRaises(ValueError):
                self.qualify(self.good, error)


if __name__ == '__main__':
    unittest.main()
