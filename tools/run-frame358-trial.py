#!/usr/bin/env python3
"""Run the separately authorized 0358 fence observation and restore."""

import argparse
from importlib import import_module

from frame356_display import matched_latencies
from frame357_display import compare
from frame358_audit import PROBE, SUMMARY_357, check_0357
from frame358_display import probe_joins
from frame358_scope import BASE, FLAGS, RESERVE, SUCCESS, expected_plan, load

EXEC = BASE/'execution'
PROBE_REPORT_BYTES = 1_000_000
prior = import_module('run-frame357-trial')


def after_restore(execution, plan, result, before, code):
    collected = prior.collect_after_restore(execution,plan,result,before,code,trial='0358',extra_kinds=(PROBE,))
    if collected is None:
        return
    frame,phase,selection,rows,retained,missed,inputs = collected
    try:
        probing = probe_joins(rows,phase,selection)
    except ValueError as error:
        result.update(state='0358-probe-capture-rejected-root-restored',probe_capture_error=str(error))
        return
    check_0357()
    references = load(BASE/'frame-host/reference-displays.json')
    comparison = compare({**references,'0358':phase})
    rate = prior.strict_rate(frame,phase)
    prior_rates = load(SUMMARY_357)['scored_crc_comparison']['strict_new_frame_rate_bounds']
    comparison['strict_new_frame_rate_bounds'] = {**prior_rates,'0358':rate}
    prior.timeline.write(execution/'present-alignment-0350-0355-0356-0357-0358.json',comparison,prior.PRESENT_REPORT_BYTES)
    prior.timeline.write(execution/'fence-probe-analysis.json',probing,PROBE_REPORT_BYTES)
    active = phase['phases']['active']['verified_full_frame_counts']
    hw = {k:v for k,v in frame['hardware'].items() if k!='windows'}
    refresh = hw['hardware_refresh_hz_bounds']
    measured = bool(frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'] and
                    refresh and hw['release_cadence']['hardware_refresh_hz_bounds'] and rate['active'] and rate['release'] and
                    phase['ready_event_configured'] and probing['probes'])
    result.update(state=SUCCESS if measured else '0358-collection-qualified-probe-or-output-incomplete-root-restored',
        frame_trace_complete=True,hardware_scanout=hw,misr=frame['misr'],crc_frame_calibration=frame['crc_frame_calibration'],
        display_phases=phase['phases'],strict_new_frame_rate_bounds=rate,
        dpu_new_content_FPS_qualified=measured and not any(
            x['verified_full_frame_counts']['unknown'] for x in phase['phases'].values()),
        stable_60_fps_observed=measured and 59<=refresh[0]<=refresh[1]<=61 and not active['unknown'] and not active['repeated'],
        fence_probe={k:v for k,v in probing.items() if k!='probes'},
        issued_retention={k:v for k,v in retained.items() if k!='verified_candidates'},
        unpresented_swap_stages=missed['phases'],
        matched_latency=matched_latencies(*inputs)['summary'], independently_bounded_copies=phase['independently_bounded_copies'],
        physical_FPS_qualified=False)


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0358',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0358 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0358 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0358',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
