#!/usr/bin/env python3
"""Compare qualified, boot-local queue joins in the same 13-stroke workload."""

import json
from math import ceil
import re

from core342_log import stats
from core343_scope import REFERENCE, REFERENCE_RESULT, require, sha, load
from kernel342_log import PHASES
from ui_trace_log import parse as parse_ui

ISSUE = PHASES[70].index('runtime_issue')
FRAME_US = 1_000_000 / 60


def strokes(kernel):
    header = parse_ui(kernel)['header']
    start = re.findall(r'SWEET UI SCRIPT: begin stroke=(\d+) tick=(\d+) origin=synthetic', kernel)
    release = re.findall(r'SWEET UI SCRIPT: end stroke=(\d+) tick=(\d+) events=34;', kernel)
    require([int(i) for i, _ in start] == [int(i) for i, _ in release] == list(range(13)),
            'script stroke sequence incomplete')
    to_us = lambda tick: int(tick) * header['numer'] // header['denom'] // 1000
    windows = [(to_us(a), to_us(b) + 1) for (_, a), (_, b) in zip(start, release)]
    require(all(a < b and (i == 0 or a > windows[i-1][1]) for i, (a, b) in enumerate(windows)),
            'script stroke time bounds overlap or are reversed')
    return windows


def percentile(data):
    if not data:
        return None
    result = stats(data)
    return dict(p50=result['median'], p95=result['p95'],
                p99=sorted(data)[ceil(.99 * len(data)) - 1], max=result['max'])


def summarize(items):
    wall, low, high, waits, completions = [], [], [], [], []
    for row, submit in items:
        issue = submit['phases'][ISSUE]
        require(0 <= issue['CPU_lower_ns'] <= issue['CPU_upper_ns'] <= issue['wall_ns']
                and issue['wall_ns'] == issue['end_ns'] - issue['begin_ns'] > 0,
                'unqualified runtime_issue CPU or wall time')
        low.append(issue['CPU_lower_ns'])
        high.append(issue['CPU_upper_ns'])
        wall.append(issue['wall_ns'])
        waits.append(row['core_queue_wait_us'])
        completions.append(row['commit_done_us'])
    return dict(count=len(items), runtime_issue_CPU_lower_ns=percentile(low),
                runtime_issue_CPU_upper_ns=percentile(high), runtime_issue_wall_ns=percentile(wall),
                core_queue_wait_us=percentile(waits), commit_done_us=percentile(completions),
                core_queue_wait_over_frame_budget=sum(wait > FRAME_US for wait in waits),
                runtime_issue_mean_CPU_ns=([sum(low)/len(low), sum(high)/len(high)] if items else None))


def trial_metrics(directory, verdict):
    collection = load(directory/'collection-analysis.json')
    join = load(directory/'kernel-IO-identity-analysis.json')
    core = load(directory/'core-wait-execution-analysis.json')
    identity = load(directory/'queue-identity-analysis.json')
    require(all(record['coverage_qualified'] and not record['errors']
                for record in (collection, join, core, identity))
            and verdict['legacy_observation_state'] == 'BC336-cache-reuse-observed-root-restored',
            'capture or configuration unqualified for timing comparison')
    script = strokes((directory/'kernel.log').read_text())
    start, end = script[0][0], script[-1][1]
    require(collection['script_window_us'] == join['full_script_bounds_us'] == [start, end],
            'IO, Core and optical alignment must use the same script boundaries')
    key = lambda row: (row['queue'], row['ticket'])
    cores = {key(row): row for row in core['rows'] if start <= row['made_us'] < end}
    ids = {key(row): row for row in identity['buffers'] if start <= row['made_us'] < end}
    require(len(cores) == len(ids) == join['complete_submit_count'] == len(join['submits']) > 0
            and set(cores) == set(ids) == {key(row) for row in join['submits']},
            'missing, duplicate or unmatched scripted queue identity')
    items = []
    for submit in join['submits']:
        row = cores[key(submit)]
        ident = ids[key(submit)]
        tid, drvq, _bo, _offset, _words, fence = row['io_identity']
        require(row['job'] == submit['job'] and row['made_us'] == ident['made_us']
                and row['object'] == ident['object'] and submit['kernel_selector'] == 70
                and (submit['caller_thread'], submit['driver_queue'], submit['driver_fence']) == (tid, drvq, fence),
                'Core identity differs from joined driver submit')
        items.append((row, submit))

    def active(row):
        return next((i for i, (a, b) in enumerate(script) if a <= row['made_us'] < b), None)

    by_stroke = []
    for i, (a, b) in enumerate(script):
        next_start = script[i+1][0] if i < 12 else b
        by_stroke.append(dict(stroke=i, begin_us=a, release_exclusive_us=b,
                              active=summarize([(r, s) for r, s in items if a <= r['made_us'] < b]),
                              through_interstroke_gap=summarize([(r, s) for r, s in items
                                                                 if a <= r['made_us'] < next_start])))
    queues = {}
    for row, submit in items:
        queues.setdefault(row['queue'], []).append((row, submit))
    windows, total_windows = [], 0
    for queue, pairs in queues.items():
        pairs.sort(key=lambda pair: pair[0]['ticket'])
        for i in range(len(pairs) - 11):
            run = pairs[i:i+12]
            first, last = run[0][0], run[-1][0]
            if last['ticket'] - first['ticket'] != 11:
                continue
            total_windows += 1
            growth = last['core_queue_wait_us'] - first['core_queue_wait_us']
            if growth < FRAME_US:
                continue
            windows.append(dict(queue=queue, first_ticket=first['ticket'], last_ticket=last['ticket'],
                                first_job=first['job'], last_job=last['job'],
                                first_stroke=active(first), last_stroke=active(last),
                                start_relative_to_script_us=first['made_us']-start,
                                wait_growth_us=growth, mean_arrival_us=(last['enq_ns']-first['enq_ns'])/11000,
                                mean_commit_start_us=(last['start_ns']-first['start_ns'])/11000,
                                program_new_BO_calls=sum(r['newbo_counts'][0] for r, _ in run),
                                phases=summarize(run)))
    tails = []
    for row, submit in sorted(items, key=lambda p: p[0]['core_queue_wait_us'], reverse=True)[:20]:
        tails.append(dict(queue=row['queue'], ticket=row['ticket'], job=row['job'],
                          driver_queue=submit['driver_queue'], fence=submit['driver_fence'],
                          stroke=active(row), relative_to_script_us=row['made_us']-start,
                          wait_us=row['core_queue_wait_us'], done_us=row['commit_done_us'],
                          runtime_issue=submit['phases'][ISSUE]))
    return dict(script_bounds_us=[start, end], full_script=summarize(items), per_stroke=by_stroke,
                queue_submit_counts={queue: len(pairs) for queue, pairs in queues.items()},
                consecutive_12_ticket_windows=total_windows, sustained_wait_growth_windows=len(windows),
                largest_growth=sorted(windows, key=lambda r: r['wait_growth_us'], reverse=True)[:20],
                longest_core_waits=tails)


def compare(directory, verdict, *, reference=REFERENCE):
    require(sha(reference/'result.json') == REFERENCE_RESULT, '0342 comparison provenance failed')
    reference_result = load(reference/'result.json')
    require(reference_result['restored'] and reference_result['independent_restore_verified']
            and verdict['restored'] and verdict['independent_restore_verified']
            and verdict['static_root_comparison_passed'], 'independent readback must precede comparison')
    baseline = trial_metrics(reference, reference_result)
    candidate = trial_metrics(directory, verdict)
    a, b = baseline['full_script'], candidate['full_script']
    delta_issue = {q: [b['runtime_issue_CPU_lower_ns'][q] - a['runtime_issue_CPU_upper_ns'][q],
                        b['runtime_issue_CPU_upper_ns'][q] - a['runtime_issue_CPU_lower_ns'][q]]
                   for q in ('p50', 'p95', 'p99', 'max')}
    report = dict(state='0343-compared-with-qualified-0342-capture',
                  source_0342_sha256=REFERENCE_RESULT, baseline_0342=baseline, candidate_0343=candidate,
                  delta_runtime_issue_CPU_ns_bounds=delta_issue,
                  delta_p95_core_queue_wait_us=b['core_queue_wait_us']['p95']-a['core_queue_wait_us']['p95'],
                  delta_p95_commit_done_us=b['commit_done_us']['p95']-a['commit_done_us']['p95'],
                  alignment='same script and stroke ordinal, with queue/ticket/job and driver identities valid within each boot',
                  physical_FPS_qualified=False, device_commands=0)
    raw = (json.dumps(report, indent=2) + '\n').encode()
    require(len(raw) <= 2_000_000, '0343 comparison artifact exceeded its storage bound')
    with (directory/'runtime343-comparison.json').open('xb') as out:
        out.write(raw)
    return {key: value for key, value in report.items() if key not in ('baseline_0342', 'candidate_0343')}
