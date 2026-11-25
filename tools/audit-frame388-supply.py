#!/usr/bin/env python3
"""Bound the restored 0388 frame supply and verify the moving Core/IO joins."""

from collections import Counter
from importlib import import_module
import json
from statistics import median
import sys

import frame344_log as trace
import kernel342_log

restored = import_module('audit-frame388-restored')
scope = restored.scope
BASE = scope.BASE
AUX = scope.MAIN/'research/tmp/gauguin-ca-receipt-analysis-worktree-20261123/tools'
INPUTS = restored.PINS | {
    'kernel-IO-analysis.json': 'ee32f6655a136a574fe69358c71d111bf2f1172912bf1138dea14ac42d60c5aa',
    'kernel-IO-identity-analysis.json': 'e930831ba6e8307c05983fd1d6df721ed102326dea6e3789679124ddf3fc9902',
}
PUBLISHED = '755a1199da3edf04906ee07e4a246b5fbc2db176b6398f9e238a487de6f47a83'


def verified_motion(execution, rows, latches, windows, n, d):
    io, joined, core = (scope.load(execution/(name+'.json')) for name in (
        'kernel-IO-analysis','kernel-IO-identity-analysis','core-wait-execution-analysis'))
    trace.require(io['coverage_qualified'] and joined['errors'] == {'unqualified_user_core':1} and
                  core['errors'] == {'invalid_category_or_submit_partition':1,'extended_record_count':1},
                  '0388 partial Core diagnostic scope differs')
    rejoined = kernel342_log.join(io,core,joined['full_script_bounds_us'])
    trace.require(rejoined == joined, '0388 per-record Core/IO joins differ on replay')
    submits = trace.indexed((row for row in io['rows'] if row['selector'] == 70 and not row['result']),
                            lambda row:row['token'], 'kernel submit')
    jobs = trace.indexed(joined['submits'],lambda row:row['kernel_token'],'submit identity')
    workers = trace.indexed(core['rows'],lambda row:(row['queue'],row['ticket'],row['job']),'Core job')
    issues = trace.indexed(rows[trace.ISSUE],lambda row:row.id,'native issue')
    counts, records = Counter(), []
    for window in windows:
        for frame in range(window['first_scan'],window['last_scan']+1):
            if frame not in latches:
                continue
            counts['eligible_latches'] += 1
            latch = latches[frame]
            issue = issues[latch['fence']]
            if issue.a not in jobs:
                counts['missing_valid_join'] += 1
                continue
            job, submit = jobs[issue.a], submits[issue.a]
            worker = workers[job['queue'],job['ticket'],job['job']]
            entry, emitted, swap = submit['first_ns'], issue.tick*n//d, latch['swap_tick']*n//d
            trace.require((issue.b,issue.c) == (submit['queue'],submit['fence']) ==
                          (job['driver_queue'],job['driver_fence']) and entry <= emitted <= submit['last_ns'],
                          'kernel submit failed to own its scanout writer')
            if entry < swap:
                counts['kernel_entered_before_swap'] += 1
                continue
            wait = worker['start_ns']-worker['enq_ns']
            inside = max(0,min(entry,worker['start_ns'])-max(swap,worker['enq_ns']))
            occupied = dict(zip(core['category_order'],worker['wait_ns'],strict=True))
            trace.require(inside <= wait and sum(occupied.values()) == worker['busy_wait_ns'] <= wait,
                          'Core wait accounting differs')
            records.append(dict(swap_to_issue=emitted-swap, swap_to_kernel_entry=entry-swap,
                kernel_entry_to_issue=emitted-entry, Core_queue_wait=wait, Core_queue_in_pre_kernel=inside,
                prior_render_and_commit=occupied['render']+occupied['commit']))
    trace.require(len(records) == 121 and not counts['missing_valid_join'] and
                  sum((len(records),counts['kernel_entered_before_swap'])) == counts['eligible_latches'],
                  'exact moving-frame cohort differs')
    threshold = trace.quantile([row['swap_to_issue'] for row in records],.9)
    tail = [row for row in records if row['swap_to_issue'] >= threshold and row['swap_to_kernel_entry'] > 0]
    return dict(latches=dict(counts), qualified_samples=len(records), timing_ns={
        key:dict(p50=trace.quantile([row[key] for row in records],.5),
                 p95=trace.quantile([row[key] for row in records],.95)) for key in records[0]},
        slowest_decile_samples=len(tail),
        median_Core_queue_fraction_of_pre_kernel=median(
            row['Core_queue_in_pre_kernel']/row['swap_to_kernel_entry'] for row in tail),
        median_render_commit_fraction_of_Core_wait=median(
            row['prior_render_and_commit']/row['Core_queue_wait'] for row in tail if row['Core_queue_wait']),
        full_Core_collection_qualified=False)


def analyze():
    terminal = BASE/'execution'
    trace.require(all(scope.sha(terminal/name) == value for name,value in INPUTS.items()) and
                  scope.sha(BASE/'restored-DPU-comparison.json') == PUBLISHED, '0388 retained evidence differs')
    stored = scope.load(BASE/'restored-DPU-comparison.json')
    trace.require(not stored['stable_60_fps_observed'], 'unexpected stability result')
    scans, measured = restored.score_archive(terminal,scope.load(BASE/'trial-plan.json')['kernel_banner'])
    trace.require(measured == stored['measurements']['0388'], '0388 physical score was not reproduced')
    raw = (terminal/'kernel.log').read_text()
    rows, _, n, d = restored.stage.staging.parse(raw)
    latches = restored.stage.staging.verified_latches(rows,restored.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    sys.path.append(str(AUX))
    replay = import_module('audit-frame384-restored')
    arrivals = replay.frame_supply(rows,scans,latches)
    windows = measured['moving_GPU']['ordinary']['windows']
    edges = trace.indexed(rows[trace.VBLANK],lambda row:row.id,'DPU edge')
    drag = replay.drag_deadlines(dict(slow_drag_repeat_waits=measured['drag_repeats']),raw,latches,edges,n,d,192)
    return dict(state='0388-restored-exact-frame-supply-and-Core-wait', device_commands=0,
        input_sha256=INPUTS, source_comparison_sha256=PUBLISHED, optimistic_supply=arrivals,
        exact_ordinary_motion_Core_IO=verified_motion(terminal,rows,latches,windows,n,d), fixed_drag_cutoffs=drag)


if __name__ == '__main__':
    print(json.dumps(analyze(),indent=2))
