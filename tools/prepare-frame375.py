#!/usr/bin/env python3
"""Freeze the bounded 0375 native CA timing and frame receipt trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame374')
shared = parent.shared
save = shared.stage.save
TRIAL = '0375'
BASE = WORK/'research/tmp/frame-375'
P374 = MAIN/'research/tmp/gauguin-native-ca-trace-worktree-20261122/research/tmp/frame-374'
REFERENCE = P374/'execution'
PROVIDER = MAIN/'research/tmp/0375-provider'
FRAMEBUFFER_BUILD = (MAIN/'research/tmp/gauguin-producer-handoff-worktree-20261121/research/tmp/frame-371'
                     /'native-kernel/build-manifest.json')
RETIREMENT = MAIN/'research/tmp/0375-storage-retirement/verified-retirement-manifest.json'
HOST = BASE/'host-verification.json'
PATCH = WORK/'xnu/patches/0286-gauguin-deliver-scanned-frame-info.patch'
DOC = WORK/'docs/gauguin-frame-375-trial-20261122.md'
HEADER = '007acea28a56c898e9363d03cab9a6e00d6f4991933d10614ffc27cdaab9c131'
LOG_BYTES = 200_416_317
BATCH = 283_000_000
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0374')],
         'allow_0375_one_60Hz_boot_and_bounded_native_frame_info')
SUCCESS = '0375-native-CA-handoff-and-frame-info-measured-root-restored'


def check_budget():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==BATCH and
            admission['current_accounted_bytes']+BATCH<=admission['limit_bytes'], 'whole 0375 batch not admitted')


def check_reference():
    pins = {
        'result.json': 'e5dc1a22c99a20c413ced429cbcdbfcd144d8436eb544d886931353621e22bbd',
        'independent-restore.json': '1d686934a064a4ea3e8d8ee1e91913a171b72263715a881ed91db9f55a0a545a',
        'restored-capture/result.json': 'c385090c918c8b58c57b50b8f7aa5e9506b72321f071bf745b4a6760e2272510',
        'frame-scanout-analysis.json': 'a8ed4e250173ba1614c4436301474a5674097fdd94ae37e830ac9fd69143535c',
        'scoped-swap-timing-0374.json': 'e043a318337c7e180037692f33962c9942c473772f9a0d2603ed36d28883da78',
        'native-render-cutoffs-0374.json': 'b5e25fef4db242dc403fc46b32ab87a42d50dc720df03e130f4b327ff6c49e19',
        'native-CA-scan-alignment-0374.json': 'b20323d2352dd88ce7fa9472271d68354dd526e72b60afb3a8a970fa6fd160d6',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in pins.items()), '0374 immutable evidence differs')
    prior = load(REFERENCE/'result.json')
    proof = load(REFERENCE/'independent-restore.json')
    original = load(REFERENCE/'restored-capture/result.json')
    frame = load(REFERENCE/'frame-scanout-analysis.json')
    require(prior['trial']=='0374' and prior['restored'] and prior['independent_restore_verified'] and
            prior['static_root_comparison_passed'] and all(prior['other_log_prefix_preserved'].values()) and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES and frame['misr']['qualified'] and
            frame['crc_frame_calibration']['qualified'] and not prior['stable_60_fps_observed'],
            '0374 comparison unqualified')
    return original


def check_baseline():
    original = check_reference()
    current = load(BASE/'current-root-capture/result.json')
    require(all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')) and
            len(current['files'])==31 and not current['device_writes'], '0375 TWRP baseline differs')
    return current


def build():
    check_budget()
    previous = P374/'native-kernel/build-manifest.json'
    return import_module('build-frame347').link_scanout(previous,BASE/'native-kernel',
        parent_trial='0374',trial=TRIAL,patches=(PATCH,),recompile_scanout=False,
        extra_units=(('gauguin_ui_trace_board',previous,'compile-gauguin_ui_trace_board'),
                     ('kdebug',previous,'compile-kdebug'),
                     ('SweetFramebuffer',FRAMEBUFFER_BUILD,'compile-SweetFramebuffer')))


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True)
    require(image['command']==load(P374/'trial-plan.json')['boot_command'], '0375 boot arguments differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P374/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P374/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame375-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def capture():
    check_budget()
    check_reference()
    profile = load(P374/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    check_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P374/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def delta():
    check_baseline()
    return shared.stage.delta(BASE,P374,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = check_baseline()
    prior = P374/'trial-plan.json'
    baseline = load(prior)
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame375-image.json',
                                                    'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0375-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).name for p in (*native['object_replacements'],*native['object_replacements'].values())}=={'kdebug.o','gauguin_ui_trace_board.o','SweetFramebuffer.o'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], '0375 native change differs')
    require(image['command']==baseline['boot_command'] and sha(image['image'])==image['image_sha256'] and
            image['image_bytes']==Path(image['image']).stat().st_size and installed['trial']==TRIAL and
            installed['changed_ranges']==12 and installed['core_sha256']==baseline['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==baseline['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==baseline['C4_sha256'] and
            installed['rows']['c4']['data_extents']==parent.parent.parent.C4_EXTENTS and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==baseline['misc_before_sha256'],
            '0375 image, EDR or six-slot baseline differs')
    host = load(HOST)
    frame = baseline['frame_capture']
    sizes = {name:current['files'][name]['bytes'] for name in baseline['log_capture']['sizes']}
    require(sum(sizes.values())==LOG_BYTES and host['projected_ring_bound']<4_194_304 and
            frame['target_refresh_hz']==60 and frame['records']>19_593 and frame['modesets']==0 and
            frame['crc_preimage_reads']==2 and frame['crc_required_preimage']==0x01000000 and
            frame['maximum_volatile_crc_register_writes']==4 and frame['crc_cleanup_readback_equals_recorded_preimage'] and
            baseline['scripted_strokes']==13 and baseline['sustained_motion']['normal_reports']==162,
            '0375 presentation mode, CRC, input or capture budget differs')
    captures = dict(baseline['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
        max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=host['reference_raw_bytes'],
        reserved_frame_console_bytes=4_194_304-host['reference_raw_bytes'],
        previous_verified_suffix_bytes=LOG_BYTES-baseline['log_capture']['measured_baseline_bytes'])
    return dict(baseline,state='prepared-frame375-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(prior),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],log_capture=captures,
        display_retry=dict(baseline['display_retry'],held_pending_limit=4),
        producer_transport=dict(baseline['producer_transport'], armed=False),
        ca_handoff=dict(cache_build='20H392',source='SpringBoard',receiver='backboardd',
            encode_debugids=['31ca01dd','31ca01de'],server_debugids=['31ca0219','31ca0104'],
            source_and_server_markers_share_transaction_id=False,producer_scheduling_changes=0),
        native_CA=dict(provider='QuartzCore userspace kdebug via the standard trace syscall',
            exact_receiver='backboardd', selected_debugids=['31ca000d','31ca000e','31ca0084',
                '31ca002c','31ca01e0','31ca0010','31ca0000','31ca0110'],
            window_seconds=45, boot_trace_subclass='0x31ca', boot_trace_ring_events=8192,
            compact_event_capacity=16384, compact_binary_limit=210000, host_proof_sha256=sha(HOST),
            extra_thread_suspensions=0, extra_GPU_calls=0),
        frame_info_provider=dict(type=3,selectors=[72,73,74],target_tag=1,target_offset=0,
            keys=['Presentation_time','Requested_presentation'],owner='backboardd',
            serialized_on_display_workloop=True,maximum_sends=1024,maximum_pending_receipts=8,
            maximum_edge_width_ns=4_000_000,requested_timestamp_max_separation_ns=2_000_000_000,
            drop_unqualified_or_expired_receipts=True,maximum_wait_ns=100_000_000,
            actual_tick='upper bound of next exact paired hardware edge after a full guarded copy',
            path_changes='Bounded native FrameInfo feedback. Display scheduling and buffer admission stay in the existing path.',
            additional_persistent_device_writes=0),
        optimization='Separate source encoding and native rendering in the input delay. Deliver qualified frame feedback.',
        performance_comparison='Same 0374 Core, C4, scripts and 60 Hz route. Join targets and CRC using exact swap and scan IDs.')



def storage(plan):
    prior = load(P374/'storage-bound-374.json')
    parts = dict(prior['components'])
    parts['native_CA_and_scan_alignment']=4_000_000
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0375 runtime exceeds reservation')
    return dict(prior,state='bounded0375-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P374,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0375 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'] and
            host['state']=='0375-offline-verified' and host['patch_sha256']==sha(PATCH) and
            host['native_schema_verified'] and host['controls']>=28 and
            host['reference_cutoffs']==dict(before_render=28,render_before_SwapBegin=3) and
            not (host['device_writes'] or host['device_boots']),
            '0375 native CA, collection or rollback proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P374,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame375-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json',
             'reused-immutable-artifacts.json')
    extra = [REFERENCE/'kernel-IO-analysis.json',REFERENCE/'scoped-swap-timing-0374.json',
             RETIREMENT,BASE/'provider-source-check.json',
             BASE/'instruments-preflight.json']
    extra += [Path(row['archive']) for row in load(RETIREMENT)['rows']]
    return shared.pins(base=BASE,prior=P374,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[HOST,*(BASE/name for name in names)])


def freeze():
    return shared.freeze(base=BASE,prior=P374,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (build,package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=steps)
    print(json.dumps(steps[cli.parse_args().step](),indent=2))
