#!/usr/bin/env python3
"""Parse opt-in SpringBoard rate and run-loop logs; never infer panel FPS."""

import argparse
import importlib.util
import json
import math
import re
from pathlib import Path


MAX_RECORDS = 100000
PREFIX = 'SWEET SB '
ACTIVE = re.compile(r'RATE: active animation=([01]) link_fps=([01]) link_range=([01]) loop=([01]) flush=1; read-only$')
INPUT_ACTIVE = re.compile(r'INPUT: active send_event=([01]) target=SpringBoard watch=1; unchanged forwarding$')
INPUT_BEGIN = re.compile(r'INPUT: begin id=(\d+) us=(\d+) event_us=(\d+) touches=(\d+) phases=([0-9a-f]+) flags=([0-9a-f]+) view=([^ ]*) window=([^ ]*)$')
INPUT_END = re.compile(r'INPUT: end id=(\d+) us=(\d+) entered_us=(\d+) returned=([01])$')
WATCH = re.compile(r'WATCH: us=(\d+) phase=([0-3]) turn_start_us=(\d+) inputs=(\d+) turns=(\d+) metadata_errors=(\d+) write_errors=(\d+)$')
ANIMATION = re.compile(r'RATE: us=([0-9]+) kind=animation class=([^ ]*) key=([^ ]*) min=([^ ]+) max=([^ ]+) preferred=([^ ]+) caller=([^ ]+)$')
LINK_FPS = re.compile(r'RATE: us=([0-9]+) kind=link-fps asked=(-?[0-9]+) caller=([^ ]+)$')
LINK_RANGE = re.compile(r'RATE: us=([0-9]+) kind=link-range min=([^ ]+) max=([^ ]+) preferred=([^ ]+) caller=([^ ]+)$')
TURN = re.compile(r'TURN: woke_us=([0-9]+) before_ca_us=([0-9]+) after_ca_us=([0-9]+)$')
LOST = re.compile(r'RATE: lost=([0-9]+)$')


def rate(value):
    number = float(value)
    if not math.isfinite(number) or number < 0 or number > 1000:
        raise ValueError('invalid SpringBoard rate')
    return number


def parse(text):
    rows = []
    active = []
    input_active = []
    input_begins = set()
    input_ends = set()
    lost = 0
    for line in text.splitlines():
        pos = line.find(PREFIX)
        if pos < 0:
            continue
        body = line[pos+len(PREFIX):]
        match = ACTIVE.fullmatch(body)
        if match:
            active.append(dict(zip(('animation','link_fps','link_range','loop'),
                                   (bool(int(value)) for value in match.groups()))))
            continue
        match = INPUT_ACTIVE.fullmatch(body)
        if match:
            input_active.append({'send_event':bool(int(match[1])),'target':'SpringBoard','watch':True})
            continue
        match = LOST.fullmatch(body)
        if match:
            lost += int(match[1])
            if lost >= 1 << 64:
                raise ValueError('lost count overflow')
            continue
        begin, end, watch = INPUT_BEGIN.fullmatch(body), INPUT_END.fullmatch(body), WATCH.fullmatch(body)
        if begin or end or watch:
            if begin:
                ident, us, stamp, touches = map(int,begin.group(1,2,3,4))
                phases, flags = int(begin[5],16), int(begin[6],16)
                if not ident or ident in input_begins or phases >= 1<<32 or flags & ~15:
                    raise ValueError('invalid/duplicate input begin')
                input_begins.add(ident)
                row = dict(kind='input-begin',id=ident,us=us,event_us=stamp,
                           touches=touches,phases=phases,flags=flags,view_class=begin[7],window_class=begin[8])
            elif end:
                ident, us, entered, returned = map(int,end.groups())
                if not ident or ident in input_ends or not 0 < entered <= us:
                    raise ValueError('invalid/duplicate input end')
                input_ends.add(ident)
                row = dict(kind='input-end',id=ident,us=us,entered_us=entered,returned=bool(returned))
            else:
                us, phase, began, inputs, turns, errors, writes = map(int,watch.groups())
                if (phase==0 and began!=0) or (phase in (1,2) and not 0<began<=us) or began>us:
                    raise ValueError('invalid watch phase/time')
                row = dict(kind='watch',us=us,phase=phase,turn_start_us=began,
                           inputs=inputs,turns=turns,metadata_errors=errors,write_errors=writes)
            if not row['us'] or any(isinstance(v,int) and not 0<=v<1<<64 for v in row.values()) or len(rows)>=MAX_RECORDS:
                raise ValueError('input/watch value or count out of bounds')
            rows.append(row)
            continue
        match = ANIMATION.fullmatch(body)
        if match:
            us = int(match[1]);minimum,maximum,preferred = map(rate,match.group(4,5,6))
            row = {'kind':'animation','us':us,'class':match[2],'key':match[3],
                   'minimum':minimum,'maximum':maximum,'preferred':preferred,
                   'caller':match[7]}
        else:
            match = LINK_FPS.fullmatch(body)
            if match:
                row = {'kind':'link-fps','us':int(match[1]),'asked':int(match[2]),
                       'caller':match[3]}
            else:
                match = LINK_RANGE.fullmatch(body)
                if match:
                    minimum,maximum,preferred = map(rate,match.group(2,3,4))
                    row = {'kind':'link-range','us':int(match[1]),'minimum':minimum,
                           'maximum':maximum,'preferred':preferred,'caller':match[5]}
                else:
                    match = TURN.fullmatch(body)
                    if not match:
                        raise ValueError('malformed SWEET SB log row')
                    woke,before,after = map(int,match.groups())
                    valid = 0 < woke <= before <= after
                    row = {'kind':'turn','us':woke,'woke_us':woke,
                           'before_ca_us':before,'after_ca_us':after,
                           'observer_order_valid':valid,
                           'wake_to_before_us':before-woke if valid else None,
                           'observer_bracket_us':after-before if valid else None}
        if row['us'] >= 1 << 64 or len(rows) >= MAX_RECORDS:
            raise ValueError('SpringBoard log timestamp/count out of bounds')
        rows.append(row)
    return {'active':active,'input_active':input_active,'lost':lost,'rows':rows}


def gap_summary(values):
    if not values:
        return {'samples':0,'median_us':None,'max_us':None,
                'over_16667_us':0,'over_50000_us':0}
    values = sorted(values)
    return {'samples':len(values),'median_us':values[len(values)//2],
            'max_us':values[-1],
            'over_16667_us':sum(x>16667 for x in values),
            'over_50000_us':sum(x>50000 for x in values)}


def summarize_input(parsed,start_us=None,end_us=None):
    def within(us):
        return start_us is None or start_us<=us<end_us
    begins={row['id']:row for row in parsed['rows'] if row['kind']=='input-begin'}
    ends={row['id']:row for row in parsed['rows'] if row['kind']=='input-end'}
    spans=[]
    for ident,begin in begins.items():
        end=ends.get(ident)
        if end is None:continue
        if end['entered_us']!=begin['us'] or end['us']<begin['us']:
            raise ValueError('input span identity/time mismatch')
        if start_us is not None and (begin['us']>=end_us or end['us']<start_us):continue
        spans.append(dict(id=ident,entered_us=begin['us'],returned_us=end['us'],
                          duration_us=end['us']-begin['us'],returned=end['returned'],
                          flags=begin['flags'],touches=begin['touches'],phases=begin['phases']))
    entries=[row for row in begins.values() if within(row['us'])]
    watches=[row for row in parsed['rows'] if row['kind']=='watch']
    for before,after in zip(watches,watches[1:]):
        if after['us']<=before['us'] or any(after[key]<before[key] for key in ('inputs','turns','metadata_errors','write_errors')):
            raise ValueError('watch clock or counters regressed; mixed boots/tail')
    selected=[row for row in watches if within(row['us'])]
    coverage=False
    if start_us is not None:
        before=[row for row in watches if row['us']<=start_us]
        after=[row for row in watches if row['us']>=end_us]
        if before and after:
            covered=[before[-1]]+[row for row in watches if start_us<row['us']<end_us]+[after[0]]
            coverage=all(b['us']-a['us']<=2500000 for a,b in zip(covered,covered[1:]))
    input_active=parsed.get('input_active',[])
    hook=len(input_active)==1 and input_active[0]['send_event']
    errors=max((row['metadata_errors'] for row in watches),default=0)
    write_errors=max((row['write_errors'] for row in watches),default=0)
    phases={str(phase):sum(row['phase']==phase for row in selected) for phase in range(4)}
    ages={str(phase):gap_summary([row['us']-row['turn_start_us'] for row in selected
                                 if row['phase']==phase and row['turn_start_us']]) for phase in (1,2,3)}
    return {
        'scope':'Public SpringBoard sendEvent touch entry and return, not raw HID receipt or gesture recognition. '
                'UIEvent timestamp age is not a validated kernel/physical touch latency. Watch phases are observer milestones, not stack samples.',
        'hook_active':hook,'activation_markers':input_active,'entries_in_window':len(entries),
        'main_thread_entries_in_window':sum(not row['flags']&8 for row in entries),
        'touch_entry_observed':hook and bool(entries),
        'no_new_touch_entries_with_window_coverage':hook and not entries and coverage and parsed['lost']==0 and errors==0 and write_errors==0,
        'callback_spans_overlap_window':bool(spans),
        'watch_covers_window':coverage,'metadata_errors_in_tail':errors,'write_errors_in_tail':write_errors,
        'callback_durations':gap_summary([row['duration_us'] for row in spans]),
        'callbacks_with_original_exception':sum(not row['returned'] for row in spans),
        'callback_spans':spans,
        'unpaired_entry_ids':[ident for ident,row in begins.items() if ident not in ends and (end_us is None or row['us']<end_us)],
        'unpaired_end_ids':[ident for ident,row in ends.items() if ident not in begins and within(row['us'])],
        'entries':entries,'watch_rows':selected,'watch_phase_counts':phases,'watch_turn_ages':ages,
        'phase_meanings':{'0':'last-before-wait observer','1':'after-wake body','2':'before-CA observer',
                          '3':'after-CA observer; zero turn_start means unobserved/invalid'},
        'physical_touch_qualified':False,'gesture_acceptance_qualified':False,'physical_fps_qualified':False,
    }


def summarize(parsed,start_us=None,end_us=None):
    if (start_us is None) != (end_us is None) or (start_us is not None and
            not 0 <= start_us < end_us):
        raise ValueError('invalid analysis window')
    rows = [row for row in parsed['rows'] if start_us is None or
            (row['us'] < end_us and (row['after_ca_us'] >= start_us if row['kind']=='turn'
                                      else row['us'] >= start_us))]
    animations = [row for row in rows if row['kind']=='animation']
    fps = [row for row in rows if row['kind']=='link-fps']
    ranges = [row for row in rows if row['kind']=='link-range']
    turns = [row for row in rows if row['kind']=='turn']
    good = [row for row in turns if row['observer_order_valid']]
    woke = sorted(row['woke_us'] for row in good)
    wake_gaps = [b-a for a,b in zip(woke,woke[1:])]
    asked = {}
    for row in fps:
        key = str(row['asked']);asked[key] = asked.get(key,0)+1
    return {'scope':'SpringBoard requests and CPU run-loop timestamps only. The CA observer order is unverified on 20H392; no causal touch/frame link, panel latch or physical FPS.',
            'window':{'start_us':start_us,'end_us':end_us},
            'observer_seen':bool(parsed['active']),
            'active_markers':parsed['active'],'lost_rows_in_log_tail':parsed['lost'],
            'records_total':len(parsed['rows']),'records_in_window':len(rows),
            'animation':{'count':len(animations),'zero_maximum':sum(row['maximum']==0 for row in animations),
                         'rows':animations},
            'display_link':{'fps_request_counts':asked,'range_rows':ranges},
            'input':summarize_input(parsed,start_us,end_us),
            'turns':{'count':len(turns),'valid_observer_order':len(good),
                     'invalid_observer_order':len(turns)-len(good),
                     'wakeup_gaps':gap_summary(wake_gaps),
                     'wake_to_before':gap_summary([row['wake_to_before_us'] for row in good]),
                     'observer_bracket':gap_summary([row['observer_bracket_us'] for row in good]),
                     'rows':turns}}


def window_from_kernel(text):
    spec = importlib.util.spec_from_file_location('ui_trace_log',
                                                    Path(__file__).with_name('ui_trace_log.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    capture = module.parse(text)
    if not capture['clock_valid']:
        raise ValueError('UI254 clock invalid')
    header = capture['header']
    return ((header['start']*header['numer']//header['denom'])//1000,
            (header['end']*header['numer']//header['denom'])//1000)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('springboard_log',type=Path)
    ap.add_argument('--kernel-log',type=Path)
    ap.add_argument('--out',type=Path)
    args = ap.parse_args()
    bounds = window_from_kernel(args.kernel_log.read_text(errors='replace')) if args.kernel_log else (None,None)
    result = summarize(parse(args.springboard_log.read_text(errors='replace')),*bounds)
    data = json.dumps(result,indent=2,allow_nan=False)+'\n'
    if args.out:
        with args.out.open('x') as stream:stream.write(data)
    else:
        print(data,end='')


if __name__ == '__main__':
    main()
