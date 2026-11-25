"""Read-only counter evidence and hardware qualification."""

import unittest

import frame344_log as frames
import frame345_log as report
from test_frame344_log import sample


def readonly(text, *, first_frame, last_frame, samples=20_000):
    return '\n'.join(line.replace('configured=1','configured=0') for line in text.splitlines()
                     if not line.startswith('SWEET F345 CRC:')) + (
        f'\nSWEET F347 RO: samples={samples} first_frame={first_frame} first_line=0 '
        f'last_frame={last_frame} last_line=1000\n')


class Frame348Trial(unittest.TestCase):
    def test_motion_is_partitioned_under_stable_control(self):
        t,_,_ = sample(scan345=True)
        t = readonly(t,first_frame=3,last_frame=30,samples=30)
        lane = 'SWEET F348 MOTION: zero=20,17,5,15,3 enabled=10,9,2,8,1 rejected_control=2\n'
        result = report.probe(t+lane)['read_only_counter']['motion']
        self.assertEqual(result['zero']['frame_changes'],5)
        self.assertEqual(result['enabled']['line_changes'],8)
        self.assertEqual(result['rejected_control'],2)
        for bad in (lane+lane, lane.replace('zero=20,17','zero=21,17'),
                    lane.replace('enabled=10,9','enabled=10,10'), lane.replace('rejected_control=2','rejected_control=33000')):
            with self.assertRaises(ValueError):
                report.probe(t+bad)

    def test_only_real_frame_edges_yield_refresh(self):
        t,_,_ = sample(scan345=True)
        rows,strokes,numer,denom = frames.parse(t)
        edges = rows[frames.VBLANK]
        t = readonly(t,first_frame=edges[0].id-1,last_frame=edges[-1].id)
        t += f'SWEET F348 MOTION: zero=20000,19995,{len(edges)},19900,100 enabled=0,0,0,0,0 rejected_control=3\n'
        state = report.probe(t)
        rows[frames.CRC] = []
        result = report.hardware(state,rows,strokes,[],numer,denom)
        self.assertIsNotNone(result['hardware_refresh_hz_bounds'])
        self.assertGreater(sum(len(w['vblank_edges']) for w in result['windows']),0)
        self.assertIsNone(result['scanout_content_fps_bounds'])
        self.assertFalse(result['complete_crc_coverage'])
        rows[frames.VBLANK] = []
        static = t.replace(f'last_frame={edges[-1].id}',f'last_frame={edges[0].id-1}')
        static = static.replace(f'19995,{len(edges)},19900','19995,0,19900')
        state = report.probe(static)
        no_edges = report.hardware(state,rows,strokes,[],numer,denom)
        self.assertIsNone(no_edges['hardware_refresh_hz_bounds'])
        self.assertGreater(state['read_only_counter']['motion']['zero']['line_changes'],0)
