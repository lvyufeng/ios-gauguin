#!/usr/bin/env python3
"""Run the frozen 0384 trial and compare exact CRC changes against 0383."""

from importlib import import_module

from frame357_display import CALIBRATION
import frame380_phase as phase
import frame384_stage as staging

scope = import_module('prepare-frame384')
parent = import_module('run-frame382-trial')
save_bounded = parent.timeline.write


def measure(execution, report, *, trial):
    raw = (execution/'kernel.log').read_text()
    rows,strokes,n,d = staging.parse(raw)
    latches = staging.verified_latches(rows,parent.latch_receipts(raw,rows)['accepted_by_scan'])
    scans = staging.trial_rows(report,trial)
    return raw,rows,strokes,n,d,latches,scans


def after_restore(execution, plan, result, before, code):
    parent.after_restore(execution,plan,result,before,code,trial_scope=scope)
    comparison = execution/'scanout-comparison-0380-0381-0384.json'
    if not comparison.is_file():
        return
    try:
        scope.require(result['independent_restore_verified'], 'stage audit requires independent restore')
        old, candidate = (scope.load(path) for path in (scope.COMPARISON,comparison))
        raw,rows,strokes,n,d,latches,scans = measure(execution,candidate,trial=scope.TRIAL)
        start,end,*_ = parent.parent.parent.envelope(raw)
        resume, = (row for row in rows[CALIBRATION] if row.id>>32==4 and row.flags==1)
        motion = staging.score.parse_motion(raw,strokes,n,d,dict(qualified=True,resume_tick=resume.tick))
        pacing = phase.phase(raw,rows,start,end,strokes,motion,n,d)
        stages = staging.early_timing(raw,rows,latches,n,d)
        ref_raw,ref_rows,ref_strokes,ref_n,ref_d,ref_latches,reference_scans = measure(
            scope.REFERENCE,old,trial='0383')
        paired = parent.parent.parent.paired_ordinals({'0383':reference_scans,'0384':scans})
    except (ValueError, OSError, KeyError) as error:
        result.update(state='0384-flip-proof-or-activation-incomplete-root-restored',stage_measurement_error=str(error))
        return
    report = dict(state='0384-compared-to-0383-after-independent-restoration',per_scan=paired,
        metrics={'0383':old['metrics'],'0384':candidate['metrics']},
        onset={'0383':old['onset'],'0384':candidate['onset']},early_staging=stages,ca_phase=pacing,
        hardware_refresh_hz_bounds=candidate['hardware_refresh_hz_bounds'],
        slow_drag={'0383':old['slow_drag_repeat_waits'],'0384':candidate['slow_drag_repeat_waits']})
    try:
        report['first_ordinary_frames'] = {
            '0383':staging.first_frames(scope.REFERENCE,ref_raw,ref_rows,ref_strokes,ref_n,ref_d,
                                       reference_scans,ref_latches),
            '0384':staging.first_frames(execution,raw,rows,strokes,n,d,scans,latches)}
    except (ValueError, OSError, KeyError) as error:
        report['first_frame_trace_error'] = str(error)
    save_bounded(execution/'scanout-comparison-0383-0384.json',report,2_000_000)
    result.update(early_staging=stages,ca_phase={k:v for k,v in pacing.items() if k!='pulses'},
        first_frame_trace_qualified='first_ordinary_frames' in report,
        comparison='scanout-comparison-0383-0384.json')
    if not pacing['qualified']:
        result.update(state='0384-private-staging-and-CRC-verified-CA-phase-incomplete-root-restored')


if __name__=='__main__':
    raise SystemExit(parent.parent.runner.main(scope,after_restore_fn=after_restore))
