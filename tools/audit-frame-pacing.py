#!/usr/bin/env python3
"""Measure output pacing and named missed scan deadlines on restored captures."""

import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
import json
from pathlib import Path

import frame344_log as trace
from frame351_display import PRESENT
import frame352_display as copy
import frame354_display as ready
from frame357_display import BOUND, CALIBRATION
from frame357_replay import scan_windows
from frame358_audit import PROBE
from frame358_display import KINDS
from frame359_scope import MAIN, REF358, check_0358, load, require, sha

REF359 = MAIN/'research/tmp/gauguin-first-frame-worktree-20261120/research/tmp/frame-359/execution'
RESULT_359 = '41eaa5ddcdb693c5245dac00c1c1ef1ec67af52382af9558cf0c064dd9c8a588'
PROOF_359 = 'c1c1fb5bdcf37cd4a61eaff4797accd1d7c52be4414eb662f4b11060a2b8854f'
GAP_THRESHOLDS_NS = (18_000_000, 34_500_000)
INPUTS = ('result.json', 'independent-restore.json', 'frame-scanout-analysis.json',
          'kernel-IO-analysis.json', 'kernel.log')


def check_restored(execution, *, result=None):
    if result is None:
        result = load(execution/INPUTS[0])
    proof = load(execution/INPUTS[1])
    require(result['restored'] and result['independent_restore_verified'] and
            result['static_root_comparison_passed'] and all(result['other_log_prefix_preserved'].values()) and
            result['frame_trace_complete'] and result['dpu_new_content_FPS_qualified'] and
            proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
            len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and not (proof['device_writes'] or proof['device_boots']),
            'read-back, capture or DPU CRC is unqualified')
    return result


def cadence(windows, swap_ticks, ns):
    counts = Counter()
    by_scan = Counter()
    gaps = []
    elapsed_low = elapsed_high = inner_low = inner_high = inner_changes = inner_swaps = 0
    inner_qualified = True
    for window, aligned in windows:
        elapsed_low += window['elapsed_ns_low']
        elapsed_high += window['elapsed_ns_high']
        previous = None
        changed = []
        for out, alignment in zip(window['outputs'], aligned['intervals'], strict=True):
            category = alignment['after_copy_boundary_check']
            counts[category] += out['step']
            if category=='unknown':
                # A new image inside the hole could shorten either neighboring gap.
                previous = None
                inner_qualified = False
            elif category=='changed':
                changed.append(out)
                if previous:
                    distance = (out['frame']-previous['frame']) & 0xffffffff
                    lo = max(0, ns(out['edge_lower_tick'])-ns(previous['edge_upper_tick']))
                    hi = ns(out['edge_upper_tick'])-ns(previous['edge_lower_tick'])
                    require(0<distance<(1<<31) and 0<=lo<=hi, 'reversed hardware image edge')
                    by_scan[distance] += 1
                    gaps.append((lo,hi))
                previous = out
        if len(changed)>1:
            first,last = changed[0],changed[-1]
            inner_low += max(0, ns(last['edge_lower_tick'])-ns(first['edge_upper_tick']))
            inner_high += ns(last['edge_upper_tick'])-ns(first['edge_lower_tick'])
            inner_changes += len(changed)-1
            inner_swaps += (bisect_right(swap_ticks,last['edge_upper_tick']) -
                            bisect_right(swap_ticks,first['edge_upper_tick']))
    return dict(scans=dict.fromkeys(('changed','repeated','unknown'),0) | dict(counts),
        new_images_per_second_bounds=([counts['changed']*1e9/elapsed_high,
            (counts['changed']+counts['unknown'])*1e9/elapsed_low] if elapsed_low else None),
        changed_image_gap_scans=dict(sorted(by_scan.items())),
        changed_image_gap_p95_ns=[trace.quantile([gap[i] for gap in gaps],.95) for i in range(2)],
        changed_image_longest_gap_ns=[max((gap[i] for gap in gaps),default=None) for i in range(2)],
        long_gap_thresholds=[dict(ns=value,certain=sum(lo>=value for lo,_ in gaps),
            possible=sum(hi>=value for _,hi in gaps)) for value in GAP_THRESHOLDS_NS],
        first_through_last_changed=dict(transitions=inner_changes,swaps=inner_swaps,
            new_image_rate_bounds=([inner_changes*1e9/inner_high,inner_changes*1e9/inner_low]
                                   if inner_qualified and inner_low else None),
            swap_rate_using_edge_upper_membership_bounds=([inner_swaps*1e9/inner_high,inner_swaps*1e9/inner_low]
                                                         if inner_qualified and inner_low else None)))


def read_deadlines(rows, display, selection, kernel, ns, scale):
    windows = {window.frame:window for window in scan_windows(rows[trace.VBLANK],ns,scale,bracketed=True)}
    outputs = {item['previous_frame']:(window['stroke'],window['phase'],item['after_copy_boundary_check'])
               for window in display['windows'] for item in window['intervals']}
    attempts = {a['attempt']:a for a in display['attempts']}
    validates = trace.indexed(rows[ready.VALIDATE],lambda row:row.id,'fresh read version validation')
    issues = trace.indexed(rows[trace.ISSUE],lambda row:row.a,'submit token')
    writers = defaultdict(set)
    for row in rows[trace.WRITER]:
        writers[row.id].add(row.a)

    def identity(row):
        return tuple(row[key] for key in ('generation','surface','version','fence'))

    next_new = {(r['target_frame'],identity(r)) for r in selection['joins'] if
                r.get('following_hardware_frame',{}).get('classification')=='changed'}
    results = []
    for chosen in selection['joins']:
        slot = chosen['target_frame']
        scoring = outputs.get(slot)
        scan = windows.get(slot)
        attempt = attempts[chosen['attempt']]
        guards = attempt['read_guards']
        exact = [g for g in guards if g['accepted'] and (g['surface'],g['fence'])==
                 (chosen['surface'],chosen['fence'])]
        if not scoring or not scan or len(exact)!=1:
            continue
        guard, = exact
        annotation = dict(stroke=scoring[0],phase=scoring[1],target_scan=slot,
            generation=chosen['generation'],surface=guard['surface'],version=chosen['version'],
            fence=guard['fence'],outcome=scoring[2],deadline_ns=scan.deadline,
            read_wait_ns=ns(guard['locked_tick'])-ns(guard['queued_tick']),
            surface_reservation=bool(guard.get('surface_reservation')))
        valid = validates.get(chosen['attempt'])
        if scoring[2]!='repeated' or chosen['copied'] or not valid or valid.flags!=1 or not any(
                p['disposition']=='deferred' for p in attempt['blanking_proofs']):
            if annotation['surface_reservation']:
                results.append(annotation | dict(crossed_deadline=False))
            continue
        if not (ns(guard['surface_ready_tick'])<=ns(guard['queued_tick'])<scan.deadline<=ns(guard['locked_tick'])):
            if annotation['surface_reservation']:
                results.append(annotation | dict(crossed_deadline=False))
            continue
        phases = []
        for request in kernel['rows']:
            selector = str(request['selector'])
            for label,begin,end in zip(kernel['phase_names'][selector],request['begin'],request['end'],strict=True):
                if begin<=scan.deadline<end:
                    native = issues.get(request['token']) if selector=='70' else None
                    targets = sorted(writers[native.id]) if native else []
                    phases.append(dict(selector=request['selector'], phase=label, recorded_writer_surfaces=targets,
                        separate_recorded_writers=bool(targets and guard['surface'] not in targets)))
        results.append(annotation | dict(crossed_deadline=True, IO_at_deadline=phases,
            same_version_changed_next_scan=((slot+1)&0xffffffff,identity(chosen)) in next_new))
    return results


def measure(raw, frame, kernel, *, display=None, selection=None):
    require(frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'] and
            kernel['coverage_qualified'], 'CRC latch or kernel IO coverage is unqualified')
    rows, strokes, numer, denom = trace.parse(raw,extra_kinds=(PRESENT,copy.WAKE,*KINDS))
    require(len(strokes)==13 and (numer,denom)==(frame['tick_numer'],frame['tick_denom']), 'trace timebase or input differs')

    def ns(tick):
        return tick*numer//denom

    if display is None:
        display = copy.analyze(raw,frame,extra_kinds=KINDS)
    if selection is None:
        selection = ready.analyze(raw,display,binding_kind=BOUND,extra_kinds=(CALIBRATION,PROBE))
    windows = list(zip(frame['hardware']['windows'],display['windows'],strict=True))
    require(len(windows)==26, 'expected active and release windows for every stroke')
    swap_ticks = [s.tick for s in rows[trace.SWAP] if not s.flags and s.b]
    samples = [row for row in windows if row[1]['phase']=='active']
    deadlines = read_deadlines(rows,display,selection,kernel,ns,numer/denom)
    late_active = [r for r in deadlines if r['phase']=='active' and r['crossed_deadline']]
    named_contention = Counter(p['phase'] for r in late_active for p in r['IO_at_deadline']
        if p['selector']==70 and p['phase'] in ('runtime_issue','surface_cache_flush') and p['separate_recorded_writers'])
    return dict(hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
        active=cadence(samples,swap_ticks,ns),
        active_strokes_3_through_13=cadence([w for w in samples if w[1]['stroke']>=3],swap_ticks,ns),
        release=cadence([w for w in windows if w[1]['phase']=='release'],swap_ticks,ns),
        strokes=[dict(stroke=w[1]['stroke'],phase=w[1]['phase'],**cadence([w],swap_ticks,ns)) for w in windows],
        active_surface_reservations=sum(r['phase']=='active' and r['surface_reservation'] for r in deadlines),
        active_read_guards_crossing_deadline=len(late_active), active_separate_recorded_writer_overlap=dict(named_contention),
        active_same_version_changed_next_scan=sum(r['same_version_changed_next_scan'] for r in late_active),
        read_deadlines=deadlines)


def audit(execution):
    result = check_restored(execution)
    raw = (execution/'kernel.log').read_text()
    frame, kernel = (load(execution/name) for name in INPUTS[2:4])
    return dict(trial=result['trial'],input_sha256={name:sha(execution/name) for name in INPUTS},
                **measure(raw,frame,kernel))


def references():
    check_0358()
    require(sha(REF359/'result.json')==RESULT_359 and sha(REF359/'independent-restore.json')==PROOF_359,
            '0359 reference receipts differ')
    return (REF358,REF359)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('execution',nargs='*',type=Path,help='defaults to the two pinned restored runs')
    paths = parser.parse_args().execution or references()
    print(json.dumps(dict(scope='DPU CRC and independently bounded present attempts',
        trials=[audit(path) for path in paths],
        repeated_crc_does_not_identify_expected_motion=True),indent=2))


if __name__=='__main__':
    main()
