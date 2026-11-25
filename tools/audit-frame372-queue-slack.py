#!/usr/bin/env python3
"""Compare optimistically removable dispatch gaps with measured frame deadlines."""

import argparse
from collections import Counter
from importlib import import_module
import json
from pathlib import Path

from frame364_analysis import core_key, score, trace

pacing = import_module('audit-frame-pacing')


def measure(run, scoped_file):
    pacing.check_restored(run)
    return compare_slack(score.load(scoped_file),score.load(run/'core-wait-execution-analysis.json'))


def compare_slack(report, core):
    """Evaluate deadline slack once the caller has qualified the scan and Core capture."""
    trace.require(core['coverage_qualified'],'unqualified Core capture')
    source = trace.indexed(core['rows'],core_key,'Core job')
    cases = []
    for miss in report['slow_drag']['identity']['repeats']:
        target = miss['next_certified_copy']
        if not target or not target.get('core'):
            cases.append(dict(frame=miss['frame'],exact_writer=False))
            continue
        job = source[core_key(target['core'])]
        available = target['relative_ns']
        trace.require(available['core_enqueue']==job['enq_ns']-miss['cutoff_ns'] and
                      available['core_commit_begin']==job['start_ns']-miss['cutoff_ns'],
                      'copy and dispatch job timing differ')
        promotion = available['ready_promoted']
        visible = available['cache_visible']
        trace.require(promotion is not None and visible is not None and promotion>=visible and
                      promotion>=available['swap'],'ready order differs')
        wait = job['start_ns']-job['enq_ns']
        busy = job['busy_wait_ns']
        trace.require(0<=busy==sum(job['wait_ns'])<=wait, 'worker service within the queue wait differs')
        slack = wait-busy
        issue = target['runtime_issue_ns']['wall_ns']
        def left(advance):
            return max(available['swap'],promotion-advance)
        cases.append(dict(frame=miss['frame'],writer=target['native_fence'],job=target['core'],
            exact_writer=True,at_cutoff=target['stage'],ready_late_ns=promotion,
            full_queue_wait_ns=wait,preceding_measured_worker_ns=busy,
            preceding_worker_category_ns=job['wait_ns'],uncovered_FIFO_wait_ns=slack,
            late_if_uncovered_FIFO_wait_removed_ns=left(slack),
            runtime_issue_wall_ns=issue,late_if_runtime_issue_cost_zero_ns=left(issue),
            late_if_both_removed_ns=left(slack+issue)))
    candidates = Counter()
    fields = ('late_if_uncovered_FIFO_wait_removed_ns','late_if_runtime_issue_cost_zero_ns',
              'late_if_both_removed_ns')
    for case in cases:
        for field in fields:
            value = case.get(field)
            if value is not None and value<=0:
                candidates[field] += 1
    misses = report['swap_timing']['no_swap_cutoff_position_warm']
    return dict(slow_cases=cases,potentially_ready_by_cutoff=dict.fromkeys(fields,0)|dict(candidates),
        warm_no_swap=misses,
        scope=('Retain the FIFO phase-metered preceding work, which includes recording jobs between '
               'commit tickets. The unmeasured part is an optimistic bound and can include cleanup '
               'or locks. Fix accepted swaps and translate ready publication by the named arithmetic '
               'improvement. GPU dependencies, guard acquisition and scanout still constrain presentation.'))


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('execution',type=Path)
    cli.add_argument('scoped_report',type=Path)
    args = cli.parse_args()
    print(json.dumps(measure(args.execution,args.scoped_report),indent=2))
