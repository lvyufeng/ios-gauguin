#!/usr/bin/env python3
"""Stage the known six slots, exercise the live-shaped rollback, and freeze inputs."""

import argparse
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys

from core342_install import EXPECTED, BLOCK, sha as digest
from core342_slots import data_extents
from frame344_scope import BASE, DOC, HEADER, LOG_PATHS, MAIN, MANUAL, P343, POST_LOG_BYTES, RESERVE, WORK
from frame344_scope import expected_plan, load, require, sha


def module(name):
    spec = importlib.util.spec_from_file_location(name, WORK/'tools'/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def delta(base=BASE, prior=P343, *, trial='0344', header=HEADER, baseline=None, core_logical=None,
          sb_receipt=None, c4_receipt=None):
    baseline = baseline or MANUAL/'execution/restored-capture/result.json'
    previous = load(prior/'slot-delta/install-plan.json')
    source_trial = previous.get('trial', f'{int(trial)-1:04d}')
    snapshot_path = base/'slot-capture/result.json'
    snapshot = load(snapshot_path)
    require(snapshot['root_header_sha256'] == header and snapshot['baseline_sha256'] == sha(baseline),
            'slot files differ from the most recently restored baseline')
    new_receipts = {'core': load(base/'core-native/result.json'), 'admission': load(base/'edr-native/result.json')}
    if sb_receipt is not None:
        new_receipts['eagl'] = load(sb_receipt)
    if c4_receipt is not None:
        new_receipts['c4'] = load(c4_receipt)
    catalogs, images = {}, {}
    for name, path in EXPECTED.items():
        row = previous['rows'][name]
        fresh = snapshot['files'][path]
        require(row['path'] == path and (row['old_logical'], row['old_file_sha256'], row['old_data_sha256']) ==
                (fresh['logical'], fresh['sha256'], fresh['data_alloc_sha256']) and
                all(row[k] == fresh[k] for k in ('cnid','mode','data_block','data_blocks')),
                'owned slot changed: ' + name)
        allocated = (base/'slot-capture'/(name+'-old-data.bin')).read_bytes()
        catalog = (base/'slot-capture'/(name+'-old-catalog.bin')).read_bytes()
        require(digest(allocated) == fresh['data_alloc_sha256'] and digest(catalog) == fresh['catalog_sha256'],
                'old range digest differs: ' + name)
        extents = data_extents(dict(fresh,path=path))
        if len(extents) > 1:
            row['data_extents'] = extents
        else:
            row.pop('data_extents', None)
        if name in new_receipts:
            receipt = new_receipts[name]
            contents = Path(receipt['binary']).read_bytes()
            require(digest(contents) == receipt['binary_sha256'], 'signed candidate differs: ' + name)
        else:
            old_target = prior/'slot-delta'/(name+'-new-data.bin')
            require(sha(old_target) == row['new_data_sha256'], '0343 slot staging differs: ' + name)
            contents = old_target.read_bytes()[:row['new_logical']]
            require(digest(contents) == row['new_file_sha256'], '0343 slot digest differs: ' + name)
        if name == 'core' and core_logical is not None:
            row['new_logical'] = core_logical
        if name == 'eagl' and sb_receipt is not None:
            row['new_logical'] = len(contents)
        if name == 'c4' and c4_receipt is not None:
            require((fresh['data_blocks']-1)*BLOCK < len(contents) <= len(allocated),
                    'new C4 does not require all allocated blocks')
            row['new_logical'] = len(contents)
        require(len(contents) == row['new_logical'] <= len(allocated), 'new slot size differs: ' + name)
        block, field = fresh['catalog_block'], fresh['catalog_offset']
        before, target = catalogs.setdefault(block, (catalog, bytearray(catalog)))
        require(before == catalog and struct.unpack_from('>Q', before, field)[0] == row['old_logical'] and
                struct.unpack_from('>Q', target, field)[0] == row['old_logical'], 'owned catalog fields overlap')
        struct.pack_into('>Q', target, field, len(contents))
        images[name] = contents + allocated[len(contents):]
        row.update(catalog_block=block,catalog_offset=field,old_catalog_sha256=digest(before),
                   new_file_sha256=digest(contents),new_data_sha256=digest(images[name]))

    require(len(catalogs)==5 and sum(map(len,images.values()))==10_280_960,
            'six-slot install range or byte count differs')
    output = base/'slot-delta'
    output.mkdir()
    for name, row in previous['rows'].items():
        catalog = catalogs[row['catalog_block']][1]
        row['new_catalog_sha256'] = digest(catalog)
        (output/(name+'-new-catalog.bin')).write_bytes(catalog)
        (output/(name+'-new-data.bin')).write_bytes(images[name])
    install_ranges = len(catalogs) + sum(len(data_extents(row)) for row in previous['rows'].values())
    previous.update(trial=trial, root_header_sha256=header, capture_sha256=sha(snapshot_path),
                    changed_ranges=install_ranges,
                    admission_sha256=new_receipts['admission']['binary_sha256'],
                    core_sha256=new_receipts['core']['binary_sha256'],
                    admission_receipt_sha256=sha(base/'edr-native/result.json'),
                    core_receipt_sha256=sha(base/'core-native/result.json'))
    previous.pop('reuse_exact_0342_candidate_names', None)
    previous.pop('reuse_exact_0343_candidate_names', None)
    if sb_receipt is not None:
        previous.update(unchanged_337_SB=False,SB_sha256=new_receipts['eagl']['binary_sha256'],
                        SB_receipt_sha256=sha(sb_receipt))
    if c4_receipt is not None:
        previous.update(C4_sha256=new_receipts['c4']['binary_sha256'],C4_receipt_sha256=sha(c4_receipt))
    previous[f'reuse_exact_{source_trial}_candidate_names'] = sorted(set(EXPECTED)-set(new_receipts))
    save(output/'install-plan.json', previous)
    return dict(install_ranges=install_ranges, install_bytes=10_301_440)


def storage_bound(current):
    components = dict(load(P343/'storage-bound-343.json')['components'])
    observed_bytes = sum(current['files'][path]['bytes'] for path in LOG_PATHS)
    components.pop('three_full_captures')
    components.pop('four_allocated_log_tails')
    components.pop('runtime_comparison_and_optical_artifacts')
    components.update(post_capture_raw_logs=POST_LOG_BYTES, three_hash_manifests=3*1048576,
                      extracted_log_suffixes=POST_LOG_BYTES-observed_bytes,
                      frame_analysis_and_comparison=10_000_000)
    require(0 < observed_bytes <= POST_LOG_BYTES and sum(components.values()) <= RESERVE,
            'complete runtime batch exceeds reservation')
    return dict(state='bounded0344-runtime-batch', components=components, fresh_log_bytes=observed_bytes,
                worst_case_bytes=sum(components.values()), reserve_bytes=RESERVE,
                nonmatching_log_suffix_hardlinked=True)


def freeze():
    for name in ('ready.json','trial-plan.json','final-review.json','approval.json','execution',
                 'capture-profile.json','expected-baseline.json','storage-bound-344.json'):
        require(not (BASE/name).exists(), 'file already exists: '+name)
    plan = expected_plan()
    current = load(BASE/'current-root-capture/result.json')
    pristine = load(MANUAL/'execution/restored-capture/result.json')
    require(current['files'] == pristine['files'] and current['directories'] == pristine['directories'] and
            current['root_header_sha256'] == HEADER, 'fresh complete capture differs from the restore')
    model = load(BASE/'restore-model/result.json')
    require(model['all_model_IO_writes_memory_only'] and len(model['checks']) == 47 and
            model['all_restore_partial_write_points'] == 17, 'rollback tests incomplete')
    checks = load(BASE/'frame-host/result.json')
    require(checks['state']=='0344-frame-join-and-coverage-host-passed', 'frame analysis tests incomplete')
    bound = storage_bound(current)
    budget = json.loads(subprocess.check_output([sys.executable,str(MAIN/'tools/storage-budget.py'),
                                                 '--planned-bytes',str(RESERVE)], text=True, timeout=600))
    require(budget['admitted'] and budget['current_accounted_bytes']+RESERVE <= budget['limit_bytes'],
            'runtime reservation unavailable')
    profile = load(P343/'capture-profile.json')
    profile.update(out=str((BASE/'execution/fresh-before').relative_to(MAIN)), expected_header_sha256=HEADER)
    for name, value in (('trial-plan.json',plan),('capture-profile.json',profile),
                        ('expected-baseline.json',current),('storage-bound-344.json',bound),
                        ('storage-runtime-admission.json',budget)):
        save(BASE/name, value)

    previous = load(P343/'ready.json')
    pins = dict(previous['input_pins'])
    paths = [DOC, Path(__file__), P343/'ready.json', P343/'post-analysis-prefix-v1/result.json',
             P343/'post-analysis-prefix-v1/runtime343-comparison.json',
             P343/'post-analysis-prefix-v1/comparison-inputs/kernel-IO-identity-analysis.json',
             P343/'execution/core-wait-execution-analysis.json',
             MANUAL/'execution/result.json', MANUAL/'execution/independent-restore.json',
             MANUAL/'execution/restored-capture/result.json', WORK/'graphics/gauguin-program-io/0344-core-encoding.patch',
             WORK/'xnu/patches/0253-gauguin-scanout-frame-trace.patch', WORK/'xnu/patches/series',
             WORK/'tests/fixtures/core344_encoding.cpp', WORK/'tests/test_frame344_log.py']
    paths += [WORK/'tools'/name for name in ('frame344_scope.py','run-frame344-trial.py',
               'frame344_log.py','build-core344.py','check-core344.py','build-kernel344.py',
               'package-frame344.py','capture-core342-root.py','capture-sb-cadence-root.py','run-core342-trial.py',
               'compare-runtime343.py','check-core342-pipeline.py','review-frame344-trial.py')]
    paths += [BASE/name for name in ('trial-plan.json','expected-baseline.json','capture-profile.json',
               'storage-bound-344.json','storage-runtime-admission.json','core-native/result.json',
               'core-host-reviewed/result.json','frame-host/result.json','frame344-image.json',
               'edr-native/result.json','cleanup-plan.json','cleanup-result.json')]
    paths += [Path(plan['image']), Path(load(BASE/'edr-native/result.json')['binary']),
              Path(load(BASE/'core-native/result.json')['binary']), Path(load(BASE/'frame344-image.json')['kernel_manifest'])]
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        paths += [p for p in (BASE/folder).rglob('*') if p.is_file()]
    for path in paths:
        digest_value = sha(path)
        require(pins.setdefault(str(path),digest_value) == digest_value, 'shared trial pin differs')
    for path, checksum in pins.items():
        require(sha(path) == checksum, 'frozen input changed: ' + path)
    ready = dict(state='ready-frame344-one-shot', trial_plan_sha256=sha(BASE/'trial-plan.json'),
                 install_plan_sha256=plan['install_plan_sha256'], image_sha256=plan['image_sha256'],
                 pin_count=len(pins), input_pins=pins, approval_pending=True, device_writes=0, boot_attempts=0)
    save(BASE/'ready.json',ready)
    return dict(pin_count=len(pins), reserve=RESERVE,worst_case=bound['worst_case_bytes'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=('delta','model','freeze'))
    args = parser.parse_args()
    if args.stage == 'delta':
        record = delta()
    elif args.stage == 'model':
        record = module('check-core342-rollback').check(BASE, BASE/'restore-model',trial='0344')
        record = {k:v for k,v in record.items() if k != 'input_pins'}
    else:
        record = freeze()
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
