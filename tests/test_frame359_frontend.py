"""Reject false first-frame and callback-stack associations."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from frame359_frontend import callback_trace, PREFIX, STACK


class CallbackTraceTest(unittest.TestCase):
    entered, held, left = 232_991_402, 233_030_001, 233_249_686
    ident = 22
    active = PREFIX+'active input=1 ca_commit=1 ca_flush=1 max_rows=8192\n'
    config = STACK.PREFIX+'active '+' '.join(f'{k}={v}' for k,v in STACK.CALLBACK_CONFIG.items())+'\n'

    def fixture(self, *, sample=True, watch_ident=22, held=None, stale=False):
        held = self.held if held is None else held
        parsed = {'rows':[
            dict(kind='input-begin',id=self.ident,flags=0,us=self.entered-5),
            dict(kind='input-end',id=self.ident,us=self.left,returned=True)]}
        original = PREFIX+f'input id={self.ident} entered_us={self.entered} left_us={self.left} returned=1\n'
        log = self.active + self.config + original
        if sample:
            watch = (watch_ident<<32)|self.entered
            row = dict(sample=1,requested_us=held-2,us=held-1,held_us=held,resumed_us=held+100,
                watch=watch,stopped_watch=0 if stale else watch,suspend=0,state=STACK.NOT_CALLED if stale else 0,
                read=STACK.NOT_CALLED if stale else 0,resume=0,stop=2 if stale else 5,frames=0 if stale else 1,
                valid=int(not stale),pc=0x180001000,lr=0x180002000,sp=0x10000,fp=0x10020)
            log += STACK.PREFIX+' '.join(f'{k}={row[k]:x}' if k in STACK.HEX else f'{k}={row[k]}' for k in STACK.SAMPLE_KEYS)+'\n'
            if not stale:
                log += ''.join(f'{STACK.PREFIX}frame sample=1 index={i} address={address:x} image=QuartzCore+0x100\n'
                    for i,address in enumerate([row['pc'],row['lr'],0x180003000]))
        return log,parsed

    def test_exact_callback_and_original_timing(self):
        log,parsed = self.fixture()
        log += PREFIX+'ca method=flush entered_us=233200000 left_us=233200100 returned=1\n'
        observed = callback_trace(log,parsed)
        self.assertEqual(observed['calls'][22]['wrapper_to_call_us'],5)
        self.assertEqual(observed['linked_stacks'][0]['input_id'],22)
        self.assertEqual(observed['CA_API_calls'][0]['method'],'flush')

    def test_wrong_callback_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'does not name'):
            callback_trace(*self.fixture(watch_ident=21))

    def test_stale_watcher_and_post_callback_sample_do_not_join(self):
        self.assertFalse(callback_trace(*self.fixture(stale=True))['linked_stacks'])
        self.assertFalse(callback_trace(*self.fixture(held=self.left))['linked_stacks'])

    def test_entry_without_matching_end_rejected(self):
        log,parsed = self.fixture(sample=False)
        parsed['rows'].pop()
        with self.assertRaisesRegex(ValueError,'wrapper identity'):
            callback_trace(log,parsed)

    def test_sample_for_inactive_or_incomplete_capture_rejected(self):
        log,parsed = self.fixture()
        with self.assertRaisesRegex(ValueError,'lacks activation'):
            callback_trace(log.replace(self.active,''),parsed)
        with self.assertRaisesRegex(ValueError,'stack capture is incomplete'):
            callback_trace('\n'.join(log.splitlines()[:-1]),parsed)


if __name__=='__main__':
    unittest.main()
