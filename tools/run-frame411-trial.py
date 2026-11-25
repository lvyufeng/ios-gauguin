#!/usr/bin/env python3
"""Measure managed linear scanout after independently restoring the 0411 root."""

from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame411')
control = import_module('run-frame407-trial')
prior = control.prior


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'],'0411 scoring requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    receipt = execution/'page-flip-latches.json'
    if code or not receipt.is_file():
        return
    try:
        evidence = scope.load(receipt)
        trace.require(evidence['managed_linear_slot_bytes']==scope.SLOT_BYTES and evidence['original_front_latched'],
                      '0411 requires both managed backing latches and the original view restored')
        home,_,_,_,comparison,_,_ = scope.prior.check.measured(scope.CONTROL)
        report = control.score(execution,plan,trial=scope.TRIAL,control=home,old_trial=scope.CONTROL,
                               comparison=comparison,target_khz=1_401_600)
        phase = report['measurements'][scope.TRIAL]['ca_phase']
        trace.require(phase['qualified'] and not phase['missed'] and phase['work_duration_us']==plan['work_duration_us'],
                      '0411 reference DPU cadence or workload budget differs')
        report['managed_linear_scanout'] = dict(bytes_per_slot=scope.SLOT_BYTES,
            private_latches=evidence['latched_private'],original_view_restored=True,producer_route='guarded CPU copy')
        name = 'scanout-comparison-0409-0411.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0411-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        managed_scanout_layout_qualified=True,managed_private_latches=evidence['latched_private'])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
