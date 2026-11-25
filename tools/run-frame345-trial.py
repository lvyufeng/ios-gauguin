#!/usr/bin/env python3
"""Execute a reviewed, separately authorized 0345 trial once."""

import argparse
from importlib import import_module
import json
import subprocess
import sys

import frame344_log as frames
import frame345_log as scanout
from frame345_scope import BASE, FLAGS, MAIN, P344, RESERVE, SUCCESS, expected_plan, load, require, sha
from kernel342_log import PHASES


EXEC = BASE/'execution'
CORE_PASSED = 'CR342-lossless-wait-execution-observed-root-restored'


def authorization(run):
    require(not EXEC.exists() and (BASE/'approval.json').is_file(), '0345 trial already claimed or its authorization is absent')
    plan, ready, review = (load(BASE/name) for name in ('trial-plan.json','ready.json','final-review.json'))
    require(plan==expected_plan() and ready['state']=='ready-frame345-one-shot' and
            ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and ready['pin_count']==len(ready['input_pins']) and
            ready['install_plan_sha256']==plan['install_plan_sha256'] and ready['image_sha256']==plan['image_sha256'],
            'frozen 0345 inputs differ')
    approval = load(BASE/'approval.json')
    run.check_consent(approval,ready,plan,trial='0345',flags=FLAGS)
    require(review['state']=='reviewed-frame345-one-shot' and review['ready_sha256']==sha(BASE/'ready.json') and
            review['restore_precedes_analysis'] and review['no_device_mutation_during_preparation'], 'unqualified review')
    for name, digest in {**ready['input_pins'],**review['input_pins']}.items():
        require(sha(name)==digest,'frozen input changed: '+name)
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
                                                '--planned-bytes',str(RESERVE)],text=True,timeout=600))
    require(budget['admitted'] and budget['current_accounted_bytes']+RESERVE<=budget['limit_bytes'],
            'runtime storage reservation unavailable')
    return plan,approval,budget


def write(path, result, limit):
    content = (json.dumps(result,separators=(',',':'))+'\n').encode()
    require(len(content)<=limit,'analysis file exceeds reserved bytes: '+path.name)
    with path.open('xb') as stream:
        stream.write(content)


def phases(core, joins, strokes, numer, denom):
    key = lambda row:(row['queue'],row['ticket'],row['job'])
    by_key = {key(row):row for row in joins}
    selected = [(row,by_key[key(row)]) for row in core if key(row) in by_key]
    require(len(selected)==len(joins)>0,'Core/IO joins incomplete')
    names = ('command_validation','surface_alias_validation','escrow','surface_cache_flush','runtime_issue')
    filters = [(i,which,a*numer/denom/1000,b*numer/denom/1000)
               for i,which,a,b in scanout.windows(strokes,numer,denom)
               if i<12 or which=='active']  # exact joins end at the thirteenth release

    def summarize(items):
        quantiles = {}
        for key in ('core_queue_wait_us','own_render_us','own_recording_execution_us','own_commit_us',
                    'commit_done_us','wait_render_us','wait_commit_us'):
            quantiles[key] = percentile([row[key] for row,_ in items])
        quantiles['encode_and_packet_ns'] = percentile([sum(row['render_ns'][4:6]) for row,_ in items])
        for name in names:
            index = PHASES[70].index(name)
            selected_phases = [submit['phases'][index] for _,submit in items]
            quantiles[name] = {key:percentile([p[key] for p in selected_phases])
                               for key in ('wall_ns','CPU_lower_ns','CPU_upper_ns')}
        return dict(count=len(items),**quantiles)

    release_items = []
    windows = []
    for ordinal,kind,a,b in filters:
        subset = [(row,submit) for row,submit in selected if a<=row['made_us']<b]
        if kind=='release':
            release_items.extend(subset)
        windows.append(dict(stroke=ordinal,window=kind,metrics=summarize(subset)))
    return dict(full_script=summarize(selected), first_250ms_after_release=summarize(release_items),windows=windows)


def percentile(values):
    return {f'p{int(p*100)}':frames.quantile(values,p) for p in (.50,.95,.99)} if values else None


def present_by_window(attempts, strokes, numer, denom, *, after_final_release=False):
    result = []
    for ordinal,kind,a,b in scanout.windows(strokes,numer,denom):
        if ordinal==12 and kind=='release' and not after_final_release:
            continue
        subset = [row for row in attempts if a<=row['attempt_tick']<b]
        layers = [layer for row in subset for layer in row['layers']]
        result.append(dict(stroke=ordinal, window=kind, attempts=len(subset),
                           refused_guards=sum(row['refused_guards'] for row in subset),
                           written_layers=len(layers), copy_ns=percentile([r['copy_ns'] for r in layers]),
                           lock_wait_ns=percentile([r['lock_wait_ns'] for r in layers]),
                           frame_attempts=[dict(attempt=r['attempt'], generation=r['generation'],
                                relative_attempt_ns=(r['attempt_tick']-a)*numer/denom) for r in subset]))
    return result


def compare(execution, verdict, analysis, core, joins):
    old = P344/'execution'
    previous_verdict = load(old/'result.json')
    _,old_strokes,old_numer,old_denom = frames.parse((old/'kernel.log').read_text())
    prior_core = load(old/'core-wait-execution-analysis.json')['rows']
    prior_joins = load(old/'kernel-IO-identity-analysis.json')['submits']
    prior_attempts = load(old/'frame-scanout-analysis.json')['attempts']
    complete = import_module('compare-runtime343').trial_metrics
    report = dict(state='0345-vs-0344-matched-script', alignment='same swipe ordinal and time relative to its phase',
                  previous=dict(queues=complete(old,previous_verdict),
                      execution=phases(prior_core,prior_joins,old_strokes,old_numer,old_denom),
                      frame_windows=present_by_window(prior_attempts,old_strokes,old_numer,old_denom)),
                  current=dict(queues=complete(execution,verdict),
                      execution=phases(core,joins,analysis['strokes'],analysis['tick_numer'],analysis['tick_denom']),
                      frame_windows=present_by_window(analysis['attempts'],analysis['strokes'],
                                   analysis['tick_numer'],analysis['tick_denom'],after_final_release=True)),
                  baseline_hardware_FPS=None,
                  identity_scope='Core queue, ticket and job; IO token; GPU native fence; surface and swap generation within each boot')
    write(execution/'comparison-0344.json',report,2_000_000)
    return {label:report[label]['execution']['first_250ms_after_release'] for label in ('previous','current')}


def after_restore(execution,plan,result,before,code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede collection and interpretation')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    core = load(execution/'core-wait-execution-analysis.json')['rows']
    joins = load(execution/'kernel-IO-identity-analysis.json')['submits']
    try:
        analysis = scanout.analyze((execution/'kernel.log').read_text(),joins,core)
    except ValueError as error:
        result.update(state='0345-frame-capture-rejected-root-restored', frame_capture_error=str(error))
        return
    write(execution/'frame-scanout-analysis.json',analysis,8_000_000)
    hardware = {key:value for key,value in analysis['hardware'].items() if key!='windows'}
    result.update(dpu_probe=analysis['dpu_probe'], frame_trace_complete=True, hardware_scanout=hardware,
                  core_linked_layers=analysis['core_linked_layers'],
                  after_release_0344_0345=compare(execution,result,analysis,core,joins), physical_FPS_qualified=False)
    result['state'] = (SUCCESS if hardware['complete_crc_coverage']
                       else '0345-collection-qualified-hardware-coverage-incomplete-root-restored')


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = authorization(run)
    except (Exception,KeyboardInterrupt) as error:
        print('0345 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0345 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0345',
                       after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
