#!/usr/bin/env python3
"""Validate UI254 CPU-clock evidence. Never infer GPU time or panel fps."""
import argparse,json,re
from pathlib import Path

KINDS={1:'report',2:'hid-begin',3:'hid-end',4:'hid-return',5:'hid-enqueue',6:'hid-no-queue',
       10:'api-begin',11:'api-end',
       12:'submit-begin',13:'submit-end',14:'surface',20:'swap',21:'present-begin',
       22:'present-end',23:'layer',24:'read-lock',25:'read-end',30:'synthetic-input'}
FIELDS={'H':'version count reason lost start end numer denom which gestures'.split(),
        'E':'seq tick kind id pid flags a b c'.split(),'F':['count','lost']}

def parse(text):
    header=None;footer=None;events=[]
    for line in text.splitlines():
        i=line.find('SWEET UI254 ')
        if i<0:continue
        line=line[i:]
        m=re.fullmatch(r'SWEET UI254 ([HEF]): (.*)',line)
        if not m:continue # explicit armed/refused/allocation status, not records
        kind,body=m.groups()
        if kind=='F':
            suffix='; CPU-clock capture only'
            if not body.endswith(suffix):raise ValueError('footer scope missing')
            body=body[:-len(suffix)]
        words=body.split(' ')
        if len(words)!=len(FIELDS[kind]):raise ValueError('record field count')
        row={}
        for key,word in zip(FIELDS[kind],words):
            if not re.fullmatch(re.escape(key)+r'=[0-9]+',word):raise ValueError('record field '+key)
            value=int(word.split('=')[1])
            limit=(1<<32) if key in {'version','count','reason','numer','denom','which','gestures','kind','pid','flags'} else (1<<64)
            if value>=limit:raise ValueError('integer range '+key)
            row[key]=value
        if kind=='H':
            if header or events or footer:raise ValueError('multiple or late header')
            header=row
        elif kind=='E':
            if not header or footer:raise ValueError('event outside capture')
            if len(events)>=4096:raise ValueError('capture exceeds bound')
            events.append(row)
        else:
            if not header or footer:raise ValueError('multiple or early footer')
            footer=row
    if not header or not footer:raise ValueError('incomplete capture: header/footer absent')
    h=header
    if h['version']!=1 or h['reason'] not in range(1,5) or not 1<=h['which']<=16 or not h['numer'] or not h['denom']:
        raise ValueError('unsupported capture header')
    if h['count']!=len(events) or h['count']>4096 or footer!={'count':h['count'],'lost':h['lost']}:
        raise ValueError('capture prefix/count/loss mismatch')
    if h['reason']!=4 and h['gestures']!=h['which']:raise ValueError('gesture selection mismatch')
    clock_valid=h['reason']!=3
    if clock_valid and events and (not h['start'] or h['end']<=h['start']):raise ValueError('bad clock interval')
    for i,e in enumerate(events,1):
        if e['seq']!=i or e['kind'] not in KINDS:raise ValueError('missing/unknown record')
        if clock_valid and not h['start']<=e['tick']<h['end']:raise ValueError('event outside time window')
        if i>1 and e['tick']<events[i-2]['tick']:raise ValueError('CPU clock regressed')
        if e['kind']==1 and (e['id']!=i or (not e['flags'] and not 0<e['a']<=e['b']<=e['tick'])):
            raise ValueError('invalid report timing')
    reports={e['id']:e for e in events if e['kind']==1}
    generated=set()
    for e in events:
        if e['kind']!=30:continue
        origin=reports.get(e['id'])
        if not origin or origin['seq']>=e['seq'] or e['id'] in generated or e['flags']>=13 or e['a']>33 or e['b']>1079 or e['c']>2399:
            raise ValueError('invalid synthetic report marker')
        generated.add(e['id'])
    input_origin=('synthetic' if len(generated)==len(reports) else 'mixed') if generated else 'physical-driver-or-unmarked'
    # Match only explicit identities. Temporal proximity never proves a touch
    # caused a particular CA frame. Unpaired endpoints are retained as unknown.
    pairs={3:2,11:10,13:12,22:21,25:24};pending={};spans=[];unpaired=[]
    for e in events:
        k=e['kind'];key=(k,e['id'])
        if k in pairs.values():
            if key in pending:unpaired.append(pending[key])
            pending[key]=e
        elif k in pairs:
            begin=pending.pop((pairs[k],e['id']),None)
            if begin and clock_valid:
                spans.append({'kind':KINDS[pairs[k]],'id':e['id'],'begin_seq':begin['seq'],'end_seq':e['seq'],
                              'elapsed_ns':((e['tick']-begin['tick'])*h['numer'])//h['denom'],
                              'end_flags':e['flags']})
            else:unpaired.append(e)
    unpaired.extend(pending.values())
    beginnings={}
    for e in events:
        if e['kind']==2:
            beginnings.setdefault(e['a'],[]).append(e)
    queue_links=[]
    for e in events:
        if e['kind'] not in (5,6):continue
        matches=beginnings.get(e['id'],[])
        if len(matches)!=1:continue
        begin=matches[0]
        if begin['seq']>=e['seq'] or begin['tick']>e['tick']:continue
        queue_links.append({'report_id':begin['id'],'event_stamp':e['id'],
                            'queue_seq':e['seq'],'status':KINDS[e['kind']],
                            'enqueued':e['kind']==5 and bool(e['flags']),
                            'elapsed_ns':((e['tick']-begin['tick'])*h['numer'])//h['denom']})
    return {'scope':'CPU-clock kernel prefix; queue result is not SpringBoard receipt; no CA encode, GPU-only duration, panel latch or causal touch/frame proof',
            'header':h,'input_origin':input_origin,'physical_touch_qualified':False,
            'clock_valid':clock_valid,'contention_seen':bool(h['lost']),
            'truncated_by_capacity':h['reason']==2,'events':events,'spans':spans,
            'unpaired_endpoints':unpaired,'queue_links':queue_links}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('log',type=Path);ap.add_argument('--out',type=Path)
    a=ap.parse_args();result=parse(a.log.read_text(errors='replace'));data=json.dumps(result,indent=2)+'\n'
    if a.out:
        with a.out.open('x') as f:f.write(data)
    else:print(data,end='')
if __name__=='__main__':main()
