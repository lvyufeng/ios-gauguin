"""Lossless bounded kernel stream and exact per-call user/kernel identity joins."""
from collections import Counter
import re
import struct
from phase342_log import partition,bounds as CPU_bounds

PREFIX='SWEET IO342: '
BEGIN=(('version',1),('first_ns',1),('last_ns',1),('count',1),('capacity',1),('lost',1),('pending',1),
    ('invalid',1),('row_bytes',1),('byte_limit',1),('byte_limited',1))
END=(('count',1),('lost',1),('pending',1),('invalid',1),('emitted',1),('byte_limited',1))
FIELDS=tuple((k,1) for k in ('index','token','pid','tid','selector','queue','fence','handle','bytes','bos','cmds','result',
    'first_ns','last_ns','query_ns','queries','mask','flags','wait_ns','waits'))+tuple((k,12) for k in ('begin','end','cpu','envelope'))
PHASES={
    70:('request_lock','GPU_lock','pending_gate','arguments_descriptors','copyin','BO_validation',
        'command_validation','surface_alias_validation','escrow','surface_cache_flush','runtime_issue','publication_cleanup'),
    66:('request_lock','GPU_lock','pending_gate','validation_cache_lookup','backing_allocation_pressure_retry',
        'zero','limits_slots_VA','prepare','physical_spans_alias','PTEs','synchronize','publication_cleanup'),
    67:('request_lock','GPU_lock','pending_gate','lookup','unused4','unused5','unused6','unused7','unused8','unused9','unused10','copyout_cleanup'),
    256:('request_lock','GPU_lock','lookup','fast_policy','pending_gate','retain_ready','unused6','unused7','unused8','unused9','unused10','publication_metrics'),
}


def fields(text,contract,*,positional=False):
    a=text.split()
    if len(a)!=len(contract):raise ValueError('kernel field count')
    result={}
    for token,(key,n) in zip(a,contract):
        value=token
        if not positional:
            k,sep,value=token.partition('=')
            if not sep or k!=key:raise ValueError('kernel field grammar')
        v=value.split(',')
        if len(v)!=n or any(not re.fullmatch(r'[0-9]+',s) for s in v):raise ValueError('kernel field grammar')
        v=list(map(int,v))
        if any(x>=2**64 for x in v):raise ValueError('kernel field overflow')
        result[key]=v[0] if n==1 else v
    return result


def ring_status(raw,text):
    if raw is None:return dict(qualified=False,reason='raw persistent ring missing')
    try:
        magic,version,size,total,seq=struct.unpack_from('<8sIIQQ',raw)
        ok=(len(raw)==4198400 and magic==b'SWEETLOG' and version==1 and size==4194304 and
            0<total<=size and seq>0 and raw[4096:4096+total].decode('utf-8').replace('\r','')==text)
        return dict(qualified=ok,ring_bytes=size,total_bytes=total,flush_sequence=seq,wrapped=total>size,
            decoded_raw_equal=ok)
    except (ValueError,UnicodeError,struct.error):return dict(qualified=False,reason='invalid persistent ring')


def parse(text,raw=None):
    errors=Counter();rows=[];header=None;footer=None;row_bytes=0;closed=False
    stream=[s for s in text.splitlines() if PREFIX in s]
    if not stream:errors['missing_kernel_stream']+=1
    for line in stream:
        if not line.startswith(PREFIX) or len(line.encode())+2>2048:
            errors['kernel_line_bound_or_prefix']+=1;continue
        tail=line[len(PREFIX):]
        try:
            kind,sep,body=tail.partition(' ')
            if not sep:raise ValueError('kernel record grammar')
            if kind=='begin':
                if header is not None or rows or closed:raise ValueError('duplicate or out-of-order begin')
                header=fields(body,BEGIN)
            elif kind=='end':
                if header is None or closed:raise ValueError('duplicate or out-of-order end')
                footer=fields(body,END);closed=True
            elif kind=='row':
                if header is None or closed:raise ValueError('row outside stream')
                r=fields(body,FIELDS,positional=header['version']==2);row_bytes+=len(line.encode())+2
                if r['index']!=len(rows) or r['token']!=len(rows)+1:raise ValueError('kernel index/token continuity')
                if r['selector'] not in PHASES or not 0<r['pid']<2**31 or not r['tid']:raise ValueError('kernel caller identity')
                if any(r[k]>=2**32 for k in ('queue','fence','handle','bos','cmds','result')):raise ValueError('kernel request identity width')
                if not 210000000000<=r['first_ns']<270000000000:raise ValueError('kernel capture start outside window')
                if r['wait_ns']>r['last_ns']-r['first_ns'] or bool(r['waits'])!=bool(r['wait_ns']):raise ValueError('nested unlocked waits')
                r['phases']=partition(r['first_ns'],r['last_ns'],r['mask'],r['queries'],r['query_ns'],r['flags'],
                    r['begin'],r['end'],r['cpu'],r['envelope'])
                for i,p in enumerate(r['phases']):p.update(begin_ns=r['begin'][i],end_ns=r['end'][i])
                if not r['result']:
                    required={70:4095,67:2063,256:2111}.get(r['selector'])
                    if required is not None and r['mask']!=required:raise ValueError('successful selector phase mask')
                    if r['selector']==66 and r['mask'] not in (2095,4095):raise ValueError('successful allocation phase mask')
                rows.append(r)
            else:raise ValueError('unknown kernel record')
        except ValueError as e:errors[str(e)]+=1
    if header is None or footer is None:errors['missing_kernel_begin_or_end']+=1
    else:
        if (header['version'] not in (1,2) or header['first_ns']!=210000000000 or header['last_ns']!=270000000000 or
            header['capacity']!=4096 or not 0<header['count']<=4096 or header['byte_limit']!=2097152 or
            any(header[k] or footer[k] for k in ('lost','pending','invalid','byte_limited')) or
            header['count']!=footer['count'] or header['count']!=footer['emitted'] or header['count']!=len(rows) or
            row_bytes!=header['row_bytes'] or row_bytes>2097152-4096 or sum(len(s.encode())+2 for s in stream)>2097152):
            errors['kernel_stream_incomplete_or_over_bound']+=1
    ring=ring_status(raw,text)
    if not ring['qualified']:errors['persistent_ring_not_lossless']+=1
    return dict(state='IO342-kernel-stream-qualified' if not errors else 'IO342-kernel-stream-unqualified',
        coverage_qualified=not errors,errors=dict(errors),header=header,footer=footer,rows=rows,ring=ring,
        phase_names=PHASES,device_commands=0,physical_FPS_qualified=False)


def inside(r,start,end):return start-1000<=r['first_ns']<=r['last_ns']<=end+1000


def join(decoded,core,bounds,*,require_program_activity=True):
    """Qualify all in-window submits and observed program maxima. Warm windows may have neither allocation nor reuse."""
    errors=Counter(decoded['errors']);matched=[];allocations=[];used=set();pids=set()
    if not core.get('coverage_qualified'):errors['unqualified_user_core']+=1
    start,end=bounds
    if start is None or end is None:errors['missing_full_script_window']+=1;selected=[]
    else:selected=[r for r in core['rows'] if start<=r['made_us']<end]
    if not selected:errors['empty_full_script']+=1
    for r in selected:
        tid,q,handle,offset,words,fence=r['io_identity']
        if not 210000000000<=r['io_begin_ns']<=r['io_end_ns']<=270000000000:
            errors['full_script_IO_outside_kernel_window']+=1
        matches=[k for k in decoded['rows'] if k['selector']==70 and k['tid']==tid and k['queue']==q and
            k['fence']==fence and k['handle']==handle and k['bytes']==words*4 and k['bos']==r['bo_unique'] and
            k['cmds']==1 and k['result']==0 and inside(k,r['io_begin_ns'],r['io_end_ns'])]
        if len(matches)!=1:errors['missing_or_ambiguous_submit_identity']+=1;continue
        k=matches[0]
        if k['token'] in used:errors['kernel_submit_reused']+=1;continue
        used.add(k['token']);pids.add(k['pid'])
        lo=sum(p['CPU_lower_ns'] for p in k['phases']);hi=sum(p['CPU_upper_ns'] for p in k['phases'])
        if lo>r['cpu_ns'][6]:errors['kernel_CPU_exceeds_user_call_upper_bound']+=1
        matched.append(dict(queue=r['queue'],ticket=r['ticket'],job=r['job'],kernel_token=k['token'],
            kernel_selector=k['selector'],caller_pid=k['pid'],caller_thread=tid,driver_queue=q,driver_fence=fence,
            IO_wall_ns=r['io_ns'],kernel_wall_ns=k['last_ns']-k['first_ns'],kernel_query_ns=k['query_ns'],
            phases=k['phases'],unlocked_wait_ns=k['wait_ns'],unlocked_waits=k['waits'],
            CPU_outside_measured_phases_lower_ns=max(0,r['cpu_ns'][5]-hi),
            CPU_outside_measured_phases_upper_ns=max(0,r['cpu_ns'][6]-lo),
            IO_elapsed_outside_callback_ns=max(0,r['io_ns']-(k['last_ns']-k['first_ns']))))
        if not r['newbo_counts'][0]:continue
        job,thread,bo,size,first,last,mask,n,query,flags=r['newbo_max']
        if not 210000000000<=first<=last<=270000000000:errors['program_max_outside_kernel_window']+=1;continue
        children=[]
        for index,selector in ((1,66),(2,67),(3,256)):
            candidates=[x for x in decoded['rows'] if x['selector']==selector and x['tid']==thread and x['handle']==bo
                and x['result']==0 and (selector==67 or x['bytes']==size) and
                inside(x,r['newbo_begin'][index],r['newbo_end'][index])]
            if len(candidates)!=1:errors['missing_or_ambiguous_program_BO_identity']+=1;continue
            x=candidates[0];pids.add(x['pid'])
            if x['token'] in used:errors['kernel_program_callback_reused']+=1;continue
            used.add(x['token'])
            user_phase=CPU_bounds(r['newbo_end'][index]-r['newbo_begin'][index],r['newbo_max_cpu'][index],r['newbo_max_envelope'][index])
            if sum(p['CPU_lower_ns'] for p in x['phases'])>user_phase['CPU_upper_ns']:
                errors['kernel_program_CPU_exceeds_user_phase_upper_bound']+=1

            children.append(dict(selector=selector,kernel_token=x['token'],phases=x['phases'],
                user_phase_wall_ns=r['newbo_end'][index]-r['newbo_begin'][index],
                kernel_callback_wall_ns=x['last_ns']-x['first_ns'],nested_unlocked_wait_ns=x['wait_ns'],
                callback_excludes_IPC_and_VM_mapping=True))
        if len(children)==3:allocations.append(dict(queue=r['queue'],ticket=r['ticket'],job=job,thread=thread,
            handle=bo,bytes=size,first_ns=first,last_ns=last,children=children,maximum_only=True))
    if len(pids)!=1:errors['caller_process_identity_not_unique']+=1
    expected=sum(bool(r['newbo_counts'][0]) for r in selected)
    if require_program_activity and not expected and not any(r.get('program_slab_reuses',0) for r in selected):
        errors['program_new_BO_or_slab_reuse_not_observed_in_full_script']+=1
    if len(matched)!=len(selected) or len(allocations)!=expected:errors['full_script_join_coverage']+=1
    return dict(state='IO342-user-kernel-identity-joined' if not errors else 'IO342-identity-join-unqualified',
        coverage_qualified=not errors,errors=dict(errors),full_script_bounds_us=bounds,complete_submit_count=len(matched),
        program_maximum_join_count=len(allocations),caller_pids=sorted(pids),submits=matched,program_maxima=allocations,
        scope='Calling-thread CPU bounds include measured query envelopes and 2us clock slop. Unlocked waits are nested elapsed intervals, not extra time. Driver callbacks exclude IPC and IOKit VM work outside each callback. Program maxima are partial evidence. No proportional CPU placement, lock-wait classification or pure GPU-time claim.',
        device_commands=0,physical_FPS_qualified=False)


def summarize(joined,core):
    if not joined['coverage_qualified'] or not core['coverage_qualified']:
        return dict(state='IO342-backlog-interpretation-withheld',physical_FPS_qualified=False)
    pairs={(r['queue'],r['ticket']):r for r in joined['submits']}
    rows=[r for r in core['rows'] if (r['queue'],r['ticket']) in pairs]
    def sums(items):
        values=[pairs[r['queue'],r['ticket']] for r in items]
        return {name:{field:sum(v['phases'][i][field] for v in values) for field in
            ('wall_ns','CPU_lower_ns','CPU_upper_ns','off_CPU_lower_ns','off_CPU_upper_ns')}
            for i,name in enumerate(PHASES[70])}
    windows=[]
    for queue in sorted({r['queue'] for r in rows}):
        ordered=sorted((r for r in rows if r['queue']==queue),key=lambda r:r['ticket'])
        for i in range(len(ordered)-11):
            group=ordered[i:i+12];first=group[0];last=group[-1]
            if last['ticket']-first['ticket']!=11 or last['core_queue_wait_us']-first['core_queue_wait_us']<16666.667:continue
            windows.append(dict(queue=queue,first_ticket=first['ticket'],last_ticket=last['ticket'],
                queue_wait_growth_us=last['core_queue_wait_us']-first['core_queue_wait_us'],
                mean_arrival_interval_us=(last['enq_ns']-first['enq_ns'])/11000,
                mean_commit_start_interval_us=(last['start_ns']-first['start_ns'])/11000,
                program_new_BO_calls=sum(r['newbo_counts'][0] for r in group),
                IO_wall_sum_ns=sum(r['io_ns'] for r in group),phase_sums=sums(group),
                overlapping_scopes_not_utilization=True))
    predecessor=[]
    for row in sorted(rows,key=lambda r:r['core_queue_wait_us'],reverse=True)[:20]:
        parts=[]
        for old in rows:
            if old['queue']!=row['queue'] or old['job']>=row['job']:continue
            for i,p in enumerate(pairs[old['queue'],old['ticket']]['phases']):
                overlap=max(0,min(row['start_ns'],p['end_ns'])-max(row['enq_ns'],p['begin_ns']))
                if not overlap:continue
                outside=p['wall_ns']-overlap
                parts.append(dict(predecessor_ticket=old['ticket'],predecessor_job=old['job'],phase=PHASES[70][i],
                    overlap_ns=overlap,CPU_lower_ns=max(0,p['CPU_lower_ns']-outside),
                    CPU_upper_ns=min(overlap,p['CPU_upper_ns']),
                    off_CPU_lower_ns=max(0,p['off_CPU_lower_ns']-outside),
                    off_CPU_upper_ns=min(overlap,p['off_CPU_upper_ns'])))
        predecessor.append(dict(queue=row['queue'],ticket=row['ticket'],wait_us=row['core_queue_wait_us'],
            prior_commit_phase_intersections=parts,render_jobs_and_query_gaps_not_extrapolated=True))
    return dict(state='IO342-identity-qualified-backlog-CPU-stages-observed',phase_sums=sums(rows),
        submit_count=len(rows),sustained_windows=sorted(windows,key=lambda r:r['queue_wait_growth_us'],reverse=True)[:20],
        longest_wait_predecessor_phases=predecessor,
        longest_submit_calls=sorted(joined['submits'],key=lambda r:r['IO_wall_ns'],reverse=True)[:20],
        program_maxima=joined['program_maxima'],CPU_utilization_claim=False,physical_FPS_qualified=False,
        scope=joined['scope'],device_commands=0)
