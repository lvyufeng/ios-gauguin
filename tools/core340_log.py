"""Strict340 fine draw/BO/IO joins over the unchanged339 partial-order checks."""
from collections import Counter
import importlib.util
from pathlib import Path
import re

spec=importlib.util.spec_from_file_location('isolated340_base339',Path(__file__).with_name('core339_log.py'))
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
stats=OLD.stats;CATEGORIES=OLD.CATEGORIES;STAGES=OLD.STAGES
DRAW=('entry','vertex_bindings','fragment_bindings','argument_members','draw_state','render_body','resource_keep','exit')
RENDER=('entry_freshen','null_private','program_table','pass_setup','encode','packets','resource_uses','exit')
GPU=('entry','BO_list','descriptor','transport','publication')
PREFIX='GAUGUIN CR340: '
PRIOR=re.compile(r'GAUGUIN (?:CR339|N339|Q339|C4Q339|CR338|N338|Q338|C4Q338|Q337|C4Q321):')
FIELDS=(('draw_calls',1),('draw_ok',1),('render_calls',1),('render_ok',1),('render_skipped',1),
    ('draw_ns',8),('render_ns',8),('draw_reuse',4),('draw_max_job',1),('draw_max_start_ns',1),
    ('draw_max_end_ns',1),('draw_max_ns',1),('draw_max_phases',8),('gpu_calls',1),('gpu_ok',1),
    ('gpu_begin_ns',1),('gpu_end_ns',1),('gpu_ns',5),('submit_reuse',4),('io_calls',1),
    ('io_begin_ns',1),('io_end_ns',1),('io_ns',1),('bo_uses',1),('bo_unique',1),
    ('bo_comparisons',1),('bo_mode',1),('reserve_failures',1),('fine_flags',1))


def normalize(text):
    rows=[]
    for line in text.splitlines():
        if PRIOR.search(line):continue
        if PREFIX in line:line=line.split(' draw_calls=',1)[0]
        for tag in ('C4Q','Q','CR','N'):line=line.replace('GAUGUIN '+tag+'340:','GAUGUIN '+tag+'339:')
        rows.append(line)
    return '\n'.join(rows)+'\n'


def lifecycle(text):
    r=OLD.lifecycle(normalize(text));r['state']=r['state'].replace('339','340');return r


def identity(text):
    r=OLD.identity(normalize(text));r['state']=r['state'].replace('339','340');return r


def parse_extra(line):
    _head,separator,tail=line.partition(' draw_calls=')
    if not separator or len(line.encode())+1>4096:return None
    tokens=('draw_calls='+tail).split()
    if len(tokens)!=len(FIELDS):return None
    result={}
    for token,(key,n) in zip(tokens,FIELDS):
        name,separator,encoded=token.partition('=')
        if not separator or name!=key:return None
        parts=encoded.split(',')
        if len(parts)!=n or any(not re.fullmatch(r'[0-9]+',v) for v in parts):return None
        values=list(map(int,parts))
        if any(v>=2**64 for v in values):return None
        result[key]=values[0] if n==1 else values
    return result


FINE_METRICS={**{'draw_'+s+'_us':('draw_ns',i) for i,s in enumerate(DRAW)},
    **{'render_'+s+'_us':('render_ns',i) for i,s in enumerate(RENDER)},
    **{'gpu_'+s+'_us':('gpu_ns',i) for i,s in enumerate(GPU)}}


def value(row,key):
    if key in row:return row[key]
    if key in FINE_METRICS:
        field,i=FINE_METRICS[key];return row[field][i]/1000
    if key=='io_connect_us':return row['io_ns']/1000
    if key=='transport_outside_IO_us':return (row['gpu_ns'][3]-row['io_ns'])/1000
    if key=='core_native_outside_gpu_probe_us':return (row['submit_ns'][6]-sum(row['gpu_ns']))/1000
    if key=='render_job_outside_common_us':return (row['exec_ns'][2]-sum(row['draw_ns']))/1000
    if key=='draw_vector_growths':return row['draw_reuse'][2]
    if key=='submit_vector_growths':return row['submit_reuse'][2]
    raise KeyError(key)


def valid_extra(row,x):
    calls=x['draw_calls'];draw=x['draw_ns'];render=x['render_ns'];gpu=x['gpu_ns']
    good=(x['fine_flags']==0 and calls==x['draw_ok']==row['counts'][2] and
        x['render_calls']==calls and x['render_ok']+x['render_skipped']==calls and
        sum(draw)<=row['exec_ns'][2] and sum(render)<=draw[5] and
        sum(x['draw_reuse'][:2])==calls and all(v<=7*calls for v in x['draw_reuse'][2:]))
    if not calls:
        good=good and not any(draw+render+x['draw_reuse']+x['draw_max_phases']) and all(x[k]==0 for k in ('draw_max_job','draw_max_start_ns','draw_max_end_ns','draw_max_ns'))
    else:
        good=good and 0<x['draw_max_job']<row['job'] and row['made_us']*1000-1000<=x['draw_max_start_ns']<=x['draw_max_end_ns']<=row['start_ns']
        good=good and x['draw_max_ns']==x['draw_max_end_ns']-x['draw_max_start_ns']==sum(x['draw_max_phases'])
        good=good and x['draw_max_ns']<=sum(draw)<=calls*x['draw_max_ns'] and x['draw_max_ns']<=row['max_exec_ns'][2]
        good=good and all(a<=b for a,b in zip(x['draw_max_phases'],draw))
    begin,end=x['gpu_begin_ns'],x['gpu_end_ns']
    good=good and x['gpu_calls']==x['gpu_ok']==1 and row['submit_begin_ns']<=begin<=end<=row['submit_end_ns']
    good=good and sum(gpu)==end-begin<=row['submit_ns'][6]
    transport_begin=begin+sum(gpu[:3]);transport_end=transport_begin+gpu[3]
    good=good and x['io_calls']==1 and transport_begin<=x['io_begin_ns']<=x['io_end_ns']<=transport_end
    good=good and x['io_ns']==x['io_end_ns']-x['io_begin_ns']<=gpu[3]
    good=good and 1<=x['bo_unique']<=x['bo_uses']+1 and x['bo_mode'] in (0,1,2)
    good=good and sum(x['submit_reuse'][:2])==1 and all(v<=1 for v in x['submit_reuse'][2:])
    good=good and (x['submit_reuse'][0]==(x['bo_mode']!=0)) and x['reserve_failures']<=1
    if x['bo_mode']==0:good=good and x['reserve_failures']==0
    if x['bo_mode']==1:good=good and x['bo_unique']<=1024
    if x['bo_mode']==2:good=good and x['bo_unique']>1024 and x['submit_reuse'][3]==1
    return good


def analyze(text):
    base=OLD.analyze(normalize(text));errors=Counter(base['errors']);extended={};total=0;limits=0
    for line in text.splitlines():
        if PRIOR.search(line):errors['prior_wire_in_current_collection']+=1
        if PREFIX not in line:continue
        total+=len(line.encode())+1
        if line==PREFIX+'limit=4096 coverage=incomplete':limits+=1;continue
        item=parse_extra(line)
        common=line.split(' counts=',1)[0].replace(PREFIX,OLD.OLD.CR_PREFIX)
        m=OLD.OLD.CR.fullmatch(common)
        if not item or not m:errors['malformed_fine_core_row']+=1;continue
        key=(m[1],int(m[2]))
        if key in extended:errors['duplicate_fine_core_row']+=1
        extended[key]=item
    if limits or len(extended)>4096 or total>4097*4096:errors['fine_trace_bound_or_limit']+=1
    rows=[]
    for row in base['rows']:
        x=extended.get((row['object'],row['made_us']))
        if x is None:errors['fine_identity_coverage']+=1;continue
        if not valid_extra(row,x):errors['invalid_draw_submit_IO_or_reuse_partition']+=1;continue
        rows.append(dict(row,**x))
    if len(extended)!=base['core_records'] or len(rows)!=base['complete_count']:errors['fine_record_count']+=1
    keys=tuple(base['metrics'])+tuple(FINE_METRICS)+('io_connect_us','transport_outside_IO_us','core_native_outside_gpu_probe_us',
        'render_job_outside_common_us','draw_calls','bo_uses','bo_unique','bo_comparisons','draw_vector_growths','submit_vector_growths')
    reuse=dict(borrowed_draw_calls=sum(r['draw_reuse'][0] for r in rows),
        borrowed_submit_calls=sum(r['submit_reuse'][0] for r in rows),
        warm_indexed_submits=sum(r['bo_mode']==1 and r['submit_reuse'][2]==0 for r in rows))
    reuse['observed']=bool(reuse['borrowed_draw_calls'] and reuse['borrowed_submit_calls'] and reuse['warm_indexed_submits'])
    qualified=base['coverage_qualified'] and bool(rows) and not errors
    return dict(base,state='CR340-core-wait-fine-draw-submit-IO-qualified' if qualified else 'CR340-core-coverage-unqualified',
        coverage_qualified=qualified,errors=dict(errors),fine_records=len(extended),fine_trace_bytes=total,worker_reuse=reuse,
        fine_limit_markers=limits,complete_count=len(rows),rows=rows,lifecycle=lifecycle(text),identity=identity(text),
        metrics={k:stats([value(r,k) for r in rows]) for k in keys},draw_phase_order=DRAW,render_phase_order=RENDER,GPU_phase_order=GPU,
        scope=base['scope']+'340 adds nested drawCommon/render CPU phases, Gpu::submit BO preparation vs transport and actual IOConnect elapsed, plus bounded worker scratch counters. Time scopes overlap by nesting; they must not be added together. Actual IO elapsed includes kernel waits, not GPU-only execution.')
