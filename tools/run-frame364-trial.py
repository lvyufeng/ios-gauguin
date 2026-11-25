#!/usr/bin/env python3
"""Run the approved matched 0364 capture and analyze it after independent readback."""

import argparse
from importlib import import_module
from itertools import zip_longest

from frame364_analysis import measure
from frame364_scope import BASE, FLAGS, REF363, REPORT_BYTES, RESERVE, SUCCESS
from frame364_scope import expected_plan, load, require

EXEC = BASE/'execution'
scorer = import_module('run-frame360-trial')


def compare(reference, current):
    before = reference['slow_drag']['identity']['frames']
    after = current['slow_drag']['identity']['frames']
    return dict(scope='Same capture image, signed userspace, original strokes and independent slow drag.',
        reference_0363=reference,current_0364=current,
        slow_drag_alignment_by_scan_ordinal=[
            dict(ordinal=i,reference_0363=old,current_0364=new)
            for i,(old,new) in enumerate(zip_longest(before,after),1)])


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede 0364 frame analysis')
    original_passed = '0364-original-strokes-measured-root-restored'
    archive = load(REF363/'frame-pacing-0361-0363.json')
    scorer.after_restore(execution,plan,result,before,code,trial='0364',refs={'0363':REF363},
        history={'0363':archive['0363']},success=original_passed)
    if result['state']!=original_passed:
        return
    try:
        current = measure(execution)
        reference = load(BASE/'frame-host/archived-0363-deadlines.json')
        report = compare(reference,current)
        scorer.prior.timeline.write(execution/'motion-identity-0363-0364.json',report,REPORT_BYTES)
    except ValueError as error:
        result.update(state='0364-late-identity-or-producer-analysis-unqualified-root-restored',
                      comparison_error=str(error))
        return
    slow = current['slow_drag']
    result.update(state=SUCCESS,expected_motion_benchmark=True,sustained_motion_steady_60_qualified=slow['steady_60_qualified'],
        sustained_motion={key:value for key,value in slow.items() if key!='identity'},
        slow_drag_joined_submissions=slow['identity']['complete_IO_submits'],
        same_13_strokes=current['same_13_strokes'],driver_copy_motion_cadence=current['driver_copy_motion_cadence'],
        callback_to_swap={key:value for key,value in current['frontend'].items() if key!='details'})


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0364',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0364 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0364 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0364',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
