#!/usr/bin/env python3
"""Run 0359 after exact approval and score the independently restored capture."""

import argparse
from importlib import import_module

from frame356_display import matched_latencies
from frame357_display import compare
from frame358_audit import PROBE
from frame358_display import probe_joins
from frame359_frontend import analyze
from frame359_scope import BASE, FLAGS, P358, REF358, RESERVE, SUCCESS, expected_plan, load, require

prior = import_module('run-frame357-trial')
analyze_core = import_module('analyze-core342').analyze_saved
EXEC = BASE/'execution'


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede 0359 first-frame analysis')
    collected = prior.collect_after_restore(execution,plan,result,before,code,trial='0359',
                                            extra_kinds=(PROBE,),join_tail_copy=True,core_analyzer=analyze_core)
    if collected is None:
        return
    frame,phase,selection,rows,retained,missed,inputs = collected
    try:
        frontend = analyze(execution,targeted=True,display=phase)
        probe = probe_joins(rows,phase,selection)
    except ValueError as error:
        result.update(state='0359-first-frame-capture-rejected-root-restored',first_frame_error=str(error))
        return
    baseline = load(BASE/'frame-host/reference-first-frame.json')
    prior.timeline.write(execution/'first-frame-0358-0359.json',
        dict(alignment='Same stroke ordinal on each boot',trials={'0358':baseline,'0359':frontend}),1_000_000)
    reference = load(P358/'frame-host/reference-displays.json')['0357']
    previous = load(BASE/'frame-host/reference-display.json')
    alignment = compare({'0357':reference,'0358':previous,'0359':phase})
    rate = prior.strict_rate(frame,phase)
    alignment['strict_new_frame_rate_bounds'] = {
        '0358':load(REF358/'result.json')['strict_new_frame_rate_bounds'],'0359':rate}
    prior.timeline.write(execution/'present-alignment-0357-0358-0359.json',alignment,prior.PRESENT_REPORT_BYTES)
    prior.timeline.write(execution/'fence-probe-analysis.json',probe,1_000_000)
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    refresh = hardware['hardware_refresh_hz_bounds']
    counts = {name:row['verified_full_frame_counts'] for name,row in phase['phases'].items()}
    measured = (frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'] and refresh and
                hardware['release_cadence']['hardware_refresh_hz_bounds'] and rate['active'] and rate['release'] and
                phase['ready_event_configured'] and not any(row['unknown'] for row in counts.values()))
    result.update(state=SUCCESS if measured else '0359-nonqualified-output-root-restored',
        frame_trace_complete=True,hardware_scanout=hardware,misr=frame['misr'],crc_frame_calibration=frame['crc_frame_calibration'],
        display_phases=phase['phases'],strict_new_frame_rate_bounds=rate,dpu_new_content_FPS_qualified=bool(measured),
        stable_60_fps_observed=bool(measured and 59<=refresh[0]<=refresh[1]<=61 and not counts['active']['repeated']),
        first_frame={key:value for key,value in frontend.items() if key!='strokes'},
        second_swipe=frontend['strokes'][1],fence_probe=probe['checks'],
        issued_retention={key:value for key,value in retained.items() if key!='verified_candidates'},
        unpresented_swap_stages=missed['phases'],matched_latency=matched_latencies(*inputs)['summary'],
        independently_bounded_copies=phase['independently_bounded_copies'],physical_FPS_qualified=False)


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0359',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0359 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0359 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0359',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
