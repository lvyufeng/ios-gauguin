"""Bounded six-file restoration, completed journal, original free tail reclaim.

No device entry point or recovery reboot. Preparation is read-only and refuses
unsupported state before saving images or attempting a write. The caller owns
the separately authorized one-shot trial and exclusive recovery IO.
"""
import bisect
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from core340_hfs import BLOCK,VOLUME,attribute_extents,inspect_journal,require,sha

MAX_BYTES=10330112
MAX_RANGES=18


def module(name,leaf):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(leaf))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


ENGINE=module('reviewed_raw_preimage_engine340','restore-queue337-trim.py')
EXPECTED=module('install_scope340','core340_install.py').EXPECTED


def identity_gate(io):
    i=io.identity()
    require(i['state']=='recovery' and i['product']=='gauguin' and i['partition_bytes']==114919714816 and
            i['unmounted'] and i['no_holders'],'unique unmounted recovery IO required')


def prepare(plan_dir,capture_dir,io,HFS,Remote,out=None):
    raw=(plan_dir/'install-plan.json').read_bytes();plan=json.loads(raw)
    require(plan['state']=='prepared-six-file-core340-delta' and set(plan['rows'])==set(EXPECTED) and
            plan['restore_max_write_bytes']==MAX_BYTES and plan['restore_max_ranges']==MAX_RANGES and
            plan['restore_max_bitmap_blocks']==4 and plan['journal_home_replay_allowed'] is False and
            plan['alternate_header_write_allowed'] is False,'unsupported restore policy')
    require(sha((capture_dir/'result.json').read_bytes())==plan['capture_sha256'],'original capture changed')
    require(out is None or not out.exists(),'fresh restore output required')
    identity_gate(io);header=io.read(0,BLOCK);alternate=io.read(VOLUME-BLOCK,BLOCK)
    journal,jcurrent,jtarget,info,jraw=inspect_journal(io,header)
    h=HFS(stream=Remote(io),size=VOLUME);images={};ranges=[];catalog={};data=[];tails=[]
    def add(name,kind,block,current,target,fields=None):
        require(len(current)==len(target)>0 and len(current)%BLOCK==0,'restore range size')
        if current==target:return
        row=dict(name=name,kind=kind,block=block,bytes=len(target),current_sha256=sha(current),target_sha256=sha(target))
        if fields is not None:row['fields']=fields
        ranges.append(row);images[name]=(current,target)
    try:
        require(struct.unpack_from('>II',h.header,40)==(BLOCK,VOLUME//BLOCK),'volume geometry changed')
        bitmap=h.fork_read(h.special['allocation'])
        free=h.blocks-sum(byte.bit_count() for byte in bitmap)
        require(free==struct.unpack_from('>I',h.header,48)[0],'postboot bitmap/primary free count mismatch')
        for name,path in EXPECTED.items():
            row=plan['rows'][name];file=h.paths[path];fork=file['data']
            require(row['path']==path and file['type']==2 and not file['flags']&0x20 and file['id']==row['cnid'] and
                (file['uid'],file['gid'],file['mode'])==(0,0,row['mode']),'restore file identity changed: '+name)
            minimum=(row['new_logical']+BLOCK-1)//BLOCK
            require(fork['logical']==row['new_logical'] and minimum<=fork['blocks']<=row['data_blocks'] and
                fork['extents']==[[row['data_block'],fork['blocks']]],'fork moved/grew beyond original slot: '+name)
            require(file['resource']['logical']==file['resource']['blocks']==0 and not file['resource']['extents'],
                'owned resource fork changed: '+name)
            require(sha(h.content(path))==row['new_file_sha256'],'candidate content changed: '+name)
            old=(capture_dir/(name+'-old-data.bin')).read_bytes()
            require(len(old)==row['data_blocks']*BLOCK and sha(old)==row['old_data_sha256'] and
                sha(old[:row['old_logical']])==row['old_file_sha256'],'original allocated/logical preimage changed')
            current=io.read(row['data_block']*BLOCK,len(old));data.append((name,row['data_block'],current,old))
            released=list(range(row['data_block']+fork['blocks'],row['data_block']+row['data_blocks']))
            require(all(not bitmap[n//8]&(1<<(7-n%8)) for n in released),'original tail reused: '+name)
            tails+=released
            span=list(h.spans(h.catalog,file['catalog_bsd_offset']+56,80))
            require(len(span)==1 and span[0][1]==80,'catalog fork spans extents')
            block,at=divmod(span[0][0],BLOCK);require(at+80<=BLOCK,'catalog fork crosses physical block')
            group=catalog.setdefault(block,dict(current=io.read(block*BLOCK,BLOCK),fields=[]))
            require(group['current'][at:at+8]==struct.pack('>Q',row['new_logical']),'logical catalog field changed')
            group['fields'].append(dict(offset=at,bytes=8,value=row['old_logical'],file=name))
            if released:
                require(group['current'][at+24:at+80]==bytes(56),'trimmed owned fork has additional inline extents')
                group['fields'] += [dict(offset=at+12,bytes=4,value=row['data_blocks'],file=name),
                                    dict(offset=at+20,bytes=4,value=row['data_blocks'],file=name)]
        require(len(tails)==len(set(tails)),'original slots overlap')
        tails.sort()
        def unowned(extents):
            for start,count in extents:
                i=bisect.bisect_left(tails,start)
                require(i==len(tails) or tails[i]>=start+count,'free tail has a catalog/resource/special/overflow/attribute owner')
        if tails:
            for file in h.records.values():
                for kind in ('data','resource'):unowned(file.get(kind,{}).get('extents',[]))
            for fork in h.special.values():unowned(fork['extents'])
            for extents in h.extent_records.values():unowned(extents)
            attr,counts=attribute_extents(h.fork_read(h.special['attributes']));unowned(attr)
        else:counts={}
        bitmaps={}
        for n in tails:
            spans=list(h.spans(h.special['allocation'],n//8,1));require(len(spans)==1,'bitmap span')
            block,at=divmod(spans[0][0],BLOCK)
            group=bitmaps.setdefault(block,dict(current=io.read(block*BLOCK,BLOCK),masks={}))
            group['masks'][at]=group['masks'].get(at,0)|(1<<(7-n%8))
        require(len(bitmaps)<=4,'bitmap blocks exceed frozen restore bound')
        # Every pending home image is already applied; clear journal first so
        # old replay cannot overwrite subsequent owned metadata restoration.
        add('journal-header','journal',journal['offset']//BLOCK,jcurrent,jtarget)
        for block,group in sorted(bitmaps.items()):
            target=bytearray(group['current'])
            for at,mask in group['masks'].items():
                require(not target[at]&mask,'reclaimed bit changed');target[at]|=mask
            add('bitmap-'+str(block),'bitmap',block,group['current'],bytes(target),
                [dict(offset=at,mask=mask) for at,mask in sorted(group['masks'].items())])
        for name,block,current,old in data:add(name+'-data','data',block,current,old)
        for block,group in sorted(catalog.items()):
            current=group['current'];target=bytearray(current);owned=set()
            for field in group['fields']:
                indexes=set(range(field['offset'],field['offset']+field['bytes']))
                require(not indexes&owned,'owned catalog field overlap');owned|=indexes
                struct.pack_into('>Q' if field['bytes']==8 else '>I',target,field['offset'],field['value'])
            require({n for n,(a,b) in enumerate(zip(current,target)) if a!=b}<=owned,'unrelated catalog byte changed')
            add('catalog-'+str(block),'catalog',block,current,bytes(target),group['fields'])
        target=bytearray(header);struct.pack_into('>I',target,1072,free-len(tails))
        add('primary-header','primary',0,header,bytes(target),[dict(offset=1072,bytes=4,value=free-len(tails))])
        expected_header=bytes(target)
    finally:h.close()
    intervals=sorted((r['block']*BLOCK,r['block']*BLOCK+r['bytes']) for r in ranges)
    require(all(0<=a<z<=VOLUME for a,z in intervals) and all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),
            'restore physical ranges overlap or leave root volume')
    require(sum(r['bytes'] for r in ranges)<=MAX_BYTES and len(ranges)<=MAX_RANGES and
        len([r for r in ranges if r['kind']=='data'])==6,'restore byte/range bound exceeded')
    require(io.read(0,BLOCK)==header and sha(io.read(journal['offset'],journal['size']))==journal['journal_sha256'],
        'metadata changed during restore preparation')
    result=dict(state='prepared-dynamic-core340-restoration',base_plan_sha256=sha(raw),ranges=ranges,
        write_bytes=sum(r['bytes'] for r in ranges),range_count=len(ranges),reclaimed_blocks=tails,
        free_blocks_before=free,free_blocks_after=free-len(tails),postboot_header_sha256=sha(header),
        expected_header_sha256=sha(expected_header),alternate_sha256=sha(alternate),journal=journal,
        attribute_record_types=counts,device_writes=0)
    if out is not None:
        out.mkdir()
        for name,pair in images.items():
            for suffix,value in zip(('current','target'),pair):(out/(name+'-'+suffix+'.bin')).write_bytes(value)
        with (out/'restore-plan.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    return result,images


def verify_originals(plan_dir,recipe,images,io,HFS,Remote):
    identity_gate(io);plan=json.loads((plan_dir/'install-plan.json').read_text())
    for row in recipe['ranges']:
        require(io.read(row['block']*BLOCK,row['bytes'])==images[row['name']][1],'final restore range mismatch')
    require(sha(io.read(0,BLOCK))==recipe['expected_header_sha256'] and
        sha(io.read(VOLUME-BLOCK,BLOCK))==recipe['alternate_sha256'],'final primary/alternate mismatch')
    h=HFS(stream=Remote(io),size=VOLUME)
    try:
        for name,row in plan['rows'].items():
            file=h.paths[row['path']];fork=file['data']
            require(file['id']==row['cnid'] and (file['uid'],file['gid'],file['mode'])==(0,0,row['mode']) and
                fork['logical']==row['old_logical'] and fork['blocks']==row['data_blocks'] and
                fork['extents']==[[row['data_block'],row['data_blocks']]],'original metadata differs: '+name)
            require(sha(h.content(row['path']))==row['old_file_sha256'] and
                sha(io.read(row['data_block']*BLOCK,row['data_blocks']*BLOCK))==row['old_data_sha256'],
                'original logical/allocated bytes differ: '+name)
        bitmap=h.fork_read(h.special['allocation'])
        require(h.blocks-sum(n.bit_count() for n in bitmap)==struct.unpack_from('>I',h.header,48)[0]==recipe['free_blocks_after'],
                'restored bitmap/free count mismatch')
        require(all(bitmap[n//8]&(1<<(7-n%8)) for row in plan['rows'].values() for n in range(
            row['data_block'],row['data_block']+row['data_blocks'])),'restored original allocation has free blocks')
    finally:h.close()
    inspect_journal(io,io.read(0,BLOCK),require_empty=True)


def apply(plan_dir,capture_dir,approval,io,HFS,Remote,out,report):
    raw=(plan_dir/'install-plan.json').read_bytes()
    require(approval.get('approved') is True and approval.get('one_shot') is True and
        approval.get('plan_sha256')==sha(raw) and all(approval.get(k) is True for k in (
        'allow_restore','allow_rollback','allow_original_tail_reclaim','allow_completed_journal_header',
        'allow_primary_free_count_update')),'fresh0340 restoration-policy approval required')
    if approval.get('fixture_only'):require(getattr(io,'model_only',False) is True,'fixture cannot reach native IO')
    recipe,images=prepare(plan_dir,capture_dir,io,HFS,Remote,out)
    for block,digest in recipe['journal']['home_block_sha256'].items():
        require(sha(io.read(int(block)*BLOCK,BLOCK))==digest,'journal home changed before restore')
    for row in recipe['ranges']:
        require(io.read(row['block']*BLOCK,row['bytes'])==images[row['name']][0],'restore preimage changed before first write')
    mapping={'0337-six-files-and-original-C4-allocation-restored':'restore-applied-and-readback-verified',
        'rescue-applying':'core340-restoring','rescue-failed-preimages-restored':'restore-failed-rollback-verified',
        'rescue-failed-rollback-incomplete':'restore-failed-rollback-incomplete'}
    def mapped(value):report(dict(value,state=mapping[value['state']]))
    result=ENGINE.apply_ranges(recipe,images,io,mapped,
        lambda:verify_originals(plan_dir,recipe,images,io,HFS,Remote))
    result['state']=mapping[result['state']]
    result.update(base_plan_sha256=recipe['base_plan_sha256'],prepared_ranges=recipe['range_count'],
        prepared_write_bytes=recipe['write_bytes'],reclaimed_blocks=recipe['reclaimed_blocks'],
        journal_completed_without_home_replay=True,alternate_unchanged=True,device_boots=0)
    return result
