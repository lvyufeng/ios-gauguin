"""Check SwapWait joins around acceptance and lock contention."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from frame344_log import Event, ISSUE, SWAP, WRITER
from frame370_swap_wait import SWAP_WAIT, decode, join_issue


def receipt(sequence, tick, kind, state, generation=0, accepted=0):
    return Event(sequence, tick, kind, 24, state, 20_000, generation, accepted)


class SwapWaitTest(unittest.TestCase):
    def setUp(self):
        self.swap = Event(3,50,SWAP,25,0,24,1,(48<<32)|7)

    def test_wait_before_accept_and_while_copying(self):
        result = decode({SWAP:[self.swap],SWAP_WAIT:[
            receipt(1,20,SWAP_WAIT,0,accepted=24),receipt(2,22,SWAP_WAIT,5),
            receipt(4,51,SWAP_WAIT,1,25,25),receipt(5,56,SWAP_WAIT,4,25,25)]})
        self.assertEqual([r['accepted_before_sample'] for r in result['samples']],
                         [False,False,True,True])
        self.assertEqual(result['states'],{'outside_retained_slots':1,'lock_busy':1,'pending':1,'copying':1})
        self.assertEqual(result['timeout_scalars'],{20_000:4})

    def test_wrong_generation_and_impossible_early_live_state(self):
        for sample in (receipt(4,52,SWAP_WAIT,3,24,25), receipt(1,20,SWAP_WAIT,3,25,25)):
            with self.subTest(sample=sample), self.assertRaises(ValueError):
                decode({SWAP:[self.swap],SWAP_WAIT:[sample]})

    def test_lock_busy_does_not_report_a_snapshot(self):
        with self.assertRaisesRegex(ValueError,'has no snapshot'):
            decode({SWAP:[self.swap],SWAP_WAIT:[receipt(4,52,SWAP_WAIT,5,25,25)]})

    def test_unaccepted_and_truncated_trace(self):
        row = receipt(4,52,SWAP_WAIT,0,accepted=25)
        with self.assertRaisesRegex(ValueError,'unbounded'):
            decode({SWAP:[self.swap],SWAP_WAIT:[row]*385})
        output = decode({SWAP:[self.swap],SWAP_WAIT:[Event(4,52,SWAP_WAIT,28,0,100,0,25)]})
        self.assertIsNone(output['samples'][0]['accepted_before_sample'])

    def test_exact_issue_position(self):
        rows = {SWAP:[self.swap],SWAP_WAIT:[
            receipt(4,51,SWAP_WAIT,1,25,25),receipt(7,65,SWAP_WAIT,2,25,25)],
            ISSUE:[Event(5,60,ISSUE,9,0,8,2,17)],
            WRITER:[Event(6,61,WRITER,9,0,7,(25<<32)|7,48)]}
        output = join_issue(decode(rows),rows)
        self.assertEqual(output['issue_positions']['pending'],{'before_native_issue':1})
        self.assertEqual(output['issue_positions']['issued'],{'after_native_issue':1})


if __name__ == "__main__":
    unittest.main()
