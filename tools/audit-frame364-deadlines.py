#!/usr/bin/env python3
"""Compare missing-swap lead time and observed blank-window headroom after readback."""

import argparse
from collections import Counter
import json

from frame364_analysis import core_key, score, trace
from frame364_scope import BASE, REF363, load, pacing, require, sha


def producer_budget(report, rows, core, joined, to_ns):
    issued = trace.indexed(rows[trace.ISSUE],lambda row:row.id,'native issue')
    bound = trace.indexed((row for row in rows[trace.WRITER] if row.b),lambda row:row.b>>32,'bound generation')
    eligible = trace.indexed((row for row in rows[trace.SWAP] if not row.flags and row.c),lambda row:row.id,'eligible swap')
    by_token = trace.indexed(joined,lambda row:row['kernel_token'],'exact IO token')
    cores = trace.indexed(core,core_key,'Core job')
    selected = []
    for miss in report['frontend']['details']:
        callback = miss['returned_main_callback']
        if not (callback and miss['next_swap_within_stroke_tail']):
            continue
        generation = miss['next_swap']['generation']
        swap = eligible[generation]
        writer = bound.get(generation)
        issue = issued.get(writer.id) if writer else None
        submit = by_token.get(issue.a) if issue else None
        if submit is None:
            continue
        require(swap.c==((writer.c<<32)|writer.a) and (issue.b,issue.c)==
                (submit['driver_queue'],submit['driver_fence']), 'next swap and Core writer identity disagree')
        job = cores[core_key(submit)]
        returned = callback['returned_us']*1000
        created = job['made_us']*1000
        swap_time = to_ns(swap.tick)
        selected.append(dict(stroke=miss['stroke'],frame=miss['scan'],generation=generation,
            queue=job['queue'],ticket=job['ticket'],job=job['job'],kernel_token=issue.a,native_fence=issue.id,
            return_to_Core_creation_ns=created-returned,Core_creation_to_swap_ns=swap_time-created,
            swap_to_Core_commit_enqueue_ns=job['enq_ns']-swap_time,
            Core_creation_after_cutoff_ns=created-miss['deadline_ns']))

    def summarize(rows):
        fields = ('return_to_Core_creation_ns','Core_creation_to_swap_ns','swap_to_Core_commit_enqueue_ns')
        return dict(exact_next_writer=len(rows),
            Core_created_after_cutoff=sum(row['Core_creation_after_cutoff_ns']>0 for row in rows),
            timing_ns={name:{'p50':trace.quantile([r[name] for r in rows],.50),
                             'p95':trace.quantile([r[name] for r in rows],.95)} for name in fields})
    misses = Counter(r['stroke'] for r in report['frontend']['details'])
    return dict(all_strokes=summarize(selected),warm_strokes_3_to_13=summarize([r for r in selected if r['stroke']>=3]),
        no_new_swap_by_stroke={i:misses[i] for i in range(1,14)},exact_next_writers=selected,
        scope='The next accepted swap and its writer share exact identities. The preceding touch return '
              'is time-aligned and has no shared CA transaction ID.')


def slow_budget(report, rows, to_ns, scale):
    scans = {slot.frame:slot for slot in score.scan_windows(rows[trace.VBLANK],to_ns,scale,bracketed=True)}
    details = []
    for miss in report['slow_drag']['identity']['repeats']:
        scan = scans[miss['scan_slot']]
        next_copy = miss['next_certified_copy']
        relative = next_copy['relative_ns'] if next_copy and 'core' in next_copy else {}
        available = scan.end-scan.deadline
        completion = relative.get('observed_GPU_completion')
        visible = relative.get('cache_visible')
        details.append(dict(frame=miss['frame'],certified_same_CRC_copy=miss['same_CRC_copy'],
            native_fence=next_copy.get('native_fence') if next_copy else None,
            conservative_blank_time_after_cutoff_ns=available,
            EOP_observation_after_safe_blank_end_ns=completion-available if completion is not None else None,
            cache_visible_after_safe_blank_end_ns=visible-available if visible is not None else None))
    return dict(scans=details,
        remaining_late_if_copy_took_zero_ns=sum(r['cache_visible_after_safe_blank_end_ns'] is not None and
                                               r['cache_visible_after_safe_blank_end_ns']>0 for r in details),
        scope='Hold observed visibility and scan timing fixed. The zero-copy comparison is arithmetic and '
              'does not establish hardware completion time or compare candidate scheduling policies.')


def analyze(execution, report):
    pacing.check_restored(execution)
    input_names = ('independent-restore.json','result.json','kernel.log','core-wait-execution-analysis.json',
                   'kernel-IO-identity-analysis.json')
    raw = (execution/'kernel.log').read_text()
    rows,_,num,den = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    core = load(execution/'core-wait-execution-analysis.json')
    io = load(execution/'kernel-IO-identity-analysis.json')
    require(core['coverage_qualified'] and io['coverage_qualified'],'producer budget requires exact IO identification')
    to_ns = lambda tick:tick*num//den
    return dict(producer=producer_budget(report,rows,core['rows'],io['submits'],to_ns),
        slow_drag=slow_budget(report,rows,to_ns,num/den),input_sha256={name:sha(execution/name) for name in input_names})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archived-only',action='store_true')
    args = parser.parse_args()
    archive = BASE/'frame-host/archived-0363-deadlines.json'
    result = {'0363':analyze(REF363,load(archive))}
    if not args.archived_only:
        execution = BASE/'execution'
        pacing.check_restored(execution)
        comparison = execution/'motion-identity-0363-0364.json'
        result['0364'] = analyze(execution,load(comparison)['current_0364'])
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
