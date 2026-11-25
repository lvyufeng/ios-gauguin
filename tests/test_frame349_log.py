import unittest

import frame344_log as frames
import frame349_log as crc


def edge(number, index):
    tick = 1_000_000+index*16_600_000
    return frames.Event(index+1,tick+120_000,frames.VBLANK,number,1,tick,tick+100_000,31)


def double(sample_slot, sig0, sig1=None):
    if sig1 is None:
        sig1 = sig0
    start = sample_slot.a+9_500_000
    step = (100_000<<40)|(1000<<20)|1500
    return frames.Event(1,start+103_000,frames.CRC,sample_slot.id,2752|(3100<<13),
                        sig0<<32|sig1,start,step)


def reset(*,owned_before='81000301',after='0',writes=4,readable=1,count=1,fault=0):
    return (f'SWEET F349 RESET: poll=500 readable={readable} before={owned_before} '
            f'after={after} writes={writes} fault={fault} pairs={count} not_ready=0 rejected=0\n')


class Frame349(unittest.TestCase):
    def setUp(self):
        self.edges = [edge(i,i) for i in range(1,28)]
        self.slots = {row.id:row for row in self.edges}
        self.gate = dict(polls=500,configured=True,restored=True)
        self.arm = 'SWEET F349 ARM: poll=25 frame=4 line=31 streak=3 preimage=0 readback=81000101 writes=2\n'

    def test_one_setup_one_cleanup(self):
        receipt = crc.misr_receipts(self.arm+reset(),self.gate,self.edges,1)
        self.assertTrue(receipt['qualified'])
        self.assertEqual((receipt['arm']['writes'],receipt['reset']['writes']),(2,2))

    def test_busy_no_writes_and_no_crc(self):
        arm = self.arm.replace('preimage=0 readback=81000101 writes=2','preimage=81000101 readback=81000101 writes=0')
        result = crc.misr_receipts(arm+reset(owned_before='ffffffff',after='ffffffff',writes=0,readable=0,count=0),
                                  dict(self.gate,configured=False),self.edges,1)
        self.assertFalse(result['qualified'])
        self.assertEqual(result['total_writes'],0)

    def test_no_cleanup_write_when_owned_value_has_changed(self):
        result = crc.misr_receipts(self.arm+reset(owned_before='abc',after='abc',writes=2,fault=1),
                                  dict(self.gate,restored=False),self.edges,1)
        self.assertFalse(result['qualified'])
        self.assertEqual(result['reset']['writes'],0)

    def test_failed_setup_readback_is_not_a_measurement(self):
        arm = self.arm.replace('readback=81000101','readback=0')
        result = crc.misr_receipts(arm+reset(owned_before='0',after='0',writes=2,count=0),
                                  dict(self.gate,configured=False),self.edges,1)
        self.assertFalse(result['qualified'])

    def test_arm_refuses_nonadjacent_vblank(self):
        wrong = self.edges[:2]+self.edges[3:]
        with self.assertRaisesRegex(ValueError,'three qualified'):
            crc.misr_receipts(self.arm+reset(),self.gate,wrong,1)

    def test_reset_refuses_unowned_writes(self):
        with self.assertRaisesRegex(ValueError,'write count'):
            crc.misr_receipts(self.arm+reset(owned_before='abc'),self.gate,self.edges,1)

    def test_pair_retains_both_disagreeing_values(self):
        receipt = crc.misr_receipts(self.arm+reset(),self.gate,self.edges,1)
        pair = crc.paired_reads([double(self.slots[6],0,0xf0000000)],self.slots,receipt,1)[6]
        self.assertEqual(pair['signatures'],[0,0xf0000000])
        self.assertFalse(pair['agrees'])

    def test_bad_trace_or_duplicate_pair_refused(self):
        receipt = crc.misr_receipts(self.arm+reset(),self.gate,self.edges,1)
        valid = double(self.slots[6],1)
        for rows in ([double(self.slots[5],1)], [valid,valid], []):
            with self.assertRaises(ValueError):
                crc.paired_reads(rows,self.slots,receipt,1)

    def phase_data(self,lags):
        entries = [(5,10),(12,20),(19,30)]
        copies = [dict(seq=f,start_tick=self.slots[f].a-3_000_000,
                       end_tick=self.slots[f].a-2_000_000) for f,_ in entries]
        signatures = {f+lag:value for (f,value),lag in zip(entries,lags)}
        signature = 0
        records = []
        for frame in self.slots:
            signature = signatures.get(frame,signature)
            records.append(double(self.slots[frame],signature))
        return crc.paired_reads(records,self.slots,dict(arm={'frame':0xfffffffe},pairs=len(records)),1),copies

    def test_calibrates_same_frame_or_one_frame_lag(self):
        for lag in (0,1):
            pairs,copies = self.phase_data([lag]*3)
            qualified = crc.calibrate(self.edges,pairs,copies,1)
            self.assertTrue(qualified['qualified'])
            self.assertEqual(qualified['lag_frames'],lag)

    def test_conflicting_lag_keeps_unknown(self):
        pairs,copies = self.phase_data([0,1,0])
        result = crc.calibrate(self.edges,pairs,copies,1)
        self.assertFalse(result['qualified'])
        self.assertIsNone(result['lag_frames'])

    def test_repeat_and_skipped_interval_accounting(self):
        pairs,copies = self.phase_data([0]*3)
        # The slots for measured output are 3,4,5,7. Missing edge 6 is two unknown intervals.
        rows = [self.slots[i] for i in (3,4,5,7)]
        window = dict(window='active',elapsed_ns_low=66_300_000,elapsed_ns_high=66_500_000,
                      vblank_edges=[dict(frame=x.id) for x in rows])
        base = dict(windows=[window],hardware_refresh_hz_bounds=[60,60.5])
        results = crc.summarize_windows(base,self.edges,pairs,copies,
                                       dict(qualified=True,lag_frames=0),True,1)
        self.assertEqual((results[0]['changed'],results[0]['repeated'],results[0]['unknown']),(1,1,2))
        self.assertIsNone(base['scanout_content_fps_bounds'])
        self.assertIsNotNone(base['scanout_partial_coverage_fps_bounds'])
        self.assertFalse(base['uninterrupted_60_fps_observed'])

    def test_copy_possible_during_scan_is_unknown(self):
        pairs,copies = self.phase_data([0]*3)
        copies.append(dict(seq=99,start_tick=self.slots[4].b,end_tick=self.slots[4].b+900_000))
        window = dict(window='active',elapsed_ns_low=16_500_000,elapsed_ns_high=16_700_000,
                      vblank_edges=[dict(frame=3),dict(frame=4)])
        base = dict(windows=[window],hardware_refresh_hz_bounds=[59.9,60.7])
        result = crc.summarize_windows(base,self.edges,pairs,copies,dict(qualified=True,lag_frames=0),True,1)[0]
        self.assertEqual((result['repeated'],result['unknown'],result['possible_copy_overlap']),(0,1,1))
        self.assertEqual(result['outputs'][0]['overlapping_copies'][0]['seq'],99)


if __name__ == "__main__":
    unittest.main()
