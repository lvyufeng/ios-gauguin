#!/usr/bin/env python3
"""Freeze the bounded 0374 native QuartzCore frame trace."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame373')
shared = parent.shared
save = shared.stage.save
TRIAL = '0374'
BASE = WORK/'research/tmp/frame-374'
P373 = MAIN/'research/tmp/gauguin-ca-transaction-worktree-20261121/research/tmp/frame-373'
REFERENCE = P373/'execution'
KDEBUG_SOURCE = (MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/.deps-cache/p0-20261105'
                /'source301-causal-trace/bsd/kern/kdebug.c')
BOARD_BUILD = (MAIN/'research/tmp/gauguin-ca-handoff-worktree-20261121/research/tmp/frame-372'
              /'native-kernel/build-manifest.json')
RETIREMENT = MAIN/'research/tmp/0374-storage-retirement/verified-retirement-manifest.json'
HOST = BASE/'host-verification.json'
PATCH = WORK/'xnu/patches/0285-gauguin-capture-native-ca-frame-events.patch'
DOC = WORK/'docs/gauguin-frame-374-trial-20261122.md'
HEADER = 'a384b7cbf73a8b294afbeb86113d702155abf2416bc812b0bd6405d69013af40'
LOG_BYTES = 196_390_596
BATCH = 288_000_000
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0373')],
         'allow_0374_one_60Hz_boot_and_scoped_native_CA_trace')
SUCCESS = '0374-native-CA-and-physical-frames-measured-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'], 'whole 0374 batch not admitted')


def check_reference():
    pins = {
        'result.json': '89b4df540d272c2f9942b955c91aa8546271d14cde625c9ae810ac09126d55d4',
        'independent-restore.json': 'fd05c43b6dc3ea385b90038b5ace846ed12b465e7b6f3b194124addb027f996b',
        'restored-capture/result.json': '9dfcc91d25acc9570a9c3475c6aeb3256f0ca12e3a45b6a0a61d87ef1c6e56fb',
        'frame-scanout-analysis.json': 'a3a37193ad8545835b8e89e0aef1b17987328b6b50100e5e49cdaea71d495569',
        'scoped-swap-timing-0373.json': 'da036aa78750ca5ae15c2c524570bbae2aac8bb238c9a23489de6dfa586b8196',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in pins.items()), '0373 immutable evidence differs')
    prior = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    frame = load(REFERENCE/'frame-scanout-analysis.json')
    require(prior['trial']=='0373' and prior['restored'] and prior['independent_restore_verified'] and
            prior['static_root_comparison_passed'] and all(prior['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and frame['misr']['qualified'] and
            frame['crc_frame_calibration']['qualified'] and not prior['stable_60_fps_observed'],
            '0373 comparison unqualified')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0374 TWRP baseline differs')
    return current


def build():
    check_budget()
    previous = P373/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0373',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_sources={'bsd/kern/kdebug.c': KDEBUG_SOURCE},
        extra_units=(('gauguin_ui_trace_board',BOARD_BUILD,'compile-gauguin_ui_trace_board'),
                     ('kdebug',BASE/'kdebug-origin/result.json','compile-kdebug')))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P373/'trial-plan.json')['boot_command'], '0374 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P373/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P373/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame374-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P373/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P373/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P373,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P373/'trial-plan.json'
    baseline = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame374-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0374-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'kdebug.o','gauguin_ui_trace_board.o'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0374 native change differs')
    require(image['command']==baseline['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==baseline['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==baseline['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==baseline['C4_sha256'] and
            installed['rows']['c4']['data_extents']==parent.parent.C4_EXTENTS and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==baseline['misc_before_sha256'],
            '0374 image, EDR or six-slot baseline differs')
    host = load(HOST)
    frame = baseline['frame_capture']
    sizes = {name:current['files'][name]['bytes'] for name in baseline['log_capture']['sizes']}
    require(sum(sizes.values())==LOG_BYTES and host['projected_ring_bound']<4_194_304 and
            frame['target_refresh_hz']==60 and frame['records']>19_593 and frame['modesets']==0 and
            frame['crc_preimage_reads']==2 and frame['crc_required_preimage']==0x01000000 and
            frame['maximum_volatile_crc_register_writes']==4 and frame['crc_cleanup_readback_equals_recorded_preimage'] and
            baseline['scripted_strokes']==13 and baseline['sustained_motion']['normal_reports']==162,
            '0374 presentation mode, CRC, input or capture budget differs')
    captures = dict(baseline['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
        max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=host['reference_raw_bytes'],
        reserved_frame_console_bytes=4_194_304-host['reference_raw_bytes'],
        previous_verified_suffix_bytes=LOG_BYTES-baseline['log_capture']['measured_baseline_bytes'])
    return dict(baseline,state='prepared-frame374-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=captures,
        display_retry=dict(baseline['display_retry'],held_pending_limit=4),
        producer_transport=dict(baseline['producer_transport'], armed=False),
        ca_handoff=dict(cache_build='20H392',producer_scheduling_changes=0),
        native_CA=dict(provider='QuartzCore userspace kdebug via the standard trace syscall',
            exact_receiver='backboardd', selected_debugids=['31ca000d','31ca000e','31ca0084',
                '31ca002c','31ca01e0','31ca0010','31ca0000','31ca0110'],
            window_seconds=45, boot_trace_subclass='0x31ca', boot_trace_ring_events=8192,
            compact_event_capacity=16384, compact_binary_limit=210000, host_proof_sha256=sha(HOST),
            extra_thread_suspensions=0, extra_GPU_calls=0, changes_presentation=False),
        optimization='Collect native CA target and actual times for exact swap IDs.',
        performance_comparison='Same 0373 Core, C4, scripts and 60 Hz route. Join CRC by hardware scan ordinal.')



def storage(plan):
    prior = load(P373/'storage-bound-373.json')
    parts = dict(prior['components'])
    parts.pop('unmatched_and_CA_summary')
    parts['native_CA_and_scan_alignment']=2_500_000
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0374 runtime exceeds reservation')
    return dict(prior,state='bounded0374-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P373,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0374 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0374-offline-verified' and host['patch_sha256']==sha(PATCH) and
            host['native_schema_verified'] and host['controls']>=9 and
            not (host['device_writes'] or host['device_boots']),
            '0374 native CA, collection or rollback proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P373,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame374-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json',
             'reused-immutable-artifacts.json')
    extra = [REFERENCE/'kernel-IO-analysis.json',REFERENCE/'scoped-swap-timing-0373.json',
             RETIREMENT,BASE/'kdebug-origin/result.json',BASE/'native-source-check.json',
             BASE/'instruments-preflight.json']
    return shared.pins(base=BASE,prior=P373,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[HOST,*(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P373,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
