#!/usr/bin/env python3
"""Boot the separately approved 0361 Core and compare restored measurements."""

import argparse
from importlib import import_module

import frame344_log as trace
from frame361_scope import BASE, FLAGS, REF360, RESERVE, SUCCESS, expected_plan, load, require

EXEC = BASE/'execution'
scorer = import_module('run-frame360-trial')


def score_recording(path):
    core = load(path/'core-wait-execution-analysis.json')
    joined = load(path/'kernel-IO-identity-analysis.json')
    require(core['coverage_qualified'] and joined['coverage_qualified'],'Core identity coverage is incomplete')
    ids = lambda row: (row['queue'],row['ticket'],row['job'])
    jobs = trace.indexed(core['rows'],ids,'Core job')
    rows = [jobs[ids(row)] for row in joined['submits']]
    phase = core['render_phase_order'].index('encode')
    require(len(rows)==joined['complete_submit_count'] and rows,'missing matched recording data')
    return dict(matched_submissions=len(rows),
        core_queue_p95_us=trace.quantile([r['core_queue_wait_us'] for r in rows],.95),
        core_recording_p95_us=trace.quantile([r['own_recording_execution_us'] for r in rows],.95),
        render_encode_p95_us=trace.quantile([r['render_ns'][phase]/1000 for r in rows],.95),
        core_commit_p95_us=trace.quantile([r['own_commit_us'] for r in rows],.95))


def after_restore(execution, plan, result, before, code):
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'],
            'independent restore must precede 0361 frame analysis')
    recorded = load(REF360/'frame-pacing-0358-0359-0360.json')
    scorer.after_restore(execution,plan,result,before,code,trial='0361',refs={'0360':REF360},
                         history={'0360':recorded['0360']},success=SUCCESS)
    if result.get('frame_trace_complete'):
        result.update(recording_comparison={label:score_recording(path) for label,path in
            (('0360',REF360),('0361',execution))},different_SDK_than_0360=True,
            SDK_matched_control_measured=False)


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0361',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0361 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0361 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0361',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
