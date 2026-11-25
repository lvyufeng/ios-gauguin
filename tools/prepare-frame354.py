#!/usr/bin/env python3
"""Build, stage, model and freeze the bounded 0354 trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path

from frame354_scope import BASE, CLEANUP, DOC, HEADER, P353, PATCH, POLICY, REF350, REF353, RESERVE, TOOLCHAIN
from frame354_scope import expected_plan, load, require

shared = import_module('prepare-frame349')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=405_000_000, 'whole 0354 batch not admitted')
    previous = P353/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',parent_trial='0353',trial='0354',
        patches=(PATCH,),extra_units=(('GauguinGPU',previous,'compile-GauguinGPU'),),compiler_bin=Path(TOOLCHAIN)/'usr/bin')


def package():
    return shared.package(base=BASE,prior=P353,trial='0354',patch=PATCH,mode=9,
                          signed_edr_reference=P353/'edr-native/result.json')


def delta():
    return shared.stage.delta(BASE,P353,trial='0354',header=HEADER,
        baseline=BASE/'current-root-capture/result.json',core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0354')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    bound = shared.storage(plan)
    run = import_module('run-frame354-trial')
    bound['components'].update(present_alignment_report=run.PRESENT_REPORT_BYTES,
        ready_selection_report=run.READY_REPORT_BYTES,release_queue_report=run.QUEUE_REPORT_BYTES)
    total = sum(bound['components'].values())
    require(total<=RESERVE,'modeled output exceeds the 0354 reserve')
    return dict(bound,state='bounded0354-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P353/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'effect outside frozen 0354 scope')
    frame, old_frame = (p['frame_capture'] for p in (plan,previous))
    require({k:v for k,v in frame.items() if k!='presentation_policy'}==
            {k:v for k,v in old_frame.items() if k!='presentation_policy'} and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442, 'display register or workload scope differs')
    old_policy = dict(old_frame['presentation_policy'])
    old_policy.pop('observed_ready_kept_with_latest_pending_generation')
    require(frame['presentation_policy']=={**old_policy,**POLICY}, 'held readiness or copy rules differ')
    host = load(BASE/'frame-host/result.json')
    rollback = load(BASE/'restore-model/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['prior_output_changes']==[[83,77],[34,41]] and host['reference_windows']==52 and
            host['c_fixtures']==9 and host['unit_tests']>=48 and host['ready_models']==10 and host['control_models']==9 and
            host['independent_readback_precedes_analysis'], 'rollback, comparison or selection qualification differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P353,HEADER,plan)


def pins():
    extra = [REF350/'kernel-IO-analysis.json',REF353/'kernel-IO-analysis.json',REF353/'ready-selection-analysis.json',
        REF353/'present-alignment-0350-0352-0353.json',REF353/'analysis-after-readback/cross-frame-present-audit.json',
        CLEANUP/'verified-retirement-manifest.json',CLEANUP/'retirement-complete.json']
    return shared.pins(base=BASE,prior=P353,doc=DOC,patch=PATCH,reference=REF353,trial='0354',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P353,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins)


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
