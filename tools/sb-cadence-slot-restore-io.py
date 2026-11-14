#!/usr/bin/env python3
"""Gated exact-range restore core; no device entry point or approval creator."""

import hashlib
import json
import struct


BLOCK = 4096
VOLUME = 17179869184
PARTITION_BYTES = 114919714816


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def restore_rows(base_dir, dynamic_dir, approval, io):
    base_raw = (base_dir/'install-plan.json').read_bytes()
    base = json.loads(base_raw)
    dynamic = json.loads((dynamic_dir/'restore-plan.json').read_bytes())
    require(base['state'] == 'prepared-four-file-SpringBoard-cadence-delta',
            'unexpected base plan')
    require(dynamic['state'] == 'prepared-dynamic-SpringBoard-cadence-restoration' and
            dynamic['base_plan_sha256'] == sha(base_raw), 'dynamic/base plan mismatch')
    require(approval.get('approved') is True and approval.get('one_shot') is True and
            approval.get('allow_restore') is True and approval.get('allow_rollback') is True and
            approval.get('plan_sha256') == sha(base_raw), 'fresh exact-scope approval required')
    if approval.get('fixture_only'):
        require(getattr(io,'model_only',False) is True,
                'fixture approval cannot reach writable phone IO')
    ident = io.identity()
    require(ident.get('state') == 'recovery' and ident.get('product') == 'gauguin' and
            ident.get('partition_bytes') == PARTITION_BYTES and
            ident.get('unmounted') is True and ident.get('no_holders') is True,
            'one unmounted Gauguin recovery partition required')
    require(sha(io.read(0,BLOCK)) == dynamic['postboot_header_sha256'],
            'postboot header changed')
    require(5 <= len(dynamic['ranges']) <= 8 and dynamic['catalog_blocks'] == len(dynamic['ranges'])-4,
            'unexpected restore range count')
    rows = []
    found_data, found_fields = set(), set()
    for item in dynamic['ranges']:
        name,block,size = item['name'],item['block'],item['bytes']
        require(type(block) is int and type(size) is int and block > 0 and
                size > 0 and size % BLOCK == 0 and block+size//BLOCK < VOLUME//BLOCK,
                'restore range outside root')
        current = (dynamic_dir/(name+'-current.bin')).read_bytes()
        target = (dynamic_dir/(name+'-target.bin')).read_bytes()
        require(len(current) == len(target) == size and
                sha(current) == item['current_sha256'] and
                sha(target) == item['target_sha256'], 'restore range hash/size mismatch')
        if item['kind'] == 'data':
            file_name = name.removesuffix('-data')
            require(name == file_name+'-data' and file_name in base['rows'] and
                    file_name not in found_data, 'unexpected data range')
            source = base['rows'][file_name]
            require(block == source['data_block'] and size == source['data_blocks']*BLOCK and
                    sha(current[:source['new_logical']]) == source['new_file_sha256'] and
                    sha(target) == source['old_data_sha256'], 'data restore differs from base')
            found_data.add(file_name)
        elif item['kind'] == 'catalog':
            require(name == 'catalog-'+str(block) and size == BLOCK, 'unexpected catalog range')
            fields = item['fields']
            require(1 <= len(fields) <= 4, 'catalog fields empty/oversized')
            expected = bytearray(current)
            offsets = []
            for field in fields:
                file_name,at,length = field['file'],field['offset'],field['old_logical']
                require(file_name in base['rows'] and file_name not in found_fields and
                        type(at) is int and 0 <= at <= BLOCK-8 and
                        length == base['rows'][file_name]['old_logical'] and
                        all(abs(at-other) >= 8 for other in offsets),
                        'catalog field differs from base')
                require(current[at:at+8] == struct.pack('>Q',base['rows'][file_name]['new_logical']),
                        'current catalog logical length differs')
                expected[at:at+8] = struct.pack('>Q',length)
                found_fields.add(file_name)
                offsets.append(at)
            require(bytes(expected) == target, 'catalog restore changes unrelated bytes')
        else:
            raise ValueError('unexpected restore range kind')
        rows.append((block,current,target))
    require(found_data == found_fields == set(base['rows']), 'restore file set incomplete')
    spans = [(block,block+len(current)//BLOCK) for block,current,_target in rows]
    require(all(a[1] <= b[0] or b[1] <= a[0] for i,a in enumerate(spans) for b in spans[i+1:]),
            'restore ranges overlap')
    require(sum(len(current) for _block,current,_target in rows) == dynamic['write_bytes'] and
            dynamic['write_bytes'] <= base['install_write_bytes'], 'restore byte bound exceeded')
    for block,current,_target in rows:
        require(io.read(block*BLOCK,len(current)) == current, 'restore preimage changed')
    return rows, dynamic['postboot_header_sha256']


def restore(base_dir, dynamic_dir, approval, io, HFS, Remote, report):
    rows, header_sha = restore_rows(base_dir,dynamic_dir,approval,io)
    base = json.loads((base_dir/'install-plan.json').read_bytes())
    touched = []
    try:
        for block,current,target in rows:
            touched.append((block,current))
            io.write(block*BLOCK,target)
            io.sync()
            require(io.read(block*BLOCK,len(target)) == target, 'restore readback differs')
            report({'state':'restoring','verified_ranges':len(touched),'range_count':len(rows)})
        remote = Remote(io)
        hfs = HFS(stream=remote,size=VOLUME)
        try:
            for name,source in base['rows'].items():
                file = hfs.paths[source['path']]
                require(file['type']==2 and file['id']==source['cnid'] and
                        file['data']['logical']==source['old_logical'] and
                        file['data']['blocks']==source['data_blocks'] and
                        file['data']['extents']==[[source['data_block'],source['data_blocks']]] and
                        sha(hfs.content(source['path']))==source['old_file_sha256'],
                        'restored HFSX file differs: '+name)
        finally:
            hfs.close()
        require(sha(io.read(0,BLOCK)) == header_sha, 'header changed during restore')
        result = {'state':'restore-applied-and-readback-verified',
                  'ranges':len(rows),'bytes':sum(len(row[1]) for row in rows),
                  'hfsx_files_verified':len(base['rows']),'rollback':False}
        report(result)
        return result
    except (Exception,KeyboardInterrupt) as error:
        failures = []
        for block,current in reversed(touched):
            try:
                io.write(block*BLOCK,current)
                io.sync()
                require(io.read(block*BLOCK,len(current)) == current,
                        'rollback readback differs')
            except (Exception,KeyboardInterrupt) as problem:
                failures.append({'block':block,'error':repr(problem)})
        result = {'state':'restore-failed-rollback-incomplete' if failures else
                         'restore-failed-rollback-verified',
                  'error':repr(error),'touched_ranges':len(touched),
                  'rollback_failures':failures}
        report(result)
        return result
