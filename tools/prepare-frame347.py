#!/usr/bin/env python3
"""Package, exercise rollback models, and freeze the bounded 0347 experiment."""

import argparse
from importlib import import_module
import json
from pathlib import Path
from statistics import median
import subprocess
import sys

from frame347_scope import ANALYSIS, BASE, DOC, HEADER, MAIN, P346, REFERENCE, RESERVE, WORK
from frame347_scope import expected_plan, load, require, sha


stage = import_module('prepare-frame344')


def package():
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    native = load(manifest)
    require(native['state']=='0347-native-ARM64-linked' and native['inputs_unchanged'], 'unqualified 0347 kernel')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial='0347',
                            enable_frame_line_counter=True)
    previous = load(P346/'trial-plan.json')['boot_command']
    require(len(image['command'].encode())==607 and image['command']==previous.replace('sweetfb_stats=2','sweetfb_stats=3'),
            '0347 packed command changed beyond the counter mode')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial='0347')
    stage.save(BASE/'frame347-image.json',image)
    stage.save(BASE/'edr-native/result.json',edr)
    return dict(image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
                edr_sha256=edr['binary_sha256'])


def delta():
    core = load(BASE/'core-native/result.json')
    return stage.delta(BASE,P346,trial='0347',header=HEADER,baseline=BASE/'current-root-capture/result.json',
                       core_logical=core['bytes'])


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0347')
    return {k:v for k,v in result.items() if k!='input_pins'}


def storage(plan):
    components = dict(load(P346/'storage-bound-346.json')['components'])
    cap = plan['log_capture']
    require(sum(cap['sizes'].values())==cap['measured_baseline_bytes'] and
            cap['max_combined_log_bytes']-cap['measured_baseline_bytes']==cap['maximum_suffix_bytes'] > 0,
            'log space must match the measured baseline and aggregate cap')
    components['verified_log_suffixes'] = cap['maximum_suffix_bytes'] + len(cap['sizes'])*4096
    total = sum(components.values())
    require(total<=RESERVE and components['compact_analysis']==ANALYSIS, 'runtime storage exceeds reservation')
    return dict(state='bounded0347-runtime-batch',components=components,worst_case_bytes=total,reserve_bytes=RESERVE,
                fresh_log_bytes=cap['measured_baseline_bytes'],log_cap_bytes=cap['max_combined_log_bytes'],
                new_log_data_stored_once=True)


def criteria(plan):
    previous = load(P346/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','owned_core_sha256','owned_core_logical_bytes','parent_trial_plan_sha256',
               'root_header_sha256','install_plan_sha256','misc_before_sha256','optimization',
               'performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)} <= allowed,
            '0347 changed an effect outside the reviewed set')
    frame = plan['frame_capture']
    require(frame['volatile_counter_register_address']=='0x0ae6b8a8' and
            frame['maximum_volatile_counter_register_writes']==2 and frame['counter_enable_value']==3 and
            frame['counter_restore_value']==0 and frame['exact_counter_zero_preimage'] and
            frame['stable_counter_geometry_snapshots']==2 and frame['counter_write_readback'] and
            frame['counter_cleanup_requires_readable_domain_and_owned_value'] and
            frame['volatile_crc_register_address']=='0x0ae6b980' and frame['maximum_volatile_crc_register_writes']==4 and
            frame['maximum_total_display_register_writes']==6 and frame['target_refresh_hz']==60 and
            frame['modesets']==0 and plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'display writes, scripted input or sampling bounds differ')
    rollback = load(BASE/'restore-model/result.json')
    tests = load(BASE/'frame-host/result.json')
    bench = load(BASE/'core-host-reviewed/result.json')['warm_packet_benchmark']
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            tests['baseline_exact_joins']==730 and tests['unit_tests']>=26 and tests['control_models']==9 and
            tests['independent_readback_precedes_analysis'] and
            median(bench['ns_per_draw']['candidate']) < median(bench['ns_per_draw']['reference']),
            'insufficient packet, pipeline or rollback qualification')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P346,HEADER,plan)


def pins():
    prior = P346/'ready.json'
    inherited = dict(load(prior)['input_pins'])
    files = [WORK/name for name in subprocess.check_output(
        ['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()]
    files += [prior,DOC,Path(__file__),MAIN/'tools/storage-budget.py',P346/'trial-plan.json',
              P346/'storage-bound-346.json',P346/'execution/independent-restore.json',
              P346/'analysis-after-readback/restored-capture/result.json']
    files += [WORK/name for name in (
        'xnu/patches/series','xnu/patches/0257-gauguin-arm-scanout-counters.patch',
        'xnu/patches/0258-gauguin-scanout-counter-stats-mode.patch',
        'graphics/gauguin-program-io/0347-packet-shadow-ranges.patch',
        'tests/fixtures/dpu346_counter.c','tests/fixtures/dpu345_status.c','tests/fixtures/core344_encoding.cpp',
        'tests/fixtures/core346_program_slabs.cpp','tests/test_frame345_log.py','tests/test_frame344_log.py',
        'tests/test_core342_log.py','tests/test_frame347_trial.py')]
    files += [REFERENCE/name for name in ('result.json','kernel.log','kernel.log.bin','collection-analysis.json',
              'core-wait-execution-analysis.json','kernel-IO-identity-analysis.json','queue-identity-analysis.json',
              'frame-scanout-analysis.json')]
    files += [BASE/name for name in ('frame347-image.json','frame347-image.img','native-kernel/build-manifest.json',
              'native-kernel/candidate.kernel','core-native/result.json','edr-native/result.json',
              'core-host-reviewed/result.json','core-host-reviewed/program-slabs.log','frame-host/result.json',
              'frame-host/baseline-0346.json','current-root-capture/result.json',
              'build-storage-admission.json','prior-build-log-archive.json')]
    receipt_names = ('native-kernel/build-manifest.json','core-native/result.json','edr-native/result.json',
                     'frame347-image.json','frame-host/result.json','restore-model/result.json')
    for name in receipt_names:
        receipt = load(BASE/name)
        for path,digest in receipt.get('input_pins',{}).items():
            require(inherited.setdefault(path,digest)==digest, 'conflicting pinned build input: '+path)
        if 'binary' in receipt:
            files.append(Path(receipt['binary']))
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        files.extend(path for path in (BASE/folder).rglob('*') if path.is_file())
    for path in files:
        digest = sha(path)
        require(inherited.setdefault(str(path),digest)==digest, 'inherited pin changed: '+str(path))
    for name,digest in inherited.items():
        require(sha(name)==digest, 'pinned artifact changed: '+name)
    return inherited


def freeze():
    require(not any((BASE/name).exists() for name in ('trial-plan.json','ready.json','approval.json','execution',
                                                     'final-review.json','capture-profile.json')),
            '0347 already prepared or claimed')
    plan = expected_plan()
    criteria(plan)
    bound = storage(plan)
    pinned = pins()
    manifest_bytes = len(json.dumps(pinned,indent=2).encode()) + 1_048_576
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
        '--planned-bytes',str(RESERVE+manifest_bytes)],text=True,timeout=600))
    require(budget['admitted'], 'frozen files and runtime reservation unavailable')
    current = load(BASE/'current-root-capture/result.json')
    profile = load(P346/'capture-profile.json')
    profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=plan['log_capture']['max_combined_log_bytes'])
    for name,value in (('trial-plan.json',plan),('capture-profile.json',profile),('expected-baseline.json',current),
                       ('storage-bound-347.json',bound),('storage-runtime-admission.json',budget)):
        path = BASE/name
        stage.save(path,value)
        pinned[str(path)]=sha(path)
    ready = dict(state='ready-frame347-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
                 install_plan_sha256=plan['install_plan_sha256'],image_sha256=plan['image_sha256'],
                 pin_count=len(pinned),input_pins=pinned,approval_pending=True,device_writes=0,boot_attempts=0)
    stage.save(BASE/'ready.json',ready)
    return dict(ready_sha256=sha(BASE/'ready.json'),pin_count=len(pinned),
                worst_case_bytes=bound['worst_case_bytes'],runtime_reserve=RESERVE)


def review():
    ready_path, plan_path = BASE/'ready.json', BASE/'trial-plan.json'
    ready,plan = load(ready_path),load(plan_path)
    require(not (BASE/'approval.json').exists() and not (BASE/'execution').exists() and
            ready['state']=='ready-frame347-one-shot' and plan==expected_plan() and
            ready['trial_plan_sha256']==sha(plan_path) and ready['pin_count']==len(ready['input_pins']) and
            ready['image_sha256']==plan['image_sha256'] and ready['install_plan_sha256']==plan['install_plan_sha256'],
            'frozen 0347 scope differs')
    criteria(plan)
    profile = load(BASE/'capture-profile.json')
    budget = load(BASE/'storage-runtime-admission.json')
    require(profile['max_combined_log_bytes']==plan['log_capture']['max_combined_log_bytes'] and
            load(BASE/'storage-bound-347.json')==storage(plan) and budget['admitted'] and
            budget['planned_batch_bytes']>=RESERVE and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            'frozen log profile or storage budget differs')
    for name,digest in ready['input_pins'].items():
        require(sha(name)==digest, 'frozen input differs: '+name)
    report = dict(state='reviewed-frame347-one-shot',ready_sha256=sha(ready_path),trial_plan_sha256=sha(plan_path),
                  image_sha256=ready['image_sha256'],install_plan_sha256=ready['install_plan_sha256'],
                  no_device_mutation_during_preparation=True,restore_precedes_analysis=True,
                  device_writes=0,boot_attempts=0,pin_count=ready['pin_count'],
                  input_pins={str(p):sha(p) for p in (Path(__file__),DOC,WORK/'tools/run-frame347-trial.py')})
    stage.save(BASE/'final-review.json',report)
    return {k:v for k,v in report.items() if k!='input_pins'}


if __name__=='__main__':
    stages = {fn.__name__:fn for fn in (package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=stages)
    print(json.dumps(stages[parser.parse_args().step](),indent=2))
