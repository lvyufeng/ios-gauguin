#!/usr/bin/env python3
"""Freeze one temporary 60 Hz boot with a sustained drag and scanout readback."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


build = import_module('build-frame417')
prior = import_module('prepare-frame416')
capture_tools, batch_tools = prior.capture_tools, prior.batch_tools
shared, save, RESERVE = prior.shared, prior.save, prior.RESERVE
BASE, KERNEL, PATCH = build.BASE, build.MANIFEST, build.PATCH
P416, LAST = build.P416, build.P416 / 'execution'
TRIAL = '0417'
LIVE_BATCH = 315_000_000
IMAGE = BASE / 'frame417-image.json'
HOST = BASE / 'sustained-host.json'
DOC = WORK / 'docs/gauguin-frame-417-sustained-60-20261124.md'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[flag for flag in prior.FLAGS
           if not flag.startswith('allow_0416') and flag != 'allow_physical_NVT_input'],
         'allow_0417_one_bounded_60Hz_33s_synthetic_drag')
SUCCESS = '0417-sustained-60Hz-measured-root-restored'
ANDROID = MAIN / 'docs/gauguin-same-clock-high-refresh-plan-20261124.md'
ROUNDTRIPS = MAIN / 'research/tmp/same-clock-high-refresh-20261124/mode-roundtrips.json'


def baseline(*, fresh=True):
    end_path, proof_path = (LAST / name for name in ('result.json', 'independent-restore.json'))
    end, proof, restored = map(load, (end_path, proof_path, LAST / 'restored-capture/result.json'))
    require(sha(end_path) == 'ceef357afd35950b6a41bd99dff94582e3af21d1908ee0bc0772f97be8ab6f99'
            and sha(proof_path) == '78f46ed4f1bc4e7bd3b7c9b661697c776ce91e6598c116efc0a85eb2334a15e0'
            and end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256'],
            '0416 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256', 'combined_log_bytes', 'files', 'directories')),
            '0417 live recovery root differs from the 0416 readback')
    return current


def native():
    kernel = load(KERNEL)
    require(kernel['state'] == '0417-native-ARM64-linked' and kernel['inputs_unchanged']
            and kernel['baseline_reproduced_except_uuid'] and sha(kernel['kernel']) == kernel['kernel_sha256']
            and kernel['input_pins'][str(PATCH)] == sha(PATCH)
            and kernel['input_pins'][str(build.PARENT)] == sha(build.PARENT)
            and {Path(path).stem for path in kernel['object_replacements'].values()} == build.UNITS,
            '0417 native profile differs')
    return kernel


def sustained_command(command):
    replacements = {'sweetnvt=1': 'sweetnvt=0', 'swp=0': 'swp=5'}
    words = command.split()
    require(all(words.count(word) == 1 for word in replacements)
            and {'sweetfb_hz=60', 'gpf=5', 'gsp=0', 'sweet_ca_work_us=7200'} <= set(words),
            '0417 boot argument donor differs')
    return ' '.join(replacements.get(word, word) for word in words)


def package():
    batch_tools.budget(BASE / 'build-storage-admission.json', build.BATCH)
    baseline(fresh=False)
    parent, kernel = load(P416 / 'trial-plan.json'), native()
    pack = import_module('package-frame344')
    shim = load(prior.prior.prior.SHIM)
    require(sha(shim['binary']) == shim['binary_sha256'], '0416 reserved scanout shim differs')
    image = pack.boot_image(load(pack.P343 / 'runtime343-image.json'), kernel, base=BASE, trial=TRIAL,
        frame_capture_mode=9, scripted_motion=True, private_scanout_shim=Path(shim['binary']),
        private_scanout_slot_bytes=prior.prior.SLOT_BYTES,
        command_profile=lambda command: sustained_command(
            prior.prior.manual_command(capture_tools.command_profile(command))))
    old, new = (pack.parts(Path(row['image']).read_bytes()) for row in (parent, image))
    require(old[0][:16] == new[0][:16] and old[0][20:] == new[0][20:] and old[1] == new[1]
            and old[3] == new[3] and image['command'] == sustained_command(parent['boot_command']),
            '0417 boot shape differs')
    image['kernel_manifest'] = str(KERNEL)
    save(IMAGE, image)
    helper = prior.retarget_helper(pack, image, parent, base=BASE, reference=P416 / 'edr-native/result.json', trial=TRIAL)
    save(BASE / 'edr-native/result.json', helper)
    for kind in ('core', 'c4'):
        name = f'{kind}-native/result.json'
        (BASE / name).parent.mkdir()
        shutil.copyfile(P416 / name, BASE / name)
    return {key: image[key] for key in ('image_sha256', 'image_bytes', 'build_identity')}


def capture():
    batch_tools.budget(BASE / 'live-batch-admission.json', LIVE_BATCH)
    result = capture_tools.capture_from(BASE, P416, TRIAL, baseline)
    prior.prior.capture_resources(current=baseline(), resources=RESOURCES)
    return result


def delta():
    return shared.stage.delta(BASE, P416, trial=TRIAL, header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json', core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE, BASE / 'restore-model', trial=TRIAL, resources=RESOURCES)
    return dict(checks=len(proof['checks']), failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), native()
    parent_path = P416 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    helper_path = BASE / 'edr-native/result.json'
    parent, image, install, helper = map(load, (parent_path, IMAGE, install_path, helper_path))
    header, size = (current[key] for key in ('root_header_sha256', 'combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest'] == str(KERNEL) and kernel['kernel_sha256'] == image['kernel_sha256']
            and sha(image['image']) == image['image_sha256']
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['command'] == sustained_command(parent['boot_command']) and helper['identity_only_retarget']
            and sha(helper['binary']) == helper['binary_sha256'] == install['admission_sha256']
            and install['core_sha256'] == parent['owned_core_sha256'] and install['C4_sha256'] == parent['C4_sha256']
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256']
            and frame['target_refresh_hz'] == 60 and frame['modesets'] == 0 and frame['crc_required_preimage'] == 0x01000000,
            '0417 package, baseline or device effects differ')
    return dict(parent, state='prepared-frame417-sustained-60Hz', trial=TRIAL, root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'], kernel_banner=kernel['kernel_banner'], boot_command=image['command'],
        EDR_helper_sha256=helper['binary_sha256'], signed_native_EDR_scope_sha256=sha(helper_path),
        user_input='bounded-synthetic-horizontal-drag', scripted_strokes=1, scripted_reports=34, wake_button_pairs_max=1,
        sustained_motion=dict(duration_ms=33_000, report_interval_ms=10, position_step_count=3300,
                              max_release_reports=1, x_bounds=[180, 900], y=1200,
                              start_delay_after_unlock_ms=6000, score_after_seconds=2, score_seconds=30),
        log_capture=dict(parent['log_capture'], measured_baseline_bytes=size, max_combined_log_bytes=size + LOG_SUFFIX,
            sizes={name: current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size - parent['log_capture']['measured_baseline_bytes']),
        frame_capture=dict(frame, starts_at='qualified display-on settle', records=6144, motion_wire='F417 MOTION',
            maximum_total_display_register_writes=6154, publish_new_content_fps=True,
            fps_requires_unambiguous_latch_calibration=False,
            presentation_policy=dict(frame['presentation_policy'], maximum_private_full_copy_attempts=3072,
                                     only_during_45s_frame_capture=False, only_during_45s_runtime_window=True)),
        display_drain=dict(parent['display_drain'], private_copy_limit=3072, trace_limit=6144,
                           trace_limit_ends_fast_path=False),
        optimization='Keep the existing 7.2 ms CA work phase and presentation active throughout a separate 45 s runtime window.',
        performance_comparison='Count new displayed content in every one-second bin of a fixed sustained drag.')


def criteria(plan):
    batch_tools.budget(BASE / 'build-storage-admission.json', build.BATCH)
    batch_tools.budget(BASE / 'live-batch-admission.json', LIVE_BATCH)
    parent = load(P416 / 'trial-plan.json')
    allowed = {'state', 'trial', 'root_header_sha256', 'parent_trial_plan_sha256', 'install_plan_sha256',
               'image', 'image_sha256', 'image_bytes', 'kernel_identity', 'kernel_banner', 'boot_command',
               'EDR_helper_sha256', 'signed_native_EDR_scope_sha256', 'log_capture', 'display_drain',
               'user_input', 'scripted_strokes', 'scripted_reports', 'wake_button_pairs_max', 'sustained_motion',
               'frame_capture', 'optimization', 'performance_comparison'}
    require({key for key in parent.keys() | plan.keys() if plan.get(key) != parent.get(key)} <= allowed,
            '0417 changes exceed the reviewed scope')
    old, new = (load(path / 'slot-delta/install-plan.json') for path in (P416, BASE))
    require({name for name, row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'}, '0417 userspace differs beyond the identity-bound helper')
    host = load(HOST)
    require(host['kernel_sha256'] == load(KERNEL)['kernel_sha256'] and host['patch_sha256'] == sha(PATCH)
            and host['framebuffer_cases'] >= 8 and host['scan_worker_cases'] >= 8 and host['motion_cases'] >= 5
            and not host['device_commands'], '0417 native host proof differs')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17, '0417 restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE, P416, plan['root_header_sha256'], plan)


def storage(plan):
    old = load(P416 / 'storage-bound-416.json')
    components = dict(old['components'], sustained_metric_receipts=196_608)
    total = sum(components.values())
    require(total <= RESERVE, '0417 outputs exceed the reserved runtime batch')
    return dict(old, state='bounded0417-sustained-60Hz-runtime', components=components, worst_case_bytes=total,
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'], log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git', 'ls-files', 'tools/*.py', 'tools/*.sh'], cwd=WORK, text=True).splitlines()
    parent = load(P416 / 'trial-plan.json')
    require(sha(ROUNDTRIPS) == '997c555443e4bca03953f5eb8e2330aed605f11781962fac16a94e05b0dc78e1',
            'offline Android mode replay differs')
    files = [*(WORK / name for name in tracked), DOC, KERNEL, PATCH, IMAGE, HOST, ANDROID, ROUNDTRIPS,
        WORK / 'tests/fixtures/gauguin_display_drain_host.cpp', WORK / 'tests/fixtures/gauguin_scan_worker_drain_host.c',
        WORK / 'tests/fixtures/gauguin_sustain_motion_host.c',
        build.PARENT, prior.prior.prior.SHIM, Path(parent['observer_helper']), MAIN / 'tools/storage-budget.py',
        *(BASE / name for name in ('build-storage-admission.json', 'live-batch-admission.json', 'current-root-capture/result.json')),
        *(P416 / name for name in ('ready.json', 'trial-plan.json', 'storage-bound-416.json', 'capture-profile.json',
                                  'core-native/result.json', 'c4-native/result.json', 'edr-native/result.json')),
        *(LAST / name for name in ('result.json', 'independent-restore.json', 'restored-capture/result.json', 'kernel.log'))]
    return capture_tools.scoped_pins(BASE, files, KERNEL, IMAGE)


def freeze():
    return shared.freeze(base=BASE, prior=P416, expected=expected_plan, validate=criteria, storage_bound=storage,
                         pin_inputs=pins, reserve=RESERVE)


def review():
    return shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria, storage_bound=storage,
                         preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__: fn for fn in (package, capture, delta, model, freeze, review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=actions)
    print(json.dumps(actions[parser.parse_args().step](), indent=2))
