#!/usr/bin/env python3
"""Run the frozen 0388 hardware comparison and score it after restoration."""

from importlib import import_module
import re

import frame344_log as trace
from frame357_display import CALIBRATION
import frame374_native_ca as native
import frame380_phase as phase

scope = import_module('prepare-frame388')
stage = import_module('run-frame384-trial')
executor = import_module('run-core342-trial')
runner = import_module('run-frame374-trial')


def deadline_receipts(raw, pacing):
    size = sum(len(line) + 1 for line in raw.splitlines() if line.startswith('SWEET F388 '))
    count, aligned, software, fallback, missed, first, last = map(int, trace.one(
        r'^SWEET F388 F: rows=(\d+) aligned=(\d+) software=(\d+) fallback=(\d+) missed=(\d+) '
        r'first=(\d+) last=(\d+)$', raw, 'independent deadline footer'))
    rows = re.findall(r'^SWEET F388 P: seq=(\d+) scan=(\d+) source=(\d+) o=(\d+) w=(\d+) '
                      r'r=(\d+) p=(\d+) a=(\d+)$', raw, re.M)
    expected = pacing['pulses']
    trace.require(size <= scope.CONSOLE_RECEIPTS_MAX and count == len(rows) == len(expected) <= 24 and
                  aligned == pacing['aligned'] and missed == pacing['missed'] and
                  fallback == pacing['software_after_first'] and software >= pacing['software_before_first']+fallback and
                  (first,last) == (pacing['first_tick'],pacing['last_tick']),
                  'independent deadline counts do not agree with the legacy phase lane')
    total = 4910
    end = int(trace.one(r'^SWEET F351 WINDOW: available=1 frame=\d+ end=(\d+)$', raw, 'flip window'))
    tail = total - end + 192
    low, high = ((period*tail + total-1)//total for period in (312000,328320))
    work_us = pacing.get('work_duration_us',0)
    work_ticks = work_us*96//5
    samples = []
    for encoded, previous in zip(rows, expected, strict=True):
        ordinal, scan, source, observed, wake, ready, edge, actual = map(int, encoded)
        trace.require((ordinal,scan,source,observed,wake,edge,actual) == tuple(previous[key] for key in (
            'sequence','scan','source','source_observed_tick','wake_tick','predicted_tick','notification_tick')) and
            wake < ready < edge and low <= edge-ready <= high and
            (ready-wake==work_ticks and actual<ready if work_ticks else edge-wake==76800),
            'ready deadline has no matching target scan or valid DPU cutoff')
        samples.append(dict(scan=scan, wake_tick=wake, ready_tick=ready, target_tick=edge, notification_tick=actual))
    return dict(qualified=bool(pacing['qualified'] and samples), count=count, aligned=aligned, software=software,
        fallback=fallback, missed=missed, first=first, last=last, tail_lines=tail, samples=samples)


def after_restore(execution, plan, result, before, code):
    trial = scope.TRIAL
    stage.parent.after_restore(execution, plan, result, before, code, trial_scope=scope)
    local = execution/f'scanout-comparison-0380-0381-{trial}.json'
    if not local.is_file():
        return
    try:
        trace.require(result['independent_restore_verified'], '0388 comparison requires independent restoration')
        old, new = (scope.load(path) for path in (scope.COMPARISON,local))
        raw, rows, strokes, n, d, latches, scans = stage.measure(execution,new,trial=trial)
        old_raw, old_rows, old_strokes, old_n, old_d, old_latches, old_scans = stage.measure(
            scope.REFERENCE,old,trial='0384')
        resume, = (row for row in rows[CALIBRATION] if row.id >> 32 == 4 and row.flags == 1)
        motion = stage.staging.score.parse_motion(raw,strokes,n,d,dict(qualified=True,resume_tick=resume.tick))
        start, end, _, _ = native.envelope(raw)
        pacing = phase.phase(raw,rows,start,end,strokes,motion,n,d)
        receipt = deadline_receipts(raw,pacing)
        early = stage.staging.early_timing(raw,rows,latches,n,d)
        first_frames = {
            '0384':stage.staging.first_frames(scope.REFERENCE,old_raw,old_rows,old_strokes,old_n,old_d,old_scans,old_latches),
            trial:stage.staging.first_frames(execution,raw,rows,strokes,n,d,scans,latches)}
        gpu = executor.module('matched_moving_gpu',scope.MOTION_ANALYZER)
        moving = {'0384':gpu.measure(old_rows,old_scans,old_n,old_d), trial:gpu.measure(rows,scans,n,d)}
        paired = stage.parent.parent.parent.paired_ordinals({'0384':old_scans,trial:scans})
        report = dict(state='0384-0388-compared-after-independent-restore',per_scan=paired,
            metrics={'0384':old['metrics'],trial:new['metrics']}, onset={'0384':old['onset'],trial:new['onset']},
            first_ordinary_frames=first_frames, moving_GPU=moving, ca_phase=pacing, deadline_dispatch=receipt,
            early_staging=early, hardware_refresh_hz_bounds=new['hardware_refresh_hz_bounds'],
            CRC_control=new['crc_control'], drag_repeats=new['slow_drag_repeat_waits'])
        output = execution/'scanout-comparison-0384-0388.json'
        stage.save_bounded(output,report,2_000_000)
    except (KeyError, OSError, ValueError) as error:
        result.update(state='0388-physical-capture-with-incomplete-deadline-comparison-root-restored',
                      deadline_comparison_error=str(error))
        return
    result.update(comparison=output.name, early_staging=early, first_frame_trace_qualified=True,
        moving_GPU_qualified=True, deadline_dispatch={key:value for key,value in receipt.items() if key!='samples'})
    if not receipt['qualified']:
        result['state'] = '0388-physical-comparison-with-unqualified-deadline-phase-root-restored'


if __name__ == '__main__':
    raise SystemExit(runner.main(scope, after_restore_fn=after_restore))
