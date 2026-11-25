#!/usr/bin/env python3
"""Freeze a byte-identical 0419 trial with only the CA work argument changed."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


sustained = import_module('prepare-frame417')
prior = sustained.prior
capture_tools, batch_tools = sustained.capture_tools, sustained.batch_tools
shared, save, RESERVE = sustained.shared, sustained.save, sustained.RESERVE
BASE = WORK / 'research/tmp/frame-422'
P419 = MAIN / 'research/tmp/gauguin-frame419-deadline-worktree-20261125/research/tmp/frame-419'
P421 = MAIN / 'research/tmp/gauguin-frame421-completion-wake-worktree-20261125/research/tmp/frame-421'
LAST = P421 / 'execution'
KERNEL = P419 / 'native-kernel/build-manifest.json'
REPLAY = P421 / '0419-optional-work-phase-replay.json'
BATCH = 800_000_000
WORK_US = 9700
TRIAL = '0422'
LIVE_BATCH = 315_000_000
IMAGE = BASE / 'frame422-image.json'
HOST = BASE / 'argument-difference.json'
DOC = WORK / 'docs/gauguin-frame-422-work-phase-20261125.md'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[flag for flag in sustained.FLAGS if not flag.startswith('allow_0417')],
         'allow_0422_one_bounded_60Hz_33s_drag_with_9700us_work_phase')
SUCCESS = '0422-sustained-60Hz-work-phase-compared-root-restored'


def baseline(*, fresh=True):
    end_path, proof_path = (LAST / name for name in ('result.json', 'independent-restore.json'))
    end, proof, restored = map(load, (end_path, proof_path, LAST / 'restored-capture/result.json'))
    require(sha(end_path) == '5734d3c2f0213c57a0014bc88c833991d5624c0cd6628a27a80f01dfcb05905a'
            and sha(proof_path) == '465b5b9bfcee393712b647135da3bc035577ceee62e23a7ca23c4dfd1b6fe023'
            and end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and end['completely_measured_seconds'] == 30
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256'],
            '0421 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256', 'combined_log_bytes', 'files', 'directories')),
            '0422 recovery differs from the 0421 readback')
    return current


def native():
    kernel = load(KERNEL)
    require(kernel['state'] == '0419-native-ARM64-linked' and kernel['inputs_unchanged']
            and kernel['baseline_reproduced_except_uuid'] and sha(kernel['kernel']) == kernel['kernel_sha256']
            == 'f3f8fe2c626578f7806ecd11b5b87a85842ff2ee63a7ba7d48b719b3a6447736',
            '0422 linked 0419 control differs')
    return kernel


def phase_command(command):
    words = command.split()
    require({'swp=5', 'sweetfb_stats=9', 'sweetfb_hz=60', 'f419=1'} <= set(words)
            and [word for word in words if word.startswith('sweet_ca_work_us=')] == ['sweet_ca_work_us=7200'],
            '0422 must change only the existing 0419 work budget')
    return command.replace('sweet_ca_work_us=7200', f'sweet_ca_work_us={WORK_US}')


def package():
    batch_tools.budget(BASE / 'phase-batch-admission.json', BATCH)
    baseline(fresh=False)
    kernel = native()
    parent = load(P419 / 'trial-plan.json')
    path = Path(parent['image'])
    require(sha(path) == parent['image_sha256'] and parent['kernel_identity'] == kernel['identity'],
            '0422 image donor differs')
    parts = import_module('package-frame344').parts
    before = path.read_bytes()
    header, shim, payload, dtb = parts(before)
    command = parent['boot_command'].encode()
    requested = phase_command(parent['boot_command'])
    require(payload[0x48:0x2a8].rstrip(bytes(1)) == command and len(command) == len(requested.encode()) < 608,
            '0422 donor command or fixed-size field differs')
    offset = len(header) + len(shim) + (-len(shim) % len(header)) + 0x48
    changed_payload = payload[:0x48] + requested.encode().ljust(608, bytes(1)) + payload[0x2a8:]
    after = before[:offset] + requested.encode().ljust(608, bytes(1)) + before[offset+608:]
    differences = [offset+i for i, (old,new) in enumerate(zip(command, requested.encode(), strict=True)) if old != new]
    require(parts(after) == [header, shim, changed_payload, dtb]
            and len(differences) == 2 and len(before) == len(after), '0422 changed bytes outside the two work digits')
    image_path = BASE / 'frame422-image.img'
    with image_path.open('xb') as stream:
        stream.write(after)
    edr = load(P419 / 'edr-native/result.json')
    require(sha(edr['binary']) == edr['binary_sha256'] == parent['EDR_helper_sha256']
            and edr['kernel_identity'] == kernel['identity'], '0422 exact signed 0419 helper differs')
    for kind in ('core', 'c4', 'edr'):
        name = f'{kind}-native/result.json'
        (BASE / name).parent.mkdir()
        shutil.copyfile(P419 / name, BASE / name)
    image = dict(state='0422-only-work-argument-changed', image=str(image_path), image_sha256=sha(image_path),
        image_bytes=len(after), command=requested, build_identity=kernel['identity'],
        kernel_manifest=str(KERNEL), kernel_sha256=kernel['kernel_sha256'], kernel_banner=kernel['kernel_banner'],
        input_pins={str(path):sha(path),str(KERNEL):sha(KERNEL)})
    save(IMAGE, image)
    save(HOST, dict(byte_offsets=differences, image_sha256=image['image_sha256'],
                    same_bootloader_kernel_userspace=True, previous_work_us=7200, work_us=WORK_US, device_commands=0))
    return {key: image[key] for key in ('image_sha256', 'image_bytes', 'build_identity')}

def capture():
    batch_tools.budget(BASE / 'live-batch-admission.json', LIVE_BATCH)
    result = capture_tools.capture_from(BASE, P421, TRIAL, baseline)
    prior.prior.capture_resources(current=baseline(), resources=RESOURCES)
    return result


def delta():
    return shared.stage.delta(BASE, P421, trial=TRIAL, header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json', core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE, BASE / 'restore-model', trial=TRIAL, resources=RESOURCES)
    return dict(checks=len(proof['checks']), failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), native()
    parent_path = P419 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    helper_path = BASE / 'edr-native/result.json'
    parent, image, install, helper = map(load, (parent_path, IMAGE, install_path, helper_path))
    recovered_plan = load(P421 / 'trial-plan.json')
    header, size = (current[key] for key in ('root_header_sha256', 'combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest'] == str(KERNEL) and kernel['kernel_sha256'] == image['kernel_sha256']
            and sha(image['image']) == image['image_sha256']
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['command'] == phase_command(parent['boot_command']) and helper['identity_only_retarget']
            and sha(helper['binary']) == helper['binary_sha256'] == install['admission_sha256']
            and install['core_sha256'] == parent['owned_core_sha256'] and install['C4_sha256'] == parent['C4_sha256']
            and install['trial'] == TRIAL and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256']
            and frame['target_refresh_hz'] == 60 and frame['modesets'] == 0 and frame['crc_required_preimage'] == 0x01000000,
            '0422 package, baseline or device effects differ')
    return dict(parent, state='prepared-frame422-60Hz-work-phase-comparison', trial=TRIAL, root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'], kernel_banner=kernel['kernel_banner'], boot_command=image['command'],
        EDR_helper_sha256=helper['binary_sha256'], signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'], measured_baseline_bytes=size, max_combined_log_bytes=size + LOG_SUFFIX,
            sizes={name: current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size - recovered_plan['log_capture']['measured_baseline_bytes']),
        ca_work_phase=dict(control_us=7200, active_us=WORK_US, image_byte_changes=2,
                           same_kernel=True, same_signed_payloads=True),
        optimization='Advance the CA timer work allowance by 2.5 ms against the unchanged 0419 deadline.',
        performance_comparison='Compare actual CRC transitions during the identical 33-second stimulus.')


def criteria(plan):
    batch_tools.budget(BASE / 'phase-batch-admission.json', BATCH)
    batch_tools.budget(BASE / 'live-batch-admission.json', LIVE_BATCH)
    parent = load(P419 / 'trial-plan.json')
    allowed = {'state', 'trial', 'root_header_sha256', 'parent_trial_plan_sha256', 'install_plan_sha256',
               'image', 'image_sha256', 'image_bytes', 'kernel_identity', 'kernel_banner', 'boot_command',
               'EDR_helper_sha256', 'signed_native_EDR_scope_sha256', 'log_capture', 'ca_work_phase',
               'optimization', 'performance_comparison'}
    require({key for key in parent.keys() | plan.keys() if plan.get(key) != parent.get(key)} <= allowed,
            '0422 changed the timing control or device scope')
    old, new = (load(path / 'slot-delta/install-plan.json') for path in (P419, BASE))
    require({name for name, row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == set(), '0422 signed userspace differs from 0419')
    host = load(HOST)
    require(host['image_sha256'] == plan['image_sha256'] and host['same_bootloader_kernel_userspace']
            and len(host['byte_offsets']) == 2 and host['previous_work_us'] == 7200
            and host['work_us'] == WORK_US and not host['device_commands'], '0422 command proof differs')
    require(sha(REPLAY) == '124486e7af14b8f39c56f604bc588cd4a9ff56f2d0c216a9d7f64949c8789de4',
            '0422 host timer replay differs')
    replay = load(REPLAY)
    case, = (case for case in replay['cases'] if case['work_us'] == WORK_US and case['extra_delay_ticks'] == 19200)
    require(not replay['device_commands'] and case['eligible'] == case['on_time'] == 2691 and not case['invalid'],
            '0422 earlier timer budget did not pass the hardware-edge replay')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17, '0422 restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE, P419, plan['root_header_sha256'], plan)


def storage(plan):
    old = load(P419 / 'storage-bound-419.json')
    components = dict(old['components'], phase_comparison=262_144)
    total = sum(components.values())
    require(total <= RESERVE, '0422 outputs exceed the reserved runtime batch')
    return dict(old, state='bounded0422-60Hz-work-phase-runtime', components=components, worst_case_bytes=total,
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'], log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git', 'ls-files', 'tools/*.py', 'tools/*.sh'], cwd=WORK, text=True).splitlines()
    parent = load(P419 / 'trial-plan.json')
    files = [*(WORK / name for name in tracked), DOC, KERNEL, IMAGE, HOST, REPLAY,
        Path(parent['observer_helper']), MAIN / 'tools/storage-budget.py',
        *(BASE / name for name in ('phase-batch-admission.json', 'live-batch-admission.json', 'current-root-capture/result.json')),
        *(P419 / name for name in ('ready.json', 'trial-plan.json', 'storage-bound-419.json', 'capture-profile.json',
                                  'core-native/result.json', 'c4-native/result.json', 'edr-native/result.json')),
        P421 / 'capture-profile.json', P421 / 'trial-plan.json',
        *(LAST / name for name in ('result.json', 'independent-restore.json', 'restored-capture/result.json',
                                  'completion-wake-comparison.json')),
        P419 / 'execution/sustained-scanout.json', P419 / 'execution/result.json']
    return capture_tools.scoped_pins(BASE, files, KERNEL, IMAGE)


def freeze():
    return shared.freeze(base=BASE, prior=P421, expected=expected_plan, validate=criteria, storage_bound=storage,
                         pin_inputs=pins, reserve=RESERVE)


def review():
    return shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria, storage_bound=storage,
                         preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__: fn for fn in (package, capture, delta, model, freeze, review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=actions)
    print(json.dumps(actions[parser.parse_args().step](), indent=2))
