#!/usr/bin/env python3
"""Pack, stage, model, and freeze the bounded 0345 experiment."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame345_scope import ANALYSIS, BASE, DOC, HEADER, LOG_PATHS, MAIN, P344, POST_LOG_BYTES, RESERVE, WORK
from frame345_scope import expected_plan, load, require, sha


save = import_module('prepare-frame344').save


def package():
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    native = load(manifest)
    require(native['state']=='0345-native-ARM64-linked' and native['inputs_unchanged'],'unqualified 0345 kernel')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial='0345')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial='0345')
    save(BASE/'frame345-image.json',image)
    save(BASE/'edr-native/result.json',edr)
    return dict(image_sha256=image['image_sha256'], image_bytes=image['image_bytes'], helper_sha256=edr['binary_sha256'])


def delta():
    return import_module('prepare-frame344').delta(BASE,P344,trial='0345',header=HEADER,
                                                  baseline=BASE/'current-root-capture/result.json')


def model():
    value = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0345')
    return {key:val for key,val in value.items() if key!='input_pins'}


def storage(current):
    original = load(P344/'storage-bound-344.json')['components']
    keep = ('kernel_ring_raw_and_decoded','observer_stdout_stderr','one_restore_preimage_and_target_set',
            'eight_executor_receipts','progress_and_restore_recipe','three_hash_manifests')
    components = {key:original[key] for key in keep}
    baseline_bytes = sum(current['files'][path]['bytes'] for path in LOG_PATHS)
    require(0<baseline_bytes<=POST_LOG_BYTES,'postboot log limit is smaller than the baseline')
    components.update(verified_log_suffixes=POST_LOG_BYTES-baseline_bytes+4*4096,
                      compact_analysis=ANALYSIS,frame_analysis_and_comparison=10_000_000,
                      overhead_and_executor_output=2_000_000)
    total = sum(components.values())
    require(total<=RESERVE,'runtime batch cannot fit its numeric reservation')
    return dict(state='bounded0345-runtime-batch',components=components, worst_case_bytes=total,
                reserve_bytes=RESERVE, fresh_log_bytes=baseline_bytes, new_log_data_stored_once=True)


def criteria(plan):
    prior = load(P344/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','kernel_identity','kernel_banner',
               'EDR_helper_sha256','owned_core_sha256','root_header_sha256','install_plan_sha256',
               'misc_before_sha256','parent_trial_plan_sha256','storage_reserve_bytes','all_core_TUs_recompiled',
               'max_analysis_bytes','verified_log_suffixes_only','optimization','performance_comparison','frame_capture'}
    require({key for key in set(plan)|set(prior) if plan.get(key)!=prior.get(key)} <= allowed,
            '0345 scope changes a device effect outside the reviewed list')
    frame = plan['frame_capture']
    require(frame['volatile_crc_register_address']=='0x0ae6b980' and frame['maximum_volatile_crc_register_writes']==4
            and frame['zero_control_preimage_required'] and frame['modesets']==0 and frame['target_refresh_hz']==60
            and plan['scripted_reports']==442 and plan['scripted_strokes']==13
            and plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'CRC, mode or swipe and sample limits differ')
    checks = load(BASE/'restore-model/result.json')
    host = load(BASE/'frame-host/result.json')
    require(checks['all_model_IO_writes_memory_only'] and len(checks['checks'])==47 and
            checks['all_restore_partial_write_points']==17 and checks['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['unit_tests']==10 and host['baseline_script_jobs']==725 and
            'actual-executor-control-suffix-prefix-mismatch' in host['model_controls'] and
            'actual-executor-control-suffix-success' in host['model_controls'], '0345 host review incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P344,HEADER,plan)


def freeze():
    require(not any((BASE/name).exists() for name in ('trial-plan.json','ready.json','approval.json','execution',
                                                     'final-review.json','capture-profile.json')),
            '0345 trial already prepared or claimed')
    plan = expected_plan()
    criteria(plan)
    current = load(BASE/'current-root-capture/result.json')
    bound = storage(current)
    prior_ready = P344/'ready.json'
    pins = dict(load(prior_ready)['input_pins'])
    paths = [Path(__file__),DOC,prior_ready,P344/'trial-plan.json',P344/'storage-bound-344.json',
             WORK/'xnu/patches/series',WORK/'xnu/patches/0254-gauguin-scanout-gates-submit-resolve.patch',
             WORK/'graphics/gauguin-program-io/0345-core-recording.patch',
             WORK/'tests/fixtures/dpu345_status.c',WORK/'tests/fixtures/core344_encoding.cpp',
             WORK/'tests/fixtures/gpu-user/async_submit_host.cpp',WORK/'tests/test_gpu_async_submit.py',
             WORK/'tests/test_frame345_log.py',WORK/'tests/test_frame344_log.py',WORK/'tools/dpu-readonly345.c',
             MAIN/'tools/storage-budget.py']
    test = load(BASE/'submit-host-final/result.json')
    require(all(sha(name)==digest for name,digest in test['input_pins'].items()),
            'submit ownership test inputs differ')
    paths += [WORK/path for path in subprocess.check_output(
        ['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()]
    for name in ('build-frame345.py','check-frame345-host.py','frame345_scope.py','frame345_log.py','run-frame345-trial.py'):
        paths.append(WORK/'tools'/name)
    paths += [P344/'execution'/name for name in ('independent-restore.json','restored-capture/result.json','result.json',
        'collection-analysis.json','kernel.log','kernel-IO-identity-analysis.json','core-wait-execution-analysis.json',
        'queue-identity-analysis.json','frame-scanout-analysis.json')]
    paths += [BASE/name for name in ('frame345-image.json','frame345-image.img','core-native/result.json',
        'native-kernel/build-manifest.json','edr-native/result.json','submit-host-final/result.json',
        'core-host-reviewed/result.json','frame-host/result.json','host-retirement-result.json',
        'dpu-readonly/recovery-kms-stdout.txt','dpu-readonly/recovery-clock-status.txt')]
    paths += [Path(load(BASE/path)['binary']) for path in ('core-native/result.json','edr-native/result.json')]
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        paths.extend(path for path in (BASE/folder).rglob('*') if path.is_file())
    for path in paths:
        value = sha(path)
        require(pins.setdefault(str(path),value)==value,'existing pinned artifact differs: '+str(path))
    for name,digest in pins.items():
        require(sha(name)==digest,'pinned artifact differs: '+name)

    # The new ready manifest is a second billed copy of the chained pins.
    # Reserve its measured serialization in addition to the runtime batch.
    freeze_bytes = len(json.dumps(pins,indent=2).encode())+1_048_576
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
                      '--planned-bytes',str(RESERVE+freeze_bytes)],text=True,timeout=600))
    require(budget['admitted'],'frozen files and runtime storage reservation unavailable')
    profile = load(P344/'capture-profile.json')
    profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)),expected_header_sha256=HEADER)
    for name,record in (('trial-plan.json',plan),('capture-profile.json',profile),('expected-baseline.json',current),
                        ('storage-bound-345.json',bound),('storage-runtime-admission.json',budget)):
        path = BASE/name
        save(path,record)
        pins[str(path)] = sha(path)
    ready = dict(state='ready-frame345-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
                 install_plan_sha256=plan['install_plan_sha256'],image_sha256=plan['image_sha256'],
                 pin_count=len(pins), input_pins=pins,approval_pending=True,device_writes=0,boot_attempts=0)
    save(BASE/'ready.json',ready)
    return dict(ready_sha256=sha(BASE/'ready.json'),pin_count=len(pins),worst_case_bytes=bound['worst_case_bytes'],
                runtime_reserve=RESERVE)


def review():
    ready_path = BASE/'ready.json'
    ready = load(ready_path)
    plan_path = BASE/'trial-plan.json'
    plan = load(plan_path)
    require(not (BASE/'approval.json').exists() and not (BASE/'execution').exists() and
            ready['state']=='ready-frame345-one-shot' and plan==expected_plan() and
            ready['trial_plan_sha256']==sha(plan_path) and ready['pin_count']==len(ready['input_pins']) and
            plan['install_plan_sha256']==ready['install_plan_sha256'] and
            plan['image_sha256']==ready['image_sha256'],'frozen inputs or scope differ')
    criteria(plan)
    budget = load(BASE/'storage-runtime-admission.json')
    bound = load(BASE/'storage-bound-345.json')
    require(bound==storage(load(BASE/'expected-baseline.json')) and budget['admitted'] and
            budget['planned_batch_bytes']>=RESERVE and budget['current_accounted_bytes']+
            budget['planned_batch_bytes']<=budget['limit_bytes'],'frozen storage bound differs')
    for name,digest in ready['input_pins'].items():
        require(sha(name)==digest,'frozen input differs: '+name)
    result = dict(state='reviewed-frame345-one-shot',ready_sha256=sha(ready_path),
                  trial_plan_sha256=sha(plan_path), image_sha256=ready['image_sha256'],
                  install_plan_sha256=ready['install_plan_sha256'],no_device_mutation_during_preparation=True,
                  restore_precedes_analysis=True,device_writes=0,boot_attempts=0,pin_count=ready['pin_count'],
                  input_pins={str(path):sha(path) for path in (Path(__file__),DOC,WORK/'tools/run-frame345-trial.py')})
    save(BASE/'final-review.json',result)
    return {k:v for k,v in result.items() if k!='input_pins'}


if __name__=='__main__':
    stages = {task.__name__:task for task in (package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=stages)
    print(json.dumps(stages[parser.parse_args().stage](),indent=2))
