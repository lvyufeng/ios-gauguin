#!/usr/bin/env python3
"""Verify the native bus step and compare physical scans after independent recovery."""

from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame409')
base = import_module('run-frame407-trial')
prior = base.prior


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0409 scoring requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        index = plan['native_bandwidth_index']
        report = base.score(execution,plan,trial=scope.TRIAL,control=scope.P408,old_trial='0408',
                            comparison=scope.COMPARISON,target_khz=1_401_600)
        phase = report['measurements'][scope.TRIAL]['ca_phase']
        vote = report['native_GPU_profile']
        trace.require(phase['qualified'] and not phase['missed'] and phase['work_duration_us']==plan['work_duration_us'] and
                      vote['native_request_accepted'] and vote['perf_index']==5 and vote['bw_index']==index,
                      '0409 DPU phase or exact native request differs')
        name = 'scanout-comparison-0408-0409.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0409-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        independently_repeated_identical_profile=index==10,native_bandwidth_index=index,native_GPU_profile=vote)


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
