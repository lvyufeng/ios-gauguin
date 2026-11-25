"""Validate the 0344 frame capture and join device scanout to software work."""

from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
import math
import re


SWAP, ATTEMPT, RESULT, LOCK, COPY, ISSUE, WRITER, EOP, READY, VBLANK, CRC, TIMING = range(40, 52)
SWAP_TIMING = 62
SWAP_WAIT = 63
LOCK_SURFACE_RESERVATION = 3
LOCK_ACCEPTED = (2, LOCK_SURFACE_RESERVATION)
FRAME_BYTES = 1080 * 2400 * 4
CRC_CONTROL = 0x81000301
MAX_EDGE_NS = 4_000_000


@dataclass(frozen=True)
class Event:
    seq: int
    tick: int
    kind: int
    id: int
    flags: int
    a: int
    b: int
    c: int


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def one(pattern, text, label):
    rows = re.findall(pattern, text, re.M)
    require(len(rows) == 1, 'expected one ' + label)
    return rows[0]


def indexed(rows, key, label):
    output = {}
    for row in rows:
        index = key(row)
        require(index not in output, 'duplicate ' + label)
        output[index] = row
    return output


def parse(text, *, extra_kinds=()):
    header = one(r'^SWEET F344 H: count=(\d+) reason=(\d+) lost=(\d+) start=(\d+) end=(\d+) numer=(\d+) denom=(\d+)$',
                 text, 'frame capture header')
    count, reason, lost, start, end, numer, denom = map(int, header)
    footer = one(r'^SWEET F344 F: count=(\d+) lost=(\d+)$', text, 'frame capture footer')
    capacity = 16384
    if 60 in extra_kinds:  # F358 probe capture
        require(one(r'^SWEET F344: armed window=45s capacity=(\d+)$', text, 'F358 frame capacity')=='20480' and
                one(r'^SWEET F358 PROBE: first_line=(\d+) limit=(\d+)$', text, 'F358 probe scope')==('1728','1024'),
                'F358 frame capacity or probe scope differs')
        capacity = 20480
    require(0 < count < capacity and reason == 1 and not lost and list(map(int, footer)) == [count, 0],
            'frame capture dropped, wrapped or ended early')
    require(0 < start < end and numer > 0 and denom > 0 and
            abs((end - start) * numer - 45_000_000_000 * denom) <= numer, 'invalid frame timebase')
    event_lines = re.findall(r'^(?:SWEET F344 E |F344E )(.*)$', text, re.M)
    require(len(event_lines) == count, 'frame capture row count differs')
    rows = defaultdict(list)
    for seq, line in enumerate(event_lines, 1):
        fields = line.split()
        require(len(fields) == 8 and all(re.fullmatch('[0-9a-f]{1,16}', field) for field in fields),
                'malformed frame record')
        row = Event(*[int(field, 16) for field in fields])
        require(row.seq == seq and start <= row.tick < end and
                row.kind in (1, *range(SWAP, TIMING + 1), SWAP_TIMING, SWAP_WAIT, *extra_kinds),
                'invalid frame sequence, kind or tick')
        rows[row.kind].append(row)
    require(len(rows.get(SWAP_TIMING, ())) <= 1024, 'unbounded swap timing events')
    require(len(rows.get(SWAP_WAIT, ())) <= 384, 'unbounded SwapWait events')
    require(len(rows[1]) == 1, 'missing or repeated display settle trigger')
    for group in rows.values():
        group.sort(key=lambda row: (row.tick, row.seq))
    first = re.findall(r'^SWEET UI SCRIPT: begin stroke=(\d+) tick=(\d+) origin=synthetic$', text, re.M)
    last = re.findall(r'^SWEET UI SCRIPT: end stroke=(\d+) tick=(\d+) events=34; HID return only$', text, re.M)
    for boundaries in (first, last):
        require([int(i) for i, _ in boundaries] == list(range(13)), 'expected all 13 scripted strokes')
    one(r'^(SWEET UI SCRIPT: complete strokes=13 events=442;.*)$', text, 'script completion')
    strokes = [(int(a), int(b)) for (_, a), (_, b) in zip(first, last)]
    require(all(start < a < b < end for a, b in strokes) and
            all(left[1] < right[0] for left, right in zip(strokes, strokes[1:])), 'script outside frame capture')
    return rows, strokes, numer, denom


def software(rows, joined_submits, core_rows, begin_tick, end_tick, numer, denom):
    scale = numer / denom
    submits = indexed(joined_submits, lambda row: row['kernel_token'], 'IO token')
    cores = indexed(core_rows, lambda row: (row['queue'], row['ticket'], row['job']), 'core job')
    issued = indexed(rows[ISSUE], lambda row: row.id, 'native fence')
    eop = indexed(rows[EOP], lambda row: row.id, 'EOP')
    ready = indexed(rows[READY], lambda row: row.id, 'surface ready')
    swaps = indexed(rows[SWAP], lambda row: row.id, 'swap generation')
    results = indexed(rows[RESULT], lambda row: row.id, 'present result')
    expect_tokens = set(submits)
    seen_tokens = set()
    for issue in issued.values():
        submit = submits.get(issue.a)
        if submit is None:
            continue  # a submit outside the matched workload
        require(issue.a not in seen_tokens and (issue.b, issue.c) == (submit['driver_queue'], submit['driver_fence']),
                'IO and native fence identities disagree')
        seen_tokens.add(issue.a)
    require(expect_tokens and expect_tokens == seen_tokens, 'matched Core submits lack a native fence receipt')

    writers = defaultdict(list)
    for writer in rows[WRITER]:
        issue = issued.get(writer.id)
        require(issue is not None and issue.tick <= writer.tick and writer.a, 'writer without a native issue')
        writers[writer.a].append(writer)
    writer_ticks = {surface: [row.tick for row in values] for surface, values in writers.items()}
    trace = []
    starts = indexed(rows[ATTEMPT], lambda row: row.id, 'present attempt')
    locks = rows[LOCK]
    copies = rows[COPY]
    lock_ticks = [row.tick for row in locks]
    copy_ticks = [row.tick for row in copies]
    last_end = 0
    for attempt in starts.values():
        if not begin_tick <= attempt.tick < end_tick:
            continue
        result = results.get(attempt.id)
        swap = swaps.get(attempt.a)
        require(result is not None and last_end <= attempt.tick <= result.tick, 'missing or overlapping present result')
        require(swap is not None and swap.tick <= attempt.tick and (swap.a, swap.b) == (attempt.b, attempt.c),
                'present and swap identity disagree')
        last_end = result.tick
        acquired = locks[bisect_left(lock_ticks, attempt.tick):bisect_right(lock_ticks, result.tick)]
        written = copies[bisect_left(copy_ticks, attempt.tick):bisect_right(copy_ticks, result.tick)]
        require(all(attempt.tick <= row.a <= row.b <= row.c <= row.tick and row.flags in (0, *LOCK_ACCEPTED)
                    for row in acquired), 'bad read-lock interval')
        require(all(attempt.tick <= row.a <= row.b <= row.tick and 0 < row.c <= FRAME_BYTES and row.flags < 4
                    for row in written), 'bad copy interval')
        require(sum(row.c for row in written) == result.a and sum(row.flags == 0 for row in acquired) == result.b,
                'copy or guard totals differ')
        layers = []
        for copy in written:
            matching = [lock for lock in acquired if lock.id == copy.id and lock.flags in LOCK_ACCEPTED and lock.c <= copy.a]
            require(matching, 'copy has no completed guard')
            guard = matching[-1]
            item = dict(surface=copy.id, bytes=copy.c, copy_start_tick=copy.a, copy_end_tick=copy.b,
                        copy_ns=(copy.b - copy.a) * scale, lock_wait_ns=(guard.b - guard.a) * scale,
                        ready_check_ns=(guard.c - guard.b) * scale)
            latest = bisect_right(writer_ticks.get(copy.id, []), guard.b) - 1
            if latest >= 0:
                writer = writers[copy.id][latest]
                issue = issued[writer.id]
                end, available = eop.get(writer.id), ready.get(writer.id)
                visible_by = guard.b if guard.flags == LOCK_SURFACE_RESERVATION else guard.c
                require(end and available and writer.tick <= end.tick <= available.tick <= visible_by,
                        'read precedes the observed producer fence or surface readiness')
                item.update(native_fence=writer.id, eop_observed_tick=end.tick, surface_ready_tick=available.tick)
                submission = submits.get(issue.a)
                if submission:
                    queue_ticket = {k: submission[k] for k in ('queue', 'ticket', 'job')}
                    core = cores[tuple(queue_ticket.values())]
                    item.update(**queue_ticket, core_wait_us=core['core_queue_wait_us'],
                                core_start_ns=core['start_ns'])
            layers.append(item)
        trace.append(dict(generation=attempt.a, attempt=attempt.id, swap=attempt.b, retry=attempt.flags,
                          swap_tick=swap.tick, attempt_tick=attempt.tick, result_tick=result.tick,
                          ready=bool(result.flags), refused_guards=result.b, layers=layers))
    require(trace, 'no present attempts in the matched workload')
    return trace


def quantile(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * percentile) - 1)]


def hardware(text, rows, strokes, trace, numer, denom):
    scale = numer / denom
    status = one(r'^SWEET F344 DPU: stopped=([a-z]+) polls=(\d+) configured=([01]) restored=([01])$',
                 text, 'DPU probe result')
    require(status[0] == 'deadline' and status[2:] == ('1', '1'), 'DPU probe did not complete and restore its control register')
    require(len(rows[TIMING]) == 1, 'missing DPU timing geometry')
    geometry = rows[TIMING][0]
    require(geometry.c - geometry.b == 2399 and geometry.c < geometry.a, 'wrong DPU active geometry')
    crc = indexed(rows[CRC], lambda row: row.id, 'CRC frame')
    slots = rows[VBLANK]
    have = indexed(slots, lambda row: row.id, 'hardware frame counter')
    for slot in slots:
        require(0 < slot.a < slot.b <= slot.tick and slot.c < geometry.a, 'invalid vblank edge bracket')
    for identifier, sample in crc.items():
        slot = have.get(identifier)
        require(slot and slot.b <= sample.tick and sample.c == CRC_CONTROL and sample.a <= 0xffffffff and
                geometry.b + 128 <= sample.b < geometry.b + 768, 'CRC not phase matched to a hardware edge')

    layers = sorted((layer['copy_start_tick'], layer['copy_end_tick'], frame['generation'])
                    for frame in trace for layer in frame['layers'])
    totals = dict(changed=0, repeated=0, crc_missing=0, possible_copy_overlap=0, edges=0)
    elapsed_low = elapsed_high = 0
    reports = []
    intervals = []
    longest_update_gap = []
    for ordinal, (begin, end) in enumerate(strokes):
        selected = [slot for slot in slots if begin <= slot.a and slot.b <= end]
        require(len(selected) >= 2, 'insufficient vblank edges in stroke ' + str(ordinal))
        window = dict(changed=0, repeated=0, crc_missing=0, possible_copy_overlap=0, edges=0)
        outputs = []
        for left, right in zip(selected, selected[1:]):
            require(right.flags == 1 and ((right.id - left.id) & 0xffffffff) == 1,
                    'counter gap in stroke ' + str(ordinal))
            require(max(left.b - left.a, right.b - right.a) * scale <= MAX_EDGE_NS,
                    'vblank timestamp uncertainty in stroke ' + str(ordinal))
            before, after = crc.get(left.id), crc.get(right.id)
            window['edges'] += 1
            if not before or not after or before.flags or after.flags:
                window['crc_missing'] += 1
                continue
            changed = before.a != after.a
            window['changed' if changed else 'repeated'] += 1
            overlaps = [generation for a, b, generation in layers if a < right.b and left.a < b]
            window['possible_copy_overlap'] += bool(overlaps)
            completed = [generation for _, b, generation in layers if b <= left.a]
            outputs.append(dict(frame=right.id, edge_lower_tick=right.a, edge_upper_tick=right.b,
                                crc=after.a, changed=changed, overlapping_copies=sorted(set(overlaps)),
                                prior_copied_generation=completed[-1] if not overlaps and completed else None))
        changed_edges = [row for row in outputs if row['changed']]
        intervals.extend((b['edge_upper_tick'] - a['edge_lower_tick']) * scale
                         for a, b in zip(changed_edges, changed_edges[1:]))
        if changed_edges:
            longest_update_gap.extend(((changed_edges[0]['edge_upper_tick'] - begin) * scale,
                                       (end - changed_edges[-1]['edge_lower_tick']) * scale))
        else:
            longest_update_gap.append((end - begin) * scale)
        elapsed_low += selected[-1].a - selected[0].b
        elapsed_high += selected[-1].b - selected[0].a
        for key, value in window.items():
            totals[key] += value
        reports.append(dict(stroke=ordinal, outputs=outputs, **window))

    require(elapsed_low > 0 and totals['edges'] > 0, 'no bounded hardware time')
    seconds_low, seconds_high = elapsed_low * scale / 1e9, elapsed_high * scale / 1e9
    refresh = [totals['edges'] / seconds_high, totals['edges'] / seconds_low]
    covered = totals['crc_missing'] == 0
    return dict(**totals, hardware_refresh_hz_bounds=refresh, complete_crc_coverage=covered,
                scanout_content_fps_bounds=[totals['changed'] / seconds_high, totals['changed'] / seconds_low]
                if covered else None,
                update_interval_upper_ns_p95=quantile(intervals, .95) if covered else None,
                update_interval_upper_ns_p99=quantile(intervals, .99) if covered else None,
                longest_update_interval_upper_ns=max([*intervals, *longest_update_gap]) if covered else None,
                uninterrupted_60_fps_observed=covered and totals['repeated'] == 0 and
                totals['possible_copy_overlap'] == 0 and 59 <= refresh[0] <= refresh[1] <= 61,
                scope='DPU output CRC sampled twice per slot; overlapping writes can mix frames',
                optical_FPS_qualified=False, strokes=reports)


def analyze(text, joins, cores):
    rows, strokes, numer, denom = parse(text)
    begin, end = strokes[0][0], strokes[-1][1]
    # Include one leading refresh so the first presented frame can be matched
    # to the last observed write before the first script report.
    before = max(0, begin - 25_000_000 * denom // numer)
    trace = software(rows, joins, cores, before, end, numer, denom)
    try:
        output = hardware(text, rows, strokes, trace, numer, denom)
    except ValueError as error:
        output = dict(complete_crc_coverage=False, scanout_content_fps_bounds=None, reason=str(error),
                      uninterrupted_60_fps_observed=False, optical_FPS_qualified=False)
    return dict(frame_trace_complete=True, matched_attempts=len(trace),
                core_linked_layers=sum('ticket' in layer for frame in trace for layer in frame['layers']),
                attempts=trace, hardware=output)
