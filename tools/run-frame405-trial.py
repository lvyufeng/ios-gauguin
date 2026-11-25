#!/usr/bin/env python3
"""Measure physical movement and exact raw GPU completion after restoration."""

from importlib import import_module
import sys

import frame344_log as trace
import frame393_timeline as timeline
import frame405_deadline as deadline

scope = import_module('prepare-frame405')
producer = import_module('run-frame401-trial')
prior = producer.prior
sys.path.append(str(scope.prior.P403_TOOLS))
cpu = import_module('run-frame402-trial')


def score(execution,plan):
    report = prior.score(execution,plan,trial=scope.TRIAL)
    audit = prior.common.audit
    reference_trial = '0404' if scope.COMPARISON.is_file() else '0403'
    reference = scope.P404 if reference_trial=='0404' else scope.prior.P403
    old_report = scope.load(scope.COMPARISON if reference_trial=='0404' else scope.prior.CONTROL)
    old_plan = scope.load(reference/'trial-plan.json')
    old_scans,old = audit.score_archive(reference/'execution',old_plan['kernel_banner'],
        expected_pairs=None,require_first=False)
    scans,new = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==old_report['measurements'][reference_trial] and new==report['measurements'][scope.TRIAL],
                  'restored physical replay differs')
    raw = (execution/'kernel.log').read_text()
    rows,strokes,n,d = prior.stage.staging.parse(raw)
    latches = prior.stage.staging.verified_latches(rows,prior.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    clk = cpu.cpu_receipts(raw,new,n,d)
    if 'trace_error' in report['first_CA_timeline']:
        try:
            report['first_CA_timeline'] = timeline.measure(execution,raw,rows,n,d,latches,scans,
                allow_refused_prefix=True)
        except (KeyError,OSError,ValueError) as error:
            report['first_CA_timeline'] = dict(trace_error=str(error))
    for key in ('measurements','moving_Core_IO','all_warm_GPU_writers'):
        report[key][reference_trial] = old_report[key][reference_trial]
    try:
        samples = deadline.completion_samples(raw,rows,strokes)
        observation = deadline.repeat_deadlines(rows,scans,latches,new,samples)
        observation['qualified'] = bool(samples)
    except (KeyError,TypeError,ValueError) as error:
        observation = dict(qualified=False,completion_measurement_error=str(error))
    report.update(per_scan_reference=prior.flip.parent.parent.paired_ordinals({reference_trial:old_scans,scope.TRIAL:scans}),
        reference_trial=reference_trial,
        stock_interaction_CPU={reference_trial:old_report['stock_interaction_CPU'][reference_trial],scope.TRIAL:clk},
        native_render_producer=producer.producer_receipts(rows,latches,new['moving_GPU']),
        raw_GPU_completion=observation,
        stable_60_fps_observed=report['stable_60_fps_observed'] and clk['selector_cleanup_qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0405 scoring requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = f"scanout-comparison-{report['reference_trial']}-0405.json"
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0405-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    clk = report['stock_interaction_CPU'][scope.TRIAL]
    qualified = report['raw_GPU_completion']['qualified']
    state = scope.SUCCESS if qualified else '0405-DPU-measured-raw-EOP-incomplete-root-restored'
    result.update(state=state,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        stock_CPU_selector_cleanup_qualified=clk['selector_cleanup_qualified'],raw_GPU_completion_qualified=qualified)


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
