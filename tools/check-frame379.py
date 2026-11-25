#!/usr/bin/env python3
"""Replay known crossings, verify segment bytes, and bound the console budget."""

from base64 import b64encode
from collections import Counter
from importlib import import_module
from math import ceil
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

import frame379_concurrency as capture
from frame344_log import require
from frame353_display import TAKE

scope=import_module('prepare-frame379')
runner=import_module('run-frame379-trial')

NATIVE=r'''
#include "gauguin_copy379_probe.h"
#include <cassert>
#include <cstdio>
#include <vector>

static void check_surface(unsigned alignment)
{
    std::vector<uint8_t> src(SCAN352_SOURCE_STRIDE * SCAN352_HEIGHT + 128, 0x74);
    std::vector<uint8_t> plain(SCAN352_PANEL_STRIDE * SCAN352_HEIGHT + 128, 0xc9);
    std::vector<uint8_t> sampled(plain.size(),0xc9);
    auto *from=src.data()+alignment;
    auto *control=plain.data()+alignment;
    auto *target=sampled.data()+alignment;
    struct f379_segments timing{};
    for (unsigned row=0;row<SCAN352_HEIGHT;++row) {
        auto *value=from+row*SCAN352_SOURCE_STRIDE;
        for (unsigned x=0;x<SCAN352_PANEL_STRIDE;++x) value[x]=(row*19+x*7+(x>>5))&255;
        scan356_copy_row(control+row*SCAN352_PANEL_STRIDE,value);
        if (row%F379_SEGMENT_ROWS)
            scan356_copy_row(target+row*SCAN352_PANEL_STRIDE,value);
        else
            scan379_probe_row(target+row*SCAN352_PANEL_STRIDE,value,row/F379_SEGMENT_ROWS,&timing);
        for (unsigned x=SCAN352_PANEL_STRIDE;x<SCAN352_SOURCE_STRIDE;++x) assert(value[x]==0x74);
    }
    assert(plain==sampled);
    for (unsigned x=0;x<alignment;++x) assert(sampled[x]==0xc9);
    for (size_t x=alignment+SCAN352_PANEL_STRIDE*SCAN352_HEIGHT;x<sampled.size();++x) assert(sampled[x]==0xc9);
    uint64_t measured=0;
    for (unsigned i=0;i<F379_SEGMENTS;++i) measured+=timing.read[i]+timing.issue[i];
    assert(measured && measured<UINT32_MAX);
}

int main()
{
    assert(scan352_can_copy(3044,4878) && !scan352_can_copy(3045,4878));
    assert(f379_scene(157056000)==F379_STROKE2 && f379_scene(166656000)==0);
    assert(f379_scene(246720000)==F379_STROKE4 && f379_scene(256320000)==0);
    assert(f379_wait_scene(159744000)==F379_STROKE2 && f379_wait_scene(163392000)==0);
    assert(f379_wait_scene(249888000)==F379_STROKE4 && f379_wait_scene(253728000)==0);
    struct f379_wait_state state{};
    assert(f379_new_wait(&state,6,19));
    state={19,11,6};
    assert(f379_waiting(&state,6,11));
    assert(!f379_waiting(&state,6,0) && !f379_waiting(&state,6,12));
    assert(!f379_new_wait(&state,6,20) && !f379_new_wait(&state,7,19));
    assert(f379_new_wait(&state,7,20));
    check_surface(0);
    check_surface(16);
    check_surface(32);
    uint8_t out[F379_RECORD_BYTES];
    struct f379_segments data{};
    for (unsigned i=0;i<F379_SEGMENTS;++i) {
        data.end[i]=200*(i+1);
        data.row[i]=24;
        data.read[i]=4;
        data.issue[i]=5;
    }
    assert(!f379_pack(out,0,F379_STROKE2,&data));
    assert(!f379_pack(out,10,4,&data));
    data.row[0]=8;
    assert(!f379_pack(out,10,F379_STROKE2,&data));
    data.row[0]=24;
    assert(f379_pack(out,10,F379_STROKE2,&data));
    assert(fwrite(out,1,sizeof(out),stdout)==sizeof(out));
    return 0;
}
'''


def native():
    include=scope.BASE/'native-kernel/source/bsd/dev'
    original=scope.P375/'native-kernel/source/bsd/dev/gauguin_copy356.h'
    require((include/original.name).read_bytes()==original.read_bytes(),'original full copy instructions differ')
    require((include/'gauguin_frame377_slots.h').read_bytes()==
            (scope.P378/'native-kernel/source/bsd/dev/gauguin_frame377_slots.h').read_bytes(),
            'IPC ownership object differs')
    with TemporaryDirectory() as work:
        path=Path(work)/'test.cpp'
        path.write_text(NATIVE)
        target=path.with_suffix('')
        subprocess.run(['c++','-O2','-std=c++17','-Wall','-Wextra','-Werror','-I',str(include),
                        str(path),'-o',str(target)],check=True)
        wire=subprocess.check_output([str(target)])
    data='SWEET F379 S 0 1 '+b64encode(wire).decode()+'\\nSWEET F379 F: rows=1 lost=0 control=0 stroke2=1 stroke4=0\\n'
    data=data.replace('\\n','\n')
    rows,counts,lost=capture.wire_rows(data)
    require(rows==[dict(attempt=10,lane=2,points=[(200*(i+1),24,4,5) for i in range(8)])]
            and not lost and counts=={1:0,2:1,3:0},'segment codec lost source/issue intervals')
    try:
        capture.wire_rows(data.replace('S 0','S 1'))
    except ValueError:
        return
    raise ValueError('segment decoder accepted incorrect block ordinal')


def replay():
    raw=(scope.REFERENCE/'kernel.log').read_text()
    start,end,n,d=runner.parent.envelope(raw)
    _,strokes,_,_=runner.trace.parse(raw,extra_kinds=(runner.score.PRESENT,runner.score.copy.WAKE,*runner.score.KINDS))
    events,_,_,_=runner.trace.parse(raw,extra_kinds=(runner.score.PRESENT,runner.score.copy.WAKE,*runner.score.KINDS))
    old=scope.load(scope.COMPARISON)
    copies=old['copy_phases']['rows']
    failures=old['copy']['0378']['check_failed']
    pending=capture.gpu_intervals(events,end)
    windows=capture.retest(copies,start,n,d,strokes,pending,bad=failures)
    possible={}
    generations,scans,counts=set(),set(),Counter()
    for row in events[TAKE]:
        lane=capture.lane_in(row.tick-start,capture.HOLD_TICKS)
        if lane and row.a not in generations and row.c not in scans and counts[lane]<capture.MAX_HOLDS:
            active=[w for w in pending if w['issued']<=row.tick<w['window_end'] and
                    row.tick-w['issued']<=capture.AGE_TICKS]
            if active:
                generation=row.a
                generations.add(generation)
                scans.add(row.c)
                counts[lane]+=1
                possible[row.id]=dict(case=capture.LABELS[lane],generation=generation,scan=row.c,fence=active[-1]['fence'])
    require(len(failures)==2 and all(row['attempt'] in possible for row in failures),
            'the two exact prior take receipts must meet the bounded deferral rule')
    return windows,{str(row['attempt']):possible[row['attempt']] for row in failures},len(possible)


def main():
    native()
    scenes,crossings,holds=replay()
    prior=scope.load(scope.P378/'host-verification.json')
    frame377=scope.load(scope.parent.P377/'host-verification.json')
    projection=frame377['projected_ring_bound']-6666+ceil(
        sum(capture.LIMITS.values())*capture.PACKED_BYTES*4/3)+8*30+24*150+128
    require(projection<4_194_304,'segment and deferral receipts exceed the reference console reservation')
    report=dict(state='0379-offline-verified',patch_sha256=scope.sha(scope.PATCH),native_schema_verified=True,
        controls=20,full_surface_bytes_verified=True,original_loop_and_probe_bytes_match=True,
        reference_windows_verified=True,reference_crossings_deferred=True,reference_take_replay=holds,
        reference_scenes=scenes,reference_crossings=crossings,projected_ring_bound=projection,
        reference_raw_bytes=prior['reference_raw_bytes'],device_writes=0,device_boots=0)
    scope.save(scope.HOST,report)
    print({key:value for key,value in report.items() if key!='reference_scenes'})


if __name__=='__main__':
    main()
