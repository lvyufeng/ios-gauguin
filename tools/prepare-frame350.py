#!/usr/bin/env python3
"""Prepare the fixed 0350 display-control and queue-trace trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path

from frame350_scope import BASE, DOC, HEADER, P349, PATCH, REFERENCE, RESERVE, WORK
from frame350_scope import expected_plan, load, require
from frame349_log import DATA_INPUT


shared = import_module('prepare-frame349')
TRIAL = '0350'


def build():
    require(load(BASE/'build-storage-admission.json')['admitted'],'whole 0350 batch not admitted')
    import_module('build-frame347').link_scanout(P349/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0349',trial=TRIAL,patches=(PATCH,))


def package():
    return shared.package(base=BASE,prior=P349,trial=TRIAL,patch=PATCH,mode=6)


def delta():
    return shared.stage.delta(BASE,P349,trial=TRIAL,header=HEADER,baseline=BASE/'current-root-capture/result.json',
                              core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    bound = shared.storage(plan)
    bound['components']['focused_queue_report'] = import_module('run-frame350-trial').QUEUE_REPORT_BYTES
    total = sum(bound['components'].values())
    require(total<=RESERVE,'combined output exceeds 0350 reserve')
    return dict(bound,state='bounded0350-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P349/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'change outside the 0350 effect scope')
    frame = plan['frame_capture']
    require(frame['opt_in']=='sweetfb_stats=6' and frame['controls_observed']==[0] and
            frame['crc_required_preimage']==DATA_INPUT and frame['crc_preimage_reads']==2 and
            frame['crc_preimage_requires_adjacent_qualified_edges'] and
            frame['crc_cleanup_values']==[1024,DATA_INPUT] and frame['crc_cleanup_readback_equals_recorded_preimage'] and
            frame['crc_no_cleanup_stores_after_ownership_fault'] and
            frame['volatile_crc_register_address']=='0x0ae6b980' and
            frame['read_only_crc_signature_address']=='0x0ae6b984' and
            frame['maximum_total_display_register_writes']==frame['maximum_volatile_crc_register_writes']==4 and
            frame['maximum_volatile_counter_register_writes']==frame['modesets']==frame['crc_retries']==0 and
            frame['target_refresh_hz']==60 and frame['crc_polls_per_pair']==2 and
            frame['crc_setup_attempts']==frame['crc_cleanup_attempts']==1 and
            frame['crc_blank_lines']==[2752,4480] and frame['crc_sample_rows_max']==3000 and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'MISR, display mode, input or sampling scope differs')
    rollback = load(BASE/'restore-model/result.json')
    host = load(BASE/'frame-host/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['reference_vblank_intervals']==[270,182] and host['reference_script_joins']==726 and
            host['crc_replay_phases']==[0,1] and host['unit_tests']>=45 and host['control_models']==9 and
            host['independent_readback_precedes_analysis'] and host['focus_strokes']==[3,11],
            'local scanout, queue or restore proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P349,HEADER,plan)


def pins():
    extra = [REFERENCE/'kernel-IO-analysis.json',BASE/'frame-host/0349-queue-tail.json']
    return shared.pins(base=BASE,prior=P349,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P349,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__))


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    result = steps[parser.parse_args().step]()
    if result is not None:
        print(json.dumps(result,indent=2))
