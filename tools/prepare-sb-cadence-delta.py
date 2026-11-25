#!/usr/bin/env python3
"""Six-file stage-cache delta within existing allocations."""
import argparse
import hashlib
import json
import plistlib
import struct
from pathlib import Path
from sb_cadence_launch import transform_edr_loader, BACKBOARD_JOB, CACHE, REUSE_SLOT


WORK = Path(__file__).resolve().parents[1]
C4 = '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop'
ADMISSION = '/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib'
CORE = '/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib'
BLOCK = 4096


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(capture_dir, binary_receipt, c4_receipt, admission_receipt, core_receipt, out):
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    raw = (capture_dir/'result.json').read_bytes()
    capture = json.loads(raw)
    binary_raw = binary_receipt.read_bytes()
    binary = json.loads(binary_raw)
    assert capture['state'] == 'readonly-six-file-Q337-capture'
    assert binary['state']=='native-SB337-baseline-qualified-candidate-signed-import-subset'
    assert binary['imports_20H392_qualified'] and binary['checked_imports']==65 and not binary['missing_imports']
    assert binary['capacity']==1024 and binary['extra_threads']==0
    observer_product=binary['products']['candidate']
    assert binary['install_name'] == REUSE_SLOT
    observer = Path(observer_product['binary']).read_bytes()
    assert sha(observer) == observer_product['sha256']
    c4_raw=c4_receipt.read_bytes();c4_build=json.loads(c4_raw)
    assert c4_build['state']=='native-Q337-C4Q321-baseline-reproduced-candidate-signed'
    assert c4_build['baseline_all_code_data_UUID_symbols_identical'] and c4_build['queue_metadata_stages']==3
    assert c4_build['queue_metadata_max_bytes']==6291648
    assert c4_build['inputs_unchanged'] and c4_build['original_loader_order_unchanged'] and c4_build['source_change_reversible'] and c4_build['imports_unchanged']
    c4_product=c4_build['products']['candidate'];frontend=Path(c4_product['binary']).read_bytes()
    assert sha(frontend)==c4_product['sha256'] and len(frontend)==c4_product['bytes']<=430080
    admission_raw = admission_receipt.read_bytes()
    admission_build = json.loads(admission_raw)
    assert admission_build['state'] == 'native-EDR337-kernel-scope-canonical-baseline-candidate-signed'
    assert admission_build['inputs_unchanged'] and admission_build['private_data_pointer_bytes'] == 8
    candidate = admission_build['products']['candidate']
    admission = Path(candidate['binary']).read_bytes()
    assert sha(admission) == candidate['sha256'] and len(admission) == candidate['bytes'] <= 73728
    assert capture['files'][ADMISSION]['sha256'] == 'a1b98155d1e01b17d50a6bd733dbf560ce21a74572758d8ae97c52a4174d3562'
    assert admission_build['baseline_reproduction']['original_sha256'] == '60a90e85a452fa9e2171aa572158f225a9a48a781d5c8a5dcdb424546271b0a5' and admission_build['baseline_reproduction']['canonical_signed_bytes_identical']
    assert admission_build['pointer_write_and_once_contract_unchanged'] and admission_build['imports_unchanged']
    assert admission_build['required_optin']=='gpf=4' and admission_build['required_mapping_optin']=='sweetgpumap=1' and admission_build['required_sampling_optin']=='gsp=328'
    core_raw = core_receipt.read_bytes()
    core_build = json.loads(core_raw)
    assert core_build['state'] == 'SURF334-native-baseline-canonical-signature-reproduced-candidate-signed'
    assert core_build['inputs_unchanged'] and core_build['all_core_TUs_recompiled'] and core_build['fits_existing_allocation']
    assert not core_build['exports_added'] and not core_build['exports_removed'] and core_build['loads_unchanged'] and core_build['imports_unchanged']
    assert core_build['cache_build_tag'] == '8a71fe61aded108fa9ba5a22'
    assert core_build['products']['baseline']['sha256'] == '3ab7d3c3a24df5ed6452cd05f6c7fac8ba89c795d60eab83e9e495545321081a'
    assert core_build['baseline_reproduction']['original_sha256'] == '1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
    assert core_build['baseline_reproduction']['canonical_signed_bytes_identical'] and core_build['baseline_reproduction']['installed_input_unchanged']
    assert capture['files'][CORE]['sha256'] == 'c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674'
    core_product = core_build['products']['candidate']
    core = Path(core_product['binary']).read_bytes()
    assert sha(core) == core_product['sha256'] == 'dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
    assert len(core) == core_product['bytes'] == 8391360
    assert capture['files'][CORE]['logical'] == 8407792
    originals = {}
    for name,path in [('backboard',BACKBOARD_JOB),('cache',CACHE)]:
        row = capture['files'][path]
        data = (capture_dir/(name+'-old-data.bin')).read_bytes()[:row['logical']]
        assert sha(data) == row['sha256']
        originals[name] = plistlib.loads(data)
    backboard,cache = transform_edr_loader(originals['backboard'],originals['cache'])
    candidates = {
        'eagl':(REUSE_SLOT,observer),
        'cache':(CACHE,plistlib.dumps(cache,fmt=plistlib.FMT_BINARY,sort_keys=False)),
        'c4':(C4,frontend),
        'admission':(ADMISSION,admission),
        'backboard':(BACKBOARD_JOB,plistlib.dumps(backboard,fmt=plistlib.FMT_BINARY,sort_keys=False)),
        'core':(CORE,core),
    }
    rows,blobs,catalogs = {},{},{}
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
        group = catalogs.setdefault(prior['catalog_block'], dict(old=old_cat, fields=[]))
        assert group['old'] == old_cat
        assert all(abs(at-other) >= 8 for other,_length in group['fields'])
        group['fields'].append((at,new_len))
        rows[name] = dict(path=path,cnid=prior['cnid'],mode=prior['mode'],
            old_logical=old_len,new_logical=new_len,data_block=prior['data_block'],
            logical_size_changed=(old_len != new_len),
            data_blocks=prior['data_blocks'],catalog_block=prior['catalog_block'],
            catalog_offset=at,old_file_sha256=prior['sha256'],new_file_sha256=sha(new_file),
            old_data_sha256=sha(old_data),new_data_sha256=sha(new_data),
            old_catalog_sha256=sha(old_cat))
        blobs[name] = new_data
    spans = [(r['data_block'],r['data_block']+r['data_blocks']) for r in rows.values()]
    assert len(rows) == 6 and 4 <= len(catalogs) <= 6
    for group in catalogs.values():
        merged = bytearray(group['old'])
        for at,length in group['fields']:
            merged[at:at+8] = struct.pack('>Q',length)
        group['new'] = bytes(merged)
    for name,row in rows.items():
        row['new_catalog_sha256'] = sha(catalogs[row['catalog_block']]['new'])
    assert all(a[1]<=b[0] or b[1]<=a[0] for i,a in enumerate(spans) for b in spans[i+1:])
    assert all(not any(a<=r['catalog_block']<b for a,b in spans) for r in rows.values())
    data_bytes = sum(r['data_blocks']*BLOCK for r in rows.values())
    changed_catalogs = sum(group['new'] != group['old'] for group in catalogs.values())
    assert changed_catalogs == 5
    changed = data_bytes + changed_catalogs*BLOCK
    restore_max = data_bytes + sum(r['logical_size_changed'] for r in rows.values())*BLOCK
    assert data_bytes == 10280960 and changed == 10301440 and restore_max == 10305536
    out.mkdir(parents=True)
    for name,data in blobs.items():
        cat = catalogs[rows[name]['catalog_block']]['new']
        (out/(name+'-new-data.bin')).write_bytes(data)
        (out/(name+'-new-catalog.bin')).write_bytes(cat)
    plan = dict(state='prepared-six-file-Q337-cadence-delta',
        root_header_sha256=capture['root_header_sha256'],capture_sha256=sha(raw),
        binary_receipt_sha256=sha(binary_raw),c4_sha256=sha(frontend),c4_receipt_sha256=sha(c4_raw),
        admission_receipt_sha256=sha(admission_raw),admission_sha256=sha(admission),
        core_receipt_sha256=sha(core_raw),core_sha256=sha(core),core_logical_size_unchanged=False,
        rows=rows,changed_ranges=6+changed_catalogs,install_write_bytes=changed,data_write_bytes=data_bytes,
        read_catalog_groups=len(catalogs),written_catalog_groups=changed_catalogs,
        restore_max_write_bytes=restore_max,restore_max_ranges=12,
        normal_install_restore_userdata_bytes_max=changed+restore_max,no_new_allocation=True,
        unrelated_launch_jobs_unchanged=530,launch_transform_reversible=True,
        device_writes=0,device_boots=0,device_qualified=False)
    (out/'install-plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    return plan


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('capture','binary_receipt','c4_receipt','admission_receipt','core_receipt','out'):
        ap.add_argument('--'+name.replace('_','-'),dest=name,type=Path,required=True)
    args=ap.parse_args()
    plan=prepare(args.capture.resolve(),args.binary_receipt.resolve(),args.c4_receipt.resolve(),args.admission_receipt.resolve(),args.core_receipt.resolve(),args.out.resolve())
    print(json.dumps({k:v for k,v in plan.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
