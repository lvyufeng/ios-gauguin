#!/usr/bin/env python3
"""Decode bounded CPU allocation phases; no device I/O or hardware FPS claim."""
from pathlib import Path
import argparse,importlib.util,json,math,statistics

def analyze(text,ui):
    capture=ui.parse(text);h=capture['header'];events=capture['events']
    by_id={};begins={};ends={}
    for e in events:
        if e['kind']==10 and e['flags']==0x42:
            if e['id'] in begins:raise ValueError('duplicate allocation API begin')
            begins[e['id']]=e
        elif e['kind']==11 and e['b']==0x42:
            if e['id'] in ends:raise ValueError('duplicate allocation API end')
            ends[e['id']]=e
        elif e['kind']==32:
            if not e['id'] or not e['pid'] or not 1<=e['flags']<=6:
                raise ValueError('invalid allocation metadata')
            by_id.setdefault(e['id'],[]).append(e)
    if not capture['clock_valid']:raise ValueError('invalid allocation clock')
    us=lambda ticks:ticks*h['numer']/h['denom']/1000
    rows=[];partial=[]
    for token,records in by_id.items():
        phases=[e['flags'] for e in records]
        if phases!=sorted(set(phases)) or len({e['pid'] for e in records})!=1:
            raise ValueError('duplicate, reversed or cross-process allocation phases')
        if phases[0]!=1 or phases[-1]!=6 or token not in begins or token not in ends:
            if token in begins and token in ends and not h['lost']:
                raise ValueError('complete API envelope lacks allocation endpoint')
            partial.append(dict(token=token,phases=phases,reason='capture endpoint absent'));continue
        a,z=begins[token],ends[token];p={e['flags']:e for e in records}
        if a['pid']!=z['pid'] or a['pid']!=p[1]['pid'] or not a['seq']<p[1]['seq']<p[6]['seq']<z['seq']:
            raise ValueError('allocation API envelope mismatch')
        if not 0<a['a']<=a['b']<=a['tick']<=p[1]['tick']<=p[6]['tick']<=z['a']<=z['tick']:
            raise ValueError('invalid allocation API timestamps')
        if p[6]['a']!=z['flags'] or p[6]['c']>9 or not p[1]['c']:
            raise ValueError('allocation result/stage/thread mismatch')
        success=p[6]['a']==0
        if phases not in ([1,6],[1,2,3,6],[1,2,3,4,6],[1,2,3,4,5,6]):
            if h['lost']:
                partial.append(dict(token=token,phases=phases,reason='lost intermediate phase'));continue
            raise ValueError('missing allocation phase without recorded loss')
        if success and phases!=[1,2,3,4,5,6]:
            if h['lost']:
                partial.append(dict(token=token,phases=phases,reason='lost successful allocation phase'));continue
            raise ValueError('successful allocation lacks required phase')
        if 2 in p and (not 0<p[1]['a']<=64*1024*1024 or p[2]['a']!=((p[1]['a']+16383)&~16383)):
            raise ValueError('allocation page rounding mismatch')
        if 3 in p and p[3]['a'] not in (0,1):raise ValueError('invalid descriptor presence')
        if 4 in p and p[3]['a']!=1:raise ValueError('zeroing without descriptor')
        if 5 in p and (p[5]['a']!=p[2]['a'] or not p[5]['b'] or p[5]['c']!=p[1]['b']):
            raise ValueError('published allocation mapping mismatch')
        if success and (p[6]['b']!=p[5]['b'] or p[6]['c']!=0):
            raise ValueError('successful allocation handle/stage mismatch')
        for phase in (2,3,4):
            if phase in p and (p[phase]['b'] or p[phase]['c'] or (phase==4 and p[phase]['a'])):
                raise ValueError('reserved allocation fields')
        stages={'request_queue':us(a['b']-a['a']),'phase_total':us(p[6]['tick']-p[1]['tick'])}
        for lo,hi,name in [(1,2,'dispatch_gate'),(2,3,'backing_allocation'),(3,4,'zeroing'),(4,5,'mapping_preparation'),(5,6,'synchronization_and_return')]:
            if lo in p and hi in p:stages[name]=us(p[hi]['tick']-p[lo]['tick'])
        rows.append(dict(token=token,pid=p[1]['pid'],thread_id=p[1]['c'],requested_bytes=p[1]['a'],flags=p[1]['b'],result=p[6]['a'],allocation_stage=p[6]['c'],handle=p[6]['b'],phases=phases,start_us=us(p[1]['tick']),end_us=us(p[6]['tick']),durations_us=stages))
    def stats(values):
        v=sorted(values)
        return dict(count=len(v),median_us=statistics.median(v) if v else None,p95_us=v[math.ceil(.95*len(v))-1] if v else None,max_us=max(v) if v else None)
    good=[r for r in rows if r['result']==0]
    qualified=bool(good) and not h['lost'] and not capture['truncated_by_capacity']
    missing_api_tokens=sorted((set(begins)&set(ends))-set(by_id))
    if missing_api_tokens:qualified=False
    return dict(state='BO333-allocation-phases-observed' if qualified else 'BO333-allocation-phases-incomplete',coverage_qualified=qualified,metadata_events=sum(len(r) for r in by_id.values()),complete_count=len(rows),successful_count=len(good),failed_count=len(rows)-len(good),partial_count=len(partial),partial=partial,missing_metadata_tokens=missing_api_tokens,trace_lost=h['lost'],capacity_truncated=capture['truncated_by_capacity'],thread_ids=sorted({r['thread_id'] for r in rows}),success_stages_us={key:stats([r['durations_us'][key] for r in good]) for key in (good[0]['durations_us'] if good else [])},rows=rows,device_commands=0,physical_FPS_qualified=False,scope='CPU elapsed phase intervals include instrumentation and scheduling. Synchronization includes the existing SMMU path and return; no GPU-only time or allocation-to-frame causality is inferred.')

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('log',type=Path);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    ui_path=Path(__file__).resolve().parent/'ui_trace_log.py'
    spec=importlib.util.spec_from_file_location('bo333_ui',ui_path);ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
    assert ui.KINDS[32]=='bo-allocation333'
    out=analyze(a.log.read_text(errors='replace'),ui);raw=json.dumps(out,indent=2)+'\n';assert len(raw.encode())<=4*1024*1024
    with a.out.open('x') as f:f.write(raw)
    print(json.dumps({k:v for k,v in out.items() if k not in ('rows','partial','missing_metadata_tokens')},indent=2))
if __name__=='__main__':main()
