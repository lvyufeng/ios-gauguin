"""Qualify per-frame blanking MISR reads and measure DPU output cadence."""

from bisect import bisect_right
from collections import Counter
import re

import frame344_log as frames
import frame345_log as scanout


CONFIG = 0x81000101
READY = frames.CRC_CONTROL
MASK32 = 0xffffffff
STEP = 0xfffff
LINE_MASK = 0x1fff
BLANK_FIRST, BLANK_END = 2752, 4480
COPY_GUARD_NS = 1_000_000
DATA_INPUT = 0x01000000


def owned(control):
    return control in (CONFIG, READY)


def qualified_edge(edges, frame, line, intervals, scale):
    i = next((i for i,row in enumerate(edges) if row.id==frame),-1)
    lane = edges[max(0,i-intervals):i+1]
    return (len(lane)==intervals+1 and 0<=line==lane[-1].c<4910//4 and
            all(b.flags==1 and (b.id-a.id)&MASK32==1 and b.c<4910//4 and
                14_300_000<=(b.b-a.b)*scale<=19_000_000 and (b.b-b.a)*scale<=3_200_000
                for a,b in zip(lane,lane[1:])))


def stable_preimage_reads(text, edges, scale, terminal_poll):
    records = re.findall(r'^SWEET F350 PRE: (.*)$',text,re.M)
    frames.require(len(records)<=2,'too many MISR control observations')
    reads = []
    for i,record in enumerate(records,1):
        match = re.fullmatch(r'read=([12]) poll=(\d+) frame=(\d+) line=(\d+)'
                             r' streak=([34]) value=([0-9a-f]{1,8})',record)
        frames.require(match is not None,'invalid MISR control observation')
        index,poll,frame,line,streak = map(int,match.groups()[:5])
        frames.require(index==i and (reads[-1]['poll'] if reads else 0)<poll<=terminal_poll and
                       (i==2 or streak==3) and qualified_edge(edges,frame,line,streak,scale),
                       'MISR control read lacks its independent hardware edge')
        reads.append(dict(poll=poll,frame=frame,line=line,streak=streak,value=int(match[6],16)))
    if len(reads)==2:
        first,second = reads
        frames.require(first['value']==DATA_INPUT,'second MISR control read after an ineligible first read')
        confirmed = (second['value']==DATA_INPUT and second['streak']==4 and
                     (second['frame']-first['frame'])&MASK32==1)
    else:
        confirmed = False
    return reads, confirmed


def misr_receipts(text, gate, edges, scale, *, preserve_data_preimage=False):
    reset = frames.one(r'^SWEET F349 RESET: poll=(\d+) readable=([01]) before=([0-9a-f]{1,8})'
                       r' after=([0-9a-f]{1,8}) writes=([024]) fault=([01]) pairs=(\d+)'
                       r' not_ready=(\d+) rejected=(\d+)$', text, 'blanking MISR cleanup')
    poll, readable, before, after, writes, fault, pairs, not_ready, rejected = (
        int(value, 16 if i in (2, 3) else 10) for i, value in enumerate(reset))
    arms = re.findall(r'^SWEET F349 ARM: (.*)$', text, re.M)
    frames.require(len(arms)<=1 and poll==gate['polls'] and
                   pairs*2+not_ready+rejected<=poll and
                   (readable or before==after==MASK32), 'invalid MISR terminal receipt')
    reads, confirmed = (stable_preimage_reads(text,edges,scale,poll) if preserve_data_preimage else ([],False))
    if preserve_data_preimage:
        frames.require(bool(arms)==confirmed,'MISR setup requires two matching idle control reads')
    arm = None
    if arms:
        fields = re.fullmatch(r'poll=(\d+) frame=(\d+) line=(\d+) streak=([34]) preimage=([0-9a-f]{1,8})'
                              r' readback=([0-9a-f]{1,8}) writes=([02])', arms[0])
        frames.require(fields is not None, 'invalid MISR setup receipt')
        at, frame, line, streak, preimage, readback, setup_writes = (
            int(value,16 if i in (4,5) else 10) for i,value in enumerate(fields.groups()))
        if preserve_data_preimage:
            last = reads[-1]
            frames.require((at,frame,line,streak,preimage,setup_writes)==
                           (last['poll'],last['frame'],last['line'],4,DATA_INPUT,2),
                           'MISR setup differs from the independently verified preimage')
        else:
            frames.require(0<at<=poll and frame<=MASK32 and streak==3 and
                           ((preimage==0 and setup_writes==2) or (preimage==readback!=0 and setup_writes==0)),
                           'MISR setup exceeded its zero-preimage write scope')
            frames.require(qualified_edge(edges,frame,line,streak,scale),
                           'MISR setup lacks three qualified 60 Hz intervals')
        arm = dict(poll=at,frame=frame,line=line,preimage=preimage,readback=readback,writes=setup_writes)
    setup_writes = arm['writes'] if arm else 0
    configured = bool(setup_writes and owned(arm['readback']))
    reset_writes = writes-setup_writes
    restore_value = arm['preimage'] if setup_writes else None
    should_reset = readable and owned(before) and not (preserve_data_preimage and fault)
    restored = writes==0 or (readable and after==restore_value)
    frames.require((not readable or setup_writes==2) and
                   reset_writes==(2 if should_reset else 0) and
                   (reset_writes or before==after) and
                   gate['configured']==configured and gate['restored']==restored and
                   (configured or not (pairs or not_ready or rejected or fault)),
                   'MISR ownership, write count or readback does not reconcile')
    return dict(arm=arm,reset=dict(poll=poll,readable=bool(readable),before=before,after=after,
                                 writes=reset_writes),total_writes=writes,fault=bool(fault),
                pairs=pairs,not_ready_polls=not_ready,rejected_polls=rejected,
                preimage_control_reads=reads,preimage_confirmed=confirmed,
                qualified=configured and not fault and reset_writes==2 and restored)


def paired_reads(rows, slots, receipt, scale):
    frames.require(len(rows)<=3000, 'MISR pair capacity exceeded')
    paired = {}
    for row in rows:
        slot = slots.get(row.id)
        following = slots.get((row.id+1)&MASK32)
        first_line, second_line = row.flags&LINE_MASK, row.flags>>13
        first_start = row.b
        first_end = first_start+((row.c>>20)&STEP)
        second_start = first_start+(row.c>>40)
        second_end = second_start+(row.c&STEP)
        frames.require(receipt['arm'] and slot and row.id not in paired and row.c>>60==0 and
                       2<=(row.id-receipt['arm']['frame'])&MASK32<40960 and
                       BLANK_FIRST<=first_line<second_line<BLANK_END and
                       slot.b<=first_start<first_end<second_start<second_end<=row.tick and
                       (not following or second_end<=following.b) and
                       (first_end-first_start)*scale<=250_000 and (second_end-second_start)*scale<=250_000 and
                       (second_end-first_start)*scale<=8_000_000,
                       'dual MISR read has no valid blanking/frame bracket')
        sig0,sig1 = row.a>>32,row.a&MASK32
        paired[row.id] = dict(frame=row.id,lines=[first_line,second_line],
                              ticks=[[first_start,first_end],[second_start,second_end]],
                              signatures=[sig0,sig1],agrees=sig0==sig1)
    frames.require(len(paired)==receipt['pairs'], 'MISR pair rows differ from cleanup receipt')
    return paired


def copy_overlap(copies, start, end):
    return [row for row in copies if row['start_tick']<end and start<row['end_tick']]


def consecutive(slot_rows, scale):
    return (all((b.id-a.id)&MASK32==1 and b.flags==1 and
                11_000_000<=(b.b-a.b)*scale<=23_000_000 for a,b in zip(slot_rows,slot_rows[1:])) and
            all((row.b-row.a)*scale<=frames.MAX_EDGE_NS for row in slot_rows))


def calibrate(edges, paired, copies, scale):
    """Use stationary plateaus and isolated blanking copies to resolve 0/1-frame latch phase."""
    static = None
    witnesses = []
    conflicts = []
    modeled = 0
    for i in range(1,len(edges)-2):
        edge = edges[i]
        previous_slot = edges[i-1]
        trio = edges[i:i+3]
        reads = [paired.get(row.id) for row in trio]
        if not static and consecutive([previous_slot,*trio],scale) and all(row and row['agrees'] for row in reads):
            if len({row['signatures'][0] for row in reads})==1 and not copy_overlap(
                    copies,previous_slot.a,reads[-1]['ticks'][1][1]):
                static = dict(frames=[row.id for row in trio],signature=reads[0]['signatures'][0])
        if i<3:
            continue
        lane = edges[i-2:i+3]
        first_possible_scan = edges[i-3]
        if not consecutive([first_possible_scan,*lane],scale):
            continue
        reads = [paired.get(row.id) for row in lane]
        if not all(row and row['agrees'] for row in reads):
            continue
        # The previous frame was already in verified post-active blanking.
        # Keep a 1 ms margin before the lower edge bound of the next frame.
        intervals = copy_overlap(copies,first_possible_scan.a,reads[-1]['ticks'][1][1])
        if len(intervals)!=1:
            continue
        copy = intervals[0]
        if not (reads[1]['ticks'][0][1]<copy['start_tick'] and
                (edge.a-copy['end_tick'])*scale>=COPY_GUARD_NS):
            continue
        modeled += 1
        signatures = [row['signatures'][0] for row in reads]
        changes = [j for j in range(1,len(signatures)) if signatures[j]!=signatures[j-1]]
        if not changes:  # repainted identical content
            continue
        item = dict(expected_scan_frame=edge.id,observed_frames=[row.id for row in lane],
                    signature_changes=changes,copy=copy)
        if changes in ([2],[3]):
            witnesses.append(dict(item,sample_lag_frames=changes[0]-2))
        else:
            conflicts.append(item)
    lags = {row['sample_lag_frames'] for row in witnesses}
    qualified = bool(static and len(witnesses)>=3 and len(lags)==1 and not conflicts)
    return dict(qualified=qualified,lag_frames=next(iter(lags)) if qualified else None,
                stationary=static,isolated_copy_windows=modeled,witnesses=witnesses,conflicts=conflicts)


def summarize_windows(base, edges, paired, copies, phase, enabled, scale):
    slots = frames.indexed(edges,lambda row:row.id,'hardware frame count')
    lag = phase['lag_frames']
    ordered_copies = sorted(copies,key=lambda row:row['end_tick'])
    copy_ends = [row['end_tick'] for row in ordered_copies]
    reports = []
    for window in base.get('windows',[]):
        rows = [slots[edge['frame']] for edge in window['vblank_edges']]
        counts = Counter()
        outputs = []
        for left,right in zip(rows,rows[1:]):
            if not window['elapsed_ns_low']:
                break
            step = (right.id-left.id)&MASK32
            item = dict(frame=right.id,previous_frame=left.id,edge_lower_tick=right.a,edge_upper_tick=right.b)
            if not enabled or lag is None:
                item['reason'] = 'MISR-or-latch-unqualified'
            elif step!=1 or not consecutive((left,right),scale):
                item['reason'] = 'missing-or-unqualified-vblank'
            else:
                before,after = (paired.get((row.id+lag)&MASK32) for row in (left,right))
                if not before or not after or not before['agrees'] or not after['agrees']:
                    item['reason'] = 'missing-or-disagreeing-CRC'
                else:
                    # Use the physical scan, even when its signature latches
                    # in the next counter slot. Widen to a proved blank sample.
                    ends = [paired.get(row.id) for row in (left,right)]
                    if any(row is None for row in ends):
                        item['reason'] = 'missing-post-active-boundary'
                    else:
                        overlaps = []
                        for slot,read in zip((left,right),ends):
                            overlaps.extend(copy_overlap(copies,slot.a,read['ticks'][0][1]))
                        if overlaps:
                            item['reason'] = 'possible-mid-scan-copy'
                            item['overlapping_copies'] = list({row['seq']:row for row in overlaps}.values())
                        elif preceding := bisect_right(copy_ends,right.a):
                            item['preceding_copy_seq'] = ordered_copies[preceding-1]['seq']
                        item.update(crc=after['signatures'][0],previous_crc=before['signatures'][0],
                                    sample_frame=after['frame'],previous_sample_frame=before['frame'])
            kind = ('unknown' if 'reason' in item else
                    'repeated' if item['crc']==item['previous_crc'] else 'changed')
            counts[kind] += step
            if item.get('reason')=='possible-mid-scan-copy':
                counts['possible_copy_overlap'] += step
            outputs.append(dict(item,classification=kind,step=step))
        reports.append(dict(window,outputs=outputs,**{key:counts[key] for key in
            ('changed','repeated','unknown','possible_copy_overlap')}))
    for kind, original in (('active',base),('release',base.get('release_cadence',{}))):
        rows = [row for row in reports if row['window']==kind]
        counts = {key:sum(row[key] for row in rows) for key in ('changed','repeated','unknown','possible_copy_overlap')}
        refresh = original.get('hardware_refresh_hz_bounds')
        low = sum(row['elapsed_ns_low'] for row in rows)
        high = sum(row['elapsed_ns_high'] for row in rows)
        known = bool(enabled and phase['qualified'] and refresh and low and (counts['changed'] or counts['repeated']))
        complete = known and not counts['unknown']
        bounds = ([counts['changed']*1e9/high,(counts['changed']+counts['unknown'])*1e9/low] if known else None)
        intervals = [(b['edge_upper_tick']-a['edge_lower_tick'])*scale for row in rows
                     for changes in ([x for x in row['outputs'] if x['classification']=='changed'],)
                     for a,b in zip(changes,changes[1:])]
        original.update(**counts,complete_crc_coverage=complete,
                        scanout_content_fps_bounds=bounds if complete else None,
                        scanout_partial_coverage_fps_bounds=None if complete else bounds,
                        uninterrupted_60_fps_observed=bool(complete and not counts['repeated'] and
                                                           59<=refresh[0]<=refresh[1]<=61),
                        update_interval_upper_ns_p95=frames.quantile(intervals,.95) if complete else None,
                        update_interval_upper_ns_p99=frames.quantile(intervals,.99) if complete else None,
                        longest_update_interval_upper_ns=max(intervals,default=None) if complete else None)
    return reports


def analyze(text, joins, cores, *, preserve_data_preimage=False, extra_kinds=(), latch_calibration=None,
            join_tail_copy=False, offscreen_copy_end_ticks=()):
    rows, strokes, numer, denom = frames.parse(text,extra_kinds=extra_kinds)
    scale = numer/denom
    start = max(0,strokes[0][0]-25_000_000*denom//numer)
    end = strokes[-1][1]+scanout.RELEASE_NS*denom//numer
    if join_tail_copy:
        # The final scored frame's post-active CRC can overlap a copy
        # after the software cutoff. Extend joins only, not scored windows.
        next_edge = next((edge for edge in rows[frames.VBLANK] if edge.b>end),None)
        if next_edge and next_edge.flags==1 and (next_edge.b-end)*scale<=23_000_000:
            end = next_edge.b
    trace = frames.software(rows,joins,cores,start,end,numer,denom)
    gate = scanout.probe(text,read_only_counts_with_crc=True)
    read_only = gate.get('read_only_counter', {})
    motion = read_only.get('motion',{})
    frames.require('zero' in motion and motion['enabled']['samples']==0 and
                   any(p['gate']=='ok' and p['counter_enable']==0 for p in gate['checkpoints']),
                   '0349 requires successful read-only zero-control counter samples')
    edges = rows[frames.VBLANK]
    slots = frames.indexed(edges,lambda row:row.id,'hardware frame count')
    receipt = misr_receipts(text,gate,edges,scale,preserve_data_preimage=preserve_data_preimage)
    paired = paired_reads(rows[frames.CRC],slots,receipt,scale)
    if receipt['arm'] and receipt['arm']['writes']:
        frames.require(len(rows[frames.TIMING])==1 and
                       (rows[frames.TIMING][0].a,rows[frames.TIMING][0].b,rows[frames.TIMING][0].c)==(4910,32,2431) and
                       all(p['hsync']>>16==462 for p in gate['checkpoints'] if p['gate']=='ok'),
                       'MISR wrote outside the frozen geometry')
    # Use the exact 0348 decoder for vblank. Only the new wire describes CRC.
    base = scanout.hardware(gate,rows|{frames.CRC:[]},strokes,trace,numer,denom)
    layer_links = {(layer['surface'],layer['copy_start_tick'],layer['copy_end_tick']):
        dict(generation=attempt['generation'],attempt=attempt['attempt'],layer=layer)
        for attempt in trace for layer in attempt['layers']}
    copies = [dict(seq=row.seq,surface=row.id,start_tick=row.a,end_tick=row.b,
                   link=layer_links.get((row.id,row.a,row.b))) for row in rows[frames.COPY]]
    frames.require(all(0<row.a<row.b<=row.tick and 0<row.c<=frames.FRAME_BYTES for row in rows[frames.COPY]),
                   'malformed framebuffer copy interval')
    copies = [copy for copy in copies if copy['end_tick'] not in offscreen_copy_end_ticks]
    phase = (calibrate(edges,paired,copies,scale) if latch_calibration is None else
             latch_calibration(rows, strokes, paired, copies, scale))
    base['windows'] = summarize_windows(base,edges,paired,copies,phase,receipt['qualified'],scale)
    base.update(crc_scope='INTF1 output data in measured post-active blanking', optical_FPS_qualified=False)
    return dict(frame_trace_complete=True,matched_attempts=len(trace),dpu_probe=gate,hardware=base,
                misr=receipt,crc_frame_calibration=phase,raw_crc_pairs=list(paired.values()),
                core_linked_layers=sum('ticket' in layer for frame in trace for layer in frame['layers']),
                attempts=trace,strokes=strokes,tick_numer=numer,tick_denom=denom)
