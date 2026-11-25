#!/usr/bin/env python3
"""Run 0375 and qualify native FrameInfo against CRC after read-back."""

from importlib import import_module

from frame344_log import VBLANK, SWAP, indexed
from frame374_native_ca import decode
from frame375_receipts import align_requests, since_callback

scope = import_module('prepare-frame375')
runner = import_module('run-frame374-trial')


def add_receipts(native, scoped, onset, raw, rows, result, measured):
    clock = native['clock']
    events = decode(raw,clock['start'],clock['end'])
    n,d = clock['numer'],clock['denom']
    edges = indexed(rows[VBLANK],lambda row:row.id,'physical edge')
    feedback = align_requests(events,native['scans'],native['matches'],rows[SWAP],edges,n,d)
    handoff = since_callback(events,native['matches'],scoped['frontend_cutoffs'],onset,n,d)
    native.update(frame_info_receipts=feedback,callback_to_render=handoff)
    result.update(platform_frame_info=feedback,callback_to_render={k:v for k,v in handoff.items() if k!='rows'})
    return measured and all(item['FrameInfo_roundtrip'] for item in feedback['active'].values())


if __name__ == '__main__':
    raise SystemExit(runner.main(scope,extend_native=add_receipts))
