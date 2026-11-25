#!/usr/bin/env python3
"""Actual compressed HFS metadata, real delta, all restore partial-write faults."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import struct
import subprocess
import sys
from core341_hfs import checksum,inspect_journal,sha
from core341_model_io import Snapshot,MAIN,WORK,BASE
import core341_install as INSTALL
import core341_restore as RESTORE

sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
             str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112')]
from local_hfs175v3 import HFS
from metal_ca_c5_delta import Remote


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')


def geometry(io,plan):
    h=HFS(stream=Remote(io),size=17179869184)
    try:
        bits={}
        for row in plan['rows'].values():
            for block in range(row['data_block'],row['data_block']+row['data_blocks']):
                spans=list(h.spans(h.special['allocation'],block//8,1));assert len(spans)==1
                physical=spans[0][0];bits[block]=(physical//4096,physical%4096,1<<(7-block%8))
        other=h.paths['/System/Library/Extensions/GauguinMetalDesktop.bundle/_CodeSignature/CodeResources']
        span=list(h.spans(h.catalog,other['catalog_bsd_offset']+136,80));assert len(span)==1
        return bits,span[0][0]
    finally:h.close()


def trim(io,plan,bits,names):
    freed=[]
    for name in names:
        row=plan['rows'][name];count=(row['new_logical']+4095)//4096
        tail=list(range(row['data_block']+count,row['data_block']+row['data_blocks']))
        cat=bytearray(io.read(row['catalog_block']*4096,4096));at=row['catalog_offset']
        struct.pack_into('>I',cat,at+12,count);struct.pack_into('>I',cat,at+20,count)
        io.overwrite(row['catalog_block']*4096,cat)
        for block in tail:
            physical,at,mask=bits[block];raw=bytearray(io.read(physical*4096,4096));assert raw[at]&mask
            raw[at]&=~mask;io.overwrite(physical*4096,raw)
            io.overwrite(block*4096,bytes(4096)) # freed data may already be discarded
        freed+=tail
    if freed:
        primary=bytearray(io.read(0,4096));free=struct.unpack_from('>I',primary,1072)[0]
        struct.pack_into('>I',primary,1072,free+len(freed));io.overwrite(0,primary)
    return freed


def synthetic_journal(io,blocks,extra=False):
    offset=12978577408;size=8388608;blsize=94208;start=512
    old=io.read(offset,4096);raw=bytearray(size);raw[:4096]=old
    def transaction(at,sequence):
        used=blsize+len(blocks)*4096;header=bytearray(blsize)
        struct.pack_into('<HHIII',header,0,(blsize-16)//16,len(blocks)+1,used,0,3)
        struct.pack_into('<I',header,28,sequence)
        for index,block in enumerate(blocks,1):
            data=io.read(block*4096,4096)
            struct.pack_into('<qiI',header,16+16*index,block*8,4096,checksum(data))
            raw[at+blsize+(index-1)*4096:at+blsize+index*4096]=data
        struct.pack_into('<I',header,8,checksum(header[:32]));raw[at:at+blsize]=header
        return at+used
    end=transaction(start,77)
    if extra:transaction(end,78)
    struct.pack_into('<QQ',raw,8,start,end);struct.pack_into('<I',raw,44,77)
    raw[36:40]=bytes(4);struct.pack_into('<I',raw,36,checksum(raw[:44]))
    io.overwrite(offset,raw)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists();out.mkdir()
    plan_dir=BASE/'slot-delta';capture=BASE/'slot-capture';plan_raw=(plan_dir/'install-plan.json').read_bytes();plan=json.loads(plan_raw)
    snapshot=Snapshot();initial=snapshot.io()
    approved=dict(approved=True,one_shot=True,fixture_only=True,plan_sha256=sha(plan_raw),
        source='fixture-only0341-model-not-user-authorization',allow_install=True,allow_restore=True,
        allow_rollback=True,allow_original_tail_reclaim=True,allow_completed_journal_header=True,allow_primary_free_count_update=True)
    save(out/'fixture-only-approval.json',approved)
    checks=[];bits,resource=geometry(initial,plan)
    install=INSTALL.install(plan_dir,capture,approved,initial,HFS,Remote,lambda _:None)
    assert install['state']=='install-applied-and-HFSX-verified'
    h=HFS(stream=Remote(initial),size=17179869184)
    try:
        signatures=[]
        for name,row in plan['rows'].items():
            data=h.content(row['path']);assert sha(data)==row['new_file_sha256']
            if name not in ('eagl','admission','c4','core'):continue
            path=out/(name+'-independent-HFS-extract.bin')
            if name=='c4':
                bundle=out/'GauguinMetalDesktop.bundle';bundle.mkdir();(bundle/'_CodeSignature').mkdir()
                root='/System/Library/Extensions/GauguinMetalDesktop.bundle/'
                for resource_leaf in ('Info.plist','_CodeSignature/CodeResources'):
                    (bundle/resource_leaf).write_bytes(h.content(root+resource_leaf))
                path=bundle/'GauguinMetalDesktop'
            path.write_bytes(data)
            verified=subprocess.run(['codesign','--verify','--strict',str(path)],capture_output=True,text=True)
            assert verified.returncode==0,verified.stderr
            signatures.append(dict(name=name,sha256=sha(data),signature_verified=True))
        save(out/'independent-candidate-signatures.json',dict(checks=signatures,device_writes=0))
    finally:h.close()
    checks.append('actual-HFS-six-candidate-contents-and-four-strict-signatures')
    installed=dict(initial.changes);initial.close();checks.append('actual-delta-installs-in-complete-live-metadata-view')
    def io():
        value=snapshot.io();value.changes=dict(installed);return value
    full_recipe=None;full_images=None;full_changes=None
    for label,names,journal in [('empty-untrimmed',[],False),('C4-trim',['c4'],False),
        ('C4-core-trim-completed-journal',['c4','core'],True),('all-four-MachO-trims',['eagl','admission','c4','core'],True)]:
        model=io()
        try:
            freed=trim(model,plan,bits,names)
            if journal:synthetic_journal(model,[0,plan['rows']['c4']['catalog_block']])
            recipe,images=RESTORE.prepare(plan_dir,capture,model,HFS,Remote)
            assert recipe['reclaimed_blocks']==sorted(freed) and recipe['write_bytes']<=10330112 and recipe['range_count']<=18
            if label=='all-four-MachO-trims':
                full_recipe,full_images,full_changes=recipe,images,dict(model.changes)
                assert len([r for r in recipe['ranges'] if r['kind']=='bitmap'])==4
            result=RESTORE.apply(plan_dir,capture,approved,model,HFS,Remote,None,lambda _:None)
            assert result['state']=='restore-applied-and-readback-verified' and result['rollback_bytes']==0
            verifier=RESTORE.module('independent_model_verify340','verify-core341-restore.py')
            verified=verifier.verify(model,plan_dir,HFS,Remote,lambda:snapshot.misc,
                recipe['expected_header_sha256'],recipe['alternate_sha256'])
            assert verified['all_original_slot_bits_allocated'] and verified['journal_empty']
            checks.append(label+'-restored-original-logical-allocated-bytes-and-forks')
            save(out/(label+'.json'),dict(recipe=recipe,result=result))
        finally:model.close()
    # Inject every partial write against the largest actual policy recipe.
    for index in range(1,len(full_recipe['ranges'])+1):
        model=io();model.changes=dict(full_changes);model.fail_at=index
        try:
            result=RESTORE.ENGINE.apply_ranges(full_recipe,full_images,model,lambda _:None,lambda:None)
            assert result['state']=='rescue-failed-preimages-restored'
            assert model.bytes<=2*10330112
            for row in full_recipe['ranges']:
                assert model.read(row['block']*4096,row['bytes'])==full_images[row['name']][0]
            checks.append('partial-restore-range-'+str(index)+'-exact-preimages')
        finally:model.close()
    model=io();model.changes=dict(full_changes);model.fail_at=3;model.rollback_fail=True
    try:
        result=RESTORE.ENGINE.apply_ranges(full_recipe,full_images,model,lambda _:None,lambda:None)
        assert result['state']=='rescue-failed-rollback-incomplete' and not result['reboot_permitted']
        assert struct.unpack_from('<QQ',model.read(12978577408,4096),8)[0]==struct.unpack_from('<QQ',model.read(12978577408,4096),8)[1]
        assert model.bytes<=2*10330112;checks.append('rollback-failure-keeps-journal-empty-no-reboot')
    finally:model.close()
    for fault in ('final-verification','receipt-write'):
        model=io();model.changes=dict(full_changes);reported=False
        def report(row):
            nonlocal reported
            if fault=='receipt-write' and row['state']=='0337-six-files-and-original-C4-allocation-restored' and not reported:
                reported=True;raise OSError('model receipt failure')
        def verify():
            if fault=='final-verification':raise ValueError('model independent readback failure')
        try:
            result=RESTORE.ENGINE.apply_ranges(full_recipe,full_images,model,report,verify)
            assert result['state']=='rescue-failed-preimages-restored' and model.bytes<=2*10330112
            for row in full_recipe['ranges']:
                assert model.read(row['block']*4096,row['bytes'])==full_images[row['name']][0]
            checks.append(fault+'-exact-preimages')
        finally:model.close()
    for index in range(1,12):
        model=snapshot.io();model.fail_at=index
        try:
            result=INSTALL.install(plan_dir,capture,approved,model,HFS,Remote,lambda _:None)
            assert result['state']=='install-failed-rollback-verified' and model.bytes<=2*10301440
            original=snapshot.io()
            try:
                for at,data in model.changes.items():assert original.read(at,4096)==data
            finally:original.close()
            checks.append('partial-install-range-'+str(index)+'-exact-preimages')
        finally:model.close()
    for fault in ('nonempty-install-journal','fixture-on-native-IO'):
        model=snapshot.io()
        try:
            if fault=='nonempty-install-journal':synthetic_journal(model,[0])
            else:model.model_only=False
            try:INSTALL.preflight(plan_dir,capture,approved,model,HFS,Remote)
            except (ValueError,AssertionError):pass
            else:raise AssertionError('accepted '+fault)
            assert model.writes==0;checks.append(fault+'-refused-before-write')
        finally:model.close()
    for fault in ('unapplied-journal','bad-journal-checksum','valid-extra-journal','tail-reused','tail-resource-owner','data-relocation','allocation-growth'):
        model=io()
        try:
            freed=trim(model,plan,bits,['c4','core'])
            synthetic_journal(model,[0,plan['rows']['c4']['catalog_block']],extra=fault=='valid-extra-journal')
            if fault=='unapplied-journal':
                at=plan['rows']['c4']['catalog_block']*4096+4000;model.overwrite(at,b'\x93')
            elif fault=='bad-journal-checksum':model.overwrite(12978577408+36,b'\x99')
            elif fault=='tail-reused':
                block,at,mask=bits[freed[0]];data=bytearray(model.read(block*4096,4096));data[at]|=mask;model.overwrite(block*4096,data)
                data=bytearray(model.read(0,4096));struct.pack_into('>I',data,1072,struct.unpack_from('>I',data,1072)[0]-1);model.overwrite(0,data)
                synthetic_journal(model,[0,plan['rows']['c4']['catalog_block']])
            elif fault=='tail-resource-owner':
                data=bytearray(80);struct.pack_into('>QII',data,0,4096,0,1);struct.pack_into('>II',data,16,freed[0],1);model.overwrite(resource,data)
            elif fault in ('data-relocation','allocation-growth'):
                row=plan['rows']['c4'];at=row['catalog_block']*4096+row['catalog_offset'];data=bytearray(model.read(row['catalog_block']*4096,4096))
                if fault=='data-relocation':struct.pack_into('>I',data,row['catalog_offset']+16,row['data_block']+1)
                else:
                    struct.pack_into('>I',data,row['catalog_offset']+12,row['data_blocks']+1)
                    struct.pack_into('>I',data,row['catalog_offset']+20,row['data_blocks']+1)
                model.overwrite(row['catalog_block']*4096,data);synthetic_journal(model,[0,row['catalog_block']])
            model.writes=0
            try:RESTORE.prepare(plan_dir,capture,model,HFS,Remote)
            except (ValueError,AssertionError):pass
            else:raise AssertionError('accepted '+fault)
            assert model.writes==0;checks.append(fault+'-refused-before-write')
        finally:model.close()
    # Replay the actual0337 journal observation in memory, not only synthetic
    # fixtures. All its home blocks were captured independently in that run.
    prior=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/execution/allocation-inspection'
    model=io()
    try:
        model.overwrite(0,(prior/'primary-block.bin').read_bytes())
        model.overwrite(3170646*4096,(prior/'journal-info-block.bin').read_bytes())
        model.overwrite(12978577408,(prior/'journal-full.bin').read_bytes())
        for p in (prior/'journal-home-blocks').glob('*-current.bin'):
            model.overwrite(int(p.name.split('-')[0])*4096,p.read_bytes())
        actual,*_=inspect_journal(model,model.read(0,4096))
        assert len(actual['chunks'])==17 and actual['coalesced_sectors']==1048
        checks.append('actual0337-journal-17-chunks1048-sectors-home-equality-reproduced')
    finally:model.close()
    paths=[Path(__file__),WORK/'tools/core341_restore.py',WORK/'tools/core341_install.py',WORK/'tools/core341_hfs.py',
           WORK/'tools/core341_model_io.py',WORK/'tools/verify-core341-restore.py',plan_dir/'install-plan.json',BASE/'metadata-snapshot/result.json',BASE/'slot-capture/result.json']
    result=dict(state='0341-live-metadata-install-and-tail-journal-restore-models-passed',checks=checks,
        install_ranges=11,all_restore_partial_write_points=len(full_recipe['ranges']),
        maximum_actual_model_restore_bytes=full_recipe['write_bytes'],frozen_restore_limit_bytes=10330112,
        policy_maximum_ranges=18,original_allocation_bitmap_pages=4,
        complete_actual_metadata_overlay=True,all_model_IO_writes_memory_only=True,device_writes=0,device_boots=0,
        input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    save(out/'result.json',result);print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
