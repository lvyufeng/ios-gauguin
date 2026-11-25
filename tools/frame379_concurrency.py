"""Join bounded row segments to the observed native fence lifecycle."""

from base64 import b64decode, b64encode
from collections import Counter, defaultdict
import re

import frame344_log as frame
from frame353_display import TAKE
from frame378_memory import stats

LABELS = {1:'control',2:'stroke_2_release',3:'stroke_4_release'}
LIMITS = {1:12,2:26,3:26}
PROBE_TICKS = {2:(157_056_000,166_656_000),3:(246_720_000,256_320_000)}
HOLD_TICKS = {2:(159_744_000,163_392_000),3:(249_888_000,253_728_000)}
SEGMENTS = 8
ROWS_PER_SEGMENT = 300
PACKED_BYTES = 99
BLOCK = 8
MAX_HOLDS = 12
AGE_TICKS = 1_536_000
MASK32 = 0xffffffff


def lane_in(offset, bounds):
    return next((lane for lane,(lo,hi) in bounds.items() if lo<=offset<hi),0)


def wire_rows(raw):
    total,lost,*counts = map(int,frame.one(
        r'^SWEET F379 F: rows=(\d+) lost=(\d+) control=(\d+) stroke2=(\d+) stroke4=(\d+)$',raw,'segment footer'))
    selected = dict(zip(LABELS,counts,strict=True))
    frame.require(total+lost==sum(counts) and all(selected[k]<=LIMITS[k] for k in LABELS),'segment counts differ')
    decoded = []
    for head in re.finditer(r'^SWEET F379 S (\d+) (\d+) ([A-Za-z0-9+/]+={0,2})$',raw,re.M):
        ordinal,count,encoded = int(head[1]),int(head[2]),head[3]
        frame.require(ordinal==len(decoded) and 0<count<=BLOCK and ordinal+count<=total and
                      (count==BLOCK or ordinal+count==total),'segment block order differs')
        block = b64decode(encoded,validate=True)
        frame.require(len(block)==count*PACKED_BYTES and b64encode(block).decode()==encoded,'segment row size differs')
        for offset in range(0,len(block),PACKED_BYTES):
            row = block[offset:offset+PACKED_BYTES]
            attempt,lane = int.from_bytes(row[:2],'little'),row[2]
            frame.require(attempt and lane in LABELS,'invalid segment identity')
            samples = [int.from_bytes(row[pos:pos+3],'little') for pos in range(3,PACKED_BYTES,3)]
            decoded.append(dict(attempt=attempt,lane=lane,points=list(zip(
                samples[::4],samples[1::4],samples[2::4],samples[3::4],strict=True))))
    actual = Counter(row['lane'] for row in decoded)
    frame.require(len(decoded)==total and all(actual[k]<=selected[k] for k in LABELS) and
                  len({row['attempt'] for row in decoded})==total,'duplicate or missing segment attempts')
    return decoded,selected,lost


def gpu_intervals(rows, capture_end):
    ends = frame.indexed(rows[frame.EOP],lambda event:event.id,'observed EOP')
    visible = frame.indexed(rows[frame.READY],lambda event:event.id,'surface visibility')
    writes = defaultdict(set)
    for event in rows[frame.WRITER]:
        writes[event.id].add(event.a)
    issued = frame.indexed(rows[frame.ISSUE],lambda event:event.id,'issued fence')
    windows = []
    for fence,event in issued.items():
        eop,ready = ends.get(fence),visible.get(fence)
        frame.require(event.tick<=(eop.tick if eop else capture_end) and
                      (not ready or eop and eop.tick<=ready.tick),'native GPU lifecycle order differs')
        windows.append(dict(fence=fence,issued=event.tick,eop=eop.tick if eop else None,
            window_end=eop.tick if eop else capture_end,ready=ready.tick if ready else None,
            driver_queue=event.b,driver_fence=event.c,kernel_token=event.a,writer_surfaces=sorted(writes[fence])))
    return sorted(windows,key=lambda row:row['issued'])


def overlaps(windows, start, end):
    intersections = []
    for window in windows:
        if window['issued']>=end:
            break
        first,last = max(start,window['issued']),min(end,window['window_end'])
        if first<last:
            intersections.append(dict(fence=window['fence'],ticks=last-first,covers=first==start and last==end,
                writer_surfaces=window['writer_surfaces'],observed_EOP=window['eop']))
    return intersections


def join_deferrals(raw, start, rows, windows):
    count=int(frame.one(r'^SWEET F379 D footer: rows=(\d+)$',raw,'deferral footer'))
    records = re.findall(r'^SWEET F379 D: scan=(\d+) gen=(\d+) fence=(\d+) tick=(\d+) issue=(\d+) lane=(\d+)$',raw,re.M)
    frame.require(len(records)==count<=2*MAX_HOLDS,'held scan count differs')
    by_fence = {item['fence']:item for item in windows}
    by_gen = defaultdict(list)
    for event in rows[TAKE]:
        by_gen[event.a].append(event)
    accepted = frame.indexed(rows[frame.SWAP],lambda event:event.id,'swap generation')
    result = []
    generations,scans,counts = set(),set(),Counter()
    for rec in records:
        scan,generation,fence,tick,published,lane = map(int,rec)
        gpu = by_fence.get(fence)
        swap = accepted.get(generation)
        frame.require(lane and lane==lane_in(tick-start,HOLD_TICKS) and gpu and swap and not swap.flags and
            swap.tick<=tick and gpu['issued']<=published<=tick and tick-published<=AGE_TICKS and
            generation not in generations and scan not in scans,'deferral lacks its scope, fence, or ready generation')
        selected = next((row for row in by_gen[generation] if row.tick>=tick),None)
        steps = ((selected.c-scan)&MASK32) if selected else None
        result.append(dict(scan=scan,generation=generation,fence=fence,tick=tick,observed_issue_tick=gpu['issued'],
            publication_tick=published,eop_tick=gpu['eop'],matched_before_observed_EOP=gpu['eop'] is None or tick<=gpu['eop'],
            case=LABELS[lane],resume_attempt=selected.id if selected else None,scans_until_same_generation_taken=steps))
        generations.add(generation)
        scans.add(scan)
        counts[lane]+=1
    frame.require(all(value<=MAX_HOLDS for value in counts.values()),'deferral window exceeded cap')
    return result


def retest(copies, start, n, d, strokes, windows, probe_ids=(), bad=(), holds=()):
    scale = n/d
    outcomes = {}
    for lane,(lo,hi) in PROBE_TICKS.items():
        stroke = 2 if lane==2 else 4
        down,up = strokes[stroke-1]
        frame.require(up<start+lo<start+hi and (start+hi-down)*scale<1_600_000_000,
                      'retest window is outside its actual release')
        lane_copies=[row for row in copies if start+lo<=row['begin_tick']<start+hi]
        peak=max(lane_copies,key=lambda row:row['total_ns'],default=None)
        where=LABELS[lane]
        outcomes[where]=dict(stroke=stroke,after_release_ms=[(start+t-up)*scale/1e6 for t in (lo,hi)],
            copy_wall_ns=stats([row['total_ns'] for row in lane_copies]),
            sampled=sum(row['attempt'] in probe_ids for row in lane_copies),
            peak_attempt=peak['attempt'] if peak else None,
            peak_sampled=bool(peak and peak['attempt'] in probe_ids),peak_pending_fences=overlaps(
                windows,peak['begin_tick'],peak['end_tick']) if peak else [],
            crossed=[row for row in bad if any(row['attempt']==copy['attempt'] for copy in lane_copies)],
            deferred=sum(row['case']==where for row in holds))
    return outcomes


def copy_overlap(copies, windows, bad):
    groups=defaultdict(list)
    crossing=[]
    selected=frame.indexed(bad,lambda row:row['attempt'],'unchecked boundary')
    for copy in copies:
        own=copy['surface']
        active=overlaps(windows,copy['begin_tick'],copy['end_tick'])
        category='other_surface' if any(s!=own for f in active for s in f['writer_surfaces']) else (
            'observed_pending' if active else 'no_observed_pending')
        groups[category].append(copy['total_ns'])
        if copy['attempt'] in selected:
            crossing.append(dict(attempt=copy['attempt'],copy_surface=own,pending_fences=active,
                copy_ns=copy['total_ns']))
    return dict(wall_ns={key:stats(values) for key,values in sorted(groups.items())},
                crossings=crossing)


def analyze(raw, rows, timing, start, end, n, d, strokes, bad):
    wire,selected,lost = wire_rows(raw)
    copies=frame.indexed(timing['rows'],lambda row:row['attempt'],'phase copy')
    windows=gpu_intervals(rows,end)
    scale=n/d
    segments,groups=[],defaultdict(list)
    for item in wire:
        copy=copies.get(item['attempt'])
        lane=item['lane']
        frame.require(copy and (lane_in(copy['begin_tick']-start,PROBE_TICKS) or
            (1 if item['attempt']%71==0 else 0))==lane,'probe does not match its copy and lane')
        absolute=copy['begin_tick']
        prior=0
        for i,(stop,row,load,issue) in enumerate(item['points']):
            frame.require(stop>prior and 0<row<=stop-prior and load+issue<=row and
                          absolute+stop<=copy['stores_tick'],'segment or row brackets differ from full copy')
            sample=overlaps(windows,absolute+prior,absolute+prior+row)
            cache=any(w['eop'] is not None and w['ready'] is not None and
                      max(absolute+prior,w['eop'])<min(absolute+prior+row,w['ready']) for w in windows)
            phase='covers_row' if any(f['covers'] for f in sample) else 'intersects_row' if sample else 'no_observed_pending'
            measured=dict(attempt=item['attempt'],case=LABELS[lane],row=i*ROWS_PER_SEGMENT,
                segment_ticks=[absolute+prior,absolute+stop],sample_row_end_tick=absolute+prior+row,
                segment_wall_ns=(stop-prior)*scale,source_completion_ns=load*scale,store_issue_ns=issue*scale,
                source_surface=copy['surface'],gpu_observation=phase,pending_fences=sample,
                cache_publication_overlap=cache)
            groups[phase].append(measured)
            segments.append(measured)
            prior=stop
    holds=join_deferrals(raw,start,rows,windows)
    probe_ids={item['attempt'] for item in wire}
    return dict(qualified=bool(wire) and lost==0 and all(selected.values()),records=len(wire),lost=lost,
        selected=selected,segment_count=len(segments),segments=segments,deferrals=holds,
        deferral_summary=dict(count=len(holds),same_scan=sum(row['scans_until_same_generation_taken']==0 for row in holds),
            next_scan=sum(row['scans_until_same_generation_taken']==1 for row in holds),
            not_reused_within_one_scan=sum(row['scans_until_same_generation_taken'] not in (0,1) for row in holds)),
        retest=retest(copies.values(),start,n,d,strokes,windows,probe_ids,bad,holds),
        copy_overlap=copy_overlap(copies.values(),windows,bad),
        row_sample_stats={phase:{k:stats([row[k] for row in values])
                          for k in ('source_completion_ns','store_issue_ns','segment_wall_ns')}
                          for phase,values in sorted(groups.items())},
        gpu_issue_records=len(windows),issues_without_eop=sum(w['eop'] is None for w in windows),
        observation='Issue-to-observed-EOP is a software fence envelope. It does not measure GPU utilization or '
                    'show when the engine completed. Each source sample is bracketed by one row. '
                    'The complete segment retains the original interleaved copy.')
