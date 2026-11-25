#!/usr/bin/env python3
"""Run the exact approved 0352 candidate once and compare restored captures."""

import argparse
from importlib import import_module

import frame349_log as scanout
import frame350_queue as queue
import frame351_display as present
import frame352_display as display
from frame352_scope import BASE, FLAGS, FOCUS, RELEASE_NS, RESERVE, SUCCESS
from frame352_scope import check_references, expected_plan, load, require

EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
previous = import_module('run-frame350-trial')
timeline = import_module('run-frame345-trial')
PRESENT_REPORT_BYTES = 5_000_000
QUEUE_REPORT_BYTES = 1_000_000


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede 0352 analysis')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement'] = 'withheld-by-core-collection-gate'
        return
    check_references()
    inputs = previous.trace_inputs(execution)
    core,submits,_ = inputs
    raw = (execution/'kernel.log').read_text()
    try:
        frame = scanout.analyze(raw,submits['submits'],core['rows'],preserve_data_preimage=True,
                                extra_kinds=(present.PRESENT,display.WAKE))
        phase = display.analyze(raw,frame)
    except ValueError as error:
        result.update(state='0352-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    references = load(BASE/'frame-host/reference-displays.json')
    timeline.write(execution/'present-alignment-0350-0351-0352.json',
        dict(performance_baseline='0350',references=references,current=phase),PRESENT_REPORT_BYTES)
    waits = queue.analyze(*inputs,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
    old_waits = load(BASE/'frame-host/reference-release-queues.json')
    timeline.write(execution/'queue-release-0350-0351-0352.json',
        dict(strokes=FOCUS,release_bounds_ns=RELEASE_NS,trials={**old_waits,'0352':waits}),QUEUE_REPORT_BYTES)
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    complete = all(row['output_updates_per_second'] and not row['verified_full_frame_counts']['unknown']
                   for row in phase['phases'].values())
    result.update(hardware_scanout=hardware,misr=frame['misr'],crc_frame_calibration=frame['crc_frame_calibration'],
        display_phases=phase['phases'],display_mode_receipts=phase['mode_receipts'],frame_trace_complete=True,
        core_linked_layers=frame['core_linked_layers'],verified_copy_dispositions=phase['measured_attempt_proofs'],
        independently_bounded_copies=phase['independently_bounded_copies'],paired_copies=phase['paired_copies'],
        GPU_ready_retry_joins=len(phase['wake_joins']),GPU_ready_event_configured=phase['ready_event_configured'],
        dpu_new_content_FPS_qualified=bool(complete),physical_FPS_qualified=False)
    observed = (phase['ready_event_configured'] and phase['wake_joins'] and phase['paired_copies'] and
                phase['independently_bounded_copies'] and
                all(w['output_updates_per_second'] for w in phase['phases'].values()))
    result['state'] = SUCCESS if observed else '0352-collection-qualified-display-measurement-incomplete-root-restored'


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = shared.authorization(run,base=BASE,trial='0352',
                                                    expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0352 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0352 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0352',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
