#!/usr/bin/env python3
"""Validate guarded staging and confirmed DPU latches after independent restore."""

from bisect import bisect_right
from collections import Counter
from importlib import import_module
from itertools import pairwise
import re

import frame344_log as trace
import frame349_log as crc
from frame354_display import VALIDATE
from frame357_display import calibration
from frame364_analysis import score
import frame380_phase as timing
from kernel342_log import ring_status

scope = import_module('prepare-frame382')
preflight = import_module('run-frame381-trial')
parent = preflight.parent
timeline = parent.parent.previous.timeline
load,require = scope.load,scope.require
MASK = 0xffffffff
MANAGED_LINEAR_BYTES = 0xab8000
MANAGED_LINEAR_MAP = 'SWEET F383 MAP: two-private-managed-linear-slots'
RESERVED_LINEAR_MAP = 'SWEET F383 MAP: two-private-reserved-linear-slots'
IOKIT_WC_MAP = 'SWEET F383 MAP: two-private-IOKit-WC-slots'


def latch_receipts(raw, rows):
    backing, = re.findall(r'^SWEET F382 BACKING: first=([0-9a-f]{8}) second=([0-9a-f]{8}) bytes=(\d+)$',
                          raw,re.M)
    first,second = (int(word,16) for word in backing[:2])
    size = int(backing[2])
    managed = MANAGED_LINEAR_MAP in raw
    reserved = RESERVED_LINEAR_MAP in raw
    if size == MANAGED_LINEAR_BYTES:
        require(managed!=reserved and IOKIT_WC_MAP not in raw and
                all(addr and addr % 0x4000 == 0 and addr+size <= 1<<32 and
                    (addr >= 0xa2400000 or addr+size <= 0xa0000000) for addr in (first,second)) and
                abs(second-first)>=size,'invalid padded private scanout buffers')
        if managed:
            require(raw.count(f'SWEET F411: two managed linear backings bytes={size}\n')==1 and
                    raw.count(MANAGED_LINEAR_MAP+'\n')==1,'missing managed backing receipt')
        else:
            require(raw.count(RESERVED_LINEAR_MAP+'\n')==1 and second-first==size and
                    'SWEET F411: two managed linear backings' not in raw,'missing reserved backing receipt')
    else:
        require(not (managed or reserved) and size==0x9e4000 and first%0x4000==0 and
                second-first==size and second+size<=1<<32,
                'invalid private scanout buffers')
    require('SWEET F382 STOP:' not in raw,'hardware request or latch was quarantined')
    staged = [tuple(map(int,row)) for row in re.findall(r'^SWEET F38[24] P (\d+) ([12]) (\d+)$',raw,re.M)]
    requests = [tuple(map(int,row)) for row in re.findall(r'^SWEET F382 I (\d+) (\d+) ([012]) (\d+)(?: C)?$',raw,re.M)]
    confirmed = [tuple(map(int,row)) for row in re.findall(r'^SWEET F382 L (\d+) (\d+) ([012]) (\d+)$',raw,re.M)]
    require(2<len(requests)==len(confirmed)<=1025 and requests[-1][0]==requests[-1][2]==0 and
            len(staged)<=1025, 'missing private flip sequence or original source latch')
    copied = trace.indexed((r for r in rows[trace.COPY] if r.c==trace.FRAME_BYTES),
                           lambda row:row.b,'full copy completion')
    attempts = trace.indexed(rows[trace.ATTEMPT],lambda row:row.id,'guarded attempt')
    guards = trace.indexed((r for r in rows[VALIDATE] if r.flags==1),lambda row:row.id,'GPU read lease')
    endings = trace.indexed((r for r in rows[trace.RESULT] if r.a),lambda row:row.id,'accepted copy result')
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'DPU frame counter')
    stage = {}
    for key,slot,tick in staged:
        record,attempt,guard,end = copied.get(tick),attempts.get(key),guards.get(key),endings.get(key)
        require(key not in stage and record and attempt and guard and end and
                attempt.tick<=guard.tick<=record.a<tick<=end.tick and guard.a==record.id and guard.b==guard.c,
                'staged data lacks an exact current GPU read lease')
        stage[key] = dict(attempt=key,slot=slot,tick=tick,begin=record.a,generation=attempt.a,swap=attempt.b)

    front = last_latch = last_generation = 0
    accepted = {}
    for request,latch in zip(requests,confirmed,strict=True):
        key,cycle,slot,issued = request
        same,scan,confirmed_slot,latched = latch
        edge = edges.get(scan)
        require((same,confirmed_slot,scan)==(key,slot,(cycle+1)&MASK) and slot!=front and
                last_latch < issued <= latched and edge and edge.flags==1 and issued<edge.b and edge.a<=latched,
                'unconfirmed or out-of-order source latch')
        if key:
            ready = stage.get(key)
            require(scan not in accepted and ready and ready['slot']==slot and
                    last_latch<ready['begin']<ready['tick']<issued and last_generation<ready['generation'],
                    'reused front buffer or published a stale generation')
            last_generation = ready['generation']
            accepted[scan] = dict(ready,old_slot=front,issued_tick=issued,confirmed_tick=latched)
        else:
            require(slot==0 and request==requests[-1],'early return to original source')
        front,last_latch = slot,latched
    require({row['slot'] for row in accepted.values()}=={1,2},'both private buffers were not latched')
    receipt = dict(hardware_requests=len(requests),latched_private=len(accepted),
        original_front_latched=True,staged=staged,accepted_by_scan=accepted)
    if managed:
        receipt['managed_linear_slot_bytes'] = size
    if reserved:
        receipt['reserved_linear_slot_bytes'] = size
    return receipt


def scan_rows(ordinary, moving, latches):
    scans = []
    for workload,windows in (('ordinary',ordinary),('slow_drag',moving)):
        for w in windows:
            for raw in w['outputs']:
                row = dict(workload=workload,stroke=w['stroke']+1,
                    phase=w['window'],frame=raw['frame'],crc=raw['classification'],
                    vblank_ticks=[raw['edge_lower_tick'],raw['edge_upper_tick']])
                if 'crc' in raw:
                    row['crc_signatures'] = [raw['previous_crc'],raw['crc']]
                if receipt := latches.get(row['frame']):
                    row.update(generation=receipt['generation'],native_swap_id=receipt['swap'])
                scans.append(row)
    return scans


def rates(windows, numer, denom):
    counts = Counter()
    for window in windows:
        for row in window['outputs']:
            counts[row['classification']] += row['step']
    lo,hi = (sum(window['elapsed_ns_'+name] for window in windows) for name in ('low','high'))
    require(0<lo<=hi,'invalid scoring window')
    gaps = [((b['edge_lower_tick']-a['edge_upper_tick'])*numer//denom,
             (b['edge_upper_tick']-a['edge_lower_tick'])*numer//denom)
            for window in windows for a,b in pairwise([r for r in window['outputs'] if r['classification']=='changed'])]
    return dict(scans={k:counts[k] for k in ('changed','repeated','unknown')},
        new_images_per_second_bounds=[counts['changed']*1e9/hi,(counts['changed']+counts['unknown'])*1e9/lo],
        changed_image_gap_p95_ns=[trace.quantile(x,.95) for x in zip(*gaps)] if gaps else None)


def drag_wait(scans, rows, latches):
    visible = {r.id:r.tick for r in rows[trace.READY]}
    eops = {r.id:r.tick for r in rows[trace.EOP]}
    issues = {r.id:r.tick for r in rows[trace.ISSUE]}
    bound = {r.b>>32:r for r in rows[trace.WRITER] if r.b}
    accepted = [r for r in rows[trace.SWAP] if not r.flags and r.c]
    preceding = sorted(latches)
    result = []
    for scan in (s for s in scans if s['workload']=='slow_drag' and s['crc']=='repeated'):
        cutoff = scan['vblank_ticks'][0]
        ix = bisect_right(preceding,scan['frame'])-1
        generation = latches[preceding[ix]]['generation'] if ix>=0 else 0
        next_swaps = [r for r in accepted if r.id>generation and r.tick<=cutoff]
        candidates = []
        for swap in next_swaps:
            writer = bound.get(swap.id)
            fence = writer.id if writer and swap.c==((writer.c<<32)|writer.a) else None
            step = ('writer-unbound' if not fence else
                    'awaiting-issue' if issues.get(fence,1<<64)>cutoff else
                    'awaiting-observed-EOP' if eops.get(fence,1<<64)>cutoff else
                    'awaiting-cache-visibility' if visible.get(fence,1<<64)>cutoff else
                    'visible-before-earliest-edge')
            candidates.append(dict(generation=swap.id,fence=fence,stage=step))
        result.append(dict(frame=scan['frame'],earliest_edge_tick=cutoff,candidates=candidates,
            certified_same_CRC_latch=scan['frame'] in latches))
    return result


def after_restore(execution, plan, result, before, code, *, trial_scope=scope):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent state restoration must precede analysis')
    raw = (execution/'kernel.log').read_text()
    trial = trial_scope.TRIAL
    try:
        require(code==0 and plan['kernel_banner'] in raw, 'exact kernel did not reach the collection window')
        require(ring_status((execution/'kernel.log.bin').read_bytes(),raw)['qualified'],'console capture lost records')
        require(preflight.dma_route(raw)['address_translation_bypassed_for_both'],'display DMA route differs')
        kinds = (score.PRESENT,score.copy.WAKE,*score.KINDS)
        rows,strokes,n,d = trace.parse(raw,extra_kinds=kinds)
        require(len(strokes)==13,'script does not contain 13 swipes')
        gate = score.scanout.probe(raw,read_only_counts_with_crc=True)
        edges = rows[trace.VBLANK]
        snapshot = crc.misr_receipts(raw,gate,edges,n/d,preserve_data_preimage=True)
        pairs = crc.paired_reads(rows[trace.CRC],trace.indexed(edges,lambda row:row.id,'DPU edge'),snapshot,n/d)
        cadence = score.scanout.hardware(gate,rows|{trace.CRC:[]},strokes,[],n,d)
        result.update(hardware_refresh_hz_bounds=cadence['hardware_refresh_hz_bounds'],
            crc_control=snapshot,hardware_CRC_pairs=len(pairs),observed_strokes=len(strokes))
        evidence = latch_receipts(raw,rows)
        layout = plan['display_dma']
        managed = layout.get('private_managed_linear_bytes')
        reserved = layout.get('private_reserved_linear_bytes')
        require(managed==evidence.get('managed_linear_slot_bytes') and reserved==evidence.get('reserved_linear_slot_bytes'),
                'private scanout backing differs from plan')
        if plan['display_dma'].get('private_iokit_WC_maps'):
            tag = MANAGED_LINEAR_MAP if managed else RESERVED_LINEAR_MAP if reserved else IOKIT_WC_MAP
            require(tag in raw,'both private IOKit mappings are unverified')
    except (ValueError, OSError) as error:
        result.update(state=f'{trial}-flip-unqualified-root-restored',frame_error=str(error))
        return
    timeline.write(execution/'page-flip-latches.json',evidence,800_000)
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement'] = 'withheld-by-core-collection-gate'
        return
    cores,join,_ = import_module('run-frame350-trial').trace_inputs(execution)
    try:
        stage_times = {row[2] for row in evidence['staged']}
        frame = crc.analyze(raw,join['submits'],cores['rows'],preserve_data_preimage=True,
            extra_kinds=kinds,latch_calibration=calibration,join_tail_copy=True,offscreen_copy_end_ticks=stage_times)
        cal = frame['crc_frame_calibration']
        require(frame['misr']['qualified'] and cal['qualified'] and cal['lag_frames']==0 and
                len(cal['dedicated_witnesses'])==3, 'CRC setup, cleanup or calibration lost')
        motion = score.parse_motion(raw,strokes,n,d,cal)
        ordinary = frame['hardware']['windows']
        require(len(ordinary)==26,'missing ordinary stroke and release windows')
        times = [(motion['start_tick'],motion['end_tick'])]
        moving = score.scanout.hardware(frame['dpu_probe'],rows|{trace.CRC:[]},times,[],n,d)
        moving['windows'] = [w for w in moving['windows'] if w['window']=='active']
        paired = trace.indexed(frame['raw_crc_pairs'],lambda row:row['frame'],'CRC pair')
        front_writes = [copy for copy in score.layers_for_copies(rows,[]) if copy['end_tick'] not in stage_times]
        moving['windows'] = crc.summarize_windows(moving,rows[trace.VBLANK],paired,front_writes,
                                                cal,frame['misr']['qualified'],n/d)
        latches = evidence['accepted_by_scan']
        scans = scan_rows(ordinary,moving['windows'],latches)
        require(all(s['crc']!='changed' or s['frame'] in latches for s in scans),
                'changed CRC in a scored scan without a qualified flip')
        old = load(scope.preflight.REFERENCE/'scanout-comparison-0375-0379-0380.json')
        control = load(scope.REFERENCE/'scanout-comparison-0380-0381-control.json')
        compare = parent.parent.paired_ordinals({'0380':old['native']['scans'],
            '0381-control':control['native']['scans'],trial:scans})
        metric = dict(ordinary_active=rates([w for w in ordinary if w['window']=='active'],n,d),
            warm_active=rates([w for w in ordinary if w['window']=='active' and w['stroke']>=2],n,d),
            ordinary_release=rates([w for w in ordinary if w['window']=='release'],n,d),
            slow_drag=rates(moving['windows'],n,d))
        onset = timing.onset(scans,frame)
        fourth = [s for s in scans if s['workload']=='ordinary' and s['stroke']==4 and s['phase']=='release']
        retest = [dict(scan=s['frame'],**latches[s['frame']]) for s in fourth if s['frame'] in latches]
        require(retest,'missing fourth release switch evidence')
        for staged in retest:
            staged['offscreen_copy_crossed_edges'] = [
                s['frame'] for s in fourth
                if staged['begin']<s['vblank_ticks'][0] and s['vblank_ticks'][1]<staged['tick']]
        waits = drag_wait(scans,rows,latches)
        report = dict(page_flips=evidence,metrics=metric,onset=onset,scans=compare,
            hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
            crc_control=frame['misr'],CRC_witnesses=cal['dedicated_witnesses'],
            fourth_release=retest,slow_drag_repeat_waits=waits)
        timeline.write(execution/f'scanout-comparison-0380-0381-{trial}.json',report,5_000_000)
    except (ValueError, KeyError, OSError) as error:
        result.update(state=f'{trial}-latches-verified-physical-score-incomplete-root-restored',frame_error=str(error))
        return
    complete = all(not row['scans']['unknown'] for row in metric.values())
    result.update(state=trial_scope.SUCCESS if complete else f'{trial}-flips-verified-partial-CRC-root-restored',
        frame_trace_complete=True,dpu_new_content_FPS_qualified=complete,measured=metric,
        stable_60_fps_observed=complete and not metric['warm_active']['scans']['repeated'] and
            not metric['slow_drag']['scans']['repeated'],
        hardware_refresh_hz_bounds=report['hardware_refresh_hz_bounds'],latched_frames=evidence['latched_private'],
        fourth_release_latches=len(retest),
        fourth_release_offscreen_crossings=sum(bool(row['offscreen_copy_crossed_edges']) for row in retest),
        slow_drag_repeats=waits)


if __name__=='__main__':
    raise SystemExit(parent.runner.main(scope,after_restore_fn=after_restore))
