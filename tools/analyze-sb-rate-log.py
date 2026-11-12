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
ACTIVE = re.compile(r'RATE: active animation=1 link_fps=([01]) link_range=([01]) loop=1 flush=1; read-only$')
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
    lost = 0
    for line in text.splitlines():
        pos = line.find(PREFIX)
        if pos < 0:
            continue
        body = line[pos+len(PREFIX):]
        match = ACTIVE.fullmatch(body)
        if match:
            active.append({'link_fps':bool(int(match[1])),
                           'link_range':bool(int(match[2]))})
            continue
        match = LOST.fullmatch(body)
        if match:
            lost += int(match[1])
            if lost >= 1 << 64:
                raise ValueError('lost count overflow')
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
    return {'active':active,'lost':lost,'rows':rows}


def gap_summary(values):
    if not values:
        return {'samples':0,'median_us':None,'max_us':None,
                'over_16667_us':0,'over_50000_us':0}
    values = sorted(values)
    return {'samples':len(values),'median_us':values[len(values)//2],
            'max_us':values[-1],
            'over_16667_us':sum(x>16667 for x in values),
            'over_50000_us':sum(x>50000 for x in values)}


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
