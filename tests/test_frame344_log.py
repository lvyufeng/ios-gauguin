import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import frame344_log as frames


def sample(fault=None, *, scan345=False):
    start = 120_000_000_000
    stop = start + 45_000_000_000
    first = start + 1_000_000_000
    events = []
    marks = []
    def put(kind, tick, ident, flags=0, a=0, b=0, c=0):
        events.append((tick, kind, ident, flags, a, b, c))

    put(1, start, 1, a=start, b=start, c=1)
    put(frames.TIMING, start+1, 1, a=2480, b=32, c=2431)
    if scan345:
        put(frames.VBLANK,first-100_000_000,8,1,first-100_010_000,first-100_000_000,0)
    for stroke in range(13):
        now = first + 2_000_000_000 * stroke
        marks.extend((
            f'SWEET UI SCRIPT: begin stroke={stroke} tick={now} origin=synthetic',
            f'SWEET UI SCRIPT: end stroke={stroke} tick={now+65_000_000} events=34; HID return only',
        ))
        for i in range(4):
            frame = stroke * 120 + i + 10
            tick = now + 2_000_000 + i * 16_666_667
            put(frames.VBLANK, tick, frame, 2 if fault == 'gap' and frame == 11 else 1,
                tick - 100_000, tick, 8)
            if fault != 'missing-crc' or frame != 11:
                put(frames.CRC, tick+2_000_000, frame, int(fault == 'moving-crc' and frame == 11),
                    frame if fault != 'repeat' or frame != 11 else 10, 375, frames.CRC_CONTROL)

    put(frames.ISSUE, first+1_000_000, 9, a=5, b=7, c=6 if fault=='wrong-fence' else 3)
    put(frames.WRITER, first+1_100_000, 9, a=43)
    put(frames.EOP, first+1_300_000, 9)
    if fault != 'missing-ready':
        put(frames.READY, first+1_400_000, 9)
    put(frames.SWAP, first+3_000_000, 50, a=7, b=1)
    put(frames.ATTEMPT, first+3_100_000, 51, a=50, b=7, c=1)
    put(frames.LOCK, first+4_000_000, 43, 2, first+3_110_000, first+3_990_000, first+3_999_999)
    put(frames.COPY, first+6_000_000, 43, 0, first+4_010_000, first+5_999_999, frames.FRAME_BYTES)
    put(frames.RESULT, first+6_100_000, 51, 1, frames.FRAME_BYTES)
    exact = dict(queue=1, ticket=2, job=4, kernel_token=5, driver_queue=7, driver_fence=3)
    core = dict(queue=1, ticket=2, job=4, core_queue_wait_us=500, start_ns=first)
    lines = [f'SWEET F344 H: count={len(events)} reason=1 lost=0 start={start} end={stop} numer=1 denom=1']
    lines.extend('SWEET F344 E '+' '.join(f'{v:x}' for v in (i, *event))
                 for i, event in enumerate(sorted(events),1))
    lost = int(fault == 'lost')
    lines.extend((f'SWEET F344 F: count={len(events)} lost={lost}',
                  'SWEET F344 DPU: stopped=deadline polls=33000 configured=1 restored=1',
                  'SWEET UI SCRIPT: complete strokes=13 events=442; UI acceptance and physical touch unqualified',
                  *marks))
    if scan345:
        lines.extend(('SWEET F345 G: poll=1 gate=0 seen=1f display=1 gcc=2 ahb=1 mdp=1 rev=60040000 live=1 en=0 counter=3 hsync=49e000c period=2c0000 start=1000 end=2a0000',
                      'SWEET F345 CRC: poll=50 frame=8 preimage=0 line=0',
                      'SWEET F345 DPU: stopped=deadline polls=33000 configured=1 restored=1 gate=0'))
    return '\n'.join(lines), [exact], [core]


class Frame344(unittest.TestCase):
    def test_complete_route(self):
        result = frames.analyze(*sample())
        self.assertTrue(result['frame_trace_complete'])
        self.assertEqual(result['core_linked_layers'], 1)
        self.assertEqual(result['attempts'][0]['layers'][0]['native_fence'], 9)
        self.assertAlmostEqual(result['attempts'][0]['layers'][0]['lock_wait_ns'], 880_000)
        report = result['hardware']
        self.assertTrue(report['complete_crc_coverage'])
        self.assertEqual(report['changed'], 39)
        self.assertEqual(report['possible_copy_overlap'], 1)
        self.assertLess(report['scanout_content_fps_bounds'][0], 60)
        self.assertGreater(report['scanout_content_fps_bounds'][1], 60)
        self.assertFalse(report['uninterrupted_60_fps_observed'])

    def test_repeated_content(self):
        report = frames.analyze(*sample('repeat'))['hardware']
        self.assertEqual(report['repeated'], 1)
        self.assertLess(report['scanout_content_fps_bounds'][1],60)

    def test_crc_failure_retains_refresh_evidence(self):
        for fault in ('missing-crc', 'moving-crc'):
            with self.subTest(fault=fault):
                report = frames.analyze(*sample(fault))['hardware']
                self.assertFalse(report['complete_crc_coverage'])
                self.assertIsNone(report['scanout_content_fps_bounds'])
                self.assertEqual(report['crc_missing'], 2)
                self.assertIn('hardware_refresh_hz_bounds', report)

    def test_counter_gap_withholds_rate(self):
        report = frames.analyze(*sample('gap'))['hardware']
        self.assertIsNone(report['scanout_content_fps_bounds'])
        self.assertIn('counter gap', report['reason'])

    def test_refuses_lost_rows_and_incomplete_or_wrong_fences(self):
        for fault in ('lost','missing-ready','wrong-fence'):
            with self.subTest(fault=fault):
                with self.assertRaises(ValueError):
                    frames.analyze(*sample(fault))


if __name__ == '__main__':
    unittest.main()
