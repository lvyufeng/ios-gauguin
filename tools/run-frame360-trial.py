#!/usr/bin/env python3
"""Execute the approved 0360 transaction and score only the restored capture."""

import argparse
from importlib import import_module

import frame352_display as copy
from frame356_display import matched_latencies
from frame357_display import compare
from frame358_display import KINDS, LOCK_RETRY, PROBE, probe_joins
from frame360_scope import BASE, FLAGS, REF358, REF359, RESERVE, SUCCESS, expected_plan, load, pacing, require

EXEC = BASE/'execution'
PACING_BYTES = 1_500_000
prior = import_module('run-frame357-trial')
PROBE_BYTES = import_module('run-frame358-trial').PROBE_REPORT_BYTES


def analyze_pacing(raw, frame, display, selection, kernel):
    measured = pacing.measure(raw,frame,kernel,display=display,selection=selection)
    archived = load(BASE/'frame-host/result.json')['trials']
    require([row['trial'] for row in archived]==['0358','0359'], '0360 pacing references differ')
    return {'0358':archived[0],'0359':archived[1],'0360':measured}


def after_restore(execution, plan, result, before, code, *, trial='0360', refs=None, history=None, success=SUCCESS):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede '+trial+' frame analysis')
    proof = load(execution/'independent-restore.json')
    require(proof['state']=='independently-verified-six-original-files-misc-and-empty-journal' and
            len(proof['files'])==6 and proof['all_original_slot_bits_allocated'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and not (proof['device_writes'] or proof['device_boots']),
            trial+' read-back proof is incomplete')
    probe_kinds = (PROBE,LOCK_RETRY) if plan.get('fence_probe',{}).get('lock_retry_wire_kind')==LOCK_RETRY else (PROBE,)
    collected = prior.collect_after_restore(execution,plan,result,before,code,trial=trial,
                                            extra_kinds=probe_kinds,join_tail_copy=True)
    if collected is None:
        return
    frame,display,selection,rows,retained,missed,inputs = collected
    hardware = {key:value for key,value in frame['hardware'].items() if key!='windows'}
    rate = prior.strict_rate(frame,display)
    counts = {name:row['verified_full_frame_counts'] for name,row in display['phases'].items()}
    refs = refs or {'0358':REF358,'0359':REF359}
    comparison_name = '-'.join((*refs,trial))
    try:
        probe = probe_joins(rows,display,selection)
        raw = (execution/'kernel.log').read_text()
        if history is None:
            details = analyze_pacing(raw,frame,display,selection,inputs[2])
        else:
            require(tuple(history)==tuple(refs),'historical pacing inputs differ')
            details = {**history,trial:pacing.measure(raw,frame,inputs[2],display=display,selection=selection)}
        past = {tag:copy.analyze((path/'kernel.log').read_text(),load(path/'frame-scanout-analysis.json'),extra_kinds=KINDS)
                for tag,path in refs.items()}
        alignment = compare({**past,trial:display},reference=next(iter(refs)))
        alignment['strict_new_frame_rate_bounds'] = {
            **{tag:load(path/'result.json')['strict_new_frame_rate_bounds'] for tag,path in refs.items()},
            trial:rate}
    except ValueError as error:
        result.update(state=trial+'-frame-capture-rejected-root-restored',frame_capture_error=str(error))
        return
    prior.timeline.write(execution/('frame-pacing-'+comparison_name+'.json'),details,PACING_BYTES)
    prior.timeline.write(execution/('present-alignment-'+comparison_name+'.json'),alignment,prior.PRESENT_REPORT_BYTES)
    prior.timeline.write(execution/'fence-probe-analysis.json',probe,PROBE_BYTES)
    current = details[trial]
    active = current['active_surface_reservations']
    measured = bool(frame['misr']['qualified'] and frame['crc_frame_calibration']['qualified'] and
        hardware['hardware_refresh_hz_bounds'] and hardware['release_cadence']['hardware_refresh_hz_bounds'] and
        rate['active'] and rate['release'] and display['ready_event_configured'] and
        not any(row['unknown'] for row in counts.values()))
    result.update(state=success if measured and active else trial+'-output-or-reservation-incomplete-root-restored',
        frame_trace_complete=True,hardware_scanout=hardware,misr=frame['misr'],crc_frame_calibration=frame['crc_frame_calibration'],
        display_phases=display['phases'],strict_new_frame_rate_bounds=rate,dpu_new_content_FPS_qualified=measured,
        stable_60_fps_observed=False,expected_motion_benchmark=False,
        active_surface_reservations=active,active_read_guards_crossing_deadline=current['active_read_guards_crossing_deadline'],
        active_separate_recorded_writer_overlap=current['active_separate_recorded_writer_overlap'],
        pacing= {key:current[key] for key in ('active','active_strokes_3_through_13','release')},
        fence_probe=probe['checks'],issued_retention={k:v for k,v in retained.items() if k!='verified_candidates'},
        unpresented_swap_stages=missed['phases'],matched_latency=matched_latencies(*inputs)['summary'],
        independently_bounded_copies=display['independently_bounded_copies'],
        copy_boundary_outcomes=display['measured_attempt_proofs'],physical_FPS_qualified=False)


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0360',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0360 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0360 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0360',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
