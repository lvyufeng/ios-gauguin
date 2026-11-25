#!/usr/bin/env python3
"""Run the separately approved 0351 display and focused queue trial once."""

import argparse
from importlib import import_module

import frame349_log as scanout
import frame350_queue as queue
import frame351_display as display
from frame351_scope import BASE, FLAGS, FOCUS, REFERENCE, REFERENCE_PROOF, REFERENCE_RESULT, RELEASE_NS, RESERVE, SUCCESS
from frame351_scope import expected_plan, load, require, sha


EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
previous = import_module('run-frame350-trial')
timeline = import_module('run-frame345-trial')
PRESENT_REPORT_BYTES = 3_000_000
QUEUE_REPORT_BYTES = 1_000_000


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede phase analysis')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    inputs = previous.trace_inputs(execution)
    core,submits,_ = inputs
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT and sha(REFERENCE/'independent-restore.json')==REFERENCE_PROOF,
            '0350 restored baseline evidence differs')
    raw = (execution/'kernel.log').read_text()
    try:
        frame = scanout.analyze(raw,submits['submits'],core['rows'],preserve_data_preimage=True,extra_kinds=(display.PRESENT,))
        phase = display.analyze(raw,frame)
    except ValueError as error:
        result.update(state='0351-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    baseline = load(BASE/'frame-host/0350-present-baseline.json')
    timeline.write(execution/'present-alignment-0350-0351.json',dict(baseline=baseline['phases'],current=phase),
                   PRESENT_REPORT_BYTES)
    waits = queue.analyze(*inputs,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
    timeline.write(execution/'queue-release-0350-0351.json',
        dict(strokes=FOCUS,release_bounds_ns=RELEASE_NS,
             trials={'0350':load(BASE/'frame-host/0350-queue-release.json'),'0351':waits}),QUEUE_REPORT_BYTES)
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    result.update(hardware_scanout=hardware,misr=frame['misr'],crc_frame_calibration=frame['crc_frame_calibration'],
                  display_phases=phase['phases'],display_mode_receipts=phase['mode_receipts'],
                  verified_copy_dispositions=phase['measured_attempt_proofs'],
                  frame_trace_complete=True,core_linked_layers=frame['core_linked_layers'],
                  dpu_new_content_FPS_qualified=bool(hardware['complete_crc_coverage']),physical_FPS_qualified=False)
    observed = bool(phase['measured_attempt_proofs'].get('verified-blank') and
                    all(w['output_updates_per_second'] for w in phase['phases'].values()))
    result['state'] = SUCCESS if observed else '0351-collection-qualified-display-measurement-incomplete-root-restored'


def main(check_gate=False):
    run=import_module('run-core342-trial')
    try:
        plan,approval,budget=shared.authorization(run,base=BASE,trial='0351',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0351 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0351 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0351',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
