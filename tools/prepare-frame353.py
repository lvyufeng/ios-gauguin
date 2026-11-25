#!/usr/bin/env python3
"""Build and freeze the bounded 0353 cross-frame readiness trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path

from frame353_scope import BASE, CLEANUP, DOC, HEADER, P352, PATCH, REF350, REF352, RESERVE, TOOLCHAIN
from frame353_scope import expected_plan, load, require, sha

shared = import_module('prepare-frame349')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=405_000_000,
            'whole 0353 build batch not admitted')
    previous = P352/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0352',trial='0353',patches=(PATCH,),
        extra_units=(('GauguinGPU',previous,'compile-GauguinGPU'),),
        compiler_bin=Path(TOOLCHAIN)/'usr/bin')


def package():
    return shared.package(base=BASE,prior=P352,trial='0353',patch=PATCH,mode=9,
                          signed_edr_reference=P352/'edr-native/result.json')


def delta():
    return shared.stage.delta(BASE,P352,trial='0353',header=HEADER,
        baseline=BASE/'current-root-capture/result.json',core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0353')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    bound = shared.storage(plan)
    run = import_module('run-frame353-trial')
    bound['components'].update(present_alignment_report=run.PRESENT_REPORT_BYTES,
        ready_selection_report=run.READY_REPORT_BYTES,release_queue_report=run.QUEUE_REPORT_BYTES)
    total = sum(bound['components'].values())
    require(total<=RESERVE,'combined modeled output exceeds the 0353 reserve')
    return dict(bound,state='bounded0353-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P352/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'effect outside frozen 0353 scope')
    frame = plan['frame_capture']

    def inherited(capture):
        return {key:value for key,value in capture.items() if key not in ('opt_in','presentation_policy')}

    require(inherited(frame)==inherited(previous['frame_capture']) and frame['opt_in']=='sweetfb_stats=9' and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442,
            'CRC setup, restoration or workload changed')
    policy=frame['presentation_policy']
    old=previous['frame_capture']['presentation_policy']
    for key in ('copy_budget_ns','phase_open_line','guard_lines','full_copy_bytes','full_copy_panel_and_source_stride',
                'read_only_prefetch_registers','normal_notification_clock','existing_reference_and_requeue_rules',
                'existing_read_guard_required','verified_after_guard_before_copy','output_store_barrier_and_end_phase_receipt'):
        require(policy[key]==old[key],f'0353 changed {key}')
    require(policy['maximum_attempts_per_hardware_frame']==policy['maximum_copies_per_hardware_frame']==1 and
            policy['readiness_watched_at_swap'] and policy['observed_ready_kept_with_latest_pending_generation'] and
            policy['readiness_probe_uses_GPU_try_lock_outside_framebuffer_lock'] and
            policy['target_hardware_slot_selected_after_readiness'],
            'ready scheduling or copy rules differ')
    host = load(BASE/'frame-host/result.json')
    rollback = load(BASE/'restore-model/result.json')
    edr = load(BASE/'edr-native/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['prior_output_changes']==[[83,77],[50,51]] and host['reference_windows']==52 and host['c_fixtures']==8 and
            host['control_models']==9 and host['ready_models']==8 and host['focus_strokes']==[4,6] and
            host['independent_readback_precedes_analysis'] and edr['identity_only_retarget'],
            '0353 model, reference or signature gate differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P352,HEADER,plan)


def toolchain_replacements():
    xcode=Path('/Applications/Xcode.app/Contents/Developer')
    sdk=xcode/'Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk'
    quartz=sdk/'System/Library/Frameworks/QuartzCore.framework/Headers'
    runtime='usr/lib/clang/21/lib/darwin/libclang_rt.cc_kext.a'
    historical=(sdk/'SDKSettings.json',quartz/'CAAnimation.h',quartz/'CADisplayLink.h',quartz/'CAFrameRateRange.h',
                xcode/'Toolchains/XcodeDefault.xctoolchain'/runtime)
    prior=P352/'ready.json'
    require(sha(prior)=='425c4ce902896bba9b44c4f27a7480ea3ece6c17ee5ec9ff9847e52aa99f6750','0352 ready receipt differs')
    inherited=load(prior)['input_pins']
    built=BASE/'native-kernel/build-manifest.json'
    edr=BASE/'edr-native/result.json'
    manifest=load(built)
    require(manifest['baseline_reproduced_except_uuid'] and load(edr)['identity_only_retarget'] and
            all(str(xcode) not in arg for step in manifest['steps'] for arg in step['argv']),
            '0353 requires historical Xcode build inputs')
    require(not any(str(name) in dep.read_text() for dep in (built.parent).glob('*.d') for name in historical),
            'a replaced toolchain input is a direct 0353 compiler dependency')
    replaced=[]
    for path in historical:
        before=inherited[str(path)]
        current=sha(path) if path.is_file() else None
        if before!=current:
            replaced.append(dict(path=str(path),historical_sha256=before,current_sha256=current))
    receipt=BASE/'toolchain-replacements.json'
    details=dict(state='0353-CLT-reproduced-baseline-and-retargeted-signed-helper',replaced=replaced,
                 prior_ready_sha256=sha(prior),reproduced_build_sha256=sha(built),signed_helper_receipt_sha256=sha(edr))
    if receipt.exists():
        require(load(receipt)==details,'toolchain replacement audit changed')
    else:
        shared.stage.save(receipt,details)
    return receipt,Path(TOOLCHAIN)/runtime,[item['path'] for item in replaced]


def pins():
    toolchain,clang_runtime,retired=toolchain_replacements()
    extra = [toolchain,clang_runtime,REF350/'kernel-IO-analysis.json',REF352/'kernel-IO-analysis.json',
        REF352/'analysis-after-readback/gpu-ready-window-audit.json',REF352/'queue-release-0350-0351-0352.json',
        REF352/'present-alignment-0350-0351-0352.json',CLEANUP/'verified-retirement-manifest.json',
        CLEANUP/'retirement-complete.json']
    return shared.pins(base=BASE,prior=P352,doc=DOC,patch=PATCH,reference=REF352,trial='0353',
                       extra=extra,replaced_historical_paths=retired)


def freeze():
    return shared.freeze(base=BASE,prior=P352,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins)


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
