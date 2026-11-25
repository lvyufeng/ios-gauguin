#!/usr/bin/env python3
"""Check the aperture and sample actual Metal bindings after independent recovery."""

from importlib import import_module

import frame344_log as trace
import frame374_native_ca as render
from frame369_swap_timing import decode as native_swaps
from frame412_target_binding import decode, measure

scope = import_module('prepare-frame414')
analysis = import_module('run-frame407-trial')
prior = analysis.prior


def binding_report(execution,raw,scored):
    rows,_,num,den = prior.stage.staging.parse(raw)
    start,end,*_ = render.envelope(raw)
    commits,targets = decode((execution/'post-capture/backboardd.log').read_text(),num,den)
    native = render.link_swaps(render.decode(raw,start,end),native_swaps(rows,num,den,begin_threads=True),start,end,num,den)
    latches = prior.stage.staging.verified_latches(rows,prior.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    windows = {name:work['windows'] for name,work in scored['moving_GPU'].items()}
    return dict(attachment_observations=len(targets),moving=measure(commits,targets,native,latches,windows,num,den))


def after_restore(execution,plan,result,before,code):
    trace.require(result['restored'] and result['independent_restore_verified'] and
                  result['static_root_comparison_passed'],'0414 requires independent restoration before scoring')
    prior.flip.after_restore(execution,plan,result,before,code,trial_scope=scope)
    inherited = result['state']
    if code or not (execution/'page-flip-latches.json').is_file():
        return
    try:
        raw = (execution/'kernel.log').read_text()
        exact = plan['frame414_exact_repeat']
        _,_,comparison = scope.choice()
        report = analysis.score(execution,plan,trial=scope.TRIAL,control=scope.P413,
            old_trial='0413',comparison=comparison,target_khz=1_401_600)
        phase = report['measurements'][scope.TRIAL]['ca_phase']
        trace.require(phase['qualified'] and not phase['missed'] and phase['work_duration_us']==plan['work_duration_us'],
                      '0414 DPU phase differs')
        aperture = [line for line in raw.splitlines() if line.startswith('SWEET F414 GPU MAP: ')]
        if not exact:
            report['reserved_GPU_mapping'] = dict(rows=aperture,page_tables_qualified=aperture==[scope.MAP_RECEIPT])
            try:
                bindings = binding_report(execution,raw,report['measurements'][scope.TRIAL])
                prior.stage.save_bounded(execution/'Metal-target-bindings.json',bindings,650_000)
            except (ValueError,KeyError,OSError) as error:
                bindings = dict(trace_error=str(error))
            report['Metal_target_summary'] = {key:value for key,value in bindings.items() if key!='moving'}
        name = 'scanout-comparison-0413-0414.json'
        prior.stage.save_bounded(execution/name,report,3_300_000)
    except (KeyError,OSError,ValueError) as error:
        result.update(state='0414-comparison-incomplete-root-restored',comparison_error=str(error))
        return
    result.update(state=scope.SUCCESS,comparison=name,core_and_legacy_state=inherited,
        DPU_independent_physical_FPS_qualified=True,stable_60_fps_observed=report['stable_60_fps_observed'],
        independently_repeated_identical_profile=bool(exact and report['stable_60_fps_observed']),
        GPU_readonly_aperture_qualified=aperture==[scope.MAP_RECEIPT])


if __name__=='__main__':
    raise SystemExit(prior.common.runner.main(scope,after_restore_fn=after_restore))
