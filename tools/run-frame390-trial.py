#!/usr/bin/env python3
"""Observe the frozen CA timeline and score the restored phone independently."""

from importlib import import_module

import frame344_log as trace
import frame390_timeline as timeline

scope = import_module('prepare-frame390')
runner = import_module('run-frame374-trial')
old_run = import_module('run-frame388-trial')
previous = import_module('run-frame389-trial')
audit = scope.prior.audit
stage,flip = audit.stage,audit.flip


def score_pair(execution, plan, *, trial='0390', measure_CA=True):
    reference = scope.load(scope.P388/'trial-plan.json')
    old_scans, old = audit.score_archive(scope.REFERENCE,reference['kernel_banner'])
    archived = scope.load(scope.P388/'restored-DPU-comparison.json')['measurements']['0388']
    trace.require(old==archived,'0388 independent timing control could not be reproduced')
    new_scans, new = audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    raw = (execution/'kernel.log').read_text()
    aligned = old_run.deadline_receipts(raw,new['ca_phase'])
    trace.require(aligned['qualified'],trial+' DPU deadline receipt differs')
    per_scan = flip.parent.parent.paired_ordinals({'0388':old_scans,trial:new_scans})
    rows,_,n,d = stage.staging.parse(raw)
    latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
    first = {}
    if measure_CA:
        try:
            first = timeline.measure(execution,raw,rows,n,d,latches,new_scans)
        except (KeyError, OSError, ValueError) as error:
            first = dict(trace_error=str(error))
    try:
        core = previous.moving_core(execution,raw,new['moving_GPU'])
    except (KeyError, OSError, ValueError) as error:
        core = dict(trace_error=str(error))
    stable = (new['onset']['warm']['moving_swipes']==11 and
              new['onset']['warm']['moving_scan_counts'].get('repeated',0)==0 and
              new['metrics']['slow_drag']['scans']['repeated']==0)
    return dict(state=f'0388-{trial}-compared-after-independent-restore',
        measurements={'0388':old,trial:new},deadline_dispatch=aligned,per_scan=per_scan,
        first_CA_timeline=first,moving_Core_IO=core,stable_60_fps_observed=stable)


def after_restore(execution, plan, result, before, code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'CA and display scoring requires independent restoration')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        scored = score_pair(execution,plan)
        name = 'scanout-comparison-0388-0390.json'
        stage.save_bounded(execution/name,scored,2_000_000)
    except (KeyError, OSError, ValueError) as error:
        result.update(state='0390-display-measurement-incomplete-root-restored',comparison_error=str(error))
        return
    ca = scored['first_CA_timeline']
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=scored['stable_60_fps_observed'],
        warm_exact_CA_swaps=ca.get('warm_matched',0),
        warm_exact_CA_first_inclusion=ca.get('warm_with_first_inclusion',0))


if __name__=='__main__':
    raise SystemExit(runner.main(scope,after_restore_fn=after_restore))
