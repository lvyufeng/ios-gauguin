"""Receipt parser negative controls; synthetic data is never GPU proof."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from metal_fp16_log import cpu_image, fnv64, qualify_fp16_log


def fixture(seed=42):
    raw = cpu_image(seed); digest = fnv64(raw)
    rows = [f'GAUGUIN FP16 begin seed={seed} width=64 height=64 format=115 GPU_jobs=1']
    rows += [f'GAUGUIN FP16 row={y} hex=' + raw[y*512:(y+1)*512].hex() for y in range(64)]
    rows += [f'GAUGUIN FP16 pixels=4096 half_channels=16384 hash={digest} PASS',
             f'GAUGUIN FP16 activated=1 seed={seed} hash={digest} public_families=0 root_only=1 PASS']
    stderr = f'GAUGUIN METAL235 nativeFP16 enabled seed={seed} pixels=4096 hash={digest} root-only families=0\n'
    return '\n'.join(rows)+'\n', stderr


class Prelude(unittest.TestCase):
    def test_scoped_activation_matches_full_raw_image(self):
        stdout, stderr = fixture()
        result = qualify_fp16_log(stdout, stderr, expected_seeds=[42])
        self.assertEqual(result['compared_channels'], 16384)
        self.assertTrue(result['capability_activated'])
        self.assertFalse(result['public_family_certified'])

    def test_missing_corrupt_or_premature_activation_refused(self):
        stdout, stderr = fixture()
        lines = stdout.splitlines(); activation = lines[-1]
        corrupt_row = lines[1][:-1] + ('1' if lines[1][-1] != '1' else '2')
        cases = [(stdout.replace(lines[1], corrupt_row, 1), stderr),
                 (stdout.replace(lines[1]+'\n', '', 1), stderr),
                 (stdout.replace('row=1 ', 'row=0 ', 1), stderr),
                 (stdout.replace(activation+'\n', ''), stderr),
                 (activation+'\n'+stdout, stderr), (stdout+activation+'\n', stderr),
                 (stdout.replace('activated=1 seed=42', 'activated=1 seed=43'), stderr),
                 (stdout.replace('public_families=0', 'public_families=1'), stderr),
                 (stdout, ''), (stdout, stderr+stderr),
                 (stdout, stderr.replace('families=0', 'families=1'))]
        for out, err in cases:
            with self.subTest(case=cases.index((out, err))):
                with self.assertRaises(ValueError):
                    qualify_fp16_log(out, err, expected_seeds=[42])


if __name__ == '__main__':
    unittest.main()
