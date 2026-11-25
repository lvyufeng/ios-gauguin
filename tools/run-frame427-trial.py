#!/usr/bin/env python3
"""Compare the 12.2 ms compositor budget with the restored passive control."""

import argparse
from importlib import import_module
import json
import re
from types import SimpleNamespace

import frame419_log as timeline


scope = import_module('prepare-frame427')
gpu = import_module('run-frame425-trial')


def check_consent(approval, ready, plan, *, trial, flags):
    scope.require(trial == scope.TRIAL and flags == scope.FLAGS and approval == gpu.approval_fields(ready,flags)
                  and approval['plan_sha256'] == plan['install_plan_sha256'],'work margin trial authorization differs')


def received_budget(raw):
    scope.require(raw.splitlines().count(f'SWEET F388 DISPATCH: work_us={scope.WORK_US}') == 1,
                  '12.2 ms work allowance missing')
    samples = re.findall(r'^SWEET F388 P: seq=\d+ scan=\d+ source=\d+ o=\d+ w=(\d+) r=(\d+) p=(\d+) a=(\d+)$',
                         raw,re.M)
    footer, = re.findall(r'^SWEET F388 F: rows=(\d+) aligned=(\d+) software=(\d+) fallback=(\d+) missed=(\d+) first=\d+ last=\d+$',
                         raw,re.M)
    count,aligned,software,fallback,missed = map(int,footer)
    scope.require(0 < count == len(samples) <= 24 and aligned > count
                  and all(ready-wake == scope.WORK_US*96//5 and wake <= actual < ready < edge
                          for wake,ready,edge,actual in (map(int,row) for row in samples)),
                  'sampled work allowance differs')
    return dict(work_us=scope.WORK_US,samples=count,aligned=aligned,software=software,fallback=fallback,missed=missed)


def comparison(score, timing):
    return dict(new_images=score['whole_interval'], repeats=len(score['repeated_scan_ids']),
        worst_confirmed_second=score['sliding_windows']['minimum_confirmed'],
        fixed_seconds_at_least_60=sum(x['new_frames_min']>=60 for x in score['fixed_seconds']),
        seconds=score['completely_measured_seconds'], aligned=timing['aligned_dispatches'],
        exact_native_cutoffs=timing['native_deadline_comparison']['exact_requested_target'],
        exact_writer_joins=timing['exact_writer_joins_in_score'])


def after_restore(execution, plan, result, _before, code):
    scope.require(result['independent_restore_verified'] and result['static_root_comparison_passed'],
                  'independent restoration must precede scoring')
    log,userspace = (execution/name for name in ('kernel.log','springboard-new.log'))
    raw = log.read_text()
    try:
        scope.require(code == 0 and raw.splitlines().count(plan['kernel_banner']) == 1,'kernel identity missing')
        score = gpu.marker_score(raw,userspace.read_text(),plan)
    except (KeyError,ValueError) as error:
        result.update(state='0427-marker-unverified-root-restored',measurement_error=str(error))
        return
    evidence = dict(kernel_log_sha256=scope.sha(log), springboard_log_sha256=scope.sha(userspace),
                    independent_restore_sha256=scope.sha(execution/'independent-restore.json'))
    scope.phase.save(execution/'marker-output.json',dict(score,**evidence))
    result.update(physical_FPS_qualified=score['completely_measured_seconds']==30,
                  stable_60_fps_observed=score['stable_60_fps_observed'],comparison='marker-output.json')
    try:
        timing = timeline.measure(raw,score,plan)
        budget = received_budget(raw)
        scope.require(len(json.dumps(timing,indent=2)) < 524_288,'work allowance report exceeds reserve')
    except (KeyError,ValueError) as error:
        result.update(state='0427-crc-measured-timeline-unverified-root-restored',timeline_error=str(error))
        return
    scope.phase.save(execution/'passive-completion.json',dict(timing,**evidence))
    control = scope.gpu.BASE/'execution'
    baseline = comparison(scope.load(control/'marker-output.json'),scope.load(control/'passive-completion.json'))
    name = 'marker-budget-comparison.json'
    scope.phase.save(execution/name,dict(control_7200=baseline,candidate_12200=comparison(score,timing),runtime=budget))
    result.update(state=scope.SUCCESS,comparison=name,runtime=budget)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record-actual-request',action='store_true')
    if parser.parse_args().record_actual_request:
        gpu.record_grant(scope.BASE,scope.TRIAL,scope.FLAGS)
        return 0
    plan,approval,budget = import_module('run-frame347-trial').authorization(
        SimpleNamespace(check_consent=check_consent),base=scope.BASE,trial=scope.TRIAL,
        expected=scope.expected_plan,flags=scope.FLAGS,reserve=scope.gpu.RESERVE)
    return import_module('run-core342-trial').execute(plan,approval,budget,scope.BASE,scope.BASE/'execution',
        trial=scope.TRIAL,after_restore=after_restore,success_state=scope.SUCCESS)


if __name__ == '__main__':
    raise SystemExit(main())
