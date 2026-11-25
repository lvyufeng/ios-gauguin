#!/usr/bin/env python3
"""Verify a physical 0413 confirmation or padded-view qualification after restoration."""

from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame413')
scorer = import_module('run-frame407-trial')
prior = scorer.prior


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'],'0413 requires independent restoration before scoring')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    evidence = execution/'page-flip-latches.json'
    if code or not evidence.is_file():
        return
    try:
        old = plan['frame413_control']
        exact = plan['frame413_exact_repeat']
        path,_,_,reference = scope.control(dict(control=old,repeat=exact))
        receipt = scope.load(evidence)
        trace.require(receipt['original_front_latched'] and receipt.get('reserved_linear_slot_bytes')==
                      (None if exact else scope.DPU_LINEAR_SLOT_BYTES),'0413 missing activation and original-view restore')
        report = scorer.score(execution,plan,trial=scope.TRIAL,control=path,old_trial=old,comparison=reference,
                              target_khz=1_401_600)
        phase = report['measurements'][scope.TRIAL]['ca_phase']
        trace.require(phase['qualified'] and not phase['missed'] and phase['work_duration_us']==plan['work_duration_us'] and
                      report['native_GPU_profile']['native_request_accepted'],'0413 pacing or GPU receipt differs')
        if not exact:
            report['reserved_linear_scanout'] = dict(bytes_per_slot=scope.DPU_LINEAR_SLOT_BYTES,
                private_latches=receipt['latched_private'],original_view_restored=True,producer_route='guarded CPU copy')
        name = f'scanout-comparison-{old}-0413.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0413-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        independently_repeated_identical_profile=bool(exact and report['stable_60_fps_observed']),
        reserved_linear_scanout_qualified=not exact)


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
