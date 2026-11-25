"""Strict341 nested program/slab scopes and bounded IO CPU accounting."""
import ast
from collections import Counter
import importlib.util
from pathlib import Path
import re

SOURCE=Path(__file__).with_name('core340_log.py')
spec=importlib.util.spec_from_file_location('isolated341_base340',SOURCE)
OLD=importlib.util.module_from_spec(spec);spec.loader.exec_module(OLD)
# Keep the inherited record count4096; change only its per-line byte bound.
tree=ast.parse(SOURCE.read_text());overrides=[]
for fn in tree.body:
    if not isinstance(fn,ast.FunctionDef) or fn.name not in ('parse_extra','analyze'):continue
    changed=0
    if fn.name=='parse_extra':
        for n in ast.walk(fn):
            if isinstance(n,ast.Constant) and n.value==4096:n.value=8192;changed+=1
    else:
        for n in ast.walk(fn):
            if isinstance(n,ast.BinOp) and isinstance(n.op,ast.Mult) and isinstance(n.left,ast.Constant) and n.left.value==4097 and isinstance(n.right,ast.Constant) and n.right.value==4096:
                n.right.value=8192;changed+=1
    assert changed==1,(fn.name,changed);overrides.append(fn)
exec(compile(ast.Module(body=overrides,type_ignores=[]),str(SOURCE),'exec'),OLD.__dict__)
stats=OLD.stats;CATEGORIES=OLD.CATEGORIES;STAGES=OLD.STAGES
DRAW=OLD.DRAW;RENDER=OLD.RENDER;GPU=OLD.GPU
PREFIX='GAUGUIN CR341: '
PRIOR=re.compile(r'GAUGUIN (?:CR340|N340|Q340|C4Q340|CR339|N339|Q339|C4Q339|CR338|N338|Q338|C4Q338|Q337|C4Q321):')
PARTS={
    'address':('lookup','program_buffer','resource_keep','publication'),
    'resident':('lock','lookup_evict','new_BO','upload_publish','exit'),
    'table':('piece',),
    'piece':('align','acquire_record','validate','resource_keep_exit'),
    'pool':('size_lock','lookup','new_BO','reused_zero','counters','exit'),
}
COUNTS=('address_hits','address_misses','uploaded_entries_checked','resident_hits','resident_misses',
    'resident_entries_checked','piece_reuses','piece_slab_requests','piece_large_requests',
    'pool_hits','pool_misses','uploaded_word_bytes','resident_word_bytes','pooled_zero_bytes')
FIELDS=tuple((k+s,n) for k,parts in PARTS.items() for s,n in (('_counts',3),('_ns',len(parts)),('_max',len(parts)+3)))+(
    ('program_counts',14),('cpu_counts',3),('cpu_ns',9),('detail_flags',1))
CPU_SLOP_NS=2000


def normalize(text):
    lines=[]
    for line in text.splitlines():
        if PRIOR.search(line):continue
        if PREFIX in line:line=line.split(' address_counts=',1)[0]
        for tag in ('C4Q','Q','CR','N'):line=line.replace('GAUGUIN '+tag+'341:','GAUGUIN '+tag+'340:')
        lines.append(line)
    return '\n'.join(lines)+'\n'


def lifecycle(text):
    r=OLD.lifecycle(normalize(text));r['state']=r['state'].replace('340','341');return r


def identity(text):
    r=OLD.identity(normalize(text));r['state']=r['state'].replace('340','341');return r


def parse_extra(line):
    _head,separator,tail=line.partition(' address_counts=')
    if not separator or len(line.encode())+1>8192:return None
    tokens=('address_counts='+tail).split()
    if len(tokens)!=len(FIELDS):return None
    result={}
    for token,(key,n) in zip(tokens,FIELDS):
        name,sep,encoded=token.partition('=');values=encoded.split(',')
        if not sep or name!=key or len(values)!=n or any(not re.fullmatch(r'[0-9]+',v) for v in values):return None
        data=list(map(int,values))
        if any(v>=2**64 for v in data):return None
        result[key]=data[0] if key=='detail_flags' else data
    return result


def valid_extra(row,x):
    if x['detail_flags']!=0:return False
    for key,parts in PARTS.items():
        count,ok,hit=x[key+'_counts'];values=x[key+'_ns'];worst=x[key+'_max']
        job,start,end=worst[:3];phases=worst[3:]
        if count!=ok+hit or (key not in ('address','resident') and hit):return False
        if not count:
            if any(values+worst):return False
        else:
            if not (0<job<row['job'] and row['made_us']*1000-1000<=start<=end<=row['start_ns']):return False
            if not (sum(phases)==end-start<=sum(values)<=count*(end-start)):return False
            if any(a>b for a,b in zip(phases,values)):return False
            if job==row['draw_max_job']:
                body_begin=row['draw_max_start_ns']+sum(row['draw_max_phases'][:5]);body_end=body_begin+row['draw_max_phases'][5]
                if not body_begin<=start<=end<=body_end:return False
    a=x['address_counts'];r=x['resident_counts'];t=x['table_counts'];p=x['piece_counts'];b=x['pool_counts'];c=x['program_counts']
    if a[0]!=2*row['render_ok'] or t[0]!=row['render_ok'] or r[0]!=a[1] or p[0]<t[0]:return False
    if c[0]!=a[2] or c[1]!=a[1] or c[2]<c[0] or c[3]!=r[2] or c[4]!=r[1] or c[5]<c[3]:return False
    if sum(c[6:9])!=p[0] or sum(c[9:11])!=b[0] or b[0]<c[7]+c[8]:return False
    if c[12]>c[11] or c[13]<4096*c[9]:return False
    render=sum(row['render_ns'])
    if sum(x['address_ns'])+sum(x['table_ns'])>row['render_ns'][2]:return False
    if sum(x['resident_ns'])>x['address_ns'][1] or sum(x['piece_ns'])>render or sum(x['pool_ns'])>render:return False
    if x['cpu_counts']!=[1,1,2]:return False
    before,after,begin,end,overhead,lower,upper,off_lower,off_upper=x['cpu_ns']
    transport_begin=row['gpu_begin_ns']+sum(row['gpu_ns'][:3]);transport_end=transport_begin+row['gpu_ns'][3]
    if after<before or not begin or not (transport_begin<=begin<=row['io_begin_ns']<=row['io_end_ns']<=end<=transport_end):return False
    wall=end-begin;delta=after-before;io=row['io_ns']
    if delta>wall+CPU_SLOP_NS or overhead!=wall-io:return False
    expected_lower=max(0,delta-overhead-CPU_SLOP_NS);expected_upper=min(io,delta+CPU_SLOP_NS)
    return (0<=lower==expected_lower<=upper==expected_upper<=io and off_lower==io-upper and off_upper==io-lower)


DETAIL_METRICS={k+'_'+s+'_us':(k+'_ns',i) for k,parts in PARTS.items() for i,s in enumerate(parts)}
COUNT_METRICS={k:('program_counts',i) for i,k in enumerate(COUNTS)}


def value(row,key):
    if key in DETAIL_METRICS:
        field,i=DETAIL_METRICS[key];return row[field][i]/1000
    if key in COUNT_METRICS:
        field,i=COUNT_METRICS[key];return row[field][i]
    if key=='IO_CPU_delta_us':return (row['cpu_ns'][1]-row['cpu_ns'][0])/1000
    cpu={'IO_sampling_envelope_us':4,'IO_CPU_lower_us':5,'IO_CPU_upper_us':6,'IO_off_CPU_lower_us':7,'IO_off_CPU_upper_us':8}
    if key in cpu:return row['cpu_ns'][cpu[key]]/1000
    if key=='program_address_max_us':return (row['address_max'][2]-row['address_max'][1])/1000
    if key=='piece_max_us':return (row['piece_max'][2]-row['piece_max'][1])/1000
    return OLD.value(row,key)


def analyze(text):
    base=OLD.analyze(normalize(text));errors=Counter(base['errors']);extended={};total=0;limits=0
    for line in text.splitlines():
        if PRIOR.search(line):errors['prior_wire_in_current_collection']+=1
        if PREFIX not in line:continue
        total+=len(line.encode())+1
        if line==PREFIX+'limit=4096 coverage=incomplete':limits+=1;continue
        item=parse_extra(line);m=re.search(r'GAUGUIN CR341: object=(0x[0-9a-f]+) made_us=([0-9]+) ',line)
        if item is None or m is None:errors['malformed_program_or_CPU_row']+=1;continue
        key=(m[1],int(m[2]))
        if key in extended:errors['duplicate_program_or_CPU_row']+=1
        extended[key]=item
    if limits or len(extended)>4096 or total>4097*8192:errors['detail_trace_bound_or_limit']+=1
    rows=[]
    for row in base['rows']:
        x=extended.get((row['object'],row['made_us']))
        if x is None:errors['detail_identity_coverage']+=1;continue
        if not valid_extra(row,x):errors['invalid_program_slab_or_CPU_accounting']+=1;continue
        rows.append(dict(row,**x))
    if len(extended)!=base['core_records'] or len(rows)!=base['complete_count']:errors['detail_record_count']+=1
    keys=tuple(base['metrics'])+tuple(DETAIL_METRICS)+tuple(COUNT_METRICS)+(
        'IO_CPU_delta_us','IO_sampling_envelope_us','IO_CPU_lower_us','IO_CPU_upper_us',
        'IO_off_CPU_lower_us','IO_off_CPU_upper_us','program_address_max_us','piece_max_us')
    cpu=dict(records=sum(r['cpu_counts'][0] for r in rows),valid=sum(r['cpu_counts'][1] for r in rows),
        queries=sum(r['cpu_counts'][2] for r in rows),
        informative_intervals=sum(r['cpu_ns'][6]-r['cpu_ns'][5]<r['io_ns'] for r in rows),
        clock_slop_ns=CPU_SLOP_NS)
    cpu['observed']=bool(rows) and cpu['records']==cpu['valid']==len(rows) and cpu['queries']==2*len(rows)
    program=dict(address_calls=sum(r['address_counts'][0] for r in rows),table_calls=sum(r['table_counts'][0] for r in rows),piece_calls=sum(r['piece_counts'][0] for r in rows))
    program['observed']=bool(program['address_calls'] and program['table_calls'] and program['piece_calls'])
    qualified=base['coverage_qualified'] and bool(rows) and not errors
    return dict(base,state='CR341-program-slab-and-IO-accounting-qualified' if qualified else 'CR341-core-coverage-unqualified',
        coverage_qualified=qualified,errors=dict(errors),detail_records=len(extended),detail_trace_bytes=total,
        detail_limit_markers=limits,complete_count=len(rows),rows=rows,lifecycle=lifecycle(text),identity=identity(text),
        metrics={k:stats([value(r,k) for r in rows]) for k in keys},CPU_accounting=cpu,program_detail=program,
        inherited_record_limit_4096_preserved=True,inherited_line_bound_only_expanded_to_8192=True,
        program_phase_order=PARTS,program_counter_order=COUNTS,
        scope=base['scope']+'341 adds nested program lookup/resident upload/table/slab/pool elapsed scopes and bounded calling-thread CPU/off-CPU intervals. CPU bounds include the measured clock-query envelope and2us slop. Off-CPU may include blocking, runnable delay or work on other threads; it is not classified lock wait or pure driver/GPU execution. No independent percentiles or nested scopes may be added.')
