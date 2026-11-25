#!/usr/bin/env python3
"""Run the exact 0356 trial and validate display output after restore."""

import argparse
from importlib import import_module

import frame349_log as scanout
import frame350_queue as queue
import frame351_display as present
import frame352_display as copy
import frame354_display as ready
from frame355_display import inventory, verify_startup
from frame356_display import focus_copy, matched_latencies
from frame356_scope import BASE, FLAGS, FOCUS, RELEASE_NS, RESERVE, SUCCESS
from frame356_scope import check_references, expected_plan, load, require

EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
previous = import_module('run-frame350-trial')
timeline = import_module('run-frame345-trial')
PRESENT_REPORT_BYTES = 5_000_000
READY_REPORT_BYTES = 2_000_000
QUEUE_REPORT_BYTES = 1_000_000
STARTUP_REPORT_BYTES = 65_536
MISSED_REPORT_BYTES = 1_000_000
LATENCY_REPORT_BYTES = 1_000_000
STROKE_COPY_REPORT_BYTES = 500_000


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede 0356 analysis')
    raw = (execution/'kernel.log').read_text(errors='replace')
    try:
        require(code==0 and plan['kernel_banner'] in raw,'observer did not record the exact 0356 kernel')
        startup = verify_startup(raw)
    except ValueError as error:
        result.update(state='0356-startup-acceptance-failed-root-restored',startup_error=str(error))
        return
    timeline.write(execution/'empty-layer-startup-analysis.json',startup,STARTUP_REPORT_BYTES)
    result['empty_layer_startup'] = startup
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement'] = 'withheld-by-core-collection-gate'
        return
    check_references()
    inputs = previous.trace_inputs(execution)
    core,submits,_ = inputs
    try:
        frame = scanout.analyze(raw,submits['submits'],core['rows'],preserve_data_preimage=True,
                                extra_kinds=(present.PRESENT,copy.WAKE,*ready.KINDS))
        phase = copy.analyze(raw,frame,extra_kinds=ready.KINDS)
    except ValueError as error:
        result.update(state='0356-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    references = load(BASE/'frame-host/reference-displays.json')
    timeline.write(execution/'present-alignment-0350-0355-0356.json',
        dict(performance_baseline='0350',references=references,current=phase,
             aligned_by='stroke index, active/release and ordinal hardware frame within each boot-local window'),PRESENT_REPORT_BYTES)
    waits = queue.analyze(*inputs,frame,strokes=FOCUS,release_bounds_ns=RELEASE_NS)
    old_waits = load(BASE/'frame-host/reference-release-queues.json')
    timeline.write(execution/'queue-release-0350-0355-0356.json',
        dict(strokes=FOCUS,release_bounds_ns=RELEASE_NS,trials={**old_waits,'0356':waits}),QUEUE_REPORT_BYTES)
    latency = matched_latencies(*inputs)
    old_latency = load(BASE/'frame-host/reference-latency.json')
    timeline.write(execution/'latency-0350-0355-0356.json',
        dict(trials={**old_latency,'0356':latency},scope='Exact matched Core job and native command submission'),
        LATENCY_REPORT_BYTES)
    focus = focus_copy(phase)
    old_focus = load(BASE/'frame-host/reference-stroke-10-copy.json')
    timeline.write(execution/'stroke-10-copy-0355-0356.json',{**old_focus,'0356':focus},
                   STROKE_COPY_REPORT_BYTES)
    result['matched_latency'] = latency['summary']
    result['stroke_10_copy'] = {p:{k:v for k,v in row.items() if k!='hardware_intervals'}
                                for p,row in focus['phases'].items()}
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
        missed = inventory(raw,selection)
    except ValueError as error:
        result.update(state='0356-output-measured-ready-provenance-rejected-root-restored',ready_capture_error=str(error))
        return
    timeline.write(execution/'ready-selection-analysis.json',selection,READY_REPORT_BYTES)
    timeline.write(execution/'unpresented-swap-stages.json',missed,MISSED_REPORT_BYTES)
    result['ready_selection'] = selection['phases']
    result['unpresented_swap_stages'] = missed['phases']
    observed = (phase['ready_event_configured'] and
                selection['phases']['all']['older_ready_with_newer_swap_verified_copies'] and
                phase['paired_copies'] and all(w['output_updates_per_second'] for w in phase['phases'].values()))
    result['state'] = SUCCESS if observed else '0356-collection-qualified-retention-or-display-incomplete-root-restored'


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = shared.authorization(run,base=BASE,trial='0356',
                                                    expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0356 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0356 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0356',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
