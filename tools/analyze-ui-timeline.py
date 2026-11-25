#!/usr/bin/env python3
"""Align the bounded UI254 kernel trace with opt-in HakiOS Metal CPU timestamps."""

import argparse
import bisect
import importlib.util
import json
import re
from pathlib import Path


SPEC = importlib.util.spec_from_file_location('ui_trace_log', Path(__file__).with_name('ui_trace_log.py'))
UI_TRACE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UI_TRACE)

METAL = re.compile(r'tl: M made ([0-9]+) committed ([0-9]+) done ([0-9]+) gpu ([0-9]+)$')
MAX_METAL = 100000


def parse_metal(text):
    """The four numbers are microseconds; GPU is a duration, not a timestamp."""
    rows = []
    for line in text.splitlines():
        pos = line.find('tl: M ')
        if pos < 0:
            continue
        match = METAL.fullmatch(line[pos:])
        if not match:
            raise ValueError('malformed tl: M record')
        made, committed, done, gpu = map(int, match.groups())
        if not 0 < made <= committed <= done or any(x >= 1 << 64 for x in (made, committed, done, gpu)):
            raise ValueError('invalid tl: M time/range')
        if len(rows) >= MAX_METAL:
            raise ValueError('Metal record count exceeds bound')
        rows.append({'made_us': made, 'committed_us': committed, 'done_us': done,
                     'gpu_duration_us': gpu, 'make_to_commit_us': committed - made,
                     'commit_to_done_us': done - committed})
    return rows


def summarize_gaps(times_ns):
    gaps = [(b-a)//1000 for a, b in zip(times_ns, times_ns[1:])]
    if not gaps:
        return {'samples': 0, 'median_us': None, 'max_us': None, 'over_16667_us': 0}
    gaps.sort()
    return {'samples': len(gaps), 'median_us': gaps[len(gaps)//2], 'max_us': gaps[-1],
            'over_16667_us': sum(g > 16667 for g in gaps)}


def next_gap(after_ns, times_ns):
    pos = bisect.bisect_left(times_ns, after_ns)
    return (times_ns[pos]-after_ns)//1000 if pos < len(times_ns) else None


def analyze(kernel_text, metal_text):
    capture = UI_TRACE.parse(kernel_text)
    header = capture['header']
    if not capture['clock_valid']:
        raise ValueError('UI254 clock invalid; cannot align logs')
    start_ns = header['start'] * header['numer'] // header['denom']
    end_ns = header['end'] * header['numer'] // header['denom']
    if end_ns <= start_ns:
        raise ValueError('UI254 interval too short to align')

    def tick_ns(tick):
        return tick * header['numer'] // header['denom']

    events = capture['events']
    metal = parse_metal(metal_text)
    overlapping = [row for row in metal if row['done_us']*1000 >= start_ns
                   and row['made_us']*1000 < end_ns]
    made = sorted(row['made_us']*1000 for row in overlapping
                  if start_ns <= row['made_us']*1000 < end_ns)
    committed = sorted(row['committed_us']*1000 for row in overlapping
                       if start_ns <= row['committed_us']*1000 < end_ns)
    done = sorted(row['done_us']*1000 for row in overlapping
                  if start_ns <= row['done_us']*1000 < end_ns)
    swap = [tick_ns(e['tick']) for e in events if e['kind'] == 20]
    present_end = [tick_ns(e['tick']) for e in events if e['kind'] == 22]
    report = {e['id']: e for e in events if e['kind'] == 1}
    queue = {link['report_id']: link for link in capture['queue_links']}
    contacts = []
    for event in events:
        if event['kind'] != 2 or not event['flags']:
            continue
        origin = report.get(event['id'])
        link = queue.get(event['id'])
        if not origin:
            continue
        # UI254 marks unusable physical-report timing in flags. Do not turn
        # that sentinel into a huge apparent touch-to-frame delay.
        origin_ns = tick_ns(origin['a']) if not origin['flags'] and origin['a'] else None
        contact = {'report_id': event['id'], 'report_seq': origin['seq'],
                   'report_offset_us': (origin_ns-start_ns)//1000 if origin_ns is not None else None,
                   'hid_begin_offset_us': (tick_ns(event['tick'])-start_ns)//1000,
                   'queue_status': ('accepted' if link['enqueued'] else 'rejected') if link else 'unobserved',
                   'hid_begin_to_queue_us': link['elapsed_ns']//1000 if link else None,
                   'next_metal_made_us': next_gap(origin_ns, made) if origin_ns is not None else None,
                   'next_metal_commit_us': next_gap(origin_ns, committed) if origin_ns is not None else None,
                   'next_swap_end_us': next_gap(origin_ns, swap) if origin_ns is not None else None,
                   'next_present_end_us': next_gap(origin_ns, present_end) if origin_ns is not None else None}
        contacts.append(contact)

    timeline = [{'source': 'kernel', 'name': UI_TRACE.KINDS[e['kind']], 'seq': e['seq'],
                 'id': e['id'], 'offset_us': (tick_ns(e['tick'])-start_ns)//1000}
                for e in events]
    for index, row in enumerate(overlapping, 1):
        for name in ('made', 'committed', 'done'):
            ns = row[name+'_us']*1000
            if start_ns <= ns < end_ns:
                timeline.append({'source': 'metal', 'name': name, 'index': index,
                                 'offset_us': (ns-start_ns)//1000})
    timeline.sort(key=lambda e: (e['offset_us'], e['source'], e.get('seq', 0)))

    return {'scope': 'Same mach_absolute_time domain, CPU timestamp alignment only. '
            'Nearest future event is temporal proximity, not a causal touch-to-frame link; '
            'Metal gpu duration is author-reported, and no panel latch or physical FPS is measured.',
            'capture': {'reason': header['reason'], 'duration_us': (end_ns-start_ns)//1000,
                        'input_origin': capture['input_origin'], 'physical_touch_qualified': False,
                        'kernel_events': len(events), 'lost': header['lost'],
                        'truncated_by_capacity': capture['truncated_by_capacity'],
                        'unpaired_spans': len(capture['unpaired_endpoints'])},
            'metal': {'total_records': len(metal), 'overlapping_records': len(overlapping),
                      'missing_in_window': not overlapping, 'made_in_window': len(made),
                      'committed_in_window': len(committed), 'done_in_window': len(done),
                      'made_gaps': summarize_gaps(made),
                      'commit_gaps': summarize_gaps(committed)},
            'display': {'swap_end_count': len(swap), 'present_end_count': len(present_end),
                        'swap_gaps': summarize_gaps(swap),
                        'present_end_gaps': summarize_gaps(present_end)},
            'hid': {'changed_reports': len(contacts),
                    'queue_enqueued': sum(c['queue_status'] == 'accepted' for c in contacts),
                    'queue_refused': sum(c['queue_status'] == 'rejected' for c in contacts),
                    'queue_unobserved': sum(c['queue_status'] == 'unobserved' for c in contacts),
                    'contacts': contacts},
            'kernel_spans': capture['spans'], 'timeline': timeline}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('kernel_log', type=Path)
    ap.add_argument('backboardd_log', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    result = analyze(args.kernel_log.read_text(errors='replace'),
                     args.backboardd_log.read_text(errors='replace'))
    data = json.dumps(result, indent=2)+'\n'
    if args.out:
        with args.out.open('x') as target:
            target.write(data)
    else:
        print(data, end='')


if __name__ == '__main__':
    main()
