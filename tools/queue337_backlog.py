"""Attribute observed frontend wait only to work on the same queue lifetime."""
from collections import defaultdict
import math
import statistics

def stats(values):
    v=sorted(values)
    return dict(count=len(v),median=statistics.median(v)if v else None,
                p95=v[math.ceil(.95*len(v))-1]if v else None,max=max(v)if v else None)

def clipped_union(spans,start,end):
    total=0;cursor=start
    for a,z in sorted(spans):
        a,z=max(a,start),min(z,end)
        if a<z:total+=max(0,z-max(cursor,a));cursor=max(cursor,z)
    return total

def analyze(collection,c4,identity):
    if not collection.get('coverage_qualified'):
        return dict(state='Q337-backlog-interpretation-withheld',reason='collection-unqualified',
                    physical_FPS_qualified=False,device_commands=0)
    if not c4['coverage_qualified']or not identity['coverage_qualified']:
        raise ValueError('qualified collection contradicted by independent trace coverage')
    cb={(r['object'],r['made_us']):r for r in c4['buffers']}
    byqueue=defaultdict(list);begin,end=collection['script_window_us']
    for r in identity['buffers']:
        c=cb[r['object'],r['made_us']];t={int(k):v for k,v in c['times_us'].items()}
        item=dict(r,times=t,commit_done_us=c['existing_timeline']['done_us']-t[0],queue_us=t[1]-t[0])
        if item['commit_done_us']<0:raise ValueError('negative completed CB duration')
        byqueue[r['queue']].append(item)
    queues=[];all_details=[]
    for queue,rows in sorted(byqueue.items()):
        rows.sort(key=lambda r:r['ticket']);selected=[r for r in rows if begin<=r['made_us']<end]
        if not selected:continue
        intervals=[(r['times'][1],r['retire_us'])for r in rows]
        details=[]
        for r in selected:
            t=r['times'];a,z=t[0],t[1]
            prior=[p for p in rows if p['ticket']<r['ticket']and p['retire_us']>a and p['times'][1]<z]
            occupied=clipped_union(intervals,a,z);components={}
            for name,lo,hi in [('turn_and_event',1,2),('core_commit_call',2,3),('status_drain',3,4),('post_status_body',4,None)]:
                spans=[(p['times'][lo],p['retire_us']if hi is None else p['times'][hi])for p in prior]
                components[name]=clipped_union(spans,a,z)
            if sum(components.values())!=occupied:raise ValueError('same-queue service partition overlaps or is incomplete')
            tickets=[p['ticket']for p in prior]
            detail=dict(queue=queue,ticket=r['ticket'],made_us=r['made_us'],queue_us=r['queue_us'],
                commit_done_us=r['commit_done_us'],earlier_unretired_snapshot=r['earlier_unretired_at_admission'],
                observed_same_queue_body_us=occupied,uncovered_wait_us=r['queue_us']-occupied,
                predecessor_count=len(prior),predecessor_tickets=tickets,
                unobserved_predecessor_ticket_gap=any(b!=a+1 for a,b in zip(tickets,tickets[1:])),
                unobserved_snapshot_predecessors=max(0,r['earlier_unretired_at_admission']-len(prior)),
                wait_components_us=components,
                own_service_us=r['retire_us']-t[1],own_status_drain_us=t[4]-t[3],
                own_post_status_body_us=r['retire_us']-t[4])
            details.append(detail)
        ranked=sorted(details,key=lambda r:r['commit_done_us']);all_details.extend(details)
        episodes=[];current=[]
        def finish():
            if not current:return
            span=current[-1]['retire_us']-current[0]['times'][1]
            arrival_span=current[-1]['admit_us']-current[0]['admit_us']
            episodes.append(dict(first_ticket=current[0]['ticket'],last_ticket=current[-1]['ticket'],
                buffers=len(current),elapsed_us=span,
                observed_body_us=sum(r['retire_us']-r['times'][1]for r in current),
                admission_span_us=arrival_span,
                admission_rate_per_second=(len(current)-1)*1e6/arrival_span if arrival_span else None,
                service_rate_per_second=len(current)*1e6/span if span else None))
        for r in rows:
            if current and (r['ticket']!=current[-1]['ticket']+1 or r['admit_us']>current[-1]['retire_us']):
                finish();current=[]
            current.append(r)
        finish()
        queues.append(dict(queue=queue,script_buffers=len(selected),metrics={k:stats([r[k]for r in details])for k in
            ('queue_us','commit_done_us','earlier_unretired_snapshot','uncovered_wait_us','own_service_us','own_status_drain_us','own_post_status_body_us')},
            p95_ranked_CB=ranked[math.ceil(.95*len(ranked))-1],
            longest_queues=sorted(details,key=lambda r:r['queue_us'],reverse=True)[:12],
            busiest_observed_episodes=sorted(episodes,key=lambda r:r['buffers'],reverse=True)[:12]))
    if not queues:raise ValueError('no identified queue buffers in validated script window')
    ranked=sorted(all_details,key=lambda r:r['commit_done_us']);tails=ranked[math.ceil(.95*len(ranked))-1:]
    return dict(state='Q337-identified-queue-backlog-observed',queues=queues,
        script_window_us=[begin,end],script_buffers=len(all_details),
        overall_metrics={k:stats([r[k]for r in all_details])for k in('queue_us','commit_done_us','uncovered_wait_us')},
        overall_p95_ranked_CB=ranked[math.ceil(.95*len(ranked))-1],tail_count=len(tails),
        tail_totals_us={k:sum(r[k]for r in tails)for k in ('queue_us','observed_same_queue_body_us','uncovered_wait_us')},
        tail_predecessor_components_us={k:sum(r['wait_components_us'][k]for r in tails)for k in
            ('turn_and_event','core_commit_call','status_drain','post_status_body')},
        physical_FPS_qualified=False,device_commands=0,
        scope='CPU elapsed with logging/scheduling overhead. Queue lifetimes are explicit; uncovered wait also includes unseen tickets, pre-admission work and unobserved tails. Retired milestones precede final log write and dispatch block destruction. Episode rates are admissions/service over the whole trace, not panel FPS. Tail is the global ranked script tail. Stage/compiler overlap alone does not establish a causal CB/shader identity.')
