#!/usr/bin/env python3
"""Execute the separately authorized 0349 blanking CRC trial once."""

import argparse
from importlib import import_module

import frame349_log as scanout
from frame349_scope import BASE, FLAGS, REFERENCE, REFERENCE_RESULT, RESERVE, SUCCESS
from frame349_scope import expected_plan, load, require, sha


EXEC = BASE/'execution'
shared = import_module('run-frame347-trial')
comparison = import_module('run-frame348-trial')
timeline = import_module('run-frame345-trial')


def compare(execution, verdict, frame, rows, joins):
    require(sha(REFERENCE/'result.json')==REFERENCE_RESULT, '0348 reference provenance differs')
    previous = load(REFERENCE/'result.json')
    require(previous['restored'] and previous['independent_restore_verified'] and
            previous['static_root_comparison_passed'], '0348 reference was not independently restored')
    baseline = comparison.compared_trial(REFERENCE,previous,load(REFERENCE/'frame-scanout-analysis.json'),
        load(REFERENCE/'core-wait-execution-analysis.json')['rows'],load(REFERENCE/'kernel-IO-identity-analysis.json')['submits'])
    candidate = comparison.compared_trial(execution,verdict,frame,rows,joins)
    trials = {'0348':baseline,'0349':candidate}
    timeline.write(execution/'comparison-0348.json',dict(state='0349-vs-0348-matched-script',trials=trials,
        alignment='Same stroke and phase. Use boot-local Core, IO, GPU and scanout identities.'),2_000_000)
    return {key:value['warm_lanes']['first_250ms_after_release'] for key,value in trials.items()}


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore and static proof must precede capture acceptance')
    import_module('analyze-core342').analyze_saved(execution,plan,result,before,code)
    if result['state']!=timeline.CORE_PASSED:
        result['frame_measurement']='withheld-by-core-collection-gate'
        return
    rows = load(execution/'core-wait-execution-analysis.json')['rows']
    joins = load(execution/'kernel-IO-identity-analysis.json')['submits']
    try:
        frame = scanout.analyze((execution/'kernel.log').read_text(),joins,rows)
    except ValueError as error:
        result.update(state='0349-frame-capture-rejected-root-restored',frame_capture_error=str(error))
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
                  after_release_0348_0349=compare(execution,result,frame,rows,joins))
    result['state'] = (SUCCESS if active and release and bounds is not None else
                       '0349-collection-qualified-vblank-or-CRC-incomplete-root-restored')


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = shared.authorization(run,base=BASE,trial='0349',expected=expected_plan,
                                                    flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0349 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0349 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0349',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
