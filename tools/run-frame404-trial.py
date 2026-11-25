#!/usr/bin/env python3
"""Score exact producer and CPU-clock evidence on an independently restored root."""

from importlib import import_module
import sys

import frame344_log as trace

scope = import_module('prepare-frame404')
previous = import_module('run-frame401-trial')
prior = previous.prior
sys.path.append(str(scope.P403_TOOLS))
cpu = import_module('run-frame402-trial')


def score(execution,plan):
    report = prior.score(execution,plan,trial=scope.TRIAL)
    audit = prior.common.audit
    old_plan = scope.load(scope.P403/'trial-plan.json')
    old_report = scope.load(scope.CONTROL)
    old_scans,old = audit.score_archive(scope.LAST,old_plan['kernel_banner'],expected_pairs=None,require_first=False)
    scans,new = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==old_report['measurements']['0403'] and new==report['measurements']['0404'],
                  '0403/0404 independent physical replay differs')
    raw = (execution/'kernel.log').read_text()
    rows,_,n,d = prior.stage.staging.parse(raw)
    latches = prior.stage.staging.verified_latches(rows,prior.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    clk = cpu.cpu_receipts(raw,new,n,d)
    for key in ('measurements','moving_Core_IO','all_warm_GPU_writers'):
        report[key]['0403'] = old_report[key]['0403']
    report.update(per_scan_0403_0404=prior.flip.parent.parent.paired_ordinals({'0403':old_scans,'0404':scans}),
        stock_interaction_CPU={'0403':old_report['stock_interaction_CPU'],'0404':clk},
        native_render_producer=previous.producer_receipts(rows,latches,new['moving_GPU']),
        stable_60_fps_observed=report['stable_60_fps_observed'] and clk['selector_cleanup_qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'0404 requires independent restoration')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0403-0404.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0404-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    counts = report['native_render_producer']
    clk = report['stock_interaction_CPU']['0404']
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        stock_CPU_selector_cleanup_qualified=clk['selector_cleanup_qualified'],
        stock_CPU_warm_eleven_qualified=clk['warm_eleven_qualified'],
        exact_producer_claims=counts['qualified_claims'],newly_bound_warm_latches=counts['warm_motion_latches'])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
