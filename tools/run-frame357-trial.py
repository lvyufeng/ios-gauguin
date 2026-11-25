#!/usr/bin/env python3
"""Run the explicitly authorized 0357 trial once and score restored evidence."""

import argparse
from importlib import import_module

import frame344_log as trace
import frame349_log as scanout
import frame351_display as present
import frame352_display as copy
import frame354_display as ready
from frame355_display import inventory, verify_startup
from frame356_display import matched_latencies
from frame357_display import BOUND, CALIBRATION, KINDS, calibration, compare, retained_before_completion
from frame356_scope import REF350, REF355
from frame357_scope import BASE, FLAGS, REF356, RESERVE, SUCCESS, expected_plan, load, require

EXEC = BASE/'execution'
PRESENT_REPORT_BYTES = 5_000_000
READY_REPORT_BYTES = 2_000_000
MISSED_REPORT_BYTES = 1_000_000
STARTUP_REPORT_BYTES = 65_536
timeline = import_module('run-frame345-trial')


def strict_rate(frame, display):
    bounds = {}
    for name,data in display['phases'].items():
        w = [w for w in frame['hardware']['windows'] if w['window']==name]
        low, high = (sum(x['elapsed_ns_'+limit] for x in w) for limit in ('low','high'))
        counts = data.get('verified_full_frame_counts',data['full_frame_counts'])
        bounds[name] = ([counts['changed']*1e9/high, (counts['changed']+counts['unknown'])*1e9/low]
                        if low>0 and frame['crc_frame_calibration']['qualified'] and
                        (counts['changed'] or counts['repeated']) else None)
    return bounds


def collect_after_restore(execution, plan, result, before, code, *, trial, extra_kinds=(), join_tail_copy=False,
                          core_analyzer=None, display_options=None):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede 0357 analysis')
    raw = (execution/'kernel.log').read_text(errors='replace')
    try:
        require(code==0 and plan['kernel_banner'] in raw,'observer did not record the exact '+trial+' kernel')
        startup = verify_startup(raw)
    except ValueError as error:
        result.update(state=trial+'-startup-rejected-root-restored',startup_error=str(error))
        return
    timeline.write(execution/'empty-layer-startup-analysis.json',startup,STARTUP_REPORT_BYTES)
    result['empty_layer_startup'] = startup
    analyze_core = core_analyzer or import_module('analyze-core342').analyze_saved
    analyze_core(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement'] = 'withheld-by-core-collection-gate'
        return
    core,submits,kernel = import_module('run-frame350-trial').trace_inputs(execution)
    kinds = (*KINDS,*extra_kinds)
    try:
        frame = scanout.analyze(raw,submits['submits'],core['rows'],preserve_data_preimage=True,
                                extra_kinds=(present.PRESENT,copy.WAKE,*kinds),latch_calibration=calibration,
                                join_tail_copy=trial=='0358' or join_tail_copy)
        phase = copy.analyze(raw,frame,extra_kinds=kinds,**(display_options or {}))
        selection = ready.analyze(raw,phase,binding_kind=BOUND,extra_kinds=(CALIBRATION,*extra_kinds))
        rows,_,_,_ = trace.parse(raw,extra_kinds=(present.PRESENT,copy.WAKE,*kinds))
        retained = retained_before_completion(rows,selection)
        missed = inventory(raw,selection,extra_kinds=(BOUND,CALIBRATION,*extra_kinds))
    except ValueError as error:
        result.update(state=trial+'-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    timeline.write(execution/'frame-scanout-analysis.json',frame,8_000_000)
    timeline.write(execution/'issued-retention-analysis.json',retained,READY_REPORT_BYTES)
    timeline.write(execution/'unpresented-swap-stages.json',missed,MISSED_REPORT_BYTES)
    return frame,phase,selection,rows,retained,missed,(core,submits,kernel)


def after_restore(execution, plan, result, before, code):
    collected = collect_after_restore(execution,plan,result,before,code,trial='0357')
    if collected is None:
        return
    frame,phase,selection,_,retained,missed,inputs = collected
    references = load(BASE/'frame-host/reference-displays.json')
    comparison = compare({**references,'0357':phase})
    rate = strict_rate(frame,phase)
    comparison['strict_new_frame_rate_bounds'] = {
        name:strict_rate(load(path/'frame-scanout-analysis.json'), references[name])
        for name,path in zip(('0350','0355','0356'),(REF350,REF355,REF356),strict=True)}
    comparison['strict_new_frame_rate_bounds']['0357'] = rate
    timeline.write(execution/'present-alignment-0350-0355-0356-0357.json',comparison,PRESENT_REPORT_BYTES)
    active = phase['phases']['active']['verified_full_frame_counts']
    hardware = {k:v for k,v in frame['hardware'].items() if k!='windows'}
    refresh = hardware['hardware_refresh_hz_bounds']
    measured = bool(frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'] and
                    refresh and hardware['release_cadence']['hardware_refresh_hz_bounds'] and
                    rate['active'] and rate['release'] and phase['ready_event_configured'])
    result.update(state=SUCCESS if measured else '0357-collection-qualified-output-incomplete-root-restored',
        frame_trace_complete=True,hardware_scanout=hardware,misr=frame['misr'],
        crc_frame_calibration=frame['crc_frame_calibration'],display_phases=phase['phases'],
        strict_new_frame_rate_bounds=rate,
        dpu_new_content_FPS_qualified=measured and not any(
            p['verified_full_frame_counts']['unknown'] for p in phase['phases'].values()),
        stable_60_fps_observed=measured and 59<=refresh[0]<=refresh[1]<=61 and
            not active['unknown'] and not active['repeated'],
        issued_retention={k:v for k,v in retained.items() if k!='verified_candidates'},
        ready_selection=selection['phases'],unpresented_swap_stages=missed['phases'],
        matched_latency=matched_latencies(*inputs)['summary'],
        independently_bounded_copies=phase['independently_bounded_copies'],physical_FPS_qualified=False)


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0357',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0357 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0357 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0357',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
