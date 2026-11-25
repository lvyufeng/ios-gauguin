#!/usr/bin/env python3
"""Measure compositor CPU placement and physical content after independent restore."""

from collections import Counter
from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame398')
prior = import_module('run-frame397-trial')
common,stock,flip,stage = prior.common,prior.stock,prior.flip,prior.stage


def placement(execution,raw,rows,n,d,measured):
    tid,selected,others,issues = trace.one(r'^SWEET CPU398: tid=(\d+) selected=(\d+) other_writer=(\d+) issues=([\d,]+)$',
        raw,'display recorder placement')
    cpus = list(map(int,issues.split(',')))
    tid,selected,others = map(int,(tid,selected,others))
    trace.require(len(cpus)==8,'unexpected recorder CPU topology')
    edges = trace.indexed(rows[trace.VBLANK],lambda r:r.id,'physical scan')
    windows = [(edges[w['first_scan']].tick*n//d,edges[w['last_scan']].tick*n//d)
        for w in measured['moving_GPU']['ordinary']['windows']]
    io = scope.load(execution/'kernel-IO-analysis.json')
    workers = Counter(r['tid'] for r in io['rows'] if r['selector']==70 and not r['result'] and
        any(begin<=r['first_ns']<end for begin,end in windows))
    return dict(recorder=tid,preferred_dispatches=selected,other_surface_writers=others,native_issues_by_CPU=cpus,
        moving_submit_workers=dict(workers),qualified=bool(io['coverage_qualified'] and tid in workers and selected and sum(cpus[6:])))


def score(execution,plan):
    trial = scope.TRIAL
    activation = scope.load(execution/'edr-activation.json')
    trace.require(activation['active'] and activation['code_checks_qualified'] and activation['once_abi_qualified'],
        '0398 compositor helper did not activate')
    report = common.score_pair(execution,plan,trial=trial,measure_CA=False)
    old_plan = scope.load(scope.P397/'trial-plan.json')
    archived = scope.load(scope.LAST/'scanout-comparison-0393-0397.json')
    old_scans,old = common.audit.score_archive(scope.LAST,old_plan['kernel_banner'],expected_pairs=None,require_first=False)
    scans,new = common.audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==archived['measurements']['0397'] and new==report['measurements'][trial],'0397/0398 physical replay differs')
    raw,old_raw = ((p/'kernel.log').read_text() for p in (execution,scope.LAST))
    vote = stock.perf.analyze(raw,perf_index=5)
    trace.require(vote['native_request_accepted'] and archived['native_GPU_profile']['native_request_accepted'],
        '0397/0398 GPU operating point differs')
    rows,_,n,d = stage.staging.parse(raw)
    latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
    try:
        causal = prior.timeline.measure(execution,raw,rows,n,d,latches,scans)
    except (KeyError,OSError,ValueError) as error:
        causal = dict(trace_error=str(error))
    active = stock.active_after_onset(scans,new)
    report.update(measurements={**report['measurements'],'0397':old},first_CA_timeline=causal,
        per_scan_0397_0398=flip.parent.parent.paired_ordinals({'0397':old_scans,trial:scans}),
        moving_Core_IO={'0397':archived['moving_Core_IO'],trial:report['moving_Core_IO']},
        all_warm_GPU_writers={'0397':stock.producer(old_raw,old),trial:stock.producer(raw,new)},
        native_GPU_profile=vote,recorder_CPU_placement=placement(execution,raw,rows,n,d,new),
        motion_after_onset=active,stable_60_fps_observed=report['stable_60_fps_observed'] and active['qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
        '0398 scoring requires independent restore')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0397-0398.json'
        stage.save_bounded(execution/name,report,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0398-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,DPU_independent_physical_FPS_qualified=True,
        stable_60_fps_observed=report['stable_60_fps_observed'],recorder_CPU_placement=report['recorder_CPU_placement'])


if __name__=='__main__':
    raise SystemExit(common.runner.main(scope,after_restore_fn=after_restore))
