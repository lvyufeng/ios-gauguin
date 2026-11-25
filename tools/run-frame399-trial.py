#!/usr/bin/env python3
"""Measure the 0399 observations and compare physical frames after independent readback."""

from importlib import import_module
import re

import frame344_log as trace
import frame399_clock
import frame399_writer

scope = import_module('prepare-frame399')
prior = import_module('run-frame398-trial')
common,stock,flip,stage = prior.common,prior.stock,prior.flip,prior.stage


def score(execution,plan):
    result = common.score_pair(execution,plan,trial=scope.TRIAL,measure_CA=False)
    baseline = scope.P394/'execution'
    saved = scope.load(scope.CONTROL)
    control_plan = scope.load(scope.P394/'trial-plan.json')
    old_scans,old = common.audit.score_archive(baseline,control_plan['kernel_banner'],expected_pairs=None,
                                              require_first=False)
    scans,new = common.audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==saved['measurements']['0394'] and result['measurements'][scope.TRIAL]==new,
                  '0399 physical comparison did not reproduce')
    raw = (execution/'kernel.log').read_text()
    activation = scope.load(execution/'edr-activation.json')
    vote = stock.perf.analyze(raw,perf_index=5)
    trace.require(activation['active'] and activation['code_checks_qualified'] and activation['once_abi_qualified'] and
                  vote['native_request_accepted'] and saved['native_GPU_profile']['native_request_accepted'],
                  '0399 signed GPU operating point differs')
    rows,_,n,d = stage.staging.parse(raw)
    try:
        clock = frame399_clock.observe(raw,rows,n,d,new['moving_GPU'])
    except (KeyError, ValueError) as error:
        clock = dict(qualified=False,error=str(error))
    try:
        frontend,capped = frame399_writer.decode((execution/'backboardd.log.current').read_text(errors='replace'))
        writer = dict(records=len(frontend),capped=capped,qualified=bool(frontend) and not capped)
    except (OSError, ValueError) as error:
        writer = dict(qualified=False,error=str(error))
    latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
    try:
        causal = prior.prior.timeline.measure(execution,raw,rows,n,d,latches,scans)
    except (KeyError,OSError,ValueError) as error:
        causal = dict(trace_error=str(error))
    active = stock.active_after_onset(scans,new)
    trial = scope.TRIAL
    placement = prior.placement(execution,raw,rows,n,d,new)
    workers = re.findall(r'^GAUGUIN QOS394: worker=(\d+) before=(\d+) applied=33 result=0$',
                         (execution/'backboardd.log.current').read_text(errors='replace'),re.M)
    qos = [dict(worker=int(tid),prior_class=int(before),current_class=33)
           for tid,before in workers if int(tid)==placement['recorder']]
    result.update(measurements={**result['measurements'],'0394':old},first_CA_timeline=causal,
        per_scan_0394_0399=flip.parent.parent.paired_ordinals({'0394':old_scans,trial:scans}),
        moving_Core_IO={'0394':saved['moving_Core_IO']['0394'],trial:result['moving_Core_IO']},
        all_warm_GPU_writers={'0394':saved['all_warm_GPU_writers']['0394'],trial:stock.producer(raw,new)},
        native_GPU_profile=vote,recorder_CPU_placement=placement,recorder_qos=qos,
        CPU_frequency_observation=clock,frontend_writer_observation=writer,motion_after_onset=active,
        stable_60_fps_observed=result['stable_60_fps_observed'] and active['qualified'])
    return result


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'],'0399 scoring requires independent restoration')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0394-0399.json'
        stage.save_bounded(execution/name,report,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0399-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        CPU_frequency_observation_qualified=report['CPU_frequency_observation']['qualified'],
        frontend_writer_observation=report['frontend_writer_observation'])


if __name__ == '__main__':
    raise SystemExit(common.runner.main(scope,after_restore_fn=after_restore))
