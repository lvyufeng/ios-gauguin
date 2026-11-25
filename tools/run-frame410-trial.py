#!/usr/bin/env python3
"""Score one proven compositor budget with independent DPU and CRC receipts."""

from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame410')
base = import_module('run-frame407-trial')
prior = base.prior


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0410 scoring requires independent original restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        old = plan['phase_control_trial']
        ref,_,_,_,comparison,_,_ = scope.check.measured(old)
        report = base.score(execution,plan,trial=scope.TRIAL,control=ref,old_trial=old,
                            comparison=comparison,target_khz=1_401_600)
        phase = report['measurements'][scope.TRIAL]['ca_phase']
        trace.require(phase['qualified'] and not phase['missed'] and phase['work_duration_us']==plan['work_duration_us'],
                      '0410 DPU cadence or verified work duration differs')
        name = f'scanout-comparison-{old}-0410.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0410-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        independently_repeated_identical_profile=plan['exact_repeat'],
        compositor_work_duration_us=plan['work_duration_us'],native_GPU_profile=report['native_GPU_profile'])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
