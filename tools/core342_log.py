"""Strict program-only new-BO CPU stages and numeric IO identities over 0341."""
from collections import Counter
import re
import core341_log as OLD
from phase342_log import bounds,partition

stats=OLD.stats;CATEGORIES=OLD.CATEGORIES;STAGES=OLD.STAGES
DRAW=OLD.DRAW;RENDER=OLD.RENDER;GPU=OLD.GPU
PREFIX='GAUGUIN CR342: '
PRIOR=re.compile(r'GAUGUIN (?:CR|N|Q|C4Q)(?:337|338|339|340|341):|GAUGUIN C4Q321:')
PARTS=('validate_metadata','GemNew','GemInfo','map','publication','failure_cleanup')
FIELDS=(('io_identity',6),('newbo_counts',5),('newbo_wall',6),('newbo_cpu',6),('newbo_envelope',6),
    ('newbo_max',10),('newbo_begin',6),('newbo_end',6),('newbo_max_cpu',6),('newbo_max_envelope',6),
    ('io_identity_flags',1),('newbo_flags',1))


def normalize(text):
    lines=[]
    for line in text.splitlines():
        if PRIOR.search(line):continue
        if PREFIX in line:line=line.split(' io_identity=',1)[0]
        for tag in ('C4Q','Q','CR','N'):line=line.replace('GAUGUIN '+tag+'342:','GAUGUIN '+tag+'341:')
        lines.append(line)
    return '\n'.join(lines)+'\n'


def lifecycle(text):
    r=OLD.lifecycle(normalize(text));r['state']=r['state'].replace('341','342');return r


def identity(text):
    r=OLD.identity(normalize(text));r['state']=r['state'].replace('341','342');return r


def parse_extra(line, *, program_slabs=False):
    head,sep,tail=line.partition(' io_identity=')
    if not sep or len(line.encode())+1>8192:return None
    tokens=('io_identity='+tail).split()
    fields=FIELDS+(('program_slab_reuses',1),) if program_slabs else FIELDS
    if len(tokens)!=len(fields):return None
    result={}
    for token,(key,n) in zip(tokens,fields):
        k,sep,encoded=token.partition('=');a=encoded.split(',')
        if not sep or k!=key or len(a)!=n or any(not re.fullmatch(r'[0-9]+',v) for v in a):return None
        a=list(map(int,a))
        if any(v>=2**64 for v in a):return None
        result[key]=a[0] if n==1 else a
    return result


def valid_extra(row,x):
    if x['io_identity_flags'] or x['newbo_flags']:return False
    tid,queue,handle,offset,words,fence=x['io_identity']
    if not (tid and all(0<v<2**32 for v in (queue,handle,words,fence)) and offset<2**32 and offset%4==0):return False
    calls,ok,failed,queries,query=x['newbo_counts']
    if calls+x.get('program_slab_reuses',0)!=row['program_counts'][4] or ok!=calls or failed or queries!=6*calls:return False
    vectors=('newbo_wall','newbo_cpu','newbo_envelope','newbo_max','newbo_begin','newbo_end','newbo_max_cpu','newbo_max_envelope')
    if not calls:return not any(v for k in vectors for v in x[k]) and query==0
    job,thread,bo,size,first,last,mask,n,q,flags=x['newbo_max']
    if not (0<job<row['job'] and thread and 0<bo<2**32 and size and mask==31 and n==6 and flags==0):return False
    if not row['made_us']*1000-1000<=first<=last<=row['start_ns']:return False
    if job==row['draw_max_job']:
        start=row['draw_max_start_ns']+sum(row['draw_max_phases'][:5]);end=start+row['draw_max_phases'][5]
        if not start<=first<=last<=end:return False
    try:
        p=partition(first,last,mask,n,q,flags,x['newbo_begin'],x['newbo_end'],x['newbo_max_cpu'],x['newbo_max_envelope'])
        for i in range(6):
            bounds(x['newbo_wall'][i],x['newbo_cpu'][i],x['newbo_envelope'][i],2000*calls)
            if any(a>b for a,b in ((p[i]['wall_ns'],x['newbo_wall'][i]),
                (x['newbo_max_cpu'][i],x['newbo_cpu'][i]),(x['newbo_max_envelope'][i],x['newbo_envelope'][i]))):return False
        if any(x[k][5] for k in ('newbo_wall','newbo_cpu','newbo_envelope')):return False
        if calls==1 and (q!=query or any(x[a]!=x[b] for a,b in (('newbo_cpu','newbo_max_cpu'),('newbo_envelope','newbo_max_envelope')))):return False
        return (q<=query and last-first<=sum(x['newbo_wall'])+query<=calls*(last-first)
            and sum(x['newbo_wall'])+query<=row['resident_ns'][2])
    except ValueError:return False


def value(row,key):
    if key.startswith('newbo_'):
        for i,name in enumerate(PARTS):
            if key=='newbo_'+name+'_us':return row['newbo_wall'][i]/1000
    return OLD.value(row,key)


def analyze(text, *, program_slabs=False):
    base=OLD.analyze(normalize(text));errors=Counter(base['errors']);extra={};total=0
    for line in text.splitlines():
        if PRIOR.search(line):errors['prior_wire_in_current_collection']+=1
        if PREFIX not in line:continue
        total+=len(line.encode())+1
        if line==PREFIX+'limit=4096 coverage=incomplete':errors['newbo_trace_limit']+=1;continue
        x=parse_extra(line,program_slabs=program_slabs);m=re.search(r'GAUGUIN CR342: object=(0x[0-9a-f]+) made_us=([0-9]+) ',line)
        if x is None or m is None:errors['malformed_IO_identity_or_newbo']+=1;continue
        k=m[1],int(m[2])
        if k in extra:errors['duplicate_IO_identity_or_newbo']+=1
        extra[k]=x
    if len(extra)>4096 or total>4097*8192:errors['newbo_trace_bounds']+=1
    rows=[]
    for row in base['rows']:
        x=extra.get((row['object'],row['made_us']))
        if x is None:errors['newbo_identity_coverage']+=1;continue
        if not valid_extra(row,x):errors['invalid_IO_identity_or_newbo_partition']+=1;continue
        rows.append(dict(row,**x))
    if len(extra)!=base['core_records'] or len(rows)!=base['complete_count']:errors['newbo_record_count']+=1
    metrics=tuple(base['metrics'])+tuple('newbo_'+k+'_us' for k in PARTS)
    qualified=base['coverage_qualified'] and bool(rows) and not errors
    activation=dict(calls=sum(r['newbo_counts'][0] for r in rows),program_only=True,records=len(rows))
    if program_slabs:activation['slab_reuses']=sum(r['program_slab_reuses'] for r in rows)
    activation['observed']=activation['calls']>0
    return dict(base,state='CR342-program-BO-and-IO-identity-qualified' if qualified else 'CR342-core-coverage-unqualified',
        coverage_qualified=qualified,errors=dict(errors),complete_count=len(rows),rows=rows,
        metrics={k:stats([value(r,k) for r in rows]) for k in metrics},lifecycle=lifecycle(text),identity=identity(text),
        newbo_detail=activation,newbo_records=len(extra),newbo_trace_bytes=total,
        scope=base['scope']+'342 records only program resident-miss newBO phases and per-phase CPU envelopes, and numeric IO thread/queue/handle/fence identities. Kernel joins are separately required. Maxima are partial evidence, not a complete job trace; mapping callback excludes IOKit VM work outside the callback.')
