#!/usr/bin/env python3
"""Build and freeze the bounded 0380 DPU-clock trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame379')
shared = parent.shared
save = shared.stage.save
TRIAL = '0380'
BASE = WORK/'research/tmp/frame-380'
P375 = parent.P375
P379 = MAIN/'research/tmp/gauguin-frame-379-worktree-20261122/research/tmp/frame-379'
REFERENCE = P379/'execution'
COMPARISON = REFERENCE/'scanout-comparison-0375-0379.json'
RETIREMENT = MAIN/'research/tmp/0380-storage-retirement/verified-retirement-manifest.json'
HOST = BASE/'host-verification.json'
PATCH = WORK/'xnu/patches/0291-gauguin-align-ca-notify-to-dpu-vblank.patch'
DOC = WORK/'docs/gauguin-frame-380-trial-20261122.md'
HEADER = 'b77064ff79732dbe5d729ea108f15639fd0e6bf3fc294f6bfaa6d0681f92337d'
LOG_BYTES = 220_471_034
BATCH = 335_000_000
UNITS = ('kdebug','SweetFramebuffer','gauguin_ui_trace_board')
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0379')],
         'allow_0380_one_60Hz_boot_with_dpu_aligned_CA_notifications')
SUCCESS = '0380-aligned-CA-and-physical-scanout-measured-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'], 'whole 0380 batch not admitted')


def check_reference():
    pins = {
        'result.json': '0063d8b90989c9138353782c1fc929c776383602640845d5cdec6ce6956511f2',
        'independent-restore.json': 'b20781a9573a7fc0e7bb511adc98f77936aa546fd35d0658995cfe7cc1dc1212',
        'restored-capture/result.json': '84fae82f14534b3dc0e8671d21b0fce81e1d481f7001025e47d3f47a786af439',
        'kernel.log': 'a22ba7a487a4d4c938ed208e422c74e87e65aba81217904b4c663a1f6776687c',
        'frame-scanout-analysis.json': 'd8b74ae153e302622f73f1ff2aff6badee8d2e2ac9ac2a51a335a474c488ad97',
        'scanout-comparison-0375-0379.json': 'c508039d2eff4cbafae8faed97d42697a4ac6f9868d0b65878e84c0767a0fa2e',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in pins.items()), '0379 immutable evidence differs')
    parent.check_reference()
    prior,proof,original = (load(REFERENCE/name) for name in
        ('result.json','independent-restore.json','restored-capture/result.json'))
    comparison = load(COMPARISON)
    require(prior['trial']=='0379' and prior['restored'] and prior['independent_restore_verified'] and
            prior['static_root_comparison_passed'] and all(prior['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and comparison['crc_register']['qualified'] and
            comparison['crc_calibration']['qualified'] and comparison['ring']['qualified'] and
            not comparison['stable_60_fps_observed'], '0379 comparison or restored baseline differs')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0380 TWRP baseline differs')
    return current


def build():
    check_budget()
    previous = P379/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0379',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=tuple((name,previous,'compile-'+name) for name in UNITS))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
                           frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P379/'trial-plan.json')['boot_command'], '0380 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P379/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P379/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame380-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P379/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P379/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P379,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P379/'trial-plan.json'
    previous = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame380-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0380-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).stem for p in (*native['object_replacements'],*native['object_replacements'].values())}==set(UNITS) and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0380 native change differs')
    require(image['command']==previous['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==previous['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==previous['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==previous['C4_sha256'] and
            installed['rows']['c4']['data_extents']==load(P379/'slot-delta/install-plan.json')['rows']['c4']['data_extents'] and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==previous['misc_before_sha256'],
            '0380 image, EDR or six-slot scope differs')
    host = load(HOST)
    sizes = {name:current['files'][name]['bytes'] for name in previous['log_capture']['sizes']}
    frame = previous['frame_capture']
    require(sum(sizes.values())==LOG_BYTES and host['projected_ring_bound']<4_194_304 and
            frame['target_refresh_hz']==60 and frame['modesets']==0 and frame['crc_preimage_reads']==2 and
            frame['crc_required_preimage']==0x01000000 and frame['maximum_volatile_crc_register_writes']==4 and
            frame['crc_cleanup_readback_equals_recorded_preimage'] and previous['scripted_strokes']==13 and
            previous['sustained_motion']['normal_reports']==162, '0380 CRC, input or capture scope differs')
    return dict(previous,state='prepared-frame380-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(previous['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=host['reference_raw_bytes'],
            reserved_frame_console_bytes=4_194_304-host['reference_raw_bytes'],
            previous_verified_suffix_bytes=LOG_BYTES-previous['log_capture']['measured_baseline_bytes']),
        contention_deferral=dict(absolute_maximum=0),native_CA=dict(previous['native_CA'],host_proof_sha256=sha(HOST)),
        ca_phase=dict(history=20,absolute_timebase=[625,12],lead_ns=4_000_000,minimum_notice_spacing_ns=12_000_000,
            maximum_sample_age_ns=40_000_000,maximum_bracket_ns=3_000_000,
            fallback_after_missed_callback_ns=40_000_000,
            consecutive_misses_disable_alignment=3,
            maximum_schedule_ahead_ns=24_000_000,source='existing qualified read-only INTF1 scan edge brackets',
            timer='notification-only on the original display workloop',notification_timestamp='actual callback time',
            missing_or_late_prediction='preserve original software notification fallback without duplicate bursts',
            maximum_sample_rows=24,additional_mmio_reads=0,additional_mmio_writes=0,
            frame_selection='0375 guarded copy and retained ownership',host_verification_sha256=sha(HOST)),
        optimization='Phase-lock compatibility vsync notification to measured scanout and wake four ms ahead.',
        performance_comparison='Compare 0375 and 0379 by gesture, phase and scan ordinal. Split onset from motion.')


def storage(plan):
    previous = load(P379/'storage-bound-379.json')
    parts = dict(previous['components'])
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0380 runtime exceeds reservation')
    return dict(previous,state='bounded0380-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    previous = load(P379/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'contention_deferral','native_CA','ca_phase','optimization','performance_comparison'}
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=allowed,
            '0380 changed an effect outside its scope')
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P379,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0380 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0380-offline-verified' and host['patch_sha256']==sha(PATCH) and
            host['controls']>=12 and host['original_0375_take_verified'] and host['replay']['early_pulses']>=2600 and
            not (host['device_writes'] or host['device_boots']), '0380 host timing or restore proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P379,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame380-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json')
    extra = [COMPARISON,P375/'partial-audit-0375.json',P375/'execution/frame-scanout-analysis.json',
             P375/'native-kernel/source/iokit/Kernel/arm/SweetFramebuffer.cpp',
             REFERENCE/'kernel-IO-analysis.json',RETIREMENT]
    extra += [Path(row['archive']) for row in load(RETIREMENT)['rows']]
    return shared.pins(base=BASE,prior=P379,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[HOST,*(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P379,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
