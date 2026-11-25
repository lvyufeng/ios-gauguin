#!/usr/bin/env python3
"""Compare the fixed physical cadence after the reviewed work-duration decision."""

from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame408')
base = import_module('run-frame407-trial')
prior = base.prior


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0408 scoring requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    state = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        work = plan['work_duration_us']
        reference,archive,reference_trial,target = ((scope.P404,scope.BEST_CONTROL,'0404',1_401_600)
            if work else (scope.P407,scope.CONTROL,'0407',1_766_400))
        report = base.score(execution,plan,trial=scope.TRIAL,control=reference,old_trial=reference_trial,
                            comparison=archive,target_khz=target)
        paced = report['measurements'][scope.TRIAL]['ca_phase']
        trace.require(paced['qualified'] and not paced['missed'] and paced.get('work_duration_us',0)==work,
                      '0408 hardware phase or exact work duration differs')
        if work:
            control = scope.load(scope.CONTROL)
            for key in ('measurements','moving_Core_IO','all_warm_GPU_writers','stock_interaction_CPU'):
                report[key]['0407'] = control[key]['0407']
            audit = prior.common.audit
            saved,observed = audit.score_archive(scope.LAST,scope.load(scope.P407/'trial-plan.json')['kernel_banner'],
                expected_pairs=None,require_first=False)
            scans,candidate = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
            trace.require(observed==control['measurements']['0407'] and candidate==report['measurements'][scope.TRIAL],
                          '0407 independent physical replay differs')
            report['per_scan_0407_0408'] = prior.flip.parent.parent.paired_ordinals({'0407':saved,scope.TRIAL:scans})
        name = 'scanout-comparison-0407-0408.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0408-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=state,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        independently_repeated_identical_profile=work==0,compositor_work_duration_us=work)


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
