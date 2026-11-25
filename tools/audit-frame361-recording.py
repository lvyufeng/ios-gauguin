#!/usr/bin/env python3
"""Locate repeated scans in the restored 0358/0360 producer pipeline."""

from bisect import bisect_right
from collections import Counter
import json

import frame344_log as trace
from frame351_display import PRESENT
import frame352_display as copy
from frame354_display import PROMOTE, TAKE
from frame357_display import BOUND
from frame357_replay import scan_windows
from frame358_display import KINDS
from frame360_scope import MAIN, REF358, load, pacing, require, sha

REF360 = MAIN/'research/tmp/gauguin-read-guard-worktree-20261120/research/tmp/frame-360/execution'
RESULT360 = 'e5dbbba3fa55d1ce89522cea75a4bf884ac27bef139f764825e6680a0c6cb0f1'
PROOF360 = 'e09133e26ff43536b6dcd4cb4fca7acd0d6b852fe47f844069489ca2580eafe5'


def job_id(row):
    return (row['queue'],row['ticket'],row['job'])


def audit(path):
    result = pacing.check_restored(path)
    names = ('frame-scanout-analysis','kernel-IO-analysis','kernel-IO-identity-analysis',
             'core-wait-execution-analysis')
    files = [path/(name+'.json') for name in names]
    frame,kernel,identity,core = map(load,files)
    require(all(data['coverage_qualified'] for data in (kernel,identity,core)),
            'missing Core or kernel coverage')
    raw = path/'kernel.log'
    text = raw.read_text()
    rows,_,numer,denom = trace.parse(text,extra_kinds=(PRESENT,copy.WAKE,*KINDS))

    def ns(tick):
        return tick*numer//denom

    slots = {slot.frame:slot for slot in scan_windows(rows[trace.VBLANK],ns,numer/denom,bracketed=True)}
    display = copy.analyze(text,frame,extra_kinds=KINDS)
    issues,eops,visible,promotions,claims,attempts = (
        trace.indexed(rows[k],lambda event:event.id,'producer event') for k in
        (trace.ISSUE,trace.EOP,trace.READY,PROMOTE,BOUND,trace.ATTEMPT))
    require(issues.keys()==eops.keys()==visible.keys(),'incomplete observation of native fences')
    takes = trace.indexed(rows[TAKE],lambda row:row.c,'timed hardware scan')
    swaps = [event for event in rows[trace.SWAP] if not event.flags and event.c]
    swap_times = [ns(event.tick) for event in swaps]
    used = sorted((ns(event.tick),attempts[event.id].a) for event in rows[trace.RESULT] if event.a)
    used_clock = [entry[0] for entry in used]
    writers = trace.indexed(rows[trace.WRITER],lambda event:(event.a,event.c),'surface writer version')
    bound = trace.indexed((r for r in rows[trace.WRITER] if r.b),lambda event:event.b,'ticket writer')
    linked = trace.indexed(identity['submits'],lambda row:row['kernel_token'],'Core submit token')
    jobs = trace.indexed(core['rows'],job_id,'Core job')
    calls = trace.indexed(kernel['rows'],lambda row:row['token'],'kernel I/O token')
    phase_names = kernel['phase_names']['70']

    def producer(writer, cutoff):
        issue = issues[writer.id]
        if ns(issue.tick)<=cutoff:
            if ns(eops[writer.id].tick)>cutoff:
                return 'issued_awaiting_observed_EOP',None
            if ns(visible[writer.id].tick)>cutoff:
                return 'EOP_observed_awaiting_cache_visibility',None
            return 'visible',None

        joined = linked.get(issue.a)
        if not joined:
            return 'issued_late_without_joined_Core_job',None
        require((joined['driver_queue'],joined['driver_fence'])==(issue.b,issue.c),
                'native fence carried a different logical ticket')
        job = jobs[job_id(joined)]
        request = calls[issue.a]
        if job['enq_ns']>cutoff:
            return 'Core_enqueue_late',job
        if job['start_ns']>cutoff:
            return 'Core_queue',job
        for name,start,end in zip(phase_names,request['begin'],request['end'],strict=True):
            if start<=cutoff<end:
                return 'IO_'+name,job
        return 'Core_recording_or_IO_between_trace_phases',job

    totals = {phase:Counter() for phase in ('active','release')}
    details = []
    for window in display['windows']:
        lane = window['phase']
        for item in window['intervals']:
            if item['after_copy_boundary_check']!='repeated':
                continue
            phase = totals[lane]
            scan = item['previous_frame']
            slot = slots.get(scan)
            if not slot:
                phase['unqualified_scan_bracket']+=1
                continue
            if scan in takes:
                phase['timed_selection']+=1
                continue
            last_index = bisect_right(used_clock,slot.opening)-1
            last = used[last_index][1] if last_index>=0 else 0
            latest_index = bisect_right(swap_times,slot.deadline)-1
            latest = swaps[latest_index] if latest_index>=0 else None
            if not latest or latest.id<=last:
                phase['no_new_surface_swap_by_cutoff']+=1
                continue

            surface,version = latest.c&0xffffffff,latest.c>>32
            ticket = latest.id<<32|surface
            exact = bound.get(ticket)
            writer = writers.get((surface,version))
            require(not exact or (writer==exact and latest.id in claims),'exact writer claim differs')
            if writer is None:
                phase['no_surface_version_in_trace']+=1
                continue
            stage,job = producer(writer,slot.deadline)
            if stage=='visible':
                promote = promotions.get(latest.id)
                stage = 'promoted' if promote and ns(promote.tick)<=slot.deadline else 'visible_awaiting_promotion'
            key = ('exact_' if exact else 'version_only_')+stage
            phase[key]+=1
            entry = dict(phase=lane,stroke=window['stroke'],scan=scan,deadline_ns=slot.deadline,
                         generation=latest.id,surface=surface,version=version,native_fence=writer.id,
                         exact_ticket=bool(exact),stage=stage)
            if job:
                entry.update(queue=job['queue'],ticket=job['ticket'],job=job['job'],
                             enqueued_ns=job['enq_ns'],started_ns=job['start_ns'])
            details.append(entry)
    for phase,counts in totals.items():
        require(sum(counts.values())==display['phases'][phase]['verified_full_frame_counts']['repeated'],
                'repeat counts disagree with the output classification')
    matched = [jobs[job_id(row)] for row in identity['submits']]
    timings = {key:trace.quantile([row[key] for row in matched],.95) for key in
               ('core_queue_wait_us','core_observed_busy_in_wait_us','own_recording_execution_us','own_commit_us')}
    encode = core['render_phase_order'].index('encode')
    timings['render_encode_us'] = trace.quantile([r['render_ns'][encode]/1000 for r in matched],.95)
    return dict(trial=result['trial'],repeated_scans={phase:dict(counts) for phase,counts in totals.items()},
        matched_core_rows=len(matched),p95_us=timings,producer_details=details,
        input_sha256={p.name:sha(p) for p in (raw,*files,path/'result.json',path/'independent-restore.json')})


def report():
    pacing.references()
    require(sha(REF360/'result.json')==RESULT360 and sha(REF360/'independent-restore.json')==PROOF360,
            '0360 restored receipt differs')
    return dict(scope='Newest accepted surface swap at the conservative start cutoff. An unbound writer version is a correlation.',
                trials=[audit(p) for p in (REF358,REF360)],device_commands=0)


if __name__=='__main__':
    print(json.dumps(report(),indent=2))
