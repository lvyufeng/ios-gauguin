#!/usr/bin/env python3
"""Run a separately authorized 0348 read-only scanout trial once."""

import argparse
from importlib import import_module

import frame345_log as scanout
from frame348_scope import BASE, FLAGS, REFERENCES, RESERVE, SUCCESS
from frame348_scope import expected_plan, load, require, sha


EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
timeline = import_module('run-frame345-trial')


def compared_trial(path, verdict, frame, rows, joins):
    summary = shared.trial_summary(path,verdict,frame,rows,joins)
    attempts = {item['attempt']:item for item in frame['attempts']}
    hardware = {(item['stroke'],item['window']):item for item in frame['hardware'].get('windows',())}
    for window in summary['frames']:
        for item in window['frame_attempts']:
            item['layers'] = attempts[item['attempt']]['layers']
        observed = hardware.get((window['stroke'],window['window']),{})
        if 'vblank_edges' in observed:
            begin = observed['start_tick']
            numer,denom = frame['tick_numer'],frame['tick_denom']
            window['vblank_edges'] = [{
                'frame':edge['frame'],'step':edge['step'],'line':edge['line'],
                'relative_lower_ns':(edge['edge_lower_tick']-begin)*numer//denom,
                'relative_upper_ns':(edge['edge_upper_tick']-begin)*numer//denom,
            } for edge in observed['vblank_edges']]
    return summary


def compare(execution, verdict, frame, rows, joins):
    trials = {}
    for trial,(path,digest) in REFERENCES.items():
        require(sha(path/'result.json')==digest, trial+' reference provenance differs')
        previous = load(path/'result.json')
        require(previous['restored'] and previous['independent_restore_verified'] and
                previous['static_root_comparison_passed'], trial+' reference lacks independent restoration')
        trials[trial] = compared_trial(path,previous,load(path/'frame-scanout-analysis.json'),
            load(path/'core-wait-execution-analysis.json')['rows'],load(path/'kernel-IO-identity-analysis.json')['submits'])
    trials['0348'] = compared_trial(execution,verdict,frame,rows,joins)
    report = dict(state='0348-vs-0346-and-0347-matched-script',trials=trials,
                  alignment='Stroke ordinal and phase-relative time. Core, IO, GPU and surface IDs are boot-local.',
                  timing_scope='Own completed Core job times already include commit and exclude queue residence.')
    timeline.write(execution/'comparison-0346-0347.json',report,2_000_000)
    return {key:item['warm_lanes']['first_250ms_after_release'] for key,item in trials.items()}


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede collection and interpretation')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    rows = load(execution/'core-wait-execution-analysis.json')['rows']
    joins = load(execution/'kernel-IO-identity-analysis.json')['submits']
    try:
        frame = scanout.analyze((execution/'kernel.log').read_text(),joins,rows)
        require('motion' in frame['dpu_probe'].get('read_only_counter',{}), 'missing read-only counter motion receipt')
        require(frame['hardware']['scanout_content_fps_bounds'] is None, 'unexpected CRC qualification in mode 4')
    except ValueError as error:
        result.update(state='0348-read-only-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    active = hardware['hardware_refresh_hz_bounds']
    release = hardware.get('release_cadence',{}).get('hardware_refresh_hz_bounds')
    result.update(dpu_probe=frame['dpu_probe'],hardware_scanout=hardware,frame_trace_complete=True,
                  core_linked_layers=frame['core_linked_layers'],physical_FPS_qualified=False,
                  after_release_0346_0347_0348=compare(execution,result,frame,rows,joins))
    result['state'] = (SUCCESS if active and release else
                       '0348-collection-qualified-vblank-coverage-incomplete-root-restored')


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan, approval, budget = shared.authorization(run,base=BASE,trial='0348',expected=expected_plan,
                                                      flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0348 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0348 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0348',
                       after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
