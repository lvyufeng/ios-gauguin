#!/usr/bin/env python3
"""Audit the immutable 0372 run after independent restoration."""

from collections import Counter
from importlib import import_module
from itertools import zip_longest
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from frame358_display import LOCK_RETRY, PROBE
from frame364_analysis import motion_io_join, score, trace
from frame367_route import decode as decode_route
from frame369_analysis import analyze as analyze_motion
from frame371_transport import phases
from frame372_transport import PACKET_FAMILY, decode, snapshot_handoff, workload_scope
from kernel342_log import ring_status

trial = import_module('run-frame372-trial')
scope = trial.scope
prior = trial.scorer.prior
load, require, sha = scope.load, scope.require, scope.sha
KIND = (score.PRESENT, score.copy.WAKE, *score.KINDS)
C4 = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
PINS = {
    'trial-plan.json': '84650ceec5b4f46dc1c660fea03325f7cbc61a65eaca82088b0c72967c75098a',
    'execution/result.json': '306ca4f01b1b3baab83eca7abf320f6872788a9b2e9d5c7b3b60e51895b1ee93',
    'execution/independent-restore.json': '6ac8ae760b39859d03742860398117264bb38b526e1184ca25a258b909fb3bb0',
    'execution/kernel.log': 'e2e1b04cfe59568f51679682b7cef4e8a4345bf664bdacd3c1030041cc0d7f5f',
    'execution/kernel.log.bin': '847a45a5b40fdbcb9677e4e833675490bbdca69d15a89b16dafb7ac0ad9516ab',
    'execution/restored-capture/result.json': '5b778c3c9908f64c264565d3602922e613c8f24e600ea1242aa818d2e111a7c7',
    'execution/springboard-new.log': '71f266732d2ffa79f9dc28ca5ee7abc42ac77016f29b8ba239e35ed1b360c736',
    'execution/core-wait-execution-analysis.json': '1dbf894cea471f36d366d4ec5c387c6644458c02302394436ca466c735c711c7',
    'execution/kernel-IO-analysis.json': 'b1beb90f1fb492c58fcf3db8ea00d973a17bb95a48cd9e266e69a152c79f1840',
    'execution/kernel-IO-identity-analysis.json': 'e7cb00dfe245569ddeae371cbc9079690662046fe6d10ca475384e068b303317',
}
PROJECTED = ('independent-restore.json', 'kernel.log', 'core-wait-execution-analysis.json',
             'kernel-IO-analysis.json', 'kernel-IO-identity-analysis.json', 'springboard-new.log')


def restore_inputs():
    require(all(sha(scope.BASE/name)==digest for name,digest in PINS.items()), '0372 archive differs')
    reference = scope.check_reference()
    plan = load(scope.BASE/'trial-plan.json')
    result = load(trial.EXEC/'result.json')
    proof = load(trial.EXEC/'independent-restore.json')
    static = load(trial.EXEC/'restored-capture/result.json')
    require(result['trial']=='0372' and result['boot_attempts']==1 and result['observer_exit']==0 and
            result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            len(result['other_log_prefix_preserved'])==4 and all(result['other_log_prefix_preserved'].values()) and
            proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
            len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and proof['install_plan_sha256']==plan['install_plan_sha256'] and
            not (proof['device_writes'] or proof['device_boots'] or static['device_writes']) and
            proof['files'][C4]['fork']['extents']==scope.C4_EXTENTS and
            static['root_header_sha256']==proof['root_header_sha256'],
            '0372 independent read-back or static files differ')
    import_module('run-sb-cadence-trial').static_compare(reference,static)
    return plan,result,proof


def counter_schema(raw, plan, result):
    """Check the one excluded pair against the frozen four-slot device contract."""
    legacy = import_module('analyze-present-retry-log')
    parsed = legacy.analyze(raw)
    require({k:v for k,v in parsed.items() if k!='rows'}==result['display_retry_analysis'],
            'legacy held-frame report differs from the archived verdict')
    rejected,unpaired = parsed['errors']
    line = rejected['line']
    raw_lines = raw.splitlines()
    require(rejected['reason']=='malformed-hold-record' and
            unpaired==dict(line=line+1,reason='retry-without-hold') and
            parsed['retry_exercised'] and parsed['final_snapshot_quiescent'],
            'legacy held-frame report has another failure')
    retention = plan['issued_retention']
    slots = tuple(retention[name] for name in ('waiting_candidates','ready_candidates','issued_mailbox_cells'))
    require(slots==(1,1,2), '0372 held slot layout differs')
    extended = re.compile(legacy.HOLD.pattern.replace('([012])', f'([0-{sum(slots)}])'))
    hold = extended.fullmatch(raw_lines[line-1])
    retry = legacy.RETRY.fullmatch(raw_lines[line])
    require(hold is not None and retry is not None, 'excluded hold/retry pair does not match the frozen grammar')
    submitted,replaced,consumed,retired,canceled,rejected_count,pending,active = map(int,hold.groups())
    requeued,newer,retry_canceled,exhausted = map(int,retry.groups())
    require(2<pending<=sum(slots) and
            submitted+requeued==replaced+consumed+canceled+pending and
            consumed==retired+requeued+active and
            8*exhausted<=requeued<=8*submitted and newer+retry_canceled+exhausted<=retired,
            'excluded hold/retry pair violates held-frame accounting')
    totals = dict(submitted=submitted,replaced=replaced,consumed=consumed,retired=retired,
                  canceled=canceled,rejected=rejected_count,requeued=requeued,newer=newer,
                  retry_canceled=retry_canceled,exhausted=exhausted)
    previous = next(row for row in reversed(parsed['rows']) if row['retry_line']<line)
    following = next(row for row in parsed['rows'] if row['hold_line']>line+1)
    require(all(previous[key]<=value<=following[key]<2**64 for key,value in totals.items()),
            'excluded hold/retry pair regresses a cumulative count')
    return dict(legacy_errors=parsed['errors'],legacy_limit=2,frozen_limit=sum(slots),pending=pending,
                accounted_snapshots=parsed['snapshots']+1,terminal_quiescent=True)


def workload_score(raw, frame, core, ring, report):
    rows,strokes,n,d = trace.parse(raw,extra_kinds=KIND)
    display = score.copy.analyze(raw,frame,extra_kinds=score.KINDS)
    motion = score.parse_motion(raw,strokes,n,d,frame['crc_frame_calibration'])
    joined = motion_io_join(ring,core,motion,lambda tick:tick*n//d)
    _,drag = score.motion_display(raw,frame,rows,motion,core['rows'],joined['submits'],n,d)
    resolved = {(r['stroke'],r['phase'],r['frame']):r['classification'] for r in report['resolved_scans']}
    for source,window in zip(frame['hardware']['windows'],display['windows'],strict=True):
        for output,scan in zip(source['outputs'],window['intervals'],strict=True):
            key = window['stroke'],window['phase'],scan['frame']
            if key in resolved:
                counts = display['phases'][window['phase']]['verified_full_frame_counts']
                counts['unknown'] -= output['step']
                counts[resolved[key]] += output['step']
                scan['after_copy_boundary_check'] = resolved[key]
    return display,drag,rows,strokes,n,d,motion


def deadline_evidence(transport, display):
    first_changed_frame = {}
    for window in display['windows']:
        if window['phase']!='active':
            continue
        first = next((r['frame'] for r in window['intervals']
                      if r['after_copy_boundary_check']=='changed'),None)
        first_changed_frame[window['stroke']] = first
    rows = []
    for row in transport['cutoff_details']:
        timely = [p for p in row['candidate_transports']
                  if p['message_id'] in PACKET_FAMILY and p['copyout_ns']<=row['cutoff_ns']]
        before_first = first_changed_frame[row['stroke']]
        rows.append(dict(stroke=row['stroke'],scan=row['scan'],
            before_first_new_scan=before_first is not None and row['scan']<before_first,
            CA_receipts_before_cutoff=[p['serial'] for p in timely],
            latest_timely_copyout_to_next_begin_ns=(row['begin_ns']-max(p['copyout_ns'] for p in timely)
                                                    if timely else None),
            next_Core_created_after_cutoff_ns=(row['exact_next_Core']['Core_creation_after_cutoff_ns']
                                                if row['exact_next_Core'] else None)))
    warm = [r for r in rows if r['stroke']>=3]
    return dict(rows=rows,warm=dict(deadlines=len(warm),
        before_first_new_scan=sum(r['before_first_new_scan'] for r in warm),
        with_CA_receipt_before_cutoff=sum(bool(r['CA_receipts_before_cutoff']) for r in warm),
        with_exact_next_Core=sum(r['next_Core_created_after_cutoff_ns'] is not None for r in warm),
        with_next_Core_created_late=sum((r['next_Core_created_after_cutoff_ns'] or 0)>0 for r in warm),
        latest_timely_copyout_to_next_begin=phases(r['latest_timely_copyout_to_next_begin_ns']
            for r in warm if r['latest_timely_copyout_to_next_begin_ns'] is not None)),
        interpretation='Time-coincident encoder receipts do not identify the transaction consumed by the render thread.')


def analyze(output):
    plan,result,proof = restore_inputs()
    execution = trial.EXEC
    raw = (execution/'kernel.log').read_text()
    require(raw.splitlines()[0]==plan['kernel_banner'] and
            ring_status((execution/'kernel.log.bin').read_bytes(),raw)['qualified'],
            'kernel image or lossless persistent console ring differs')
    route = decode_route(raw)['route']
    require(route and route['pipe']=='VIG0' and prior.verify_startup(raw)['qualified'],
            'expected VIG0 route or empty-layer startup differs')
    held = counter_schema(raw,plan,result)
    core,joins,ring = import_module('run-frame350-trial').trace_inputs(execution)
    collection = load(execution/'collection-analysis.json')
    require(all(r['coverage_qualified'] and not r['errors'] for r in (core,joins,ring,collection)) and
            collection==result['collection_analysis'], '0372 Core, IO or original script collection differs')
    frame = prior.scanout.analyze(raw,joins['submits'],core['rows'],preserve_data_preimage=True,
        extra_kinds=KIND,latch_calibration=prior.calibration,join_tail_copy=True)
    with TemporaryDirectory(dir=output) as directory:
        projection = Path(directory)
        for name in PROJECTED:
            (projection/name).symlink_to(execution/name)
        prior.timeline.write(projection/'frame-scanout-analysis.json',frame,8_000_000)
        scoped = analyze_motion(projection,begin_threads=True)
    require(not scoped['unverified_copy_completions'], 'unverified ordinary copy boundary')
    display,drag,rows,strokes,n,d,motion = workload_score(raw,frame,core,ring,scoped)
    require(not import_module('audit-frame366-restored').copy_boundary_audit(rows,drag,n,d),
            'unverified fixed-drag copy boundary')
    selection = prior.ready.analyze(raw,display,binding_kind=prior.BOUND,
                                  extra_kinds=(prior.CALIBRATION,PROBE,LOCK_RETRY))
    retained = prior.retained_before_completion(rows,selection)
    probe = trial.scorer.probe_joins(rows,display,selection)

    reference = scope.REFERENCE
    old = load(reference/'scoped-swap-timing-0371.json')
    old_frame = load(reference/'frame-scanout-analysis.json')
    old_core,_,old_ring = import_module('run-frame350-trial').trace_inputs(reference)
    old_display,old_drag,*_ = workload_score((reference/'kernel.log').read_text(),
                                            old_frame,old_core,old_ring,old)
    alignment = prior.compare({'0371':old_display,'0372':display},reference='0371')
    drag_scans = zip_longest(old_drag['windows'][0]['intervals'],drag['windows'][0]['intervals'])
    alignment['fixed_drag'] = [dict(ordinal=i,trials={
        name:(dict(frame=row['frame'],kind=row['after_copy_boundary_check'],crc=row['crc_relation'])
              if row else None) for name,row in zip(('0371','0372'),scans,strict=True)})
        for i,scans in enumerate(drag_scans,1)]
    alignment['motion_summary'] = {name:trial.previous.motion_summary(view)
                                   for name,view in (('0371',old),('0372',scoped))}

    capture = decode(raw,n,d)
    workload = workload_scope(capture,strokes,motion)
    map_path = scope.HOST.parent/'20H392-ca-code-ranges.json'
    require(sha(map_path)=='1e39add5787eb88227027d8b6b033dde5770e55c0c9d4958ef9f500326ec4325',
            'BackBoard stage code map SHA differs')
    code_map = load(map_path)
    require(code_map['cache_build']=='20H392', 'BackBoard stage code map differs')
    snapshots = snapshot_handoff(raw,capture,scoped['swap_timing']['swap_timing'],code_map['ranges'])
    transport = trial.analyze_transport(execution,scoped,raw,rows,n,d,load,capture=capture)
    transport.update(workload=workload,observed_handoff=snapshots,deadline_evidence=deadline_evidence(transport,display))
    trial.summarize_deadline_candidates(transport)
    onset = import_module('audit-frame371-stroke-onset').ready_shift_bound(
        scoped['frontend_cutoffs']['details'],rows,lambda tick:tick*n//d)
    slack = import_module('audit-frame372-queue-slack').compare_slack(scoped,core)
    scoped.update(route=route,comparison_0371_0372=alignment['motion_summary'])
    summary = dict(archive=PINS,legacy_state=result['state'],legacy_frame_measurement=result['frame_measurement'],
        independent_restore=proof['state'],hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
        held_retry_counter_schema=held,crc_control=frame['misr'],crc_latch=frame['crc_frame_calibration'],
        compared_motion=alignment['motion_summary'],certified_copies=display['independently_bounded_copies'],
        fixed_drag_certified_copies=drag['independently_bounded_copies'],
        retained={k:v for k,v in retained.items() if k!='verified_candidates'},probe=probe['checks'],
        warm_onset_ready_advance=onset,slow_FIFO_slack=slack,
        stable_60_fps_observed=scoped['stable_60_fps_qualified'],
        compact_capture=capture['counters'],transport_complete_workload=workload['complete_13_and_fixed_drag'],
        transaction_handoff_proven=snapshots['continuous_transaction_identity_verified'],device_commands=0)
    for name,value,limit in (
        ('frame-scanout-analysis',frame,8_000_000), ('scoped-swap-timing-0372',scoped,3_500_000),
        ('producer-transport-0372',transport,4_000_000), ('present-alignment-0371-0372',alignment,5_000_000),
        ('audit-result',summary,150_000),
    ):
        prior.timeline.write(output/f'{name}.json',value,limit)
    return summary


if __name__=='__main__':
    import argparse

    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('output',type=Path,help='new directory for derived reports')
    args = cli.parse_args()
    args.output.mkdir()
    analyze(args.output)
