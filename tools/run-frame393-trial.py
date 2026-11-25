#!/usr/bin/env python3
"""Link the frozen multi-context CA receipt to a physical first frame after restore."""

from importlib import import_module

import frame344_log as trace
import frame393_timeline as timeline

scope = import_module('prepare-frame393')
prior = import_module('run-frame392-trial')
previous,flip,stage = prior.previous,prior.flip,prior.stage


def score(execution, plan):
    trial = scope.TRIAL
    measured = previous.score_pair(execution,plan,trial=trial,measure_CA=False)
    old_plan = scope.load(scope.P395/'trial-plan.json')
    old_scans,old = previous.audit.score_archive(scope.LAST,old_plan['kernel_banner'],expected_pairs=None,require_first=False)
    archived = scope.load(scope.LAST/'scanout-comparison-0391-0395.json')
    trace.require(old==archived['measurements']['0395'],'0395 physical control did not replay')
    scans,new = previous.audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(new==measured['measurements'][trial],'0393 physical comparison did not replay')
    raw = (execution/'kernel.log').read_text()
    vote = prior.perf.analyze(raw,perf_index=5)
    trace.require(vote['native_request_accepted'] and
        archived['native_GPU_profile']['native_request_accepted'],'0395/0393 GPU operating point differs')
    rows,_,n,d = stage.staging.parse(raw)
    latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
    try:
        causal = timeline.measure(execution,raw,rows,n,d,latches,scans)
    except (KeyError,OSError,ValueError) as error:
        causal = dict(trace_error=str(error))
    scope_0393 = prior.active_after_onset(scans,new)
    measured.update(measurements={**measured['measurements'],'0395':old},first_CA_timeline=causal,
        per_scan_0395_0393=flip.parent.parent.paired_ordinals({'0395':old_scans,trial:scans}),
        motion_after_onset=scope_0393,native_GPU_profile=vote,
        stable_60_fps_observed=measured['stable_60_fps_observed'] and scope_0393['qualified'])
    return measured


def after_restore(execution, plan, result, before, code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'CA and display scoring requires independent restoration')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        measured = score(execution,plan)
        name = 'scanout-comparison-0395-0393.json'
        stage.save_bounded(execution/name,measured,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0393-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    causal = measured['first_CA_timeline']
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=measured['stable_60_fps_observed'],
        exact_CA_warm_strokes=causal.get('warm_strokes_with_exact_member',0),
        exact_CA_warm_members=causal.get('warm_exact_members',0),
        exact_CA_first_inclusions=causal.get('warm_members_with_native_inclusion',0))


if __name__=='__main__':
    raise SystemExit(previous.runner.main(scope,after_restore_fn=after_restore))
