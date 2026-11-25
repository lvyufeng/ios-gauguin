#!/usr/bin/env python3
"""Run the separately approved 0362 control and score after independent restore."""

import argparse
from importlib import import_module

from frame362_analysis import measure
from frame362_scope import BASE, FLAGS, REF361, RESERVE, SUCCESS, expected_plan, load, pacing, require

EXEC = BASE/'execution'
scorer = import_module('run-frame360-trial')
REPORT_BYTES = 2_000_000


def after_restore(execution, plan, result, before, code, *, trial='0362', success=SUCCESS):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede '+trial+' frame analysis')
    original_passed = trial+'-original-strokes-measured-root-restored'
    archive = load(REF361/'frame-pacing-0360-0361.json')
    scorer.after_restore(execution,plan,result,before,code,trial=trial,refs={'0361':REF361},
        history={'0361':archive['0361']},success=original_passed)
    if result['state']!=original_passed:
        return
    pacing.check_restored(REF361)
    reference = measure(REF361)
    measured = measure(execution,with_motion=True)
    report = dict(sdk='27.2',optimized_0361=reference,
        scope='Original 13 strokes compare the SDK-matched Core pair. Added late motion uses the '+trial+' control.')
    report['unmodified_'+trial] = measured
    scorer.prior.timeline.write(execution/('SDK27-0361-'+trial+'-comparison.json'),report,REPORT_BYTES)
    result.update(sdk_matched_Core_control_measured=True,matched_SDK='27.2',
        matched_original_stroke_core={key:value['original_stroke_core']
                                      for key,value in (('0361',reference),(trial,measured))},
        driver_copy_motion_cadence=measured['driver_copy_motion_cadence'],
        repeat_scans_without_new_swap={k:v for k,v in measured['active_repeats_without_new_swap'].items()
                                      if k!='details'})
    if 'sustained_motion_error' in measured:
        result.update(state=trial+'-sustained-motion-unqualified-root-restored',
                      sustained_motion_error=measured['sustained_motion_error'])
        return
    motion = measured['sustained_motion']
    result.update(state=success,expected_motion_benchmark=True,stable_60_fps_observed=motion['steady_60_qualified'],
                  sustained_motion={key:value for key,value in motion.items()
                                    if key not in ('stimulus','repeats_without_new_swap')})
    if repeats := motion.get('repeats_without_new_swap'):
        result['sustained_motion']['repeats_without_new_swap'] = {
            key:value for key,value in repeats.items() if key!='details'}


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0362',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0362 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0362 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0362',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
