#!/usr/bin/env python3
"""Run the frozen 0389 Core-only test, then score independently restored captures."""

from collections import Counter
from importlib import import_module

import frame344_log as trace
import kernel342_log

scope = import_module('prepare-frame389')
old_run = import_module('run-frame388-trial')
audit = scope.audit
flip, stage = audit.flip, audit.stage


def moving_core(execution, raw, motion):
    native, stored, core = (scope.load(execution/(name+'.json')) for name in (
        'kernel-IO-analysis','kernel-IO-identity-analysis','core-wait-execution-analysis'))
    trace.require(native['coverage_qualified'] and
        kernel342_log.join(native,core,stored['full_script_bounds_us'])==stored,
        'Core and kernel join failed replay')
    rows, _, n, d = stage.staging.parse(raw)
    evidence = flip.latch_receipts(raw,rows)
    latches = stage.staging.verified_latches(rows,evidence['accepted_by_scan'])
    issues = trace.indexed(rows[trace.ISSUE],lambda row:row.id,'native issue')
    submits = trace.indexed((r for r in native['rows'] if r['selector']==70 and not r['result']),
                            lambda row:row['token'],'kernel submit')
    joins = trace.indexed(stored['submits'],lambda row:row['kernel_token'],'Core/IO join')
    jobs = trace.indexed(core['rows'],lambda row:(row['queue'],row['ticket'],row['job']),'Core job')
    counts = Counter()
    measurements = []
    for window in motion['ordinary']['windows']:
        for scan in range(window['first_scan'],window['last_scan']+1):
            if scan not in latches:
                continue
            counts['eligible_latches'] += 1
            latch = latches[scan]
            issue = issues[latch['fence']]
            if issue.a not in joins:
                counts['no_valid_Core_join'] += 1
                continue
            job, submit = joins[issue.a], submits[issue.a]
            worker = jobs[job['queue'],job['ticket'],job['job']]
            entry, emitted, accepted = submit['first_ns'], issue.tick*n//d, latch['swap_tick']*n//d
            trace.require((issue.b,issue.c)==(submit['queue'],submit['fence'])==
                          (job['driver_queue'],job['driver_fence']) and entry<=emitted<=submit['last_ns'],
                          'exact native issue identity or ordering differs')
            if entry < accepted:
                counts['kernel_entered_before_swap'] += 1
                continue
            counts['qualified_samples'] += 1
            if 'render_ns' not in worker or worker.get('fine_flags') or worker.get('detail_flags'):
                counts['missing_render_detail'] += 1
                continue
            measurements.append(dict(
                swap_to_issue=emitted-accepted, kernel_entry_to_issue=emitted-entry,
                core_queue_wait=worker['start_ns']-worker['enq_ns'], render=worker['exec_ns'][2],
                encode=worker['render_ns'][4], packets=worker['render_ns'][5],
                render_calls=worker['render_calls']))
    trace.require(measurements and sum(counts[key] for key in ('no_valid_Core_join','kernel_entered_before_swap',
                  'qualified_samples'))==counts['eligible_latches'],'exact moving-frame cohort is incomplete')
    render_calls = [row.pop('render_calls') for row in measurements]
    return dict(counts=dict(counts), detail_samples=len(measurements),
        median_render_calls=trace.quantile(render_calls,.5),
        timing_ns={key:{label:trace.quantile([row[key] for row in measurements],q)
                        for label,q in (('p50',.5),('p95',.95))} for key in measurements[0]},
        full_core_collection_qualified=core['coverage_qualified'],core_errors=core['errors'])


def score_pair(execution, plan):
    old, new = scope.REFERENCE, execution
    archived = scope.load(scope.P388/'restored-DPU-comparison.json')['measurements']['0388']
    reference, candidate = (scope.load(scope.P388/'trial-plan.json'), plan)
    old_scans, old_metrics = audit.score_archive(old,reference['kernel_banner'])
    trace.require(old_metrics==archived,'0388 score differs from the published independent replay')
    new_scans, new_metrics = audit.score_archive(new,candidate['kernel_banner'],
                                               expected_pairs=None,require_first=False)
    old_raw,new_raw = ((path/'kernel.log').read_text() for path in (old,new))
    deadline = old_run.deadline_receipts(new_raw,new_metrics['ca_phase'])
    trace.require(deadline['qualified'],'0389 DPU deadline receipts are incomplete')
    per_scan = flip.parent.parent.paired_ordinals({'0388':old_scans,'0389':new_scans})
    core_data = {}
    for name, path, raw, metrics in (('0388',old,old_raw,old_metrics),('0389',new,new_raw,new_metrics)):
        try:
            core_data[name] = moving_core(path,raw,metrics['moving_GPU'])
        except (KeyError, OSError, ValueError) as error:
            core_data[name] = dict(trace_error=str(error))
    return dict(state='0388-0389-compared-after-independent-restore',
        measurements={'0388':old_metrics,'0389':new_metrics},deadline_dispatch=deadline,
        moving_Core_IO=core_data,per_scan=per_scan,
        stable_60_fps_observed=all(new_metrics['metrics'][name]['scans']['repeated']==0
                                 for name in ('warm_active','slow_drag')))


def after_restore(execution, plan, result, before, code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'],'independent recovery must precede comparison')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    original_state = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        comparison = score_pair(execution,plan)
        stage.save_bounded(execution/'scanout-comparison-0388-0389.json',comparison,2_000_000)
    except (KeyError, OSError, ValueError) as error:
        result.update(state='0389-independent-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,core_and_legacy_state=original_state,
        DPU_independent_physical_FPS_qualified=True,comparison='scanout-comparison-0388-0389.json',
        stable_60_fps_observed=comparison['stable_60_fps_observed'])


if __name__=='__main__':
    raise SystemExit(old_run.runner.main(scope,after_restore_fn=after_restore))
