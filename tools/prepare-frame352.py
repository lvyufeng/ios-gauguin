#!/usr/bin/env python3
"""Build or freeze the bounded 0352 GPU-ready presentation trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path

from frame352_scope import BASE, CLEANUP, COPY_BUDGET_NS, DOC, GPU_BUILD, HEADER, P351, PATCH, REF350, REF351, RESERVE
from frame352_scope import expected_plan, load, require

shared = import_module('prepare-frame349')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=430_000_000,
            'whole 0352 build batch not admitted')
    import_module('build-frame347').link_scanout(P351/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0351',trial='0352',patches=(PATCH,),
        extra_units=(('GauguinGPU',GPU_BUILD,'compile-corrected-GauguinGPU'),))


def package():
    return shared.package(base=BASE,prior=P351,trial='0352',patch=PATCH,mode=8)


def delta():
    return shared.stage.delta(BASE,P351,trial='0352',header=HEADER,
        baseline=BASE/'current-root-capture/result.json',core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0352')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    bound = shared.storage(plan)
    run = import_module('run-frame352-trial')
    bound['components'].update(present_alignment_report=run.PRESENT_REPORT_BYTES,release_queue_report=run.QUEUE_REPORT_BYTES)
    total = sum(bound['components'].values())
    require(total<=RESERVE,'combined modeled output exceeds the 0352 reserve')
    return dict(bound,state='bounded0352-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P351/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'effect outside frozen 0352 scope')
    frame = plan['frame_capture']
    def inherited(capture):
        return {key:value for key,value in capture.items() if key not in ('opt_in','presentation_policy')}
    require(inherited(frame)==inherited(previous['frame_capture']) and frame['opt_in']=='sweetfb_stats=8' and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442,
            'CRC setup, restoration or workload changed')
    policy = frame['presentation_policy']
    require(policy['copy_budget_ns']==COPY_BUDGET_NS and policy['single_layer_mask']==1 and
            policy['maximum_attempts_per_hardware_frame']==2 and policy['maximum_copies_per_hardware_frame']==1 and
            policy['timed_attempts_per_hardware_frame']==policy['ready_retry_attempts_per_hardware_frame']==1 and
            policy['ready_ticket_surface_and_pending_generation_required'] and policy['existing_read_guard_required'] and
            policy['normal_notification_clock'] and policy['existing_reference_and_requeue_rules'] and
            policy['wake_after_surface_visibility_and_completion_publication'] and
            policy['only_during_45s_frame_capture'] and policy['verified_after_guard_before_copy'] and
            policy['output_store_barrier_and_end_phase_receipt'],
            'GPU-ready, copy or lifetime policy differs')
    host = load(BASE/'frame-host/result.json')
    rollback = load(BASE/'restore-model/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['prior_output_changes']==[[83,77],[28,36]] and host['reference_windows']==52 and host['c_fixtures']==7 and
            host['control_models']==9 and host['ready_models']>=6 and host['focus_strokes']==[4,6] and
            host['independent_readback_precedes_analysis'], '0352 model or reference gate differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P351,HEADER,plan)


def pins():
    extra = [REF350/'kernel-IO-analysis.json',REF351/'kernel-IO-analysis.json',
        REF351/'analysis-after-readback/blanking-boundary-verification.json',REF351/'queue-release-0350-0351.json',
        REF351/'present-alignment-0350-0351.json',CLEANUP/'verified-retirement-manifest.json',
        CLEANUP/'retirement-complete.json']
    return shared.pins(base=BASE,prior=P351,doc=DOC,patch=PATCH,reference=REF351,trial='0352',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P351,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__))


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    steps = {fn.__name__:fn for fn in (build,package,delta,model,freeze,review)}
    parser.add_argument('step',choices=steps)
    result = steps[parser.parse_args().step]()
    if result is not None:
        print(json.dumps(result,indent=2))
