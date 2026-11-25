#!/usr/bin/env python3
"""Run a reviewed 60 Hz CA timing candidate under the user's standing grant."""

import hashlib
from importlib import import_module
from itertools import zip_longest
from types import SimpleNamespace

from frame364_analysis import measure, score, trace
from frame365_analysis import attribute, parse
from frame365_scope import BASE, FLAGS, REF364, REPORT_BYTES, RESERVE, SUCCESS, TRIAL
from frame365_scope import expected_plan, load, require

EXEC = BASE/'execution'
scorer = import_module('run-frame360-trial')
STANDING_INSTRUCTION = '以后不用我手动授权，你直接跑就可以了 直到能达成60hz'


def check_standing_consent(approval,ready,plan,*,trial,flags):
    require(trial==TRIAL and all(approval.get(flag) is True for flag in flags) and
            approval.get('fixture_only') is not True and
            approval.get('source')=='actual-user-60Hz-standing-grant' and
            approval.get('provenance')=='direct-standing-user-instruction' and
            approval.get('user_answer')==STANDING_INSTRUCTION and
            approval.get('user_answer_sha256')==hashlib.sha256(STANDING_INSTRUCTION.encode()).hexdigest() and
            approval.get('plan_sha256')==ready['install_plan_sha256'] and
            approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
            approval.get('image_sha256')==plan['image_sha256'] and
            not load(REF364/'result.json')['sustained_motion_steady_60_qualified'],
            'standing user grant does not match this reviewed 60 Hz scope')


def after_restore(execution,plan,result,before,code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede 0365 CA and frame analysis')
    original_passed = '0365-original-strokes-measured-root-restored'
    history = load(REF364/'frame-pacing-0363-0364.json')['0364']
    scorer.after_restore(execution,plan,result,before,code,trial=TRIAL,refs={'0364':REF364},
        history={'0364':history},success=original_passed)
    if result['state']!=original_passed:
        return
    try:
        current = measure(execution)
        reference = load(REF364/'motion-identity-0363-0364.json')['current_0364']
        raw = (execution/'kernel.log').read_text()
        rows,_,num,den = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
        ca = parse((execution/'springboard-new.log').read_text())
        audit = import_module('audit-frame364-deadlines')
        io = load(execution/'kernel-IO-identity-analysis.json')['submits']
        core = load(execution/'core-wait-execution-analysis.json')['rows']
        producer = audit.producer_budget(current,rows,core,io,lambda tick:tick*num//den)
        attribution = attribute(ca,current['frontend'],{'producer':producer})
        old,new = [run['slow_drag']['identity']['frames'] for run in (reference,current)]
        report = dict(reference_0364=reference,current_0365=current,CA_attribution=attribution,
            producer_placement=producer,slow_drag_by_scan_ordinal=[
                dict(ordinal=ordinal,reference_0364=a,current_0365=b)
                for ordinal,(a,b) in enumerate(zip_longest(old,new),1)])
        scorer.prior.timeline.write(execution/'CA-timing-0364-0365.json',report,REPORT_BYTES)
    except ValueError as error:
        result.update(state='0365-CA-or-late-motion-unqualified-root-restored',comparison_error=str(error))
        return
    slow = current['slow_drag']
    result.update(state=SUCCESS,expected_motion_benchmark=True,sustained_motion_steady_60_qualified=slow['steady_60_qualified'],
        sustained_motion={key:value for key,value in slow.items() if key!='identity'},
        same_13_strokes=current['same_13_strokes'],driver_copy_motion_cadence=current['driver_copy_motion_cadence'],
        slow_drag_joined_submissions=slow['identity']['complete_IO_submits'],
        CA_summary={key:value for key,value in attribution.items() if key!='details'},
        producer_placement={key:value for key,value in producer.items() if key!='exact_next_writers'})


def main():
    tools = import_module('run-core342-trial')
    gate = SimpleNamespace(check_consent=check_standing_consent)
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            gate,base=BASE,trial=TRIAL,expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0365 refused before device IO: '+repr(error),flush=True)
        return 2
    return tools.execute(plan,approval,budget,BASE,EXEC,trial=TRIAL,after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
