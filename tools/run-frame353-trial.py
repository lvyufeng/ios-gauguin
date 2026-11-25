#!/usr/bin/env python3
"""Run the exact 0353 trial and validate display output after restore."""

import argparse
from importlib import import_module

import frame349_log as scanout
import frame350_queue as queue
import frame351_display as present
import frame352_display as copy
import frame353_display as ready
from frame353_scope import BASE, FLAGS, FOCUS, RELEASE_NS, RESERVE, SUCCESS
from frame353_scope import check_references, expected_plan, load, require

EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
previous = import_module('run-frame350-trial')
timeline = import_module('run-frame345-trial')
PRESENT_REPORT_BYTES = 5_000_000
READY_REPORT_BYTES = 2_000_000
QUEUE_REPORT_BYTES = 1_000_000


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede 0353 analysis')
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
                                extra_kinds=(present.PRESENT,copy.WAKE,*ready.KINDS))
        phase = copy.analyze(raw,frame,extra_kinds=ready.KINDS)
    except ValueError as error:
        result.update(state='0353-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    references = load(BASE/'frame-host/reference-displays.json')
    timeline.write(execution/'present-alignment-0350-0352-0353.json',
        dict(performance_baseline='0350',references=references,current=phase),PRESENT_REPORT_BYTES)
    waits = queue.analyze(*inputs,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
    old_waits = load(BASE/'frame-host/reference-release-queues.json')
    timeline.write(execution/'queue-release-0350-0352-0353.json',
        dict(strokes=FOCUS,release_bounds_ns=RELEASE_NS,trials={**old_waits,'0353':waits}),QUEUE_REPORT_BYTES)
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    complete = all(row['output_updates_per_second'] and not row['verified_full_frame_counts']['unknown']
                   for row in phase['phases'].values())
    result.update(hardware_scanout=hardware,misr=frame['misr'],crc_frame_calibration=frame['crc_frame_calibration'],
        display_phases=phase['phases'],display_mode_receipts=phase['mode_receipts'],frame_trace_complete=True,
        core_linked_layers=frame['core_linked_layers'],verified_copy_dispositions=phase['measured_attempt_proofs'],
        independently_bounded_copies=phase['independently_bounded_copies'],paired_copies=phase['paired_copies'],
        GPU_ready_event_configured=phase['ready_event_configured'],
        dpu_new_content_FPS_qualified=bool(complete),physical_FPS_qualified=False)
    try:
        selection = ready.analyze(raw,phase)
    except ValueError as error:
        result.update(state='0353-output-measured-ready-provenance-rejected-root-restored',ready_capture_error=str(error))
        return
    timeline.write(execution/'ready-selection-analysis.json',selection,READY_REPORT_BYTES)
    result['ready_selection'] = selection['phases']
    observed = (phase['ready_event_configured'] and selection['phases']['all']['cross_frame_verified_copies'] and
                phase['paired_copies'] and all(w['output_updates_per_second'] for w in phase['phases'].values()))
    result['state'] = SUCCESS if observed else '0353-collection-qualified-cross-frame-or-display-incomplete-root-restored'


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = shared.authorization(run,base=BASE,trial='0353',
                                                    expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0353 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0353 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0353',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
