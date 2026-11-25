#!/usr/bin/env python3
"""0342 gated six-file install with empty-journal/allocation preflight."""

import hashlib
import json
import struct
from core342_hfs import inspect_journal
from core342_slots import data_extents, split_allocation


BLOCK = 4096
VOLUME = 17179869184
PARTITION_BYTES = 114919714816
EXPECTED = {
    'eagl':'/usr/local/lib/gauguin/libGauguinEAGL.dylib',
    'cache':'/System/Library/xpc/launchd.plist',
    'c4':'/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop',
    'admission':'/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib',
    'backboard':'/System/Library/LaunchDaemons/com.apple.backboardd.plist',
    'core':'/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib',
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
    require(plan['state']=='prepared-six-file-core342-delta' and
            plan['capture_sha256']==sha(capture_raw) and
            plan['changed_ranges'] in (11,12) and plan['install_write_bytes']==10301440 and
            plan['data_write_bytes']==10280960 and plan['restore_max_write_bytes']==10330112 and
            plan['restore_max_ranges']==18 and plan['core_logical_size_unchanged'] is False and
            plan['no_new_allocation'] is True and
            set(plan['rows'])==set(EXPECTED), 'unexpected six-file install plan')
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
        bitmap=hfs.fork_read(hfs.special['allocation'])
        require(hfs.blocks-sum(value.bit_count() for value in bitmap)==struct.unpack_from('>I',hfs.header,48)[0],
                'bitmap/primary free count differs before installation')
        for owned in plan['rows'].values():
            for start,count in data_extents(owned):
                require(all(bitmap[block//8]&(1<<(7-block%8)) for block in range(start,start+count)),
                        'original slot has unallocated blocks')
        inspect_journal(io,io.read(0,BLOCK),require_empty=True)
        for name,path in EXPECTED.items():
            row = plan['rows'][name]
            prior = capture['files'][path]
            file = hfs.paths[path]
            require(row['path']==path and file['type']==2 and not file['flags']&0x20 and
                    file['id']==row['cnid']==prior['cnid'] and
                    (file['uid'],file['gid'],file['mode'])==(0,0,row['mode']) and
                    file['data']['logical']==row['old_logical'] and
                    file['data']['blocks']==row['data_blocks'] and
                    file['data']['extents']==data_extents(row)==data_extents(dict(prior,path=path)) and
                    not (file['resource']['logical'] or file['resource']['blocks'] or file['resource']['extents']) and
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
        require(row['logical_size_changed'] is True and row['old_logical'] != row['new_logical'],
                'unexpected logical size mutation: '+name)
        if name == 'core':
            core_logical={'0346':7_992_224, '0347':7_992_176, '0348':7_992_224, '0349':7_992_224,
                          '0350':7_992_224, '0351':7_992_224, '0352':7_992_224, '0353':7_992_224,
                          '0354':7_992_224, '0355':7_992_224, '0356':7_992_224,
                          '0357':7_992_224, '0358':7_992_224, '0359':7_992_224,
                          '0360':7_992_224, '0361':7_975_728, '0362':7_975_712,
                          '0363':7_975_712, '0364':7_975_712, '0365':7_975_712,
                          '0366':7_975_712, '0367':7_975_712, '0368':7_975_712,
                          '0369':7_975_712, '0370':7_975_712, '0371':7_975_712,
                          '0372':7_975_712, '0373':7_975_712, '0374':7_975_712, '0375':7_975_712,
                          '0376':7_975_712, '0377':7_975_712, '0378':7_975_712, '0379':7_975_712,
                          '0380':7_975_712, '0381':7_975_712, '0382':7_975_712,
                          '0383':7_975_712, '0384':7_975_712, '0387':7_975_712,
                          '0388':7_975_712, '0389':7_975_728, '0390':7_975_712,
                          '0391':7_975_712, '0392':7_975_712, '0393':7_975_712,
                          '0397':7_975_712, '0398':7_975_712, '0399':7_975_888,
                          '0400':7_975_888, '0401':7_975_984, '0404':7_975_984,
                          '0405':7_975_984, '0406':7_975_984, '0407':7_975_984,
                          '0408':7_975_984, '0409':7_975_984, '0410':7_975_984,
                          '0411':7_975_984, '0412':7_975_984, '0413':7_975_984,
                          '0414':7_975_984, '0415':7_975_984, '0416':7_975_984, '0417':7_975_984,
                          '0419':7_975_984, '0422':7_975_984, '0423':7_975_984, '0424':7_975_984,
                          '0425':7_975_984, '0426':7_975_984, '0427':7_975_984}.get(plan.get('trial'),7_975_792)
            require(row['old_logical']==8407792 and row['new_logical']==core_logical and row['data_blocks']==2053,
                    'owned core allocation differs')
        old = (capture_dir/(name+'-old-data.bin')).read_bytes()
        new = (plan_dir/(name+'-new-data.bin')).read_bytes()
        require(len(old)==len(new)==row['data_blocks']*BLOCK and
                0 < row['old_logical'] <= len(old) and 0 < row['new_logical'] <= len(new) and
                sha(old)==row['old_data_sha256'] and sha(new)==row['new_data_sha256'] and
                sha(old[:row['old_logical']])==row['old_file_sha256'] and
                sha(new[:row['new_logical']])==row['new_file_sha256'],
                'data image differs: '+name)
        extents = data_extents(row)
        require(len(extents)==1 or (row['data_blocks']-1)*BLOCK < row['new_logical'],
                'split C4 candidate could release its tail')
        for (start,before),(_,after) in zip(split_allocation(extents,old),split_allocation(extents,new),strict=True):
            rows.append((start,before,after))
    catalogs = {}
    for name in EXPECTED:
        row = plan['rows'][name]
        old = (capture_dir/(name+'-old-catalog.bin')).read_bytes()
        new = (plan_dir/(name+'-new-catalog.bin')).read_bytes()
        at = row['catalog_offset']
        require(len(old)==len(new)==BLOCK and
                sha(old)==row['old_catalog_sha256'] and sha(new)==row['new_catalog_sha256'] and
                type(at) is int and 0 <= at <= BLOCK-8 and
                old[at:at+8]==struct.pack('>Q',row['old_logical']) and
                new[at:at+8]==struct.pack('>Q',row['new_logical']),
                'catalog image or owned logical length differs: '+name)
        group = catalogs.setdefault(row['catalog_block'], dict(old=old,new=new,fields=[]))
        require(group['old']==old and group['new']==new and
                all(abs(at-other)>=8 for other,_length in group['fields']),
                'shared catalog images or offsets disagree')
        group['fields'].append((at,row['new_logical']))
    require(len(catalogs)==5, 'unexpected initial catalog grouping')
    for block,group in catalogs.items():
        expected = bytearray(group['old'])
        for at,length in group['fields']:
            expected[at:at+8] = struct.pack('>Q',length)
        require(bytes(expected)==group['new'], 'catalog image changes unrelated bytes')
        if group['new'] != group['old']:
            rows.append((block,group['old'],group['new']))
    spans = [(block,block+len(old)//BLOCK) for block,old,_new in rows]
    require(all(0<a<b<VOLUME//BLOCK for a,b in spans) and
            all(a[1]<=b[0] or b[1]<=a[0] for i,a in enumerate(spans) for b in spans[i+1:]) and
            len(rows)==plan['changed_ranges'] and sum(len(old) for _block,old,_new in rows)==plan['install_write_bytes'],
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
                        file['data']['extents']==data_extents(row) and
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
