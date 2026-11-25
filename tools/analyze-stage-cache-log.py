#!/usr/bin/env python3
"""Validate bounded SC323 CPU records; cache hits never qualify physical FPS."""
import collections
import math
import re
import statistics

PREFIX = 'GAUGUIN SC323: '
TIMES = ('start', 'ready', 'keyed', 'fast', 'locking', 'locked', 'retry', 'compiled', 'saved', 'end')
LINE = re.compile(r'id=(\d+) thread=([0-9a-f]+) key=([0-9a-f]{32}|-) known=([01]) bytes=(\d+) outcome=([0-4]) source=([0-2]) '
                  + ' '.join(k+r'=(\d+)' for k in TIMES))


def stats(values):
    values = sorted(values)
    return dict(count=len(values), median_us=statistics.median(values) if values else None,
                p95_us=values[math.ceil(len(values)*.95)-1] if values else None,
                max_us=max(values) if values else None)


def analyze(text, prefix_preserved=True):
    rows, errors, limit = [], collections.Counter(), 0
    lines = [x for x in text.splitlines() if x.startswith(PREFIX)]
    for line in lines:
        if line == PREFIX+'limit=1 max=1024':
            limit += 1
            continue
        match = LINE.fullmatch(line[len(PREFIX):])
        if not match or len(line) >= 640:
            errors['malformed'] += 1
            continue
        groups = match.groups()
        identifier, thread, key = int(groups[0]), int(groups[1], 16), groups[2]
        known, size, outcome, source = map(int, groups[3:7])
        times = dict(zip(TIMES, map(int, groups[7:])))
        if not (1 <= identifier <= 1024 and 0 < thread < 1 << 64 and 0 < size < 1 << 64
                and all(0 <= v < 1 << 64 for v in times.values())):
            errors['bounds'] += 1
            continue
        active = {1: TIMES[:4]+('end',), 2: TIMES[:7]+('end',),
                  0: TIMES, 3: TIMES, 4: ('start', 'ready', 'end')}[outcome]
        values = [times[k] for k in active]
        if (not all(values) or values != sorted(values) or
                any(times[k] != 0 for k in TIMES if k not in active)):
            errors['clock_or_branch'] += 1
            continue
        if ((outcome in (1, 2)) != (source in (1, 2)) or
                (outcome in (1, 2) and key == '-') or (outcome == 4 and key != '-')):
            errors['outcome'] += 1
            continue
        durations = dict(total=times['end']-times['start'], initialization=times['ready']-times['start'])
        for name, a, b in (('key', 'ready', 'keyed'), ('fast_lookup', 'keyed', 'fast'),
                           ('lock_wait', 'locking', 'locked'), ('locked_lookup', 'locked', 'retry'),
                           ('compile', 'retry', 'compiled'), ('save', 'compiled', 'saved')):
            if a in active and b in active:
                durations[name] = times[b]-times[a]
        rows.append(dict(id=identifier, thread=hex(thread), key=key, known=bool(known), bytes=size,
                         outcome=outcome, source=source, times_us=times, duration_us=durations))
    ids = [r['id'] for r in rows]
    if len(set(ids)) != len(ids): errors['duplicate_id'] += 1
    if sorted(ids) != list(range(1, len(rows)+1)): errors['missing_id'] += 1
    if limit: errors['limit_reached'] += limit
    if len(lines) > 1025: errors['too_many_records'] += 1
    failures = sum(r['outcome'] in (0, 4) for r in rows)
    qualified = bool(rows) and prefix_preserved and not errors and failures == 0
    outcomes = collections.Counter(str(r['outcome']) for r in rows)
    return dict(state='SC323-cache-stages-observed' if qualified else 'SC323-cache-trace-unqualified',
        coverage_qualified=qualified, prefix_preserved=prefix_preserved, errors=dict(errors),
        count=len(rows), trace_bytes=sum(len(s.encode())+1 for s in lines), limit_markers=limit,
        failures=failures, outcome_counts=dict(outcomes), fast_hits=outcomes['1'], locked_hits=outcomes['2'],
        compilations=outcomes['3'], thread_count=len({r['thread'] for r in rows}),
        stages_us={name: stats([r['duration_us'][name] for r in rows if name in r['duration_us']])
                   for name in ('total', 'initialization', 'key', 'fast_lookup', 'lock_wait', 'locked_lookup', 'compile', 'save')},
        rows=rows, physical_FPS_qualified=False, timing_scope='CPU absolute timestamps; logging and scheduling affect callers; no hardware-only GPU duration')
