#!/usr/bin/env python3
"""Measure restored 0379 and compare CRC, read segments and observed GPU overlap."""

from importlib import import_module
import frame379_concurrency as concurrency

scope=import_module('prepare-frame379')
parent=import_module('run-frame377-trial')
runner=parent.runner
trace=parent.trace
score=parent.score
load,require=scope.load,scope.require


def analyze(execution,plan,frame,display,rows,inputs):
    report=parent.analyze(execution,plan,frame,display,rows,inputs)
    limit=plan['native_CA']['compact_binary_limit']
    require(report['native']['capture']['wire_bytes']<=limit,'0379 dedicated FrameInfo cap differs')
    prior=load(scope.COMPARISON)
    base=load(scope.P375/'partial-audit-0375.json')
    for name in ('metrics','guard','copy'):
        observed=report[name]
        report[name]={'0375':observed['0375'],'0378':prior[name]['0378'],'0379':observed['0377']}
    report['per_scan']=parent.paired_ordinals({'0375':base['native_alignment']['scans'],
        '0378':prior['native']['scans'],'0379':report['native']['scans']})
    raw=(execution/'kernel.log').read_text()
    start,end,n,d=parent.envelope(raw)
    _,strokes,_,_=trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    try:
        require(report['copy_phases']['full_capture_qualified'],'lack of full copy timings for segment joins')
        data=concurrency.analyze(raw,rows,report['copy_phases'],start,end,n,d,strokes,
                                 report['copy']['0379']['check_failed'])
        old_raw=(scope.REFERENCE/'kernel.log').read_text()
        old_start,old_end,old_n,old_d=parent.envelope(old_raw)
        old_rows,old_strokes,_,_=trace.parse(old_raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
        old_gpu=concurrency.gpu_intervals(old_rows,old_end)
        old_copy=prior['copy_phases']['rows']
        old_bad=prior['copy']['0378']['check_failed']
        data['reference_0378']=dict(retest=concurrency.retest(old_copy,old_start,old_n,old_d,old_strokes,old_gpu,bad=old_bad),
            copy_overlap=concurrency.copy_overlap(old_copy,old_gpu,old_bad))
        report['concurrency']=data
    except ValueError as error:
        report['concurrency']=dict(qualified=False,error=str(error))
    return report


def after_restore(execution,plan,result,before,code):
    collected=runner.prior.collect_after_restore(execution,plan,result,before,code,trial=scope.TRIAL,
        extra_kinds=(runner.PROBE,runner.LOCK_RETRY),join_tail_copy=True,
        display_options=dict(copy_budget_ns=plan['copy_diagnostics']['required_early_lead_ns']))
    if collected is None:
        return
    frame,display,_,rows,retained,_,inputs=collected
    try:
        proof=load(execution/'independent-restore.json')
        slots=load(scope.BASE/'slot-delta/install-plan.json')
        require(proof['files'][runner.audit.C4]['fork']['extents']==slots['rows']['c4']['data_extents'] and
            runner.decode_route((execution/'kernel.log').read_text())['route']['pipe']=='VIG0',
            'slot extent or panel route differs')
        report=analyze(execution,plan,frame,display,rows,inputs)
    except (KeyError,ValueError) as error:
        result.update(state='0379-frame-comparison-incomplete-root-restored',frame_error=str(error))
        return
    parent.previous.timeline.write(execution/'scanout-comparison-0375-0379.json',report,5_000_000)
    physical,native=report['physical_score_qualified'],report['system_present_alignment_qualified']
    timing,ipc,diagnostic=report['copy_phases'],report['transport'],report['concurrency']
    complete=physical and native and timing['full_capture_qualified'] and ipc['qualified'] and diagnostic['qualified']
    result.update(state=scope.SUCCESS if complete else '0379-partially-qualified-root-restored',
        frame_trace_complete=True,dpu_new_content_FPS_qualified=physical,system_present_alignment_qualified=native,
        stable_60_fps_observed=report['stable_60_fps_observed'],
        hardware_refresh_hz_bounds=report['hardware_refresh_hz_bounds'],compared=report['metrics'],
        copy=report['copy']['0379'],copy_phases={k:v for k,v in timing.items() if k!='rows'},
        concurrency={k:v for k,v in diagnostic.items() if k not in ('segments','deferrals')},
        ipc={k:ipc[k] for k in ('qualified','counters','table','error') if k in ipc},
        frame_info=report['native']['frame_info'],fence_and_lifetime_verified=retained['issued_with_exact_claim'])


if __name__=='__main__':
    raise SystemExit(runner.main(scope,after_restore_fn=after_restore))
