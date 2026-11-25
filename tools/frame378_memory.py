"""Verify and summarize the sparse source-load, store-issue and drain samples."""

from base64 import b64decode, b64encode
from collections import Counter
import re

from frame344_log import indexed, one, quantile, require

ROWS = 8
BLOCK_SIZE = 8
PACKED_ROW_BYTES = 55
FOOTER = r'^SWEET F378 F: rows=(\d+) lost=(\d+) control=(\d+) stroke2=(\d+) stroke6=(\d+)$'
CASES = {1:'control',2:'stroke_2_release',3:'stroke_6_release'}
LIMITS = {1:16,2:32,3:32}
WINDOWS = {2:(157_056_000,166_656_000),3:(336_960_000,346_752_000)}
ROW_NUMBERS = [128+288*row for row in range(ROWS)]


def lane_for(attempt, offset):
    for lane,(start,end) in WINDOWS.items():
        if start<=offset<end:
            return lane
    return 1 if offset>=0 and attempt%71==0 else 0


def wire_rows(raw):
    total,lost,control,second,sixth = map(int,one(FOOTER,raw,'bounded memory probe footer'))
    selected = dict(zip(CASES,(control,second,sixth),strict=True))
    require(total+lost==sum(selected.values()) and
        all(selected[key]<=LIMITS[key] for key in CASES),'memory probe selection accounting differs')
    rows = []
    for block in re.finditer(r'^SWEET F378 P (\d+) (\d+) ([A-Za-z0-9+/]+={0,2})$',raw,re.M):
        ordinal,count,encoded = int(block[1]),int(block[2]),block[3]
        require(ordinal==len(rows) and 0<count<=BLOCK_SIZE and ordinal+count<=total and
                (count==BLOCK_SIZE or ordinal+count==total),'memory probe block order differs')
        data = b64decode(encoded,validate=True)
        require(len(data)==count*PACKED_ROW_BYTES and b64encode(data).decode()==encoded,
                'memory probe block length or padding differs')
        for i in range(count):
            record = data[i*PACKED_ROW_BYTES:(i+1)*PACKED_ROW_BYTES]
            attempt = int.from_bytes(record[:2],'little')
            lane,drain_index = record[2:4]
            require(attempt>0 and lane in CASES and drain_index==attempt%ROWS,'memory probe row header differs')
            phases = [int.from_bytes(record[j:j+3],'little') for j in range(4,PACKED_ROW_BYTES,3)]
            rows.append(dict(attempt=attempt,lane=lane,drain_index=drain_index,read_ticks=phases[:-1:2],
                issue_ticks=phases[1:-1:2],drain_ticks=phases[-1]))
    counts = Counter(row['lane'] for row in rows)
    require(len(rows)==total and all(counts[k]<=selected[k] for k in CASES) and
        len({row['attempt'] for row in rows})==total,'memory probe totals or attempt uniqueness differ')
    return rows,selected,lost


def stats(values):
    return dict(samples=len(values),p50=quantile(values,.50),p95=quantile(values,.95),max=max(values,default=None))


def analyze(raw, timings, start, n, d, strokes):
    reserved,selected,lost = wire_rows(raw)
    require((n,d)==(625,12) and len(strokes)==13,'memory probe script or timebase differs')
    duration = lambda ticks: ticks*n/d
    whole = indexed(timings['rows'],lambda row:row['attempt'],'full phase timing')
    rows = []
    for sample in reserved:
        attempt,lane = sample['attempt'],sample['lane']
        copy = whole.get(attempt)
        require(copy and lane_for(attempt,copy['begin_tick']-start)==lane,
                'memory probe lane differs from the full copy start')
        read = [duration(t) for t in sample['read_ticks']]
        issue = [duration(t) for t in sample['issue_ticks']]
        drain = duration(sample['drain_ticks'])
        require(0<sum(read)+sum(issue)+drain<=copy['read_write_body_ns'],
                'sparse phases lie outside their full copy')
        rows.append(dict(attempt=attempt,case=CASES[lane],lane=lane,read_ns=read,store_issue_ns=issue,
            store_drain_ns=drain,store_drain_row=ROW_NUMBERS[sample['drain_index']],
            full_copy_wall_ns=copy['total_ns'],full_body_ns=copy['read_write_body_ns'],
            begin_tick=copy['begin_tick']))

    scenes = {}
    for lane in (2,3):
        stroke = 2 if lane==2 else 6
        begins,released = strokes[stroke-1]
        low,high = (start+value for value in WINDOWS[lane])
        require(released<low<high and duration(high-begins)<1_600_000_000,
                'target window is not inside the observed stroke release scenario')
        copies = [entry for entry in whole.values() if low<=entry['begin_tick']<high]
        picked = [row for row in rows if row['lane']==lane]
        scenes[CASES[lane]] = dict(stroke=stroke,relative_to_onset_ms=[duration(t-begins)/1e6 for t in (low,high)],
            relative_to_release_ms=[duration(t-released)/1e6 for t in (low,high)],matched_copies=len(copies),
            sampled_copies=len(picked),copy_wall_ns=stats([entry['total_ns'] for entry in copies]),
            peak_copy_attempt=max(copies,key=lambda entry:entry['total_ns'])['attempt'] if copies else None,
            peak_copy_sampled=bool(copies and max(copies,key=lambda entry:entry['total_ns'])['attempt']
                                   in {row['attempt'] for row in picked}))

    summary = {}
    for lane,name in CASES.items():
        values = [row for row in rows if row['lane']==lane]
        summary[name] = dict(copy_attempts=len(values),
            source_load_ns=stats([ns for row in values for ns in row['read_ns']]),
            store_issue_ns=stats([ns for row in values for ns in row['store_issue_ns']]),
            store_drain_ns=stats([row['store_drain_ns'] for row in values]))
    probe_set = {row['attempt'] for row in rows}
    comparison = dict(probed=stats([row['total_ns'] for row in whole.values() if row['attempt'] in probe_set]),
                      ordinary=stats([row['total_ns'] for row in whole.values() if row['attempt'] not in probe_set]))
    return dict(selected=selected,records=len(rows),lost=lost,rows=rows,row_numbers=ROW_NUMBERS,
        qualified=not lost and all(summary[name]['copy_attempts'] for name in CASES.values()),scenes=scenes,
        envelopes=summary,copy_wall_observations=comparison,
        scope='Sparse 64-byte samples with counter ordering and intervening barriers. Store issue is observed before '
              'the optional completion barrier. The drained span includes stores queued earlier in the same copy. '
              'Phase envelopes include measurement overhead and are not an additive partition of the full body.')
