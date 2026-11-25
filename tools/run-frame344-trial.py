#!/usr/bin/env python3
"""Execute the reviewed 0344 scope once, using the existing restore executor."""

import argparse
import importlib.util
import json
import subprocess
import sys

from frame344_log import analyze, quantile
from frame344_scope import BASE, FLAGS, MAIN, P343, RESERVE, SUCCESS, WORK
from frame344_scope import expected_plan, load, require, sha


EXEC = BASE/'execution'
CORE_PASSED = 'CR342-lossless-wait-execution-observed-root-restored'


def module(name):
    spec = importlib.util.spec_from_file_location(name, WORK/'tools'/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def authorization(run):
    require(not EXEC.exists(), '0344 execution already claimed')
    require((BASE/'approval.json').is_file(), '0344 individual approval absent')
    plan, ready, review = [load(BASE/name) for name in ('trial-plan.json','ready.json','final-review.json')]
    require(plan == expected_plan() and ready['state']=='ready-frame344-one-shot' and
            ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and ready['pin_count']==len(ready['input_pins']) and
            ready['install_plan_sha256']==plan['install_plan_sha256'] and ready['image_sha256']==plan['image_sha256'],
            'frozen 0344 inputs differ')
    approval = load(BASE/'approval.json')
    run.check_consent(approval,ready,plan,trial='0344',flags=FLAGS)
    require(review['state']=='reviewed-frame344-one-shot' and review['ready_sha256']==sha(BASE/'ready.json') and
            review['no_device_mutation_during_preparation'] and review['restore_precedes_analysis'],
            '0344 review missing or inconsistent')
    for name, digest in {**ready['input_pins'], **review['input_pins']}.items():
        require(sha(name)==digest, 'frozen input changed: '+name)
    result = subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),'--planned-bytes',str(RESERVE)],
                            capture_output=True,text=True,check=True,timeout=600)
    budget = json.loads(result.stdout)
    require(budget['admitted'] and budget['current_accounted_bytes']+RESERVE <= budget['limit_bytes'],
            'complete runtime reservation unavailable')
    return plan,approval,budget


def output(path,value,limit):
    raw = (json.dumps(value,indent=2)+'\n').encode()
    require(len(raw)<=limit,'analysis exceeds reserved bytes')
    with path.open('xb') as stream:
        stream.write(raw)


def encoding(rows, joins):
    keys = {(r['queue'],r['ticket'],r['job']) for r in joins}
    selected = [r['render_ns'] for r in rows if (r['queue'],r['ticket'],r['job']) in keys]
    require(selected,'missing render timing')
    fields = {'encode_ns': [r[4] for r in selected],
              'packets_ns': [r[5] for r in selected],
              'encode_and_packets_ns': [r[4]+r[5] for r in selected]}
    return dict(available_rows=len(selected), join_rows=len(keys),
                **{name:{'p50':quantile(values,.5),'p95':quantile(values,.95),
                         'p99':quantile(values,.99),'max':max(values)} for name,values in fields.items()})


def comparison(execution, verdict, core, joins):
    reference = P343/'post-analysis-prefix-v1'
    previous = load(reference/'runtime343-comparison.json')['candidate_0343']
    prior_joins = load(reference/'comparison-inputs/kernel-IO-identity-analysis.json')['submits']
    prior_core = load(P343/'execution/core-wait-execution-analysis.json')['rows']
    current = module('compare-runtime343').trial_metrics(execution, verdict)
    report = dict(state='0344-vs-0343-same-13-strokes', previous=previous, current=current,
                  baseline_encode=encoding(prior_core,prior_joins), candidate_encode=encoding(core,joins),
                  baseline_encode_missing_row_policy='Use only individually parsed 0343 rows',
                  cross_boot_alignment='matched script and stroke ordinal',
                  separate_physical_FPS_measurement=True)
    output(execution/'comparison-0343.json',report,2_000_000)
    return dict(reference_queue_p95_us=previous['full_script']['core_queue_wait_us']['p95'],
                candidate_queue_p95_us=current['full_script']['core_queue_wait_us']['p95'],
                baseline_encode=report['baseline_encode'],candidate_encode=report['candidate_encode'])


def after_restore(execution,plan,verdict,before,code):
    require(verdict['restored'] and verdict['independent_restore_verified'] and
            verdict['static_root_comparison_passed'], 'restore and independent readback must precede capture analysis')
    module('analyze-core342').analyze_saved(execution,plan,verdict,before,code)
    if verdict['state'] != CORE_PASSED:
        verdict['frame_measurement'] = 'withheld-by-core-collection-gate'
        return
    core = load(execution/'core-wait-execution-analysis.json')['rows']
    joins = load(execution/'kernel-IO-identity-analysis.json')['submits']
    verdict['comparison_0343'] = comparison(execution,verdict,core,joins)
    try:
        analysis = analyze((execution/'kernel.log').read_text(),joins,core)
    except ValueError as problem:
        verdict.update(state='0344-frame-capture-rejected-root-restored', frame_capture_error=str(problem))
        return
    output(execution/'frame-scanout-analysis.json',analysis,8_000_000)
    hardware = {k:v for k,v in analysis['hardware'].items() if k!='strokes'}
    verdict.update(state=SUCCESS, frame_trace_complete=True,
                   core_linked_layers=analysis['core_linked_layers'], hardware_scanout=hardware,
                   physical_FPS_qualified=False)  # optical output is not sampled


def main(check_gate=False):
    run = module('run-core342-trial')
    try:
        plan, approval, budget = authorization(run)
    except (Exception,KeyboardInterrupt) as problem:
        print('0344 refused before device IO: '+repr(problem),flush=True)
        return 2
    if check_gate:
        print('0344 exact consent and reviewed pins accepted; zero device IO',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0344',
                       after_restore=after_restore,success_state=SUCCESS)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate', action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
