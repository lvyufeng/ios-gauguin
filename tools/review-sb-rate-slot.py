#!/usr/bin/env python3
"""Read-only virtual HFSX replay of the prepared SpringBoard observer delta."""

import argparse
import hashlib
import json
import plistlib
import struct
import sys
from pathlib import Path


MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
BLOCK = 4096
VOLUME = 17179869184


def sha(data):
    return hashlib.sha256(data).hexdigest()


class OverlayIO:
    """Forward reads to an unmodified phone, patching six ranges in memory."""
    def __init__(self, base, ranges):
        self.base, self.ranges = base, ranges

    def read(self, offset, count):
        raw = bytearray(self.base.read(offset, count))
        for start, image in self.ranges:
            end = start+len(image)
            lo, hi = max(offset,start), min(offset+count,end)
            if lo < hi:
                raw[lo-offset:hi-offset] = image[lo-start:hi-start]
        return bytes(raw)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--capture',type=Path,required=True)
    ap.add_argument('--delta',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    capture_dir, delta_dir = args.capture.resolve(), args.delta.resolve()
    out = args.out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    capture_raw = (capture_dir/'result.json').read_bytes()
    capture = json.loads(capture_raw)
    plan_raw = (delta_dir/'install-plan.json').read_bytes()
    plan = json.loads(plan_raw)
    assert capture['state'] == 'readonly-existing-slot-capture'
    assert plan['state'] == 'prepared-offline-existing-slot-SpringBoard-observer-delta'
    assert plan['capture_sha256'] == sha(capture_raw)
    assert plan['root_header_sha256'] == capture['root_header_sha256']
    assert plan['changed_ranges'] == 6 and plan['no_new_allocation']
    sys.path[:0] = [str(MAIN/'research/tmp/dsh-0175'),
                    str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote

    io = RecoveryIO()
    ident = io.identity()
    assert ident['state'] == 'recovery' and ident['product'] == 'gauguin'
    assert ident['unmounted'] and ident['no_holders']
    assert sha(io.read(0,BLOCK)) == plan['root_header_sha256']
    ranges = []
    for name, row in plan['rows'].items():
        prior = capture['files'][row['path']]
        assert row['cnid'] == prior['cnid'] and row['old_logical'] == prior['logical']
        assert (row['data_block'],row['data_blocks'],row['catalog_block'],row['catalog_offset']) == (
            prior['data_block'],prior['data_blocks'],prior['catalog_block'],prior['catalog_offset'])
        old_data = (capture_dir/(name+'-old-data.bin')).read_bytes()
        old_cat = (capture_dir/(name+'-old-catalog.bin')).read_bytes()
        new_data = (delta_dir/(name+'-new-data.bin')).read_bytes()
        new_cat = (delta_dir/(name+'-new-catalog.bin')).read_bytes()
        assert len(old_data) == len(new_data) == row['data_blocks']*BLOCK
        assert len(old_cat) == len(new_cat) == BLOCK
        for label, blob in [('old_data',old_data),('old_catalog',old_cat),
                            ('new_data',new_data),('new_catalog',new_cat)]:
            assert sha(blob) == row[label+'_sha256']
        at = row['catalog_offset']
        assert old_cat[:at] == new_cat[:at] and old_cat[at+8:] == new_cat[at+8:]
        assert old_cat[at:at+8] == struct.pack('>Q',row['old_logical'])
        assert new_cat[at:at+8] == struct.pack('>Q',row['new_logical'])
        assert sha(new_data[:row['new_logical']]) == row['new_file_sha256']
        assert io.read(row['data_block']*BLOCK,len(old_data)) == old_data
        assert io.read(row['catalog_block']*BLOCK,BLOCK) == old_cat
        ranges.extend([(row['data_block']*BLOCK,new_data),(row['catalog_block']*BLOCK,new_cat)])
    assert sum(len(image) for _,image in ranges) == plan['install_write_bytes']
    remote = Remote(OverlayIO(io,ranges))
    hfs = HFS(stream=remote,size=VOLUME)
    contents = {}
    try:
        for name, row in plan['rows'].items():
            file = hfs.paths[row['path']]
            assert file['id'] == row['cnid'] and file['type'] == 2
            assert file['data']['logical'] == row['new_logical']
            assert file['data']['blocks'] == row['data_blocks']
            assert file['data']['extents'] == [[row['data_block'],row['data_blocks']]]
            payload = hfs.content(row['path'])
            assert len(payload) == row['new_logical'] and sha(payload) == row['new_file_sha256']
            contents[name] = payload
    finally:
        hfs.close()
    job = plistlib.loads(contents['job'])
    cache = plistlib.loads(contents['cache'])
    path = '/System/Library/LaunchDaemons/com.apple.SpringBoard.plist'
    library = '/usr/local/lib/gauguin/libGauguinEAGL.dylib'
    assert job['EnvironmentVariables']['DYLD_INSERT_LIBRARIES'] == library
    assert cache['LaunchDaemons'][path]['EnvironmentVariables']['DYLD_INSERT_LIBRARIES'] == library
    assert len(cache['LaunchDaemons']) == 531
    assert sha(io.read(0,BLOCK)) == plan['root_header_sha256']
    review = {'state': 'passed-readonly-virtual-HFSX-SpringBoard-slot-replay',
              'plan_sha256': sha(plan_raw), 'root_header_sha256': plan['root_header_sha256'],
              'read_only_overlay_bytes': remote.bytes,
              'candidate_files_seen_by_HFSX': len(contents),
              'springboard_library_path': library,
              'device_writes': 0, 'device_boots': 0,
              'runtime_dyld_AMFI_qualified': False,
              'physical_fps_measured': False}
    with out.open('x') as stream:
        json.dump(review,stream,indent=2);stream.write('\n')
    print(json.dumps(review,indent=2))


if __name__ == '__main__':
    main()
