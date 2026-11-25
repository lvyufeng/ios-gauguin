#!/usr/bin/env python3
"""Decompose qualified0338 CPU paths; retain signed completion overlap."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from core338_scope import BASE,WORK,PRIOR,load,sha
from core338_log import stats


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    compared=BASE/'post-analysis/comparison-summary.json';comparison=load(compared)
    assert comparison['state']=='0338-qualified-raw-comparison-and-core-queue-split'
    for p,h in comparison['input_pins'].items():assert sha(p)==h,p
    execution=BASE/'execution';core=load(execution/'core-wait-execution-analysis.json')
    c4=load(execution/'c4-queue-analysis.json');assert core['coverage_qualified'] and c4['coverage_qualified']
    lifecycle={(r['object'],r['made_us']):r for r in c4['buffers']}
    begin,end=comparison['candidate338']['script_bounds_us'];rows=[]
    for r in core['rows']:
        if not begin<=r['made_us']<end:continue
        t={int(k):v for k,v in lifecycle[r['object'],r['made_us']]['times_us'].items()}
        done=lifecycle[r['object'],r['made_us']]['existing_timeline']['done_us']
        earlier_commit_ns=sum(max(0,min(other['end_ns'],r['start_ns'])-max(other['start_ns'],r['enq_ns']))
            for other in core['rows'] if other['queue']==r['queue'] and other['ticket']<r['ticket'])
        assert 0<=earlier_commit_ns<=r['busy_wait_ns']
        own_precommit=r['own_exec_ns']-(r['end_ns']-r['start_ns']);assert own_precommit>=0
        item=dict(queue=r['queue'],ticket=r['ticket'],made_us=r['made_us'],jobs_through_commit=r['jobs'],
            frontend_queue_us=t[1]-t[0],turn_event_us=t[2]-t[1],core_admission_us=r['enq_ns']/1000-t[2],
            core_queue_wait_us=(r['start_ns']-r['enq_ns'])/1000,
            core_commit_body_us=(r['end_ns']-r['start_ns'])/1000,
            core_body_end_to_timeline_us=done-r['end_ns']/1000,
            core_body_end_to_callback_us=t[5]-r['end_ns']/1000,
            commit_done_us=done-t[0],own_precommit_body_sum_us=own_precommit/1000,
            own_all_body_sum_us=r['own_exec_ns']/1000,notice_lag_us=r['notification_lag_us'],
            observed_worker_body_in_wait_us=r['busy_wait_ns']/1000,
            observed_earlier_commit_body_in_wait_us=earlier_commit_ns/1000,
            remaining_worker_body_in_wait_us=(r['busy_wait_ns']-earlier_commit_ns)/1000,
            uncovered_queue_wait_us=r['core_uncovered_queue_wait_us'],
            minimum_other_buffer_body_in_wait_us=max(0,r['busy_wait_ns']-own_precommit)/1000)
        components=('frontend_queue_us','turn_event_us','core_admission_us','core_queue_wait_us',
            'core_commit_body_us','core_body_end_to_timeline_us')
        assert abs(sum(item[k] for k in components)-item['commit_done_us'])<.001
        rows.append(item)
    assert len(rows)==comparison['candidate338']['count']==710
    ranked=sorted(rows,key=lambda r:(r['commit_done_us'],r['ticket']));rank=math.ceil(.95*len(ranked))-1;tail=ranked[rank:]
    assert ranked[rank]['commit_done_us']==comparison['candidate338']['stage_us']['commit_to_done_us']['p95']
    fields=[k for k in rows[0] if k.endswith('_us') and k!='made_us']
    total=sum(r['commit_done_us'] for r in tail)
    component_sums={k:sum(r[k] for r in tail) for k in components}
    assert abs(sum(component_sums.values())-total)<.001
    # Add the actual SpringBoard inputs read by the workload comparison to the
    # consolidated provenance, and independently reproduce those summaries.
    spec=importlib.util.spec_from_file_location('raw_workload_recheck338',WORK/'tools/summarize-core338-results.py')
    tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)
    for key,folder,bounds in [('baseline337',PRIOR/'execution',comparison['baseline337']['script_bounds_us']),
        ('candidate338',execution,comparison['candidate338']['script_bounds_us'])]:
        observed=tool.workload_profile((folder/'backboardd.log.current').read_text(),
            (folder/'springboard-new.log').read_text(),bounds)
        assert observed==comparison[key]['workload']
    paths=[Path(__file__),WORK/'tools/summarize-core338-results.py',compared,
        execution/'core-wait-execution-analysis.json',execution/'c4-queue-analysis.json',
        execution/'result.json',execution/'springboard-new.log',PRIOR/'execution/springboard-new.log']
    result=dict(state='0338-qualified-core-critical-path-decomposed',script_count=len(rows),
        metrics={k:stats([r[k] for r in rows]) for k in fields},p95_buffer=ranked[rank],
        tail_count=len(tail),tail_elapsed_sum_us=total,tail_component_sums_us=component_sums,
        tail_component_shares={k:v/total for k,v in component_sums.items()},
        tail_core_wait_sum_us=sum(r['core_queue_wait_us'] for r in tail),
        tail_known_earlier_commit_sum_us=sum(r['observed_earlier_commit_body_in_wait_us'] for r in tail),
        core_body_end_after_timeline_count=sum(r['core_body_end_to_timeline_us']<0 for r in rows),
        own_body_sum_above_16667us=sum(r['own_all_body_sum_us']>16667 for r in rows),
        source_scope='All core jobs share the existing queue worker. Known predecessor commit bodies are exact interval overlaps; remaining body includes encoding/notification work. The foreign-body quantity is a lower bound, not complete per-operation attribution. Body elapsed includes preemption and nested waits; post-body time includes GPU/kernel/completion dispatch and is not GPU-only.',
        additive_components_are_per_buffer=True,percentiles_must_not_be_added=True,
        overlapping_job_queue_sums_not_critical_path=True,rows=rows,
        original_trial_result_unchanged=True,physical_FPS_qualified=False,device_commands=0,
        input_pins={str(p):sha(p) for p in paths})
    raw=(json.dumps(result,indent=2)+'\n').encode();assert len(raw)<=2097152
    out.mkdir()
    with (out/'result.json').open('xb') as f:f.write(raw)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','input_pins','source_scope')},indent=2))


if __name__=='__main__':main()
