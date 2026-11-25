#!/usr/bin/env python3
"""Fixed six-slot0338 delta from fresh independently restored337 originals."""
from pathlib import Path
import hashlib
import json
import plistlib
import struct
from sb_cadence_launch import transform_edr_loader,BACKBOARD_JOB,CACHE,REUSE_SLOT

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
RESTORE_MAX=10330112


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    capture_dir=BASE/'slot-capture';raw=(capture_dir/'result.json').read_bytes();capture=json.loads(raw)
    assert capture['state']=='readonly-six-file-Q337-capture' and capture['root_header_sha256']=='99624b0524a34e438bc323aa9f2b6344e912b133d4469cae70cb9bcb9ff7f1cd'
    sources={
        'eagl':PRIOR/'sb-qualified-v1/result.json',
        'admission':PRIOR/'edr-native-v1/result.json',
        'c4':BASE/'frontend-native-v1/result.json',
        'core':BASE/'native-v1/result.json',
    }
    receipts={name:json.loads(path.read_text()) for name,path in sources.items()}
    assert receipts['eagl']['state']=='native-SB337-baseline-qualified-candidate-signed-import-subset'
    assert receipts['admission']['state']=='native-EDR337-kernel-scope-canonical-baseline-candidate-signed'
    assert receipts['c4']['state']=='0338-frontend-baseline-reproduced-candidate-signed'
    assert receipts['core']['state']=='0338-native-core-baseline-reproduced-candidate-signed'
    abi=json.loads((BASE/'frontend-abi-v1/result.json').read_text());assert not abi['missing_imports'] and abi['checked_imports']==355
    candidates={}
    for name,receipt in receipts.items():
        product=receipt['products']['candidate'];data=Path(product['binary']).read_bytes()
        assert sha(data)==product['sha256'];candidates[name]=data
    originals={}
    for name,path in [('backboard',BACKBOARD_JOB),('cache',CACHE)]:
        row=capture['files'][path];data=(capture_dir/(name+'-old-data.bin')).read_bytes()[:row['logical']]
        assert sha(data)==row['sha256'];originals[name]=plistlib.loads(data)
    backboard,cache=transform_edr_loader(originals['backboard'],originals['cache'])
    candidates['backboard']=plistlib.dumps(backboard,fmt=plistlib.FMT_BINARY,sort_keys=False)
    candidates['cache']=plistlib.dumps(cache,fmt=plistlib.FMT_BINARY,sort_keys=False)
    paths={name:path for name,path in [
        ('eagl',REUSE_SLOT),('cache',CACHE),('c4','/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'),
        ('admission','/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib'),('backboard',BACKBOARD_JOB),
        ('core','/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib')]}
    rows={};images={};catalogs={}
    for name,path in paths.items():
        prior=capture['files'][path];data=candidates[name]
        old=(capture_dir/(name+'-old-data.bin')).read_bytes();cat=(capture_dir/(name+'-old-catalog.bin')).read_bytes()
        assert sha(old)==prior['data_alloc_sha256'] and sha(cat)==prior['catalog_sha256']
        assert len(old)==prior['data_blocks']*4096 and 0<len(data)<=len(old) and len(data)!=prior['logical']
        group=catalogs.setdefault(prior['catalog_block'],dict(old=cat,fields=[]))
        assert group['old']==cat
        at=prior['catalog_offset'];assert cat[at:at+8]==struct.pack('>Q',prior['logical'])
        assert all(abs(at-other)>=8 for other,_n in group['fields']);group['fields'].append((at,len(data)))
        new=data+old[len(data):];images[name]=new
        rows[name]=dict(path=path,cnid=prior['cnid'],mode=prior['mode'],old_logical=prior['logical'],
            new_logical=len(data),data_block=prior['data_block'],data_blocks=prior['data_blocks'],
            logical_size_changed=True,catalog_block=prior['catalog_block'],catalog_offset=at,
            old_file_sha256=prior['sha256'],new_file_sha256=sha(data),old_data_sha256=sha(old),
            new_data_sha256=sha(new),old_catalog_sha256=sha(cat))
    for group in catalogs.values():
        target=bytearray(group['old'])
        for at,n in group['fields']:struct.pack_into('>Q',target,at,n)
        group['new']=bytes(target)
    for row in rows.values():row['new_catalog_sha256']=sha(catalogs[row['catalog_block']]['new'])
    assert len(catalogs)==5 and sum(r['data_blocks']*4096 for r in rows.values())==10280960
    # Allocation bitmap coverage of the ORIGINAL extents is fixed: four pages.
    bitmap_pages={block//32768 for row in rows.values() for block in range(row['data_block'],row['data_block']+row['data_blocks'])}
    assert len(bitmap_pages)==4
    out=BASE/'slot-delta';assert not out.exists();out.mkdir()
    for name,data in images.items():
        (out/(name+'-new-data.bin')).write_bytes(data)
        (out/(name+'-new-catalog.bin')).write_bytes(catalogs[rows[name]['catalog_block']]['new'])
    plan=dict(state='prepared-six-file-core338-delta',root_header_sha256=capture['root_header_sha256'],
        capture_sha256=sha(raw),rows=rows,changed_ranges=11,install_write_bytes=10301440,
        data_write_bytes=10280960,restore_max_write_bytes=RESTORE_MAX,restore_max_ranges=18,
        restore_max_bitmap_blocks=4,core_logical_size_unchanged=False,no_new_allocation=True,
        normal_install_restore_userdata_bytes_max=10301440+RESTORE_MAX,
        maximum_install_plus_restore_and_failure_rollback_bytes=10301440+RESTORE_MAX*2,
        automatic_restore_policy='empty-or-already-applied-journal; reclaim-only-original-free-unowned-tail',
        journal_home_replay_allowed=False,alternate_header_write_allowed=False,
        binary_receipt_sha256=sha(sources['eagl'].read_bytes()),
        c4_receipt_sha256=sha(sources['c4'].read_bytes()),c4_sha256=sha(candidates['c4']),
        admission_receipt_sha256=sha(sources['admission'].read_bytes()),admission_sha256=sha(candidates['admission']),
        core_receipt_sha256=sha(sources['core'].read_bytes()),core_sha256=sha(candidates['core']),
        ABI_receipt_sha256=sha((BASE/'frontend-abi-v1/result.json').read_bytes()),
        unchanged_337_kernel_helper_SB=True,unrelated_launch_jobs_unchanged=530,
        device_writes=0,device_boots=0,device_qualified=False)
    with (out/'install-plan.json').open('x') as f:json.dump(plan,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in plan.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
