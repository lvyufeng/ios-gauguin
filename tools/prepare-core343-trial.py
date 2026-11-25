#!/usr/bin/env python3
"""Prepare or freeze the 0343 trial. Only the root stage reads the phone."""

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

from core343_scope import (BASE, DOC, EDR, HEADER, IDENTITY, IMAGE, MAIN, P342,
                           REFERENCE, REF_DECODE, ROOT_FILES, STORAGE_RESERVE,
                           WORK, expected_plan, load, require, sha)
from core342_install import BLOCK, EXPECTED, sha as digest


def tool(name):
    spec = importlib.util.spec_from_file_location(name, WORK / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def storage():
    answer = subprocess.run([sys.executable, str(MAIN / 'tools/storage-budget.py'),
                             '--planned-bytes', str(STORAGE_RESERVE)],
                            capture_output=True, text=True, timeout=600, check=True)
    budget = json.loads(answer.stdout)
    require(budget['admitted'] is True
            and budget['current_accounted_bytes'] + STORAGE_RESERVE <= budget['limit_bytes'],
            'complete 0343 execution and analysis do not fit the storage budget')
    return budget


def capture_root():
    prior = P342 / 'execution/restored-capture/result.json'
    pristine = load(prior)
    require(pristine['root_header_sha256'] == HEADER, '0342 restored header differs')
    if not (BASE / 'slot-capture/result.json').exists():
        subprocess.run([sys.executable, str(WORK / 'tools/capture-sb-cadence-slot.py'),
                        '--baseline', str(prior), '--out', str(BASE / 'slot-capture')],
                       check=True, timeout=300)
    require(load(BASE / 'slot-capture/result.json')['baseline_sha256'] == sha(prior),
            'live slots were compared with a different baseline')
    profile = load(P342 / 'capture-profile.json')
    profile.update(out=str(BASE / 'current-root-capture'), phase='before-boot', expected_header_sha256=HEADER)
    actual_path = BASE / 'current-root-capture/result.json'
    actual = (load(actual_path) if actual_path.exists()
              else tool('capture-core342-root').capture(profile, save_files=False))
    require(actual['root_header_sha256'] == HEADER and actual['files'] == pristine['files']
            and actual['directories'] == pristine['directories'], 'live 31-file baseline changed')
    path = BASE / 'metadata-snapshot/result.json'
    meta = (load(path) if path.exists()
            else tool('capture-core342-metadata').capture(path.parent, HEADER, trial='0343'))
    require(meta['root_header_sha256'] == HEADER and meta['state'].startswith('readonly0343-')
            and meta['device_writes'] == meta['device_boots'] == 0, 'wrong metadata snapshot')
    return dict(files=len(actual['files']), directories=len(actual['directories']),
                metadata_bytes=meta['compressed_bytes'], device_writes=0, device_boots=0)


def prepare_delta():
    previous = load(P342 / 'slot-delta/install-plan.json')
    capture_path = BASE / 'slot-capture/result.json'
    capture = load(capture_path)
    require(capture['root_header_sha256'] == HEADER and set(previous['rows']) == set(EXPECTED),
            'slot capture or parent delta differs')
    helper = load(BASE / 'edr-native/result.json')
    binary = Path(helper['binary'])
    require(helper['kernel_identity'] == IDENTITY and helper['binary_sha256'] == EDR == sha(binary),
            'EDR helper is not the reviewed 0343 product')
    catalogs, images = {}, {}
    for name, path in EXPECTED.items():
        row = previous['rows'][name]
        fresh = capture['files'][path]
        require(row['path'] == path and (row['old_logical'], row['old_file_sha256'], row['old_data_sha256'])
                == (fresh['logical'], fresh['sha256'], fresh['data_alloc_sha256'])
                and all(row[k] == fresh[k] for k in ('cnid', 'mode', 'data_block', 'data_blocks',
                                                    'catalog_block', 'catalog_offset')),
                'live file content or geometry differs: ' + name)
        old = BASE / 'slot-capture' / (name + '-old-data.bin')
        cat = BASE / 'slot-capture' / (name + '-old-catalog.bin')
        require(sha(old) == row['old_data_sha256'] and sha(cat) == fresh['catalog_sha256'],
                'live slot artifacts differ: ' + name)
        if name == 'admission':
            data = binary.read_bytes()
        else:
            target = P342 / 'slot-delta' / (name + '-new-data.bin')
            require(sha(target) == row['new_data_sha256'], '0342 candidate changed: ' + name)
            data = target.read_bytes()[:row['new_logical']]
            require(digest(data) == row['new_file_sha256'], '0342 logical candidate changed: ' + name)
        require(len(data) == row['new_logical'] <= row['data_blocks'] * BLOCK,
                '0343 needs a different allocation: ' + name)
        images[name] = data + old.read_bytes()[len(data):]
        row.update(new_file_sha256=digest(data), new_data_sha256=digest(images[name]),
                   old_catalog_sha256=fresh['catalog_sha256'])
        block, at = row['catalog_block'], row['catalog_offset']
        catalog = cat.read_bytes()
        group = catalogs.setdefault(block, [catalog, bytearray(catalog), set()])
        require(len(catalog) == BLOCK and catalog == group[0]
                and all(abs(at - other) >= 8 for other in group[2])
                and struct.unpack_from('>Q', catalog, at)[0] == row['old_logical'],
                'live catalog preimages/locations differ: ' + name)
        struct.pack_into('>Q', group[1], at, len(data))
        group[2].add(at)

    require(len(catalogs) == 5 and len(catalogs) + len(images) == previous['changed_ranges'] == 11
            and sum(map(len, images.values())) == 10280960
            and all(before != after for before, after, _ in catalogs.values()),
            '0343 install requires a different write bound')
    out = BASE / 'slot-delta'
    out.mkdir()
    for name, row in previous['rows'].items():
        catalog = catalogs[row['catalog_block']][1]
        row['new_catalog_sha256'] = digest(catalog)
        (out / (name + '-new-catalog.bin')).write_bytes(catalog)
        (out / (name + '-new-data.bin')).write_bytes(images[name])
    previous.pop('new_342_kernel_and_helper')
    previous.update(trial='0343', root_header_sha256=HEADER, capture_sha256=sha(capture_path),
                    admission_sha256=EDR, admission_receipt_sha256=sha(BASE / 'edr-native/result.json'),
                    new_343_kernel_and_helper=True, reuse_exact_0342_candidate_names=sorted(set(EXPECTED)-{'admission'}))
    save(out / 'install-plan.json', previous)
    return dict(changed_ranges=11, install_bytes=previous['install_write_bytes'],
                restore_max_bytes=previous['restore_max_write_bytes'])


def freeze():
    for leaf in ('approval.json', 'execution', 'trial-plan.json', 'ready.json', 'final-review.json',
                 'storage-runtime-admission-343.json', *ROOT_FILES):
        require(not (BASE / leaf).exists(), 'freeze output or execution already exists: ' + leaf)
    plan = expected_plan()
    model = load(BASE / 'restore-model-343/result.json')
    require(len(model['checks']) == 47 and model['all_restore_partial_write_points'] >= 17
            and model['policy_maximum_ranges'] == 18 and model['frozen_restore_limit_bytes'] == 10330112
            and model['all_model_IO_writes_memory_only'], 'restore model incomplete')
    require(load(BASE / 'current-root-capture/result.json')['root_header_sha256'] == HEADER,
            'current root snapshot missing')
    budget = storage()
    bound = load(P342 / 'storage-bound.json')
    require(sum(bound['components'].values()) == bound['worst_case_bytes'] == 959827600,
            '0342 runtime bound changed')
    bound['components'].update(runtime_comparison_and_optical_artifacts=10000000)
    bound.update(state='bounded0343-complete-runtime-batch',reserve_bytes=STORAGE_RESERVE,
                 worst_case_bytes=sum(bound['components'].values()),
                 optical_input_streamed_from_user_original=True)
    require(bound['worst_case_bytes'] <= STORAGE_RESERVE, '0343 runtime exceeds admitted reserve')
    profile = load(P342 / 'capture-profile.json')
    profile.update(out=str((BASE / 'execution/fresh-before').relative_to(MAIN)), expected_header_sha256=HEADER)
    for name, value in zip(ROOT_FILES, [load(BASE / 'current-root-capture/result.json'), profile, bound]):
        save(BASE / name, value)
    save(BASE / 'storage-runtime-admission-343.json', budget)
    save(BASE / 'trial-plan.json', plan)

    prior = load(P342 / 'ready.json')
    require(prior['pin_count'] == 28885 == len(prior['input_pins']), 'wrong 0342 parent pin set')
    pins = dict(prior['input_pins'])

    def pin(path, h=None):
        name = str(Path(path).resolve())
        digest = h if h is not None else sha(name)
        require(name not in pins or pins[name] == digest, 'conflicting frozen input: ' + name)
        pins[name] = digest

    for path in (P342/'ready.json', P342/'trial-plan.json', P342/'execution/result.json',
                 P342/'execution/independent-restore.json', P342/'execution/restored-capture/result.json',
                 MAIN/'tools/storage-budget.py', DOC, BASE/'trial-plan.json', BASE/'runtime343-image.json',
                 BASE/'runtime343-review.json', BASE/'kernel-native/build-manifest.json',
                 BASE/'runtime343-image.img', BASE/'edr-native/result.json',
                 BASE/'edr-native/libGauguinEAGLAdmission.dylib', BASE/'storage-runtime-admission-343.json',
                 WORK/'xnu/patches/0252-gauguin-share-async-ring-barrier-guards.patch', *[BASE/f for f in ROOT_FILES],
                 *[REFERENCE/f for f in REF_DECODE], Path(plan['observer_helper'])):
        pin(path)
    for receipt, key in (('kernel-native/build-manifest.json', 'input_pins'), ('edr-native/result.json', 'pins'),
                         ('runtime343-image.json', 'input_pins'), ('restore-model-343/result.json', 'input_pins')):
        for name, value in load(BASE / receipt)[key].items():
            pin(name, value['sha256'] if isinstance(value, dict) else value)
    for folder in ('current-root-capture', 'slot-capture', 'slot-delta', 'metadata-snapshot',
                   'restore-model-343', 'pipeline-343'):
        for path in (BASE / folder).rglob('*'):
            if path.is_file():
                pin(path)
    for path in (WORK / 'tools').glob('*'):
        if path.suffix in ('.py', '.sh'):
            pin(path)
    for path, digest in pins.items():
        require(sha(path) == digest, 'changed input: ' + path)
    require(pins[plan['image']] == IMAGE, '0343 image was not pinned')
    ready = dict(state='ready-core343-one-shot', trial_plan_sha256=pins[str(BASE/'trial-plan.json')],
                 install_plan_sha256=plan['install_plan_sha256'], image_sha256=IMAGE,
                 root_header_sha256=HEADER, parent_342_pins_preserved=len(prior['input_pins']),
                 pin_count=len(pins), input_pins=dict(sorted(pins.items())),
                 approval_pending=True, device_writes=0, boot_attempts=0)
    save(BASE / 'ready.json', ready)
    return {k: v for k, v in ready.items() if k != 'input_pins'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('root', 'delta', 'model', 'freeze'))
    stage = parser.parse_args().stage
    if stage == 'model':
        result = tool('check-core342-rollback').check(BASE, BASE/'restore-model-343', trial='0343')
        result.pop('input_pins')
    else:
        result = {'root': capture_root, 'delta': prepare_delta, 'freeze': freeze}[stage]()
    print(json.dumps(result, indent=2))
