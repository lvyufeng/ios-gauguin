#!/usr/bin/env python3
"""Freeze the measured 60 Hz profile with independent deadline diagnostics."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


build = import_module('build-frame419')
sustained = import_module('prepare-frame417')
prior = sustained.prior
capture_tools, batch_tools = sustained.capture_tools, sustained.batch_tools
shared, save, RESERVE = sustained.shared, sustained.save, sustained.RESERVE
BASE, KERNEL, PATCH = build.BASE, build.MANIFEST, build.PATCH
P417, LAST = build.P417, build.P417 / 'execution'
TRIAL = '0419'
LIVE_BATCH = 315_000_000
IMAGE = BASE / 'frame419-image.json'
HOST = BASE / 'deadline-host.json'
DOC = WORK / 'docs/gauguin-frame-419-deadline-timeline-20261125.md'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[flag for flag in sustained.FLAGS if not flag.startswith('allow_0417')],
         'allow_0419_one_bounded_60Hz_33s_drag_with_deadline_receipts')
SUCCESS = '0419-sustained-60Hz-deadlines-measured-root-restored'
ROW_LIMIT, WIRE_BYTES = 12_288, 786_432


def baseline(*, fresh=True):
    end_path, proof_path = (LAST / name for name in ('result.json', 'independent-restore.json'))
    end, proof, restored = map(load, (end_path, proof_path, LAST / 'restored-capture/result.json'))
    require(sha(end_path) == '59fe69ce2890c5ae574ae371be37bb0923889ad63643b48db82df01f8552f9d4'
            and sha(proof_path) == '55df2ba09b7bd395ce0feda103db5256333928eb1c0bcf43ac1b94f87965ac82'
            and end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and end['completely_measured_seconds'] == 30
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256'],
            '0417 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256', 'combined_log_bytes', 'files', 'directories')),
            '0419 recovery differs from the 0417 readback')
    return current


def diagnostic_command(command):
    words = command.split()
    require({'swp=5', 'sweetfb_stats=9', 'sweetfb_hz=60', 'sweet_ca_work_us=7200'} <= set(words)
            and not any(word.startswith('f419=') for word in words)
            and len((command + ' f419=1').encode()) < 608, '0419 boot argument donor differs')
    return command + ' f419=1'


def package():
    batch_tools.budget(BASE / 'build-storage-admission.json', build.BATCH)
    baseline(fresh=False)
    parent, kernel = load(P417 / 'trial-plan.json'), build.native()
    pack = import_module('package-frame344')
    shim = load(prior.prior.prior.SHIM)
    require(sha(shim['binary']) == shim['binary_sha256'], '0417 reserved scanout shim differs')
    image = pack.boot_image(load(pack.P343 / 'runtime343-image.json'), kernel, base=BASE, trial=TRIAL,
        frame_capture_mode=9, scripted_motion=True, private_scanout_shim=Path(shim['binary']),
        private_scanout_slot_bytes=prior.prior.SLOT_BYTES,
        command_profile=lambda command: diagnostic_command(sustained.sustained_command(
            prior.prior.manual_command(capture_tools.command_profile(command)))))
    old, new = (pack.parts(Path(row['image']).read_bytes()) for row in (parent, image))
    require(old[0][:16] == new[0][:16] and old[0][20:] == new[0][20:] and old[1] == new[1]
            and old[3] == new[3] and image['command'] == diagnostic_command(parent['boot_command']),
            '0419 boot shape differs')
    image['kernel_manifest'] = str(KERNEL)
    save(IMAGE, image)
    helper = prior.retarget_helper(pack, image, parent, base=BASE, reference=P417 / 'edr-native/result.json', trial=TRIAL)
    save(BASE / 'edr-native/result.json', helper)
    for kind in ('core', 'c4'):
        name = f'{kind}-native/result.json'
        (BASE / name).parent.mkdir()
        shutil.copyfile(P417 / name, BASE / name)
    return {key: image[key] for key in ('image_sha256', 'image_bytes', 'build_identity')}


def capture():
    batch_tools.budget(BASE / 'live-batch-admission.json', LIVE_BATCH)
    result = capture_tools.capture_from(BASE, P417, TRIAL, baseline)
    prior.prior.capture_resources(current=baseline(), resources=RESOURCES)
    return result


def delta():
    return shared.stage.delta(BASE, P417, trial=TRIAL, header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json', core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE, BASE / 'restore-model', trial=TRIAL, resources=RESOURCES)
    return dict(checks=len(proof['checks']), failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), build.native()
    parent_path = P417 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    helper_path = BASE / 'edr-native/result.json'
    parent, image, install, helper = map(load, (parent_path, IMAGE, install_path, helper_path))
    header, size = (current[key] for key in ('root_header_sha256', 'combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest'] == str(KERNEL) and kernel['kernel_sha256'] == image['kernel_sha256']
            and sha(image['image']) == image['image_sha256']
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['command'] == diagnostic_command(parent['boot_command']) and helper['identity_only_retarget']
            and sha(helper['binary']) == helper['binary_sha256'] == install['admission_sha256']
            and install['core_sha256'] == parent['owned_core_sha256'] and install['C4_sha256'] == parent['C4_sha256']
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256']
            and frame['target_refresh_hz'] == 60 and frame['modesets'] == 0 and frame['crc_required_preimage'] == 0x01000000,
            '0419 package, baseline or device effects differ')
    return dict(parent, state='prepared-frame419-60Hz-deadline-timeline', trial=TRIAL, root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'], kernel_banner=kernel['kernel_banner'], boot_command=image['command'],
        EDR_helper_sha256=helper['binary_sha256'], signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'], measured_baseline_bytes=size, max_combined_log_bytes=size + LOG_SUFFIX,
            sizes={name: current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size - parent['log_capture']['measured_baseline_bytes']),
        deadline_timeline=dict(rows=ROW_LIMIT, wire_bytes=WIRE_BYTES, duration_seconds=45, boot_option='f419=1',
            gpu_completion_and_visibility='bound native fence, ticket, surface version',
            promotion='exact generation and writer', copy='post-guard through store barrier, by attempt',
            dispatch='target scan, expected edge, ready deadline and send'),
        optimization='Measure each private presentation and deadline with 0418 trace-independent completion.',
        performance_comparison='Repeat the exact 0417 workload and CRC score with the separate deadline evidence.')


def criteria(plan):
    batch_tools.budget(BASE / 'build-storage-admission.json', build.BATCH)
    batch_tools.budget(BASE / 'live-batch-admission.json', LIVE_BATCH)
    parent = load(P417 / 'trial-plan.json')
    allowed = {'state', 'trial', 'root_header_sha256', 'parent_trial_plan_sha256', 'install_plan_sha256',
               'image', 'image_sha256', 'image_bytes', 'kernel_identity', 'kernel_banner', 'boot_command',
               'EDR_helper_sha256', 'signed_native_EDR_scope_sha256', 'log_capture', 'deadline_timeline',
               'optimization', 'performance_comparison'}
    require({key for key in parent.keys() | plan.keys() if plan.get(key) != parent.get(key)} <= allowed,
            '0419 changed the timing control or device scope')
    old, new = (load(path / 'slot-delta/install-plan.json') for path in (P417, BASE))
    require({name for name, row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'}, '0419 userspace differs beyond the identity-bound helper')
    host = load(HOST)
    require(host['kernel_sha256'] == load(KERNEL)['kernel_sha256'] and host['patch_sha256'] == sha(PATCH)
            and host['cases'] >= 8 and host['archived_0417_score_matches']
            and host['native_hooks_validated'] and not host['device_commands'], '0419 native deadline proof differs')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17, '0419 restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE, P417, plan['root_header_sha256'], plan)


def storage(plan):
    old = load(P417 / 'storage-bound-417.json')
    components = dict(old['components'], deadline_timeline_and_receipts=WIRE_BYTES + 524_288)
    total = sum(components.values())
    require(total <= RESERVE, '0419 outputs exceed the reserved runtime batch')
    return dict(old, state='bounded0419-60Hz-deadline-runtime', components=components, worst_case_bytes=total,
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'], log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git', 'ls-files', 'tools/*.py', 'tools/*.sh'], cwd=WORK, text=True).splitlines()
    parent = load(P417 / 'trial-plan.json')
    files = [*(WORK / name for name in tracked), DOC, KERNEL, PATCH, IMAGE, HOST,
        WORK / 'tests/fixtures/gauguin_deadline_timeline_host.c', build.PARENT, build.P418 / 'completion-host.json', prior.prior.prior.SHIM,
        Path(parent['observer_helper']), MAIN / 'tools/storage-budget.py',
        *(BASE / name for name in ('build-storage-admission.json', 'live-batch-admission.json', 'current-root-capture/result.json')),
        *(P417 / name for name in ('ready.json', 'trial-plan.json', 'storage-bound-417.json', 'capture-profile.json',
                                  'core-native/result.json', 'c4-native/result.json', 'edr-native/result.json')),
        *(LAST / name for name in ('result.json', 'independent-restore.json', 'restored-capture/result.json',
                                  'sustained-scanout.json', 'repeat-analysis.json', 'kernel.log'))]
    return capture_tools.scoped_pins(BASE, files, KERNEL, IMAGE)


def freeze():
    return shared.freeze(base=BASE, prior=P417, expected=expected_plan, validate=criteria, storage_bound=storage,
                         pin_inputs=pins, reserve=RESERVE)


def review():
    return shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria, storage_bound=storage,
                         preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__: fn for fn in (package, capture, delta, model, freeze, review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=actions)
    print(json.dumps(actions[parser.parse_args().step](), indent=2))
