"""Check exact accepted-swap joins and refusal of inconsistent wire receipts."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from frame344_log import Event, ISSUE, READY, SWAP, SWAP_TIMING, WRITER
from frame369_swap_timing import decode, observe


class SwapTimingTest(unittest.TestCase):
    def setUp(self):
        self.swap = Event(2,200,SWAP,18,0,18,1,(12<<32)|5)
        self.timing = Event(3,201,SWAP_TIMING,18,0,170,8|1,self.swap.c)
        self.rows = {SWAP:[self.swap],SWAP_TIMING:[self.timing],
            WRITER:[Event(1,150,WRITER,24,0,5,0,8)],ISSUE:[],READY:[]}

    def test_report_exact_observed_writer_and_cutoff(self):
        misses = {'details':[dict(next_swap={'generation':18},next_swap_within_stroke_tail=True,
            deadline_ns=180,stroke=4,scan=280)]}
        r = observe(self.rows,1,1,misses)
        self.assertEqual(r['begin_to_accept_p50_ns'],30)
        self.assertEqual(r['no_swap_cutoff_position_warm'],{'begin_before_cutoff':1})
        self.assertEqual(r['unclaimed_observed_writer'],1)
        self.assertEqual(r['swap_timing'][0]['observed_version_writer']['native_fence'],24)

    def test_missing_begin_and_advanced_version(self):
        swap = Event(2,200,SWAP,18,0,18,1,(16<<32)|5)
        timing = Event(3,201,SWAP_TIMING,18,1,0,8|3,swap.c)
        record, = decode({SWAP:[swap],SWAP_TIMING:[timing]},1,1)
        self.assertIsNone(record['begin_to_accept_ns'])
        self.assertTrue(record['advanced_past_pending'])

    def test_refuse_malformed_timing_join(self):
        invalid = [
            Event(3,201,SWAP_TIMING,19,0,170,9,self.swap.c),
            Event(3,201,SWAP_TIMING,18,0,201,9,self.swap.c),
            Event(3,201,SWAP_TIMING,18,0,170,13,self.swap.c),
            Event(3,201,SWAP_TIMING,18,0,170,9,self.swap.c+1),
        ]
        for row in invalid:
            with self.subTest(row=row), self.assertRaises(ValueError):
                decode({SWAP:[self.swap],SWAP_TIMING:[row]},1,1)

    def test_refuse_missing_prefix_record(self):
        self.rows[SWAP].append(Event(4,300,SWAP,19,0,19,1,(16<<32)|5))
        with self.assertRaisesRegex(ValueError,'exact eligible prefix'):
            observe(self.rows,1,1,{'details':[]})

    def test_refuse_wrong_claimed_version(self):
        self.rows[WRITER].append(Event(4,250,WRITER,25,0,5,18<<32,16))
        with self.assertRaisesRegex(ValueError,'accepted swap writer version'):
            observe(self.rows,1,1,{'details':[]})


if __name__ == "__main__":
    unittest.main()
