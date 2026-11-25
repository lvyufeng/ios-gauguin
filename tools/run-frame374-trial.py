#!/usr/bin/env python3
"""Run the frozen 0374 trial, restore the device, and align native CA with DPU."""

import argparse
from hashlib import sha256
from functools import partial
from importlib import import_module
from itertools import zip_longest
from types import SimpleNamespace

from frame358_display import LOCK_RETRY, PROBE
from frame364_analysis import score, trace
from frame367_route import decode as decode_route
from frame369_analysis import analyze
from frame374_native_ca import align_scans, capture_summary, decode, envelope, link_swaps

scope = import_module('prepare-frame374')
previous = import_module('run-frame373-trial')
audit = previous.audit
prior = previous.prior
boundaries = import_module('audit-frame366-restored')
load, require, sha = scope.load, scope.require, scope.sha
EXEC = scope.BASE/'execution'
WORDING = previous.WORDING
GRANT_SHA = sha256(WORDING.encode()).hexdigest()


def record_grant(trial_scope=scope):
    base,trial = trial_scope.BASE,trial_scope.TRIAL
    ready = load(base/'ready.json')
    reviewed = load(base/'final-review.json')
    require(not (base/'execution').exists() and reviewed['state']==f'reviewed-frame{int(trial)}-one-shot' and
            reviewed['ready_sha256']==sha(base/'ready.json') and
            reviewed['trial_plan_sha256']==sha(base/'trial-plan.json'),
            'standing grant requires the reviewed unclaimed plan')
    trial_scope.save(base/'approval.json',dict.fromkeys(trial_scope.FLAGS,True)|dict(
        approved=True,one_shot=True,source='actual-user-60Hz-standing-grant',
        provenance='direct-standing-user-instruction',user_answer=WORDING,user_answer_sha256=GRANT_SHA,
        plan_sha256=ready['install_plan_sha256'],trial_plan_sha256=ready['trial_plan_sha256'],
        image_sha256=ready['image_sha256']))


def check_consent(approval, ready, plan, *, trial, flags, trial_scope=scope):
    require(trial==trial_scope.TRIAL and approval.get('approved') is True and approval.get('one_shot') is True and
            all(approval.get(flag) is True for flag in flags) and not approval.get('fixture_only') and
            approval.get('source')=='actual-user-60Hz-standing-grant' and
            approval.get('provenance')=='direct-standing-user-instruction' and approval.get('user_answer')==WORDING and
            approval.get('user_answer_sha256')==GRANT_SHA and approval.get('plan_sha256')==ready['install_plan_sha256'] and
            approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
            approval.get('image_sha256')==plan['image_sha256'], 'standing grant differs from the frozen trial')


def compare(display, drag, scoped, trial_scope=scope):
    trial = trial_scope.TRIAL
    reference = trial_scope.REFERENCE
    previous_trial = f'{int(trial)-1:04d}'
    old = load(reference/f'scoped-swap-timing-{previous_trial}.json')
    old_frame = load(reference/'frame-scanout-analysis.json')
    old_core,_,old_ring = import_module('run-frame350-trial').trace_inputs(reference)
    old_display,old_drag,*_ = audit.workload_score((reference/'kernel.log').read_text(),
                                                            old_frame,old_core,old_ring,old)
    names = (previous_trial,trial)
    delta = prior.compare(dict(zip(names,(old_display,display),strict=True)),reference=previous_trial)
    slow_scans = zip_longest(old_drag['windows'][0]['intervals'],drag['windows'][0]['intervals'])
    delta['fixed_drag'] = [dict(ordinal=i,trials={
        name:(dict(frame=row['frame'],kind=row['after_copy_boundary_check'],crc=row['crc_relation']) if row else None)
        for name,row in zip(names,pair,strict=True)}) for i,pair in enumerate(slow_scans,1)]
    delta['compared_motion'] = {name:previous.old_trial.previous.motion_summary(item)
                                for name,item in zip(names,(old,scoped),strict=True)}
    return delta


def native_alignment(raw, scoped, display, drag, rows, strokes, n, d, motion):
    start, end, numer, denom = envelope(raw)
    require((n,d)==(numer,denom), 'native and physical timebases differ')
    events = decode(raw,start,end)
    timing, = rows[trace.TIMING]
    attempts = list(trace.indexed((*display['attempts'],*drag['attempts']),
                                 lambda row:row['attempt'],'ordinary or slow-drag attempt').values())
    edges,_ = boundaries.refine_post_copy_edges(rows,dict(attempts=attempts),timing)
    certs = score.copy.copy_certificates(attempts,edges,timing)
    links = link_swaps(events,scoped['swap_timing']['swap_timing'],start,end,n,d)
    windows = [('ordinary',w) for w in display['windows']] + [('slow_drag',w) for w in drag['windows']]
    scans = align_scans(windows,attempts,certs,edges,links,n,d)
    interval = motion['samples'][0][1], motion['samples'][-1][2]
    coverage = capture_summary(events,strokes,interval,links,scans)
    report = dict(summary=coverage, clock=dict(start=start,end=end,numer=n,denom=d), matches=list(links.values()),
                  scans=scans, timing_scope='CoreAnimation uses mach absolute ticks. Physical scan intervals use DPU.')
    return report


def after_restore(execution, plan, result, before, code, *, trial_scope=scope, extend_native=None):
    trial = trial_scope.TRIAL
    collected = prior.collect_after_restore(execution,plan,result,before,code,trial=trial,
                                            extra_kinds=(PROBE,LOCK_RETRY),join_tail_copy=True)
    if collected is None:
        return
    frame,_,selection,_,retained,_,inputs = collected
    raw = (execution/'kernel.log').read_text()
    try:
        proof = load(execution/'independent-restore.json')
        installed = load(trial_scope.BASE/'slot-delta/install-plan.json')
        require(proof['files'][audit.C4]['fork']['extents']==installed['rows']['c4']['data_extents'] and
                decode_route(raw)['route']['pipe']=='VIG0', 'C4 or physical route differs')
        scoped = analyze(execution,begin_threads=True)
        core,_,ring = inputs
        display,drag,rows,strokes,n,d,motion = audit.workload_score(raw,frame,core,ring,scoped)
        require(not scoped['unverified_copy_completions'] and not boundaries.copy_boundary_audit(rows,drag,n,d),
                'unverified frame copy boundary')
        delta = compare(display,drag,scoped,trial_scope=trial_scope)
        probes = previous.old_trial.scorer.probe_joins(rows,display,selection)
    except (KeyError,ValueError) as error:
        result.update(state=f'{trial}-frame-comparison-unqualified-root-restored',frame_error=str(error))
        return
    scoped_path = execution/f'scoped-swap-timing-{trial}.json'
    prior.timeline.write(execution/f'present-alignment-{int(trial)-1:04d}-{trial}.json',delta,5_000_000)
    prior.timeline.write(scoped_path,scoped,3_500_000)
    result.update(frame_trace_complete=True,dpu_new_content_FPS_qualified=True,
        stable_60_fps_observed=scoped['stable_60_fps_qualified'],compared_motion=delta['compared_motion'],
        hardware_refresh_hz_bounds=frame['hardware']['hardware_refresh_hz_bounds'],
        crc_register=frame['misr'],crc_calibration=frame['crc_frame_calibration'],
        ordinary_certified_copies=display['independently_bounded_copies'],
        fixed_drag_certified_copies=drag['independently_bounded_copies'],
        retained={k:v for k,v in retained.items() if k!='verified_candidates'},fence_probes=probes['checks'])
    try:
        onset = import_module('audit-frame371-stroke-onset').measure(execution,scoped_path,result=result)
        prior.timeline.write(execution/f'onset-and-motion-{trial}.json',onset,450_000)
        result['onset_and_motion_by_direction'] = onset['warm_by_direction']
        native = native_alignment(raw,scoped,display,drag,rows,strokes,n,d,motion)
        measured = native['summary']['native_capture_covers_workloads'] and all(
            item['requested'] and item['system_and_physical'] for item in native['summary']['physical'].values())
        if extend_native is not None:
            measured = extend_native(native,scoped,onset,raw,rows,result,measured)
        prior.timeline.write(execution/f'native-CA-scan-alignment-{trial}.json',native,2_000_000)
    except (KeyError,ValueError) as error:
        result.update(state=f'{trial}-DPU-qualified-native-CA-incomplete-root-restored',native_CA_error=str(error))
        return
    result.update(state=trial_scope.SUCCESS if measured else f'{trial}-DPU-qualified-native-CA-partial-root-restored',
                  native_CA_trace=native['summary'], system_present_alignment_qualified=bool(measured))


def main(trial_scope=scope, *, extend_native=None, after_restore_fn=None):
    trial,base = trial_scope.TRIAL,trial_scope.BASE
    cli = argparse.ArgumentParser(description=f'Run and independently restore the frozen {trial} trial')
    cli.add_argument('--record-standing-grant',action='store_true')
    if cli.parse_args().record_standing_grant:
        record_grant(trial_scope)
        return 0
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            SimpleNamespace(check_consent=partial(check_consent,trial_scope=trial_scope)),base=base,trial=trial,
            expected=trial_scope.expected_plan,flags=trial_scope.FLAGS,reserve=trial_scope.RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print(f'{trial} refused before device IO: '+repr(error),flush=True)
        return 2
    return import_module('run-core342-trial').execute(plan,approval,budget,base,base/'execution',
        trial=trial,after_restore=after_restore_fn or partial(after_restore,trial_scope=trial_scope,extend_native=extend_native),
        success_state=trial_scope.SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
