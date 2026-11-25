#!/usr/bin/env python3
"""Decode bounded C4 CPU stages; preserve callback/submit partial ordering."""
from pathlib import Path
import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import re
import statistics

PREFIX = 'GAUGUIN C4Q321: '
ROW = re.compile(r'GAUGUIN C4Q321: phase=([0-9]) object=(0x[0-9a-f]+) start_us=([0-9]+) end_us=([0-9]+) value=([0-9]+)')
METAL = re.compile(r'tl: M made (\d+) committed (\d+) done (\d+) gpu (\d+)')
LIMIT = PREFIX+'limit=32768 coverage=incomplete'
EDGES = ((0, 1), (1, 2), (2, 3), (3, 4), (2, 5), (5, 6), (6, 7))
# The callback may finish before commit() or status() returns, including errors.
# Branches overlap: these durations must not be added as an exclusive timeline.
STAGES = {'frontend_queue': (0, 1), 'turn_and_event_wait': (1, 2),
          'core_commit_call': (2, 3), 'core_status_drain': (3, 4),
          'core_call_to_callback': (2, 5), 'callback_first_timing_read': (5, 6),
          'callback_to_handlers_posted': (6, 7), 'commit_to_callback_entry': (0, 5)}


def stats(values):
    values = sorted(values)
    return dict(count=len(values), median=statistics.median(values) if values else None,
                p95=values[max(0, math.ceil(len(values)*.95)-1)] if values else None,
                max=max(values) if values else None)


def analyze(text):
    records = []
    errors = Counter()
    limit_markers = 0
    trace_bytes = 0
    metal = defaultdict(list)
    for lineno, line in enumerate(text.splitlines(), 1):
        m = METAL.fullmatch(line)
        if m:
            made, committed, done, gpu = map(int, m.groups())
            metal[made, committed].append(dict(done_us=done, gpu_us=gpu))
        if PREFIX not in line:
            continue
        trace_bytes += len(line.encode())+1
        if line == LIMIT:
            limit_markers += 1
            continue
        m = ROW.fullmatch(line)
        if not m or len(line.encode())+1 > 128:
            errors['malformed_row'] += 1
            continue
        phase, obj, start, end, value = m.groups()
        phase, start, end, value = map(int, (phase, start, end, value))
        # Printed timestamps round to nearest microsecond at the upper edge.
        if not (0 < int(obj, 16) < 2**64 and 220000000 <= start <= 270000000 and
                start <= end <= 900000000 and value < 2**32):
            errors['out_of_bounds'] += 1
            continue
        if (phase in (0, 1, 2, 3, 5, 6, 7) and value != 0) or (phase in (8, 9) and value not in (0, 1)):
            errors['invalid_value'] += 1
            continue
        records.append(dict(phase=phase, object=obj, start_us=start, end_us=end,
                            value=value, line=lineno))
    if len(records) > 32768 or limit_markers > 1 or trace_bytes > 32769*128:
        errors['log_bound_exceeded'] += 1
    groups = defaultdict(dict)
    compile_spans = []
    for row in records:
        if row['phase'] >= 8:
            compile_spans.append(row)
            continue
        key = (row['object'], row['start_us'])
        if row['phase'] in groups[key]:
            errors['duplicate_cb_phase'] += 1
        groups[key][row['phase']] = row
    complete, incomplete, timelines = [], [], []
    metrics = defaultdict(list)
    traced_keys = Counter()
    for (obj, made), phases in groups.items():
        missing = sorted(set(range(8))-phases.keys())
        bad_edges = [(a, b) for a, b in EDGES if a in phases and b in phases and
                     phases[a]['end_us'] > phases[b]['end_us']]
        if bad_edges:
            errors['impossible_partial_order'] += 1
        if missing or bad_edges:
            incomplete.append(dict(object=obj, made_us=made, missing_phases=missing, invalid_edges=bad_edges))
            continue
        times = {k: v['end_us'] for k, v in phases.items()}
        durations = {name: times[b]-times[a] for name, (a, b) in STAGES.items()}
        durations['created_to_commit'] = times[0]-made
        entry = dict(object=obj, made_us=made, times_us=times, durations_us=durations,
                     status=phases[4]['value'])
        matched = metal.get((made, times[0]), [])
        traced_keys[made, times[0]] += 1
        if len(matched) != 1:
            errors['missing_or_ambiguous_timeline'] += 1
        elif not times[6] <= matched[0]['done_us'] <= times[7]:
            errors['timeline_outside_callback'] += 1
        else:
            entry['existing_timeline'] = matched[0]
            timelines.append(matched[0])
        complete.append(entry)
        for name, duration in durations.items():
            metrics[name].append(duration)
    eligible = {key: rows for key, rows in metal.items()
                if 220000000 <= key[0] <= 270000000}
    for key, rows in eligible.items():
        # A lost *whole* trace has no group above. Cross-check the independent,
        # unchanged completion log instead of silently excluding that buffer.
        if traced_keys[key] == 0:
            errors['untraced_completed_buffer'] += len(rows)
        elif traced_keys[key] != 1:
            errors['ambiguous_trace_identity'] += 1
    spans = {str(phase): stats([row['end_us']-row['start_us'] for row in compile_spans if row['phase'] == phase])
             for phase in (8, 9)}
    qualified = bool(complete) and not incomplete and not errors and not limit_markers
    return dict(state='C4Q321-CPU-stages-observed' if qualified else 'C4Q321-coverage-unqualified',
                coverage_qualified=qualified, trace_rows=len(records), trace_bytes=trace_bytes,
                limit_markers=limit_markers, errors=dict(errors), complete_cb_count=len(complete),
                incomplete_cb_count=len(incomplete), matched_timeline_count=len(timelines),
                eligible_timeline_count=sum(map(len, eligible.values())),
                stage_us={name: stats(values) for name, values in metrics.items()},
                compiler_span_us=spans, buffers=complete, incomplete=incomplete,
                compiler_spans=compile_spans, physical_FPS_qualified=False,
                duration_semantics='CPU timestamps; overlapping branches, includes logging overhead; no hardware-only GPU duration')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    assert not args.out.exists()
    raw = args.log.read_bytes()
    result = analyze(raw.decode('utf-8', 'replace'))
    result.update(input_sha256=hashlib.sha256(raw).hexdigest(), input=str(args.log.resolve()))
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('buffers', 'incomplete', 'compiler_spans')}, indent=2))


if __name__ == '__main__':
    main()
