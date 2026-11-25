#!/usr/bin/env python3
"""Freeze a single 0388 hardware comparison at 60 Hz."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from core342_slots import data_extents
from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

pacing = import_module('prepare-frame384')
shared, save = pacing.shared, pacing.save
TRIAL = '0388'
BASE = WORK/'research/tmp/frame-388'
P384 = MAIN/'research/tmp/gauguin-early-stage-worktree-20261123/research/tmp/frame-384'
P387 = MAIN/'research/tmp/gauguin-frame387-manual-touch-worktree-20261123/research/tmp/frame-387'
LAST = P387/'execution'
REFERENCE = P384/'execution'
COMPARISON = REFERENCE/'scanout-comparison-0380-0381-0384.json'
MOTION_ANALYZER = MAIN/'research/tmp/gauguin-frame385-ca-transaction-worktree-20261123/tools/frame385_motion.py'
HEADER = 'cdf08fb80a02556ef178c1e94f979fb206d99114bb1a2741a4e1b60045dff9fe'
LOG_BYTES = 244_848_681
BATCH = 316_000_000
RESERVE = 206_000_000
CONSOLE_RECEIPTS_MAX = 8192
DOC = WORK/'docs/gauguin-frame-388-hardware-trial-20261123.md'
SHIM = pacing.parent.P382/'shim-native/Image'
NATIVE = BASE/'native-kernel-final/build-manifest.json'
IMAGE = BASE/'frame388-image.json'
HOST = BASE/'offline-final.json'
PATCHES = tuple(WORK/'xnu/patches'/name for name in (
    '0299-gauguin-dispatch-ca-by-dpu-deadline.patch',
    '0300-gauguin-record-dpu-dispatch-independently.patch'))
FLAGS = (*[flag for flag in pacing.FLAGS if not flag.startswith('allow_0384')],
         'allow_0388_one_60Hz_temporary_boot_with_default_DPU_deadline_dispatch')
SUCCESS = '0388-DPU-dispatch-and-visible-frames-measured-root-restored'


def admitted():
    receipt = load(BASE/'live-batch-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes'] == BATCH and
            receipt['current_accounted_bytes'] + BATCH <= receipt['limit_bytes'],
            'complete 0388 preparation and runtime batch is not admitted')


def baseline():
    terminal, proof = LAST/'result.json', LAST/'independent-restore.json'
    require(sha(terminal) == '6c8ac5cb9a1bdd930e4d6c188eb47be2264c73d2b9cac45b4cdacfebe420e854' and
            sha(proof) == '4153dbea69df4db42cb302ff46bc0f121a1d1609032e248f9ac0c0c793db9086',
            '0387 independent recovery archive differs')
    restored, readback = load(terminal), load(proof)
    require(restored['restored'] and restored['independent_restore_verified'] and
            restored['static_root_comparison_passed'] and readback['journal_empty'] and
            readback['misc_original_4096_bytes_match'] and readback['root_header_sha256'] == HEADER,
            '0387 restoration evidence is incomplete')
    original = load(LAST/'restored-capture/result.json')
    fresh = load(BASE/'current-root-capture/result.json')
    require(not fresh['device_writes'] and len(fresh['files']) == 31 and
            fresh['root_header_sha256'] == HEADER and fresh['combined_log_bytes'] == LOG_BYTES and
            all(fresh[key] == original[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
            'live TWRP baseline differs from independently restored 0387')
    return fresh


def capture():
    admitted()
    baseline()
    subprocess.run([sys.executable, str(WORK/'tools/capture-sb-cadence-slot.py'), '--baseline',
        str(LAST/'restored-capture/result.json'), '--out', str(BASE/'slot-capture'),
        '--reuse-data-from', str(P387/'slot-capture')], check=True, capture_output=True, timeout=300)
    metadata = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot', HEADER,
        trial=TRIAL, maximum_compressed_bytes=28_000_000)
    return {key: metadata[key] for key in ('compressed_bytes','device_writes','device_boots')}


def package():
    admitted()
    pack = import_module('package-frame344')
    require(sha(SHIM) == load(SHIM.parent/'result.json')['binary_sha256'], 'private scanout shim differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'), load(NATIVE), base=BASE, trial=TRIAL,
        frame_capture_mode=9, scripted_motion=True, private_scanout_shim=SHIM)
    parent = load(P384/'trial-plan.json')
    before, after = (pack.parts(Path(path).read_bytes()) for path in (parent['image'], image['image']))
    require(before[1] == after[1] and before[3] == after[3] and image['command'] == parent['boot_command'] and
            42_000_000 < image['image_bytes'] < 44_000_000, '0388 wrapper, DTB or command differs')
    image['kernel_manifest'] = str(NATIVE)
    save(BASE/'edr-native/result.json', pack.edr(image, base=BASE, trial=TRIAL,
        signed_reference=P384/'edr-native/result.json'))
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P384/(name+'-native')/'result.json', BASE/(name+'-native')/'result.json')
    save(IMAGE, image)
    return {key: image[key] for key in ('image_sha256','image_bytes')}


def delta():
    baseline()
    return shared.stage.delta(BASE, P384, trial=TRIAL, header=HEADER,
        baseline=LAST/'restored-capture/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE, BASE/'restore-model', trial=TRIAL)
    return dict(checks=len(proof['checks']), partial_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    parent_file = P384/'trial-plan.json'
    parent = load(parent_file)
    native, image, edr, host = (load(path) for path in (NATIVE, IMAGE, BASE/'edr-native/result.json', HOST))
    slots = BASE/'slot-delta/install-plan.json'
    install = load(slots)
    old_slots = load(P384/'slot-delta/install-plan.json')
    require(native['state'] == '0388-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and all(native['input_pins'][str(patch)] == sha(patch) for patch in PATCHES) and
            {Path(path).stem for path in native['object_replacements']} == {'SweetFramebuffer','gauguin_ui_trace_board'}
            and native['identity'] == image['build_identity'] == edr['kernel_identity'] and
            sha(native['kernel']) == native['kernel_sha256'] == image['kernel_sha256'] == host['native_kernel_sha256'] and
            host['state'] == '0388-Android-display-port-offline-verified' and not host['device_commands'],
            '0388 scheduler link or offline proof differs')
    require(sha(image['image']) == image['image_sha256'] and image['command'] == parent['boot_command'] and
            not any(word.startswith('sweet_ca_work_us=') for word in image['command'].split()) and
            edr['identity_only_retarget'] and sha(edr['binary']) == edr['binary_sha256'] == install['admission_sha256'] and
            install['core_sha256'] == parent['owned_core_sha256'] and install['changed_ranges'] == 12 and
            install['trial'] == TRIAL and install['root_header_sha256'] == HEADER and
            all(data_extents(row) == data_extents(old_slots['rows'][name]) for name,row in install['rows'].items()) and
            sha(BASE/'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            '0388 image, deadline budget or reversible file effects differ')
    sizes = {path:live['files'][path]['bytes'] for path in parent['log_capture']['sizes']}
    with (REFERENCE/'kernel.log.bin').open('rb') as ring:
        magic, version, capacity, used, _ = struct.unpack('<8sIIQQ', ring.read(32))
    require(sum(sizes.values()) == LOG_BYTES and (magic, version, capacity, used) ==
            (b'SWEETLOG', 1, 4_194_304, 4_046_997) and used + CONSOLE_RECEIPTS_MAX < capacity and
            parent['frame_capture']['target_refresh_hz'] == 60 and parent['frame_capture']['modesets'] == 0 and
            parent['frame_capture']['crc_required_preimage'] == 0x01000000 and
            parent['frame_capture']['crc_cleanup_readback_equals_recorded_preimage'] and
            (parent['scripted_strokes'], parent['scripted_reports'], parent['sustained_motion']['normal_reports']) ==
            (13, 442, 162), '0384 comparison, CRC or input limits differ')
    return dict(parent, state='prepared-frame388-one-shot', trial=TRIAL, root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(parent_file), install_plan_sha256=sha(slots),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        kernel_identity=native['identity'], kernel_banner=native['kernel_banner'], EDR_helper_sha256=edr['binary_sha256'],
        storage_reserve_bytes=RESERVE, log_capture=dict(parent['log_capture'], sizes=sizes,
            measured_baseline_bytes=LOG_BYTES, max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,
            reference_kernel_log_bytes=used, reserved_frame_console_bytes=capacity-used,
            previous_verified_suffix_bytes=LOG_BYTES-load(P387/'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        deadline_dispatch=dict(default_lead_ticks=76800, ready_cutoff_from_DPU=True, sample_cap=24,
            extra_console_max_bytes=CONSOLE_RECEIPTS_MAX, host_proof_sha256=sha(HOST)),
        optimization='Dispatch CA by the predicted DPU target scan and track the ready deadline.',
        performance_comparison='Pair 0384 and 0388 scan ordinals for the 13 swipes and fixed drag.')


def storage(plan):
    previous = load(P384/'storage-bound-384.json')
    components = dict(previous['components'], deadline_and_motion_report=2_000_000)
    worst = sum(components.values())
    require(worst <= RESERVE and plan['log_capture']['measured_baseline_bytes'] == LOG_BYTES,
            '0388 runtime reserve does not cover all result files')
    return dict(previous, state='bounded0388-deadline-comparison-runtime', components=components,
        worst_case_bytes=worst, reserve_bytes=RESERVE, fresh_log_bytes=LOG_BYTES, log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    admitted()
    parent = load(P384/'trial-plan.json')
    adjustable = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256',
        'image','image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256',
        'storage_reserve_bytes','log_capture','deadline_dispatch','optimization','performance_comparison'}
    require({key for key in parent.keys() | plan.keys() if plan.get(key) != parent.get(key)} <= adjustable,
            '0388 changes an effect outside the approved 60 Hz comparison')
    old, new = (load(folder/'slot-delta/install-plan.json') for folder in (P384,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'}, '0388 userspace differs beyond the kernel identity binding')
    rollback = load(BASE/'restore-model/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges'] == 12 and
            len(rollback['checks']) == 49 and rollback['all_restore_partial_write_points'] == 17 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')] == plan['install_plan_sha256'],
            '0388 rollback proof is incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE, P384, HEADER, plan)


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'], cwd=WORK, text=True).splitlines()
    files = [*(WORK/name for name in scripts), DOC, *PATCHES, WORK/'xnu/patches/series', MAIN/'tools/storage-budget.py',
        P384/'ready.json', P384/'trial-plan.json', P384/'capture-profile.json', P384/'storage-bound-384.json',
        BASE/'live-batch-admission.json', BASE/'live-retirement/verified-retirement-manifest.json',
        BASE/'current-root-capture/result.json', HOST, SHIM, SHIM.parent/'result.json', MOTION_ANALYZER, COMPARISON,
        *(LAST/name for name in ('result.json','independent-restore.json','restored-capture/result.json')),
        *(REFERENCE/name for name in ('result.json','independent-restore.json','kernel.log','kernel.log.bin',
                                     'springboard-new.log','page-flip-latches.json')),
        Path(load(P384/'trial-plan.json')['observer_helper'])]
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        files.extend(path for path in (BASE/folder).rglob('*') if path.is_file())
    checked = {str(path):sha(path) for path in files}
    for artifact in (NATIVE, IMAGE, *(BASE/name for name in ('edr-native/result.json','c4-native/result.json',
            'core-native/result.json','restore-model/result.json'))):
        checked[str(artifact)] = sha(artifact)
        receipt = load(artifact)
        for name, digest in receipt.get('input_pins', {}).items():
            require(sha(name) == digest and checked.setdefault(name,digest) == digest, '0388 input changed: '+name)
        for key in ('kernel','image','binary'):
            if key in receipt:
                checked[receipt[key]] = sha(receipt[key])
    return checked


def freeze():
    return shared.freeze(base=BASE, prior=P384, expected=expected_plan, validate=criteria, storage_bound=storage,
        pin_inputs=pins, reserve=RESERVE)


def review():
    return shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria,
        storage_bound=storage, preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {call.__name__:call for call in (capture,package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=actions)
    print(json.dumps(actions[parser.parse_args().step](), indent=2))
