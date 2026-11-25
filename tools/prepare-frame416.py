#!/usr/bin/env python3
"""Prepare a single 60 Hz physical-touch preview with the bounded display drain."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


build = import_module('build-frame416')
prior = import_module('prepare-frame415')
capture_tools, batch_tools = prior.capture_tools, prior.prior.prior
shared, save, RESERVE = prior.shared, prior.save, prior.RESERVE
BASE, KERNEL, PATCH = build.BASE, build.MANIFEST, build.PATCH
P415 = MAIN / 'research/tmp/gauguin-shared-scanout-aperture-worktree-20261124/research/tmp/frame-415'
LAST = P415 / 'execution'
TRIAL = '0416'
IMAGE = BASE / 'frame416-image.json'
HOST = BASE / 'display-drain-host.json'
DOC = WORK / 'docs/gauguin-frame-416-display-drain-20261124.md'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0415')],
         'allow_0416_one_bounded_60Hz_physical_touch_with_confirmed_display_drain')
SUCCESS = '0416-display-drain-verified-root-restored'


def baseline(*, fresh=True):
    end_path = LAST / 'result.json'
    proof_path = LAST / 'independent-restore.json'
    end, proof, restored = map(load, (end_path, proof_path, LAST / 'restored-capture/result.json'))
    require(sha(end_path) == '2769fe19661719ad4cdf8bc64fd2019cc4a80d20cfd74b2de55a1323e68f54a4'
            and sha(proof_path) == '58417ad34a0a73f16d3d9cfa094ce88eb662d7f5c1728fdae1d92940538071d4'
            and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match']
            and proof['root_header_sha256'] == restored['root_header_sha256'],
            '0415 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256', 'combined_log_bytes', 'files', 'directories')),
            '0416 live recovery root differs from the 0415 readback')
    return current


def native():
    kernel = load(KERNEL)
    require(kernel['state'] == '0416-native-ARM64-linked' and kernel['inputs_unchanged']
            and kernel['baseline_reproduced_except_uuid'] and sha(kernel['kernel']) == kernel['kernel_sha256']
            and kernel['input_pins'][str(PATCH)] == sha(PATCH)
            and kernel['input_pins'][str(build.PARENT)] == sha(build.PARENT)
            and {Path(path).stem for path in kernel['object_replacements'].values()} == build.UNITS,
            '0416 is not the exact two-object display overlay')
    return kernel


def retarget_helper(pack, image, parent, *, base=BASE, reference=P415 / 'edr-native/result.json', trial=TRIAL):
    donor = load(reference)
    binary = Path(donor['binary'])
    require(sha(binary) == donor['binary_sha256'] == parent['EDR_helper_sha256']
            and donor['sampler_profile'] == 0, '0415 manual helper differs')
    target = base / 'edr-native' / binary.name
    target.parent.mkdir()
    projected, signature = pack.retarget_edr_identity(
        binary.read_bytes(), donor['kernel_identity'].encode(), image['build_identity'].encode())
    target.write_bytes(projected)
    subprocess.run(['codesign', '--force', '--sign', '-', str(target)], check=True, timeout=60)
    for path in (binary, target):
        subprocess.run(['codesign', '--verify', '--strict', str(path)], check=True, timeout=60)
    require(target.stat().st_size == donor['binary_bytes']
            and target.read_bytes()[:signature] == projected[:signature],
            'signed manual helper changed beyond the identity and signature')
    return dict(state=f'{trial}-manual-EDR-signed-offline', binary=str(target), binary_sha256=sha(target),
                binary_bytes=target.stat().st_size, kernel_identity=image['build_identity'], sampler_profile=0,
                identity_only_retarget=True, device_commands=0,
                input_pins={str(path): sha(path) for path in (reference, binary)})


def package():
    batch_tools.budget(BASE / 'build-storage-admission.json', build.BATCH)
    baseline(fresh=False)
    parent, kernel = load(P415 / 'trial-plan.json'), native()
    pack = import_module('package-frame344')
    shim = load(prior.prior.SHIM)
    require(sha(shim['binary']) == shim['binary_sha256'], '0415 reserved scanout shim differs')
    image = pack.boot_image(load(pack.P343 / 'runtime343-image.json'), kernel, base=BASE, trial=TRIAL,
        frame_capture_mode=9, scripted_motion=True, private_scanout_shim=Path(shim['binary']),
        private_scanout_slot_bytes=prior.SLOT_BYTES,
        command_profile=lambda command: prior.manual_command(capture_tools.command_profile(command)))
    old, new = (pack.parts(Path(row['image']).read_bytes()) for row in (parent, image))
    require(old[0][:16] == new[0][:16] and old[0][20:] == new[0][20:] and old[1] == new[1]
            and old[3] == new[3] and image['command'] == parent['boot_command'], '0416 boot profile differs')
    image['kernel_manifest'] = str(KERNEL)
    save(IMAGE, image)
    save(BASE / 'edr-native/result.json', retarget_helper(pack, image, parent))
    for kind in ('core', 'c4'):
        name = f'{kind}-native/result.json'
        (BASE / name).parent.mkdir()
        shutil.copyfile(P415 / name, BASE / name)
    return {key: image[key] for key in ('image_sha256', 'image_bytes', 'build_identity')}


def capture():
    batch_tools.budget(BASE / 'live-batch-admission.json', prior.BATCH)
    result = capture_tools.capture_from(BASE, P415, TRIAL, baseline)
    prior.capture_resources(current=baseline(), resources=RESOURCES)
    return result


def delta():
    return shared.stage.delta(BASE, P415, trial=TRIAL, header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json', core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE, BASE / 'restore-model', trial=TRIAL, resources=RESOURCES)
    return dict(checks=len(proof['checks']), failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), native()
    parent_path = P415 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    helper_path = BASE / 'edr-native/result.json'
    parent, image, install, helper = map(load, (parent_path, IMAGE, install_path, helper_path))
    header, size = (current[key] for key in ('root_header_sha256', 'combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest'] == str(KERNEL) and kernel['kernel_sha256'] == image['kernel_sha256']
            and sha(image['image']) == image['image_sha256']
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['command'] == parent['boot_command'] and helper['identity_only_retarget']
            and sha(helper['binary']) == helper['binary_sha256'] == install['admission_sha256']
            and install['core_sha256'] == parent['owned_core_sha256'] and install['C4_sha256'] == parent['C4_sha256']
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256']
            and frame['target_refresh_hz'] == 60 and frame['modesets'] == 0 and frame['crc_required_preimage'] == 0x01000000
            and parent['user_input'] == 'physical-Novatek-touch-only' and parent['scripted_strokes'] == 0,
            '0416 package, baseline or device effects differ')
    return dict(parent, state='prepared-frame416-physical-touch', trial=TRIAL, root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'], kernel_banner=kernel['kernel_banner'],
        EDR_helper_sha256=helper['binary_sha256'], signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'], measured_baseline_bytes=size, max_combined_log_bytes=size + LOG_SUFFIX,
            sizes={name: current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size - parent['log_capture']['measured_baseline_bytes']),
        display_drain=dict(private_copy_limit=1024, trace_limit=20_480, original_front_requests_max=1,
            maximum_extra_polls=160, maximum_extra_ms=180, additional_MMIO_writes_max=0,
            waits_for_pending_latch_and_GPU_lease=True, keep_ownership_on_uncertainty=True),
        optimization='Return to the inherited front when the copy budget or display capture ends.',
        performance_comparison='Confirm 60 Hz scan, original latch, CRC readback and continued display updates.')


def criteria(plan):
    batch_tools.budget(BASE / 'build-storage-admission.json', build.BATCH)
    batch_tools.budget(BASE / 'live-batch-admission.json', prior.BATCH)
    parent = load(P415 / 'trial-plan.json')
    allowed = {'state', 'trial', 'root_header_sha256', 'parent_trial_plan_sha256', 'install_plan_sha256',
               'image', 'image_sha256', 'image_bytes', 'kernel_identity', 'kernel_banner', 'EDR_helper_sha256',
               'signed_native_EDR_scope_sha256', 'log_capture', 'display_drain', 'optimization', 'performance_comparison'}
    require({key for key in parent.keys() | plan.keys() if plan.get(key) != parent.get(key)} <= allowed,
            '0416 changes exceed the reviewed scope')
    old, new = (load(path / 'slot-delta/install-plan.json') for path in (P415, BASE))
    require({name for name, row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'}, '0416 userspace differs beyond the identity-bound helper')
    host = load(HOST)
    require(host['kernel_sha256'] == load(KERNEL)['kernel_sha256'] and host['patch_sha256'] == sha(PATCH)
            and host['framebuffer_cases'] >= 8 and host['scan_worker_cases'] >= 5 and host['device_commands'] == 0,
            '0416 display drain host proof differs')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17, '0416 restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE, P415, plan['root_header_sha256'], plan)


def storage(plan):
    old = load(P415 / 'storage-bound-415.json')
    components = dict(old['components'], display_drain_receipts=65_536)
    total = sum(components.values())
    require(total <= RESERVE, '0416 outputs exceed the reserved runtime batch')
    return dict(old, state='bounded0416-display-drain-runtime', components=components, worst_case_bytes=total,
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'], log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git', 'ls-files', 'tools/*.py', 'tools/*.sh'], cwd=WORK, text=True).splitlines()
    parent = load(P415 / 'trial-plan.json')
    files = [*(WORK / name for name in tracked), DOC, KERNEL, PATCH, IMAGE, HOST,
        WORK / 'tests/fixtures/gauguin_display_drain_host.cpp', WORK / 'tests/fixtures/gauguin_scan_worker_drain_host.c',
        build.PARENT, prior.prior.SHIM, Path(parent['observer_helper']), MAIN / 'tools/storage-budget.py',
        *(BASE / name for name in ('build-storage-admission.json', 'live-batch-admission.json', 'current-root-capture/result.json')),
        *(P415 / name for name in ('ready.json', 'trial-plan.json', 'storage-bound-415.json', 'capture-profile.json',
                                  'core-native/result.json', 'c4-native/result.json', 'edr-native/result.json')),
        *(LAST / name for name in ('result.json', 'independent-restore.json', 'restored-capture/result.json', 'kernel.log'))]
    return capture_tools.scoped_pins(BASE, files, KERNEL, IMAGE)


def freeze():
    return shared.freeze(base=BASE, prior=P415, expected=expected_plan, validate=criteria, storage_bound=storage,
                         pin_inputs=pins, reserve=RESERVE)


def review():
    return shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria, storage_bound=storage,
                         preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__: fn for fn in (package, capture, delta, model, freeze, review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=actions)
    print(json.dumps(actions[parser.parse_args().step](), indent=2))
