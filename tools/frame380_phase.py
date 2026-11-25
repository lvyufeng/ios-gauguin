"""Check hardware-phase witnesses and split input onset from moving cadence."""

from collections import Counter, defaultdict
import re
from statistics import median

from frame344_log import TIMING, VBLANK, indexed, one, quantile, require

LEAD = 76_800
MIN_SPACING = 230_400
MAX_AGE = 768_000
SAMPLE_STEP = 128
SAMPLE_CAP = 24
MASK = 0xffffffff


def phase(raw, rows, start, end, strokes, motion, n, d):
    require((n,d)==(625,12), '0380 absolute timebase differs')
    ready = tuple(map(int,one(r'^SWEET F380 READY: timer=(\d+) lead=(\d+) history=(\d+)$', raw, 'phase timer')))
    require(ready==(1,LEAD,20), '0380 timer or lead differs')
    requested = re.findall(r'^SWEET F388 DISPATCH: work_us=(\d+)$',raw,re.M)
    require(len(requested)<=1,'ambiguous compositor work duration')
    work_us = int(requested[0]) if requested else 0
    if requested:
        require(0<work_us<=32_000,'compositor work duration outside the admitted timer range')
        geometry, = rows[TIMING]
        end_line = int(one(r'^SWEET F351 WINDOW: available=1 frame=\d+ end=(\d+)$',raw,'DPU ready deadline'))
        tail = geometry.a-end_line+192
        require(geometry.a==4910 and 0<tail<geometry.a,'phase geometry differs')
        low,high = ((period*tail+geometry.a-1)//geometry.a for period in (312_000,328_320))
        work_ticks = work_us*1000*d//n
        lead_min,lead_max = work_ticks+low,work_ticks+high
    else:
        lead_min = lead_max = LEAD
    count,aligned,software,fallback,missed,first,last = map(int,one(
        r'^SWEET F380 F: rows=(\d+) aligned=(\d+) software=(\d+) fallback=(\d+) missed=(\d+) first=(\d+) last=(\d+)$',
        raw,'phase footer'))
    encoded = re.findall(r'^SWEET F380 P: seq=(\d+) scan=(\d+) source=(\d+) o=(\d+) w=(\d+) p=(\d+) a=(\d+)$',raw,re.M)
    expected = ([1,*range(SAMPLE_STEP,aligned+1,SAMPLE_STEP)] if aligned else [])[:SAMPLE_CAP]
    require(count==len(encoded)==len(expected) and 0<=fallback<=software and aligned+software+missed<=4096 and
            (start<=first<=last<end if aligned else first==last==0), 'phase aggregate or sample count differs')
    edges = indexed(rows[VBLANK],lambda row:row.id,'DPU scan')
    pulses = []
    prior_scan,prior_tick = None,None
    scale = n/d
    for expected_seq,record in zip(expected,encoded,strict=True):
        sequence,scan,source,observed,wake,predicted,actual = map(int,record)
        edge = edges.get(scan)
        src = edges.get(source)
        require(sequence==expected_seq and 1<=((scan-source)&MASK)<=4 and src and src.flags==1 and
                start+observed==src.b and 0<src.b-src.a<=57600 and observed<=wake<=actual<predicted and
                lead_min<=predicted-wake<=lead_max and actual-observed<=MAX_AGE and first<=start+actual<=last and
                (prior_scan is None or 0<((scan-prior_scan)&MASK)<(1<<31) and actual-prior_tick>=MIN_SPACING),
                'phase sample lacks its exact source, deadline or notification order')
        tick = start+actual
        qualified_edge = edge and edge.flags==1 and edge.a<edge.b
        lead = [(edge.a-tick)*scale,(edge.b-tick)*scale] if qualified_edge else None
        error = (max(abs(edge.a-start-predicted),abs(edge.b-start-predicted))*scale
                 if qualified_edge else None)
        pulses.append(dict(sequence=sequence,scan=scan,source=source,source_observed_tick=src.b,
                           wake_tick=start+wake,predicted_tick=start+predicted,notification_tick=tick,
                           wake_lateness_ns=(actual-wake)*scale,actual_lead_ns_bounds=lead,
                           absolute_prediction_error_upper_ns=error))
        prior_scan,prior_tick = scan,actual
    covers = bool(aligned and first<=strokes[0][0] and last>=motion['end_tick'])
    checked = [p for p in pulses if p['actual_lead_ns_bounds'] is not None]
    early = sum(p['actual_lead_ns_bounds'][0]>0 for p in checked)
    return dict(qualified=bool(covers and count>=20 and early==count and aligned>=2500),
        aligned=aligned,software_before_first=software-fallback,software_after_first=fallback,
        missed=missed,first_tick=first,last_tick=last,covers_13_and_drag=covers,
        sampled=count,matched_edges=len(checked),certainly_early=early,
        sampled_lead_lower_min_ns=min((p['actual_lead_ns_bounds'][0] for p in checked),default=None),
        sampled_prediction_error_p95_upper_ns=quantile([p['absolute_prediction_error_upper_ns'] for p in checked],.95),
        sampled_wake_lateness_p95_ns=quantile([p['wake_lateness_ns'] for p in pulses],.95),pulses=pulses,
        **({'work_duration_us':work_us} if work_us else {}))


def onset(scans, frame):
    lanes = defaultdict(list)
    for scan in scans:
        if scan['workload']=='ordinary' and scan['phase']=='active':
            lanes[scan['stroke']].append(scan)
    windows = {w['stroke']+1:w for w in frame['hardware']['windows'] if w['window']=='active'}
    require(sorted(lanes)==sorted(windows)==list(range(1,14)), 'onset requires the original 13 swipes')
    n,d = frame['tick_numer'],frame['tick_denom']
    ns = lambda tick:tick*n//d
    results = []
    for stroke,lane in sorted(lanes.items()):
        w = windows[stroke]
        require([s['frame'] for s in lane]==[s['frame'] for s in w['outputs']], 'onset scan sequence differs')
        changed = [i for i,s in enumerate(lane) if s['crc']=='changed']
        before = Counter(s['crc'] for s in lane[:changed[0] if changed else len(lane)])
        first,last = (lane[changed[0]],lane[changed[-1]]) if changed else (None,None)
        response = gap = None
        between = Counter()
        if first:
            require(first['vblank_ticks'] and last['vblank_ticks'], 'onset lacks bracketed vblank')
            left,right = map(ns,first['vblank_ticks'])
            response = [left-ns(w['start_tick']),right-ns(w['start_tick'])]
            between.update(s['crc'] for s in lane[changed[0]:changed[-1]+1])
            if len(changed)>1:
                a,b = map(ns,last['vblank_ticks'])
                require(a>right, 'onset and final edge overlap')
                gap = [a-right,b-left]
        results.append(dict(stroke=stroke,first_new_scan=first['frame'] if first else None,
            first_new_image_ns=response,pre_onset_counts=dict(before),
            first_through_last_counts=dict(between),motion_span_ns=gap))

    def summarize(lane):
        responses = [row['first_new_image_ns'] for row in lane if row['first_new_image_ns'] and
                     not row['pre_onset_counts'].get('unknown',0)]
        moving = [row for row in lane if row['motion_span_ns']]
        counts = Counter()
        for row in moving:
            counts.update(row['first_through_last_counts'])
        elapsed = [sum(row['motion_span_ns'][k] for row in moving) for k in (0,1)]
        rate = [(counts['changed']-len(moving))*1e9/elapsed[1],
                (counts['changed']-len(moving)+counts['unknown'])*1e9/elapsed[0]] if moving else None
        return dict(swipes=len(lane),bounded_onset=len(responses),
            median_first_new_image_ns=[median(bounds) for bounds in zip(*responses)] if responses else None,
            p95_first_new_image_ns=[quantile(bounds,.95) for bounds in zip(*responses)] if responses else None,
            moving_swipes=len(moving),moving_scan_counts=dict(counts),moving_new_images_per_second_bounds=rate)

    return dict(strokes=results,ordinary=summarize(results),warm=summarize(results[2:]),
                scope='Onset from first injected report. Motion spans the first through last certified CRC change.')
