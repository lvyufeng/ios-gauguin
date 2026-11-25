import unittest

import frame345_log as report
from test_frame344_log import sample


class Frame345(unittest.TestCase):
    def test_hardware_rate_and_exact_software_link(self):
        result = report.analyze(*sample(scan345=True))
        self.assertEqual(result['core_linked_layers'], 1)
        self.assertEqual(result['attempts'][0]['layers'][0]['ticket'], 2)
        self.assertEqual(result['dpu_probe']['checkpoints'][0]['timing_engine_enable'], 0)
        rate = result['hardware']
        self.assertEqual(rate['changed'], 39)
        self.assertEqual(rate['unknown'], 0)
        self.assertTrue(rate['complete_crc_coverage'])
        self.assertLess(rate['scanout_content_fps_bounds'][0], 60)
        self.assertGreater(rate['scanout_content_fps_bounds'][1], 60)
        self.assertEqual(len(rate['windows']), 26)

    def test_incomplete_crc_bounds_and_repeats(self):
        for fault in ('moving-crc','missing-crc','repeat','gap'):
            with self.subTest(fault=fault):
                rate = report.analyze(*sample(fault,scan345=True))['hardware']
                if fault == 'repeat':
                    self.assertEqual(rate['repeated'], 1)
                    self.assertLess(rate['scanout_content_fps_bounds'][1],60)
                elif fault == 'gap':
                    self.assertIsNone(rate['hardware_refresh_hz_bounds'])
                else:
                    self.assertEqual(rate['unknown'],2)
                    self.assertIsNone(rate['scanout_content_fps_bounds'])
                    self.assertIsNotNone(rate['scanout_partial_coverage_fps_bounds'])

    def test_route_guard_exposes_which_reads_were_reached(self):
        text = (
            'SWEET F345 G: poll=1 gate=2 seen=1 display=1 gcc=80000001 ahb=0 mdp=0 rev=0 live=0 en=0 counter=0 hsync=0 period=0 start=0 end=0\n'
            'SWEET F345 DPU: stopped=route polls=530 configured=0 restored=1 gate=2\n'
        )
        state = report.probe(text)
        self.assertEqual(state['gate'],'gcc-ahb-halted')
        first = state['checkpoints'][0]
        self.assertEqual(first['gcc'],0x80000001)
        self.assertIsNone(first['ahb'])
        self.assertIsNone(first['revision'])

    def test_nonzero_misr_preimage_leaves_readonly_refresh(self):
        text,_,_ = sample(scan345=True)
        text = text.replace('configured=1','configured=0').replace('preimage=0','preimage=1')
        import frame344_log as frames
        rows,strokes,numer,denom=frames.parse(text)
        rows[frames.CRC]=[]
        result=report.hardware(report.probe(text),rows,strokes,[],numer,denom)
        self.assertIsNotNone(result['hardware_refresh_hz_bounds'])
        self.assertIsNone(result['scanout_content_fps_bounds'])
        self.assertFalse(result['complete_crc_coverage'])

    def test_counter_receipt_required_for_restored_crc(self):
        text, joins, core = sample(scan345=True)
        arm = 'SWEET F346 COUNTER: arm poll=2 preimage=0 readback=3\n'
        cleanup = 'SWEET F346 COUNTER: cleanup poll=33000 readable=1 before=3 after=0\n'
        text = text.replace('SWEET F345 CRC:', arm + 'SWEET F345 CRC:')
        text = text.replace('SWEET F345 DPU:', cleanup + 'SWEET F345 DPU:')

        result = report.analyze(text, joins, core)
        self.assertTrue(result['dpu_probe']['frame_line_counter']['restored'])
        self.assertTrue(result['hardware']['complete_crc_coverage'])

        for replacement in ('readable=1 before=3 after=3', 'readable=0 before=ffffffff after=ffffffff'):
            damaged = text.replace('readable=1 before=3 after=0', replacement)
            result = report.analyze(damaged, joins, core)
            self.assertFalse(result['dpu_probe']['frame_line_counter']['restored'])
            self.assertIsNotNone(result['hardware']['hardware_refresh_hz_bounds'])
            self.assertIsNone(result['hardware']['scanout_content_fps_bounds'])

        for damaged in (text.replace(cleanup, ''), text.replace(arm, arm + arm),
                        text.replace(arm, arm.replace('readback=3', 'readback=0')),
                        text.replace(arm, arm.replace('poll=2', 'poll=51')),
                        text.replace(cleanup, cleanup.replace('poll=33000', 'poll=32999'))):
            with self.assertRaises(ValueError):
                report.probe(damaged)

    def test_wrong_crc_phase_cannot_pass(self):
        text,joins,core=sample(scan345=True)
        text=text.replace(' 177 81000301',' 700 81000301')
        rate=report.analyze(text,joins,core)['hardware']
        self.assertIsNone(rate['scanout_content_fps_bounds'])
        self.assertIn('sampling phase',rate['reason'])

    def test_read_only_counts_can_measure_refresh_without_crc(self):
        import frame344_log as frames
        text,_,_ = sample(scan345=True)
        text = text.replace('live=1 en=0 counter=3','live=1 en=1 counter=0')
        rows,strokes,numer,denom = frames.parse(text)
        first = rows[frames.VBLANK][0]
        last = rows[frames.VBLANK][-1]
        readonly = (f'SWEET F347 RO: samples=20000 first_frame={first.id} first_line=0 '
                    f'last_frame={last.id} last_line=1000\n')
        with self.assertRaisesRegex(ValueError,'unexpected write receipt'):
            report.probe(text+'\n'+readonly)
        text = '\n'.join(line for line in text.splitlines() if not line.startswith('SWEET F345 CRC:'))
        state = report.probe(text.replace('configured=1','configured=0')+'\n'+readonly)
        with self.assertRaisesRegex(ValueError,'read-only frame edges'):
            report.hardware(state,rows,strokes,[],numer,denom)
        rows[frames.CRC]=[]
        rate = report.hardware(state,rows,strokes,[],numer,denom)
        self.assertIsNotNone(rate['hardware_refresh_hz_bounds'])
        self.assertIsNone(rate['scanout_content_fps_bounds'])


if __name__=='__main__':
    unittest.main()
