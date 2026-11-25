#!/usr/bin/env python3
"""Execute one reviewed 60 Hz issued-writer probe trial and restore before scoring."""

import hashlib
from importlib import import_module
from itertools import zip_longest
from types import SimpleNamespace

from frame364_analysis import measure, score, trace
from frame365_analysis import attribute, parse
from frame366_retry import analyze as analyze_retries
from frame366_scope import BASE, FLAGS, REF365, REPORT_BYTES, RESERVE, SUCCESS, TRIAL
from frame366_scope import expected_plan, load, require

EXEC = BASE/'execution'
scorer = import_module('run-frame360-trial')
STANDING_INSTRUCTION = import_module('run-frame365-trial').STANDING_INSTRUCTION


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
        not load(REF365/'result.json')['sustained_motion_steady_60_qualified'],
        'standing user grant differs from the reviewed 0366 scope')


def measured_retries(execution, current, rows, raw):
    slow = current['slow_drag']['identity']['frames']
    part = lambda frame:(frame-1)&0xffffffff
    frame = load(execution/'frame-scanout-analysis.json')
    ordinary = score.copy.analyze(raw,frame,extra_kinds=score.KINDS)
    phases = {i['previous_frame']:window['phase'] for window in ordinary['windows'] for i in window['intervals']}
    phases.update({part(row['frame']):'slow_drag' for row in slow})
    copies = {(part(row['frame']),row['certified_copy']['native_fence']):row['kind']
              for row in slow if row['certified_copy']}
    for row in load(execution/'fence-probe-analysis.json')['probes']:
        if row.get('same_scan') and row.get('accepted_full_frame'):
            copies[row['hardware_frame'],row['fence']] = 'changed'
    return analyze_retries(rows,phases,copies)


def after_restore(execution,plan,result,before,code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede 0366 retry and frame analysis')
    original = '0366-original-strokes-measured-root-restored'
    history = load(REF365/'frame-pacing-0364-0365.json')['0365']
    scorer.after_restore(execution,plan,result,before,code,trial=TRIAL,refs={'0365':REF365},
        history={'0365':history},success=original)
    if result['state']!=original:
        return
    try:
        current = measure(execution)
        previous = load(REF365/'CA-timing-0364-0365.json')['current_0365']
        raw = (execution/'kernel.log').read_text()
        rows,_,num,den = trace.parse(raw,extra_kinds=(score.PRESENT,score.copy.WAKE,*score.KINDS))
        retries = measured_retries(execution,current,rows,raw)
        ca = parse((execution/'springboard-new.log').read_text())
        audit = import_module('audit-frame364-deadlines')
        core = load(execution/'core-wait-execution-analysis.json')['rows']
        io = load(execution/'kernel-IO-identity-analysis.json')['submits']
        producer = audit.producer_budget(current,rows,core,io,lambda tick:tick*num//den)
        attribution = attribute(ca,current['frontend'],{'producer':producer})
        old,new = [r['slow_drag']['identity']['frames'] for r in (previous,current)]
        report = dict(reference_0365=previous,current_0366=current,probe_retries=retries,CA_attribution=attribution,
            producer_placement=producer,slow_drag_by_scan_ordinal=[
                dict(ordinal=i,reference_0365=a,current_0366=b)
                for i,(a,b) in enumerate(zip_longest(old,new),1)])
        scorer.prior.timeline.write(execution/'issued-probe-0365-0366.json',report,REPORT_BYTES)
    except ValueError as error:
        result.update(state='0366-probe-or-late-motion-unqualified-root-restored',comparison_error=str(error))
        return
    slow = current['slow_drag']
    result.update(state=SUCCESS,expected_motion_benchmark=True,sustained_motion_steady_60_qualified=slow['steady_60_qualified'],
        sustained_motion={key:value for key,value in slow.items() if key!='identity'},
        same_13_strokes=current['same_13_strokes'],driver_copy_motion_cadence=current['driver_copy_motion_cadence'],
        slow_drag_joined_submissions=slow['identity']['complete_IO_submits'],
        probe_retry_summary={key:value for key,value in retries.items() if key!='receipts'},
        CA_summary={key:value for key,value in attribution.items() if key!='details'})


def main():
    runner = import_module('run-core342-trial')
    gate = SimpleNamespace(check_consent=check_standing_consent)
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            gate,base=BASE,trial=TRIAL,expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0366 refused before device IO: '+repr(error),flush=True)
        return 2
    return runner.execute(plan,approval,budget,BASE,EXEC,trial=TRIAL,after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    raise SystemExit(main())
