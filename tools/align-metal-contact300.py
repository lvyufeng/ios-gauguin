#!/usr/bin/env python3
"""Align 0300 touch-active display intervals with C4 command-buffer times.

Both clocks originate in mach_absolute_time. This counts observations in
bounded intervals; it does not pair a touch to a frame or measure panel FPS.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT/'research/tmp/gpu-notify-hid-20261112'
KERNEL_SHA = '22e786c12d9b05ef3edbe8b3d05b18450770bc3733c20dc82da5a18a5bbe21e5'
BACKBOARD_SHA = 'e363a18f9c7671e8dff7d78e5593d84d9261e215a647917ac3d2307936341209'
HZ = 19_200_000
BEAT = re.compile(r'SWEET FB CLOCK: enabled software_us=(\d+) beat_ticks=(\d+) copy_ticks=\d+ held=1 physical_rate=unqualified')
CLOCK = re.compile(r'SWEET FB CLOCK: callbacks=(\d+) skipped=(\d+) copies=\d+ next_beat=(\d+) next_copy=\d+; software only')
METAL = re.compile(r'HakiosMetal\[backboardd \d+\]: timeline: made ([0-9]+\.[0-9]+) committed ([0-9]+\.[0-9]+) done ([0-9]+\.[0-9]+) gpu ([0-9]+\.[0-9]+)')
HZ_LINE = re.compile(r'SWEET FB: vsync=\d+ dirty=\d+ presents=\d+ client=\d+ px sample \d+ nonblack=\d+ distinct=\d+ colours:.* hz=(\d+)')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def clock_rows(kernel):
    beat = BEAT.findall(kernel)
    require(len(beat) == 1, 'exactly one 0300 software clock activation required')
    software_us, beat_ticks = map(int, beat[0])
    require(software_us == 16667 and beat_ticks == 320006,
            '0300 clock geometry differs')
    require(abs(beat_ticks*1_000_000/HZ-software_us) < 1,
            'clock tick conversion differs')
    frequencies = [int(v) for v in HZ_LINE.findall(kernel) if int(v)]
    require(frequencies and abs(sorted(frequencies)[len(frequencies)//2]-HZ) < HZ//100,
            'observed kernel timebase is not 19.2 MHz')
    rows = {}
    origins = set()
    matches = CLOCK.findall(kernel)
    require(len(matches) == kernel.count('SWEET FB CLOCK: callbacks='),
            'malformed framebuffer clock row')
    for callback, skipped, next_beat in matches:
        n, lost, tick = int(callback), int(skipped), int(next_beat)
        require(n > 0 and tick > 0 and n not in rows,
                'duplicate or malformed framebuffer clock sample')
        origin = tick-(n+lost)*beat_ticks
        require(origin > 0, 'negative clock origin')
        origins.add(origin)
        rows[n] = {'skipped': lost, 'next_beat_tick': tick}
    require(len(rows) >= 2 and len(origins) == 1,
            'display callback count cannot be mapped to one absolute clock')
    previous = None
    for callback, row in sorted(rows.items()):
        if previous is not None:
            require(callback > previous[0] and row['skipped'] >= previous[1]['skipped'] and
                    row['next_beat_tick'] > previous[1]['next_beat_tick'],
                    'display clock samples regressed')
        previous = callback, row
    return beat_ticks, rows, origins.pop()


def metal_rows(backboard):
    rows = []
    matches = METAL.findall(backboard)
    require(len(matches) == backboard.count('timeline: made '),
            'malformed C4 timeline row')
    for values in matches:
        made, committed, done, gpu = map(float, values)
        require(0 <= made <= committed <= done and 0 <= gpu < 10000,
                'malformed C4 timeline')
        rows.append({'made_ms': made, 'committed_ms': committed,
                     'done_ms': done, 'reported_gpu_ms': gpu})
    require(rows, 'no C4 command-buffer timestamps')
    return rows


def align(kernel, backboard, cadence):
    beat_ticks, clock, origin = clock_rows(kernel)
    metal = metal_rows(backboard)
    require(cadence['state'] == 'sampled-held-retirement-cadence-not-optical-fps' and
            type(cadence['intervals']) is list, '0300 held cadence missing')
    intervals = []
    for interval in cadence['intervals']:
        if not interval['contact_edges']:
            continue
        first, last = interval['from_vsync'], interval['to_vsync']
        require(type(first) is int and type(last) is int and 0 < first < last and
                type(interval['contact_edges']) is int and interval['contact_edges'] > 0 and
                type(interval['held_retired']) is int and interval['held_retired'] >= 0,
                'malformed touch-active interval')
        row = {'from_vsync': first, 'to_vsync': last,
               'contact_mask_changes': interval['contact_edges'],
               'held_retired': interval['held_retired']}
        a, b = clock.get(first), clock.get(last)
        if a is None or b is None or a['skipped'] != b['skipped']:
            row['state'] = 'not-aligned-missing-endpoint-or-skipped-beat-transition'
            intervals.append(row)
            continue
        start, end = a['next_beat_tick']/HZ*1000, b['next_beat_tick']/HZ*1000
        require(0 < start < end and abs(end-start-(last-first)*beat_ticks/HZ*1000) < 0.01,
                'clock interval differs from exact beat count')
        beat_ms = beat_ticks/HZ*1000
        near = [item for item in metal if
                min(abs(item['made_ms']-start), abs(item['made_ms']-end)) <= beat_ms]
        selected = [item for item in metal if start+beat_ms < item['made_ms'] < end-beat_ms]
        row.update(state='aligned-with-boundary-uncertainty' if near else 'aligned',
                   start_ms=round(start, 3), end_ms=round(end, 3),
                   boundary_uncertain_buffers=len(near),
                   c4_buffers_made=len(selected),
                   c4_buffers_done_within_window=sum(start+beat_ms < item['done_ms'] < end-beat_ms
                                                      for item in selected),
                   c4_made_ms=[item['made_ms'] for item in selected],
                   c4_reported_gpu_ms=[item['reported_gpu_ms'] for item in selected],
                   c4_reported_gpu_over_16_667_ms=sum(item['reported_gpu_ms'] > 16.667
                                                       for item in selected))
        intervals.append(row)
    require(intervals, 'no touch-active intervals')
    return {'state': '0300-touch-window-C4-alignment',
            'scope': 'same mach_absolute_time only; contact-mask changes are not userland receipts; C4 buffers are not all display frames; held retirement is not physical FPS or optical touch latency',
            'source_clock_hz': HZ, 'software_beat_ticks': beat_ticks,
            'absolute_clock_origin_tick': origin,
            'kernel_clock_samples': len(clock), 'c4_timeline_samples': len(metal),
            'intervals': intervals}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel', type=Path, default=TRIAL/'execution/kernel.log')
    parser.add_argument('--backboard', type=Path, default=TRIAL/'execution/backboardd.log.current')
    parser.add_argument('--cadence', type=Path, default=TRIAL/'held-cadence300.json')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    require(sha(args.kernel) == KERNEL_SHA and sha(args.backboard) == BACKBOARD_SHA,
            'raw 0300 log hash differs')
    cadence = json.loads(args.cadence.read_bytes())
    require(cadence['kernel_sha256'] == KERNEL_SHA,
            'held-cadence record is from another boot')
    result = align(args.kernel.read_text(errors='replace'),
                   args.backboard.read_text(errors='replace'), cadence)
    result['kernel_sha256'] = KERNEL_SHA
    result['backboard_sha256'] = BACKBOARD_SHA
    result['cadence_sha256'] = sha(args.cadence)
    payload = json.dumps(result, indent=2, allow_nan=False)+'\n'
    if args.out:
        require(args.out.resolve().is_relative_to(TRIAL.resolve()) and not args.out.exists(),
                'new private trial output required')
        args.out.write_text(payload)
    else:
        print(payload, end='')


if __name__ == '__main__':
    main()
