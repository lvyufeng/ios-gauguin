#!/usr/bin/env python3
"""Exercise the flip receipt gates without sending device commands."""

from collections import defaultdict
from importlib import import_module
import struct

import frame344_log as trace
from frame354_display import VALIDATE
from frame381_page_flip import exercise

scope = import_module('prepare-frame382')
runner = import_module('run-frame382-trial')


def check_fixtures():
    raw = '''SWEET F382 BACKING: first=a8f30000 second=a9914000 bytes=10371072
SWEET F382 P 1 1 95
SWEET F382 I 1 9 1 98
SWEET F382 L 1 10 1 105
SWEET F382 P 2 2 194
SWEET F382 I 2 10 2 196
SWEET F382 L 2 11 2 206
SWEET F382 I 0 11 0 296
SWEET F382 L 0 12 0 305'''
    rows = defaultdict(list)

    def add(kind, id, tick, flags, a, b, c):
        rows[kind].append(trace.Event(1,tick,kind,id,flags,a,b,c))

    add(trace.ATTEMPT,1,78,0,3,3,1)
    add(VALIDATE,1,79,1,2,4,4)
    add(trace.COPY,2,96,0,81,95,trace.FRAME_BYTES)
    add(trace.RESULT,1,97,0,1,trace.FRAME_BYTES,0)
    add(trace.ATTEMPT,2,109,0,4,4,1)
    add(VALIDATE,2,111,1,3,8,8)
    add(trace.COPY,3,195,0,113,194,trace.FRAME_BYTES)
    add(trace.RESULT,2,196,0,1,trace.FRAME_BYTES,0)
    add(trace.VBLANK,10,111,1,100,110,0)
    add(trace.VBLANK,11,212,1,200,211,0)
    add(trace.VBLANK,12,311,1,300,310,0)
    good = runner.latch_receipts(raw,rows)
    assert good['latched_private']==2 and good['original_front_latched']
    invalid = (
        raw.replace('I 2 10 2','I 2 10 1'),
        raw.replace('L 1 10','L 1 9'),
        raw.replace('P 1 1 95','P 1 1 94'),
        raw.replace('L 0 12 0 305',''),
        raw.replace('L 1 10 1 105','L 1 10 1 120'),
        raw+'\nSWEET F382 STOP: uncertain-latch front=1 next=2 scan=10',
    )
    for sample in invalid:
        try:
            runner.latch_receipts(sample,rows)
        except ValueError:
            continue
        raise AssertionError('accepted invalid flip capture')
    return 1+len(invalid)


def check():
    scope.baseline()
    manifest = scope.load(scope.BASE/'native-kernel/build-manifest.json')
    scope.require(manifest['state']=='0382-native-ARM64-linked' and
                  manifest['input_pins'][str(scope.PATCH)]==scope.sha(scope.PATCH),'native build differs')
    helper = import_module('package-frame344')
    image = scope.load(scope.BASE/'frame382-image.json')
    _,_,payload,_ = helper.parts(scope.Path(image['image']).read_bytes())
    off,size = struct.unpack_from('<2Q',payload,32)
    request = payload[off:off+size].index(b'DPUBufferRequest\0')
    assert not any(payload[off+request+36:off+request+68])
    assert len(payload)-0x200000-((off+size+0x3fff)&~0x3fff) == 2*0x9e4000+0x4000
    return dict(state='0382-phase-ownership-and-receipts-passed-on-host',device_commands=0,
        patch_sha256=scope.sha(scope.PATCH),fixture_cases=check_fixtures(),lifetime=exercise())


if __name__=='__main__':
    value = check()
    scope.save(scope.HOST,value)
    print('Page-flip receipt fixtures',value['fixture_cases'])
