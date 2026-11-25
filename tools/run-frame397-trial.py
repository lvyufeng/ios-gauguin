#!/usr/bin/env python3
"""Measure 0397 allocation overlap and vblank content after independent restore."""

from collections import Counter
from importlib import import_module

import frame344_log as trace
import frame393_timeline as timeline

scope = import_module('prepare-frame397')
prior = import_module('run-frame393-trial')
stock, flip, stage = prior.prior, prior.flip, prior.stage
common = prior.previous


def allocation_waits(execution, raw, measured):
    rows, _, n, d = stage.staging.parse(raw)
    edges = trace.indexed(rows[trace.VBLANK], lambda row:row.id, 'DPU scan')
    windows = [(edges[w['first_scan']].tick*n//d, edges[w['last_scan']].tick*n//d)
               for w in measured['moving_GPU']['ordinary']['windows']]
    source = scope.load(execution/'kernel-IO-analysis.json')
    trace.require(source['coverage_qualified'] and source['phase_names']['66'][4]=='backing_allocation_pressure_retry',
        'incomplete native allocation capture')
    counts, waits = Counter(), []
    for row in source['rows']:
        if row['selector']!=66 or not any(begin<=row['first_ns']<end for begin,end in windows):
            continue
        if row['result']:
            counts['failed'] += 1
            continue
        trace.require(row['mask']&(1<<5) and bool(row['waits'])==bool(row['wait_ns']), 'allocation receipt differs')
        kind = 'fresh' if row['mask']&(1<<4) else 'cached'
        counts[kind+('_waited' if row['waits'] else '_immediate')] += 1
        if row['waits']:
            waits.append(dict(token=row['token'], allocation=kind, bytes=row['bytes'],
                completion_gate_ns=row['phases'][2]['wall_ns'], unlocked_interval_ns=row['wait_ns']))
    return dict(counts=dict(counts), waited=waits)


def score(execution, plan):
    trial = scope.TRIAL
    activation = scope.load(execution/'edr-activation.json')
    trace.require(activation['active'] and activation['code_checks_qualified'] and activation['once_abi_qualified'],
        '0397 compositor helper did not activate')
    report = common.score_pair(execution,plan,trial=trial,measure_CA=False)
    control = scope.load(scope.P393/'trial-plan.json')
    archived = scope.load(scope.LAST/'scanout-comparison-0395-0393.json')
    old_scans,old = common.audit.score_archive(scope.LAST,control['kernel_banner'],expected_pairs=None,require_first=False)
    scans,new = common.audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==archived['measurements']['0393'] and new==report['measurements'][trial], '0393/0397 physical replay differs')
    raw,old_raw = ((path/'kernel.log').read_text() for path in (execution, scope.LAST))
    vote = stock.perf.analyze(raw,perf_index=5)
    trace.require(vote['native_request_accepted'] and archived['native_GPU_profile']['native_request_accepted'],
        '0393/0397 native GPU operating point differs')
    total,during,valid = map(int,trace.one(r'^SWEET BC397: pending_hits=(\d+) capture_hits=(\d+) valid=(\d+)$',raw,
        'resident BO overlap counter'))
    trace.require(valid==1 and 0<=during<=total,'resident BO overlap counter is invalid')
    active = stock.active_after_onset(scans,new)
    try:
        allocations = {'0393':allocation_waits(scope.LAST,old_raw,old), trial:allocation_waits(execution,raw,new)}
    except (KeyError,OSError,ValueError) as error:
        allocations = dict(trace_error=str(error))
    try:
        rows,_,n,d = stage.staging.parse(raw)
        latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
        causal = timeline.measure(execution,raw,rows,n,d,latches,scans)
    except (KeyError,OSError,ValueError) as error:
        causal = dict(trace_error=str(error))
    report.update(measurements={**report['measurements'],'0393':old},
        per_scan_0393_0397=flip.parent.parent.paired_ordinals({'0393':old_scans,trial:scans}),
        first_CA_timeline=causal, allocation_waits=allocations, resident_reuse=dict(total=total,captured=during,observed=during>0),
        all_warm_GPU_writers={'0393':stock.producer(old_raw,old),trial:stock.producer(raw,new)},
        native_GPU_profile=vote, motion_after_onset=active,
        stable_60_fps_observed=report['stable_60_fps_observed'] and active['qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
        '0397 scoring requires independent restoration')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0393-0397.json'
        stage.save_bounded(execution/name,report,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0397-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        resident_reuse=report['resident_reuse'])


if __name__=='__main__':
    raise SystemExit(common.runner.main(scope,after_restore_fn=after_restore))
