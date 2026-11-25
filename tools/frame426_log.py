"""Align Spotlight press/release with exact CA renders and paired output CRCs."""

from importlib import import_module
from itertools import pairwise
import re

import frame344_log as frame
import frame349_log as crc
import frame374_native_ca as ca
import frame384_stage as stage
import frame424_log as input_log
from frame369_swap_timing import decode as swap_timing


observer = input_log.observer
SECOND, MS = input_log.SECOND,input_log.MS


def scripted_inputs(raw):
    start = [tuple(map(int,row)) for row in re.findall(
        r'^SWEET UI SCRIPT: begin stroke=(\d+) tick=(\d+) origin=synthetic$',raw,re.M)]
    end = [tuple(map(int,row)) for row in re.findall(
        r'^SWEET UI SCRIPT: end stroke=(\d+) tick=(\d+) events=(\d+); HID return only$',raw,re.M)]
    frame.require([row[0] for row in start] == [row[0] for row in end] == list(range(11))
                  and [row[2] for row in end] == [34,34]+[12]*9
                  and raw.splitlines().count('SWEET F426 SCRIPT: complete strokes=11 reports=176; HID return only') == 1
                  and 'SWEET NVT: observed contact mask=' not in raw,
                  'bounded Spotlight stimulus differs or ended early')
    strokes = [(low,high) for (_,low),(_,high,_) in zip(start,end,strict=True)]
    frame.require(all(low < high for low,high in strokes)
                  and all(left[1] < right[0] for left,right in pairwise(strokes)),
                  'scripted inputs overlap or release is absent')
    return strokes


def hardware(raw, rows, plan):
    timing = observer.frame_timing(raw)
    edges = sorted(rows[frame.VBLANK],key=lambda r:r.id)
    frame.require(timing and timing['records'] <= plan['frame_capture']['records']
                  and all(59 <= f <= 61 for f in timing['mean_panel_hz_bounds'])
                  and len(edges) > 2 and all(left.b < right.a for left,right in pairwise(edges))
                  and raw.splitlines().count('SWEET F426: opening guarded Spotlight display window') == 1,
                  'Spotlight hardware capture unavailable or mistimed')
    poll = int(frame.one(r'^SWEET F345 DPU: stopped=\S+ polls=(\d+) configured=1 restored=1 gate=0$',
                         raw,'CRC stop and handback'))
    receipt = crc.misr_receipts(raw,dict(polls=poll,configured=True,restored=True),edges,625/12,
                               preserve_data_preimage=True)
    frame.require(receipt['qualified'] and receipt['reset']['after'] == 0x01000000,
                  'Spotlight CRC cleanup differs')
    reads = crc.paired_reads(rows[frame.CRC],{e.id:e for e in edges},receipt,625/12)
    valid = {n:x['signatures'][0] for n,x in reads.items() if x['agrees']}
    scans = []
    for left,right in pairwise(edges):
        label = 'unknown'
        if right.id == left.id+1 and right.flags == 1 and left.id in valid and right.id in valid:
            label = 'changed' if valid[left.id] != valid[right.id] else 'repeated'
        scans.append((right.a,right.b,label))
    return timing,scans,len(valid)


def source_log(text):
    touches, stages = input_log.events(text)
    frame.require(text.splitlines().count('GAUGUIN SEARCH TIME: armed loop=3 commit=1 flush=1') == 1,
                  'SpringBoard CA observers did not arm')
    turns = [tuple(map(int,row)) for row in re.findall(
        r'^GAUGUIN SEARCH TIME: input=(\d+) kind=([1-5]) start=(\d+) stop=(\d+)$',text,re.M)]
    targets = frame.indexed(((int(i),name) for i,name in re.findall(
        r'^GAUGUIN SEARCH TARGET: input=(\d+) view=(\S+)$',text,re.M)),lambda row:row[0],'input view')
    geometry = [(int(tick),*(float(v) for v in rect)) for tick,*rect in re.findall(
        r'^GAUGUIN SEARCH GEOMETRY: tick=(\d+) x=(-?\d+\.\d) y=(-?\d+\.\d) w=(\d+\.\d) h=(\d+\.\d)$',
        text,re.M)]
    frame.require(len(turns) <= 640 and all(i and 0 <= a <= b and (k >= 4 or a == b) for i,k,a,b in turns),
                  'main-loop or commit span differs')
    return touches,stages,turns,targets,geometry


def native_render(raw, rows):
    start,end,n,d = ca.envelope(raw)
    frame.require((n,d) == (625,12),'native CA uses a different clock')
    accepted = [row for row in swap_timing(rows,n,d,begin_threads=True) if row['begin_thread']]
    links = ca.link_swaps(ca.decode(raw,start,end),accepted,start,end,n,d)
    return {generation:link['render'] for generation,link in links.items() if link['render']}


def first_after(scans, start, stop):
    for lo,hi,kind in scans:
        if hi < start:
            continue
        if hi >= stop or kind == 'unknown':
            return None
        if kind == 'changed':
            return lo,hi
    return None


def measure(raw, userspace, plan):
    script = scripted_inputs(raw)
    rows = input_log.display_rows(raw)
    timing,scans,read_count = hardware(raw,rows,plan)
    touches,stages,turns,targets,geometries = source_log(userspace)
    shown = [(tick,length) for kind,tick,length in stages if kind == 2 and script[1][0] <= tick < script[2][0]]
    keyboard_visible = bool(shown and any(script[1][0] <= tick < script[2][0] and h > 0 for tick,_,_,_,h in geometries))
    result = dict(panel_timing=timing, agreeing_crc_pairs=read_count, keyboard_reported=keyboard_visible,
                  keyboard_notifications=stages, keyboard_geometry=geometries)
    opening_tick = script[1][0]
    result['pull_down_first_second'] = observer.scan_windows(scans,opening_tick,1)[0][0]
    first = scans[0][1]
    result['fixed_seconds'] = observer.scan_windows(scans,first,(scans[-1][0]-first)//SECOND)[0]
    if shown:
        result['opening_to_keyboard_notification_ms'] = (shown[0][0]-opening_tick)/MS
    try:
        latches = import_module('run-frame382-trial').latch_receipts(raw,rows)['accepted_by_scan']
        writers = stage.verified_latches(rows,latches)
    except (KeyError,ValueError) as error:
        result['writer_error'] = str(error)
        writers = {}
    try:
        renders = native_render(raw,rows)
    except (KeyError,ValueError) as error:
        result['native_CA_error'] = str(error)
        renders = {}
    result.update(exact_private_writers=len(writers),exact_CA_renders=len(renders))
    by_edge = {edge.b:edge.id for edge in rows[frame.VBLANK]}
    samples = []
    for ordinal,(down,up) in enumerate(script):
        if ordinal == 0:
            continue
        next_down = script[ordinal+1][0] if ordinal+1 < len(script) else up+SECOND
        delivered = [row for row in touches if down <= row['down'] <= down + 150*MS and
                     up - 20*MS <= row['up'] <= up + 150*MS and row['shape'] == (1 if ordinal >= 2 else 2)]
        sample = dict(stroke=ordinal,script_down=down,script_up=up,delivered=len(delivered)==1)
        samples.append(sample)
        if not delivered or len(delivered) != 1:
            continue
        touch = delivered[0]
        start = touch['down'] if ordinal == 1 else touch['up']
        view = targets.get(touch['id'],(0,None))[1]
        sample.update(touch=touch,view_class=view,keyboard_target=bool(keyboard_visible and view and 'Keyboard' in view))
        response = first_after(scans,start,min(next_down,start + SECOND//2))
        if response is None:
            continue
        lo,hi = response
        sample['first_changed_output_ms'] = [max(0,lo-start)/MS,(hi-start)/MS]
        writer = writers.get(by_edge[hi])
        if not writer:
            continue
        render = renders.get(writer['generation'])
        go = writer['swap_tick']
        sample.update(accepted_swap_ms=(go-start)/MS, swap_to_output_ms=[(lo-go)/MS,(hi-go)/MS],
                      native_render_begin_ms=(render['begin_tick']-start)/MS if render else None,
                      native_render_end_ms=(render['end_tick']-start)/MS if render else None,
                      main_loop=[dict(kind=k,start_ms=(a-start)/MS,stop_ms=(b-start)/MS)
                                 for i,k,a,b in turns if i == touch['id'] and start <= a <= hi])
    result['script_samples'] = samples
    result['verified_keyboard_targets'] = sum(row.get('keyboard_target',False) for row in samples)
    return result
