#!/usr/bin/env python3
"""Stage the 0362 control, qualify rollback and freeze all authorized effects."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame362_scope import (BASE, CONTROL, CORE_BYTES, DOC, HEADER, LOG_SUFFIX, MAIN, METADATA_CAP, MOTION, P357, P360,
    P361, PATCH, REF361, REFERENCE, RESERVE, SAVED_SLOTS, WORK, check_baseline, check_budget,
    expected_plan, load, require, sha, signed_pair)

shared = import_module('prepare-frame349')
save = shared.stage.save


def build():
    check_budget()
    previous = P360/'native-kernel/build-manifest.json'
    touch = P357/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0360',trial='0362',patches=(PATCH,),recompile_scanout=False,
        extra_units=(('sweet_touch',touch,'compile-sweet_touch'),))
    result = load(BASE/'native-kernel/build-manifest.json')
    return {key:result[key] for key in ('state','identity','kernel_bytes','kernel_sha256','object_replacements')}


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = load(BASE/'native-kernel/build-manifest.json')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial='0362',
                            frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P361/'trial-plan.json')['boot_command'].replace('swp=3','swp=4'),
            'only the scripted-motion selector may change')
    image['kernel_manifest'] = str(BASE/'native-kernel/build-manifest.json')
    edr = pack.edr(image,base=BASE,trial='0362',signed_reference=P360/'edr-native/result.json')
    save(BASE/'edr-native/result.json',edr)
    receipt,pair = signed_pair(P361)
    core = pair['variants']['reference']
    subprocess.run(['codesign','--verify','--strict',core['binary']],check=True,capture_output=True,timeout=60)
    (BASE/'core-native').mkdir()
    save(BASE/'core-native/result.json',dict(state='0362-exact-SDK27.2-unmodified-Core-signed',
        binary=core['binary'],binary_sha256=CONTROL,bytes=CORE_BYTES,sdk='27.2',signature_verified=True,
        input_pins={str(receipt):sha(receipt)},device_commands=0))
    save(BASE/'frame362-image.json',image)
    return dict(image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
                unmodified_control_sha256=CONTROL,EDR_only_identity_changed=edr['identity_only_retarget'])


def capture():
    check_budget()
    current = check_baseline()
    slots = BASE/'slot-capture'
    if not slots.exists():
        subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
            '--baseline',str(REFERENCE),'--out',str(slots),'--reuse-data-from',str(SAVED_SLOTS)],
            check=True,capture_output=True,timeout=300)
    snapshot = BASE/'metadata-snapshot'
    meta = (load(snapshot/'result.json') if snapshot.exists() else
        import_module('capture-core342-metadata').capture(snapshot,HEADER,trial='0362',
            maximum_compressed_bytes=METADATA_CAP))
    require(meta['root_header_sha256']==HEADER and meta['compressed_bytes']<=METADATA_CAP and
            not (meta['device_writes'] or meta['device_boots']), '0362 read-only metadata differs')
    return dict(files=len(current['files']),metadata_bytes=meta['compressed_bytes'],
                log_bytes=current['combined_log_bytes'],device_writes=0)


def delta():
    check_budget()
    return shared.stage.delta(BASE,P361,trial='0362',header=HEADER,baseline=REFERENCE,core_logical=CORE_BYTES)


def model():
    check_budget()
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial='0362')
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'],
                maximum_actual_model_restore_bytes=result['maximum_actual_model_restore_bytes'],device_writes=0)


def storage(plan):
    previous = load(P361/'storage-bound-361.json')
    components = dict(previous['components'])
    components['verified_log_suffixes'] += LOG_SUFFIX-8_000_000
    components['SDK_and_motion_comparison'] = import_module('run-frame362-trial').REPORT_BYTES
    measured = plan['log_capture']['measured_baseline_bytes']
    total = sum(components.values())
    require(previous['new_log_data_stored_once'] and total==186_106_272 and total<=RESERVE and
            plan['log_capture']['max_combined_log_bytes']==measured+LOG_SUFFIX,
            '0362 runtime output exceeds whole-batch reserve')
    return dict(previous,state='bounded0362-runtime-batch',components=components,
                worst_case_bytes=total,reserve_bytes=RESERVE,fresh_log_bytes=measured,
                log_cap_bytes=measured+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    original = load(P361/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','install_plan_sha256','parent_trial_plan_sha256',
        'image','image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner',
        'EDR_helper_sha256','owned_core_sha256','owned_core_logical_bytes','new_kernel_builds','new_boot_images',
        'storage_reserve_bytes','optimization','performance_comparison','matched_Core_control',
        'log_capture','sustained_motion'}
    require({key for key in original.keys()|plan.keys() if original.get(key)!=plan.get(key)}<=allowed and
            plan['frame_capture']==original['frame_capture'] and plan['sustained_motion']==MOTION and
            plan['scripted_strokes']==13 and plan['scripted_reports']==442 and
            plan['main_thread_sampling']['max_samples']==64 and plan['process_sampling']['max_register_samples']==1024,
            '0362 adds an effect outside the separate motion and SDK control')
    host,rollback,slots,metadata = (load(BASE/name) for name in ('frame-host/result.json',
        'restore-model/result.json','slot-capture/result.json','metadata-snapshot/result.json'))
    source = BASE/'native-kernel/source/bsd/dev/sweet_touch.c'
    replay = host['replay']
    require(host['state']=='0362-host-candidate-and-restored-replay-qualified' and
            host['kernel_motion']['source_sha256']==sha(source) and host['kernel_motion']['cases']==5 and
            replay['control_models']==9 and replay['scored_original_strokes']==13 and
            replay['archived_stationary_motion_fixture_not_qualified'] and
            replay['reference_copy_cadence']==50.291612304367135 and replay['reference_no_swap_scans']==64 and
            replay['reference_open_callback']==40 and rollback['all_model_IO_writes_memory_only'] and
            len(rollback['checks'])==47 and rollback['all_restore_partial_write_points']==17 and
            rollback['maximum_actual_model_restore_bytes']<=10_330_112 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            slots['baseline_sha256']==sha(REFERENCE) and len(slots['reused_original_data'])==6 and
            metadata['root_header_sha256']==HEADER and metadata['compressed_bytes']<=METADATA_CAP and
            not any(receipt['device_writes'] or receipt['device_boots'] for receipt in (slots,metadata)),
            '0362 motion, restored replay or rollback proof is incomplete')
    for name, archived in slots['reused_original_data'].items():
        expected = SAVED_SLOTS/(name+'-old-data.bin')
        require(Path(archived)==expected and (BASE/'slot-capture'/expected.name).resolve()==expected,
                '0362 original slot archive differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P361,HEADER,plan)


def pins():
    cleanup = MAIN/'research/tmp/0362-storage-retirement'
    evidence = [WORK/'tests/fixtures/motion362.c',P361/'slot-delta/install-plan.json',
        REF361/'frame-pacing-0360-0361.json',REF361/'driver-copy-rate-comparison.json',
        REF361/'springboard-new.log',REF361/'kernel-IO-analysis.json',
        cleanup/'verified-retirement-manifest.json',cleanup/'retirement-complete.json']
    evidence.extend(Path(path) for path in load(BASE/'slot-capture/result.json')['reused_original_data'].values())
    return shared.pins(base=BASE,prior=P361,doc=DOC,patch=PATCH,reference=REF361,trial='0362',extra=evidence)


def freeze():
    return shared.freeze(base=BASE,prior=P361,expected=expected_plan,validate=criteria,
                        storage_bound=storage,pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,
                        storage_bound=storage,preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
