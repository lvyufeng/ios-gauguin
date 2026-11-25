"""Negative controls for untrusted/offline CA readback receipts, not GPU proof."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from metal_ca_log import PREFIX as P, SCENES, cpu_image, fnv64, qualify_ca_log

BUILD = '123456789abcdef012345678'


def fixture():
    lines = [P + f'begin build={BUILD} delay=90 scope=root-offscreen-real-CARenderer-not-desktop',
             P + 'device=fixture seed=42 maxBO=67108864 queueSlots=4',
             P + 'CA-ABI OS=20H392 class_methods=1 instance_methods=6 PASS']
    for phase in ['before-delay', 'opened', *SCENES, 'CA-scenes-completed', 'after-resource-release']:
        lines.append(P + f'memory phase={phase} active=128 inactive=128 hard=1 footprint=1048576')
    for i, scene in enumerate(SCENES):
        data = cpu_image(scene)
        for row in range(64):
            lines.append(P + f'CA-readback scene={scene} row={row} hex=' + data[row*256:(row+1)*256].hex())
        tolerance = 2 if scene == 'alpha' else 1
        lines.append(P + f'CA-pixels scene={scene} pixels=4096 tolerance={tolerance} max_error=0 hash={fnv64(data)} PASS')
        lines.append(P + f'CA-draws scene={scene} before={i} after={i+1} omitted=0 PASS')
    lines += [P + 'ownership reacquired=1 closed=1 PASS',
              P + f'RESULT PASS build={BUILD} seed=42 scenes=5 pixels=20480 explicit_jobs=10 exact_CA=1 discovery=0 UI=0']
    return '\n'.join(lines) + '\n'


class Readbacks(unittest.TestCase):
    def test_all_channels_compared(self):
        result = qualify_ca_log(fixture(), '', BUILD)
        self.assertEqual(result['compared_channels'], 81920)
        self.assertEqual(result['accepted_CA_draws'], 5)
        self.assertFalse(result['desktop_qualified'])

    def test_refuse_missing_duplicate_stale_and_false_success(self):
        good = fixture()
        row = next(line for line in good.splitlines() if 'CA-readback scene=image row=17 ' in line)
        cases = [good.replace(row + '\n', ''), good + row + '\n',
                 good.replace(BUILD, 'f' * 24), good.replace('hard=1', 'hard=0', 1),
                 good.replace('footprint=1048576', 'footprint=134217729', 1),
                 good.replace('after=1 omitted=0', 'after=0 omitted=0', 1),
                 good.replace('omitted=0', 'omitted=1', 1),
                 good.replace('ownership reacquired=1', 'ownership reacquired=0'),
                 good.replace('explicit_jobs=10', 'explicit_jobs=9'),
                 good.replace('device=fixture seed=42', 'device=fixture seed=43'),
                 good.replace('tolerance=1', 'tolerance=2', 1),
                 good.replace('max_error=0', 'max_error=1', 1)]
        corrupt = row[:-2] + ('00' if row[-2:] != '00' else 'ff')
        cases.append(good.replace(row, corrupt))
        summary = next(line for line in good.splitlines() if 'CA-pixels scene=image ' in line)
        cases.append(good.replace(summary, summary.replace('hash=', 'hash=0')))
        for case in cases:
            with self.subTest(case=cases.index(case)):
                with self.assertRaises(ValueError):
                    qualify_ca_log(case, '', BUILD)
        with self.assertRaises(ValueError):
            qualify_ca_log(good, P + 'FAIL stage=driver', BUILD)

    def test_prelude_draws_are_separate_from_actual_CA_draws(self):
        import re
        text = re.sub(r'before=(\d+) after=(\d+) omitted=0',
                      lambda m: f'before={int(m[1])+4} after={int(m[2])+4} omitted=0', fixture())
        result = qualify_ca_log(text, '', BUILD, initial_draws=4)
        self.assertEqual(result['accepted_CA_draws'], 5)
        self.assertEqual(result['prelude_draws'], 4)
        with self.assertRaises(ValueError):
            qualify_ca_log(text, '', BUILD)
        with self.assertRaises(ValueError):
            qualify_ca_log(fixture(), '', BUILD, initial_draws=4)


if __name__ == '__main__':
    unittest.main()
