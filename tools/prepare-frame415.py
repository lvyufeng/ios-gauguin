#!/usr/bin/env python3
"""Package the latest 0415 kernel for a bounded physical-touch session."""

import argparse
from hashlib import sha256
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


prior = import_module('prepare-frame414')
capture_tools = prior.capture_tools
BATCH, RESERVE, shared, save = prior.BATCH, prior.RESERVE, prior.shared, prior.save
TRIAL = '0415'
P414 = prior.BASE
LAST = P414 / 'execution'
BASE = WORK / 'research/tmp/frame-415'
IMAGE = BASE / 'frame415-image.json'
DOC = WORK / 'docs/gauguin-frame-415-scanout-handoff-20261124.md'
NATIVE = MAIN / 'research/tmp/frame-415-write-probe/timed'
KERNEL = NATIVE / 'native-kernel/build-manifest.json'
PROOF = NATIVE.parent / 'native-latest-check.json'
PATCH = NATIVE / 'boot-slot-write-probe.patch'
GENERATOR = MAIN / 'tools/frame415-scanout-write-probe.py'
FIXTURE = MAIN / 'tests/fixtures/gauguin_scanout_write_probe_host.cpp'
CLEANUP = MAIN / 'research/tmp/storage-retirement-20261124/result.json'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
SLOT_BYTES = prior.SLOT_BYTES
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0414')],
         'allow_0415_one_bounded_60Hz_boot_with_two_offscreen_GPU_store_probes', 'allow_physical_NVT_input')
SUCCESS = '0415-physical-touch-preview-finished-root-restored'
MANUAL_ARGS = {'sweetnvt=0': 'sweetnvt=1', 'swp=4': 'swp=0', 'gsp=328': 'gsp=0',
               'sbp=1': 'sbp=0', 'touch_lat=1': 'touch_lat=0',
               'sweettzsample=1': None, 'sweettrace=2': None}


def baseline(*, fresh=True):
    end, proof, restored = (load(LAST / name) for name in (
        'result.json', 'independent-restore.json', 'restored-capture/result.json'))
    parent = load(P414 / 'trial-plan.json')
    require(end['trial'] == '0414' and end['boot_attempts'] == 1 and end['observer_exit'] == 0
            and end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and end['DPU_independent_physical_FPS_qualified'] and end['GPU_readonly_aperture_qualified']
            and not end['stable_60_fps_observed']
            and load(LAST / end['comparison'])['reserved_GPU_mapping']['page_tables_qualified']
            and proof['install_plan_sha256'] == parent['install_plan_sha256'] and not proof['device_writes']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and proof['root_header_sha256'] == restored['root_header_sha256'],
            '0415 requires independently restored 0414 with the scoped aperture proof')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31 and
            all(current[key] == restored[key] for key in ('root_header_sha256', 'combined_log_bytes', 'files', 'directories')),
            '0415 live recovery root differs from 0414 readback')
    return current


def native():
    kernel, proof = load(KERNEL), load(PROOF)
    require(kernel['state'] == '0415-native-ARM64-linked' and kernel['inputs_unchanged']
            and kernel['baseline_reproduced_except_uuid'] and proof['cases'] == 14
            and proof['paired_native_sources_checked'] and not proof['device_commands']
            and proof['manifest'] == str(KERNEL) and proof['identity'] == kernel['identity']
            and proof['kernel_sha256'] == kernel['kernel_sha256'] == sha(kernel['kernel'])
            and kernel['input_pins'][str(prior.gpu.KERNEL)] == sha(prior.gpu.KERNEL)
            and kernel['input_pins'][str(PATCH)] == sha(PATCH)
            and {Path(path).stem for path in kernel['object_replacements'].values()} ==
                {'GauguinGPU', 'SweetFramebuffer', 'gauguin_ui_trace_board'},
            '0415 native write probe and host evidence differ')
    return kernel


def manual_command(parent):
    words = parent.split()
    keys = [word.partition('=')[0] for word in words]
    require(len(keys) == len(set(keys)) and MANUAL_ARGS.keys() <= set(words) and 'sweet_ca_work_us' not in keys,
            '0415 manual profile donor differs')
    updated = [MANUAL_ARGS.get(word, word) for word in words]
    command = ' '.join([*(word for word in updated if word), 'sweet_ca_work_us=7200'])
    require(len(command.encode()) < 608, '0415 physical-touch command exceeds payload field')
    return command


def manual_edr(pack, parent, image):
    donor = P414 / 'edr-native'
    old = load(donor / 'result.json')
    binary = Path(old['binary'])
    require(sha(binary) == old['binary_sha256'] == parent['EDR_helper_sha256'],
            '0414 signed admission helper differs')
    out = BASE / 'edr-native'
    source = out / 'sources'
    source.mkdir(parents=True)
    old_identity = old['kernel_identity']
    identity = image['build_identity']
    old_scope = 'length == 7 && !memcmp(start, "gsp=328", 7)'
    new_scope = 'length == 5 && !memcmp(start, "gsp=0", 5)'
    inputs = [donor / 'result.json', binary]
    for path in sorted((donor / 'sources').iterdir()):
        content = path.read_text()
        if path.name == 'EDRDefaultCore.h':
            require(content.count(old_identity) == content.count(old_scope) == 1, '0414 helper scope differs')
            content = content.replace(old_identity, identity).replace(old_scope, new_scope)
        (source / path.name).write_text(content)
        inputs.append(path)

    fixture = donor / 'edr414_host.c'
    host = out / 'edr415_host.c'
    host.write_text(fixture.read_text().replace(old_identity, identity).replace('gsp=328', 'gsp=0')
                    .replace('gsp=316', 'gsp=328'))
    inputs.append(fixture)
    executable = out / 'edr415-host'
    subprocess.run(['xcrun', 'clang', '-std=gnu11', '-O1', '-g', '-fblocks', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', str(host), '-o', str(executable)], check=True, timeout=60)
    checks = json.loads(subprocess.check_output([str(executable)], text=True, timeout=15))
    require(checks['checks'] == old['scope_checks'] and checks['device_commands'] == 0,
            '0415 signed manual helper host checks differ')

    base = pack.P343 / 'edr-native'
    reference = base / 'result.json'
    argv = next(step['argv'] for step in load(reference)['steps'] if step['label'] == 'candidate-compile').copy()
    sdk = argv.index('-isysroot') + 1
    if not Path(argv[sdk]).is_dir():
        argv[sdk] = str(Path(argv[sdk]).with_name('iPhoneOS.sdk'))
    target = out / binary.name
    argv[argv.index(str(base / 'sources/EDRDefault.c'))] = str(source / 'EDRDefault.c')
    argv[argv.index('-o') + 1] = str(target)
    inputs.extend([reference, *(Path(name) for name in argv if name.endswith('.c') and Path(name).is_file())])
    subprocess.run(argv, cwd=WORK, check=True, timeout=120)
    subprocess.run(['codesign', '--force', '--sign', '-', str(target)], check=True, timeout=60)
    for candidate in (binary, target):
        subprocess.run(['codesign', '--verify', '--strict', str(candidate)], check=True, timeout=60)
    for command in (('nm', '-m', '-u'), ('nm', '-gUj'), ('otool', '-L')):
        before, after = (subprocess.check_output([*command, str(path)], text=True, timeout=60).splitlines()
                         for path in (binary, target))
        if command[0] == 'otool':
            before, after = before[1:], after[1:]
        require(before == after, '0415 manual helper ABI differs')
    require(target.stat().st_size == binary.stat().st_size and identity.encode() in target.read_bytes(),
            '0415 manual helper identity or slot size differs')
    return dict(state='0415-manual-EDR-signed-offline', binary=str(target), binary_sha256=sha(target),
                binary_bytes=target.stat().st_size, kernel_identity=identity, sampler_profile=0,
                scope_checks=checks['checks'], input_pins={str(path): sha(path) for path in inputs}, device_commands=0)


def package():
    prior.prior.budget(BASE / 'package-and-run-admission.json', BATCH + 60_000_000)
    baseline(fresh=False)
    parent, kernel = load(P414 / 'trial-plan.json'), native()
    pack = import_module('package-frame344')
    shim = load(prior.SHIM)
    require(sha(shim['binary']) == shim['binary_sha256'] and not shim['device_commands'],
            '0415 reserved scanout shim differs')
    command = manual_command(parent['boot_command'])
    image = pack.boot_image(load(pack.P343 / 'runtime343-image.json'), kernel, base=BASE, trial=TRIAL,
        frame_capture_mode=9, scripted_motion=True, private_scanout_shim=Path(shim['binary']),
        private_scanout_slot_bytes=SLOT_BYTES,
        command_profile=lambda base: manual_command(capture_tools.command_profile(base)))
    before, after = (pack.parts(Path(name).read_bytes()) for name in (parent['image'], image['image']))
    require(before[0][:16] == after[0][:16] and before[0][20:] == after[0][20:] and before[1] == after[1]
            and before[3] == after[3] and command == image['command'], '0415 panel or loader changed')
    helper = manual_edr(pack, parent, image)
    image['kernel_manifest'] = str(KERNEL)
    save(IMAGE, image)
    save(BASE / 'edr-native/result.json', helper)
    for kind in ('core', 'c4'):
        receipt = BASE / f'{kind}-native/result.json'
        receipt.parent.mkdir()
        shutil.copyfile(P414 / f'{kind}-native/result.json', receipt)
    return {key: image[key] for key in ('image_sha256', 'image_bytes', 'build_identity')}


def capture():
    prior.prior.budget(BASE / 'live-batch-admission.json', BATCH)
    result = capture_tools.capture_from(BASE, P414, TRIAL, baseline)
    capture_resources()
    return result


def capture_resources(*, current=None, resources=RESOURCES):
    if current is None:
        current = baseline()
    meta = load(resources.parent.parent / 'result.json')
    header = current['root_header_sha256']
    require(meta['root_header_sha256'] == header and not resources.exists(), 'model resource capture differs')
    sys.path.insert(0, str(MAIN / 'research/tmp/dsh-0175'))
    from write_root_delta175v2 import RecoveryIO

    io = RecoveryIO()
    require(sha256(io.read(0, 4096)).hexdigest() == header, 'live root changed before resource capture')
    bundle = '/System/Library/Extensions/GauguinMetalDesktop.bundle'
    ranges = []
    resources.parent.mkdir(exist_ok=True)
    for leaf in ('Info.plist', '_CodeSignature/CodeResources'):
        file = current['files'][f'{bundle}/{leaf}']
        (start, count), = file['fork']['extents']
        require(count == 1 and 0 < file['bytes'] <= 4096, 'bundle resource geometry changed')
        offset = start * 4096
        data = io.read(offset, 4096)
        require(sha256(data[:file['bytes']]).hexdigest() == file['sha256'], 'bundle resource contents changed')
        name = Path(leaf).name + '.bin'
        (resources.parent / name).write_bytes(data)
        ranges.append(dict(file=name, offset=offset, bytes=len(data), sha256=sha256(data).hexdigest()))
    require(sha256(io.read(0, 4096)).hexdigest() == header, 'live root changed during resource capture')
    result = dict(root_header_sha256=header, ranges=ranges, device_writes=0, device_boots=0)
    save(resources, result)
    return result


def delta():
    return shared.stage.delta(BASE, P414, trial=TRIAL, header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json', core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE, BASE / 'restore-model', trial=TRIAL, resources=RESOURCES)
    return dict(checks=len(proof['checks']), failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), native()
    parent_path = P414 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    helper_path = BASE / 'edr-native/result.json'
    parent, image, install, helper = map(load, (parent_path, IMAGE, install_path, helper_path))
    header, size = (current[key] for key in ('root_header_sha256', 'combined_log_bytes'))
    frame = parent['frame_capture']
    require(image['kernel_manifest'] == str(KERNEL) and kernel['kernel_sha256'] == image['kernel_sha256']
            and sha(image['image']) == image['image_sha256']
            and image['build_identity'] == kernel['identity'] == helper['kernel_identity']
            and image['command'] == manual_command(parent['boot_command']) and helper['sampler_profile'] == 0
            and sha(helper['binary']) == helper['binary_sha256'] == install['admission_sha256']
            and install['core_sha256'] == parent['owned_core_sha256'] and install['C4_sha256'] == parent['C4_sha256']
            and install['rows']['core']['new_logical'] == parent['owned_core_logical_bytes']
            and install['rows']['c4']['new_logical'] == parent['C4_logical_bytes'] and install['trial'] == TRIAL
            and install['root_header_sha256'] == header and install['changed_ranges'] == 12
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256']
            and frame['target_refresh_hz'] == 60 and frame['modesets'] == 0
            and frame['crc_required_preimage'] == 0x01000000 and parent['scripted_strokes'] == 13
            and parent['sustained_motion']['normal_reports'] == 162
            and parent['display_dma']['private_reserved_linear_bytes'] == SLOT_BYTES, '0415 exact scope differs')
    return dict(parent, state='prepared-frame415-physical-touch', trial=TRIAL, root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        kernel_identity=kernel['identity'], kernel_banner=kernel['kernel_banner'], boot_command=image['command'],
        user_input='physical-Novatek-touch-only', scripted_strokes=0, scripted_reports=0,
        wake_button_pairs_max=0, sustained_motion=None, main_thread_sampling=None, process_sampling=None,
        frame_capture=dict(frame, starts_at='first valid physical contact with display on', publish_new_content_fps=False),
        EDR_helper_sha256=helper['binary_sha256'], signed_native_EDR_scope_sha256=sha(helper_path),
        log_capture=dict(parent['log_capture'], measured_baseline_bytes=size, max_combined_log_bytes=size + LOG_SUFFIX,
            sizes={name: current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size - parent['log_capture']['measured_baseline_bytes']),
        offscreen_GPU_probe=dict(leases=2, command_dwords=8, bytes_per_slot=SLOT_BYTES,
            GPU_store_word_offsets=[0, SLOT_BYTES - 4], CPU_restore_word_offsets=[0, SLOT_BYTES - 4],
            additional_GPU_jobs=2, additional_page_table_stores=12, additional_translation_syncs=4,
            retain_resources_on_uncertainty=True, release_after_EOP_and_original_word_readback=True),
        optimization='Measure the time from guarded GPU write completion through display reuse of each reserved slot.',
        performance_comparison='Physical user interaction with guarded display and GPU write receipts.')


def criteria(plan):
    prior.prior.budget(BASE / 'package-and-run-admission.json', BATCH + 60_000_000)
    prior.prior.budget(BASE / 'live-batch-admission.json', BATCH)
    parent = load(P414 / 'trial-plan.json')
    allowed = {'state', 'trial', 'root_header_sha256', 'parent_trial_plan_sha256', 'install_plan_sha256',
               'image', 'image_sha256', 'image_bytes', 'kernel_identity', 'kernel_banner', 'EDR_helper_sha256',
               'signed_native_EDR_scope_sha256', 'log_capture', 'offscreen_GPU_probe', 'optimization', 'boot_command',
               'user_input', 'scripted_strokes', 'scripted_reports', 'wake_button_pairs_max', 'sustained_motion',
               'main_thread_sampling', 'process_sampling', 'frame_capture',
               'performance_comparison'}
    require({key for key in parent.keys() | plan.keys() if plan.get(key) != parent.get(key)} <= allowed,
            '0415 changes exceed the reviewed scope')
    old, new = (load(path / 'slot-delta/install-plan.json') for path in (P414, BASE))
    require({name for name, row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'}, '0415 userspace differs beyond the signed manual helper')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17, '0415 restore coverage differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE, P414, plan['root_header_sha256'], plan)


def storage(plan):
    previous = load(P414 / 'storage-bound-414.json')
    components = dict(previous['components'], GPU_probe_receipts=65_536)
    total = sum(components.values())
    require(total <= RESERVE, '0415 output exceeds runtime reserve')
    return dict(previous, state='bounded0415-GPU-probe-runtime', components=components, worst_case_bytes=total,
        fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'], log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git', 'ls-files', 'tools/*.py', 'tools/*.sh'], cwd=WORK, text=True).splitlines()
    parent = load(P414 / 'trial-plan.json')
    files = [*(WORK / name for name in tracked), DOC, KERNEL, IMAGE, PROOF, PATCH, GENERATOR, FIXTURE, prior.SHIM,
        Path(parent['observer_helper']), MAIN / 'tools/storage-budget.py',
        NATIVE.parent / 'full-batch-admission.json', CLEANUP,
        *(BASE / name for name in ('package-and-run-admission.json', 'live-batch-admission.json', 'current-root-capture/result.json')),
        *(P414 / name for name in ('ready.json', 'trial-plan.json', 'storage-bound-414.json', 'capture-profile.json',
                                  'core-native/result.json', 'c4-native/result.json', 'edr-native/result.json')),
        *(LAST / name for name in ('result.json', 'independent-restore.json', 'restored-capture/result.json',
                                  'kernel.log', 'kernel.log.bin', 'page-flip-latches.json', load(LAST / 'result.json')['comparison']))]
    return capture_tools.scoped_pins(BASE, files, KERNEL, IMAGE)


def freeze():
    return shared.freeze(base=BASE, prior=P414, expected=expected_plan, validate=criteria, storage_bound=storage,
                         pin_inputs=pins, reserve=RESERVE)


def review():
    return shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria, storage_bound=storage,
                         preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__: fn for fn in (package, capture, capture_resources, delta, model, freeze, review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step', choices=actions)
    print(json.dumps(actions[cli.parse_args().step](), indent=2))
