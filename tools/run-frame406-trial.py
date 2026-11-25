#!/usr/bin/env python3
"""Score completion-triggered guarded polls after independent recovery."""

from importlib import import_module
import sys

import frame344_log as trace
from frame405_deadline import completion_samples,repeat_deadlines
from frame406_hint_log import measure

scope = import_module('prepare-frame406')
producer = import_module('run-frame401-trial')
prior = producer.prior
sys.path.append(str(scope.prior.prior.P403_TOOLS))
cpu = import_module('run-frame402-trial')
timeline = import_module('frame393_timeline')


def score(execution,plan):
    report = prior.score(execution,plan,trial=scope.TRIAL)
    old_report = scope.load(scope.CONTROL)
    old_plan = scope.load(scope.P405/'trial-plan.json')
    audit = prior.common.audit
    old_scans,old = audit.score_archive(scope.LAST,old_plan['kernel_banner'],expected_pairs=None,require_first=False)
    scans,new = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==old_report['measurements']['0405'] and new==report['measurements'][scope.TRIAL],
                  '0405/0406 physical replay differs')
    raw = (execution/'kernel.log').read_text()
    rows,strokes,n,d = prior.stage.staging.parse(raw)
    latches = prior.stage.staging.verified_latches(rows,prior.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    clk = cpu.cpu_receipts(raw,new,n,d)
    if 'trace_error' in report['first_CA_timeline']:
        try:
            report['first_CA_timeline'] = timeline.measure(execution,raw,rows,n,d,latches,scans,
                allow_refused_prefix=True)
        except (OSError,KeyError,ValueError) as error:
            report['first_CA_timeline'] = dict(trace_error=str(error))
    for key in ('measurements','moving_Core_IO','all_warm_GPU_writers'):
        report[key]['0405'] = old_report[key]['0405']
    samples = completion_samples(raw,rows,strokes)
    hints = measure(rows,latches,samples,new['moving_GPU'])
    report.update(per_scan_0405_0406=prior.flip.parent.parent.paired_ordinals({'0405':old_scans,scope.TRIAL:scans}),
        stock_interaction_CPU={'0405':old_report['stock_interaction_CPU']['0405'],scope.TRIAL:clk},
        native_render_producer=producer.producer_receipts(rows,latches,new['moving_GPU']),
        raw_GPU_completion=repeat_deadlines(rows,scans,latches,new,samples),completed_probe_hints=hints,
        stable_60_fps_observed=report['stable_60_fps_observed'] and clk['selector_cleanup_qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0406 scoring requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0405-0406.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0406-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    hints = report['completed_probe_hints']
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        raw_probe_wakes=hints['wakes'],raw_probe_next_scan_latches=hints['next_scan_latches'])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
