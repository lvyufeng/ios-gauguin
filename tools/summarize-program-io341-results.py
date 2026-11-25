#!/usr/bin/env python3
"""Read-only qualified0341 phase/CPU bounds and exact predecessor intervals."""
import argparse
import importlib.util
import json
from pathlib import Path

from core341_scope import BASE,WORK,PARENT,load,sha
import core341_log as CORE
import core340_log as OLD
import collection341 as COLLECTION


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


LEGACY=module('post341_legacy_arithmetic',WORK/'tools/summarize-core340-results.py')


def partial_bounds(duration,lower,upper,overlap):
    """Conservative CPU/offCPU placement within a subinterval, never prorated."""
    assert 0<=lower<=upper<=duration and 0<=overlap<=duration
    cpu=(max(0,lower-(duration-overlap)),min(overlap,upper))
    off=(overlap-cpu[1],overlap-cpu[0])
    return cpu,off


def phase_overlaps(begin,durations,start,end):
    assert start<=end and all(n>=0 for n in durations)
    result=[]
    for n in durations:
        result.append(max(0,min(end,begin+n)-max(start,begin)));begin+=n
    return result


def detail(rows,hotspots=True):
    assert rows
    io=sum(r['io_ns'] for r in rows)
    cpu=[sum(r['cpu_ns'][i] for r in rows) for i in range(9)]
    assert all(r['cpu_counts']==[1,1,2] for r in rows)
    assert cpu[5]+cpu[8]==io==cpu[6]+cpu[7] and cpu[5]<=cpu[6]
    groups={}
    for key,labels in CORE.PARTS.items():
        values=[sum(r[key+'_ns'][i] for r in rows) for i in range(len(labels))]
        groups[key]=dict(calls=sum(r[key+'_counts'][0] for r in rows),
            completed=sum(r[key+'_counts'][1] for r in rows),
            hit_or_skipped=sum(r[key+'_counts'][2] for r in rows),
            wall_sum_us=sum(values)/1000,phases_us={k:n/1000 for k,n in zip(labels,values)})
        if hotspots:
            candidates=sorted((r for r in rows if r[key+'_counts'][0]),
                key=lambda r:r[key+'_max'][2]-r[key+'_max'][1],reverse=True)[:5]
            groups[key]['longest_calls']=[dict(queue=r['queue'],ticket=r['ticket'],
                job=r[key+'_max'][0],begin_ns=r[key+'_max'][1],end_ns=r[key+'_max'][2],
                phases_us={k:n/1000 for k,n in zip(labels,r[key+'_max'][3:])}) for r in candidates]
    return dict(CB_count=len(rows),program_scopes=groups,
        counters={k:sum(r['program_counts'][i] for r in rows) for i,k in enumerate(CORE.COUNTS)},
        IO=dict(wall_sum_us=io/1000,CPU_sum_bounds_us=[cpu[5]/1000,cpu[6]/1000],
            off_CPU_sum_bounds_us=[cpu[7]/1000,cpu[8]/1000],sampling_envelope_sum_us=cpu[4]/1000,
            CPU_share_bounds=[cpu[5]/io,cpu[6]/io] if io else None,
            off_CPU_share_bounds=[cpu[7]/io,cpu[8]/io] if io else None,
            per_CB={k:CORE.stats([CORE.value(r,k) for r in rows]) for k in
                ('io_connect_us','IO_CPU_lower_us','IO_CPU_upper_us','IO_off_CPU_lower_us',
                 'IO_off_CPU_upper_us','IO_sampling_envelope_us')},
            intervals_more_than_half_definitely_off_CPU=sum(r['cpu_ns'][7]*2>r['io_ns'] for r in rows),
            intervals_more_than_half_definitely_on_CPU=sum(r['cpu_ns'][5]*2>r['io_ns'] for r in rows)),
        nested_scopes_not_additive=True,off_CPU_not_classified_lock_wait=True)


def weighted_wait(core,rows):
    known={k:{} for k in CORE.PARTS}
    for row in core['rows']:
        for key in CORE.PARTS:
            if row[key+'_counts'][0]:
                x=row[key+'_max'];identity=(row['queue'],x[0],x[1],x[2])
                if identity in known[key]:assert known[key][identity][3:]==x[3:]
                known[key][identity]=x
    totals={k:[0]*len(v) for k,v in CORE.PARTS.items()}
    io_total=0;cpu_total=[0,0];off_total=[0,0];episodes=[]
    longest={(r['queue'],r['ticket']) for r in sorted(rows,key=lambda r:r['core_queue_wait_us'],reverse=True)[:8]}
    for row in rows:
        a,b=row['enq_ns'],row['start_ns'];parts={k:[0]*len(v) for k,v in CORE.PARTS.items()}
        for key,items in known.items():
            for (queue,job,begin,end),x in items.items():
                if queue!=row['queue'] or job>=row['job']:continue
                values=phase_overlaps(begin,x[3:],a,b)
                assert sum(x[3:])==end-begin
                parts[key]=[p+n for p,n in zip(parts[key],values)]
            assert sum(parts[key])<=row['wait_ns'][2]
            totals[key]=[p+n for p,n in zip(totals[key],parts[key])]
        used=[];io=0;cpu=[0,0];off=[0,0]
        for prior in core['rows']:
            if prior['queue']!=row['queue'] or prior['job']>=row['job']:continue
            overlap=max(0,min(b,prior['io_end_ns'])-max(a,prior['io_begin_ns']))
            if not overlap:continue
            c,o=partial_bounds(prior['io_ns'],prior['cpu_ns'][5],prior['cpu_ns'][6],overlap)
            io+=overlap;cpu=[p+n for p,n in zip(cpu,c)];off=[p+n for p,n in zip(off,o)]
            used.append(dict(ticket=prior['ticket'],job=prior['job'],IO_overlap_us=overlap/1000,
                CPU_bounds_us=[n/1000 for n in c],off_CPU_bounds_us=[n/1000 for n in o]))
        assert io<=row['wait_ns'][6] and cpu[0]+off[1]==io==cpu[1]+off[0]
        io_total+=io;cpu_total=[p+n for p,n in zip(cpu_total,cpu)];off_total=[p+n for p,n in zip(off_total,off)]
        if (row['queue'],row['ticket']) in longest:
            episodes.append(dict(queue=row['queue'],ticket=row['ticket'],wait_us=(b-a)/1000,
                known_longest_call_phase_overlap_us={k:{label:n/1000 for label,n in zip(CORE.PARTS[k],v)} for k,v in parts.items()},
                known_IO_overlap_us=io/1000,CPU_bounds_us=[n/1000 for n in cpu],
                off_CPU_bounds_us=[n/1000 for n in off],
                known_IO=sorted(used,key=lambda r:r['IO_overlap_us'],reverse=True)[:8]))
    return dict(CB_count=len(rows),known_IO_overlap_sum_us=io_total/1000,
        known_IO_CPU_sum_bounds_us=[n/1000 for n in cpu_total],
        known_IO_off_CPU_sum_bounds_us=[n/1000 for n in off_total],
        known_longest_call_phase_overlap_sums_us={k:{label:n/1000 for label,n in zip(CORE.PARTS[k],v)} for k,v in totals.items()},
        longest_waits=episodes,program_evidence_is_partial=True,
        no_proportional_CPU_placement=True,nested_scopes_not_additive=True,
        weighted_overlapping_CB_waits_not_utilization=True)


def bursts(rows,length=12,limit=5):
    candidates=[]
    for queue in sorted({r['queue'] for r in rows}):
        ordered=sorted((r for r in rows if r['queue']==queue),key=lambda r:r['ticket'])
        for i in range(len(ordered)-length+1):
            group=ordered[i:i+length];first,last=group[0],group[-1]
            if any(b['ticket']!=a['ticket']+1 for a,b in zip(group,group[1:])):continue
            growth=last['core_queue_wait_us']-first['core_queue_wait_us']
            if growth<=0:continue
            candidates.append((growth,queue,first['ticket'],last['ticket'],group))
    output=[];taken=[]
    for growth,queue,begin,end,group in sorted(candidates,key=lambda x:x[:4],reverse=True):
        if any(q==queue and not (end<a or begin>b) for q,a,b in taken):continue
        first,last=group[0],group[-1];taken.append((queue,begin,end))
        output.append(dict(queue=queue,first_ticket=begin,last_ticket=end,CB_count=len(group),
            queue_wait_growth_us=growth,first_wait_us=first['core_queue_wait_us'],last_wait_us=last['core_queue_wait_us'],
            average_commit_arrival_interval_us=(last['enq_ns']-first['enq_ns'])/1000/(length-1),
            average_commit_start_interval_us=(last['start_ns']-first['start_ns'])/1000/(length-1),
            average_own_render_us=sum(r['exec_ns'][2] for r in group)/1000/length,
            average_own_commit_us=sum(r['end_ns']-r['start_ns'] for r in group)/1000/length,
            detail=detail(group,False)))
        if len(output)==limit:break
    return output


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    e=BASE/'execution';result=load(e/'result.json');ready=load(BASE/'ready.json')
    assert result['state']=='CR341-lossless-wait-execution-observed-root-restored'
    assert result['restored'] and result['independent_restore_verified'] and result['boot_attempts']==1
    assert result['legacy_observation_state']=='BC336-cache-reuse-observed-root-restored'
    assert result['attempted_userdata_bytes']<=30961664 and result['attempted_misc_bytes']<=26
    assert not result['physical_FPS_qualified'] and not result.get('fixture_only')
    proof=load(e/'independent-restore.json')
    assert proof['journal_empty'] and proof['misc_original_4096_bytes_match'] and proof['all_original_slot_bits_allocated']
    claim=load(e/'claim.json');assert claim['approval_sha256']==sha(BASE/'approval.json') and claim['trial_plan_sha256']==ready['trial_plan_sha256']
    for p,h in ready['input_pins'].items():assert sha(p)==h,p
    before=load(e/'fresh-before/result.json');after=load(e/'post-capture/result.json')
    contract=module('post341_static_contract',WORK/'tools/run-sb-cadence-trial.py')
    contract.static_compare(before,load(e/'restored-capture/result.json'))
    paths=[]
    for path in contract.LOG_PATHS:
        old=e/'fresh-before'/before['files'][path]['output'];new=e/'post-capture'/after['files'][path]['output']
        tail=e/(before['files'][path]['output']+'.current')
        rawold,rawnew=old.read_bytes(),new.read_bytes();assert rawnew.startswith(rawold) and tail.read_bytes()==rawnew[len(rawold):]
        paths.extend((old,new,tail))
    backboard=(e/'backboardd.log.current').read_text();kernel=(e/'kernel.log').read_text();sb=(e/'springboard-new.log').read_text()
    core=CORE.analyze(backboard);assert core['coverage_qualified'] and core['CPU_accounting']['observed'] and core['program_detail']['observed']
    frozen=load(e/'core-wait-execution-analysis.json');assert frozen['rows']==core['rows'] and frozen['metrics']==core['metrics']
    allocation=load(e/'bo-allocation-analysis.json')
    collected=COLLECTION.analyze(kernel,backboard,sb,True,allocation,core['lifecycle'],core['identity'],core)
    assert collected==load(e/'collection-analysis.json') and collected['coverage_qualified']
    summary,rows,tail=LEGACY.timeline(core,collected['script_window_us'])
    bykey={(r['object'],r['made_us']):r for r in rows};slow=[bykey[r['object'],r['made_us']] for r in tail]
    old=OLD.analyze((PARENT/'execution/backboardd.log.current').read_text());assert old['coverage_qualified']
    assert load(PARENT/'execution/result.json')['state']=='CR340-lossless-wait-execution-observed-root-restored'
    prior,_,_=LEGACY.timeline(old,load(PARENT/'execution/collection-analysis.json')['script_window_us'])
    assert prior['count']==716 and prior['other_metrics']['done_us']['p95']==46310
    workload=module('post341_workload',WORK/'tools/summarize-core338-results.py').workload_profile
    prior['workload']=workload((PARENT/'execution/backboardd.log.current').read_text(),(PARENT/'execution/springboard-new.log').read_text(),prior['bounds_us'])
    summary['workload']=workload(backboard,sb,summary['bounds_us'])
    limited=dict(core,metrics={k:v for k,v in core['metrics'].items() if k in old['metrics']})
    split=LEGACY.attribution(limited,rows,tail)
    backlog=load(e/'queue-backlog-analysis.json')
    assert backlog['full_script_window']['count']==len(rows)
    assert all(backlog['full_script_window']['metrics'][k]==v for k,v in split['script_metrics'].items())
    comparisons={k:dict(baseline340_p95_us=prior['metrics'][k]['p95'],candidate341_p95_us=summary['metrics'][k]['p95']) for k in summary['metrics']}
    comparisons['commit_done_us']=dict(baseline340_p95_us=prior['other_metrics']['done_us']['p95'],candidate341_p95_us=summary['other_metrics']['done_us']['p95'])
    paths.extend([Path(__file__),WORK/'tests/test_program_io341_report.py',WORK/'tools/core341_log.py',WORK/'tools/collection341.py',WORK/'tools/summarize-core340-results.py',WORK/'tools/summarize-core338-results.py',
        BASE/'ready.json',BASE/'approval.json',BASE/'trial-plan.json',BASE/'final-review.json',
        e/'claim.json',e/'result.json',e/'restore-result.json',e/'independent-restore.json',e/'kernel.log',e/'springboard-new.log',
        e/'fresh-before/result.json',e/'post-capture/result.json',e/'restored-capture/result.json',e/'collection-analysis.json',
        e/'core-wait-execution-analysis.json',e/'queue-backlog-analysis.json',e/'bo-allocation-analysis.json',
        PARENT/'execution/result.json',PARENT/'execution/collection-analysis.json',PARENT/'execution/backboardd.log.current',PARENT/'execution/springboard-new.log'])
    report=dict(state='0341-qualified-raw-program-slab-IO-CPU-interval-attribution',baseline340=prior,candidate341=summary,
        p95_comparison=comparisons,category_and_submit_attribution=split,
        fine_attribution=dict(full_script=LEGACY.fine_aggregate(rows),completion_tail=LEGACY.fine_aggregate(slow)),
        program_IO=dict(full_script=detail(rows),completion_tail=detail(slow)),
        exact_predecessor_intervals=dict(full_script=weighted_wait(core,rows),completion_tail=weighted_wait(core,slow)),
        increasing_wait_12_CB_windows=bursts(rows),worker_reuse=core['worker_reuse'],
        BO_capture_window=backlog['BO_capture_window'],original_trial_result_unchanged=True,
        all_frozen_inputs_unchanged=True,device_commands=0,physical_FPS_qualified=False,
        scope='Qualified full13-stroke windows; diagnostic overhead/workload/scheduling/cache state differ, so p95 comparisons do not isolate causality. CPU bounds describe the calling thread, offCPU is not classified lock/GPU wait. Known program maxima are partial exact intervals; overlapping CB waits and nested phases are not additive utilization. No physical panel FPS inference.',
        input_pins={str(p.resolve()):sha(p) for p in paths})
    raw=(json.dumps(report,indent=2)+'\n').encode();assert len(raw)<=2*1048576
    out.mkdir()
    with (out/'comparison-summary.json').open('xb') as f:f.write(raw)
    print(json.dumps(dict(state=report['state'],candidate_count=summary['count'],p95_comparison=comparisons,
        program_IO_full_script=report['program_IO']['full_script']),indent=2))


if __name__=='__main__':main()
