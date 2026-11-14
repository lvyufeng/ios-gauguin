#!/usr/bin/env python3
"""Prepare a postboot SpringBoard observer restore from read-only HFSX IO.

There is deliberately no device entry point or write method here. The caller
supplies an IO object with read(offset, bytes), and receives local preimages
for a separately approved executor to verify and restore later.
"""

import hashlib
import json
import struct
from pathlib import Path


BLOCK = 4096
VOLUME = 17179869184


def sha(data):
    return hashlib.sha256(data).hexdigest()


def prepare(plan_dir, capture_dir, io, HFS, Remote, out):
    plan_raw = (plan_dir/'install-plan.json').read_bytes()
    plan = json.loads(plan_raw)
    capture_raw = (capture_dir/'result.json').read_bytes()
    capture = json.loads(capture_raw)
    assert plan['state'] == 'prepared-four-file-SpringBoard-cadence-delta'
    assert capture['state'] == 'readonly-four-file-cadence-capture'
    assert plan['capture_sha256'] == sha(capture_raw)
    assert len(plan['rows']) == 4 and plan['changed_ranges'] == 8
    assert not out.exists()
    header = io.read(0,BLOCK)
    assert header[1024:1026] == b'HX'
    remote = Remote(io)
    hfs = HFS(stream=remote,size=VOLUME)
    data = {}
    catalog = {}
    try:
        for name,row in plan['rows'].items():
            path = row['path']
            prior = capture['files'][path]
            file = hfs.paths[path]
            fork = file['data']
            assert file['id'] == prior['cnid'] == row['cnid'] and file['type'] == 2
            assert not file['flags']&0x20
            assert (file['uid'],file['gid'],file['mode']) == (0,0,row['mode'])
            assert fork['logical'] == row['new_logical']
            assert fork['blocks'] == row['data_blocks']
            assert fork['extents'] == [[row['data_block'],row['data_blocks']]]
            assert sha(hfs.content(path)) == row['new_file_sha256']
            old = (capture_dir/(name+'-old-data.bin')).read_bytes()
            assert len(old) == row['data_blocks']*BLOCK
            assert sha(old) == row['old_data_sha256']
            current = io.read(row['data_block']*BLOCK,len(old))
            assert sha(current[:row['new_logical']]) == row['new_file_sha256']
            data[name] = (row['data_block'],current,old)
            spans = list(hfs.spans(hfs.catalog,file['catalog_bsd_offset']+56,8))
            assert len(spans) == 1 and spans[0][1] == 8
            physical = spans[0][0]
            block,at = divmod(physical,BLOCK)
            assert 0 < block < VOLUME//BLOCK-1 and at+8 <= BLOCK
            current_cat = catalog.setdefault(block,{'current':io.read(block*BLOCK,BLOCK),
                                                     'fields':[]})
            assert current_cat['current'][at:at+8] == struct.pack('>Q',row['new_logical'])
            assert all(abs(at-other)>=8 for other,_name,_length in current_cat['fields'])
            current_cat['fields'].append((at,name,row['old_logical']))
    finally:
        hfs.close()
    data_spans = [(block,block+len(current)//BLOCK) for block,current,_old in data.values()]
    assert all(a[1] <= b[0] or b[1] <= a[0] for i,a in enumerate(data_spans)
               for b in data_spans[i+1:])
    assert all(not any(a <= block < b for a,b in data_spans) for block in catalog)
    assert len(catalog) <= 4
    assert io.read(0,BLOCK) == header
    images = {}
    ranges = []
    for name,(block,current,old) in data.items():
        key = name+'-data'
        images[key] = (current,old)
        ranges.append({'name':key,'kind':'data','block':block,'bytes':len(old),
                       'current_sha256':sha(current),'target_sha256':sha(old)})
    for block,group in catalog.items():
        current = group['current']
        target = bytearray(current)
        for at,_name,length in group['fields']:
            target[at:at+8] = struct.pack('>Q',length)
        target = bytes(target)
        assert target != current
        changed = {i for i,(a,b) in enumerate(zip(current,target)) if a != b}
        allowed = {i for at,_name,_length in group['fields'] for i in range(at,at+8)}
        assert changed <= allowed
        key = 'catalog-'+str(block)
        images[key] = (current,target)
        ranges.append({'name':key,'kind':'catalog','block':block,'bytes':BLOCK,
                       'fields':[{'offset':at,'file':name,'old_logical':length}
                                 for at,name,length in group['fields']],
                       'current_sha256':sha(current),'target_sha256':sha(target)})
    out.mkdir(parents=True)
    for key,(current,target) in images.items():
        with (out/(key+'-current.bin')).open('xb') as stream:stream.write(current)
        with (out/(key+'-target.bin')).open('xb') as stream:stream.write(target)
    result = {'state':'prepared-dynamic-SpringBoard-cadence-restoration',
              'base_plan_sha256':sha(plan_raw),'postboot_header_sha256':sha(header),
              'ranges':ranges,'write_bytes':sum(row['bytes'] for row in ranges),
              'catalog_blocks':len(catalog),'read_only_catalog_bytes':remote.bytes,
              'device_writes':0}
    with (out/'restore-plan.json').open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    return result
