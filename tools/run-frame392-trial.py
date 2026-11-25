#!/usr/bin/env python3
"""Observe and restore the stock GPU operating-point trial, then compare the physical scans."""

from collections import Counter, defaultdict
from importlib import import_module

import frame344_log as trace

scope = import_module('prepare-frame392')
prior = import_module('run-frame391-trial')
previous = prior.previous
flip,stage = prior.flip,prior.stage
perf = import_module('analyze-native-perf-log')


def producer(raw, measured):
    rows,_,n,d = stage.staging.parse(raw)
    scans = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'DPU vblank')
    windows = [(scans[w['first_scan']].tick,scans[w['last_scan']].tick)
               for w in measured['moving_GPU']['ordinary']['windows']]
    issues = trace.indexed(rows[trace.ISSUE],lambda row:row.id,'native issue')
    eop = trace.indexed(rows[trace.EOP],lambda row:row.id,'native EOP')
    ready = trace.indexed(rows[trace.READY],lambda row:row.id,'native cache visibility')
    surface_ids = {row.c & 0xffffffff for row in rows[trace.SWAP] if not row.flags and row.c}
    writers = defaultdict(set)
    for row in rows[trace.WRITER]:
        if row.a in surface_ids and any(start<=issues[row.id].tick<end for start,end in windows):
            writers[row.id].add((row.a,row.c))
    samples = []
    completed_versions = set()
    for fence, versions in writers.items():
        if fence not in eop or fence not in ready:
            continue
        first,done,visible = (records[fence].tick*n//d for records in (issues,eop,ready))
        trace.require(first<=done<=visible,'GPU completion and cache observation are out of order')
        completed_versions.update(versions)
        samples.append((done-first,visible-done))
    return dict(issues=len(writers),completion_events=sum(fence in eop for fence in writers),
        cache_visible_fences=len(samples),distinct_cache_visible_surface_versions=len(completed_versions),
        issue_to_observed_EOP_ns={q:trace.quantile([s[0] for s in samples],p) for q,p in (('p50',.5),('p95',.95))},
        observed_EOP_to_cache_visible_ns={q:trace.quantile([s[1] for s in samples],p) for q,p in (('p50',.5),('p95',.95))},
        scope='All issued writes to observed display surfaces in physically bounded warm motion, including unlatched writers.')


def active_after_onset(scans, measured):
    first = {entry['stroke']:entry['first_new_scan'] for entry in measured['onset']['strokes'] if entry['stroke']>=3}
    warm = defaultdict(list)
    for row in scans:
        if row['workload']=='ordinary' and row['phase']=='active' and row['stroke'] in first:
            start = first[row['stroke']]
            if start is not None and row['frame']>=start:
                warm[row['stroke']].append(row['crc'])
    counts = Counter(kind for lane in warm.values() for kind in lane)
    sufficient = len(warm)==11 and all(len(lane)>=2 for lane in warm.values())
    return dict(stroke_count=len(warm),counts=dict(counts),qualified=sufficient and set(counts)=={'changed'},
                scope='Every full active scan from first visible response through the end of each warm input stroke.')


def score(execution, plan, *, trial=scope.TRIAL):
    comparison = previous.score_pair(execution,plan,trial=trial,measure_CA=False)
    parent_path = scope.P391/'trial-plan.json'
    parent = scope.load(parent_path)
    old_scans,old = previous.audit.score_archive(scope.LAST,parent['kernel_banner'],expected_pairs=None,require_first=False)
    archived = scope.load(scope.LAST/'scanout-comparison-0388-0391.json')
    trace.require(old==archived['measurements']['0391'],'0391 physical comparison did not replay')
    scans,new = previous.audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(new==comparison['measurements'][trial],trial+' physical comparison did not replay')
    raw = (execution/'kernel.log').read_text()
    old_raw = (scope.LAST/'kernel.log').read_text()
    vote = perf.analyze(raw,perf_index=5)
    trace.require(perf.analyze(old_raw)['native_request_accepted'] and vote['native_request_accepted'],
                  'native GPU vote or its paired bandwidth receipt differs')
    warm_scope = {'0391':active_after_onset(old_scans,old),trial:active_after_onset(scans,new)}
    comparison.update(measurements={**comparison['measurements'],'0391':old},
        per_scan_control_candidate=flip.parent.parent.paired_ordinals({'0391':old_scans,trial:scans}),
        native_GPU_profile=vote,all_warm_GPU_writers={'0391':producer(old_raw,old),trial:producer(raw,new)},
        previous_swap_candidates=prior.previous_candidates(execution,new),active_after_onset=warm_scope,
        stable_60_fps_observed=comparison['stable_60_fps_observed'] and warm_scope[trial]['qualified'])
    return comparison


def after_restore(execution, plan, result, before, code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
        result['static_root_comparison_passed'],'performance comparison requires independent restore')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        measured = score(execution,plan)
        name = 'scanout-comparison-0391-0392.json'
        stage.save_bounded(execution/name,measured,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0392-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=measured['stable_60_fps_observed'],
        native_GPU_profile=measured['native_GPU_profile'])


if __name__=='__main__':
    raise SystemExit(previous.runner.main(scope,after_restore_fn=after_restore))
