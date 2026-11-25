#!/usr/bin/env python3
"""Score scanout and the CA cadence only after verified 0380 restoration."""

from importlib import import_module

import frame379_concurrency as segments
import frame380_phase as timing

scope = import_module('prepare-frame380')
parent = import_module('run-frame377-trial')
runner,trace,score = parent.runner,parent.trace,parent.score
load,require = scope.load,scope.require


def analyze(execution,plan,frame,display,rows,inputs):
    report = parent.analyze(execution,plan,frame,display,rows,inputs)
    require(report['native']['capture']['wire_bytes']<=plan['native_CA']['compact_binary_limit'],
            '0380 dedicated FrameInfo cap differs')
    before = load(scope.COMPARISON)
    base = load(scope.P375/'partial-audit-0375.json')
    for key in ('metrics','copy','guard'):
        values = report[key]
        report[key] = {'0375':values['0375'],'0379':before[key]['0379'],'0380':values['0377']}
    scans = {'0375':base['native_alignment']['scans'],'0379':before['native']['scans'],
             '0380':report['native']['scans']}
    frames = {'0375':load(scope.P375/'execution/frame-scanout-analysis.json'),
              '0379':load(scope.REFERENCE/'frame-scanout-analysis.json'),'0380':frame}
    report['per_scan'] = parent.paired_ordinals(scans)
    report['onset'] = {key:timing.onset(lane,frames[key]) for key,lane in scans.items()}
    raw = (execution/'kernel.log').read_text()
    start,end,n,d = parent.envelope(raw)
    strokes = [tuple(pair) for pair in frame['strokes']]
    motion = score.parse_motion(raw,strokes,n,d,frame['crc_frame_calibration'])
    try:
        report['ca_phase'] = timing.phase(raw,rows,start,end,strokes,motion,n,d)
    except ValueError as error:
        report['ca_phase'] = dict(qualified=False,error=str(error))
    try:
        require(report['copy_phases']['full_capture_qualified'],'copy timing capture is incomplete')
        detail = segments.analyze(raw,rows,report['copy_phases'],start,end,n,d,strokes,
                                  report['copy']['0380']['check_failed'])
        require(not detail['deferrals'],'0380 used the 0379 deferral policy')
        report['segments'] = detail
    except ValueError as error:
        report['segments'] = dict(qualified=False,error=str(error))
    return report


def after_restore(execution,plan,result,before,code):
    collected = runner.prior.collect_after_restore(execution,plan,result,before,code,trial=scope.TRIAL,
        extra_kinds=(runner.PROBE,runner.LOCK_RETRY),join_tail_copy=True,
        display_options=dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns']))
    if collected is None:
        return
    frame,display,_,rows,retained,_,inputs = collected
    try:
        proof = load(execution/'independent-restore.json')
        slots = load(scope.BASE/'slot-delta/install-plan.json')
        require(proof['files'][runner.audit.C4]['fork']['extents']==slots['rows']['c4']['data_extents'] and
                runner.decode_route((execution/'kernel.log').read_text())['route']['pipe']=='VIG0',
                'slot extents or DPU route differ')
        report = analyze(execution,plan,frame,display,rows,inputs)
    except (KeyError,ValueError) as error:
        result.update(state='0380-frame-comparison-incomplete-root-restored',frame_error=str(error))
        return
    parent.previous.timeline.write(execution/'scanout-comparison-0375-0379-0380.json',report,5_000_000)
    physical,native = report['physical_score_qualified'],report['system_present_alignment_qualified']
    phase,ipc,copy = report['ca_phase'],report['transport'],report['copy_phases']
    complete = physical and native and phase['qualified'] and ipc['qualified'] and copy['full_capture_qualified'] and report['segments']['qualified']
    result.update(state=scope.SUCCESS if complete else '0380-partially-qualified-root-restored',
        frame_trace_complete=True,dpu_new_content_FPS_qualified=physical,system_present_alignment_qualified=native,
        stable_60_fps_observed=report['stable_60_fps_observed'],hardware_refresh_hz_bounds=report['hardware_refresh_hz_bounds'],
        compared=report['metrics'],onset={k:{name:v[name] for name in ('ordinary','warm')} for k,v in report['onset'].items()},
        ca_phase={k:v for k,v in phase.items() if k!='pulses'},copy=report['copy']['0380'],
        frame_info=report['native']['frame_info'],fence_and_lifetime_verified=retained['issued_with_exact_claim'],
        segment_capture_qualified=report['segments']['qualified'],IPC_capture_qualified=ipc['qualified'])


if __name__=='__main__':
    raise SystemExit(runner.main(scope,after_restore_fn=after_restore))
