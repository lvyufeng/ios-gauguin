#!/usr/bin/env python3
"""Host-only raw0337/0338 comparison after qualified independent restoration.

Never rewrites frozen trial results. No device entry point, register dump or
physical-FPS inference. Queue latencies and overlapping branches stay separate.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from core338_scope import MAIN,WORK,BASE,PRIOR,load,sha
import core338_log as CORE


def module(name,leaf):
    spec=importlib.util.spec_from_file_location(name,WORK/'tools'/leaf)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def stages(c4,identity,bounds,wire):
    assert c4['coverage_qualified'] and identity['coverage_qualified']
    start,end=bounds;ids={(r['object'],r['made_us']):r for r in identity['buffers']};rows=[]
    for b in c4['buffers']:
        if not start<=b['made_us']<end:continue
        t={int(k):v for k,v in b['times_us'].items()};q=ids[b['object'],b['made_us']]
        done=b['existing_timeline']['done_us']
        r=dict(queue=q['queue'],ticket=q['ticket'],made_us=b['made_us'],
            frontend_queue_us=t[1]-t[0],turn_event_us=t[2]-t[1],commit_post_us=t[3]-t[2],
            phase4_us=t[4]-t[3],core_call_to_callback_us=t[5]-t[2],callback_to_timeline_us=done-t[5],
            commit_to_done_us=done-t[0],frontend_body_us=q['retire_us']-t[1],
            earlier_unretired_at_admission=q['earlier_unretired_at_admission'])
        assert sum(r[k] for k in ('frontend_queue_us','turn_event_us','core_call_to_callback_us','callback_to_timeline_us'))==r['commit_to_done_us']
        rows.append(r)
    assert rows
    fields=tuple(k for k in rows[0] if k.endswith('_us') and k!='made_us')+('earlier_unretired_at_admission',)
    ordered=sorted(rows,key=lambda r:(r['commit_to_done_us'],r['ticket']))
    rank=math.ceil(len(ordered)*.95)-1;tail=ordered[rank:]
    return dict(script_bounds_us=list(bounds),count=len(rows),
        stage_us={k:CORE.stats([r[k] for r in rows]) for k in fields},
        phase4_semantics=('synchronous status-drain return' if wire==337 else 'notification-admission return; reserved zero'),
        commit_done_above_16667us=sum(r['commit_to_done_us']>16667 for r in rows),
        p95_completion_buffer=ordered[rank],tail_count=len(tail),
        tail_metrics={k:CORE.stats([r[k] for r in tail]) for k in fields},
        physical_FPS_qualified=False),rows


def workload_profile(backboard,springboard,bounds):
    rate=module('comparison_input_window338','analyze-sb-rate-log.py')
    shader=module('comparison_shader_workload338','analyze-stage-cache-log.py')
    timing=rate.summarize(rate.parse(springboard),*bounds)
    cache=shader.analyze(backboard,True);assert cache['coverage_qualified']
    keys=sorted({r['key'] for r in cache['rows'] if r['outcome']==3 and
        r['times_us']['start']<bounds[1] and r['times_us']['end']>bounds[0]})
    return dict(input_entries=timing['input']['entries_in_window'],
        callback_us=CORE.stats([r['duration_us'] for r in timing['input']['callback_spans']]),
        compiled_shader_keys_in_script=keys,compiled_shader_key_count=len(keys),
        full_tail_shader_compilations=cache['compilations'],full_tail_shader_fast_hits=cache['fast_hits'])


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    execution=BASE/'execution';result=load(execution/'result.json');ready=load(BASE/'ready.json')
    assert result['state']=='CR338-lossless-wait-execution-observed-root-restored',result['state']
    assert result['restored'] and result['independent_restore_verified'] and result['boot_attempts']==1
    assert result['legacy_observation_state']=='BC336-cache-reuse-observed-root-restored'
    assert result['collection_analysis']['coverage_qualified'] and not result['physical_FPS_qualified']
    assert result['attempted_userdata_bytes']<=30961664 and result['attempted_misc_bytes']<=26
    independent=load(execution/'independent-restore.json')
    assert independent['state']=='independently-verified-six-original-files-misc-and-empty-journal'
    assert independent['journal_empty'] and independent['all_original_slot_bits_allocated'] and independent['misc_original_4096_bytes_match']
    claim=load(execution/'claim.json');assert claim['approval_sha256']==sha(BASE/'approval.json')
    assert claim['trial_plan_sha256']==ready['trial_plan_sha256']
    for p,h in ready['input_pins'].items():assert sha(p)==h,p
    earlier=PRIOR/'recovered-analysis';prior=load(earlier/'result.json')
    assert prior['state']=='Q337-lossless-queue-CPU-observed-root-restored'
    assert prior['collection_analysis']['coverage_qualified']
    rate=module('raw_comparison_window338','analyze-sb-rate-log.py')
    raw_c4=module('raw_c4_baseline337','analyze-c4-queue-log.py')
    raw_id=module('raw_identity_baseline337','analyze-queue337.py')
    k337=(PRIOR/'execution/kernel.log').read_text(errors='replace')
    b337=(PRIOR/'execution/backboardd.log.current').read_text(errors='replace')
    k338=(execution/'kernel.log').read_text(errors='replace')
    before=load(execution/'fresh-before/result.json');after=load(execution/'post-capture/result.json')
    b338_path=execution/(before['files']['/private/var/log/backboardd.log']['output']+'.current')
    b338=b338_path.read_text(errors='replace')
    prefixes={}
    for path in module('raw_prefix_contract338','run-sb-cadence-trial.py').LOG_PATHS:
        old=execution/'fresh-before'/before['files'][path]['output']
        new=execution/'post-capture'/after['files'][path]['output']
        oldbytes,newbytes=old.read_bytes(),new.read_bytes();assert newbytes.startswith(oldbytes),path
        tail=execution/(before['files'][path]['output']+'.current')
        assert tail.read_bytes()==newbytes[len(oldbytes):],path
        prefixes[path]=dict(before_sha256=sha(old),after_sha256=sha(new),tail_sha256=sha(tail))
    old_c4,old_id=raw_c4.analyze(b337),raw_id.analyze(b337)
    new_core=CORE.analyze(b338);assert new_core['coverage_qualified'],new_core['errors']
    old_collection=load(earlier/'collection-analysis.json')
    new_collection=load(execution/'collection-analysis.json')
    old_summary,old_rows=stages(old_c4,old_id,old_collection['script_window_us'],337)
    new_summary,new_rows=stages(new_core['lifecycle'],new_core['identity'],new_collection['script_window_us'],338)
    old_summary['workload']=workload_profile(b337,(PRIOR/'execution/springboard-new.log').read_text(),old_collection['script_window_us'])
    new_summary['workload']=workload_profile(b338,(execution/'springboard-new.log').read_text(),new_collection['script_window_us'])
    assert old_summary['count']==738 and old_summary['stage_us']['commit_to_done_us']['p95']==223499
    assert old_summary['stage_us']['frontend_queue_us']['p95']==168003
    assert old_summary['workload']['compiled_shader_key_count']==7 and old_summary['workload']['callback_us']['count']==576
    frozen=load(execution/'queue-backlog-analysis.json')
    frozen_core=load(execution/'core-wait-execution-analysis.json')
    assert frozen_core['metrics']==new_core['metrics']
    start,end=new_summary['script_bounds_us']
    script_core=[r for r in new_core['rows'] if start<=r['made_us']<end]
    assert len(script_core)==len(new_rows)
    core_metrics={k:CORE.stats([r[k] for r in script_core]) for k in new_core['metrics']}
    # The frozen runner inherited window_from_kernel(): a4s BO capture
    # window. Its field named scripted_window must not be represented as the
    # full13-stroke workload. Reproduce it separately and preserve its result.
    narrow_start,narrow_end=rate.window_from_kernel(k338)
    narrow=[r for r in new_core['rows'] if narrow_start<=r['made_us']<=narrow_end]
    assert (narrow_start,narrow_end)==(frozen['scripted_window']['start_us'],frozen['scripted_window']['end_us'])
    assert len(narrow)==frozen['scripted_window']['count']
    assert {k:CORE.stats([r[k] for r in narrow]) for k in new_core['metrics']}==frozen['scripted_window']['metrics']
    assert core_metrics['commit_done_us']==new_summary['stage_us']['commit_to_done_us']
    assert core_metrics['frontend_queue_us']==new_summary['stage_us']['frontend_queue_us']
    wait=sum(r['core_queue_wait_us'] for r in script_core)
    busy=sum(r['core_observed_busy_in_wait_us'] for r in script_core)
    uncovered=sum(r['core_uncovered_queue_wait_us'] for r in script_core)
    assert abs(wait-busy-uncovered)<.001 and 0<=busy<=wait
    comparison={k:dict(baseline337_p95_us=old_summary['stage_us'][k]['p95'],
        candidate338_p95_us=new_summary['stage_us'][k]['p95'],
        change_us=new_summary['stage_us'][k]['p95']-old_summary['stage_us'][k]['p95'])
        for k in ('commit_to_done_us','frontend_queue_us','frontend_body_us','turn_event_us','core_call_to_callback_us')}
    paths=[Path(__file__),BASE/'ready.json',BASE/'trial-plan.json',BASE/'approval.json',BASE/'final-review.json',
        execution/'claim.json',execution/'result.json',execution/'restore-result.json',execution/'independent-restore.json',
        execution/'collection-analysis.json',execution/'queue-backlog-analysis.json',execution/'core-wait-execution-analysis.json',
        execution/'kernel.log',b338_path,PRIOR/'execution/kernel.log',PRIOR/'execution/backboardd.log.current',earlier/'result.json']
    output=dict(state='0338-qualified-raw-comparison-and-core-queue-split',trial_result_unchanged=True,
        all_frozen_inputs_unchanged=True,pin_count=ready['pin_count'],boot_attempts=result['boot_attempts'],
        independently_restored=True,baseline337=old_summary,candidate338=new_summary,
        p95_comparison=comparison,script_core_metrics=core_metrics,
        frozen_narrow_window=dict(bounds_us=[narrow_start,narrow_end],count=len(narrow),
            reproduced_exactly=True,actual_scope='4s kernel BO capture, not the complete13-stroke script',
            original_scripted_window_label_correct=False),
        core_wait_aggregate_us=dict(queue_wait=wait,observed_prior_body_execution=busy,uncovered=uncovered,
            observed_busy_share=busy/wait if wait else None),
        native_core_fields_not_GPU_only=True,phase4_values_are_not_comparable_states=True,
        scope='Two qualified13-stroke runs. Different workloads/cache warm state remain possible; p95 changes alone do not prove causality. Queue/CPU/completion timings are not physical panel FPS.',
        physical_FPS_qualified=False,device_commands=0,prefix_checks=prefixes,
        input_pins={str(p):sha(p) for p in paths})
    raw=(json.dumps(output,indent=2)+'\n').encode();assert len(raw)<=1048576
    out.mkdir()
    with (out/'comparison-summary.json').open('xb') as f:f.write(raw)
    print(json.dumps({k:output[k] for k in ('state','p95_comparison','script_core_metrics','core_wait_aggregate_us')},indent=2))


if __name__=='__main__':main()
