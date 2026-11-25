#!/usr/bin/env python3
"""Compare guarded staging dispatch after independent restoration."""

from importlib import import_module
import re

import frame344_log as trace

scope = import_module('prepare-frame400')
prior = import_module('run-frame398-trial')
common,stock,flip,stage = prior.common,prior.stock,prior.flip,prior.stage
ON_STAGE = re.compile(r'^SWEET F382 I (\d+) (\d+) ([12]) (\d+) C$',re.M)


def dispatch_receipts(raw,latches):
    requests = [tuple(map(int,row)) for row in ON_STAGE.findall(raw)]
    trace.require(len({row[0] for row in requests})==len(requests) and len(requests)<=1024,
                  'ambiguous staging request receipt')
    accepted = []
    for attempt,scan,slot,tick in requests:
        latch = latches.get((scan+1)&0xffffffff)
        if latch is None:
            continue
        trace.require((latch['attempt'],latch['slot'],latch['issued_tick'])==(attempt,slot,tick) and
                      latch['tick']<=tick<=latch['confirmed_tick'],'staging request lost its confirmed slot')
        accepted.append(dict(attempt=attempt,scan=(scan+1)&0xffffffff,slot=slot,issue_tick=tick))
    return dict(requests=len(requests),qualified_latches=len(accepted),receipts=accepted)


def score(execution,plan,*,trial=scope.TRIAL):
    report = common.score_pair(execution,plan,trial=trial,measure_CA=False)
    last = scope.P394/'execution'
    control = scope.load(scope.P394/'trial-plan.json')
    saved = scope.load(scope.CONTROL)
    old_scans,old = common.audit.score_archive(last,control['kernel_banner'],expected_pairs=None,require_first=False)
    scans,new = common.audit.score_archive(execution,plan['kernel_banner'],expected_pairs=None,require_first=False)
    trace.require(old==saved['measurements']['0394'] and report['measurements'][trial]==new,
                  'physical evidence differs from the 0394 control or the new kernel')
    raw = (execution/'kernel.log').read_text()
    activation = scope.load(execution/'edr-activation.json')
    native = stock.perf.analyze(raw,perf_index=plan.get('native_gpu_perf_index',5),
                                bw_index=plan.get('native_bandwidth_index'))
    trace.require(activation['active'] and activation['code_checks_qualified'] and activation['once_abi_qualified'] and
                  native['native_request_accepted'],'0400 operating point or compositor scope differs')
    rows,_,n,d = stage.staging.parse(raw)
    latches = stage.staging.verified_latches(rows,flip.latch_receipts(raw,rows)['accepted_by_scan'])
    try:
        causal = prior.prior.timeline.measure(execution,raw,rows,n,d,latches,scans)
    except (KeyError,OSError,ValueError) as error:
        causal = dict(trace_error=str(error))
    active = stock.active_after_onset(scans,new)
    report.update(measurements={**report['measurements'],'0394':old},first_CA_timeline=causal,
        **{f'per_scan_0394_{trial}':flip.parent.parent.paired_ordinals({'0394':old_scans,trial:scans})},
        moving_Core_IO={'0394':saved['moving_Core_IO']['0394'],trial:report['moving_Core_IO']},
        all_warm_GPU_writers={'0394':saved['all_warm_GPU_writers']['0394'],trial:stock.producer(raw,new)},
        native_GPU_profile=native,recorder_CPU_placement=prior.placement(execution,raw,rows,n,d,new),
        staged_dispatch=dispatch_receipts(raw,latches),motion_after_onset=active,
        stable_60_fps_observed=report['stable_60_fps_observed'] and active['qualified'])
    return report


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'],'0400 scoring requires independent restoration')
    flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        report = score(execution,plan)
        name = 'scanout-comparison-0394-0400.json'
        stage.save_bounded(execution/name,report,3_300_000)
    except (OSError,KeyError,ValueError) as error:
        result.update(state='0400-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        staged_dispatch_requests=report['staged_dispatch']['requests'],
        qualified_staged_dispatch_latches=report['staged_dispatch']['qualified_latches'])


if __name__=='__main__':
    raise SystemExit(common.runner.main(scope,after_restore_fn=after_restore))
