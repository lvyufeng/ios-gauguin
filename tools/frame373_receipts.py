"""Decode the bounded unmatched-receive details alongside the paired wire."""

import re

from frame344_log import require
from frame372_transport import decode

UNMATCHED = re.compile(r'^SWEET F373 U: ordinal=(\d+) tick=(\d+) tid=(\d+) id=(\d+) '
                       r'reason=(\d+) copyout=(\d+) result=(\d+)$')
REASONS = {1:'no_matching_live_send', 2:'message_id_changed', 3:'missing_post', 4:'slot_busy'}


def decode_with_unmatched(raw, numer, denom, **wire_options):
    capture = decode(raw,numer,denom,**wire_options)
    start,end = capture['window_ticks']
    unmatched = []
    for line in raw.splitlines():
        if 'SWEET F373 U:' not in line:
            continue
        match = UNMATCHED.fullmatch(line)
        require(match is not None, 'malformed unmatched receive detail')
        ordinal,tick,tid,message,reason,copyout,result = map(int,match.groups())
        require(ordinal==len(unmatched) and start<=tick<end and 0<tid<1<<64 and
                0<=message<1<<32 and reason in REASONS and 0<=result<1<<32 and
                ((tick<=copyout<end) if copyout else result==0), 'invalid unmatched receive detail')
        outcome = 'outside_capture' if not copyout else 'failed' if result else 'completed'
        unmatched.append(dict(take_tick=tick,receiver_thread=tid,message_id=message,reason=REASONS[reason],
                              copyout_tick=copyout or None,copyout_result=result if copyout else None,
                              outcome=outcome))
    require([r['take_tick'] for r in unmatched]==capture['unmatched_ticks'],
            'unmatched receive details do not cover the bounded count')
    return dict(capture,unmatched_receipts=unmatched)
