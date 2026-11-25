#!/usr/bin/env python3
"""Freeze the bounded 0373 display receipt and CA replay trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame372')
shared = parent.shared
save = shared.stage.save
TRIAL = '0373'
BASE = WORK/'research/tmp/frame-373'
P372 = MAIN/'research/tmp/gauguin-ca-handoff-worktree-20261121/research/tmp/frame-372'
REFERENCE = P372/'execution'
COMPARISON = P372/'supplemental-0372'
HOST = BASE/'host-verification.json'
PATCH = WORK/'xnu/patches/0284-gauguin-describe-unmatched-display-receipts.patch'
DOC = WORK/'docs/gauguin-frame-373-trial-20261121.md'
HEADER = '70a395fbc63817591f16d3c1a54d7e04f9660f6d0af3966ccc8c71d2f9244411'
LOG_BYTES = 192_404_495
BATCH = 278_000_000
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0372')],
         'allow_0373_one_60Hz_boot_and_unmatched_receipt_metadata')
SUCCESS = '0373-vblank-CRC-unmatched-receipts-measured-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'], 'whole 0373 batch not admitted')


def check_reference():
    pins = {
        REFERENCE/'result.json': '306ca4f01b1b3baab83eca7abf320f6872788a9b2e9d5c7b3b60e51895b1ee93',
        REFERENCE/'independent-restore.json': '6ac8ae760b39859d03742860398117264bb38b526e1184ca25a258b909fb3bb0',
        REFERENCE/'restored-capture/result.json': '5b778c3c9908f64c264565d3602922e613c8f24e600ea1242aa818d2e111a7c7',
        COMPARISON/'audit-result.json': '423f1b3bec9a38c2b83caa9f34df2ec3faaa65f8b2d695b5b2576d4e9adb7d1c',
        COMPARISON/'frame-scanout-analysis.json': 'd2e316766c7e8666835f3fc3fa45da3d89beb2f85e30b14f7694be8d8cf7c54e',
        COMPARISON/'scoped-swap-timing-0372.json': 'f937711bf6699a42233ab2c9e1ddd2b3251f692e7d93c4d5df1e357e401a2a5c',
    }
    require(all(sha(path)==digest for path,digest in pins.items()), '0372 immutable evidence differs')
    prior = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    audit = load(COMPARISON/'audit-result.json')
    require(prior['trial']=='0372' and prior['restored'] and prior['independent_restore_verified'] and
            prior['static_root_comparison_passed'] and all(prior['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and audit['crc_control']['qualified'] and
            audit['crc_latch']['qualified'] and not audit['stable_60_fps_observed'], '0372 comparison unqualified')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0373 TWRP baseline differs')
    return current


def build():
    check_budget()
    previous = P372/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0372',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=(('ipc_kmsg',previous,'compile-ipc_kmsg'),))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P372/'trial-plan.json')['boot_command'], '0373 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P372/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P372/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame373-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P372/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P372/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P372,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P372/'trial-plan.json'
    baseline = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame373-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0373-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'ipc_kmsg.o'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0373 native change differs')
    require(image['command']==baseline['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==baseline['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==baseline['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==baseline['C4_sha256'] and
            installed['rows']['c4']['data_extents']==parent.C4_EXTENTS and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==baseline['misc_before_sha256'],
            '0373 image, EDR or six-slot baseline differs')
    host = load(HOST)
    frame = baseline['frame_capture']
    sizes = {name:current['files'][name]['bytes'] for name in baseline['log_capture']['sizes']}
    require(sum(sizes.values())==LOG_BYTES and host['projected_ring_bound']<4_194_304 and
            frame['target_refresh_hz']==60 and frame['records']>19_593 and frame['modesets']==0 and
            frame['crc_preimage_reads']==2 and frame['crc_required_preimage']==0x01000000 and
            frame['maximum_volatile_crc_register_writes']==4 and frame['crc_cleanup_readback_equals_recorded_preimage'] and
            baseline['scripted_strokes']==13 and baseline['sustained_motion']['normal_reports']==162,
            '0373 presentation mode, CRC, input or capture budget differs')
    captures = dict(baseline['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
        max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=host['reference_raw_bytes'],
        reserved_frame_console_bytes=4_194_304-host['reference_raw_bytes'],
        previous_verified_suffix_bytes=LOG_BYTES-baseline['log_capture']['measured_baseline_bytes'])
    return dict(baseline,state='prepared-frame373-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=captures,
        display_retry=dict(baseline['display_retry'],held_pending_limit=4),
        producer_transport=dict(baseline['producer_transport'],unmatched_details_max=64,
            unmatched_detail_fields=['bounded_receive_ordinal','take_tick','receiving_thread','message_id',
                                     'no_match_reason','copyout_tick_if_observed','copyout_status_if_observed']),
        ca_handoff=dict(coalescing_model_sha256=sha(HOST),cache_build='20H392',
                        exact_seed_provider_verified=False,producer_scheduling_changes=0),
        optimization='Qualify four-slot accounting, unmatched metadata and offline CA coalescing.',
        performance_comparison='Same 0372 Core, C4, scripts and 60 Hz route. Compare CRC by physical scan ordinal.')


def storage(plan):
    prior = load(P372/'storage-bound-372.json')
    parts = dict(prior['components'],unmatched_and_CA_summary=250_000)
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0373 runtime exceeds reservation')
    return dict(prior,state='bounded0373-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P372,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0373 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0373-offline-verified' and host['patch_sha256']==sha(PATCH) and
            host['held_snapshots']==71 and host['coalescing_verified'] and
            not host['exact_seed_provider_verified'] and not (host['device_writes'] or host['device_boots']),
            '0373 offline coalescing, collection or rollback proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P372,HEADER,plan)


def pins():
    # The 0372 frame score is a separately qualified read-only audit.
    view = BASE/'reference-0372'
    view.mkdir(exist_ok=True)
    for name in ('result.json','independent-restore.json','restored-capture/result.json','collection-analysis.json',
                 'kernel.log','kernel.log.bin','kernel-IO-identity-analysis.json','core-wait-execution-analysis.json',
                 'queue-identity-analysis.json','frame-scanout-analysis.json'):
        link = view/name
        link.parent.mkdir(parents=True,exist_ok=True)
        target = (COMPARISON if name=='frame-scanout-analysis.json' else REFERENCE)/name
        if link.is_symlink():
            require(link.readlink()==target, '0372 comparison projection differs')
        else:
            link.symlink_to(target)
    names = ('native-kernel/build-manifest.json','frame373-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json')
    extra = [REFERENCE/'kernel-IO-analysis.json',COMPARISON/'audit-result.json',COMPARISON/'scoped-swap-timing-0372.json']
    extra += list((BASE/'retired-builds').glob('*'))
    return shared.pins(base=BASE,prior=P372,doc=DOC,patch=PATCH,reference=view,trial=TRIAL,extra=extra,
                       artifacts=[HOST,*(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P372,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
