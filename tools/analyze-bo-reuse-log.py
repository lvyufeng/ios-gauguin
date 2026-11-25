#!/usr/bin/env python3
"""Separate fresh backing allocations from zeroed mapping reuse in BC335 logs."""
from pathlib import Path
import argparse
import importlib.util
import json
import math
import re
import statistics


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def stats(values):
    values = sorted(values)
    return dict(count=len(values), sum_us=sum(values), median_us=statistics.median(values) if values else None,
                p95_us=values[math.ceil(.95 * len(values)) - 1] if values else None,
                max_us=max(values) if values else None)


def analyze(text, ui):
    prefix = 'SWEET BC335: '
    lines = [line for line in text.splitlines() if line.startswith(prefix)]
    enabled = 'SWEET BC335: enabled slots=32 bytes=16777216 max_bo=1048576 zero=1'
    if lines.count(enabled) != 1:
        raise ValueError('BC335 activation absent or repeated')
    counters = re.findall(r'^SWEET BC335: hits=(\d+) misses=(\d+) stores=(\d+) evicts=(\d+) aliases=(\d+) valid=(\d+)$', text, re.M)
    residency = re.findall(r'^SWEET BC335: slots=(\d+) bytes=(\d+) connections=(\d+); completed prefix, zeroed owned only$', text, re.M)
    if len(counters) != 1 or len(residency) != 1 or len(lines) != 3:
        raise ValueError('missing, duplicate or malformed BC335 counters')
    hits, misses, stores, evicts, aliases, valid = map(int, counters[0])
    slots, retained, connections = map(int, residency[0])
    if valid not in (0, 1) or any(n >= 2**64 for n in (hits, misses, stores, evicts, aliases)):
        raise ValueError('BC335 counter range')
    if not 0 <= slots <= 32 or not 0 <= retained <= 16777216 or connections != 1:
        raise ValueError('BC335 connection or retained capacity')
    if stores != hits + evicts + slots or not slots * 16384 <= retained <= slots * 1048576:
        raise ValueError('BC335 ownership accounting mismatch')
    path = Path(__file__).with_name('analyze-bo-allocation-log.py')
    allocation = module('bc335_allocation_contract', path).analyze(text, ui)
    trace = ui.parse(text)
    tags = {}
    for event in trace['events']:
        if event['kind'] != 33:
            continue
        if not event['id'] or not event['pid'] or event['flags'] != 1 or event['id'] in tags:
            raise ValueError('invalid or duplicate BC335 reuse tag')
        if not 16384 <= event['a'] <= 1048576 or event['a'] % 16384 or not event['b']:
            raise ValueError('BC335 reused backing size or handle')
        tags[event['id']] = event
    rows = []
    consumed = set()
    for original in allocation['rows']:
        row = dict(original)
        tag = tags.get(row['token'])
        row['backing_reused'] = tag is not None
        if tag:
            if row['result'] != 0 or (tag['pid'], tag['a'], tag['b'], tag['c']) != (
                    row['pid'], (row['requested_bytes'] + 16383) & ~16383, row['handle'], row['flags']):
                raise ValueError('BC335 tag does not match successful request')
            phase = {e['flags']: e for e in trace['events'] if e['kind'] == 32 and e['id'] == row['token']}
            if not phase[5]['seq'] < tag['seq'] < phase[6]['seq']:
                raise ValueError('BC335 tag outside publication/return interval')
            consumed.add(row['token'])
            # Old six-phase envelopes remain valid, but a cache hit neither
            # allocates backing nor rewrites PTEs/synchronizes the SMMU.
            names = dict(dispatch_gate='gate_and_lookup', backing_allocation='selected_mapping',
                         zeroing='zeroing', mapping_preparation='handle_publication',
                         synchronization_and_return='tag_and_return', request_queue='request_queue', phase_total='phase_total')
            row['durations_us'] = {names[k]: v for k, v in row['durations_us'].items()}
        rows.append(row)
    unmatched = sorted(set(tags) - consumed)
    if unmatched and not trace['header']['lost'] and not trace['truncated_by_capacity']:
        partial = {row['token'] for row in allocation['partial']}
        if not set(unmatched) <= partial:
            raise ValueError('BC335 reuse tag has no matching allocation envelope')
    fresh = [row for row in rows if not row['backing_reused'] and row['result'] == 0]
    reused = [row for row in rows if row['backing_reused']]
    if len(reused) > hits:
        raise ValueError('captured BC335 reuse exceeds profiling-prefix hit count')
    summary = lambda group: {k: stats([r['durations_us'][k] for r in group]) for k in (group[0]['durations_us'] if group else [])}
    qualified = allocation['coverage_qualified'] and valid == 1 and not unmatched
    return dict(state='BC335-allocation-and-reuse-observed' if qualified else 'BC335-observation-unqualified',
                coverage_qualified=qualified, active=True, cache_hits=hits, cache_misses=misses,
                cache_stores=stores, cache_evictions=evicts, exported_alias_exclusions=aliases,
                retained_slots=slots, retained_bytes=retained, counters_scope='completed API profiling prefix',
                complete_count=len(rows), successful_count=len(fresh) + len(reused), failed_count=allocation['failed_count'],
                fresh_backing_requests=len(fresh), reused_mapping_requests=len(reused),
                fresh_backing_stages_us=summary(fresh), reused_mapping_stages_us=summary(reused),
                unmatched_reuse_tags=unmatched, partial=allocation['partial'], partial_count=allocation['partial_count'],
                missing_metadata_tokens=allocation['missing_metadata_tokens'], trace_lost=allocation['trace_lost'],
                capacity_truncated=allocation['capacity_truncated'], rows=rows, device_commands=0, physical_FPS_qualified=False,
                scope='Cache hit phases describe lookup/zero/handle publication and return. Fresh and reused timings are separate. CPU elapsed intervals are not GPU-only costs or per-frame causality.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    ui = module('bc335_ui', Path(__file__).with_name('ui_trace_log.py'))
    result = analyze(args.log.read_text(errors='replace'), ui)
    raw = json.dumps(result, indent=2) + '\n'
    assert len(raw.encode()) <= 4194304
    with args.out.open('x') as stream:
        stream.write(raw)
    print(json.dumps({k: v for k, v in result.items() if k not in ('rows', 'partial')}, indent=2))


if __name__ == '__main__':
    main()
