#!/usr/bin/env python3
"""Read-only raw0339/0340 comparison after original restoration and all gates.

This adds a bounded host report; it never changes a frozen trial input/result,
uses no device commands, and never treats weighted CB waits as CPU utilization.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
from core340_scope import BASE,WORK,PARENT,load,sha
import core340_log as CORE
import collection340 as COLLECTION

REPORT_MAX=1048576


def module(name,leaf):
    spec=importlib.util.spec_from_file_location(name,WORK/'tools'/leaf)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def selected(core,bounds):
    start,end=bounds
    assert core['coverage_qualified'] and start<end
    return [r for r in core['rows'] if start<=r['made_us']<end]


def timeline(core,bounds):
    rows=selected(core,bounds);assert rows
    lifecycle={(r['object'],r['made_us']):r for r in core['lifecycle']['buffers']}
    identities={(r['object'],r['made_us']):r for r in core['identity']['buffers']}
    paths=[]
    for r in rows:
        b=lifecycle[r['object'],r['made_us']];q=identities[r['object'],r['made_us']]
        t={int(k):v for k,v in b['times_us'].items()};done=b['existing_timeline']['done_us']
        parts=dict(frontend_queue_us=t[1]-t[0],turn_event_us=t[2]-t[1],
            core_admission_us=r['enq_ns']/1000-t[2],core_queue_us=(r['start_ns']-r['enq_ns'])/1000,
            core_commit_us=(r['end_ns']-r['start_ns'])/1000,
            body_end_to_timeline_us=done-r['end_ns']/1000)
        assert abs(sum(parts.values())-(done-t[0]))<.001
        paths.append(dict(object=r['object'],made_us=r['made_us'],queue=r['queue'],ticket=r['ticket'],
            done_us=done-t[0],components=parts,frontend_body_us=q['retire_us']-t[1],
            own_precommit_us=(r['own_exec_ns']-(r['end_ns']-r['start_ns']))/1000,
            own_all_body_us=r['own_exec_ns']/1000,core_call_to_callback_us=t[5]-t[2],
            callback_to_timeline_us=done-t[5],notification_lag_us=r['notification_lag_us']))
    ordered=sorted(paths,key=lambda r:(r['done_us'],r['queue'],r['ticket']))
    rank=math.ceil(.95*len(ordered))-1;tail=ordered[rank:]
    keys=tuple(paths[0]['components'])
    sums={k:sum(r['components'][k] for r in tail) for k in keys};total=sum(r['done_us'] for r in tail)
    assert abs(sum(sums.values())-total)<.001
    done_ordered=sorted(lifecycle[r['object'],r['made_us']]['existing_timeline']['done_us'] for r in rows)
    intervals=[b-a for a,b in zip(done_ordered,done_ordered[1:])]
    return dict(count=len(rows),bounds_us=list(bounds),
        metrics={k:CORE.stats([r['components'][k] for r in paths]) for k in keys},
        other_metrics={k:CORE.stats([r[k] for r in paths]) for k in ('done_us','frontend_body_us','own_precommit_us','own_all_body_us','core_call_to_callback_us','callback_to_timeline_us','notification_lag_us')},
        p95_buffer=ordered[rank],tail_count=len(tail),tail_CB_elapsed_sum_us=total,
        tail_component_sums_us=sums,tail_component_shares={k:v/total if total else None for k,v in sums.items()},
        own_body_sum_above_16667us=sum(r['own_all_body_us']>16667 for r in paths),
        signed_body_end_after_timeline_count=sum(r['components']['body_end_to_timeline_us']<0 for r in paths),
        completion_intervals_us=CORE.stats(intervals),completion_intervals_above_16667us=sum(x>16667 for x in intervals),
        completion_intervals_are_not_panel_frames=True),rows,tail


def attribution(core,rows,tail):
    assert rows
    bykey={(r['object'],r['made_us']):r for r in rows}
    slow=[bykey[r['object'],r['made_us']] for r in tail]
    known_jobs={}
    for r in core['rows']:
        key=(r['queue'],r['max_job']);assert key not in known_jobs
        known_jobs[key]=r
    def aggregate(items):
        wait=sum(r['start_ns']-r['enq_ns'] for r in items)
        categories=[sum(r['wait_ns'][i] for r in items) for i in range(8)]
        busy=sum(r['busy_wait_ns'] for r in items);assert sum(categories)==busy<=wait
        body=[sum(r['exec_ns'][i] for r in items) for i in range(8)]
        stages=[sum(r['submit_ns'][i] for r in items) for i in range(8)]
        commit=sum(r['end_ns']-r['start_ns'] for r in items)
        assert sum(body)==sum(r['own_exec_ns'] for r in items)
        assert body[6]==commit and sum(stages)<=commit
        known=[0]*8
        for r in items:
            covered=[0]*8
            for (queue,job),other in known_jobs.items():
                if queue!=r['queue'] or job>=r['job']:continue
                n=max(0,min(r['start_ns'],other['max_end_ns'])-max(r['enq_ns'],other['max_start_ns']))
                covered[other['max_class']]+=n
            assert all(a<=b for a,b in zip(covered,r['wait_ns'])), 'known worst-job overlap exceeds measured category coverage'
            known=[a+b for a,b in zip(known,covered)]
        return dict(CB_count=len(items),queue_wait_sum_us=wait/1000,
            observed_body_sum_us=busy/1000,uncovered_sum_us=(wait-busy)/1000,
            wait_category_sums_us={k:categories[i]/1000 for i,k in enumerate(CORE.CATEGORIES)},
            wait_category_shares_of_queue_sum={k:categories[i]/wait if wait else None for i,k in enumerate(CORE.CATEGORIES)},
            own_body_category_sums_us={k:body[i]/1000 for i,k in enumerate(CORE.CATEGORIES)},
            own_body_category_counts={k:sum(r['counts'][i] for r in items) for i,k in enumerate(CORE.CATEGORIES)},
            submit_phase_sums_us={k:stages[i]/1000 for i,k in enumerate(CORE.STAGES)},
            commit_outside_submit_sum_us=(commit-sum(stages))/1000,
            known_worst_job_covered_wait_us={k:known[i]/1000 for i,k in enumerate(CORE.CATEGORIES)},
            known_job_evidence_is_partial=True,weighted_overlapping_CB_times_not_utilization=True)
    keys=tuple(core['metrics'])
    return dict(full_script=aggregate(rows),completion_tail=aggregate(slow),
        script_metrics={k:CORE.stats([CORE.value(r,k) for r in rows]) for k in keys},
        longest_core_wait_rows=sorted(rows,key=lambda r:r['core_queue_wait_us'],reverse=True)[:10])


def fine_aggregate(rows):
    draw=[sum(r['draw_ns'][i] for r in rows) for i in range(8)]
    render=[sum(r['render_ns'][i] for r in rows) for i in range(8)]
    gpu=[sum(r['gpu_ns'][i] for r in rows) for i in range(5)]
    body=sum(r['exec_ns'][2] for r in rows);native=sum(r['submit_ns'][6] for r in rows)
    io=sum(r['io_ns'] for r in rows)
    assert sum(draw)<=body and sum(render)<=draw[5] and io<=gpu[3] and sum(gpu)<=native
    return dict(CB_count=len(rows),draw_calls=sum(r['draw_calls'] for r in rows),
        draw_common_sums_us={k:draw[i]/1000 for i,k in enumerate(CORE.DRAW)},
        render_body_sums_us={k:render[i]/1000 for i,k in enumerate(CORE.RENDER)},
        GPU_submit_sums_us={k:gpu[i]/1000 for i,k in enumerate(CORE.GPU)},
        draw_common_total_us=sum(draw)/1000,render_body_total_us=sum(render)/1000,
        render_job_outside_common_us=(body-sum(draw))/1000,
        GPU_submit_total_us=sum(gpu)/1000,actual_IO_elapsed_sum_us=io/1000,
        transport_outside_IO_us=(gpu[3]-io)/1000,
        native_submit_outside_GPU_probe_us=(native-sum(gpu))/1000,
        BO_list_share_of_GPU_submit=gpu[1]/sum(gpu) if sum(gpu) else None,
        IO_share_of_GPU_submit=io/sum(gpu) if sum(gpu) else None,
        BO_uses=sum(r['bo_uses'] for r in rows),BO_unique=sum(r['bo_unique'] for r in rows),
        BO_comparisons=sum(r['bo_comparisons'] for r in rows),
        draw_vector_growths=sum(r['draw_reuse'][2] for r in rows),
        submit_vector_growths=sum(r['submit_reuse'][2] for r in rows),
        draw_oversize_drops=sum(r['draw_reuse'][3] for r in rows),
        submit_oversize_drops=sum(r['submit_reuse'][3] for r in rows),
        reserve_failures=sum(r['reserve_failures'] for r in rows),
        submit_modes={str(k):sum(r['bo_mode']==k for r in rows) for k in (0,1,2)},
        warm_indexed_submits=sum(r['bo_mode']==1 and r['submit_reuse'][2]==0 for r in rows),
        maximum_single_draw_us=CORE.stats([r['draw_max_ns']/1000 for r in rows]),
        nested_scopes_not_additive=True,growth_counts_are_vectors_not_malloc_calls=True)


def known_wait_evidence(core,rows):
    """Intersect exact recorded phases; never scale a duration to imply overlap."""
    def overlap(a,b,c,d):return max(0,min(b,d)-max(a,c))
    def phases(begin,durations,labels):
        out=[]
        for n,label in zip(durations,labels):out.append((label,begin,begin+n));begin+=n
        return out
    draws={};commits={}
    for r in core['rows']:
        key=(r['queue'],r['job']);assert key not in commits;commits[key]=r
        if r['draw_calls']:
            key=(r['queue'],r['draw_max_job']);assert key not in draws;draws[key]=r
    sums={k:0 for k in CORE.DRAW};BO=IO=other_GPU=0;episodes=[]
    top={(r['queue'],r['ticket']) for r in sorted(rows,key=lambda x:x['core_queue_wait_us'],reverse=True)[:10]}
    for r in rows:
        a,b=r['enq_ns'],r['start_ns'];parts={k:0 for k in CORE.DRAW};bo=io=other=0;dr=[];co=[]
        for (q,job),known in draws.items():
            if q!=r['queue'] or job>=r['job']:continue
            p={k:overlap(a,b,c,d) for k,c,d in phases(known['draw_max_start_ns'],known['draw_max_phases'],CORE.DRAW)}
            n=sum(p.values())
            if not n:continue
            assert n==overlap(a,b,known['draw_max_start_ns'],known['draw_max_end_ns'])
            for k in parts:parts[k]+=p[k]
            if (r['queue'],r['ticket']) in top:
                dr.append(dict(ticket=known['ticket'],job=job,overlap_us=n/1000,
                    common_phase_overlap_us={k:v/1000 for k,v in p.items()}))
        for (q,job),known in commits.items():
            if q!=r['queue'] or job>=r['job']:continue
            p={k:overlap(a,b,c,d) for k,c,d in phases(known['gpu_begin_ns'],known['gpu_ns'],CORE.GPU)}
            n=sum(p.values())
            if not n:continue
            x=overlap(a,b,known['io_begin_ns'],known['io_end_ns']);y=p['BO_list']
            assert x<=p['transport'] and x+y<=n
            bo+=y;io+=x;other+=n-x-y
            if (r['queue'],r['ticket']) in top:
                co.append(dict(ticket=known['ticket'],job=job,GPU_overlap_us=n/1000,
                    BO_list_overlap_us=y/1000,IO_overlap_us=x/1000,
                    other_GPU_submit_overlap_us=(n-x-y)/1000))
        assert sum(parts.values())<=r['wait_ns'][2], 'known draw overlap exceeds render category'
        assert bo+io+other<=r['wait_ns'][6], 'known GPU submit overlap exceeds commit category'
        for k in sums:sums[k]+=parts[k]
        BO+=bo;IO+=io;other_GPU+=other
        if (r['queue'],r['ticket']) in top:
            episodes.append(dict(queue=r['queue'],ticket=r['ticket'],wait_us=(b-a)/1000,
                draw_common_overlap_us=sum(parts.values())/1000,
                draw_phase_overlap_us={k:v/1000 for k,v in parts.items()},
                BO_list_overlap_us=bo/1000,IO_overlap_us=io/1000,other_GPU_submit_overlap_us=other/1000,
                known_draws=sorted(dr,key=lambda x:x['overlap_us'],reverse=True)[:8],
                known_commits=sorted(co,key=lambda x:x['GPU_overlap_us'],reverse=True)[:8]))
    return dict(draw_common_phase_covered_wait_us={k:v/1000 for k,v in sums.items()},
        BO_list_covered_wait_us=BO/1000,IO_covered_wait_us=IO/1000,
        other_GPU_submit_covered_wait_us=other_GPU/1000,
        longest_waits=sorted(episodes,key=lambda x:x['wait_us'],reverse=True),
        evidence_is_partial=True,weighted_overlapping_CB_times_not_utilization=True,
        inner_render_phases_are_per_CB_sums_not_per_worst_draw=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    execution=BASE/'execution';result=load(execution/'result.json');ready=load(BASE/'ready.json')
    assert result['state']=='CR340-lossless-wait-execution-observed-root-restored',result['state']
    assert not result.get('fixture_only') and result['restored'] and result['independent_restore_verified'] and result['boot_attempts']==1
    assert result['legacy_observation_state']=='BC336-cache-reuse-observed-root-restored' and result['collection_analysis']['coverage_qualified']
    assert result['attempted_userdata_bytes']<=30961664 and result['attempted_misc_bytes']<=26 and not result['physical_FPS_qualified']
    proof=load(execution/'independent-restore.json')
    assert proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and proof['all_original_slot_bits_allocated']
    claim=load(execution/'claim.json');assert claim['approval_sha256']==sha(BASE/'approval.json') and claim['trial_plan_sha256']==ready['trial_plan_sha256']
    for path,digest in ready['input_pins'].items():assert sha(path)==digest,path
    before=load(execution/'fresh-before/result.json');after=load(execution/'post-capture/result.json')
    prefixes={};paths=[]
    legacy=module('report340_static_contract','run-sb-cadence-trial.py')
    legacy.static_compare(before,load(execution/'restored-capture/result.json'))
    for path in legacy.LOG_PATHS:
        old=execution/'fresh-before'/before['files'][path]['output'];new=execution/'post-capture'/after['files'][path]['output']
        rawold,rawnew=old.read_bytes(),new.read_bytes();assert rawnew.startswith(rawold),path
        delta=execution/(before['files'][path]['output']+'.current');assert delta.read_bytes()==rawnew[len(rawold):],path
        prefixes[path]=dict(before_sha256=sha(old),after_sha256=sha(new),tail_sha256=sha(delta));paths.extend((old,new,delta))
    kernel=(execution/'kernel.log').read_text(errors='replace');sb=(execution/'springboard-new.log').read_text(errors='replace')
    backboard=(execution/(before['files']['/private/var/log/backboardd.log']['output']+'.current')).read_text(errors='replace')
    core=CORE.analyze(backboard);assert core['coverage_qualified'],core['errors']
    frozen=load(execution/'core-wait-execution-analysis.json')
    assert frozen['rows']==core['rows'] and frozen['metrics']==core['metrics']
    allocation=load(execution/'bo-allocation-analysis.json')
    collected=COLLECTION.analyze(kernel,backboard,sb,True,allocation,core['lifecycle'],core['identity'],core)
    assert collected==load(execution/'collection-analysis.json') and collected['coverage_qualified']
    new_summary,rows,tail=timeline(core,collected['script_window_us']);split=attribution(core,rows,tail)
    bykey={(r['object'],r['made_us']):r for r in rows};slow=[bykey[r['object'],r['made_us']] for r in tail]
    fine=dict(full_script=fine_aggregate(rows),completion_tail=fine_aggregate(slow),
        full_script_wait=known_wait_evidence(core,rows),completion_tail_wait=known_wait_evidence(core,slow))
    backlog=load(execution/'queue-backlog-analysis.json')
    assert backlog['full_script_window']['metrics']==split['script_metrics']
    rate=module('report340_windows','analyze-sb-rate-log.py');bounds=rate.window_from_kernel(kernel)
    assert backlog['BO_capture_window']['bounds_us']==list(bounds)
    assert backlog['BO_capture_window']['count']==len(selected(core,bounds))
    old=CORE.OLD.analyze((PARENT/'execution/backboardd.log.current').read_text())
    assert old['coverage_qualified'] and load(PARENT/'execution/result.json')['state']=='CR339-lossless-wait-execution-observed-root-restored'
    old_summary,_,_=timeline(old,load(PARENT/'execution/collection-analysis.json')['script_window_us'])
    assert old_summary['count']==717 and old_summary['other_metrics']['done_us']['p95']==41080
    workload=module('report340_workload','summarize-core338-results.py').workload_profile
    old_summary['workload']=workload((PARENT/'execution/backboardd.log.current').read_text(),(PARENT/'execution/springboard-new.log').read_text(),old_summary['bounds_us'])
    new_summary['workload']=workload(backboard,sb,new_summary['bounds_us'])
    comparison={k:dict(baseline339_p95_us=old_summary['metrics'][k]['p95'],candidate340_p95_us=new_summary['metrics'][k]['p95'],
        change_us=new_summary['metrics'][k]['p95']-old_summary['metrics'][k]['p95']) for k in new_summary['metrics']}
    comparison['commit_done_us']=dict(baseline339_p95_us=old_summary['other_metrics']['done_us']['p95'],
        candidate340_p95_us=new_summary['other_metrics']['done_us']['p95'],change_us=new_summary['other_metrics']['done_us']['p95']-old_summary['other_metrics']['done_us']['p95'])
    paths.extend([Path(__file__),WORK/'tests/test_core340_report.py',WORK/'tools/core340_log.py',WORK/'tools/collection340.py',WORK/'tools/summarize-core338-results.py',BASE/'ready.json',BASE/'approval.json',BASE/'trial-plan.json',BASE/'final-review.json',
        execution/'claim.json',execution/'result.json',execution/'restore-result.json',execution/'independent-restore.json',execution/'fresh-before/result.json',execution/'post-capture/result.json',execution/'restored-capture/result.json',
        execution/'kernel.log',execution/'springboard-new.log',execution/'collection-analysis.json',execution/'core-wait-execution-analysis.json',execution/'queue-backlog-analysis.json',execution/'bo-allocation-analysis.json',
        PARENT/'execution/result.json',PARENT/'execution/collection-analysis.json',PARENT/'execution/backboardd.log.current',PARENT/'execution/springboard-new.log'])
    report=dict(state='0340-qualified-raw-comparison-fine-draw-BO-and-IO-attribution',baseline339=old_summary,candidate340=new_summary,
        p95_comparison=comparison,category_and_submit_attribution=split,fine_draw_BO_IO_attribution=fine,
        worker_reuse=core['worker_reuse'],BO_capture_window=backlog['BO_capture_window'],
        original_trial_result_unchanged=True,all_frozen_inputs_unchanged=True,pin_count=ready['pin_count'],
        prefix_checks=prefixes,independent_restoration_verified=True,device_commands=0,physical_FPS_qualified=False,
        scope='Qualified full13-stroke windows. Instrumentation, scheduling, shader keys and cache state may differ; paired p95 differences do not isolate causality. All body measurements include CPU preemption/waits, and uncovered gaps include bookkeeping/logging/scheduling. Known worst jobs are partial interval evidence. No GPU-only or physical panel FPS conclusion.',
        input_pins={str(p.resolve()):sha(p) for p in paths})
    raw=(json.dumps(report,indent=2)+'\n').encode();assert len(raw)<=REPORT_MAX
    out.mkdir()
    with (out/'comparison-summary.json').open('xb') as f:f.write(raw)
    print(json.dumps(dict(state=report['state'],candidate_count=new_summary['count'],p95_comparison=comparison,
        wait_categories_us=split['full_script']['wait_category_sums_us'],submit_phases_us=split['full_script']['submit_phase_sums_us'],
        tail_wait_categories_us=split['completion_tail']['wait_category_sums_us'],tail_submit_phases_us=split['completion_tail']['submit_phase_sums_us'],
        fine_full_script=fine['full_script'],fine_completion_tail=fine['completion_tail']),indent=2))


if __name__=='__main__':main()
