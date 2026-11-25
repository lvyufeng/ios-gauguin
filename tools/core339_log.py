"""Strict339 category/submit records over the unchanged338 partial orders.

Durations are CPU elapsed, including preemption. Category wait prefixes measure
worker body residence, not GPU work. Job queue latencies overlap.
"""
from collections import Counter
import importlib.util
from pathlib import Path
import re

spec=importlib.util.spec_from_file_location('isolated339_partial_orders338',Path(__file__).with_name('core338_log.py'))
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
stats=OLD.stats
CATEGORIES=('control','bindings','render','clear','compute','transfer_append','commit','notification')
STAGES=('entry','pass_tail','command_BO','command_copy','queue_lock','fault_query','native_submit','publication')
PREFIX='GAUGUIN CR339: '
ARRAY=r'(\d+(?:,\d+){7})'
EXTRA=re.compile(r' counts='+ARRAY+r' exec_ns='+ARRAY+r' wait_ns='+ARRAY+r' max_exec_ns='+ARRAY+
    r' max_class=(\d+) max_job=(\d+) max_enq_ns=(\d+) max_start_ns=(\d+) max_end_ns=(\d+)'+
    r' submit_mask=(\d+) submit_outcome=(\d+) submit_begin_ns=(\d+) submit_end_ns=(\d+) submit_ns='+ARRAY+r' flags=(\d+)')
SCALARS=('max_class','max_job','max_enq_ns','max_start_ns','max_end_ns','submit_mask','submit_outcome',
         'submit_begin_ns','submit_end_ns')
OLD_WIRE=re.compile(r'GAUGUIN (?:CR338|N338|Q338|C4Q338|Q337|C4Q321):')


def normalized(text):
    rows=[]
    for line in text.splitlines():
        if OLD_WIRE.search(line):continue
        if PREFIX in line:
            line=line.split(' counts=',1)[0]
        for tag in ('C4Q','Q','CR','N'):line=line.replace('GAUGUIN '+tag+'339:','GAUGUIN '+tag+'338:')
        rows.append(line)
    return '\n'.join(rows)+'\n'


def lifecycle(text):
    r=OLD.lifecycle(normalized(text));r['state']=r['state'].replace('338','339');return r


def identity(text):
    r=OLD.identity(normalized(text));r['state']=r['state'].replace('338','339');return r


def analyze(text):
    base=OLD.analyze(normalized(text));errors=Counter(base['errors']);extended={};trace_bytes=0;limits=0
    for line in text.splitlines():
        if OLD_WIRE.search(line):errors['prior_wire_in_current_collection']+=1
        if PREFIX not in line:continue
        trace_bytes+=len(line.encode())+1
        if line==PREFIX+'limit=4096 coverage=incomplete':limits+=1;continue
        common,separator,tail=line.partition(' counts=')
        m=OLD.CR.fullmatch(common.replace(PREFIX,OLD.CR_PREFIX));x=EXTRA.fullmatch(' counts='+tail if separator else '')
        if not m or not x or len(line.encode())+1>2048:
            errors['malformed_extended_core_row']+=1;continue
        key=(m[1],int(m[2]));g=x.groups()
        item={name:list(map(int,g[i].split(','))) for i,name in enumerate(('counts','exec_ns','wait_ns','max_exec_ns'))}
        item.update(zip(SCALARS,map(int,g[4:13])));item['submit_ns']=list(map(int,g[13].split(',')));item['flags']=int(g[14])
        if key in extended:errors['duplicate_extended_core_row']+=1
        extended[key]=item
    if limits or len(extended)>4096 or trace_bytes>4097*2048:errors['extended_trace_bound_or_limit']+=1
    rows=[]
    for row in base['rows']:
        key=(row['object'],row['made_us']);x=extended.get(key)
        if x is None:errors['extended_identity_coverage']+=1;continue
        counts,execution,wait,maximum=(x[k] for k in ('counts','exec_ns','wait_ns','max_exec_ns'))
        numeric=[n for v in (counts,execution,wait,maximum,x['submit_ns']) for n in v]+[x[k] for k in (*SCALARS,'flags')]
        valid=all(0<=n<2**64 for n in numeric)
        valid=valid and sum(counts)==row['jobs'] and sum(execution)==row['own_exec_ns'] and sum(wait)==row['busy_wait_ns']
        valid=valid and counts[6]==1 and counts[7]==0 and execution[6]==maximum[6]==row['end_ns']-row['start_ns']
        valid=valid and all((n==s==m==0) or (n>0 and m<=s<=n*m) for n,s,m in zip(counts,execution,maximum))
        k=x['max_class'];begin=x['submit_begin_ns'];end=x['submit_end_ns']
        valid=valid and k<8 and 0<x['max_job']<=row['job'] and counts[k]>0
        valid=valid and row['made_us']*1000-1000<=x['max_enq_ns']<=x['max_start_ns']<=x['max_end_ns']<=row['end_ns']
        valid=valid and x['max_end_ns']-x['max_start_ns']==max(maximum)==maximum[k]
        valid=valid and x['max_start_ns']-x['max_enq_ns']<=row['max_queue_ns']
        if k==6:
            valid=valid and (x['max_job'],x['max_enq_ns'],x['max_start_ns'],x['max_end_ns'])==(row['job'],row['enq_ns'],row['start_ns'],row['end_ns'])
        else:valid=valid and x['max_job']<row['job'] and x['max_end_ns']<=row['start_ns']
        valid=valid and row['start_ns']<=begin<=end<=row['end_ns'] and sum(x['submit_ns'])==end-begin
        valid=valid and x['submit_mask']==255 and x['submit_outcome']==0 and x['flags']==0
        if not valid:errors['invalid_category_or_submit_partition']+=1;continue
        item=dict(row,**x)
        for i,name in enumerate(CATEGORIES):
            item['own_'+name+'_us']=execution[i]/1000
            item['wait_'+name+'_us']=wait[i]/1000
            item['max_'+name+'_us']=maximum[i]/1000
        for i,name in enumerate(STAGES):item['submit_'+name+'_us']=x['submit_ns'][i]/1000
        item['commit_outside_submit_us']=(execution[6]-(end-begin))/1000
        rows.append(item)
    worst_keys=[(r['queue'],r['max_job']) for r in rows]
    if len(worst_keys)!=len(set(worst_keys)):errors['worst_job_identity_collision']+=1
    if len(extended)!=base['core_records'] or len(rows)!=base['complete_count']:errors['extended_record_count']+=1
    metrics=tuple(base['metrics'])+tuple('own_'+k+'_us' for k in CATEGORIES)+tuple('wait_'+k+'_us' for k in CATEGORIES)+tuple('max_'+k+'_us' for k in CATEGORIES)+tuple('submit_'+k+'_us' for k in STAGES)+('commit_outside_submit_us',)
    qualified=base['coverage_qualified'] and bool(rows) and not errors
    return dict(base,state='CR339-core-wait-execution-qualified' if qualified else 'CR339-core-coverage-unqualified',
        coverage_qualified=qualified,errors=dict(errors),extended_records=len(extended),complete_count=len(rows),rows=rows,
        lifecycle=lifecycle(text),identity=identity(text),category_order=CATEGORIES,submit_stage_order=STAGES,
        metrics={k:stats([r[k] for r in rows]) for k in metrics},extended_trace_bytes=trace_bytes,
        core_record_limit_markers=limits,
        scope=base['scope']+'339 adds an exact eight-category partition of observed busy wait and own completed bodies, worst own job identity/time bounds, and eight contiguous CPU submit phases. No CPU utilization or GPU-only claim.')
