#!/usr/bin/env python3
"""Run the explicitly approved, reviewed 0346 experiment once."""
import argparse
from importlib import import_module
import json
import subprocess
import sys

import frame344_log as frames
import frame345_log as scanout
from frame346_scope import BASE, FLAGS, MAIN, P345, RESERVE, SUCCESS, expected_plan, load, require, sha

shared = import_module('run-frame345-trial')
EXEC = BASE/'execution'


def authorization(run):
    require(not EXEC.exists() and (BASE/'approval.json').is_file(),'0346 already claimed or lacks exact authorization')
    plan,ready,review=(load(BASE/name) for name in ('trial-plan.json','ready.json','final-review.json'))
    require(plan==expected_plan() and ready['state']=='ready-frame346-one-shot' and
            ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and ready['pin_count']==len(ready['input_pins']) and
            ready['install_plan_sha256']==plan['install_plan_sha256'] and ready['image_sha256']==plan['image_sha256'],
            'frozen 0346 inputs differ')
    approval=load(BASE/'approval.json')
    run.check_consent(approval,ready,plan,trial='0346',flags=FLAGS)
    require(review['state']=='reviewed-frame346-one-shot' and review['ready_sha256']==sha(BASE/'ready.json') and
            review['restore_precedes_analysis'] and review['no_device_mutation_during_preparation'],'unqualified review')
    for name,digest in {**ready['input_pins'],**review['input_pins']}.items():
        require(sha(name)==digest,'frozen input changed: '+name)
    budget=json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
                                             '--planned-bytes',str(RESERVE)],text=True,timeout=600))
    require(budget['admitted'] and budget['current_accounted_bytes']+RESERVE<=budget['limit_bytes'],
            'runtime storage reservation unavailable')
    return plan,approval,budget


def program_timings(core, joins, strokes, numer, denom):
    keys={(q['queue'],q['ticket'],q['job']) for q in joins}
    selected=[row for row in core if (row['queue'],row['ticket'],row['job']) in keys]
    require(len(selected)==len(joins),'incomplete 0346 program comparison')
    releases=[(a*numer/denom/1000,b*numer/denom/1000) for i,w,a,b in scanout.windows(strokes,numer,denom)
              if i<12 and w=='release']
    pct=shared.percentile

    def summarize(rows):
        cold=[row for row in rows if row['newbo_counts'][0]]
        warm=[row for row in rows if not row['newbo_counts'][0]]
        def lanes(items):
            return {key:pct([x[key] for x in items]) for key in
                    ('core_queue_wait_us','own_recording_execution_us','own_commit_us','commit_done_us')}
        return dict(submits=len(rows),allocating_submits=len(cold),native_program_BO_calls=sum(x['newbo_counts'][0] for x in cold),
            slab_reuses=sum(x.get('program_slab_reuses',0) for x in rows),
            native_program_BO_ns=pct([sum(x['newbo_wall'])+x['newbo_counts'][4] for x in cold]),
            native_program_BO_max_ns=max((x['newbo_max'][5]-x['newbo_max'][4] for x in cold),default=None),
            warm=lanes(warm),cold=lanes(cold))
    return dict(full_script=summarize(selected),first_250ms_after_release=summarize(
        [row for row in selected if any(a<=row['made_us']<b for a,b in releases)]))


def comparison(execution, result, analysis, core, joins):
    prior=P345/'execution'
    previous=load(prior/'result.json')
    _,old_strokes,old_num,old_den=frames.parse((prior/'kernel.log').read_text())
    old_core=load(prior/'core-wait-execution-analysis.json')['rows']
    old_joins=load(prior/'kernel-IO-identity-analysis.json')['submits']
    old_attempts=load(prior/'frame-scanout-analysis.json')['attempts']
    metric=import_module('compare-runtime343').trial_metrics
    strokes,num,den=(analysis[k] for k in ('strokes','tick_numer','tick_denom'))

    def summary(path, verdict, rows, submits, windows, numer, denom, attempts, final):
        return dict(queues=metric(path,verdict),execution=shared.phases(rows,submits,windows,numer,denom),
                    program_BO=program_timings(rows,submits,windows,numer,denom),
                    frame_windows=shared.present_by_window(attempts,windows,numer,denom,after_final_release=final))

    report=dict(state='0346-vs-0345-matched-script',
                previous=summary(prior,previous,old_core,old_joins,old_strokes,old_num,old_den,old_attempts,False),
                current=summary(execution,result,core,joins,strokes,num,den,analysis['attempts'],True),
                baseline_hardware_FPS=None,
                alignment='Same stroke ordinal and phase-relative time; queue, ticket, IO, GPU and surface identities are per boot.')
    shared.write(execution/'comparison-0345.json',report,2_000_000)
    return {k:report[k]['program_BO']['first_250ms_after_release'] for k in ('previous','current')}


def after_restore(execution,plan,result,before,code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede collection and interpretation')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=shared.CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    core=load(execution/'core-wait-execution-analysis.json')['rows']
    joins=load(execution/'kernel-IO-identity-analysis.json')['submits']
    try:
        analysis=scanout.analyze((execution/'kernel.log').read_text(),joins,core)
    except ValueError as error:
        result.update(state='0346-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    shared.write(execution/'frame-scanout-analysis.json',analysis,8_000_000)
    hardware={k:v for k,v in analysis['hardware'].items() if k!='windows'}
    result.update(dpu_probe=analysis['dpu_probe'],hardware_scanout=hardware,frame_trace_complete=True,
                  core_linked_layers=analysis['core_linked_layers'],physical_FPS_qualified=False,
                  after_release_0345_0346=comparison(execution,result,analysis,core,joins))
    result['state']=SUCCESS if hardware['complete_crc_coverage'] else '0346-collection-qualified-hardware-coverage-incomplete-root-restored'


def main(check_gate=False):
    run=import_module('run-core342-trial')
    try:
        plan,approval,budget=authorization(run)
    except (Exception,KeyboardInterrupt) as error:
        print('0346 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0346 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0346',
                       after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
