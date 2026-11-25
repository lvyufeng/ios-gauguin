#!/usr/bin/env python3
"""Package, model, freeze and review the one-shot 0349 trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame349_scope import BASE, CORE_SHA, DOC, HEADER, MAIN, P346, P348, PATCH, REFERENCE, RESERVE, WORK
from frame349_scope import expected_plan, load, require, sha


stage = import_module('prepare-frame344')
common = import_module('prepare-frame347')


def build():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=490_000_000, 'whole 0349 batch not admitted')
    import_module('build-frame347').link_scanout(P348/'native-kernel/build-manifest.json',BASE/'native-kernel',
        parent_trial='0348',trial='0349',patches=(PATCH,))


def package(*, base=BASE, prior=P348, trial='0349', patch=PATCH, mode=5, signed_edr_reference=None):
    pack = import_module('package-frame344')
    manifest = base/'native-kernel/build-manifest.json'
    native = load(manifest)
    require(native['state']==trial+'-native-ARM64-linked' and native['inputs_unchanged'] and
            native['input_pins'][str(patch)]==sha(patch), 'unqualified kernel')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=base,trial=trial,frame_capture_mode=mode)
    previous = load(prior/'trial-plan.json')['boot_command']
    require(image['command']==previous.replace(f'sweetfb_stats={mode-1}',f'sweetfb_stats={mode}') and
            len(image['command'].encode())==607, 'only the mode token may change')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=base,trial=trial,signed_reference=signed_edr_reference)
    original = P346/'core-native/result.json'
    core = load(original)
    binary = Path(core['binary'])
    require(sha(binary)==core['binary_sha256']==CORE_SHA and binary.stat().st_size==core['bytes']==7_992_224,
            'original signed 0346 Core differs')
    subprocess.run(['codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=60)
    (base/'core-native').mkdir()
    stage.save(base/'core-native/result.json',dict(state=trial+'-exact-0346-core-signed',binary=str(binary),
        bytes=core['bytes'],binary_sha256=CORE_SHA,signature_verified=True,compiled_tus=0,
        input_pins={str(original):sha(original),str(binary):CORE_SHA},device_commands=0))
    stage.save(base/f'frame{int(trial)}-image.json',image)
    stage.save(base/'edr-native/result.json',edr)
    return dict(image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
                edr_sha256=edr['binary_sha256'],core_sha256=CORE_SHA)


def delta():
    return stage.delta(BASE,P348,trial='0349',header=HEADER,baseline=BASE/'current-root-capture/result.json',
                       core_logical=7_992_224)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0349')
    return {key:value for key,value in result.items() if key!='input_pins'}


def storage(plan):
    return dict(common.storage(plan),state='bounded0349-runtime-batch')


def criteria(plan):
    previous = load(P348/'trial-plan.json')
    allowed = {'state','trial','image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
               'EDR_helper_sha256','root_header_sha256','install_plan_sha256','misc_before_sha256',
               'parent_trial_plan_sha256','optimization','performance_comparison','log_capture','frame_capture'}
    require({key for key in plan.keys()|previous.keys() if plan.get(key)!=previous.get(key)}<=allowed,
            'change outside the 0349 effect set')
    frame = plan['frame_capture']
    require(frame['opt_in']=='sweetfb_stats=5' and frame['controls_observed']==[0] and
            frame['volatile_crc_register_address']=='0x0ae6b980' and
            frame['read_only_crc_signature_address']=='0x0ae6b984' and
            frame['maximum_total_display_register_writes']==frame['maximum_volatile_crc_register_writes']==4 and
            frame['maximum_volatile_counter_register_writes']==frame['modesets']==frame['crc_retries']==0 and
            frame['target_refresh_hz']==60 and frame['crc_polls_per_pair']==2 and
            frame['crc_setup_attempts']==frame['crc_cleanup_attempts']==1 and
            frame['crc_blank_lines']==[2752,4480] and frame['crc_sample_rows_max']==3000 and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            'MISR, counter, display mode, input or sampling scope differs')
    model = load(BASE/'restore-model/result.json')
    host = load(BASE/'frame-host/result.json')
    require(model['all_model_IO_writes_memory_only'] and len(model['checks'])==47 and
            model['all_restore_partial_write_points']==17 and model['maximum_actual_model_restore_bytes']<=10_330_112 and
            host['reference_vblank_intervals']==[270,181] and host['reference_script_joins']==728 and
            host['crc_replay_phases']==[0,1] and host['unit_tests']>=10 and host['control_models']==9 and
            host['independent_readback_precedes_analysis'], 'insufficient CRC, vblank or rollback qualification')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P348,HEADER,plan)


def pins(*, base=BASE, prior=P348, doc=DOC, patch=PATCH, reference=REFERENCE, trial='0349', extra=(),
         replaced_historical_paths=(), artifacts=None):
    parent = prior/'ready.json'
    pinned = dict(load(parent)['input_pins'])
    for name in replaced_historical_paths:
        require(pinned.pop(str(name),None) is not None, 'unknown historical toolchain pin: '+str(name))
    files = [WORK/name for name in subprocess.check_output(
        ['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()]
    files += [parent,doc,patch,WORK/'xnu/patches/series',MAIN/'tools/storage-budget.py',
              prior/'trial-plan.json',prior/f'storage-bound-{int(trial)-1}.json']
    files += [reference/name for name in ('result.json','independent-restore.json','restored-capture/result.json',
              'collection-analysis.json','kernel.log','kernel.log.bin','frame-scanout-analysis.json',
              'kernel-IO-identity-analysis.json','core-wait-execution-analysis.json','queue-identity-analysis.json')]
    if artifacts is None:
        artifacts = tuple(base/name for name in (
            'native-kernel/build-manifest.json',f'frame{int(trial)}-image.json','edr-native/result.json',
            'core-native/result.json','frame-host/result.json','restore-model/result.json'))
    for path in artifacts:
        files.append(path)
        receipt = load(path)
        for source,digest in receipt.get('input_pins',{}).items():
            require(pinned.setdefault(source,digest)==digest, 'conflicting pinned input: '+source)
        for key in ('binary','kernel','image'):
            if key in receipt:
                files.append(Path(receipt[key]))
    files += [base/name for name in ('current-root-capture/result.json','build-storage-admission.json')]
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        files.extend(path for path in (base/folder).rglob('*') if path.is_file())
    files.extend(extra)
    for file in files:
        digest = sha(file)
        require(pinned.setdefault(str(file),digest)==digest, 'inherited pin changed: '+str(file))
    for name,digest in pinned.items():
        require(sha(name)==digest, 'pinned artifact changed: '+name)
    return pinned


def freeze(*, base=BASE, prior=P348, expected=expected_plan, validate=criteria,
           storage_bound=storage, pin_inputs=pins, reserve=RESERVE):
    require(not any((base/name).exists() for name in ('trial-plan.json','ready.json','approval.json','execution',
                                                     'final-review.json','capture-profile.json')), 'trial already frozen or claimed')
    plan = expected()
    trial = int(plan['trial'])
    validate(plan)
    bound = storage_bound(plan)
    pinned = pin_inputs()
    metadata = len(json.dumps(pinned,indent=2).encode())+1_048_576
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
        '--planned-bytes',str(reserve+metadata)],text=True,timeout=600))
    require(budget['admitted'], 'frozen metadata and complete later runtime reservation unavailable')
    current = load(base/'current-root-capture/result.json')
    profile = load(prior/'capture-profile.json')
    profile.update(out=str((base/'execution/fresh-before').relative_to(MAIN)),
                   expected_header_sha256=plan['root_header_sha256'],
                   max_combined_log_bytes=plan['log_capture']['max_combined_log_bytes'])
    for name,value in (('trial-plan.json',plan),('capture-profile.json',profile),('expected-baseline.json',current),
                       (f'storage-bound-{trial}.json',bound),('storage-runtime-admission.json',budget)):
        path = base/name
        stage.save(path,value)
        pinned[str(path)]=sha(path)
    ready = dict(state=f'ready-frame{trial}-one-shot',trial_plan_sha256=sha(base/'trial-plan.json'),
                 install_plan_sha256=plan['install_plan_sha256'],image_sha256=plan['image_sha256'],
                 pin_count=len(pinned),input_pins=pinned,approval_pending=True,device_writes=0,boot_attempts=0)
    stage.save(base/'ready.json',ready)
    return dict(ready_sha256=sha(base/'ready.json'),pin_count=len(pinned),
                worst_case_bytes=bound['worst_case_bytes'],runtime_reserve=reserve)


def review(*, base=BASE, doc=DOC, expected=expected_plan, validate=criteria,
           storage_bound=storage, preparer=Path(__file__), reserve=RESERVE):
    ready_path, plan_path = base/'ready.json',base/'trial-plan.json'
    ready,plan = load(ready_path),load(plan_path)
    trial = int(plan['trial'])
    require(not any((base/name).exists() for name in ('approval.json','execution')) and
            ready['state']==f'ready-frame{trial}-one-shot' and plan==expected() and
            ready['trial_plan_sha256']==sha(plan_path) and ready['pin_count']==len(ready['input_pins']) and
            ready['image_sha256']==plan['image_sha256'] and ready['install_plan_sha256']==plan['install_plan_sha256'],
            'frozen trial scope differs')
    validate(plan)
    profile = load(base/'capture-profile.json')
    budget = load(base/'storage-runtime-admission.json')
    require(profile['max_combined_log_bytes']==plan['log_capture']['max_combined_log_bytes'] and
            load(base/f'storage-bound-{trial}.json')==storage_bound(plan) and budget['admitted'] and
            budget['planned_batch_bytes']>=reserve and
            budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
            'frozen capture or storage budget differs')
    for name,digest in ready['input_pins'].items():
        require(sha(name)==digest, 'frozen input differs: '+name)
    report = dict(state=f'reviewed-frame{trial}-one-shot',ready_sha256=sha(ready_path),trial_plan_sha256=sha(plan_path),
                  image_sha256=ready['image_sha256'],install_plan_sha256=ready['install_plan_sha256'],
                  no_device_mutation_during_preparation=True,restore_precedes_analysis=True,
                  device_writes=0,boot_attempts=0,pin_count=ready['pin_count'],
                  input_pins={str(path):sha(path) for path in (preparer,doc,WORK/f'tools/run-frame{trial}-trial.py')})
    stage.save(base/'final-review.json',report)
    return {key:value for key,value in report.items() if key!='input_pins'}


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    result = steps[parser.parse_args().step]()
    if result is not None:
        print(json.dumps(result,indent=2))
