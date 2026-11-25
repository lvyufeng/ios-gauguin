"""Decode native QuartzCore trace data and align exact swaps with physical scans."""

from base64 import b64decode
from collections import Counter, defaultdict
from dataclasses import dataclass
from struct import Struct
import re

from frame344_log import one, require


BEGIN, END, ANNOTATION, FRAME_INFO, HITCH, RENDER_TIME, VSYNC, VSYNC_UPDATE = range(1, 9)
ENCODE_BEGIN, ENCODE_END, SERVER_THREAD, DID_COMMIT, DRIVER_TARGET, DRIVER_DELIVERY = range(9, 15)
FIELDS = {BEGIN: Struct('<I'), END: Struct('<'), ANNOTATION: Struct('<II'),
          FRAME_INFO: Struct('<IQQQ'), HITCH: Struct('<IQQQ'), RENDER_TIME: Struct('<Q'),
          VSYNC: Struct('<'), VSYNC_UPDATE: Struct('<'), ENCODE_BEGIN: Struct('<'),
          ENCODE_END: Struct('<'), SERVER_THREAD: Struct('<II'), DID_COMMIT: Struct('<'),
          DRIVER_TARGET: Struct('<IQQQ'), DRIVER_DELIVERY: Struct('<IQQQ')}
NAMES = dict(zip(FIELDS, ('render_begin', 'render_end', 'swap_annotation', 'frame_info',
                          'hitch', 'render_time', 'compat_vsync', 'compat_vsync_update',
                          'SpringBoard_encode_begin', 'SpringBoard_encode_end', 'BackBoard_server_thread',
                          'BackBoard_did_commit', 'driver_target', 'driver_delivery'), strict=True))
HEADER = re.compile(r'H: version=([12]) active=1 start=(\d+) end=(\d+) captured=(\d+)')
FOOTER = re.compile(r'F: rows=(\d+) threads=(\d+) bytes=(\d+) lost=0')
THREAD = re.compile(r'T (\d+) ([0-9a-f]{1,16})')
BLOCK = re.compile(r'B (\d+) (\d+) ([A-Za-z0-9+/]+={0,2})')
ROW = Struct('<IBB')
EVENT_LIMIT, WIRE_LIMIT = 16384, 210000
NO_TIMESTAMP = {0, 0xffffffff, 0xffffffffffffffff}


@dataclass(frozen=True)
class Event:
    tick: int
    thread: int
    kind: int
    args: tuple


def decode(raw, start, end):
    """Read the independent trace envelope, checking every record and loss count."""
    prefix = 'SWEET F374 '
    records = [line[len(prefix):] for line in raw.splitlines() if line.startswith(prefix)]
    require(len(records) >= 3 and HEADER.fullmatch(records[0]) and FOOTER.fullmatch(records[-1]),
            'missing, stopped, or lossy native CA trace')
    version, left, right, captured = map(int, HEADER.fullmatch(records[0]).groups())
    count, thread_count, expected_bytes = map(int, FOOTER.fullmatch(records[-1]).groups())
    require((left, right) == (start, end) and 0 < end-start <= 0xffffffff and
            0 < captured == count <= EVENT_LIMIT and 0 < thread_count <= 256 and
            0 < expected_bytes <= WIRE_LIMIT, 'native CA scope or packet size differs')
    threads, events = [], []
    seen_threads, used_threads = set(), set()
    total = 0
    for record in records[1:-1]:
        thread = THREAD.fullmatch(record)
        if thread:
            index, tid = int(thread[1]), int(thread[2], 16)
            require(index == len(threads) < thread_count and tid and tid not in seen_threads,
                    'invalid native CA thread dictionary')
            seen_threads.add(tid)
            threads.append(tid)
            continue
        batch = BLOCK.fullmatch(record)
        require(batch is not None, 'unknown native CA packet')
        ordinal, rows = int(batch[1]), int(batch[2])
        require(ordinal == len(events) and 0 < rows <= 32 and ordinal + rows <= count and
                (rows == 32 or ordinal + rows == count) and len(batch[3]) <= 1452,
                'native CA packet ordinal or bound differs')
        packed = b64decode(batch[3], validate=True)
        total += len(packed)
        require(total <= expected_bytes, 'native CA wire size exceeded')
        offset = 0
        for _ in range(rows):
            require(offset + ROW.size <= len(packed), 'truncated native CA row')
            tick, kind, tid = ROW.unpack_from(packed, offset)
            offset += ROW.size
            layout = FIELDS.get(kind)
            require(layout is not None and (version == 2 or kind <= VSYNC_UPDATE) and
                    offset + layout.size <= len(packed) and
                    tick < end-start and tid < len(threads), 'invalid native CA row')
            events.append(Event(start + tick, threads[tid], kind, layout.unpack_from(packed, offset)))
            used_threads.add(tid)
            offset += layout.size
        require(offset == len(packed), 'trailing bytes in native CA block')
    require(len(events) == count and len(threads) == len(used_threads) == thread_count and
            total == expected_bytes, 'native CA trace totals differ')
    return sorted(events, key=lambda row: row.tick)


def envelope(raw):
    values = one(r'^SWEET F344 H: count=\d+ reason=1 lost=0 start=(\d+) end=(\d+) numer=(\d+) denom=(\d+)$',
                 raw, 'matching lossless F344 envelope')
    return tuple(map(int, values))


def render_spans(events):
    active = defaultdict(list)
    spans = defaultdict(list)
    for row in events:
        if row.kind == BEGIN:
            active[row.thread].append((row, []))
        elif row.kind == ANNOTATION and active[row.thread]:
            active[row.thread][-1][1].append(row)
        elif row.kind == END and active[row.thread]:
            begin, annotations = active[row.thread].pop()
            for annotation in annotations:
                spans[(row.thread, annotation.tick, annotation.args)].append((begin, row))
    return spans


def link_swaps(events, swaps, start, end, n, d):
    """Use exact swap IDs and render thread. Keep unavailable fields explicit."""
    by_swap = defaultdict(lambda: defaultdict(list))
    for row in events:
        if row.kind in (ANNOTATION, FRAME_INFO, HITCH):
            by_swap[row.args[0]][row.kind].append(row)
    unique_ids = Counter(row['client_swap_id'] for row in swaps)
    spans = render_spans(events)
    margin = 2_000_000_000*d//n
    max_allowance = 1_000_000_000*d//n

    def timestamp(value):
        return value if value not in NO_TIMESTAMP and start-margin <= value < end+margin else None

    links = {}
    for swap in swaps:
        swap_id, generation, thread = (swap[key] for key in ('client_swap_id', 'generation', 'begin_thread'))
        begin_tick = swap['begin_tick']
        require(generation not in links, 'duplicate platform swap generation')
        if not swap_id or unique_ids[swap_id] != 1:
            continue
        group = by_swap.get(swap_id, {})
        notes = [e for e in group.get(ANNOTATION, ()) if e.thread == thread]
        render = None
        if len(notes) == 1:
            note, = notes
            matching = [(a.tick, b.tick, a.args[0]) for a,b in spans.get((thread, note.tick, note.args), ())
                        if a.tick <= begin_tick <= b.tick]
            if len(matching) == 1:
                render = dict(begin_tick=matching[0][0], end_tick=matching[0][1], display_id=matching[0][2],
                              frame_seed=note.args[1], annotation_tick=note.tick)
        info, hitch = None, None
        info_values = {(earliest, actual, target) for e in group.get(FRAME_INFO, ()) if begin_tick <= e.tick
                       for _,earliest,actual,target in (e.args,)
                       if any(timestamp(value) is not None for value in (earliest, actual, target))}
        if len(info_values) == 1:
            earliest, actual, target = map(timestamp, next(iter(info_values)))
            info = dict(earliest_tick=earliest, actual_tick=actual, requested_tick=target)
        hitch_values = set()
        for event in group.get(HITCH, ()):
            _, allowable, actual, earliest = event.args
            if (begin_tick <= event.tick and 0 < allowable <= max_allowance and
                timestamp(actual) is not None and timestamp(earliest) is not None and
                actual > earliest + allowable and
                (info is None or (info['actual_tick'], info['earliest_tick']) == (actual, earliest))):
                hitch_values.add((earliest, allowable, actual))
        if len(hitch_values) == 1:
            earliest, allowable, actual = next(iter(hitch_values))
            hitch = dict(earliest_tick=earliest, allowance_ticks=allowable, expected_tick=earliest+allowable,
                         actual_tick=actual, late_ticks=actual-earliest-allowable)
        if render or info or hitch:
            links[generation] = dict(generation=generation, client_swap_id=swap_id, begin_tick=begin_tick,
                                     render=render, system_frame_info=info, system_hitch=hitch)
    return links


def align_scans(windows, attempts, certificates, edges, links, n, d):
    """Map a certified blanking copy to the subsequent scan of that exact generation."""
    by_scan = defaultdict(list)
    by_attempt = {row['attempt']: row for row in attempts}
    for key, proof in certificates.items():
        attempt_id, surface, first, last = key
        scan = (proof['frame']+1) & 0xffffffff
        attempt = by_attempt[attempt_id]
        by_scan[scan].append(dict(attempt=attempt_id, generation=attempt['generation'], surface=surface,
                                  copy_start_tick=first, copy_end_tick=last))

    def delta_bounds(edge, tick):
        return [(edge.a-tick)*n/d, (edge.b-tick)*n/d] if edge and tick is not None else None

    output = []
    for name, window in windows:
        for row in window['intervals']:
            frame = row['frame']
            scan = dict(workload=name, stroke=window['stroke'], phase=window['phase'], frame=frame,
                        crc=row['after_copy_boundary_check'])
            layer = by_scan[frame]
            edge = edges.get(frame)
            scan['vblank_ticks'] = [edge.a,edge.b] if edge and edge.flags == 1 else None
            if len(layer) == 1 and scan['vblank_ticks']:
                scan.update(layer[0])
                link = links.get(scan['generation'])
                if link:
                    scan['native_swap_id'] = link['client_swap_id']
                    info = link['system_frame_info'] or {}
                    hitch = link['system_hitch'] or {}
                    actual = info.get('actual_tick') or hitch.get('actual_tick')
                    requested = info.get('requested_tick')
                    scan.update(requested_tick=requested, system_actual_tick=actual,
                                system_hitch_deadline_tick=hitch.get('expected_tick'),
                                scan_minus_requested_ns_bounds=delta_bounds(edge,requested),
                                scan_minus_system_actual_ns_bounds=delta_bounds(edge,actual))
            output.append(scan)
    return output


def capture_summary(events, strokes, motion, links, scans):
    kinds = Counter(NAMES[row.kind] for row in events)
    windows = [*strokes, motion]
    coverage = [dict(render_begins=sum(left<=r.tick<right and r.kind==BEGIN for r in events),
                     compatibility_vsync=sum(left<=r.tick<right and r.kind==VSYNC for r in events))
                for left, right in windows]
    # A swipe may legitimately produce no render. The software-vsync stream proves the observer was live.
    complete = len(strokes) == 13 and all(w['compatibility_vsync'] for w in coverage)
    groups = {name: [r for r in scans if r['workload']==name and r['phase']=='active']
              for name in ('ordinary', 'slow_drag')}
    physical = {name: dict(scans=len(rows), crc=dict(Counter(r['crc'] for r in rows)),
                           exact_native_swaps=sum('native_swap_id' in r for r in rows),
                           requested=sum(r.get('requested_tick') is not None for r in rows),
                           system_actual=sum(r.get('system_actual_tick') is not None for r in rows),
                           system_and_physical=sum(r.get('scan_minus_system_actual_ns_bounds') is not None
                                                   for r in rows))
                for name,rows in groups.items()}
    return dict(native_capture_covers_workloads=complete, events=dict(kinds), workload_coverage=coverage,
                exact_swap_links=len(links), native_render_spans=sum(bool(r['render']) for r in links.values()),
                exact_system_hitches=sum(bool(r['system_hitch']) for r in links.values()), physical=physical)
