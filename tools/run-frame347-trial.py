#!/usr/bin/env python3
"""Run the frozen 0347 diagnostic once after exact approval."""

import argparse
from importlib import import_module
import json
import subprocess
import sys

import frame345_log as scanout
from frame347_scope import BASE, FLAGS, MAIN, REFERENCE, REFERENCE_RESULT, RESERVE, SUCCESS
from frame347_scope import expected_plan, load, require, sha


EXEC = BASE/'execution'
shared = import_module('run-frame345-trial')


def authorization(run, *, base=BASE, trial='0347', expected=expected_plan, flags=FLAGS, reserve=RESERVE):
    require(not (base/'execution').exists() and (base/'approval.json').is_file(),
            trial+' already claimed or lacks exact authorization')
    plan, ready, review = (load(base/name) for name in ('trial-plan.json','ready.json','final-review.json'))
    require(plan==expected() and ready['state']==f'ready-frame{int(trial)}-one-shot' and
            ready['trial_plan_sha256']==sha(base/'trial-plan.json') and ready['pin_count']==len(ready['input_pins']) and
            ready['install_plan_sha256']==plan['install_plan_sha256'] and ready['image_sha256']==plan['image_sha256'],
            'frozen '+trial+' inputs differ')
    approval = load(base/'approval.json')
    run.check_consent(approval,ready,plan,trial=trial,flags=flags)
    require(review['state']==f'reviewed-frame{int(trial)}-one-shot' and review['ready_sha256']==sha(base/'ready.json') and
            review['restore_precedes_analysis'] and review['no_device_mutation_during_preparation'],
            'unqualified '+trial+' review')
    for name,digest in {**ready['input_pins'], **review['input_pins']}.items():
        require(sha(name)==digest, 'frozen input changed: '+name)
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
                                             '--planned-bytes',str(reserve)],text=True,timeout=600))
    require(budget['admitted'] and budget['current_accounted_bytes']+reserve<=budget['limit_bytes'],
            trial+' runtime storage reservation unavailable')
    return plan,approval,budget


def job_times(rows):
    warm = [row for row in rows if not row['newbo_counts'][0]]
    all_ns, record_ns, commit_ns = [], [], []
    for row in warm:
        total = row['own_exec_ns']
        commit = row['exec_ns'][6]
        require(0<=commit<=total==sum(row['exec_ns']), 'recording and commit partition differs')
        all_ns.append(total)
        record_ns.append(total-commit)
        commit_ns.append(commit)
    return dict(submits=len(rows),warm_jobs=len(warm),
                native_program_BO_calls=sum(row['newbo_counts'][0] for row in rows),
                program_slab_reuses=sum(row['program_slab_reuses'] for row in rows),
                recording_and_commit_ns=shared.percentile(all_ns),
                recording_only_ns=shared.percentile(record_ns),commit_only_ns=shared.percentile(commit_ns),
                largest_warm_job_ns=max(all_ns,default=None),
                warm_jobs_above_60_fps_budget=sum(ns*60>1_000_000_000 for ns in all_ns))


def lane_comparison(rows, joins, frame):
    key = lambda row: (row['queue'],row['ticket'],row['job'])
    matching = {key(row) for row in joins}
    selected = [row for row in rows if key(row) in matching]
    require(len(selected)==len(joins)>0, 'missing or duplicate Core/IO identities')
    scale = frame['tick_numer']/frame['tick_denom']/1000
    release = [(begin*scale,end*scale)
               for i,kind,begin,end in scanout.windows(frame['strokes'],frame['tick_numer'],frame['tick_denom'])
               if i<12 and kind=='release']
    return dict(full_script=job_times(selected),
                first_250ms_after_release=job_times([row for row in selected
                    if any(a<=row['made_us']<b for a,b in release)]))


def trial_summary(path, verdict, trace, core, submits):
    metric = import_module('compare-runtime343').trial_metrics
    strokes, numer, denom = (trace[k] for k in ('strokes','tick_numer','tick_denom'))
    phases = shared.phases(core,submits,strokes,numer,denom)
    for values in [phases['full_script'],phases['first_250ms_after_release'],
                   *(window['metrics'] for window in phases['windows'])]:
        values['own_recording_and_commit_us'] = values.pop('own_recording_execution_us')
    return dict(queues=metric(path,verdict),execution=phases,warm_lanes=lane_comparison(core,submits,trace),
                frames=shared.present_by_window(trace['attempts'],strokes,numer,denom,after_final_release=True),
                hardware={k:v for k,v in trace['hardware'].items() if k!='windows'})


def compare(execution, result, frame, rows, joins):
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT, '0346 comparison provenance differs')
    previous = load(REFERENCE/'result.json')
    require(previous['independent_restore_verified'] and previous['static_root_comparison_passed'],
            '0346 baseline was not independently restored')
    before = trial_summary(REFERENCE,previous,load(REFERENCE/'frame-scanout-analysis.json'),
                           load(REFERENCE/'core-wait-execution-analysis.json')['rows'],
                           load(REFERENCE/'kernel-IO-identity-analysis.json')['submits'])
    current = trial_summary(execution,result,frame,rows,joins)
    report = dict(state='0347-vs-0346-matched-script',previous=before,current=current,
                  alignment='Stroke ordinal and phase-relative time; queue, IO, GPU and surface IDs are boot-local.',
                  timing_scope='Own completed Core job times already include commit and exclude queue residence.')
    shared.write(execution/'comparison-0346.json',report,2_000_000)
    return {name:r['warm_lanes']['first_250ms_after_release'] for name,r in
            (('previous',before),('current',current))}


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede collection and interpretation')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=shared.CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    rows = load(execution/'core-wait-execution-analysis.json')['rows']
    joins = load(execution/'kernel-IO-identity-analysis.json')['submits']
    try:
        frame = scanout.analyze((execution/'kernel.log').read_text(),joins,rows)
    except ValueError as error:
        result.update(state='0347-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    shared.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    hardware = {k:v for k,v in frame['hardware'].items() if k!='windows'}
    result.update(dpu_probe=frame['dpu_probe'],hardware_scanout=hardware,frame_trace_complete=True,
                  core_linked_layers=frame['core_linked_layers'],physical_FPS_qualified=False,
                  after_release_0346_0347=compare(execution,result,frame,rows,joins))
    result['state'] = (SUCCESS if hardware['complete_crc_coverage'] else
                       '0347-collection-qualified-hardware-coverage-incomplete-root-restored')


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan, approval, budget = authorization(run)
    except (Exception,KeyboardInterrupt) as error:
        print('0347 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0347 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0347',
                       after_restore=after_restore,success_state=SUCCESS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
