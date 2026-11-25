"""Qualify scanout and correlate the frozen swipes with the software frame trace."""

from bisect import bisect_right
import re

import frame344_log as frames


GATES = ('ok', 'software-display', 'gcc-ahb-halted', 'display-ahb-halted',
         'display-mdp-halted', 'revision', 'video-inactive', 'counters-disabled',
         'geometry', 'geometry-changed')
RELEASE_NS = 250_000_000
CRC_START_LINE = 128
CRC_STOP_LINE = 1536


def counter_probe(text, terminal_poll, crc):
    rows = re.findall(r'^SWEET F346 COUNTER: (.*)$', text, re.M)
    if not rows:
        return None
    frames.require(len(rows) == 2, 'counter arm and cleanup must each occur once')
    arm = re.fullmatch(r'arm poll=(\d+) preimage=0 readback=([0-9a-f]{1,8})', rows[0])
    cleanup = re.fullmatch(r'cleanup poll=(\d+) readable=([01]) before=([0-9a-f]{1,8}) after=([0-9a-f]{1,8})', rows[1])
    frames.require(arm is not None and cleanup is not None, 'invalid frame/line counter receipt')
    poll, readback = int(arm[1]), int(arm[2], 16)
    readable = cleanup[2] == '1'
    before, after = int(cleanup[3], 16), int(cleanup[4], 16)
    frames.require(2 <= poll <= terminal_poll == int(cleanup[1]) and
                   (readable or before == after == 0xffffffff) and
                   (crc is None or (readback == 3 and poll < crc['poll'])),
                   'counter receipt differs from the capture order')
    return dict(arm_poll=poll, enable_readback=readback, cleanup_readable=readable,
                cleanup_before=before, cleanup_after=after, restored=readable and after == 0)


def counter_motion(text, readonly, terminal_poll):
    lines = re.findall(r'^SWEET F348 MOTION: (.*)$',text,re.M)
    if not lines:
        return None
    frames.require(len(lines)==1 and readonly is not None, 'motion without one read-only capture')
    fields = re.fullmatch(r'zero=((?:\d+,){4}\d+) enabled=((?:\d+,){4}\d+) rejected_control=(\d+)',lines[0])
    frames.require(fields is not None, 'invalid read-only counter motion')
    lanes = {}
    for name,encoded in zip(('zero','enabled'),fields.groups()[:2]):
        samples,pairs,frame_changes,line_changes,line_wraps = map(int,encoded.split(','))
        frames.require(pairs<=max(0,samples-1) and frame_changes<=pairs and line_wraps<=line_changes<=pairs,
                       'read-only counter changes exceed compared samples')
        lanes[name] = dict(samples=samples,compared_pairs=pairs,frame_changes=frame_changes,
                           line_changes=line_changes,line_wraps=line_wraps)
    rejected = int(fields[3])
    frames.require(lanes['zero']['samples']+lanes['enabled']['samples']==readonly['samples'] and
                   readonly['samples']+rejected<=terminal_poll,
                   'read-only motion totals differ from accepted samples')
    return dict(lanes,rejected_control=rejected)


def probe(text, *, read_only_counts_with_crc=False):
    pattern = (
        r'^SWEET F345 G: poll=(\d+) gate=(\d+) seen=([0-9a-f]+) display=(\d+) gcc=([0-9a-f]+)'
        r' ahb=([0-9a-f]+) mdp=([0-9a-f]+) rev=([0-9a-f]+) live=([0-9a-f]+) en=([0-9a-f]+)'
        r' counter=([0-9a-f]+) hsync=([0-9a-f]+) period=([0-9a-f]+) start=([0-9a-f]+) end=([0-9a-f]+)$'
    )
    rows = []
    previous = 0
    for fields in re.findall(pattern,text,re.M):
        poll, gate = map(int,fields[:2])
        seen, display = int(fields[2],16), int(fields[3])
        values = [int(item,16) for item in fields[4:]]
        frames.require(previous < poll <= 40960 and gate < len(GATES) and seen in (0,1,3,7,15,31),
                       'invalid DPU route snapshot')
        previous = poll
        names = ('gcc', 'ahb', 'mdp', 'revision', 'video_status', 'timing_engine_enable',
                 'counter_enable', 'hsync', 'vperiod_pixels', 'vstart_pixels', 'vend_pixels')
        masks = (1,2,2,4,8,8,8,16,16,16,16)
        rows.append(dict(poll=poll, gate=GATES[gate], software_display=display,
                         **{key:value if seen & bit else None for key,value,bit in zip(names,values,masks)}))
    state, polls, configured, restored, gate = frames.one(
        r'^SWEET F345 DPU: stopped=([a-z]+) polls=(\d+) configured=([01]) restored=([01]) gate=(\d+)$',
        text,'0345 DPU stop result')
    polls, gate = int(polls), int(gate)
    frames.require(gate < len(GATES) and previous <= polls <= 40960 and
                   ((not polls and not rows) or (rows and rows[0]['poll']==1)),
                   '0345 DPU first or terminal checkpoint missing')
    arm = re.findall(r'^SWEET F345 CRC: poll=(\d+) frame=(\d+) preimage=([0-9a-f]+) line=(\d+)$',text,re.M)
    timed_out = re.findall(r'^SWEET F345 CRC: edge qualification expired at poll=(\d+)$',text,re.M)
    if read_only_counts_with_crc:
        frames.require(not arm and not timed_out, 'legacy MISR receipt in blanking capture')
    else:
        frames.require(len(arm)+len(timed_out)<=1 and
                       (configured=='0' or bool(arm and int(arm[0][2],16)==0)),
                       'MISR arm state differs from its preimage')
    crc = None
    if arm:
        poll, number, reg, line = arm[0]
        frames.require(0<int(poll)<=polls and 0<=int(number)<=0xffffffff and 0<=int(line)<6000,
                       'invalid MISR arm checkpoint')
        crc = dict(poll=int(poll),frame=int(number),control_preimage=int(reg,16),line=int(line))
    result = dict(stopped=state,polls=polls,configured=configured=='1',restored=restored=='1',
                  gate=GATES[gate],checkpoints=rows,crc_arm=crc,
                  crc_edge_qualification_expired=bool(timed_out))
    counter = counter_probe(text, polls, crc)
    if counter is not None:
        result['frame_line_counter'] = counter
    readonly = re.findall(r'^SWEET F347 RO: (.*)$', text, re.M)
    if readonly:
        frames.require(len(readonly)==1 and not counter and not crc and not timed_out and
                       (read_only_counts_with_crc or configured=='0'),
                       'read-only scanout has an unexpected write receipt')
        fields = re.fullmatch(r'samples=(\d+) first_frame=(\d+) first_line=(\d+) last_frame=(\d+) last_line=(\d+)',
                              readonly[0])
        frames.require(fields is not None, 'malformed read-only counter observations')
        samples, first_frame, first_line, last_frame, last_line = map(int,fields.groups())
        frames.require(samples<=polls and max(first_frame,last_frame)<=0xffffffff and
                       max(first_line,last_line)<6000 and
                       (samples or not any((first_frame,first_line,last_frame,last_line))),
                       'out-of-range read-only counter observations')
        result['read_only_counter'] = dict(samples=samples,first_frame=first_frame,first_line=first_line,
                                          last_frame=last_frame,last_line=last_line)
    motion = counter_motion(text,result.get('read_only_counter'),polls)
    if motion is not None:
        result['read_only_counter']['motion'] = motion
    return result


def windows(strokes, numer, denom):
    for ordinal,(begin,release) in enumerate(strokes):
        yield ordinal,'active',begin,release
        next_begin = strokes[ordinal+1][0] if ordinal+1<len(strokes) else release+RELEASE_NS*denom//numer
        yield ordinal,'release',release,min(next_begin,release+RELEASE_NS*denom//numer)


def hardware(gate, rows, strokes, trace, numer, denom):
    scale = numer/denom
    counter = gate.get('frame_line_counter')
    frames.require(counter is None or counter['enable_readback'] == 3,
                   'frame/line counter enable was not confirmed')
    frames.require(len(rows[frames.TIMING])==1, 'one stable active DPU geometry required')
    geometry = rows[frames.TIMING][0]
    frames.require(geometry.c-geometry.b==2399 and geometry.c<geometry.a<=6000,
                   'invalid active DPU geometry')
    edges = rows[frames.VBLANK]
    crcs = frames.indexed(rows[frames.CRC], lambda row:row.id,'CRC frame')
    readonly = gate.get('read_only_counter')
    if readonly:
        frames.require(not crcs and readonly['samples'] and len(edges) < readonly['samples'] and
                       max(readonly['first_line'],readonly['last_line'])<geometry.a and
                       (not edges or edges[-1].id==readonly['last_frame']),
                       'read-only frame edges differ from sampled counters')
    known = frames.indexed(edges,lambda row:row.id,'hardware frame count')
    arm = gate['crc_arm']
    frames.require(not crcs or (gate['configured'] and arm and arm['frame'] in known),
                   'CRC present without qualified arm edge')
    if arm and gate['configured']:
        edge = known.get(arm['frame'])
        frames.require(edge and edge.flags==1 and edge.c==arm['line'] and edge.c<geometry.a/4,
                       'CRC arm did not follow a low-line hardware edge')
    for edge in edges:
        frames.require(0<edge.a<edge.b<=edge.tick and edge.c<geometry.a,'invalid hardware edge bracket')
    for number, sample in crcs.items():
        slot = known.get(number)
        following = known.get((number+1)&0xffffffff)
        frames.require(slot and slot.b<=sample.tick and (not following or sample.tick<=following.b) and
                       sample.c==frames.CRC_CONTROL and sample.flags in (0,1) and sample.a<=0xffffffff and
                       geometry.b+CRC_START_LINE<=sample.b<geometry.b+CRC_STOP_LINE and
                       ((number-arm['frame'])&0xffffffff)>=2,'CRC outside its stable hardware sampling phase')

    copied = sorted((layer['copy_start_tick'],layer['copy_end_tick'],frame['generation'])
                    for frame in trace for layer in frame['layers'])
    done = sorted((b,a,generation) for a,b,generation in copied)
    copy_ends = [x[0] for x in done]
    reports = []
    for ordinal, kind, begin, end in windows(strokes,numer,denom):
        selected = [slot for slot in edges if begin<=slot.a and slot.b<=end]
        report = dict(stroke=ordinal, window=kind, start_tick=begin, end_tick=end,
                      changed=0, repeated=0, unknown=0, edges=0, possible_copy_overlap=0,
                      elapsed_ns_low=0, elapsed_ns_high=0, outputs=[])
        if readonly:
            report['vblank_edges'] = [dict(frame=edge.id,step=edge.flags,
                edge_lower_tick=edge.a,edge_upper_tick=edge.b,line=edge.c) for edge in selected]
        if len(selected)<2:
            reports.append(report)
            continue
        report['elapsed_ns_low'] = max(0,(selected[-1].a-selected[0].b)*scale)
        report['elapsed_ns_high'] = (selected[-1].b-selected[0].a)*scale
        for left,right in zip(selected,selected[1:]):
            step = (right.id-left.id)&0xffffffff
            elapsed = (right.b-left.b)*scale
            safe = (step==right.flags and 0<step and step*11_000_000<=elapsed<=step*23_000_000)
            if not safe:
                report['elapsed_ns_low'] = 0
                break
            report['edges'] += step
            before,after = crcs.get(left.id),crcs.get(right.id)
            if (step!=1 or not before or not after or before.flags or after.flags or
                max(left.b-left.a,right.b-right.a)*scale>frames.MAX_EDGE_NS):
                report['unknown'] += step
                continue
            changed = before.a!=after.a
            report['changed' if changed else 'repeated'] += 1
            # A latched signature read early in the new counter slot can
            # refer to the preceding scan. Attribute only if every possible
            # concurrent copy is excluded from the transition bracket.
            previous = known.get((left.id-1)&0xffffffff)
            lower = previous.a if previous else left.a
            following = known.get((right.id+1)&0xffffffff)
            upper = following.b if following else end
            overlaps = sorted({generation for a,b,generation in copied if a<upper and lower<b})
            report['possible_copy_overlap'] += bool(overlaps)
            preceding = bisect_right(copy_ends,lower)
            report['outputs'].append(dict(frame=right.id,edge_lower_tick=right.a,edge_upper_tick=right.b,
                scanout_crc=after.a,changed=changed,possible_copy_generations=overlaps,
                prior_copied_generation=done[preceding-1][2] if preceding and not overlaps else None))
        reports.append(report)

    def summarize(rows):
        available = all(item['elapsed_ns_low']>0 for item in rows)
        elapsed_low = sum(item['elapsed_ns_low'] for item in rows)
        elapsed_high = sum(item['elapsed_ns_high'] for item in rows)
        counts = {key:sum(item[key] for item in rows)
                  for key in ('edges','changed','repeated','unknown','possible_copy_overlap')}
        enough = bool(available and elapsed_low and counts['edges'] and gate['stopped']=='deadline' and gate['gate']=='ok')
        refresh = [counts['edges']*1e9/elapsed_high,counts['edges']*1e9/elapsed_low] if enough else None
        counter_restored = counter is None or counter['restored']
        crc_observed = enough and gate['configured'] and gate['restored'] and counter_restored and counts['changed']>0
        complete = crc_observed and not counts['unknown']
        crc_bounds = ([counts['changed']*1e9/elapsed_high,
                        (counts['changed']+counts['unknown'])*1e9/elapsed_low] if crc_observed else None)
        intervals = [(b['edge_upper_tick']-a['edge_lower_tick'])*scale for row in rows
                     for changes in ([x for x in row['outputs'] if x['changed']],)
                     for a,b in zip(changes,changes[1:])]
        return dict(**counts,usable_windows=sum(item['elapsed_ns_low']>0 for item in rows),
            total_windows=len(rows),hardware_refresh_hz_bounds=refresh,complete_crc_coverage=complete,
            scanout_content_fps_bounds=crc_bounds if complete else None,
            scanout_partial_coverage_fps_bounds=None if complete else crc_bounds,
            update_interval_upper_ns_p95=frames.quantile(intervals,.95) if complete else None,
            update_interval_upper_ns_p99=frames.quantile(intervals,.99) if complete else None,
            longest_update_interval_upper_ns=max(intervals,default=None) if complete else None,
            uninterrupted_60_fps_observed=bool(complete and not counts['repeated'] and
                not counts['possible_copy_overlap'] and refresh and 59<=refresh[0]<=refresh[1]<=61))

    cadence = {kind:summarize([item for item in reports if item['window']==kind])
               for kind in ('active','release')}
    return dict(**cadence['active'], release_cadence=cadence['release'], windows=reports,
                crc_scope='latched DPU output signature near the beginning of the observed hardware counter slot',
                optical_FPS_qualified=False)


def analyze(text, joins, cores):
    rows, strokes, numer, denom = frames.parse(text)
    before = max(0,strokes[0][0]-25_000_000*denom//numer)
    end = strokes[-1][1]+RELEASE_NS*denom//numer
    trace = frames.software(rows,joins,cores,before,end,numer,denom)
    gate = probe(text)
    try:
        report = hardware(gate,rows,strokes,trace,numer,denom)
    except ValueError as error:
        report = dict(complete_crc_coverage=False,hardware_refresh_hz_bounds=None,
                      scanout_content_fps_bounds=None,uninterrupted_60_fps_observed=False,reason=str(error))
    return dict(frame_trace_complete=True,matched_attempts=len(trace),dpu_probe=gate,hardware=report,
                core_linked_layers=sum('ticket' in layer for frame in trace for layer in frame['layers']),
                attempts=trace,strokes=strokes,tick_numer=numer,tick_denom=denom)
