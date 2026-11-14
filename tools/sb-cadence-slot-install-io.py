#!/usr/bin/env python3
"""Gated eight-range SpringBoard observer install core; no device entry point."""

import hashlib
import json
import struct


BLOCK = 4096
VOLUME = 17179869184
PARTITION_BYTES = 114919714816
EXPECTED = {
    'eagl':'/usr/local/lib/gauguin/libGauguinEAGL.dylib',
    'job':'/System/Library/LaunchDaemons/com.apple.SpringBoard.plist',
    'cache':'/System/Library/xpc/launchd.plist',
    'c4':'/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(ok,why):
    if not ok:
        raise ValueError(why)


def preflight(plan_dir,capture_dir,approval,io,HFS,Remote):
    plan_raw = (plan_dir/'install-plan.json').read_bytes()
    plan = json.loads(plan_raw)
    capture_raw = (capture_dir/'result.json').read_bytes()
    capture = json.loads(capture_raw)
    require(plan['state']=='prepared-four-file-SpringBoard-cadence-delta' and
            plan['capture_sha256']==sha(capture_raw) and
            plan['changed_ranges']==8 and plan['install_write_bytes']==1814528 and
            plan['no_new_allocation'] is True and
            set(plan['rows'])==set(EXPECTED), 'unexpected eight-range install plan')
    require(approval.get('approved') is True and approval.get('one_shot') is True and
            approval.get('allow_install') is True and approval.get('allow_rollback') is True and
            approval.get('plan_sha256')==sha(plan_raw), 'fresh exact-scope approval required')
    if approval.get('fixture_only'):
        require(getattr(io,'model_only',False) is True,
                'fixture approval cannot reach writable phone IO')
    identity = io.identity()
    require(identity.get('state')=='recovery' and identity.get('product')=='gauguin' and
            identity.get('partition_bytes')==PARTITION_BYTES and
            identity.get('unmounted') is True and identity.get('no_holders') is True,
            'one unmounted Gauguin recovery partition required')
    require(sha(io.read(0,BLOCK))==plan['root_header_sha256']==capture['root_header_sha256'],
            'current root header differs')
    remote = Remote(io)
    hfs = HFS(stream=remote,size=VOLUME)
    try:
        for name,path in EXPECTED.items():
            row = plan['rows'][name]
            prior = capture['files'][path]
            file = hfs.paths[path]
            require(row['path']==path and file['type']==2 and not file['flags']&0x20 and
                    file['id']==row['cnid']==prior['cnid'] and
                    (file['uid'],file['gid'],file['mode'])==(0,0,row['mode']) and
                    file['data']['logical']==row['old_logical'] and
                    file['data']['blocks']==row['data_blocks'] and
                    file['data']['extents']==[[row['data_block'],row['data_blocks']]] and
                    sha(hfs.content(path))==row['old_file_sha256'],
                    'live HFSX file differs: '+name)
            spans = list(hfs.spans(hfs.catalog,file['catalog_bsd_offset']+56,8))
            require(len(spans)==1 and spans[0][1]==8 and
                    divmod(spans[0][0],BLOCK)==(row['catalog_block'],row['catalog_offset']),
                    'live catalog leaf moved: '+name)
    finally:
        hfs.close()
    rows = []
    for name in EXPECTED:
        row = plan['rows'][name]
        old = (capture_dir/(name+'-old-data.bin')).read_bytes()
        new = (plan_dir/(name+'-new-data.bin')).read_bytes()
        require(len(old)==len(new)==row['data_blocks']*BLOCK and
                sha(old)==row['old_data_sha256'] and sha(new)==row['new_data_sha256'] and
                sha(old[:row['old_logical']])==row['old_file_sha256'] and
                sha(new[:row['new_logical']])==row['new_file_sha256'],
                'data image differs: '+name)
        rows.append((row['data_block'],old,new))
    for name in EXPECTED:
        row = plan['rows'][name]
        old = (capture_dir/(name+'-old-catalog.bin')).read_bytes()
        new = (plan_dir/(name+'-new-catalog.bin')).read_bytes()
        at = row['catalog_offset']
        require(len(old)==len(new)==BLOCK and
                sha(old)==row['old_catalog_sha256'] and sha(new)==row['new_catalog_sha256'] and
                old[:at]==new[:at] and old[at+8:]==new[at+8:] and
                old[at:at+8]==struct.pack('>Q',row['old_logical']) and
                new[at:at+8]==struct.pack('>Q',row['new_logical']),
                'catalog image changes more than logical length: '+name)
        rows.append((row['catalog_block'],old,new))
    spans = [(block,block+len(old)//BLOCK) for block,old,_new in rows]
    require(all(0<a<b<VOLUME//BLOCK for a,b in spans) and
            all(a[1]<=b[0] or b[1]<=a[0] for i,a in enumerate(spans) for b in spans[i+1:]) and
            sum(len(old) for _block,old,_new in rows)==plan['install_write_bytes'],
            'install ranges overlap or exceed scope')
    for block,old,_new in rows:
        require(io.read(block*BLOCK,len(old))==old,'full install preimage changed')
    return plan,rows


def install(plan_dir,capture_dir,approval,io,HFS,Remote,report):
    plan,rows = preflight(plan_dir,capture_dir,approval,io,HFS,Remote)
    touched = []
    try:
        for block,old,new in rows:
            touched.append((block,old))
            io.write(block*BLOCK,new)
            io.sync()
            require(io.read(block*BLOCK,len(new))==new,'install readback differs')
            report({'state':'installing','verified_ranges':len(touched),'range_count':len(rows)})
        remote = Remote(io)
        hfs = HFS(stream=remote,size=VOLUME)
        try:
            for name,path in EXPECTED.items():
                row = plan['rows'][name]
                file = hfs.paths[path]
                require(file['id']==row['cnid'] and file['data']['logical']==row['new_logical'] and
                        file['data']['extents']==[[row['data_block'],row['data_blocks']]] and
                        sha(hfs.content(path))==row['new_file_sha256'],
                        'installed HFSX file differs: '+name)
        finally:
            hfs.close()
        require(sha(io.read(0,BLOCK))==plan['root_header_sha256'],
                'root header changed during install')
        result={'state':'install-applied-and-HFSX-verified','ranges':len(rows),
                'bytes':sum(len(old) for _block,old,_new in rows),'rollback':False}
        report(result)
        return result
    except (Exception,KeyboardInterrupt) as error:
        failures=[]
        for block,old in reversed(touched):
            try:
                io.write(block*BLOCK,old)
                io.sync()
                require(io.read(block*BLOCK,len(old))==old,'rollback readback differs')
            except (Exception,KeyboardInterrupt) as problem:
                failures.append({'block':block,'error':repr(problem)})
        result={'state':'install-failed-rollback-incomplete' if failures else
                        'install-failed-rollback-verified',
                'error':repr(error),'touched_ranges':len(touched),
                'rollback_failures':failures}
        report(result)
        return result
