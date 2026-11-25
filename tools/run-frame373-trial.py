#!/usr/bin/env python3
"""Execute the reviewed 0373 device trial and compare restored CRC evidence."""

import argparse
from hashlib import sha256
from importlib import import_module
from itertools import zip_longest
from types import SimpleNamespace

from frame358_display import LOCK_RETRY, PROBE
from frame364_analysis import score, trace
from frame367_route import decode as decode_route
from frame369_analysis import analyze
from frame371_transport import analyze_transport
from frame372_transport import snapshot_handoff, workload_scope
from frame373_receipts import decode_with_unmatched

scope = import_module('prepare-frame373')
old_trial = import_module('run-frame372-trial')
audit = import_module('audit-frame372-restored')
prior = old_trial.scorer.prior
load, require, sha = scope.load, scope.require, scope.sha
EXEC = scope.BASE/'execution'
WORDING = old_trial.previous.prior.STANDING_INSTRUCTION
GRANT_SHA = sha256(WORDING.encode()).hexdigest()


def record_grant():
    ready = load(scope.BASE/'ready.json')
    reviewed = load(scope.BASE/'final-review.json')
    require(not EXEC.exists() and reviewed['state']=='reviewed-frame373-one-shot' and
            reviewed['ready_sha256']==sha(scope.BASE/'ready.json') and
            reviewed['trial_plan_sha256']==sha(scope.BASE/'trial-plan.json'),
            'standing grant requires the reviewed unclaimed 0373 plan')
    scope.save(scope.BASE/'approval.json',dict.fromkeys(scope.FLAGS,True)|dict(
        approved=True,one_shot=True,source='actual-user-60Hz-standing-grant',
        provenance='direct-standing-user-instruction',user_answer=WORDING,user_answer_sha256=GRANT_SHA,
        plan_sha256=ready['install_plan_sha256'],trial_plan_sha256=ready['trial_plan_sha256'],
        image_sha256=ready['image_sha256']))


def check_consent(approval, ready, plan, *, trial, flags):
    require(trial==scope.TRIAL and approval.get('approved') is True and approval.get('one_shot') is True and
            all(approval.get(flag) is True for flag in flags) and not approval.get('fixture_only') and
            approval.get('source')=='actual-user-60Hz-standing-grant' and
            approval.get('provenance')=='direct-standing-user-instruction' and
            approval.get('user_answer')==WORDING and approval.get('user_answer_sha256')==GRANT_SHA and
            approval.get('plan_sha256')==ready['install_plan_sha256'] and
            approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
            approval.get('image_sha256')==plan['image_sha256'], '0373 standing grant differs from the frozen trial')


def compare(frame, raw, scoped, inputs):
    core,_,ring = inputs
    display,drag,rows,strokes,n,d,motion = audit.workload_score(raw,frame,core,ring,scoped)
    boundaries = import_module('audit-frame366-restored')
    require(not scoped['unverified_copy_completions'] and not boundaries.copy_boundary_audit(rows,drag,n,d),
            'unverified frame copy boundary')
    old = load(scope.COMPARISON/'scoped-swap-timing-0372.json')
    old_frame = load(scope.COMPARISON/'frame-scanout-analysis.json')
    old_core,_,old_ring = import_module('run-frame350-trial').trace_inputs(scope.REFERENCE)
    old_raw = (scope.REFERENCE/'kernel.log').read_text()
    old_display,old_drag,*_ = audit.workload_score(old_raw,old_frame,old_core,old_ring,old)
    delta = prior.compare({'0372':old_display,'0373':display},reference='0372')
    rows_by_scan = zip_longest(old_drag['windows'][0]['intervals'],drag['windows'][0]['intervals'])
    delta['fixed_drag'] = [dict(ordinal=i,trials={
        name:(dict(frame=slot['frame'],kind=slot['after_copy_boundary_check'],crc=slot['crc_relation'])
              if slot else None) for name,slot in zip(('0372','0373'),slots,strict=True)})
        for i,slots in enumerate(rows_by_scan,1)]
    delta['compared_motion'] = {name:old_trial.previous.motion_summary(item)
                                for name,item in (('0372',old),('0373',scoped))}
    return display,drag,delta,rows,strokes,n,d,motion


def after_restore(execution, plan, result, before, code):
    collected = prior.collect_after_restore(execution,plan,result,before,code,trial=scope.TRIAL,
                                            extra_kinds=(PROBE,LOCK_RETRY),join_tail_copy=True)
    if collected is None:
        return
    frame,_,selection,_,retained,_,inputs = collected
    raw = (execution/'kernel.log').read_text()
    try:
        proof = load(execution/'independent-restore.json')
        require(proof['files'][audit.C4]['fork']['extents']==scope.parent.C4_EXTENTS and
                decode_route(raw)['route']['pipe']=='VIG0', '0373 C4 or physical route differs')
        scoped = analyze(execution,begin_threads=True)
        display,drag,delta,rows,strokes,n,d,motion = compare(frame,raw,scoped,inputs)
        probes = old_trial.scorer.probe_joins(rows,display,selection)
    except (KeyError,ValueError) as error:
        result.update(state='0373-frame-comparison-unqualified-root-restored',frame_error=str(error))
        return
    prior.timeline.write(execution/'present-alignment-0372-0373.json',delta,5_000_000)
    prior.timeline.write(execution/'scoped-swap-timing-0373.json',scoped,3_500_000)
    result.update(frame_trace_complete=True,dpu_new_content_FPS_qualified=True,
        stable_60_fps_observed=scoped['stable_60_fps_qualified'],compared_motion=delta['compared_motion'],
        hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
        crc_register=frame['misr'],crc_calibration=frame['crc_frame_calibration'],
        ordinary_certified_copies=display['independently_bounded_copies'],
        fixed_drag_certified_copies=drag['independently_bounded_copies'],
        retained={k:v for k,v in retained.items() if k!='verified_candidates'},fence_probes=probes['checks'],
        exact_CA_seed_handoff_verified=False,producer_scheduling_changed=False)
    try:
        capture = decode_with_unmatched(raw,n,d)
        workload = workload_scope(capture,strokes,motion)
        code_map = load(scope.P372.parent/'frame-372-host/20H392-ca-code-ranges.json')
        snapshots = snapshot_handoff(raw,capture,scoped['swap_timing']['swap_timing'],code_map['ranges'])
        transport = analyze_transport(execution,scoped,raw,rows,n,d,load,capture=capture)
        transport.update(workload=workload,observed_handoff=snapshots,
            deadline_evidence=audit.deadline_evidence(transport,display),
            offline_CA=load(scope.HOST)['static'])
        old_trial.summarize_deadline_candidates(transport)
        prior.timeline.write(execution/'producer-transport-0373.json',transport,4_000_000)
    except (KeyError,ValueError) as error:
        result.update(state='0373-CRC-qualified-receipt-details-unqualified-root-restored',transport_error=str(error))
        return
    result.update(state=scope.SUCCESS,compact_receipts=capture['counters'],
        unmatched_receive_details=capture['unmatched_receipts'],complete_pairing=workload['complete_13_and_fixed_drag'],
        warm_deadlines=transport['deadline_evidence']['warm'])


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--record-standing-grant',action='store_true')
    if cli.parse_args().record_standing_grant:
        record_grant()
        return 0
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
            expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0373 refused before device IO: '+repr(error),flush=True)
        return 2
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,EXEC,
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
