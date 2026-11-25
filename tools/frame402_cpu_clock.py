"""Decode stock CPU operating points, frequency counters and exact restoration."""

from collections import defaultdict
import re
from statistics import median

import frame344_log as trace

EVENT = re.compile(r'^SWEET CPU402 E: kind=(\d+) tick=(\d+) end=(\d+) stroke=(\d+) state=(\d+) cycles=(\d+) temp=(-?\d+)$',re.M)
MAP = re.compile(r'^SWEET CPU402 MAP: admitted=1 enable=([0-9a-f]+) original=(\d+):([0-9a-f]+):([0-9a-f]+) '
                 r'target=(\d+):([0-9a-f]+):([0-9a-f]+) sensor_state=([0-9a-f]+)$', re.M)
STOP = re.compile(r'^SWEET CPU402 STOP: selects=(\d+) restores=(\d+) pending=(\d+) disabled=(\d+) lost=(\d+)$',re.M)


def cpu_receipts(raw, measures, numer, denom, *, target_khz):
    multiplier,remainder = divmod(target_khz,19_200)
    trace.require(0<multiplier<256 and not remainder, "CPU clock is outside the stock multiplier table")
    matches = MAP.findall(raw)
    denied = re.findall(r'^SWEET CPU402 (?:MAP: admitted=0|LUT:)[^\n]*$',raw,re.M)
    trace.require(len(matches) <= 1 and (not matches or not denied),'ambiguous stock CPU map')
    if not matches:
        trace.require(not EVENT.findall(raw) and not STOP.findall(raw),'CPU receipts lack a qualified map')
        return dict(map_admitted=False,details=denied,selector_cleanup_qualified=bool(denied),
                    warm_eleven_qualified=False,drag_qualified=False)
    raw_map, = matches
    enable, original_row, original_volt, target_row, target_volt, sensors = (
        int(raw_map[i],16) for i in (0,2,3,5,6,7))
    original, selected = map(int,(raw_map[1],raw_map[4]))
    trace.require(enable & 1 and original==0 and original_row==0x0002000f and
        original_volt & 0xfff and 0<selected<40 and target_row>>30 and
        ((target_row>>16)&7)==2 and (target_row&0xff)==multiplier and target_volt&0xfff and
        sensors&0xf001==0xf001, 'CPU402 hardware map receipt differs')
    stop = STOP.findall(raw)
    trace.require(len(stop)==1,'CPU selector terminal readback is missing')
    selects,restores,pending,disabled,lost = map(int,stop[0])
    events = [tuple(map(int,e)) for e in EVENT.findall(raw)]
    trace.require(len(events)<=512 and
        all(0<tick<=end and 1<=stroke<=14 for _,tick,end,stroke,_,_,_ in events) and
        events==sorted(events,key=lambda e:e[1]),'CPU402 events malformed')
    begins, ends = {}, {}
    intervals = defaultdict(list)
    samples = {}
    interruptions = []
    active = None
    complete = not (pending or lost)
    for kind,tick,end,stroke,state,cycles,temp in events:
        if kind == 0:
            trace.require(active is None and stroke not in begins and state in (0,1),
                          'overlapping CPU402 interaction')
            if state:
                trace.require(50<=temp<650,'CPU selector enabled above its thermal gate')
                begins[stroke] = tick
                active = stroke
        elif kind == 1:
            trace.require(active==stroke and state==selected and 50<=temp<650,
                          'CPU402 sample has no selected and thermally qualified interaction')
            last = samples.get(stroke)
            if last and 0<tick-last[0] and max(end-tick,last[3]-last[0])*numer <= 20_000*denom:
                delta = (cycles-last[1]) & 0xffffffff
                khz = delta*1_000_000*denom/((tick-last[0])*numer)
                intervals[stroke].append(dict(start=last[0],end=tick,khz=khz,hottest_deci=max(temp,last[2])))
            samples[stroke] = (tick,cycles,temp,end)
        elif kind == 2:
            if state == 1 and cycles == original:
                if active == stroke:
                    active = None
                    ends[stroke] = tick
            else:
                complete = False
        elif kind == 3:
            trace.require(active==stroke and state in (1,2),
                          'CPU402 interruption has no active lease or reason')
            interruptions.append(dict(stroke=stroke,tick=tick,reason='temperature' if state==1 else 'selector',
                                      selector=cycles,hottest_deci=temp))
        else:
            raise ValueError('unknown CPU402 receipt kind')
    cleanup = complete and not active and restores>=selects==len(begins)==len(ends)
    target = target_khz
    def has_target_rate(rows):
        return any(.9*target<=row['khz']<=1.1*target for row in rows)
    ordinary = measures['moving_GPU']['ordinary']['windows']
    warm_pairs = {}
    for window in ordinary:
        stroke = window['stroke']
        warm_pairs[stroke] = [r for r in intervals[stroke]
                              if window['start']<=r['start']<r['end']<=window['end']]
    drag_windows = measures['moving_GPU']['slow_drag']['windows']
    drag_pairs = [r for r in intervals[14] if any(
        w['start']<=r['start']<r['end']<=w['end'] for w in drag_windows)]
    warm_rates = [r['khz'] for rows in warm_pairs.values() for r in rows]
    return dict(map_admitted=True,original_selector=original,requested_selector=selected,
        requested_khz=target,selector_cleanup_qualified=cleanup,successful_selects=selects,restores=restores,
        failed_or_stopped=bool(disabled),events_lost=lost,interruptions=interruptions,
        intervals=dict(intervals),selected_begins=begins,
        restored_ends=ends,warm_pairs=warm_pairs,drag_pairs=drag_pairs,
        warm_domain_median_khz=median(warm_rates) if warm_rates else None,
        warm_eleven_qualified=cleanup and set(warm_pairs)==set(range(3,14)) and
            all(has_target_rate(rows) for rows in warm_pairs.values()),
        drag_qualified=cleanup and has_target_rate(drag_pairs))
