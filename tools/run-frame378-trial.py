#!/usr/bin/env python3
"""Run the bounded 0378 trial and verify the restored scanout and memory phases."""

from importlib import import_module

import frame378_memory as memory

scope = import_module('prepare-frame378')
parent = import_module('run-frame377-trial')
runner = parent.runner
trace = parent.trace
score = parent.score
load,require = scope.load,scope.require


def analyze(execution,plan,frame,display,rows,inputs):
    report = parent.analyze(execution,plan,frame,display,rows,inputs)
    old = load(scope.COMPARISON)
    baseline = load(scope.P375/'partial-audit-0375.json')
    # The inherited scorer names the current display rows 0377. Join the
    # independent real 0377 control only after replacing that alias.
    for key in ('metrics','guard','copy'):
        inherited = report[key]
        report[key] = {'0375':inherited['0375'],'0377':old[key]['0377'],'0378':inherited['0377']}
    report['per_scan'] = parent.paired_ordinals({'0375':baseline['native_alignment']['scans'],
        '0377':old['native']['scans'],'0378':report['native']['scans']})
    raw = (execution/'kernel.log').read_text()
    start,_,n,d = parent.envelope(raw)
    _,strokes,_,_ = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
    try:
        require(report['copy_phases']['full_capture_qualified'],'memory probes require exact full copy phases')
        measured = memory.analyze(raw,report['copy_phases'],start,n,d,strokes)
        probe_attempts = {row['attempt'] for row in measured['rows']}
        for row in report['copy']['0378']['check_failed']:
            row['memory_sampled'] = row['attempt'] in probe_attempts
        report['memory_phases'] = measured
    except ValueError as error:
        report['memory_phases'] = dict(qualified=False,error=str(error))
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
            'slot extent or panel route differs')
        report = analyze(execution,plan,frame,display,rows,inputs)
    except (KeyError,ValueError) as error:
        result.update(state='0378-frame-comparison-incomplete-root-restored',frame_error=str(error))
        return
    parent.previous.timeline.write(execution/'scanout-comparison-0375-0378.json',report,5_000_000)
    physical,native = report['physical_score_qualified'],report['system_present_alignment_qualified']
    timings,ipc = report['copy_phases'],report['transport']
    memory = report['memory_phases']
    complete = physical and native and timings['full_capture_qualified'] and ipc['qualified'] and memory['qualified']
    result.update(state=scope.SUCCESS if complete else '0378-partially-qualified-root-restored',
        frame_trace_complete=True,dpu_new_content_FPS_qualified=physical,system_present_alignment_qualified=native,
        stable_60_fps_observed=report['stable_60_fps_observed'],
        hardware_refresh_hz_bounds=report['hardware_refresh_hz_bounds'],compared=report['metrics'],
        copy=report['copy']['0378'],copy_phases={k:v for k,v in timings.items() if k!='rows'},
        memory_phases={k:v for k,v in memory.items() if k!='rows'},
        ipc={k:ipc[k] for k in ('qualified','counters','table','error') if k in ipc},
        frame_info=report['native']['frame_info'],fence_and_lifetime_verified=retained['issued_with_exact_claim'])


if __name__=='__main__':
    raise SystemExit(runner.main(scope,after_restore_fn=after_restore))
