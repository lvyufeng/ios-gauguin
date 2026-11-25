#!/usr/bin/env python3
"""Freeze the 0384 back-buffer staging trial against the restored 0383 state."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from core342_slots import data_extents
from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame383')
shared, save = parent.shared, parent.save
TRIAL = '0384'
BASE = WORK/'research/tmp/frame-384'
P383 = MAIN/'research/tmp/gauguin-iokit-scanout-worktree-20261123/research/tmp/frame-383'
REFERENCE = P383/'execution'
HEADER = '1bea8bfbbb53e571c40f9bda1478a0b59980c2bff7d36eb7671b3a36bb141e73'
LOG_BYTES = 232_664_428
BATCH = 360_000_000
PATCH = WORK/'xnu/patches/0295-gauguin-stage-ready-frames-before-blanking.patch'
DOC = WORK/'docs/gauguin-frame-384-early-staging-20261123.md'
HOST = BASE/'host-verification.json'
RETIREMENT = MAIN/'research/tmp/0384-storage-retirement/verified-retirement-manifest.json'
COMPARISON = REFERENCE/'scanout-comparison-0380-0381-0383.json'
SUCCESS = '0384-early-staging-and-visible-frames-verified-root-restored'
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0383')],
         'allow_0384_one_60Hz_boot_and_bounded_private_early_staging')


def check_budget():
    receipt = load(BASE/'build-storage-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes']==BATCH and
            receipt['current_accounted_bytes']+BATCH<=receipt['limit_bytes'], 'whole 0384 batch was not admitted')


def baseline():
    pins = {
        REFERENCE/'result.json':'b43ae3b73ff81e583459a78ca276756b60b1c99eebfec26959098f0c63627017',
        REFERENCE/'independent-restore.json':'5299144fb8931fd041828c34d5bdd4e522adf415934f25397d9ff8c56260980b',
        REFERENCE/'page-flip-latches.json':'4525cda3fe04fa0027551062e64780feb3a1c6d4fef18039c28d173354dfa76c',
        COMPARISON:'95e5f8056061e1eb4c16df959a94636f580895bb73a1bc8bb38b792e7cb891e7',
    }
    require(all(sha(path)==digest for path,digest in pins.items()), '0383 measurement or restore evidence differs')
    result = load(REFERENCE/'result.json')
    original = load(REFERENCE/'restored-capture/result.json')
    proof = load(REFERENCE/'independent-restore.json')
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            result['dpu_new_content_FPS_qualified'] and result['latched_frames']==760 and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES, 'unqualified 0383 baseline')
    return original


def current_baseline():
    saved = baseline()
    fresh = load(BASE/'current-root-capture/result.json')
    require(len(fresh['files'])==31 and not fresh['device_writes'] and
            all(fresh[k]==saved[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')),
            'fresh TWRP baseline differs from verified 0383')
    return fresh


def build():
    check_budget()
    donor = P383/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(donor,BASE/'native-kernel',
        parent_trial='0383',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=(('SweetFramebuffer',donor,'compile-SweetFramebuffer'),),
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))


def capture():
    check_budget()
    baseline()
    profile = load(P383/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    current_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P383/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def package():
    check_budget()
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    shim = parent.P382/'shim-native/Image'
    require(sha(shim)==load(shim.parent/'result.json')['binary_sha256'], 'private scanout shim differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(manifest),base=BASE,trial=TRIAL,
                           frame_capture_mode=9,scripted_motion=True,private_scanout_shim=shim)
    old = load(P383/'trial-plan.json')
    before = pack.parts(Path(old['image']).read_bytes())
    after = pack.parts(Path(image['image']).read_bytes())
    require(before[1]==after[1] and before[3]==after[3] and image['command']==old['boot_command'] and
            42_000_000<image['image_bytes']<44_000_000, '0384 shim, boot arguments or DTB differ')
    image['kernel_manifest'] = str(manifest)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P383/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P383/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame384-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def delta():
    current_baseline()
    return shared.stage.delta(BASE,P383,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = current_baseline()
    previous = load(P383/'trial-plan.json')
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame384-image.json',
                                                     'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    install = load(slots)
    previous_slots = load(P383/'slot-delta/install-plan.json')
    require(native['state']=='0384-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).stem for p in (*native['object_replacements'],*native['object_replacements'].values())}==
            {'SweetFramebuffer'} and sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0384 framebuffer-only build differs')
    require(sha(image['image'])==image['image_sha256'] and image['command']==previous['boot_command'] and
            install['changed_ranges']==12 and install['trial']==TRIAL and edr['identity_only_retarget'] and
            install['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and
            install['core_sha256']==previous['owned_core_sha256'] and
            all(data_extents(row)==data_extents(previous_slots['rows'][name])
                for name,row in install['rows'].items()) and
            sha(BASE/'metadata-snapshot/misc-original.bin')==previous['misc_before_sha256'],
            '0384 image, EDR or six-slot layout differs')
    sizes = {name:current['files'][name]['bytes'] for name in previous['log_capture']['sizes']}
    with (REFERENCE/'kernel.log.bin').open('rb') as ring:
        _,_,capacity,used,_ = struct.unpack('<8sIIQQ',ring.read(32))
    frame = previous['frame_capture']
    require(sum(sizes.values())==LOG_BYTES and capacity==4_194_304 and used==4_059_208 and
            frame['target_refresh_hz']==60 and frame['modesets']==0 and
            frame['crc_required_preimage']==0x01000000 and frame['crc_preimage_reads']==2 and
            frame['crc_cleanup_readback_equals_recorded_preimage'] and
            previous['scripted_strokes']==13 and previous['sustained_motion']['normal_reports']==162,
            '0384 timing, CRC, input or measured log reserve differs')
    return dict(previous,state='prepared-frame384-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(P383/'trial-plan.json'),install_plan_sha256=sha(slots),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        frame_capture=dict(frame,presentation_policy=dict(frame['presentation_policy'],
            maximum_attempts_per_hardware_frame=None,maximum_copies_per_hardware_frame=None,
            maximum_private_full_copy_attempts=1024,
            private_copy_admission='exact ready generation and owned idle back buffer',
            checked_before_copy='exact GPU read lease and full copy geometry, no scan-position gate for staging',
            original_blanking_copy_budget_ns=5_500_000)),
        log_capture=dict(previous['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=used,
            reserved_frame_console_bytes=capacity-used,
            previous_verified_suffix_bytes=LOG_BYTES-previous['log_capture']['measured_baseline_bytes']),
        early_staging=dict(maximum_private_copy_attempts=1024,full_copy_bytes=10_368_000,
            separate_from_CA_timer_workloop=True,exact_GPU_visibility_and_read_lease=True,
            private_slots_reserved_until_latch=True,timeout_retains_both=True,host_proof_sha256=sha(HOST)),
        optimization='Stage the exact GPU-ready frame on a separate workloop in the free private scanout buffer.',
        performance_comparison='0383 and 0384 by gesture and physical scan ordinal. Audit the first changed scan separately.')


def storage(plan):
    old = load(P383/'storage-bound-383.json')
    parts = dict(old['components'],early_stage_and_first_frame_audit=2_000_000)
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0384 runtime exceeds reservation')
    return dict(old,state='bounded0384-early-stage-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old = load(P383/'trial-plan.json')
    adjustable = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256',
                  'image','image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256',
                  'frame_capture','log_capture','early_staging','optimization','performance_comparison'}
    require({key for key in old.keys()|plan.keys() if plan.get(key)!=old.get(key)}<=adjustable and
            plan['display_dma']==old['display_dma'] and
            {key for key in plan['frame_capture'] if plan['frame_capture'][key]!=old['frame_capture'][key]}==
            {'presentation_policy'}, '0384 changed the hardware or CRC budget')
    before,after = (load(path/'slot-delta/install-plan.json') for path in (P383,BASE))
    require({name for name,row in after['rows'].items() if
             row['new_file_sha256']!=before['rows'][name]['new_file_sha256']}=={'admission'},
            '0384 changed userspace beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(host['state']=='0384-offline-stage-verified' and host['patch_sha256']==sha(PATCH) and
            host['unchanged_GPU_and_DPU'] and host['exact_lease_before_copy'] and
            host['output_barrier_before_stage_publication'] and host['sanitizer_state_machine'] and
            host['reference_replay']['earlier_stage_candidates'] and host['original_latch_fixtures']==7 and
            not host['device_commands'] and rollback['all_model_IO_writes_memory_only'] and
            rollback['install_ranges']==12 and rollback['all_restore_partial_write_points']==17 and
            len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'],
            '0384 stage or recovery proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P383,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame384-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json','host-verification.json')
    extra = [COMPARISON,REFERENCE/'page-flip-latches.json',REFERENCE/'springboard-new.log',
             RETIREMENT,RETIREMENT.parent/'build-admission.json',parent.P382/'shim-native/Image',
             parent.P382/'shim-native/result.json']
    extra.extend(Path(row['archive']) for row in load(RETIREMENT)['rows'])
    # 0383 used a scanout-specific comparison instead of the older generic export.
    return shared.pins(base=BASE,prior=P383,doc=DOC,patch=PATCH,reference=parent.parent.REFERENCE,
                       trial=TRIAL,extra=[*extra,*[REFERENCE/name for name in ('result.json',
                           'independent-restore.json','restored-capture/result.json','kernel.log','kernel.log.bin')]],
                       artifacts=[BASE/name for name in names])


def freeze():
    return shared.freeze(base=BASE,prior=P383,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
