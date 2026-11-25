"""Strict 0338 wires, independent lifecycle coverage, and core wait/execution.

Reuse the proven partial-order decoders under isolated module globals. Wire338
phase4 is notification admission, never a status-drain measurement. The old
files and their global decoder state remain untouched.
"""
from collections import Counter,defaultdict
import importlib.util
from pathlib import Path
import re


def module(name,leaf):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(leaf))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


LIFE=module('isolated_c4_338','analyze-c4-queue-log.py')
LIFE.PREFIX='GAUGUIN C4Q338: '
LIFE.ROW=re.compile(LIFE.ROW.pattern.replace('C4Q321','C4Q338'))
LIFE.LIMIT=LIFE.LIMIT.replace('C4Q321','C4Q338')
LIFE.STAGES={('notification_admission' if k=='core_status_drain' else k):v for k,v in LIFE.STAGES.items()}
stats=LIFE.stats


def lifecycle(text):
    result=LIFE.analyze(text)
    for row in result['buffers']:
        value=row.pop('status');row['notification_return_value']=value
        if value!=0:
            result['errors']['invalid_phase4_reserved_value']=result['errors'].get('invalid_phase4_reserved_value',0)+1
    result['coverage_qualified']=result['coverage_qualified'] and not result['errors']
    result['state']='C4Q338-CPU-stages-observed' if result['coverage_qualified'] else 'C4Q338-coverage-unqualified'
    result['duration_semantics']='CPU elapsed and overlapping branches; phase4 is notification admission return, no synchronous status snapshot.'
    return result


def identity(text):
    decoder=module('isolated_identity338','analyze-queue337.py')
    decoder.PREFIX='GAUGUIN Q338: '
    decoder.ROW=re.compile(decoder.ROW.pattern.replace('Q337','Q338'))
    class Adapter:
        analyze=staticmethod(lifecycle)
        stats=staticmethod(stats)
    decoder.C4=Adapter
    result=decoder.analyze(text)
    for row in result['buffers']:
        row['post_notification_admission_body_us']=row.pop('post_status_body_us')
    result['metrics']['post_notification_admission_body_us']=result['metrics'].pop('post_status_body_us')
    result['state']='Q338-queue-CPU-milestones-observed' if result['coverage_qualified'] else 'Q338-coverage-unqualified'
    result['scope']='Frontend queue lifetime/ticket/retirement only. Retired precedes final logging/block destruction and may precede core commit execution and GPU completion.'
    return result


CR_PREFIX='GAUGUIN CR338: '
N_PREFIX='GAUGUIN N338: '
CR=re.compile(CR_PREFIX+r'object=(0x[0-9a-f]+) made_us=(\d+) queue=(\d+) ticket=(\d+) job=(\d+) enq_ns=(\d+) start_ns=(\d+) end_ns=(\d+) busy_wait_ns=(\d+) jobs=(\d+) own_exec_ns=(\d+) sum_queue_ns=(\d+) max_queue_ns=(\d+) state=(\d+) failed=([01])')
NOTICE=re.compile(N_PREFIX+r'object=(0x[0-9a-f]+) made_us=(\d+) tick_us=(\d+) state=(\d+)')
FIELDS=('made_us','queue','ticket','job','enq_ns','start_ns','end_ns','busy_wait_ns',
        'jobs','own_exec_ns','sum_queue_ns','max_queue_ns','state','failed')


def analyze(text):
    c4=lifecycle(text);q=identity(text);errors=Counter();core={};notice={};limits=0;bytecount=0
    for line in text.splitlines():
        if CR_PREFIX in line:
            bytecount+=len(line.encode())+1
            if line==CR_PREFIX+'limit=4096 coverage=incomplete':limits+=1;continue
            m=CR.fullmatch(line)
            if not m or len(line.encode())+1>512:errors['malformed_core_row']+=1;continue
            obj=m[1];row=dict(zip(FIELDS,map(int,m.groups()[1:])));row['object']=obj
            key=(obj,row['made_us'])
            if key in core:errors['duplicate_core_row']+=1
            core[key]=row
        elif N_PREFIX in line:
            bytecount+=len(line.encode())+1
            if line==N_PREFIX+'limit=4096 coverage=incomplete':limits+=1;continue
            m=NOTICE.fullmatch(line)
            if not m or len(line.encode())+1>128:errors['malformed_notice_row']+=1;continue
            obj,made,tick,state=m.groups();key=(obj,int(made))
            if key in notice:errors['duplicate_notice_row']+=1
            notice[key]=dict(tick_us=int(tick),state=int(state))
    if len(core)>4096 or len(notice)>4096 or limits>2 or bytecount>4097*(512+128):
        errors['trace_bound']+=1
    cb={(r['object'],r['made_us']):r for r in c4['buffers']}
    ids={(r['object'],r['made_us']):r for r in q['buffers']};rows=[];queues=defaultdict(list)
    for key in sorted(core.keys()|notice.keys()|cb.keys()|ids.keys()):
        if not all(key in group for group in (core,notice,cb,ids)):
            errors['independent_identity_coverage']+=1;continue
        r=core[key];n=notice[key];b=cb[key];i=ids[key];t={int(k):v for k,v in b['times_us'].items()}
        if 'existing_timeline' not in b:
            errors['independent_timeline_absent']+=1;continue
        valid=(0<int(r['object'],16)<2**64 and 220000000<=r['made_us']<=270000000 and
            all(0<r[k]<2**64 for k in ('queue','ticket','job','jobs')) and
            r['made_us']*1000-1000<=r['enq_ns']<=r['start_ns']<=r['end_ns']<=900000000000 and
            0<=r['busy_wait_ns']<=r['start_ns']-r['enq_ns'] and
            r['end_ns']-r['start_ns']<=r['own_exec_ns']<2**64 and
            r['start_ns']-r['enq_ns']<=r['max_queue_ns']<=r['sum_queue_ns']<2**64 and
            r['state'] in (2,3,4,5) and not r['failed'] and n['state'] in (2,3,4,5) and
            r['state']<=n['state'] and (r['queue'],r['ticket'])==(i['queue'],i['ticket']) and
            t[2]*1000-1000<=r['enq_ns']<=t[3]*1000+1000 and
            # Completion can finish before the frontend even admits notice.
            # Its timing read cannot order a not-yet-enqueued notification.
            # The independent notification lease survives that whole branch.
            r['end_ns']-1000<=n['tick_us']*1000<=900000000000)
        if not valid:errors['invalid_core_or_notice_contract']+=1;continue
        wait=r['start_ns']-r['enq_ns'];duration=r['end_ns']-r['start_ns']
        item=dict(r,notice=n,frontend_queue_us=t[1]-t[0],frontend_body_us=i['retire_us']-t[1],
            commit_done_us=b['existing_timeline']['done_us']-t[0],
            core_queue_wait_us=wait/1000,core_observed_busy_in_wait_us=r['busy_wait_ns']/1000,
            core_uncovered_queue_wait_us=(wait-r['busy_wait_ns'])/1000,
            core_commit_execution_us=duration/1000,own_recording_execution_us=r['own_exec_ns']/1000,
            notification_lag_us=max(0,n['tick_us']-r['end_ns']/1000),
            all_job_queue_latency_sum_us=r['sum_queue_ns']/1000,max_job_queue_latency_us=r['max_queue_ns']/1000)
        rows.append(item);queues[item['queue']].append(item)
    for queue,items in queues.items():
        items.sort(key=lambda r:r['ticket'])
        if any(a['job']>=b['job'] or a['end_ns']>b['start_ns'] for a,b in zip(items,items[1:])):
            errors['core_commit_FIFO_or_serial_execution']+=1
    qualified=c4['coverage_qualified'] and q['coverage_qualified'] and bool(rows) and not errors and not limits
    metrics=('frontend_queue_us','frontend_body_us','commit_done_us','core_queue_wait_us',
             'core_observed_busy_in_wait_us','core_uncovered_queue_wait_us','core_commit_execution_us',
             'own_recording_execution_us','notification_lag_us','all_job_queue_latency_sum_us','max_job_queue_latency_us')
    return dict(state='CR338-core-wait-execution-qualified' if qualified else 'CR338-core-coverage-unqualified',
        coverage_qualified=qualified,errors=dict(errors),limit_markers=limits,trace_bytes=bytecount,
        core_records=len(core),notification_records=len(notice),complete_count=len(rows),rows=rows,
        metrics={k:stats([r[k] for r in rows]) for k in metrics},lifecycle=c4,identity=q,
        physical_FPS_qualified=False,device_commands=0,
        scope='CPU elapsed ns and rounded lifecycle us. Core queue residence is split into observed prior worker-body execution and uncovered gaps. Per-CB execution is a sum of its completed job bodies; job queue latencies overlap and are not a critical-path sum. One notification CPU job per commit; no GPU-only or panel FPS measurement. ±1us cross-wire rounding tolerance.')
