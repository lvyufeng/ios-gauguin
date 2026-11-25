"""Score driver cadence, scanout and producer deadlines from restored captures."""

from bisect import bisect_right
from collections import Counter
from itertools import pairwise
import re

import frame344_log as trace
import frame345_log as scanout
import frame349_log as crc
from frame351_display import PRESENT
import frame352_display as copy
from frame354_display import TAKE
from frame357_replay import scan_windows
from frame358_display import KINDS
from frame359_frontend import RATE
from frame362_scope import MOTION, load, pacing, require

MS = 1_000_000
SAMPLE = re.compile(r'^SWEET M362: sample=(\d+) tick=(\d+) returned=(\d+) x=(\d+) down=([01])$', re.M)


def parse_motion(raw, strokes, numer, denom, calibration):
    due, limit, count = map(int,trace.one(
        r'^SWEET M362: armed due=(\d+) limit=(\d+) reports=(\d+)$',raw,'motion arm'))
    complete = int(trace.one(r'^SWEET M362: complete reports=(\d+)$',raw,'motion completion'))
    samples = [tuple(map(int,m.groups())) for m in SAMPLE.finditer(raw)]
    require(len(samples)==complete==count==MOTION['normal_reports'] and
            'SWEET M362: aborted' not in raw and calibration['qualified'] and
            strokes[-1][1]<calibration['resume_tick']<due and
            (due-strokes[-1][1])*numer>=MOTION['start_after_last_release_ms']*MS*denom and
            MOTION['timeout_from_due_ms']*MS*denom<=(limit-due)*numer<=
            (MOTION['timeout_from_due_ms']+10)*MS*denom, 'motion does not follow the original calibrated sequence')
    steps = MOTION['step_count']
    require(all((ordinal,x,down)==(i,900-720*min(i,steps)//steps,int(i<=steps)) and
                due<=entered<=returned<limit
                for i,(ordinal,entered,returned,x,down) in enumerate(samples)) and
            all((b[1]-a[2])*numer+numer>=MOTION['sample_interval_ms']*MS*denom
                for a,b in pairwise(samples)), 'motion samples violate order, pacing or trajectory')
    start = samples[0][1]+MOTION['head_excluded_ms']*MS*denom//numer
    end = samples[-1][1]-MOTION['tail_excluded_ms']*MS*denom//numer
    require((end-start)*numer>=MOTION['minimum_scored_ms']*MS*denom,'insufficient sustained motion duration')
    return dict(start_tick=start,end_tick=end,samples=samples,armed_tick=due,limit_tick=limit)


def layers_for_copies(rows, attempts):
    links = {(layer['surface'],layer['copy_start_tick'],layer['copy_end_tick']):
        dict(generation=attempt['generation'],attempt=attempt['attempt'],layer=layer)
        for attempt in attempts for layer in attempt['layers']}
    return [dict(seq=row.seq,surface=row.id,start_tick=row.a,end_tick=row.b,
                 link=links.get((row.id,row.a,row.b))) for row in rows[trace.COPY]]


def motion_display(raw, frame, rows, motion, core, joins, num, den, *, display_options=None):
    start,end = motion['start_tick'],motion['end_tick']
    trace_overlap = 55*MS*den//num
    begin, end_of_joins = start-trace_overlap, end+trace_overlap
    attempts = trace.software(rows,joins,core,begin,end_of_joins,num,den) if any(
        begin<=row.tick<end_of_joins for row in rows[trace.ATTEMPT]) else []
    hardware = scanout.hardware(frame['dpu_probe'],rows|{trace.CRC:[]},
                                [(start,end)],attempts,num,den)
    hardware['windows'] = [window for window in hardware['windows'] if window['window']=='active']
    paired = trace.indexed(frame['raw_crc_pairs'],lambda item:item['frame'],'CRC sample pair')
    hardware['windows'] = crc.summarize_windows(hardware,rows[trace.VBLANK],paired,
        layers_for_copies(rows,attempts),frame['crc_frame_calibration'],frame['misr']['qualified'],num/den)
    require(len(hardware['windows'])==1,'missing sustained motion hardware window')
    moving = dict(frame,hardware=hardware,attempts=attempts)
    return moving,copy.analyze(raw,moving,extra_kinds=KINDS,**(display_options or {}))


def window_metrics(frame, display, rows, *, motion=None):
    edges = trace.indexed(rows[trace.VBLANK],lambda event:event.id,'hardware edge')
    timing, = rows[trace.TIMING]
    copies = copy.copy_certificates(display['attempts'],edges,timing)
    by_scan = trace.indexed(copies.items(),lambda item:(item[1]['frame']+1)&0xffffffff,'copy for scan')
    paired = list(zip(frame['hardware']['windows'],display['windows'],strict=True))
    motion_ticks = [row[2] for row in motion['samples'][1:-1]] if motion else []
    num,den = frame['tick_numer'],frame['tick_denom']

    def ns(tick):
        return tick*num//den

    swap_ticks = [row.tick for row in rows[trace.SWAP] if not row.flags and row.c]
    output = {}
    for phase in sorted({lane['phase'] for _,lane in paired}):
        selected = [(window,lane) for window,lane in paired if lane['phase']==phase]
        counts = Counter()
        copy_gaps = []
        missing_input = []
        for window,lane in selected:
            require((window['window'],window['stroke']+1)==(phase,lane['stroke']),'scored windows differ')
            copies_this_window = []
            for interval in lane['intervals']:
                scan = interval['frame']
                status = interval['after_copy_boundary_check']
                counts[status] += 1
                if entry := by_scan.get(scan):
                    copies_this_window.append(entry[0][3])
                    counts['copies'] += 1
                    counts['copies_with_same_crc'] += status=='repeated'
                if motion:
                    left,right = edges[interval['previous_frame']],edges[scan]
                    begin = bisect_right(motion_ticks,left.b)
                    if begin==len(motion_ticks) or motion_ticks[begin]>=right.a:
                        missing_input.append(scan)
            copy_gaps.extend(ns(b-a) for a,b in pairwise(copies_this_window))
        lo = sum(window['elapsed_ns_low'] for window,_ in selected)
        hi = sum(window['elapsed_ns_high'] for window,_ in selected)
        require(0<lo<=hi and not counts['unknown'] and (counts['changed'] or counts['repeated']),
                'unqualified new content or hardware window')
        require(all(counts[k]==display['phases'][phase]['verified_full_frame_counts'][k]
                    for k in ('changed','repeated','unknown')), 'scan comparison counts differ')
        totals = pacing.cadence(selected,swap_ticks,ns)
        output[phase] = dict(totals,known_scans=counts['changed']+counts['repeated'],completed_copies=counts['copies'],
            copies_with_same_crc=counts['copies_with_same_crc'],
            driver_copy_rate_bounds=[counts['copies']*1e9/hi,counts['copies']*1e9/lo],
            copy_end_gap_p95_ns=trace.quantile(copy_gaps,.95),scored_span_ns_bounds=[lo,hi],
            motion_without_definite_HID_change=missing_input if motion else None)
    return output


def driver_cadence(rows, strokes, joins, cores, num, den):
    window = 2500*MS*den//num
    end = strokes[-1][0]+window
    require(rows[trace.VBLANK][-1].tick>end,'driver cadence window exceeds captured hardware period')
    attempts = trace.software(rows,joins,cores,strokes[0][0],end,num,den)
    completions = sorted(max(layer['copy_end_tick'] for layer in attempt['layers'])
                         for attempt in attempts if sum(layer['bytes'] for layer in attempt['layers'])==trace.FRAME_BYTES)
    kept = []
    dropped = 0
    for i,(start,_) in enumerate(strokes):
        follow = strokes[i+1][0] if i+1<len(strokes) else start+window
        ends = [tick for tick in completions if start<=tick<min(follow,start+window)]
        if len(ends)<3:  # Match the public frames.py minimum segment.
            continue
        for a,b in pairwise(ends):
            gap = (b-a)*num/den
            if gap<100*MS:
                kept.append(gap)
            else:
                dropped += 1
    require(kept,'no scored driver-copy intervals')
    return dict(copies_per_second=len(kept)*1e9/sum(kept),scored_intervals=len(kept),
                excluded_100ms_or_longer=dropped,copy_end_gap_p95_ns=trace.quantile(kept,.95))


def missing_swap(path, rows, display, core, num, den, strokes, *, scan_options=None):
    def ns(tick):
        return tick*num//den

    clock = num/den
    scans = {slot.frame:slot for slot in scan_windows(rows[trace.VBLANK],ns,clock,bracketed=True,**(scan_options or {}))}
    good = [r for r in rows[trace.SWAP] if r.flags==0 and r.c]
    times = [ns(r.tick) for r in good]
    took = {r.c for r in rows[TAKE]}
    source = trace.indexed(rows[trace.ATTEMPT],lambda row:row.id,'present attempt')
    used = sorted((ns(row.tick),source[row.id].a) for row in rows[trace.RESULT] if row.a)
    used_clocks = [tick for tick,_ in used]
    # Rate logs and Core can be correlated on the absolute clock. A temporal
    # match alone does not name the CA transaction or prove its causal input.
    start,end = ns(strokes[0][0])//1000,ns(strokes[-1][1])//1000
    sb = RATE.summarize(RATE.parse((path/'springboard-new.log').read_text()),start,end)
    inp = sb['input']
    require(sb['lost_rows_in_log_tail']==0 and inp['hook_active'] and inp['watch_covers_window'] and
            not any(inp[k] for k in ('unpaired_entry_ids','unpaired_end_ids','metadata_errors_in_tail',
                'write_errors_in_tail','callbacks_with_original_exception')), 'SpringBoard timing is incomplete')
    calls = inp['callback_spans']
    turns = [turn for turn in sb['turns']['rows'] if turn['observer_order_valid']]
    details = []
    for window in display['windows']:
        if window['phase']!='active':
            continue
        for interval in window['intervals']:
            if interval['after_copy_boundary_check']!='repeated':
                continue
            scan = interval['previous_frame']
            slot = scans.get(scan)
            if not slot or scan in took:
                continue
            previous = bisect_right(used_clocks,slot.opening)-1
            last = used[previous][1] if previous>=0 else 0
            i = bisect_right(times,slot.deadline)
            if i and good[i-1].id>last:
                continue
            earlier = scans.get((scan-1)&0xffffffff)
            start_us = (earlier.deadline if earlier else slot.deadline-16_667_000)//1000
            cutoff = slot.deadline//1000
            after = good[i] if i<len(good) else None
            callback = [r['id'] for r in calls if r['entered_us']<=cutoff<r['returned_us']]
            returned = [r['id'] for r in calls if start_us<r['returned_us']<=cutoff]
            bracket = [r['after_ca_us'] for r in turns if start_us<r['after_ca_us']<=cutoff]
            jobs = [dict(queue=r['queue'],ticket=r['ticket'],job=r['job'],enqueue_ns=r['enq_ns'])
                    for r in core if start_us*1000<r['enq_ns']<=slot.deadline]
            details.append(dict(stroke=window['stroke'],scan=scan,deadline_ns=slot.deadline,
                last_copied_generation=last,last_eligible_swap=good[i-1].id if i else None,
                next_swap=dict(generation=after.id,tick=after.tick,late_ns=times[i]-slot.deadline) if after else None,
                open_touch_callbacks=callback,returned_touch_callbacks=returned,
                after_CA_observer_us=bracket,core_enqueues=jobs))
    return dict(scans=len(details),open_touch_callback=sum(bool(r['open_touch_callbacks']) for r in details),
        touch_callback_returned=sum(bool(r['returned_touch_callbacks']) for r in details),
        after_CA_observer=sum(bool(r['after_CA_observer_us']) for r in details),
        Core_enqueue=sum(bool(r['core_enqueues']) for r in details),
        next_swap_within_one_60Hz_period=sum(bool(r['next_swap'] and
            r['next_swap']['late_ns']*60<=1_000_000_000) for r in details),
        details=details,correlation='Touch callbacks, CA observer and Core evidence are time-aligned.')


def sdk_core_comparison(core, joined, strokes, num, den):
    key = lambda row:(row['queue'],row['ticket'],row['job'])
    jobs = trace.indexed(core['rows'],key,'Core job')
    start = strokes[0][0]*num//den//1000
    end = strokes[-1][1]*num//den//1000+250_000
    scoped = [jobs[key(row)] for row in joined if start<=jobs[key(row)]['made_us']<end]
    require(scoped,'no Core submissions inside the original workload')
    commit = core['category_order'].index('commit')
    encoding = core['render_phase_order'].index('encode')
    require(all(sum(row['exec_ns'])==row['own_exec_ns'] and
                row['exec_ns'][commit]==row['end_ns']-row['start_ns'] for row in scoped),
            'Core recording and commit do not add up')
    return dict(joined_submissions=len(scoped),p95_us={
        name:trace.quantile([sample(row) for row in scoped],.95) for name,sample in (
            ('queue',lambda row:row['core_queue_wait_us']),
            ('recording',lambda row:(row['own_exec_ns']-row['exec_ns'][commit])/1000),
            ('commit',lambda row:row['exec_ns'][commit]/1000),
            ('encode',lambda row:row['render_ns'][encoding]/1000))})


def measure(path, *, with_motion=False):
    frame = load(path/'frame-scanout-analysis.json')
    require(frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'],
            'unqualified saved display capture')
    core = load(path/'core-wait-execution-analysis.json')
    joined = load(path/'kernel-IO-identity-analysis.json')
    require(core['coverage_qualified'] and joined['coverage_qualified'],'unqualified saved Core capture')
    raw = (path/'kernel.log').read_text()
    rows,strokes,num,den = trace.parse(raw,extra_kinds=(PRESENT,copy.WAKE,*KINDS))
    display = copy.analyze(raw,frame,extra_kinds=KINDS)
    score = dict(same_13_strokes=window_metrics(frame,display,rows),
        driver_copy_motion_cadence=driver_cadence(rows,strokes,joined['submits'],core['rows'],num,den),
        original_stroke_core=sdk_core_comparison(core,joined['submits'],strokes,num,den),
        active_repeats_without_new_swap=missing_swap(path,rows,display,core['rows'],num,den,strokes))
    if with_motion:
        try:
            input_motion = parse_motion(raw,strokes,num,den,frame['crc_frame_calibration'])
            movement,alignment = motion_display(raw,frame,rows,input_motion,core['rows'],joined['submits'],num,den)
            metrics = window_metrics(movement,alignment,rows,motion=input_motion)['active']
            hz = movement['hardware']['hardware_refresh_hz_bounds']
            require(hz and 59<=hz[0]<=hz[1]<=61 and metrics['known_scans']>=60 and
                    metrics['scored_span_ns_bounds'][0]>=1000*MS,'insufficient qualified 60 Hz edges for sustained motion')
            score['sustained_motion'] = dict(metrics,hardware_refresh_hz_bounds=hz,stimulus=input_motion,
                steady_60_qualified=(metrics['scans']['changed']==metrics['completed_copies']==metrics['known_scans']
                                     and not metrics['motion_without_definite_HID_change']))
        except ValueError as error:
            score['sustained_motion_error'] = str(error)
            return score
        try:
            motion_stroke = [(input_motion['samples'][0][1],input_motion['samples'][-1][2])]
            score['sustained_motion']['repeats_without_new_swap'] = missing_swap(
                path,rows,alignment,core['rows'],num,den,motion_stroke)
        except ValueError as error:
            score['sustained_motion']['swap_correlation_error'] = str(error)
    return score
