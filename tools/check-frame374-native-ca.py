#!/usr/bin/env python3
"""Verify the packed native CA stream, source schemas and exact scan linkage."""

from collections import Counter
from importlib import import_module
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from types import SimpleNamespace

import frame374_native_ca as ca

scope = import_module('prepare-frame374')
runner = import_module('run-frame374-trial')
require = scope.require
START, END = 5_000_000_000, 5_864_000_000


WIRE = r'''
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include "gauguin_frame374_wire.h"

int main(void)
{
    const uint64_t start = 5000000000, end = 5864000000;
    const uint64_t tid = UINT64_C(0x10100000010);
    const struct f374_event events[] = {
        {start + 10, tid, 0, 23, 0, 0, F374_RENDER_BEGIN},
        {start + 20, tid, 91, 0, 0, 0x1020304, F374_ANNOTATION},
        {start + 23, tid, 0, 0, 0, 0, F374_RENDER_TIME},
        {start + 28, tid, 0, 0, 0, 0, F374_RENDER_END},
        {start + 37, tid, 0, 0, 0, 0, F374_VSYNC},
        {start + 39, tid, 0, 0, 0, 0, F374_VSYNC_UPDATE},
        {start + 500, tid, 91, start + 1, start + 400, start + 350, F374_FRAME_INFO},
        {start + 501, tid, 91, 360, start + 400, start + 1, F374_HITCH},
        {start + 527, tid, 92, UINT32_MAX, UINT32_MAX, UINT32_MAX, F374_FRAME_INFO}
    };
    const unsigned sizes[] = {10, 14, 14, 6, 6, 6, 34, 34, 34};
    const unsigned count = sizeof(sizes) / sizeof(sizes[0]);
    uint8_t scratch[F374_BLOCK * F374_MAX_ROW];
    char encoded[4 * ((sizeof(scratch) + 2) / 3) + 1];
    unsigned used = 0;
    for (unsigned i = 0; i < count; ++i) {
        unsigned packed = f374_pack(scratch + used, start, end, &events[i], 0);
        assert(packed == sizes[i]);
        used += packed;
    }
    assert(f374_kind(0x31ca002c) == F374_FRAME_INFO && f374_kind(0x31ca01e0) == F374_HITCH);
    assert(f374_kind(0x31ca002d) == 0 && f374_kind(0x31cc002c) == 0);
    struct f374_event invalid = events[0];
    invalid.tick = end;
    assert(f374_pack(scratch + used, start, end, &invalid, 0) == 0);
    invalid.tick = start - 1;
    assert(f374_pack(scratch + used, start, end, &invalid, 0) == 0);
    invalid = events[1];
    invalid.a = UINT64_C(0x100000000);
    assert(f374_pack(scratch + used, start, end, &invalid, 0) == 0);
    f372_base64(scratch, used, encoded);
    printf("SWEET F374 H: version=1 active=1 start=%" PRIu64 " end=%" PRIu64 " captured=%u\n", start,end,count);
    printf("SWEET F374 T 0 %" PRIx64 "\n",tid);
    printf("SWEET F374 B 0 %u %s\n",count,encoded);
    printf("SWEET F374 F: rows=%u threads=1 bytes=%u lost=0\n",count,used);
}
'''


def wire_tests(source=None):
    source = source or scope.BASE/'native-kernel/source/bsd/dev'
    with TemporaryDirectory(prefix='frame374-wire-') as name:
        path = Path(name)
        (path/'wire.c').write_text(WIRE)
        subprocess.run(['/Library/Developer/CommandLineTools/usr/bin/clang','-std=c11','-O1',
            '-isysroot','/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk',
            '-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(source),
            str(path/'wire.c'),'-o',str(path/'wire')],check=True,timeout=60)
        fixture = subprocess.check_output([str(path/'wire')],text=True,timeout=30)
    events = ca.decode(fixture,START,END)
    require(Counter(row.kind for row in events)==Counter(range(1,9)) + Counter({ca.FRAME_INFO:1}) and
            events[-2].args==(91,360,START+400,START+1), 'C and Python native CA layouts differ')
    invalid = [
        fixture.replace('active=1','active=0'), fixture.replace('lost=0','lost=1'),
        fixture.replace('captured=9','captured=10'), fixture.replace('rows=9','rows=8'),
        fixture.replace('B 0 9 ','B 1 9 '), fixture.replace('threads=1','threads=2'),
        fixture.replace('T 0 ','T 1 '), fixture.replace('B 0 9 ','B 0 9 !'),
        fixture.replace('bytes=158','bytes=159'), fixture.split('SWEET F374 F')[0],
    ]
    for number, value in enumerate(invalid):
        try:
            ca.decode(value,START,END)
        except ValueError:
            continue
        raise ValueError(f'malformed native packet {number} passed')
    swap = dict(client_swap_id=91,generation=101,begin_tick=START+21,begin_thread=events[0].thread)
    sentinel = dict(swap,client_swap_id=92,generation=102)
    links = ca.link_swaps(events,[swap,sentinel],START,END,625,12)
    require(list(links)==[101] and links[101]['render']['frame_seed']==0x1020304 and
            links[101]['system_frame_info']['requested_tick']==START+350 and
            links[101]['system_hitch']['late_ticks']==39, 'native swap identity or hitch arithmetic differs')
    wrong_thread = ca.link_swaps(events,[dict(swap,begin_thread=0)],START,END,625,12)
    require(wrong_thread[101]['render'] is None and wrong_thread[101]['system_frame_info'],
            'render was bound across threads')
    competing = ca.link_swaps(events,[swap,dict(swap,generation=103)],START,END,625,12)
    require(not competing, 'duplicate client swap accepted')
    windows = [('ordinary',dict(stroke=1,phase='active',intervals=[
        dict(frame=43,after_copy_boundary_check='changed'),dict(frame=44,after_copy_boundary_check='repeated')]))]
    attempts = [dict(attempt=17,generation=101)]
    certs = {(17,3,START+330,START+392):dict(frame=42)}
    edges = {43:SimpleNamespace(flags=1,a=START+404,b=START+408)}
    new, repeat = ca.align_scans(windows,attempts,certs,edges,links,625,12)
    require(new['native_swap_id']==91 and new['system_actual_tick']==START+400 and
            new['scan_minus_system_actual_ns_bounds']==[4*625/12,8*625/12] and
            repeat['crc']=='repeated' and 'system_actual_tick' not in repeat,
            'native time or copy associated with the wrong observation')
    return len(invalid)+4


def read_only_instruments():
    env = dict(os.environ,DEVELOPER_DIR='/Applications/Xcode.app/Contents/Developer')
    run = subprocess.run(['/usr/bin/xcrun','xctrace','list','devices'],env=env,capture_output=True,
                         text=True,timeout=30)
    recovery = subprocess.run(['adb','get-state'],capture_output=True,text=True,timeout=10)
    require(recovery.returncode==0 and recovery.stdout.strip()=='recovery', 'frozen phone is not in TWRP')
    license_required = 'not agreed to the Xcode license' in run.stdout+run.stderr
    scope.save(scope.BASE/'instruments-preflight.json',dict(
        state='native-CA-fallback',xctrace_list_exit=run.returncode,xcode_admin_license_required=license_required,
        testing_phone_mode='ADB recovery',confirmed_testing_phone_usable_in_Instruments=False,
        instrument_recording_started=False,device_writes=0,device_boots=0))


def validate_schemas():
    source = scope.load(scope.BASE/'native-source-check.json')
    require(source['uuid']=='9e40b2eb260c3af1ae45a1a551a8c1b9' and
            all(scope.sha(name)==digest for name,digest in source['input_pins'].items()),
            'local QuartzCore or Instruments model identity differs')
    rules, = (Path(p) for p in source['input_pins'] if 'coreanimation-frame-lifetime-modeler' in p)
    model = rules.read_text()
    require(all(rule in model for rule in (
        '(code 0x0b) (function 0) (arg1 ?swapID) (arg2 ?earliest-time) (arg3 ?presentation-time) (arg4 ?requested-time)',
        '(code 0x21) (function 0) (arg1 ?swap-id) (arg4 ?frame-seed)',
        '(code 0x78) (function 0) (arg1 ?swapID) (arg2 ?acceptable-latency) (arg3 ?presentation-time) (arg4 ?earliest-time)',
        '(+ ?earliest-time ?acceptable-latency)')), 'installed Instruments model differs')
    implementations, = (item for symbol,item in source['trace_sites'].items() if 'frame_info_callback' in symbol)
    by_address = {item['call']:dict(item['instructions']) for item in implementations['sites']}
    require(all(token in by_address['0x1882bc848'].values() for token in (
        'mov\tw0, #0x2c','movk\tw0, #0x31ca, lsl #16','mov\tw1, w24',
        'mov\tx2, x26','mov\tx3, x22','mov\tx4, x28')) and
        all(token in by_address['0x1882bc940'].values() for token in (
        'mov\tw8, #0x2c','movk\tw8, #0x31ca, lsl #16','add\tw0, w8, #0x1b4',
        'ldr\tx1, [sp, #0x78]','ldr\tx2, [sp, #0x48]','mov\tx3, x22','mov\tx4, x26')),
        'installed iOS frame-info or hitch source differs')
    return source['input_pins']


def archive_replay():
    ref = scope.REFERENCE
    frame = scope.load(ref/'frame-scanout-analysis.json')
    scoped = scope.load(ref/'scoped-swap-timing-0373.json')
    core,_,ring = import_module('run-frame350-trial').trace_inputs(ref)
    raw = (ref/'kernel.log').read_text()
    display,drag,rows,_,n,d,_ = runner.audit.workload_score(raw,frame,core,ring,scoped)
    timing, = rows[runner.trace.TIMING]
    attempts = [*display['attempts'],*drag['attempts']]
    require(len({row['attempt'] for row in attempts})==len(attempts),'reference workloads overlap')
    edges,_ = runner.boundaries.refine_post_copy_edges(rows,dict(attempts=attempts),timing)
    certs = runner.score.copy.copy_certificates(attempts,edges,timing)
    windows = [('ordinary',window) for window in display['windows']]+[('slow_drag',drag['windows'][0])]
    scans = ca.align_scans(windows,attempts,certs,edges,{},n,d)
    samples = Counter(row['workload'] for row in scans if 'copy_end_tick' in row)
    require(all(samples[name]>60 for name in ('ordinary','slow_drag')) and
            not any('native_swap_id' in row for row in scans),'reference exact-scan coverage or provenance differs')
    try:
        ca.decode(raw,*ca.envelope(raw)[:2])
    except ValueError:
        pass
    else:
        raise ValueError('a capture with no CA events passed native scoring')
    total = scope.load(ref/'result.json')
    require(total['restored'] and total['independent_restore_verified'],'read-back required for archive replay')
    onset = import_module('audit-frame371-stroke-onset').measure(ref,ref/'scoped-swap-timing-0373.json',result=total)
    require(len(onset['strokes'])==13,'onset replay differs')
    return dict(samples)


def main():
    source_pins = validate_schemas()
    controls = wire_tests()
    covered = archive_replay()
    read_only_instruments()
    raw = (scope.REFERENCE/'kernel.log').read_bytes()
    legacy = sum(len(line) for line in raw.splitlines(keepends=True) if
                 b'SWEET F372 ' in line or b'SWEET F373 ' in line)
    overhead = 512*64 + 256*40 + 1024
    projected = len(raw)+4096-legacy+4*((ca.WIRE_LIMIT+2)//3)+2*512+overhead
    require(legacy > 190_000 and projected < 4_194_304,'native CA projection exceeds permanent ring')
    result = dict(state='0374-offline-verified',patch_sha256=scope.sha(scope.PATCH),
        native_schema_verified=True,controls=controls,reference_aligned_scans=covered,
        reference_raw_bytes=len(raw),replaced_legacy_bytes=legacy,projected_ring_bound=projected,
        device_writes=0,device_boots=0,input_pins=source_pins)
    scope.save(scope.HOST,result)
    print(result)


if __name__=='__main__':
    main()
