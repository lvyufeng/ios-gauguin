#!/usr/bin/env python3
"""Prepare the 0419 60 Hz kernel with a reversible visible-marker workload."""

import argparse
from importlib import import_module
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha


phase = import_module('prepare-frame422')
TRIAL = '0423'
BASE = WORK / 'research/tmp/frame-423'
P419, KERNEL, RESERVE = phase.P419, phase.KERNEL, phase.RESERVE
P422 = MAIN / 'research/tmp/gauguin-frame422-work-phase-worktree-20261125/research/tmp/frame-422'
LAST = P422 / 'execution'
DOC = WORK / 'docs/gauguin-0419-probe-workloads-20261125.md'
IMAGE = BASE / 'frame423-image.json'
SB = BASE / 'sb-native/result.json'
SOURCE = WORK / 'userland/refresh_probe.m'
RESOURCES = BASE / 'metadata-snapshot/model-resources/result.json'
FLAGS = (*[flag for flag in phase.FLAGS if not flag.startswith('allow_0422')],
         'allow_0423_one_bounded_0419_60Hz_marker_window')
SUCCESS = '0423-0419-marker-measured-root-restored'


def baseline(*, fresh=True):
    end, proof, restored = (load(LAST / path) for path in
                             ('result.json', 'independent-restore.json', 'restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed']
            and proof['journal_empty'] and proof['all_original_slot_bits_allocated']
            and proof['misc_original_4096_bytes_match'] and not proof['device_writes']
            and proof['root_header_sha256'] == restored['root_header_sha256']
            and proof['install_plan_sha256'] == load(P422 / 'trial-plan.json')['install_plan_sha256'],
            '0422 independently restored baseline differs')
    if not fresh:
        return restored
    current = load(BASE / 'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31
            and all(current[key] == restored[key] for key in
                    ('root_header_sha256', 'combined_log_bytes', 'files', 'directories')),
            'fresh 0423 recovery differs from the 0422 readback')
    return current


def repack(base, parent, substitutions):
    parts = import_module('package-frame344').parts
    source = Path(parent['image'])
    require(sha(source) == parent['image_sha256'], '0419 image preimage differs')
    words = parent['boot_command'].split()
    require(all(words.count(word) == 1 for word in substitutions), '0419 input arguments differ')
    command = ' '.join(substitutions.get(word, word) for word in words)
    raw = source.read_bytes()
    header, shim, payload, dtb = parts(raw)
    old, new = parent['boot_command'].encode(), command.encode()
    offset = len(header) + len(shim) + (-len(shim) % len(header)) + 0x48
    require(len(new) < 608 and payload[0x48:0x2a8] == old.ljust(608, bytes(1))
            and raw[offset:offset+608] == payload[0x48:0x2a8], '0419 payload command differs')
    field = new.ljust(608, bytes(1))
    updated = raw[:offset] + field + raw[offset+608:]
    require(parts(updated) == [header, shim, payload[:0x48] + field + payload[0x2a8:], dtb],
            'boot bytes differ outside the command field')
    path = base / 'boot.img'
    with path.open('xb') as stream:
        stream.write(updated)
    return dict(image=str(path), image_sha256=sha(path), image_bytes=len(updated), command=command,
                input_pins={str(source):sha(source), str(KERNEL):sha(KERNEL)}, identical_kernel=True,
                substitutions=substitutions)


def package():
    baseline(fresh=False)
    kernel = phase.native()
    parent = load(P419 / 'trial-plan.json')
    require(parent['kernel_identity'] == kernel['identity'], '0419 kernel identity differs')
    source_sha = sha(SOURCE)
    binary = SB.parent / 'libGauguinEAGL.dylib'
    binary.parent.mkdir(exist_ok=True)
    subprocess.run(['xcrun','--sdk','iphoneos','clang','-target','arm64-apple-ios16.0',
                    '-O2','-Wall','-Wextra','-Werror','-fobjc-arc','-DGAUGUIN_REFRESH_OVERLAY',
                    '-dynamiclib','-framework','UIKit','-framework','QuartzCore','-framework','Foundation',
                    '-Wl,-install_name,/usr/local/lib/gauguin/libGauguinEAGL.dylib',
                    str(SOURCE),'-o',str(binary)], check=True)
    subprocess.run(['codesign','--force','--sign','-','--timestamp=none',str(binary)], check=True)
    subprocess.run(['codesign','--verify','--strict',str(binary)], check=True)
    require(sha(SOURCE) == source_sha, 'marker source changed during compilation')
    phase.save(SB,dict(binary=str(binary), binary_sha256=sha(binary), bytes=binary.stat().st_size,
                       input_pins={str(SOURCE):source_sha}, sample_seconds=32))
    image = repack(BASE, parent, {'sbp=0':'sbp=1'})
    phase.save(IMAGE, image)
    for kind in ('core', 'c4', 'edr'):
        rel = f'{kind}-native/result.json'
        (BASE / rel).parent.mkdir()
        shutil.copyfile(P419 / rel, BASE / rel)
    return {key:image[key] for key in ('image_sha256','image_bytes','substitutions')}


def capture():
    phase.batch_tools.budget(BASE / 'live-batch-admission.json', phase.LIVE_BATCH)
    result = phase.capture_tools.capture_from(BASE, P422, TRIAL, baseline)
    phase.prior.prior.capture_resources(current=baseline(), resources=RESOURCES)
    return result


def delta():
    return phase.shared.stage.delta(BASE, P419, trial=TRIAL, header=baseline()['root_header_sha256'],
        baseline=LAST / 'restored-capture/result.json', core_logical=load(BASE / 'core-native/result.json')['bytes'],
        c4_receipt=BASE / 'c4-native/result.json', sb_receipt=SB)


def model():
    result = import_module('check-core342-rollback').check(BASE, BASE / 'restore-model', trial=TRIAL,
                                                          resources=RESOURCES)
    return dict(checks=len(result['checks']), failure_points=result['all_restore_partial_write_points'])


def expected_plan():
    current, kernel = baseline(), phase.native()
    parent_path = P419 / 'trial-plan.json'
    install_path = BASE / 'slot-delta/install-plan.json'
    parent, image, install, marker = map(load,(parent_path,IMAGE,install_path,SB))
    header, size = current['root_header_sha256'], current['combined_log_bytes']
    require(image['identical_kernel'] and image['substitutions'] == {'sbp=0':'sbp=1'}
            and sha(image['image']) == image['image_sha256'] and parent['kernel_identity'] == kernel['identity']
            and image['command'] == parent['boot_command'].replace(' sbp=0 ', ' sbp=1 ')
            and install['trial'] == TRIAL and install['root_header_sha256'] == header
            and install['changed_ranges'] == 12 and marker['sample_seconds'] == 32
            and parent['EDR_helper_sha256'] == install['admission_sha256']
            and parent['owned_core_sha256'] == install['core_sha256'] and parent['C4_sha256'] == install['C4_sha256']
            and sha(BASE / 'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            '0419 marker package or bounded device effects differ')
    return dict(parent, state='prepared-0419-marker-60Hz', trial=TRIAL, root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path), install_plan_sha256=sha(install_path),
        image=image['image'], image_sha256=image['image_sha256'], image_bytes=image['image_bytes'],
        new_kernel_builds=0, boot_command=image['command'], SB_sha256=marker['binary_sha256'],
        log_capture=dict(parent['log_capture'], measured_baseline_bytes=size, max_combined_log_bytes=size + LOG_SUFFIX,
                         sizes={name:current['files'][name]['bytes'] for name in parent['log_capture']['sizes']},
                         previous_verified_suffix_bytes=size - load(P422 / 'trial-plan.json')['log_capture']['measured_baseline_bytes']),
        probe=dict(workload='opaque non-key SpringBoard window', marker_seconds=32, score_seconds=30,
                   held_calibration_words=16, nominal_rate_hz=60, digits=12),
        optimization='No rendering change; run the shared refresh marker with the exact 0419 kernel.',
        performance_comparison='Count decoded marker changes and paired display CRC changes in the central 30 seconds.')


def criteria(plan):
    phase.batch_tools.budget(BASE / 'live-batch-admission.json', phase.LIVE_BATCH)
    old, new = (load(path / 'slot-delta/install-plan.json') for path in (P419, BASE))
    require({name for name, row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'eagl'}, 'a signed payload outside the existing SpringBoard slot changed')
    proof = load(BASE / 'restore-model/result.json')
    require(proof['all_model_IO_writes_memory_only'] and proof['install_ranges'] == 12 and len(proof['checks']) == 49
            and proof['all_restore_partial_write_points'] == 17, '0423 restore coverage differs')
    require(load(SB)['input_pins'][str(SOURCE)] == sha(SOURCE), 'marker source changed after compilation')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P419,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P422 / 'storage-bound-422.json')
    components = dict(old['components'], marker_receipts=524_288)
    require(sum(components.values()) <= RESERVE, 'marker reports exceed reserve')
    return dict(old, state='bounded-0419-marker-runtime', components=components,
        worst_case_bytes=sum(components.values()), fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
        log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    tracked = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK / name for name in tracked), DOC, KERNEL, IMAGE, SOURCE, SB, Path(load(SB)['binary']),
             Path(load(P419 / 'trial-plan.json')['observer_helper']), MAIN / 'tools/storage-budget.py',
             *(BASE / name for name in ('live-batch-admission.json','current-root-capture/result.json')),
             *(P419 / name for name in ('trial-plan.json','ready.json','execution/sustained-scanout.json')),
             *(P422 / name for name in ('trial-plan.json','capture-profile.json','storage-bound-422.json')),
             *(LAST / name for name in ('result.json','independent-restore.json','restored-capture/result.json'))]
    return phase.capture_tools.scoped_pins(BASE, files, KERNEL, IMAGE)


def freeze():
    return phase.shared.freeze(base=BASE, prior=P422, expected=expected_plan, validate=criteria,
                               storage_bound=storage, pin_inputs=pins, reserve=RESERVE)


def review():
    return phase.shared.review(base=BASE, doc=DOC, expected=expected_plan, validate=criteria,
                               storage_bound=storage, preparer=Path(__file__), reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=actions)
    print(actions[parser.parse_args().step]())
