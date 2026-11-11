"""Strictly parse 0221 CPU present statistics; never infer panel FPS."""
import re

MAX_U64 = (1 << 64) - 1
MAIN_PREFIX = 'SWEET FB STATS:'
GUARD_PREFIX = 'SWEET FB STATS GUARD:'
COPY_PREFIX = 'SWEET FB STATS COPY:'
MAIN = re.compile(r'SWEET FB STATS: attempts=(\d+) copied=(\d+) zero=(\d+) invalid=(\d+) '
                  r'bytes=(\d+) layers=(\d+) guards=(\d+) refused=(\d+); CPU, not scanout')
HIST = r'samples=(\d+) bins=' + ','.join([r'(\d+)'] * 8) + r'; ns upper bounds 500k,1m,2m,4m,8m,16m,33333333,inf'
GUARD = re.compile(r'SWEET FB STATS GUARD: ' + HIST)
COPY = re.compile(r'SWEET FB STATS COPY: ' + HIST)
MAIN_NAMES = ('attempts', 'copied', 'zero', 'invalid', 'bytes', 'layers', 'guards', 'refused')
BOUNDS_NS = (0, 500000, 1000000, 2000000, 4000000, 8000000, 16000000, 33333333, None)


def _values(match):
    values = tuple(map(int, match.groups()))
    if any(value > MAX_U64 for value in values):
        raise ValueError('counter exceeds uint64')
    return values


def _histogram(values):
    samples, bins = values[0], list(values[1:])
    if min(MAX_U64, sum(bins)) != samples:
        raise ValueError('histogram bins do not match sample count')
    return {'samples': samples, 'bins': bins}


def _percentile_bucket(histogram, percentile):
    count = histogram['samples']
    if count == 0 or count == MAX_U64 or any(x == MAX_U64 for x in histogram['bins']):
        return None
    rank = (count * percentile + 99) // 100
    cumulative = 0
    for index, value in enumerate(histogram['bins']):
        cumulative += value
        if cumulative >= rank:
            return {'lower_inclusive_ns': BOUNDS_NS[index], 'upper_exclusive_ns': BOUNDS_NS[index + 1]}
    raise ValueError('histogram rank is inconsistent')


def _validate(snapshot, previous):
    m, guard, copy = snapshot['counts'], snapshot['guard'], snapshot['copy']
    if min(MAX_U64, m['copied'] + m['zero']) != m['attempts']:
        raise ValueError('attempt outcome counts are inconsistent')
    if (m['invalid'] > m['attempts'] or m['refused'] > m['guards'] or
            m['layers'] < m['copied'] or
            m['bytes'] < min(MAX_U64, 4 * m['copied']) or
            guard['samples'] > m['guards'] or copy['samples'] > m['copied'] or
            copy['samples'] > guard['samples']):
        raise ValueError('present counts are inconsistent')
    # Every copied layer passes a successful read guard. Saturation makes
    # subtracting the two guard counters ambiguous, so do not infer it then.
    if m['guards'] != MAX_U64 and m['refused'] != MAX_U64:
        if m['copied'] > m['guards'] - m['refused']:
            raise ValueError('copied attempts exceed successful guards')
    if m['attempts'] != MAX_U64 and m['invalid'] != MAX_U64:
        valid = m['attempts'] - m['invalid']
        if guard['samples'] > valid or copy['samples'] > valid:
            raise ValueError('histogram includes invalid timing samples')
    if previous:
        if (m['attempts'] == previous['counts']['attempts'] and
                m['attempts'] != MAX_U64):
            raise ValueError('duplicate present snapshot or attempt counter regressed')
        for key in MAIN_NAMES:
            if m[key] < previous['counts'][key]:
                raise ValueError('present counter regressed')
        for key in ('guard', 'copy'):
            if (snapshot[key]['samples'] < previous[key]['samples'] or
                    any(a < b for a, b in zip(snapshot[key]['bins'], previous[key]['bins']))):
                raise ValueError('present histogram regressed')
    for key in ('guard', 'copy'):
        snapshot[key]['p95_bucket_ns'] = _percentile_bucket(snapshot[key], 95)
        snapshot[key]['p99_bucket_ns'] = _percentile_bucket(snapshot[key], 99)


def parse_present_stats(text):
    """Parse complete ordered snapshots; missing/interleaved records fail closed."""
    if not isinstance(text, str):
        raise ValueError('present statistics input is not text')
    pending, snapshots = None, []
    for line in text.splitlines():
        if line == 'SWEET FB STATS: enabled; CPU timing only, panel unqualified':
            continue
        if MAIN_PREFIX in line:
            match = MAIN.fullmatch(line)
            if match is None or pending is not None:
                raise ValueError('malformed, duplicate or incomplete present summary')
            pending = {'counts': dict(zip(MAIN_NAMES, _values(match)))}
        elif GUARD_PREFIX in line:
            match = GUARD.fullmatch(line)
            if match is None or pending is None or 'guard' in pending:
                raise ValueError('malformed or out-of-order guard histogram')
            pending['guard'] = _histogram(_values(match))
        elif COPY_PREFIX in line:
            match = COPY.fullmatch(line)
            if match is None or pending is None or 'guard' not in pending:
                raise ValueError('malformed or out-of-order copy histogram')
            pending['copy'] = _histogram(_values(match))
            _validate(pending, snapshots[-1] if snapshots else None)
            snapshots.append(pending)
            pending = None
    if pending is not None or not snapshots:
        raise ValueError('missing or incomplete present statistics')
    return {'snapshots': snapshots, 'scope': 'CPU guard-acquisition and copied-byte wall intervals',
            'histogram_bounds': 'lower inclusive, upper exclusive; final upper bound unbounded',
            'coverage': 'recorded cumulative prefixes only; later activity may be unreported',
            'disabled_trace_overhead_qualified': False, 'panel_scanout_qualified': False,
            'physical_FPS_qualified': False, 'input_latency_qualified': False,
            'desktop_correctness_qualified': False}
