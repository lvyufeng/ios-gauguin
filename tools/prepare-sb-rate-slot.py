#!/usr/bin/env python3
"""Offline six-range HFSX delta for a future, separately approved SB trial."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

WORK = Path(__file__).resolve().parents[1]
BLOCK = 4096
SLOT = '/usr/local/lib/gauguin/libGauguinEAGL.dylib'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    raw = path.read_bytes()
    return json.loads(raw), sha(raw)


def prepare(capture_dir, binary_receipt, launch_dir, out):
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    capture, capture_sha = load(capture_dir/'result.json')
    binary, binary_sha = load(binary_receipt)
    launch, launch_sha = load(launch_dir/'result.json')
    assert capture['state'] == 'readonly-existing-slot-capture'
    assert binary['state'] == 'native-iOS16-readonly-SpringBoard-rate-trace-not-device-qualified'
    assert binary['install_name'] == SLOT and launch['library_path'] == SLOT
    assert launch['state'] == 'offline-SpringBoard-rate-launch-candidate-not-installed'
    assert launch['root_header_sha256'] == capture['root_header_sha256']
    assert launch['binary_sha256'] == binary['sha256']
    assert launch['unrelated_jobs_unchanged'] == 530 and launch['reverse_transform_exact']
    assert not launch['new_dylib_file_allocation_unplanned']
    candidates = {
        'eagl': (SLOT, Path(binary['binary'])),
        'job': ('/System/Library/LaunchDaemons/com.apple.SpringBoard.plist',
                launch_dir/'springboard-job.plist'),
        'cache': ('/System/Library/xpc/launchd.plist', launch_dir/'launchd.plist'),
    }
    rows, blobs = {}, {}
    for name, (path, candidate) in candidates.items():
        prior = capture['files'][path]
        old_data = (capture_dir/(name+'-old-data.bin')).read_bytes()
        old_cat = (capture_dir/(name+'-old-catalog.bin')).read_bytes()
        new_file = candidate.read_bytes()
        old_len = prior['logical']
        new_len = len(new_file)
        assert prior['data_blocks']*BLOCK == len(old_data) and len(old_cat) == BLOCK
        assert sha(old_data) == prior['data_alloc_sha256']
        assert sha(old_data[:old_len]) == prior['sha256']
        assert sha(old_cat) == prior['catalog_sha256']
        assert old_cat[prior['catalog_offset']:prior['catalog_offset']+8] == struct.pack('>Q', old_len)
        assert new_len <= len(old_data)
        if name == 'eagl':
            assert sha(new_file) == binary['sha256'] and new_len < old_len
        else:
            item = launch['changed_files'][path]
            assert item['old_bytes'] == old_len and item['old_sha256'] == prior['sha256']
            assert item['new_bytes'] == new_len and item['new_sha256'] == sha(new_file)
            assert item['extent_bytes'] == len(old_data)
        at = prior['catalog_offset']
        new_data = new_file+old_data[new_len:]
        new_cat = old_cat[:at]+struct.pack('>Q',new_len)+old_cat[at+8:]
        assert len(new_data) == len(old_data) and len(new_cat) == BLOCK
        assert new_cat[:at] == old_cat[:at] and new_cat[at+8:] == old_cat[at+8:]
        rows[name] = {'path': path, 'cnid': prior['cnid'], 'mode': prior['mode'],
                      'old_logical': old_len, 'new_logical': new_len,
                      'data_block': prior['data_block'], 'data_blocks': prior['data_blocks'],
                      'catalog_block': prior['catalog_block'], 'catalog_offset': at,
                      'old_file_sha256': prior['sha256'], 'new_file_sha256': sha(new_file),
                      'old_data_sha256': sha(old_data), 'new_data_sha256': sha(new_data),
                      'old_catalog_sha256': sha(old_cat), 'new_catalog_sha256': sha(new_cat)}
        blobs[name] = (new_data, new_cat)
    spans = [(row['data_block'],row['data_block']+row['data_blocks']) for row in rows.values()]
    assert len({row['catalog_block'] for row in rows.values()}) == 3
    assert all(a[1] <= b[0] or b[1] <= a[0] for i,a in enumerate(spans) for b in spans[i+1:])
    assert all(not any(a <= row['catalog_block'] < b for a,b in spans) for row in rows.values())
    out.mkdir(parents=True)
    for name,(new_data,new_cat) in blobs.items():
        with (out/(name+'-new-data.bin')).open('xb') as stream:stream.write(new_data)
        with (out/(name+'-new-catalog.bin')).open('xb') as stream:stream.write(new_cat)
    changed = sum(row['data_blocks']*BLOCK+BLOCK for row in rows.values())
    plan = {'state': 'prepared-offline-existing-slot-SpringBoard-observer-delta',
            'root_header_sha256': capture['root_header_sha256'],
            'capture_sha256': capture_sha, 'binary_receipt_sha256': binary_sha,
            'launch_receipt_sha256': launch_sha,
            'rows': rows, 'changed_ranges': 6, 'install_write_bytes': changed,
            'normal_install_restore_userdata_bytes': changed*2,
            'no_new_allocation': True, 'device_writes': 0, 'device_boots': 0,
            'device_qualified': False}
    with (out/'install-plan.json').open('x') as stream:
        json.dump(plan,stream,indent=2);stream.write('\n')
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',type=Path,required=True)
    ap.add_argument('--binary-receipt',type=Path,required=True)
    ap.add_argument('--launch',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    print(json.dumps(prepare(args.capture.resolve(),args.binary_receipt.resolve(),
                             args.launch.resolve(),args.out.resolve()),indent=2))


if __name__ == '__main__':
    main()
