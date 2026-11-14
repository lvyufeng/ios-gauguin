#!/usr/bin/env python3
"""Read only: pin four existing HFSX files for a future SB observer trial."""

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path


MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
BLOCK = 4096
VOLUME = 17179869184
FILES = {
    'eagl': ('/usr/local/lib/gauguin/libGauguinEAGL.dylib', 33261),
    'job': ('/System/Library/LaunchDaemons/com.apple.SpringBoard.plist', 33188),
    'cache': ('/System/Library/xpc/launchd.plist', 33188),
    'c4': ('/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop', 33261),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--baseline', type=Path,
                    default=MAIN/'research/tmp/gauguin-sb-spawn-worktree-20261114/research/tmp/sb-spawn-314/execution/restored-capture/result.json')
    ap.add_argument('--springboard-capture', type=Path,
                    default=WORK/'research/tmp/sb-stack-315/initial-capture/result.json')
    args = ap.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    baseline_raw = args.baseline.read_bytes()
    baseline = json.loads(baseline_raw)
    job_capture_raw = args.springboard_capture.read_bytes()
    job_capture = json.loads(job_capture_raw)
    assert baseline['state'] == 'captured-readonly-owned-root-files'
    assert job_capture['state'] == 'readonly-SpringBoard-current-capture'
    assert job_capture['root_header_sha256'] == baseline['root_header_sha256']
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
            prior = ({'present':True, **job_capture['files'][path]} if name == 'job'
                     else baseline['files'][path])
            assert prior['present'] and prior['uid'] == prior['gid'] == 0 and prior['mode'] == mode
            row = hfs.paths[path]
            fork = row['data']
            assert row['type'] == 2 and not row['flags'] & 0x20
            assert (row['uid'], row['gid'], row['mode']) == (0, 0, mode)
            assert fork['logical'] == prior['bytes'] and fork == prior['fork']
            assert len(fork['extents']) == 1
            logical = hfs.content(path)
            assert len(logical) == prior['bytes'] and sha(logical) == prior['sha256']
            start, blocks = fork['extents'][0]
            assert start > 0 and start+blocks < VOLUME//BLOCK
            allocated = io.read(start*BLOCK, blocks*BLOCK)
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
            blobs[name] = (allocated, catalog)
    finally:
        hfs.close()
    assert len({row['catalog_block'] for row in rows.values()}) == len(rows)
    data_spans = [(row['data_block'], row['data_block']+row['data_blocks']) for row in rows.values()]
    assert all(a[1] <= b[0] or b[1] <= a[0] for i, a in enumerate(data_spans)
               for b in data_spans[i+1:])
    assert all(not any(a <= row['catalog_block'] < b for a, b in data_spans)
               for row in rows.values())
    assert io.read(0, BLOCK) == header
    out.mkdir(parents=True)
    for name, (allocated, catalog) in blobs.items():
        with (out/(name+'-old-data.bin')).open('xb') as stream:
            stream.write(allocated)
        with (out/(name+'-old-catalog.bin')).open('xb') as stream:
            stream.write(catalog)
    result = {'state': 'readonly-four-file-cadence-capture',
              'root_header_sha256': sha(header), 'baseline_sha256': sha(baseline_raw),
              'springboard_capture_sha256': sha(job_capture_raw),
              'files': rows, 'read_only_catalog_bytes': remote.bytes,
              'device_writes': 0, 'device_boots': 0}
    with (out/'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
