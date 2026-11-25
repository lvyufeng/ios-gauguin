#!/usr/bin/env python3
"""Replay old cutoff evidence and the 20H392 FrameInfo wire on the host."""

import json
import os
from importlib import import_module
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import frame344_log as frame
import frame374_native_ca as ca
from frame375_receipts import align_requests, since_callback

scope = import_module('prepare-frame375')
old_checks = import_module('check-frame374-native-ca')
require = scope.require

C = r'''
#include <assert.h>
#include "gauguin_frame374_wire.h"

int main(void)
{
    const uint64_t actual = UINT64_C(0x124355675);
    const uint64_t target = UINT64_C(0x123355675);
    uint64_t a[F375_INFO_ARGS];
    f375_values(a, 43, actual, target);
    assert(a[0] == 0x80000003 && a[1] == 43 && a[2] == 0x24355675);
    assert(a[3] == 1 && a[4] == 0x23355675 && a[5] == 1);
    const struct f375_copy copy = {target, actual - 100, 43, 7, 11};
    assert(f375_scan_after_copy(&copy, 7, actual - 200, actual));
    assert(!f375_scan_after_copy(&copy, 6, actual - 200, actual));
    assert(!f375_scan_after_copy(&copy, 7, actual - 200, actual - 100));
    assert(!f375_scan_after_copy(&copy, 7, actual, actual));
    const struct f374_event e = {actual, 25, 43, 7, actual-200, actual, F375_DELIVERY};
    uint8_t row[F374_MAX_ROW] = {0};
    assert(f374_pack(row, actual-1, actual+1, &e, 0) == 34);
    assert(row[0]==1 && row[4]==F375_DELIVERY && row[6]==43 && row[10]==7);
    assert(f374_kind(0x31ca01dd) == F375_ENCODE_BEGIN && f374_kind(0x31ca01de) == F375_ENCODE_END);
    assert(f374_kind(0x31ca0219) == F375_SERVER_THREAD && f374_kind(0x31ca0104) == F375_DID_COMMIT);
}
'''


def source_proof():
    fields = scope.PROVIDER/'frame-info-fields.json'
    iomfb = scope.PROVIDER/'IOMobileFramebuffer-provider-ranges.json'
    quartz = scope.PROVIDER/'QuartzCore-provider-ranges.json'
    upstream = scope.PROVIDER/'upstream-sites.json'
    f = scope.load(fields)
    require(scope.load(iomfb)['uuid']=='afd11f8e008f3276bd72c0e0d96cffa6' and
            scope.load(quartz)['uuid']=='9e40b2eb260c3af1ae45a1a551a8c1b9' and
            f['swap_timestamp_types']==[1,[11,0,2,4,6,8,10]] and
            [row['string'] for row in f['ca_callback_keys'].values()]==
                ['Presentation_time','Requested_presentation'] and
            f['benchmark_keys'][2:4]==['Presentation_time','Requested_presentation'],
            '20H392 FrameInfo and timestamp contract differs')
    keys = ['1882d0f88', '1af223fc4', '1af223114', '1af227bf4', '1af227c60']
    code = {key:scope.PROVIDER/(key+'.asm') for key in keys}
    checks = {
        '1882d0f88':('1882d1384 mov\tw8, #0x1','1882d138c str\tx0, [sp, #0x210]'),
        '1af223fc4':('1af22401c add\tx28, x23, #0x18','1af224064 mov\tx26, x28'),
        '1af223114':('1af223164 ldr\tx22, [x2]','1af223168 ldr\tw20, [x2, #0x8]',
                     '1af22322c tbnz\tw22, #0x1f','1af223248 orr\tx24, x24, x8, lsl #32'),
        '1af227bf4':('1af227c10 mov\tw8, #0x3','1af227c24 mov\tw1, #0x49'),
        '1af227c60':('1af227c8c mov\tw9, #0x40','1af227cb8 mov\tw1, #0x4a'),
    }
    for key in keys:
        text = code[key].read_text()
        require(all(s in text for s in checks[key]), '20H392 exact IOMFB instruction differs')
    scope.save(scope.BASE/'provider-source-check.json',dict(
        supported=['Presentation_time','Requested_presentation'], selectors=[72,73,74],
        swap_tag=1, swap_offset=0, notification_type=3, split_32bit_slots=6,
        input_pins={str(p):scope.sha(p) for p in (fields,iomfb,quartz,upstream,*code.values())}))
    return 6


def model():
    source = scope.BASE/'native-kernel/source/bsd/dev'
    count = old_checks.wire_tests(source)
    with TemporaryDirectory(prefix='frame375-wire-') as name:
        directory = Path(name)
        (directory/'wire.c').write_text(C)
        subprocess.run(['/Library/Developer/CommandLineTools/usr/bin/clang','-std=c11','-O1',
                        '-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk',
                        '-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(source),
                        str(directory/'wire.c'),'-o',str(directory/'wire')],check=True,timeout=60)
        subprocess.run([str(directory/'wire')],check=True,timeout=30)
    accepted = [frame.Event(1,100,frame.SWAP,101,0,14,1,7)]
    edges = {43:frame.Event(2,220,frame.VBLANK,43,1,180,220,0)}
    scans = [dict(workload='ordinary',phase='active',generation=101,frame=43,copy_end_tick=195,
                  vblank_ticks=[196,220])]
    match = [dict(generation=101,client_swap_id=14,
                  system_frame_info=dict(requested_tick=200,actual_tick=220))]
    target = ca.Event(102,13,ca.DRIVER_TARGET,(14,101,200,7))
    delivery = ca.Event(240,9,ca.DRIVER_DELIVERY,(14,43,180,220))
    report = align_requests([target,delivery],scans,match,accepted,edges,625,12)
    require(report['active']['ordinary']==dict(target=1,DPU_actual=1,FrameInfo_roundtrip=1) and
            scans[0]['driver_actual_tick_bounds']==[196,220], 'exact FrameInfo fixture differs')
    for bad in (ca.Event(240,9,ca.DRIVER_DELIVERY,(14,44,180,220)),
                ca.Event(240,9,ca.DRIVER_DELIVERY,(14,43,180,215)),
                ca.Event(240,9,ca.DRIVER_TARGET,(14,101,200,8))):
        try:
            align_requests([target,bad],scans,match,accepted,edges,625,12)
        except ValueError:
            pass
        else:
            raise ValueError('invalid frame, edge or surface was accepted')
    no_port = ca.Event(240,9,ca.DRIVER_DELIVERY,(14,0xe00002d8<<32|43,180,220))
    report = align_requests([target,no_port],scans,match,accepted,edges,625,12)
    require(report['active']['ordinary']==dict(target=1,DPU_actual=1,FrameInfo_roundtrip=0),
            'failed notification was counted as a FrameInfo round trip')
    return count+8


def replay():
    scope.check_reference()
    raw = (scope.REFERENCE/'kernel.log').read_text()
    start,end,n,d = ca.envelope(raw)
    align = scope.load(scope.REFERENCE/'native-CA-scan-alignment-0374.json')
    frontend = scope.load(scope.REFERENCE/'scoped-swap-timing-0374.json')['frontend_cutoffs']
    onset = scope.load(scope.REFERENCE/'onset-and-motion-0374.json')
    report = since_callback(ca.decode(raw,start,end),align['matches'],frontend,onset,n,d)
    require(report['first_warm_stages']==dict(before_render=28,render_before_SwapBegin=3)
            and not report['encode_spans'], '0374 reference cutoff replay differs')
    return report['first_warm_stages']


def preflight():
    env = dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    run = subprocess.run(['/usr/bin/xcrun','xctrace','list','devices'],env=env,capture_output=True,
                         text=True,timeout=30)
    recovery = subprocess.run(['adb','get-state'],capture_output=True,text=True,timeout=10)
    require(recovery.returncode==0 and recovery.stdout.strip()=='recovery', 'phone is not in TWRP')
    scope.save(scope.BASE/'instruments-preflight.json',dict(
        state='native-CA-fallback',xctrace_list_exit=run.returncode,
        license_required='not agreed to the Xcode license' in (run.stdout+run.stderr),
        test_phone_mode='ADB recovery',test_phone_available_in_instruments=False,
        instrument_recording_started=False,device_writes=0,device_boots=0))


def main():
    controls = source_proof()+model()
    replayed = replay()
    preflight()
    raw = (scope.REFERENCE/'kernel.log').read_bytes()
    old_native = sum(len(line) for line in raw.splitlines(keepends=True) if b'SWEET F374 ' in line)
    projected = len(raw)+4096-old_native+4*((ca.WIRE_LIMIT+2)//3)+512*66+256*40+1024
    require(old_native>40000 and projected < 4_194_304,'native provider exceeds the permanent ring')
    result = dict(state='0375-offline-verified',patch_sha256=scope.sha(scope.PATCH),
        native_schema_verified=True,controls=controls,reference_cutoffs=replayed,
        reference_raw_bytes=len(raw),projected_ring_bound=projected,
        device_writes=0,device_boots=0,input_pins=scope.load(scope.BASE/'provider-source-check.json')['input_pins'])
    scope.save(scope.HOST,result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
