#!/usr/bin/env python3
"""Cross-check Q337 queue identities against every independent C4Q321 buffer."""
from collections import Counter,defaultdict
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re

PREFIX='GAUGUIN Q337: '
ROW=re.compile(PREFIX+r'stage=([0-2]) object=(0x[0-9a-f]+) made_us=(\d+) queue=(\d+) ticket=(\d+) retired=(\d+) tick_us=(\d+)')
spec=importlib.util.spec_from_file_location('c4_queue321',Path(__file__).with_name('analyze-c4-queue-log.py'))
C4=importlib.util.module_from_spec(spec);spec.loader.exec_module(C4)

def analyze(text):
    c4=C4.analyze(text);errors=Counter();groups=defaultdict(dict);limits=0;records=0;size=0
    for line in text.splitlines():
        if PREFIX not in line:continue
        size+=len(line.encode())+1
        if line==PREFIX+'limit=32768 coverage=incomplete':limits+=1;continue
        m=ROW.fullmatch(line)
        if not m or len(line.encode())+1>192:errors['malformed_row']+=1;continue
        stage,obj,made,queue,ticket,retired,tick=m.groups()
        stage,made,queue,ticket,retired,tick=map(int,(stage,made,queue,ticket,retired,tick))
        if not (0<int(obj,16)<2**64 and 220000000<=made<=270000000 and
                made<=tick<=900000000 and 0<queue<2**64 and 0<ticket<2**64 and retired<2**64):
            errors['out_of_bounds']+=1;continue
        key=(obj,made);records+=1
        if stage in groups[key]:errors['duplicate_stage']+=1
        groups[key][stage]=dict(queue=queue,ticket=ticket,retired=retired,tick=tick)
    if records>32768 or limits>1 or size>32769*192:errors['bound_exceeded']+=1
    buffers={(r['object'],r['made_us']):r for r in c4['buffers']}
    complete=[];byqueue=defaultdict(list);identities=set()
    for key in sorted(groups.keys()|buffers.keys()):
        phases=groups.get(key,{})
        if set(phases)!={0,1,2}:errors['missing_queue_stages']+=1;continue
        if key not in buffers:errors['no_complete_C4_buffer']+=1;continue
        a,b,z=(phases[i]for i in range(3));t={int(k):v for k,v in buffers[key]['times_us'].items()}
        if len({(r['queue'],r['ticket'])for r in phases.values()})!=1:
            errors['identity_changed']+=1;continue
        ident=(a['queue'],a['ticket'])
        if ident in identities:errors['duplicate_queue_ticket']+=1
        identities.add(ident)
        if not (a['retired']<a['ticket'] and b['retired']==a['ticket']-1 and z['retired']==a['ticket']):
            errors['retirement_order']+=1
        if not (t[0]<=a['tick']<=t[1]<=b['tick']<=t[2] and t[4]<=z['tick']):
            errors['partial_order']+=1
        r=dict(object=key[0],made_us=key[1],queue=a['queue'],ticket=a['ticket'],
               earlier_unretired_at_admission=a['ticket']-a['retired']-1,
               pre_admission_us=a['tick']-t[0],admission_to_body_entry_us=b['tick']-a['tick'],
               body_us=z['tick']-b['tick'],post_status_body_us=z['tick']-t[4],
               entry_us=b['tick'],retire_us=z['tick'],admit_us=a['tick'])
        complete.append(r);byqueue[r['queue']].append(r)
    queues=[]
    for queue,rows in sorted(byqueue.items()):
        rows.sort(key=lambda r:r['ticket']);gaps=[]
        for a,b in zip(rows,rows[1:]):
            if b['admit_us']<a['admit_us'] or b['entry_us']<a['retire_us']:errors['queue_FIFO_order']+=1
            if b['ticket']!=a['ticket']+1:gaps.append([a['ticket'],b['ticket']])
        queues.append(dict(queue=queue,buffers=len(rows),unobserved_ticket_ranges=gaps,
                           max_earlier_unretired=max(r['earlier_unretired_at_admission']for r in rows)))
    qualified=c4['coverage_qualified'] and bool(complete) and not errors and not limits
    return dict(state='Q337-queue-CPU-milestones-observed'if qualified else'Q337-coverage-unqualified',
                coverage_qualified=qualified,errors=dict(errors),records=records,trace_bytes=size,
                limit_markers=limits,C4_coverage_qualified=c4['coverage_qualified'],
                C4_errors=c4['errors'],buffers=complete,queues=queues,
                metrics={k:C4.stats([r[k]for r in complete])for k in
                         ('earlier_unretired_at_admission','pre_admission_us','admission_to_body_entry_us','body_us','post_status_body_us')},
                physical_FPS_qualified=False,
                scope='Per-lifetime queue identity; retired marks the end of the block body after explicit self release. Dispatch block destruction, final logging and rescheduling remain outside this milestone. Counts include earlier running work; they are not waiting-only depth. No GPU-only or panel measurement.')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--log',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();raw=a.log.read_bytes();r=analyze(raw.decode('utf-8','replace'))
    r['input_sha256']=hashlib.sha256(raw).hexdigest()
    with a.out.open('x')as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in r.items()if k not in('buffers','queues')},indent=2))
if __name__=='__main__':main()
