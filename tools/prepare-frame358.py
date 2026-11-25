#!/usr/bin/env python3
"""Prepare and freeze the single 0358 probe experiment."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame358_audit import SUMMARY_357
from frame358_scope import BASE, CLEANUP, DOC, FRAME_CAPACITY, HEADER, LOG_SUFFIX, MAIN
from frame358_scope import P357, PATCH, REF357, RESERVE, TOOLCHAIN, WORK, expected_plan, load, require, sha

shared = import_module('prepare-frame349')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=565_000_000,'0358 whole batch not admitted')
    source = MAIN/'research/tmp/gauguin-frame-344-worktree-20261119/research/tmp/frame-344/native-kernel-v2/build-manifest.json'
    prev = P357/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(prev,BASE/'native-kernel',parent_trial='0357',trial='0358',
        patches=(PATCH,),compiler_bin=Path(TOOLCHAIN)/'usr/bin',
        extra_units=(('GauguinGPU',prev,'compile-GauguinGPU'),('gauguin_ui_trace',source,'compile-0-gauguin_ui_trace')))


def package():
    return shared.package(base=BASE,prior=P357,trial='0358',patch=PATCH,mode=9,
                          signed_edr_reference=P357/'edr-native/result.json')


def capture():
    reference = REF357/'restored-capture/result.json'
    last = load(reference)
    profile = load(P357/'capture-profile.json')
    root = BASE/'current-root-capture/result.json'
    profile.update(out=str(root.parent),phase='before-boot',expected_header_sha256=HEADER,
                   max_combined_log_bytes=last['combined_log_bytes']+LOG_SUFFIX)
    current = load(root) if root.is_file() else import_module('capture-core342-root').capture(profile,save_files=False)
    require(current['root_header_sha256']==last['root_header_sha256']==HEADER and not current['device_writes'] and
            current['files']==last['files'] and current['directories']==last['directories'],
            'fresh TWRP files differ from 0357 restore')
    slots = BASE/'slot-capture/result.json'
    if not slots.is_file():
        subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
                        '--baseline',str(reference),'--out',str(slots.parent)],
                       check=True,capture_output=True,timeout=300)
    require(load(slots)['baseline_sha256']==sha(reference),'six original slots differ')
    snap = BASE/'metadata-snapshot/result.json'
    meta = load(snap) if snap.is_file() else import_module('capture-core342-metadata').capture(snap.parent,HEADER,trial='0358')
    require(not meta['device_writes'] and meta['root_header_sha256']==HEADER,'fresh HFS snapshot differs')
    return dict(metadata_bytes=meta['compressed_bytes'],log_bytes=current['combined_log_bytes'],device_writes=0)


def delta():
    return shared.stage.delta(BASE,P357,trial='0358',header=HEADER,
        baseline=REF357/'restored-capture/result.json',core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0358')
    return {k:v for k,v in result.items() if k!='input_pins'}


def controls():
    plan = expected_plan()
    out = BASE/'frame-host'
    run = import_module('run-frame358-trial')
    try:
        run.after_restore(out,plan,dict(restored=True,independent_restore_verified=False,static_root_comparison_passed=True),
                          None,0)
    except ValueError as error:
        require('independent restore' in str(error),'unexpected pre-readback error')
    else:
        raise ValueError('0358 analyzed before independent readback')
    fixture = import_module('check-core342-pipeline')
    rows = []
    for scenario in ('success','post-capture-failure','independent-failure','restore-rollback','install-rollback',
                     'final-capture-failure','observer-owner-alive','suffix-success','suffix-prefix-mismatch'):
        fixture.control_fixture(out,plan,scenario,rows)
    receipt = dict(scenarios=rows,analysis_requires_independent_readback=True,device_commands=0)
    shared.stage.save(out/'control-models.json',receipt)
    return dict(scenarios=len(rows),analysis_requires_independent_readback=True)


def storage(plan):
    bound = import_module('prepare-frame357').storage(plan)
    bound['components']['probe_report'] = import_module('run-frame358-trial').PROBE_REPORT_BYTES
    total=sum(bound['components'].values())
    require(total<=RESERVE,'0358 total output exceeds reserve')
    return dict(bound,state='bounded0358-runtime-batch',worst_case_bytes=total)


def criteria(plan):
    previous = load(P357/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256',
               'root_header_sha256','install_plan_sha256','misc_before_sha256','parent_trial_plan_sha256','optimization',
               'performance_comparison','log_capture','frame_capture','fence_probe'}
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=allowed and
            plan['frame_capture']==dict(previous['frame_capture'],records=FRAME_CAPACITY),
            '0358 changed an unrelated effect or acquisition window')
    host,control,rollback = (load(BASE/name) for name in (
        'frame-host/result.json','frame-host/control-models.json','restore-model/result.json'))
    baseline = load(BASE/'repeat-audit.json')['lanes']['active']
    require(host['built_source_probe_fixture'] and host['built_source_ownership_fixture'] and
            host['original_guard_and_copy'] and host['native_submit_and_completion_source_identical'] and
            host['expanded_trace_fixture_rows']==16516 and host['invalid_capture_rejects']==3 and
            host['invalid_publication_rejects']==3 and host['exact_synthetic_publication_join'] and
            host['unit_tests']>=48 and host['reference_windows']==104 and len(control['scenarios'])==9 and
            control['analysis_requires_independent_readback'] and rollback['all_model_IO_writes_memory_only'] and
            len(rollback['checks'])==47 and rollback['all_restore_partial_write_points']==17 and
            rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            baseline['stages']==dict(no_new_surface_swap_before_cutoff=72,new_swap_without_exact_issue_by_cutoff=48,
                exact_issue_waiting_for_visibility=23,take_deferred=21) and
            baseline['probe_timing_opportunities']['whole_p95_observer_band']==17,
            '0358 source, measured deadline, comparison or restore proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P357,HEADER,plan)


def pins():
    extra = [BASE/'repeat-audit.json',BASE/'frame-host/control-models.json',SUMMARY_357,
        CLEANUP/'verified-retirement-manifest.json',CLEANUP/'retirement-complete.json',
        REF357/'frame-scanout-analysis.json',REF357/'kernel-IO-analysis.json']
    return shared.pins(base=BASE,prior=P357,doc=DOC,patch=PATCH,reference=REF357,trial='0358',extra=extra)


def freeze():
    return shared.freeze(base=BASE,prior=P357,expected=expected_plan,validate=criteria,
                         storage_bound=storage,pin_inputs=pins)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                         storage_bound=storage,preparer=Path(__file__))


if __name__=='__main__':
    stages = {fn.__name__:fn for fn in (build,package,capture,delta,model,controls,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=stages)
    result = stages[parser.parse_args().step]()
    if result is not None:
        print(json.dumps(result,indent=2))
