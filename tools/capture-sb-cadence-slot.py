#!/usr/bin/env python3
"""Read only: pin six existing HFSX files for the EDR default-path trial."""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from core342_slots import data_extents, read_allocation


MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
BLOCK = 4096
VOLUME = 17179869184
FILES = {
    'eagl': ('/usr/local/lib/gauguin/libGauguinEAGL.dylib', 33261),
    'cache': ('/System/Library/xpc/launchd.plist', 33188),
    'c4': ('/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop', 33261),
    'admission': ('/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib', 33261),
    'backboard': ('/System/Library/LaunchDaemons/com.apple.backboardd.plist', 33188),
    'core': ('/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib', 33261),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--baseline', type=Path,
                    default=MAIN/'research/tmp/gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336/execution/restored-capture/result.json')
    ap.add_argument('--reuse-data-from', type=Path,
                    help='Use byte-identical allocated data from a saved slot capture')
    args = ap.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    baseline_raw = args.baseline.read_bytes()
    baseline = json.loads(baseline_raw)
    assert baseline['state'] == 'captured-readonly-owned-root-files'
    assert all(path in baseline['files'] for path, _mode in FILES.values())
    sys.path[:0] = [str(MAIN/'research/tmp/dsh-0175'),
                    str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote

    io = RecoveryIO()
    identity = io.identity()
    assert identity['state'] == 'recovery' and identity['product'] == 'gauguin'
    assert identity['unmounted'] and identity['no_holders']
    assert identity['partition_bytes'] == 114919714816
    header = io.read(0, BLOCK)
    assert sha(header) == baseline['root_header_sha256']
    remote = Remote(io)
    hfs = HFS(stream=remote, size=VOLUME)
    rows = {}
    blobs = {}
    try:
        for name, (path, mode) in FILES.items():
            prior = baseline['files'][path]
            assert prior['present'] and prior['uid'] == prior['gid'] == 0 and prior['mode'] == mode
            row = hfs.paths[path]
            fork = row['data']
            assert row['type'] == 2 and not row['flags'] & 0x20
            assert (row['uid'], row['gid'], row['mode']) == (0, 0, mode)
            assert fork['logical'] == prior['bytes'] and fork == prior['fork']
            logical = hfs.content(path)
            assert len(logical) == prior['bytes'] and sha(logical) == prior['sha256']
            start = fork['extents'][0][0]
            blocks = fork['blocks']
            extents = data_extents(dict(path=path,data_block=start,data_blocks=blocks,data_extents=fork['extents']))
            allocated = read_allocation(io, extents)
            assert allocated[:len(logical)] == logical
            spans = list(hfs.spans(hfs.catalog, row['catalog_bsd_offset']+56, 8))
            assert len(spans) == 1 and spans[0][1] == 8
            catblock, at = divmod(spans[0][0], BLOCK)
            assert 0 < catblock < VOLUME//BLOCK-1 and at+8 <= BLOCK
            catalog = io.read(catblock*BLOCK, BLOCK)
            assert catalog[at:at+8] == struct.pack('>Q', len(logical))
            rows[path] = {'cnid': row['id'], 'mode': mode, 'logical': len(logical),
                          'sha256': sha(logical), 'data_block': start,
                          'data_blocks': blocks, 'data_alloc_sha256': sha(allocated),
                          'catalog_block': catblock, 'catalog_offset': at,
                          'catalog_sha256': sha(catalog)}
            if len(extents) > 1:
                rows[path]['data_extents'] = extents
            blobs[name] = (allocated, catalog)
    finally:
        hfs.close()
    groups = {}
    for path, row in rows.items():
        group = groups.setdefault(row['catalog_block'], [])
        assert all(abs(row['catalog_offset'] - rows[other]['catalog_offset']) >= 8
                   for other in group)
        group.append(path)
    assert len(rows) == 6 and 4 <= len(groups) <= 6
    data_spans = [(start, start+count) for path,row in rows.items()
                  for start,count in data_extents(dict(row,path=path))]
    assert all(a[1] <= b[0] or b[1] <= a[0] for i, a in enumerate(data_spans)
               for b in data_spans[i+1:])
    assert all(not any(a <= row['catalog_block'] < b for a, b in data_spans)
               for row in rows.values())
    assert io.read(0, BLOCK) == header
    reuse = {}
    if args.reuse_data_from:
        source = args.reuse_data_from.resolve(strict=True)
        assert source.is_relative_to(MAIN)
        for name, (allocated, _) in blobs.items():
            saved = (source/(name+'-old-data.bin')).resolve(strict=True)
            assert saved.is_relative_to(MAIN)
            if saved.read_bytes() != allocated:
                raise ValueError('fresh allocated slot differs from saved bytes: '+name)
            reuse[name] = saved

    out.mkdir(parents=True)
    for name, (allocated, catalog) in blobs.items():
        path = out/(name+'-old-data.bin')
        if name in reuse:
            path.symlink_to(reuse[name])
        else:
            with path.open('xb') as stream:
                stream.write(allocated)
        with (out/(name+'-old-catalog.bin')).open('xb') as stream:
            stream.write(catalog)
    result = {'state': 'readonly-six-file-Q337-capture',
              'root_header_sha256': sha(header), 'baseline_sha256': sha(baseline_raw),
              'files': rows, 'catalog_groups': groups, 'read_only_catalog_bytes': remote.bytes,
              'device_writes': 0, 'device_boots': 0}
    if reuse:
        result['reused_original_data'] = {name:str(path) for name,path in reuse.items()}
    with (out/'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
