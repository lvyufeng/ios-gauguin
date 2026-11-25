import unittest

import frame349_log as crc
from frame350_queue import clipped_phases
from test_frame349_log import edge, reset


class Frame350(unittest.TestCase):
    def setUp(self):
        self.edges = [edge(i,i) for i in range(1,12)]
        self.gate = dict(polls=500,configured=True,restored=True)
        self.read_one = 'SWEET F350 PRE: read=1 poll=25 frame=4 line=31 streak=3 value=1000000\n'
        self.read_two = 'SWEET F350 PRE: read=2 poll=36 frame=5 line=31 streak=4 value=1000000\n'
        self.arm = 'SWEET F349 ARM: poll=36 frame=5 line=31 streak=4 preimage=1000000 readback=81000101 writes=2\n'
        self.no_writes = reset(owned_before='ffffffff',after='ffffffff',writes=0,readable=0,count=0)

    def receipt(self,text,**gate):
        return crc.misr_receipts(text,dict(self.gate,**gate),self.edges,1,preserve_data_preimage=True)

    def test_same_idle_value_on_distinct_edges_required_then_restored(self):
        answer = self.receipt(self.read_one+self.read_two+self.arm+reset(after='1000000'))
        self.assertTrue(answer['preimage_confirmed'] and answer['qualified'])
        self.assertEqual([r['frame'] for r in answer['preimage_control_reads']],[4,5])
        self.assertEqual(answer['reset']['after'],crc.DATA_INPUT)

    def test_a_zero_cleanup_readback_refuses_fps(self):
        answer = self.receipt(self.read_one+self.read_two+self.arm+reset(after='0'),restored=False)
        self.assertFalse(answer['qualified'])

    def test_zero_or_busy_first_read_prevents_writes(self):
        for raw in ('0','1000100','1000200','81000000'):
            text = self.read_one.replace('value=1000000','value='+raw)
            answer = self.receipt(text+self.no_writes,configured=False)
            self.assertFalse(answer['preimage_confirmed'] or answer['qualified'])
            self.assertEqual(answer['total_writes'],0)

    def test_changed_second_read_prevents_writes(self):
        read_two = self.read_two.replace('value=1000000','value=1000300')
        answer = self.receipt(self.read_one+read_two+self.no_writes,configured=False)
        self.assertFalse(answer['preimage_confirmed'] or answer['qualified'])

    def test_same_frame_or_missing_read_cannot_arm(self):
        for read_two in ('',self.read_two.replace('frame=5','frame=4').replace('streak=4','streak=3')):
            with self.assertRaisesRegex(ValueError,'two matching idle control reads'):
                self.receipt(self.read_one+read_two+self.arm+reset(after='1000000'))

    def test_reappearing_owned_pattern_after_fault_cannot_reset(self):
        text = self.read_one+self.read_two+self.arm
        observed = self.receipt(text+reset(owned_before='81000301',after='81000301',writes=2,fault=1),
                                restored=False)
        self.assertFalse(observed['qualified'])
        self.assertEqual(observed['reset']['writes'],0)
        with self.assertRaisesRegex(ValueError,'write count'):
            self.receipt(text+reset(after='1000000',fault=1))

    def test_partial_native_phase_keeps_cpu_and_wait_bounds(self):
        phase = dict(begin_ns=100,end_ns=200,wall_ns=100,CPU_lower_ns=65,CPU_upper_ns=90,
                     off_CPU_lower_ns=10,off_CPU_upper_ns=35)
        measured, = clipped_phases(dict(kernel_selector=70,phases=[phase]),{'70':['runtime_issue']},130,180)
        self.assertEqual(measured,dict(phase='runtime_issue',overlap_ns=50,cpu_lower_ns=15,cpu_upper_ns=50,
                                       off_cpu_lower_ns=0,off_cpu_upper_ns=35))


if __name__ == "__main__":
    unittest.main()
