#!/usr/bin/env python3
"""Build and freeze the bounded 0356 submit and whole-row latency trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path

from frame356_scope import BASE, CLEANUP, DOC, HEADER, LATENCY, P346, P355, PATCH, REF350, REF355, RESERVE, RUNTIME_PATCH, STARTUP, TOOLCHAIN
from frame356_scope import expected_plan, load, require

shared = import_module('prepare-frame349')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=405_000_000,'whole 0356 batch not admitted')
    import_module('build-frame347').link_scanout(P355/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0355',trial='0356',patches=(RUNTIME_PATCH,PATCH),compiler_bin=Path(TOOLCHAIN)/'usr/bin',
        extra_units=(('gauguin_gpu_runtime',P346/'native-kernel/build-manifest.json','compile-gauguin_gpu_runtime'),))


def package():
    return shared.package(base=BASE,prior=P355,trial='0356',patch=PATCH,mode=9,
                          signed_edr_reference=P355/'edr-native/result.json')


def delta():
    return shared.stage.delta(BASE,P355,trial='0356',header=HEADER,
        baseline=BASE/'current-root-capture/result.json',core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0356')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    bound = shared.storage(plan)
    run = import_module('run-frame356-trial')
    bound['components'].update(present_alignment_report=run.PRESENT_REPORT_BYTES,
        ready_selection_report=run.READY_REPORT_BYTES,release_queue_report=run.QUEUE_REPORT_BYTES,
        startup_report=run.STARTUP_REPORT_BYTES,unpresented_swap_report=run.MISSED_REPORT_BYTES,
        matched_latency_report=run.LATENCY_REPORT_BYTES,focus_copy_report=run.STROKE_COPY_REPORT_BYTES)
    total = sum(bound['components'].values())
    require(total<=RESERVE,'modeled output exceeds the 0356 reserve')
    return dict(bound,state='bounded0356-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P355/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','latency_acceptance'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed and
            plan['startup_acceptance']==STARTUP and plan['latency_acceptance']==LATENCY and plan['scripted_strokes']==13 and plan['scripted_reports']==442,
            '0356 capture, register writes or workload exceeds the inherited scope')
    host = load(BASE/'frame-host/result.json')
    rollback = load(BASE/'restore-model/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['prior_output_changes']==[[83,77],[47,80]] and host['reference_windows']==52 and
            host['c_fixtures']==12 and host['unit_tests']>=48 and host['ready_models']==10 and host['control_models']==9 and
            host['startup_models']==9 and host['missed_swap_stages']==6 and host['0354_startup_rejected'] and
            host['async_ack_guard_counts']==[[12,10],[24,16]] and host['register_and_memory_transcripts_equal'] and
            host['copy_block_bytes']==288 and host['copy_byte_equality'] and host['stroke_10_unknown_preserved'] and
            host['independent_readback_precedes_analysis'], 'rollback, comparison or startup qualification differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P355,HEADER,plan)


def pins():
    extra = [RUNTIME_PATCH,REF350/'kernel-IO-analysis.json',REF355/'kernel-IO-analysis.json',
        REF355/'ready-selection-analysis.json',REF355/'unpresented-swap-stages.json',
        REF355/'present-alignment-0350-0353-0355.json',
        REF355/'analysis-after-readback/presentation-diagnosis-0355.json',
        CLEANUP/'verified-retirement-manifest.json',CLEANUP/'retirement-complete.json']
    return shared.pins(base=BASE,prior=P355,doc=DOC,patch=PATCH,reference=REF355,trial='0356',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P355,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins)


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
