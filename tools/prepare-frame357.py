#!/usr/bin/env python3
"""Prepare and freeze 0357 with only the approved candidate and restore bounds."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame355_scope import P354
from frame356_scope import REF350, REF355
from frame357_replay import INPUTS
from frame357_scope import BASE, CALIBRATION_PATCH, CLEANUP, DOC, HEADER, LOG_SUFFIX, MAIN
from frame357_scope import P356, PATCH, REF356, RESERVE, TOOLCHAIN, WORK, expected_plan, load, require, sha

shared = import_module('prepare-frame349')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=565_000_000,
            'complete 0357 build and execution batch not admitted')
    touch = MAIN/'research/tmp/gauguin-frame-344-worktree-20261119/research/tmp/frame-344/native-kernel-v2/build-manifest.json'
    import_module('build-frame347').link_scanout(P356/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0356',trial='0357',patches=(PATCH,CALIBRATION_PATCH),compiler_bin=Path(TOOLCHAIN)/'usr/bin',
        extra_units=(('GauguinGPU',P354/'native-kernel/build-manifest.json','compile-GauguinGPU'),
                     ('sweet_touch',touch,'compile-0-sweet_touch')))


def package():
    return shared.package(base=BASE,prior=P356,trial='0357',patch=PATCH,mode=9,
                          signed_edr_reference=P356/'edr-native/result.json')


def capture():
    reference = REF356/'restored-capture/result.json'
    last = load(reference)
    profile = load(P356/'capture-profile.json')
    profile.update(out=str(BASE/'current-root-capture'),phase='before-boot',expected_header_sha256=HEADER,
                   max_combined_log_bytes=last['combined_log_bytes']+LOG_SUFFIX)
    path = BASE/'current-root-capture/result.json'
    current = (load(path) if path.is_file() else
               import_module('capture-core342-root').capture(profile,save_files=False))
    require(current['root_header_sha256']==last['root_header_sha256']==HEADER and not current['device_writes'] and
            current['files']==last['files'] and current['directories']==last['directories'],
            'live files differ from 0356 independent readback')
    slot = BASE/'slot-capture/result.json'
    if not slot.is_file():
        subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
                        '--baseline',str(reference),'--out',str(slot.parent)],
                       check=True,capture_output=True,timeout=300)
    require(load(slot)['baseline_sha256']==sha(reference),'six slot receipts differ')
    path = BASE/'metadata-snapshot/result.json'
    metadata = (load(path) if path.is_file() else
                import_module('capture-core342-metadata').capture(path.parent,HEADER,trial='0357'))
    require(not metadata['device_writes'] and metadata['root_header_sha256']==HEADER,'metadata capture differs')
    return dict(log_bytes=current['combined_log_bytes'],metadata_bytes=metadata['compressed_bytes'],device_writes=0)


def delta():
    return shared.stage.delta(BASE,P356,trial='0357',header=HEADER,
        baseline=REF356/'restored-capture/result.json',core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0357')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    bound = shared.storage(plan)
    run = import_module('run-frame357-trial')
    bound['components'].update(present_alignment_report=run.PRESENT_REPORT_BYTES,ready_report=run.READY_REPORT_BYTES,
        startup_report=run.STARTUP_REPORT_BYTES,missed_report=run.MISSED_REPORT_BYTES)
    total = sum(bound['components'].values())
    require(total<=RESERVE,'0357 complete modeled output exceeds storage reserve')
    return dict(bound,state='bounded0357-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P356/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture',
               'issued_retention','latch_calibration'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            '0357 differs outside the issued retention and calibration scope')
    model = load(BASE/'restore-model/result.json')
    host = load(BASE/'frame-host/result.json')
    replay = load(BASE/'offline-replay.json')
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and model['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['checked_actual_kernel_functions'] and host['original_read_guard_and_copy'] and
            host['native_order_and_single_FIFOs_preserved'] and host['independent_readback_precedes_analysis'] and
            host['retained_claim_decoder_model'] and
            host['unit_tests']>=48 and host['control_models']==9 and host['reference_windows']==78 and
            host['calibration']['rejected_corrupt_marker_scenarios']==8 and
            [x['lag'] for x in host['calibration']['synthetic_signature_models']]==[0,1] and
            [replay['trials'][n]['scenarios']['bracketed_measured_max']['recovered_in_both_baseline_empty_slots']['active']
             for n in ('0355','0356')]==[20,16],
            '0357 lifecycle, CRC checks, restore model or replay differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P356,HEADER,plan)


def pins():
    extra = [CALIBRATION_PATCH,BASE/'offline-replay.json',CLEANUP/'verified-retirement-manifest.json',
             CLEANUP/'retirement-complete.json',REF356/'present-alignment-0350-0355-0356.json']
    extra.extend(path/name for path in (REF355,REF356) for name in INPUTS)
    extra.extend(REF350/name for name in ('result.json','independent-restore.json','frame-scanout-analysis.json'))
    return shared.pins(base=BASE,prior=P356,doc=DOC,patch=PATCH,reference=REF356,trial='0357',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P356,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__))


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    result = steps[parser.parse_args().step]()
    if result is not None:
        print(json.dumps(result,indent=2))
