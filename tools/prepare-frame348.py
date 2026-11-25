#!/usr/bin/env python3
"""Build, model and freeze the 0348 read-only scanout trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame348_scope import BASE, CORE_SHA, DOC, HEADER, MAIN, P346, P347, REFERENCES, RESERVE, WORK
from frame348_scope import expected_plan, load, require, sha


stage = import_module('prepare-frame344')
common = import_module('prepare-frame347')
PATCH_NAMES = ('0259-gauguin-readonly-scanout-counters.patch','0260-gauguin-readonly-counter-motion.patch')


def build():
    require(load(BASE/'build-storage-admission.json')['admitted'], 'whole 0348 build not admitted')
    command = import_module('build-frame347')
    command.link_scanout(P347/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0347',trial='0348',patches=tuple(WORK/'xnu/patches'/name for name in PATCH_NAMES))


def package():
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    native = load(manifest)
    require(native['state']=='0348-native-ARM64-linked' and native['inputs_unchanged'], 'unqualified kernel')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial='0348',frame_capture_mode=4)
    previous = load(P347/'trial-plan.json')['boot_command']
    require(image['command']==previous.replace('sweetfb_stats=3','sweetfb_stats=4') and
            len(image['command'].encode())==607, 'only the read-only mode token can change')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial='0348')
    record = P346/'core-native/result.json'
    core = load(record)
    binary = Path(core['binary'])
    require(sha(binary)==core['binary_sha256']==CORE_SHA and binary.stat().st_size==core['bytes']==7_992_224,
            'original signed 0346 Core differs')
    subprocess.run(['codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=60)
    (BASE/'core-native').mkdir()
    stage.save(BASE/'core-native/result.json',dict(state='0348-exact-0346-core-signed',binary=str(binary),
        bytes=core['bytes'],binary_sha256=CORE_SHA,signature_verified=True,compiled_tus=0,
        input_pins={str(record):sha(record),str(binary):CORE_SHA},device_commands=0))
    stage.save(BASE/'frame348-image.json',image)
    stage.save(BASE/'edr-native/result.json',edr)
    return dict(image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
                edr_sha256=edr['binary_sha256'],core_sha256=CORE_SHA)


def delta():
    core = load(BASE/'core-native/result.json')
    return stage.delta(BASE,P347,trial='0348',header=HEADER,baseline=BASE/'current-root-capture/result.json',
                       core_logical=core['bytes'])


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0348')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    return dict(common.storage(plan),state='bounded0348-runtime-batch')


def criteria(plan):
    previous = load(P347/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','owned_core_sha256','owned_core_logical_bytes','all_core_TUs_recompiled',
               'root_header_sha256','install_plan_sha256','misc_before_sha256','parent_trial_plan_sha256',
               'optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'changed an effect outside the reviewed 0348 set')
    frame = plan['frame_capture']
    require(frame['opt_in']=='sweetfb_stats=4' and frame['interface_mapping']=='read-only' and
            frame['stable_control_reads'] and frame['controls_observed']==[0,3] and
            frame['maximum_total_display_register_writes']==frame['maximum_volatile_counter_register_writes']==
            frame['maximum_volatile_crc_register_writes']==frame['modesets']==0 and
            frame['target_refresh_hz']==60 and not frame['crc_enabled'] and not frame['publish_new_content_fps'] and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'read-only display, scripted input or sampling scope differs')
    rollback = load(BASE/'restore-model/result.json')
    tests = load(BASE/'frame-host/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and len(rollback['checks'])==47 and
            rollback['all_restore_partial_write_points']==17 and rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            tests['baseline_exact_joins']=={'0346':730,'0347':721} and tests['unit_tests']>=28 and
            tests['control_models']==9 and tests['independent_readback_precedes_analysis'],
            'read-only pipeline or rollback qualification incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P347,HEADER,plan)


def pins():
    ready = P347/'ready.json'
    pinned = dict(load(ready)['input_pins'])
    files = [WORK/name for name in subprocess.check_output(
        ['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()]
    files += [ready,DOC,MAIN/'tools/storage-budget.py',P347/'trial-plan.json',
              P347/'execution/independent-restore.json',P347/'execution/restored-capture/result.json',
              P347/'execution/comparison-0346.json',P346/'storage-bound-346.json']
    files += [WORK/'xnu/patches'/name for name in ('series',*PATCH_NAMES)]
    files += [WORK/'tests'/name for name in ('fixtures/dpu345_status.c','fixtures/dpu346_counter.c','fixtures/dpu348_motion.c',
              'test_frame344_log.py','test_frame345_log.py','test_frame347_trial.py','test_frame348_trial.py',
              'test_core342_log.py')]
    for path,_ in REFERENCES.values():
        files += [path/name for name in ('result.json','kernel.log','kernel.log.bin','collection-analysis.json',
                  'frame-scanout-analysis.json','kernel-IO-identity-analysis.json',
                  'core-wait-execution-analysis.json','queue-identity-analysis.json')]
    receipts = ('native-kernel/build-manifest.json','core-native/result.json','edr-native/result.json',
                'frame348-image.json','frame-host/result.json','restore-model/result.json')
    for name in receipts:
        path = BASE/name
        files.append(path)
        receipt = load(path)
        for source,digest in receipt.get('input_pins',{}).items():
            require(pinned.setdefault(source,digest)==digest, 'conflicting pinned input: '+source)
        for key in ('binary','kernel','image'):
            if key in receipt:
                files.append(Path(receipt[key]))
    files += [BASE/name for name in ('current-root-capture/result.json','build-storage-admission.json',
                                    'frame-host/0346-0347-reference.json')]
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        files.extend(path for path in (BASE/folder).rglob('*') if path.is_file())
    for path in files:
        digest = sha(path)
        require(pinned.setdefault(str(path),digest)==digest, 'inherited pin changed: '+str(path))
    for name,digest in pinned.items():
        require(sha(name)==digest, 'pinned artifact changed: '+name)
    return pinned


def freeze():
    require(not any((BASE/name).exists() for name in ('trial-plan.json','ready.json','approval.json','execution',
                                                     'final-review.json','capture-profile.json')),
            '0348 already prepared or claimed')
    plan = expected_plan()
    criteria(plan)
    bound = storage(plan)
    pinned = pins()
    metadata = len(json.dumps(pinned,indent=2).encode())+1_048_576
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
        '--planned-bytes',str(RESERVE+metadata)],text=True,timeout=600))
    require(budget['admitted'], 'frozen metadata and complete runtime reservation unavailable')
    current = load(BASE/'current-root-capture/result.json')
    profile = load(P347/'capture-profile.json')
    profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=plan['log_capture']['max_combined_log_bytes'])
    for name,value in (('trial-plan.json',plan),('capture-profile.json',profile),('expected-baseline.json',current),
                       ('storage-bound-348.json',bound),('storage-runtime-admission.json',budget)):
        path = BASE/name
        stage.save(path,value)
        pinned[str(path)]=sha(path)
    ready = dict(state='ready-frame348-one-shot',trial_plan_sha256=sha(BASE/'trial-plan.json'),
                 install_plan_sha256=plan['install_plan_sha256'],image_sha256=plan['image_sha256'],
                 pin_count=len(pinned),input_pins=pinned,approval_pending=True,device_writes=0,boot_attempts=0)
    stage.save(BASE/'ready.json',ready)
    return dict(ready_sha256=sha(BASE/'ready.json'),pin_count=len(pinned),
                worst_case_bytes=bound['worst_case_bytes'],runtime_reserve=RESERVE)


def review():
    ready_path, plan_path = BASE/'ready.json', BASE/'trial-plan.json'
    ready,plan = load(ready_path),load(plan_path)
    require(not (BASE/'approval.json').exists() and not (BASE/'execution').exists() and
            ready['state']=='ready-frame348-one-shot' and plan==expected_plan() and
            ready['trial_plan_sha256']==sha(plan_path) and ready['pin_count']==len(ready['input_pins']) and
            ready['image_sha256']==plan['image_sha256'] and ready['install_plan_sha256']==plan['install_plan_sha256'],
            'frozen 0348 scope differs')
    criteria(plan)
    profile = load(BASE/'capture-profile.json')
    budget = load(BASE/'storage-runtime-admission.json')
    require(profile['max_combined_log_bytes']==plan['log_capture']['max_combined_log_bytes'] and
            load(BASE/'storage-bound-348.json')==storage(plan) and budget['admitted'] and
            budget['planned_batch_bytes']>=RESERVE and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            'frozen log profile or storage reservation differs')
    for name,digest in ready['input_pins'].items():
        require(sha(name)==digest, 'frozen input differs: '+name)
    report = dict(state='reviewed-frame348-one-shot',ready_sha256=sha(ready_path),trial_plan_sha256=sha(plan_path),
                  image_sha256=ready['image_sha256'],install_plan_sha256=ready['install_plan_sha256'],
                  no_device_mutation_during_preparation=True,restore_precedes_analysis=True,
                  device_writes=0,boot_attempts=0,pin_count=ready['pin_count'],
                  input_pins={str(path):sha(path) for path in (Path(__file__),DOC,WORK/'tools/run-frame348-trial.py')})
    stage.save(BASE/'final-review.json',report)
    return {key:value for key,value in report.items() if key!='input_pins'}


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    result = steps[parser.parse_args().step]()
    if result is not None:
        print(json.dumps(result,indent=2))
