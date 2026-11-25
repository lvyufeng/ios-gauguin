"""Score physical Spotlight input against the 0419 hardware output trace."""

from collections import defaultdict
from importlib import import_module
from itertools import pairwise
from math import ceil
import re
from statistics import median

import frame344_log as frame
import frame349_log as crc
import frame384_stage as stage


observer = import_module('run-frame417-trial')
SECOND = observer.SECOND
MS = SECOND // 1000


def display_rows(raw):
    rows = defaultdict(list)
    for line in re.findall(r'^F344E (.*)$',raw,re.M):
        row = frame.Event(*(int(col,16) for col in line.split()))
        rows[row.kind].append(row)
    return rows


def display(raw, plan):
    timing = observer.frame_timing(raw)
    frame.require(timing and timing['records'] <= plan['frame_capture']['records'] and
                  all(59 <= value <= 61 for value in timing['mean_panel_hz_bounds']) and
                  raw.splitlines().count('SWEET F387 MANUAL: opening guarded display window') == 1 and
                  'SWEET UI SCRIPT: begin stroke=' not in raw, 'physical display trace unqualified')
    rows = display_rows(raw)
    edges = sorted(rows[frame.VBLANK],key=lambda row:row.id)
    frame.require(len(edges) > 2 and all(left.b < right.a for left,right in pairwise(edges)),
                  'physical hardware edges overlap')
    stop = re.findall(r'^SWEET F345 DPU: stopped=\S+ polls=(\d+) configured=1 restored=1 gate=0$',raw,re.M)
    frame.require(len(stop) == 1, 'physical MISR teardown unverified')
    reset = crc.misr_receipts(raw,dict(polls=int(stop[0]),configured=True,restored=True),
                             edges,625/12,preserve_data_preimage=True)
    frame.require(reset['qualified'] and reset['reset']['after'] == 0x01000000, 'physical CRC preimage differs')
    pairs = crc.paired_reads(rows[frame.CRC],{row.id:row for row in edges},reset,625/12)
    valid = {number:pair['signatures'][0] for number,pair in pairs.items() if pair['agrees']}
    scans = []
    for left,right in pairwise(edges):
        kind = 'unknown'
        if right.flags == 1 and right.id == left.id + 1 and left.id in valid and right.id in valid:
            kind = 'changed' if valid[left.id] != valid[right.id] else 'repeated'
        scans.append((right.a,right.b,kind))
    original = re.findall(r'^SWEET F382 L 0 \d+ 0 (\d+)$',raw,re.M)
    drains = re.findall(r'^SWEET F416 DRAIN: cause=\S+ result=(\S+) polls=(\d+)$',raw,re.M)
    private = re.findall(r'^SWEET F382 L \d+ \d+ [12] (\d+)$',raw,re.M)
    if private:
        frame.require(len(original) == len(drains) == 1 and drains[0][0] == 'restored'
                      and 1 <= int(drains[0][1]) <= 160 and int(original[0]) > max(map(int,private)),
                      'physical display handback unverified')
    return timing, scans, len(valid), int(original[0]) if original else None


def events(log):
    frame.require(log.splitlines().count('GAUGUIN SEARCH: active numer=625 denom=12') == 1,
                  'SpringBoard input observer did not report')
    phases = [tuple(map(int,row)) for row in re.findall(
        r'^GAUGUIN SEARCH: input=(\d+) phase=([034]) shape=([0-4]) event=(\d+) begin=(\d+) end=(\d+)$',log,re.M)]
    stages = [tuple(map(int,row)) for row in re.findall(
        r'^GAUGUIN SEARCH: stage=([1-4]) tick=(\d+) length=(\d+)$',log,re.M)]
    frame.require(len(phases)+len(stages) <= 256 and
                  all(identifier > 0 and 0 < event <= begin <= end for identifier,_,_,event,begin,end in phases),
                  'UIKit input clock does not match scanout')
    press = frame.indexed((row for row in phases if row[1] == 0),lambda row:row[0],'touch press')
    release = frame.indexed((row for row in phases if row[1] == 3),lambda row:row[0],'touch release')
    completed = []
    for identifier in sorted(press.keys() & release.keys()):
        down, up = press[identifier], release[identifier]
        frame.require(down[3] < up[3] and down[4] <= up[4], 'touch release preceded its press')
        completed.append(dict(id=identifier,shape=up[2],down=down[3],up=up[3],
                              entry=down[4],exit=down[5],release_exit=up[5]))
    frame.require(all(left['up'] < right['down'] for left,right in pairwise(completed)),
                  'incomplete single-contact chronology')
    return completed, stages


def first_change(scans, start, stop, quiet=4):
    """Time to a changed output in a quiet interval with complete CRCs."""
    settled = [row for row in scans if row[1] < start][-quiet:]
    if len(settled) < quiet or any(row[2] != 'repeated' for row in settled):
        return None
    if start - settled[-1][1] > 25 * MS:
        return None
    for lo,hi,kind in scans:
        if hi < start:
            continue
        if hi >= stop or kind == 'unknown':
            break
        if kind == 'changed':
            return [max(0,lo-start)/MS,(hi-start)/MS]
    return None


def summarize(values):
    values = [bounds for bounds in values if bounds is not None]
    if not values:
        return dict(samples=0)
    lower, upper = (sorted(column) for column in zip(*values,strict=True))
    rank = ceil(.95 * len(values)) - 1
    return dict(samples=len(values),p50_ms=[median(lower),median(upper)],p95_ms=[lower[rank],upper[rank]])


def analyze(scans, touches, stages):
    openings, candidates = [], []
    open_tick = None
    for index,touch in enumerate(touches):
        down,up = touch['down'],touch['up']
        next_down = touches[index+1]['down'] if index+1 < len(touches) else scans[-1][0]
        if touch['shape'] == 2:
            open_tick = next((tick for stage,tick,_ in stages if stage == 2 and down <= tick < next_down),None)
            until = min(next_down,down + 2 * SECOND)
            frames = observer.scan_windows(scans,down,1)[0][0] if scans[-1][0] >= down + SECOND else None
            openings.append(dict(ordinal=len(openings)+1,**touch,first_output_change_ms=first_change(scans,down,until),
                                 keyboard_did_show_ms=(open_tick-down)/MS if open_tick is not None else None,
                                 first_second=frames))
        elif touch['shape'] == 1 and openings and up-down < 350 * MS:
            previous_open = openings[-1]['down']
            if not (down >= (open_tick if open_tick is not None else previous_open + SECOND)):
                continue
            until = min(next_down,up + SECOND // 2)
            changes = [(tick,length) for stage,tick,length in stages if stage == 4 and down <= tick < until]
            candidates.append(dict(**touch,opening_ordinal=len(openings),keyboard_did_show_seen=open_tick is not None,
                HID_timestamp_to_UIKit_ms=(touch['entry']-down)/MS, UIKit_press_handler_ms=(touch['exit']-touch['entry'])/MS,
                first_output_change_ms=first_change(scans,down,until),
                text_length_updates=[dict(elapsed_from_down_ms=(tick-down)/MS,length=length)
                                     for tick,length in changes]))
    return dict(openings=openings,candidate_taps=candidates,
                tap_to_first_output_change=summarize([row['first_output_change_ms'] for row in candidates]),
                semantics='A changed full-screen signature does not identify the key or character.')


def add_writer_timings(raw, result):
    rows = display_rows(raw)
    available = import_module('run-frame382-trial').latch_receipts(raw,rows)['accepted_by_scan']
    joins = stage.verified_latches(rows,available)
    id_by_tick = {edge.b:edge.id for edge in rows[frame.VBLANK]}
    for item in (*result['openings'],*result['candidate_taps']):
        first = item['first_output_change_ms']
        if first is None:
            continue
        scan = id_by_tick.get(item['down'] + round(first[1]*MS))
        writer = joins.get(scan)
        if writer is None:
            continue
        item['first_changed_scan_writer'] = dict(scan=scan,generation=writer['generation'],fence=writer['fence'],
            swap_from_down_ms=(writer['swap_tick']-item['down'])/MS,
            issue_from_down_ms=(writer['issue_tick']-item['down'])/MS,
            issue_to_observed_completion_ms=(writer['eop_tick']-writer['issue_tick'])/MS,
            completion_to_visibility_ms=(writer['visible_tick']-writer['eop_tick'])/MS,
            visibility_to_copy_start_ms=(writer['begin']-writer['visible_tick'])/MS,
            copy_ms=(writer['tick']-writer['begin'])/MS,
            copy_end_to_confirmed_latch_ms=(writer['confirmed_tick']-writer['tick'])/MS)
    result['exact_private_writer_joins'] = len(joins)


def measure(raw, userspace, plan):
    timing,scans,pairs,original = display(raw,plan)
    touches,stages = events(userspace)
    nvt = re.findall(r'^SWEET NVT: observed contact mask=(\w+) packets=(\d+)$',raw,re.M)
    frame.require('starting physical reports' in raw and nvt,'physical Novatek receipt missing')
    first, last = scans[0][1], scans[-1][0]
    fixed, _ = observer.scan_windows(scans,first,(last-first)//SECOND)
    for index, row in enumerate(fixed):
        begin, end = first + index * SECOND, first + (index+1) * SECOND
        row['private_scanout'] = original is not None and end <= original
        row['inherited_scanout'] = original is not None and begin >= original
    covered = [touch for touch in touches if first <= touch['down'] < touch['up'] < last]
    result = analyze(scans,covered,stages)
    try:
        add_writer_timings(raw,result)
    except (ValueError,KeyError) as error:
        result['writer_timeline_error'] = str(error)
    return dict(result,panel_timing=timing,agreeing_crc_pairs=pairs,physical_contact_transitions=len(nvt),
                fixed_seconds=fixed,trace_start_tick=first,original_front_tick=original,
                completed_UI_touches=len(covered),keyboard_stages=stages)
