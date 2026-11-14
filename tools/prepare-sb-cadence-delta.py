#!/usr/bin/env python3
"""Offline four-file delta: C4, observer slot and two SpringBoard launch jobs."""
import argparse
import hashlib
import json
import plistlib
import struct
from pathlib import Path
from sb_cadence_launch import transform, JOB, CACHE, REUSE_SLOT


WORK = Path(__file__).resolve().parents[1]
C4 = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
C4_SHA = '560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5'
BLOCK = 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(capture_dir, binary_receipt, c4, out):
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    raw = (capture_dir/'result.json').read_bytes()
    capture = json.loads(raw)
    binary_raw = binary_receipt.read_bytes()
    binary = json.loads(binary_raw)
    assert capture['state'] == 'readonly-four-file-cadence-capture'
    assert binary['state'] == 'native-iOS16-SpringBoard-timing-stack-probe-not-device-qualified'
    assert binary['main_thread_sampling'] and binary['maximum_samples']==64 and binary['maximum_stack_frames']==16
    assert binary['install_name'] == REUSE_SLOT
    observer = Path(binary['binary']).read_bytes()
    assert sha(observer) == binary['sha256']
    frontend = c4.read_bytes()
    assert sha(frontend) == C4_SHA
    originals = {}
    for name,path in [('job',JOB),('cache',CACHE)]:
        row = capture['files'][path]
        data = (capture_dir/(name+'-old-data.bin')).read_bytes()[:row['logical']]
        assert sha(data) == row['sha256']
        originals[name] = plistlib.loads(data)
    job,cache = transform(originals['job'],originals['cache'],REUSE_SLOT)
    candidates = {
        'eagl':(REUSE_SLOT,observer),
        'job':(JOB,plistlib.dumps(job,fmt=plistlib.FMT_BINARY,sort_keys=False)),
        'cache':(CACHE,plistlib.dumps(cache,fmt=plistlib.FMT_BINARY,sort_keys=False)),
        'c4':(C4,frontend),
    }
    rows,blobs = {},{}
    for name,(path,new_file) in candidates.items():
        prior = capture['files'][path]
        old_data = (capture_dir/(name+'-old-data.bin')).read_bytes()
        old_cat = (capture_dir/(name+'-old-catalog.bin')).read_bytes()
        old_len,new_len = prior['logical'],len(new_file)
        at = prior['catalog_offset']
        assert prior['data_blocks']*BLOCK == len(old_data) and len(old_cat) == BLOCK
        assert sha(old_data) == prior['data_alloc_sha256']
        assert sha(old_data[:old_len]) == prior['sha256']
        assert sha(old_cat) == prior['catalog_sha256']
        assert 0<=at<=BLOCK-8 and old_cat[at:at+8] == struct.pack('>Q',old_len)
        assert 0<new_len<=len(old_data) and old_len != new_len
        new_data = new_file+old_data[new_len:]
        new_cat = old_cat[:at]+struct.pack('>Q',new_len)+old_cat[at+8:]
        rows[name] = dict(path=path,cnid=prior['cnid'],mode=prior['mode'],
            old_logical=old_len,new_logical=new_len,data_block=prior['data_block'],
            data_blocks=prior['data_blocks'],catalog_block=prior['catalog_block'],
            catalog_offset=at,old_file_sha256=prior['sha256'],new_file_sha256=sha(new_file),
            old_data_sha256=sha(old_data),new_data_sha256=sha(new_data),
            old_catalog_sha256=sha(old_cat),new_catalog_sha256=sha(new_cat))
        blobs[name] = new_data,new_cat
    spans = [(r['data_block'],r['data_block']+r['data_blocks']) for r in rows.values()]
    # Refuse an initial shared leaf. Postboot restoration resolves and groups
    # current leaves, preserving all unrelated bytes even after catalog growth.
    assert len({r['catalog_block'] for r in rows.values()}) == 4
    assert all(a[1]<=b[0] or b[1]<=a[0] for i,a in enumerate(spans) for b in spans[i+1:])
    assert all(not any(a<=r['catalog_block']<b for a,b in spans) for r in rows.values())
    changed = sum(r['data_blocks']*BLOCK+BLOCK for r in rows.values())
    assert changed == 1814528
    out.mkdir(parents=True)
    for name,(data,cat) in blobs.items():
        (out/(name+'-new-data.bin')).write_bytes(data)
        (out/(name+'-new-catalog.bin')).write_bytes(cat)
    plan = dict(state='prepared-four-file-SpringBoard-cadence-delta',
        root_header_sha256=capture['root_header_sha256'],capture_sha256=sha(raw),
        binary_receipt_sha256=sha(binary_raw),c4_sha256=C4_SHA,
        rows=rows,changed_ranges=8,install_write_bytes=changed,
        normal_install_restore_userdata_bytes=changed*2,no_new_allocation=True,
        unrelated_launch_jobs_unchanged=530,launch_transform_reversible=True,
        device_writes=0,device_boots=0,device_qualified=False)
    (out/'install-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','binary_receipt','c4','out'):
        ap.add_argument('--'+name.replace('_','-'),dest=name,type=Path,required=True)
    args=ap.parse_args()
    plan=prepare(args.capture.resolve(),args.binary_receipt.resolve(),args.c4.resolve(),args.out.resolve())
    print(json.dumps({k:v for k,v in plan.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
