#!/usr/bin/env python3
"""Compare the next same-phone CPU point after exact HFSX and misc readback."""

from importlib import import_module

import frame344_log as trace
from frame402_cpu_clock import cpu_receipts
from frame405_deadline import completion_samples,repeat_deadlines

scope = import_module('prepare-frame407')
producer = import_module('run-frame401-trial')
prior = producer.prior
timeline = import_module('frame393_timeline')


def score(execution,plan,*,trial=scope.TRIAL,control=scope.P404,old_trial='0404',comparison=scope.CONTROL,
          target_khz=scope.clock.TARGET_KHZ):
    report = prior.score(execution,plan,trial=trial)
    old_report = scope.load(comparison)
    old_plan = scope.load(control/'trial-plan.json')
    audit = prior.common.audit
    previous,old = audit.score_archive(control/'execution',old_plan['kernel_banner'],
        expected_pairs=None,require_first=False)
    scans,new = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==old_report['measurements'][old_trial] and new==report['measurements'][trial],
                  'reference and candidate physical replay differ')
    raw = (execution/'kernel.log').read_text()
    rows,strokes,n,d = prior.stage.staging.parse(raw)
    latches = prior.stage.staging.verified_latches(rows,prior.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    clk = cpu_receipts(raw,new,n,d,target_khz=target_khz)
    if 'trace_error' in report['first_CA_timeline']:
        try:
            report['first_CA_timeline'] = timeline.measure(execution,raw,rows,n,d,latches,scans,
                allow_refused_prefix=True)
        except (KeyError,OSError,ValueError) as error:
            report['first_CA_timeline'] = dict(trace_error=str(error))
    for key in ('measurements','moving_Core_IO','all_warm_GPU_writers'):
        report[key][old_trial] = old_report[key][old_trial]
    try:
        samples = completion_samples(raw,rows,strokes)
        raw_gpu = repeat_deadlines(rows,scans,latches,new,samples)
        raw_gpu['qualified'] = bool(samples)
    except (KeyError,TypeError,ValueError) as error:
        raw_gpu = dict(qualified=False,completion_measurement_error=str(error))
    report.update(**{f'per_scan_{old_trial}_{trial}':prior.flip.parent.parent.paired_ordinals({old_trial:previous,trial:scans})},
        stock_interaction_CPU={old_trial:old_report['stock_interaction_CPU'][old_trial],trial:clk},
        native_render_producer=producer.producer_receipts(rows,latches,new['moving_GPU']),
        raw_GPU_completion=raw_gpu,
        stable_60_fps_observed=report['stable_60_fps_observed'] and clk['selector_cleanup_qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0407 scoring requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0404-0407.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0407-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    clk = report['stock_interaction_CPU'][scope.TRIAL]
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        stock_CPU_warm_eleven_qualified=clk['warm_eleven_qualified'],
        stock_CPU_selector_cleanup_qualified=clk['selector_cleanup_qualified'],
        raw_GPU_completion_qualified=report['raw_GPU_completion']['qualified'])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
