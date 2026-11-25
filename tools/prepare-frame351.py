#!/usr/bin/env python3
"""Freeze the bounded 0351 display trial and review its inputs."""

import argparse
from importlib import import_module
import json
from pathlib import Path

from frame351_scope import BASE, CLEANUP, DOC, HEADER, P350, PATCH, REFERENCE, RESERVE
from frame351_scope import expected_plan, load, require


shared=import_module('prepare-frame349')


def storage(plan):
    bound=shared.storage(plan)
    run=import_module('run-frame351-trial')
    bound['components'].update(present_alignment_report=run.PRESENT_REPORT_BYTES,release_queue_report=run.QUEUE_REPORT_BYTES)
    total=sum(bound['components'].values())
    require(total<=RESERVE,'combined modeled output exceeds the 0351 reserve')
    return dict(bound,state='bounded0351-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous=load(P350/'trial-plan.json')
    allowed={'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
             'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
             'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'effect outside frozen 0351 scope')
    frame=plan['frame_capture']
    inherited={key:val for key,val in frame.items() if key not in ('opt_in','presentation_policy')}
    require(inherited=={key:val for key,val in previous['frame_capture'].items() if key!='opt_in'} and
            frame['opt_in']=='sweetfb_stats=7' and plan['scripted_strokes']==13 and plan['scripted_reports']==442,
            'CRC setup, restoration or workload changed')
    p=frame['presentation_policy']
    require(p['single_layer_mask']==1 and p['maximum_attempts_per_hardware_frame']==2 and
            p['maximum_copies_per_hardware_frame']==1 and p['normal_notification_clock'] and
            p['existing_reference_and_requeue_rules'] and p['only_during_45s_frame_capture'],
            'present scheduling exceeds the reviewed path')
    host=load(BASE/'frame-host/result.json')
    rollback=load(BASE/'restore-model/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['reference_vblank_intervals']==[270,182] and host['reference_changes']==[83,77] and
            host['focus_strokes']==[4,6] and host['control_models']==9 and host['independent_readback_precedes_analysis'],
            'local validation gate differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P350,HEADER,plan)


def pins():
    extra=[REFERENCE/'kernel-IO-analysis.json',P350/'analysis-after-readback/same-frame-output-updates.json',
           CLEANUP/'verified-retirement-manifest.json',CLEANUP/'retirement-complete.json']
    return shared.pins(base=BASE,prior=P350,doc=DOC,patch=PATCH,reference=REFERENCE,trial='0351',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P350,expected=expected_plan,validate=criteria,storage_bound=storage,pin_inputs=pins)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    steps={fn.__name__:fn for fn in (freeze,review)}
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
