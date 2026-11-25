#!/usr/bin/env python3
"""Measure distinct visible updates from original camera samples, after restore."""

import argparse
from fractions import Fraction
import json
from pathlib import Path
from statistics import median
import subprocess

from core343_scope import BASE, COMPLETE, load, require, sha

WIDTH, HEIGHT = 128, 12
STRIP_BYTES = WIDTH * HEIGHT
THREE_STRIPS = 3 * STRIP_BYTES


def probe(video):
    fields = 'stream=width,height,time_base,duration:format=duration:frame=best_effort_timestamp'
    info = json.loads(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_streams', '-show_frames', '-show_format',
         '-read_intervals', '%+91', '-show_entries', fields, '-of', 'json', str(video)], timeout=120))
    stream, = info['streams']
    duration = stream.get('duration') or info['format']['duration']
    require(0 < Fraction(duration) <= 90, 'use the original clip up to 90 seconds')
    scale = Fraction(stream['time_base']) * 1_000_000
    pts = [int(row['best_effort_timestamp']) for row in info['frames']]
    require(2 <= len(pts) <= 22500, 'unexpected camera sample count')
    times = [round((tick - pts[0]) * scale) for tick in pts]
    rate, step = camera_clock(times)
    return stream['width'], stream['height'], times, rate, step


def camera_clock(times):
    intervals = [b - a for a, b in zip(times, times[1:])]
    step = median(intervals)
    rate = min((120, 240), key=lambda fps: abs(step - 1_000_000 / fps))
    nominal = 1_000_000 / rate
    require(abs(step - nominal) <= nominal * .025
            and all(.75 * step <= gap <= 1.25 * step for gap in intervals),
            'camera timestamps show a dropped sample, slow-motion export or non-native frame rate')
    return rate, step


def decode(video, width, height, rois, count):
    require(len(rois) == 3, 'two screen strips and one still reference are required')
    filters = ['[0:v:0]split=3[a][b][c]']
    for source, (x, y, w, h) in zip('abc', rois):
        require(all(type(v) is int and v % 2 == 0 for v in (x, y, w, h))
                and 0 <= x < x+w <= width and 0 <= y < y+h <= height and w >= 32 and h >= 4,
                'crop outside the original image or too small')
        filters.append(f'[{source}]crop={w}:{h}:{x}:{y},scale={WIDTH}:{HEIGHT}:flags=area,format=gray[{source}o]')
    left, right = rois[:2]
    require(left[1] == right[1] and left[3] == right[3] and left[0]+left[2] <= right[0],
            'screen strips must be separated across one camera scan band')
    filters.append('[ao][bo][co]hstack=inputs=3[out]')
    raw = subprocess.check_output(
        ['ffmpeg', '-nostdin', '-v', 'error', '-noautorotate', '-i', str(video),
         '-filter_complex', ';'.join(filters), '-map', '[out]', '-frames:v', str(count+1),
         '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'gray', 'pipe:1'], timeout=120)
    require(len(raw) == count * THREE_STRIPS, 'decoded camera frame count differs from its timestamps')
    return raw


def differences(raw):
    frame = memoryview(raw)
    result = [[], [], []]
    for pos in range(THREE_STRIPS, len(frame), THREE_STRIPS):
        for strip, scores in enumerate(result):
            start = pos + strip * WIDTH
            total = 0
            for y in range(HEIGHT):
                at = start + y * 3 * WIDTH
                old = frame[at-THREE_STRIPS:at-THREE_STRIPS+WIDTH]
                new = frame[at:at+WIDTH]
                total += sum(abs(a-b) for a,b in zip(old,new))
            scores.append(total/STRIP_BYTES)
    return result


def transitions(times, scores, indices, threshold, max_span):
    groups = []
    for i in indices:
        if scores[i-1] <= threshold:
            continue
        if groups and i == groups[-1][-1] + 1:
            groups[-1].append(i)
        else:
            groups.append([i])
    require(all(len(g) <= max_span for g in groups),
            'mixed or continuous optical transitions cannot be resolved at this camera rate')
    return [(times[g[0]-1], times[g[-1]]) for g in groups]


def measure(times, scores, script, layout, rate, step):
    still_start, still_end = layout['still_reference_us']
    strokes = layout['visible_strokes_us']
    require(len(strokes) == len(script) == 13 and 0 <= still_start < still_end <= strokes[0][0]
            and still_end - still_start >= 500000, 'need static calibration and all 13 visible intervals')
    require(all(0 <= a < b <= times[-1] and (i == 0 or a >= strokes[i-1][1])
                for i, (a,b) in enumerate(strokes)), 'invalid or overlapping optical intervals')
    require(all(abs((a-strokes[0][0]) - (kernel['begin_us']-script[0]['begin_us'])) <= 750000
                for (a, _), kernel in zip(strokes, script)),
            'visible stroke ordinals do not align with the same kernel workload')
    still = [i for i in range(1, len(times)) if still_start <= times[i-1] and times[i] < still_end]
    require(len(still) >= rate//3, 'calibration interval not present in video')
    noise = [max(ch[i-1] for i in still) for ch in scores]
    require(all(n <= 3.0 for n in noise), 'camera motion/lighting/noise in still reference')
    thresholds = [max(2.5, 3*n) for n in noise]
    rows = []
    for stroke, (a,b) in enumerate(strokes):
        active = [i for i in range(1, len(times)) if a <= times[i] < b]
        require(len(active) >= 4 and all(scores[2][i-1] <= thresholds[2] for i in active),
                'missing optical samples or movement in the still reference during stroke ' + str(stroke))
        left, right = [transitions(times, channel, active, threshold, rate//120)
                       for channel, threshold in zip(scores[:2], thresholds[:2])]
        require(len(left) == len(right) >= 2 and
                all(abs(x[1]-y[1]) <= step * 1.25 for x,y in zip(left,right)),
                'the two optical strips disagree during stroke ' + str(stroke))
        updates = [(min(x[0], y[0]), max(x[1], y[1])) for x,y in zip(left,right)]
        gaps = [[max(0, nxt[0]-prev[1]), nxt[1]-prev[0]] for prev,nxt in zip(updates, updates[1:])]
        rows.append(dict(stroke=stroke, start_us=a, end_us=b, visible_updates=len(updates),
                         visible_FPS=len(updates)*1_000_000/(b-a), transition_time_bounds_us=updates,
                         inter_update_gap_bounds_us=gaps,
                         definitely_over_25ms=sum(lo > 25000 for lo,_ in gaps),
                         possibly_over_25ms=sum(hi > 25000 for _,hi in gaps)))
    lateral = rows[1:]
    duration = sum(r['end_us']-r['start_us'] for r in lateral)
    return dict(strokes=rows, lateral_visible_FPS=sum(r['visible_updates'] for r in lateral)*1_000_000/duration,
                lateral_observed_motion_us=duration, camera_nominal_fps=rate, camera_median_sample_us=step,
                method='Matched visible content transitions in two fixed optical strips; gaps include camera sampling uncertainty',
                metric_scope='Visible motion intervals, including within-stroke stalls; deliberate gaps between strokes excluded',
                panel_refresh_rate_inferred=False, stable_60fps_claim=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('video', type=Path)
    parser.add_argument('layout', type=Path)
    args = parser.parse_args()
    execution = BASE/'execution'
    trial = load(execution/'result.json')
    proof = load(execution/'independent-restore.json')
    plan = load(BASE/'trial-plan.json')
    require(trial['state'] == COMPLETE and trial['trial'] == '0343'
            and trial['restored'] and trial['independent_restore_verified'] and trial['static_root_comparison_passed']
            and proof['install_plan_sha256'] == plan['install_plan_sha256']
            and trial['collection_analysis']['coverage_qualified'], 'restore/readback and trace must qualify first')
    compare = load(execution/'runtime343-comparison.json')
    script = compare['candidate_0343']['per_stroke']
    video = args.video.resolve(strict=True)
    require(video.is_file() and args.layout.stat().st_size < 16384, 'invalid optical input')
    layout = load(args.layout)
    require(layout['native_original_not_resampled'] is True
            and layout['trial_plan_sha256'] == sha(BASE/'trial-plan.json'),
            'original camera capture of this exact trial required')
    output = execution/'optical343-fps.json'
    require(not output.exists(), 'optical result already saved')
    before = sha(video)
    width, height, times, rate, step = probe(video)
    pixels = decode(video, width, height, layout['rois_xywh'], len(times))
    report = measure(times, differences(pixels), script, layout, rate, step)
    require(sha(video) == before, 'camera file changed while measuring')
    report.update(state='0343-optical-visible-motion-measured', video_sha256=before, layout=layout,
                  restore_proof_sha256=sha(execution/'independent-restore.json'),
                  trial_plan_sha256=sha(BASE/'trial-plan.json'), physical_FPS_qualified=True, device_commands=0)
    contents = (json.dumps(report, indent=2)+'\n').encode()
    require(len(contents) <= plan['optical_FPS']['project_artifacts_max_bytes'], 'optical result exceeds bound')
    with output.open('xb') as stream:
        stream.write(contents)
    print(json.dumps({k:v for k,v in report.items() if k != 'strokes'}, indent=2))


if __name__ == '__main__':
    main()
