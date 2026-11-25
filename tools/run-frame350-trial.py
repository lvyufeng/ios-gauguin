#!/usr/bin/env python3
"""Execute the separately authorized 0350 CRC and queue observation once."""

import argparse
from importlib import import_module

import frame349_log as scanout
import frame350_queue as queue
from frame350_scope import BASE, FLAGS, REFERENCE, REFERENCE_PROOF, REFERENCE_RESULT, RESERVE, SUCCESS
from frame350_scope import expected_plan, load, require, sha


EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
comparison = import_module('run-frame348-trial')
timeline = import_module('run-frame345-trial')
QUEUE_REPORT_BYTES = 1_000_000


def trace_inputs(execution):
    names = ('core-wait-execution-analysis','kernel-IO-identity-analysis','kernel-IO-analysis')
    return [load(execution/f'{name}.json') for name in names]


def focused_summary(execution, frame, inputs):
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and
            sha(REFERENCE/'independent-restore.json')==REFERENCE_PROOF, 'restored 0349 evidence differs')
    baseline = load(BASE/'frame-host/0349-queue-tail.json')
    current = queue.analyze(*inputs,frame)
    timeline.write(execution/'queue-tail-0349-0350.json',
                   dict(state='0350-vs-0349-strokes-3-and-11',trials={'0349':baseline,'0350':current}),
                   QUEUE_REPORT_BYTES)
    return {key:[{k:v for k,v in stroke.items() if k!='tail'} for stroke in item['focus']]
            for key,item in (('0349',baseline),('0350',current))}


def compare(execution, verdict, frame, rows, joins):
    previous = load(REFERENCE/'result.json')
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and previous['restored'] and
            previous['independent_restore_verified'] and previous['static_root_comparison_passed'],
            '0349 reference provenance differs')
    old_core,old_joins,_ = trace_inputs(REFERENCE)
    baseline = comparison.compared_trial(REFERENCE,previous,load(REFERENCE/'frame-scanout-analysis.json'),
                                         old_core['rows'],old_joins['submits'])
    current = comparison.compared_trial(execution,verdict,frame,rows,joins)
    timeline.write(execution/'comparison-0349.json',dict(state='0350-vs-0349-matched-script',
        trials={'0349':baseline,'0350':current},alignment='Same stroke and phase, boot-local Core, IO and display identities.'),
        2_000_000)
    return {name:d['warm_lanes']['first_250ms_after_release'] for name,d in (('0349',baseline),('0350',current))}


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede capture acceptance')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    core,submits,kernel = inputs = trace_inputs(execution)
    text = (execution/'kernel.log').read_text()
    try:
        frame = scanout.analyze(text,submits['submits'],core['rows'],preserve_data_preimage=True)
    except ValueError as error:
        result.update(state='0350-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    active = hardware['hardware_refresh_hz_bounds']
    release = hardware['release_cadence']['hardware_refresh_hz_bounds']
    bounds = hardware['scanout_content_fps_bounds'] or hardware['scanout_partial_coverage_fps_bounds']
    result.update(dpu_probe=frame['dpu_probe'],hardware_scanout=hardware,misr=frame['misr'],
                  crc_frame_calibration=frame['crc_frame_calibration'],frame_trace_complete=True,
                  core_linked_layers=frame['core_linked_layers'],physical_FPS_qualified=False,
                  dpu_new_content_FPS_qualified=bool(hardware['complete_crc_coverage']),
                  after_release_0349_0350=compare(execution,result,frame,core['rows'],submits['submits']),
                  focus_queue_wait=focused_summary(execution,frame,inputs))
    result['state'] = (SUCCESS if active and release and bounds is not None else
                       '0350-collection-qualified-vblank-or-CRC-incomplete-root-restored')


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = shared.authorization(run,base=BASE,trial='0350',expected=expected_plan,
                                                    flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0350 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0350 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0350',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
