#!/usr/bin/env python3
"""Independent field/range/layout review plus read-only virtual HFS extraction."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess
import sys

WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/queue-loss-337'
MAIN=Path('/Users/baai/Project/ios-gauguin')


def sha(data):return hashlib.sha256(data).hexdigest()


def load(path):return json.loads(path.read_text())


class ReadOnlyOverlay:
    def __init__(self,base,patches):self.base=base;self.patches=patches
    def identity(self):return self.base.identity()
    def read(self,offset,n):
        data=bytearray(self.base.read(offset,n))
        for at,b in self.patches:
            lo=max(offset,at);hi=min(offset+n,at+len(b))
            if lo<hi:data[lo-offset:hi-offset]=b[lo-at:hi-at]
        return bytes(data)


def main():
    folder=BASE/'trim-rescue';raw=(folder/'rescue-plan.json').read_bytes();plan=json.loads(raw)
    install=load(BASE/'slot-delta/install-plan.json');model=load(folder/'model-result.json')
    assert model['state']=='model-0337-trim-rescue-passed' and model['successful']
    assert model['plan_sha256']==sha(raw) and model['all_14_partial_write_failures_restored']
    assert model['rollback_failure_keeps_empty_journal'] and model['device_writes']==0
    assert model['source_sha256']==sha((WORK/'tools/test-queue337-trim-rescue.py').read_bytes())
    # Compile ACTUAL vendored packed HFS types and verbatim journal typedefs.
    # hfs_journal.h kernel locking includes are omitted; typedefs are unaltered.
    source=(MAIN/'deps/mirror/hfs/core/hfs_journal.h').read_text()
    names=['_blk_info','block_info','block_list_header','journal_header'];types=[]
    for name in names:
        match=re.search(r'typedef struct '+re.escape(name)+r' \{',source)
        assert match,name
        depth=1;at=match.end()
        while depth:
            if source[at]=='{':depth+=1
            elif source[at]=='}':depth-=1
            at+=1
        end=source.index(';',at)+1
        types.append(source[match.start():end])
    code='''#include <sys/types.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include "hfs_format.h"
'''+ '\n'.join(types)+'''
_Static_assert(sizeof(HFSPlusVolumeHeader)==512,"VH size");
_Static_assert(offsetof(HFSPlusVolumeHeader,freeBlocks)==48,"free count");
_Static_assert(offsetof(HFSPlusForkData,totalBlocks)==12,"fork blocks");
_Static_assert(offsetof(HFSPlusForkData,extents)==16,"fork extents");
_Static_assert(offsetof(JournalInfoBlock,offset)==36,"JIB offset");
_Static_assert(offsetof(JournalInfoBlock,size)==44,"JIB size");
_Static_assert(sizeof(block_info)==16,"block info");
_Static_assert(offsetof(block_list_header,binfo)==16,"block info offset");
_Static_assert(offsetof(journal_header,start)==8,"journal start");
_Static_assert(offsetof(journal_header,end)==16,"journal end");
_Static_assert(offsetof(journal_header,checksum)==36,"journal checksum");
_Static_assert(offsetof(journal_header,sequence_num)==44,"journal checksum length");
int main(void){puts("actual HFS packed and verbatim journal layouts passed");return 0;}
'''
    c=folder/'actual-layout.c';c.write_text(code)
    command=['xcrun','--sdk','macosx','clang','-std=c11','-Wall','-Wextra','-Werror',
             '-D__APPLE_API_UNSTABLE','-I'+str(MAIN/'deps/mirror/hfs/core'),str(c),'-o',str(folder/'actual-layout')]
    p=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (folder/'actual-layout-compile.log').write_text(p.stdout);assert p.returncode==0,p.stdout
    layout=subprocess.run([str(folder/'actual-layout')],capture_output=True,text=True,check=True).stdout.strip()
    assert plan['state']=='prepared-exact-0337-trim-rescue' and plan['write_ranges']==14
    rows=plan['ranges'];assert len(rows)==14 and sum(r['bytes'] for r in rows)==10313728
    expected_catalog={}
    for name,r in install['rows'].items():
        expected_catalog.setdefault(r['catalog_block'],[]).append((r['catalog_offset'],8,r['old_logical']))
        if name=='c4':expected_catalog[r['catalog_block']]+=[(r['catalog_offset']+12,4,105),(r['catalog_offset']+20,4,105)]
    patches=[];current_images={};diffs={}
    for r in rows:
        old=(folder/(r['name']+'-current.bin')).read_bytes()
        new=(folder/(r['name']+'-target.bin')).read_bytes()
        assert len(old)==len(new)==r['bytes'] and sha(old)==r['current_sha256'] and sha(new)==r['target_sha256']
        expected=bytearray(old);fields=[]
        if r['kind']=='journal':
            assert r['block']==3168598 and len(old)==4096
            assert struct.unpack_from('<QQ',old,8)==(4910592,8338944)
            struct.pack_into('<Q',expected,8,8338944);expected[36:40]=bytes(4)
            value=0
            for byte in expected[:44]:value=((value*256)^(value+byte))&0xffffffff
            struct.pack_into('<I',expected,36,(~value)&0xffffffff)
            fields=[(8,8),(36,4)]
            assert struct.unpack_from('<QQ',new,8)==(8338944,8338944)
        elif r['kind']=='bitmap':
            assert r['block']==117 and old[2100]&15==0
            expected[2100]|=15;fields=[(2100,1)]
        elif r['kind']=='primary':
            assert r['block']==0 and struct.unpack_from('>I',old,1072)[0]==404889
            struct.pack_into('>I',expected,1072,404885);fields=[(1072,4)]
        elif r['kind']=='data':
            name=r['name'].removesuffix('-data');original=install['rows'][name]
            assert r['block']==original['data_block'] and r['bytes']==original['data_blocks']*4096
            assert sha(new)==original['old_data_sha256']
            assert sha(new[:original['old_logical']])==original['old_file_sha256']
            assert sha(old[:original['new_logical']])==original['new_file_sha256']
            assert new==(BASE/'slot-capture'/(name+'-old-data.bin')).read_bytes()
            expected[:]=new;fields=[(0,len(new))]
        else:
            assert r['kind']=='catalog' and r['block'] in expected_catalog
            for at,n,value in expected_catalog.pop(r['block']):
                struct.pack_into('>Q' if n==8 else '>I',expected,at,value);fields.append((at,n))
        assert bytes(expected)==new,r['name']
        changed={i for i,(a,b) in enumerate(zip(old,new)) if a!=b}
        allowed={i for at,n in fields for i in range(at,at+n)}
        assert changed and changed<=allowed
        if r['kind']!='data':diffs[r['name']]=dict(changed_bytes=len(changed),allowed_fields=fields)
        patches.append((r['block']*4096,new));current_images[r['block']]=old
    assert not expected_catalog
    assert [r['kind'] for r in rows]==['journal','bitmap']+['data']*6+['catalog']*5+['primary']
    intervals=sorted((at,at+len(b)) for at,b in patches)
    assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
    assert all(end<=17179869184 for begin,end in intervals)
    assert all(at!=17179869184-4096 for at,_ in patches)
    # Independently extract the proposed HFS contents using the canonical
    # packed-layout reader over real read-only blocks + exact target overlays.
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
                  str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    io=RecoveryIO();identity=io.identity();assert identity['state']=='recovery' and identity['product']=='gauguin'
    assert identity['unmounted'] and identity['no_holders']
    for r in rows:assert io.read(r['block']*4096,r['bytes'])==current_images[r['block']]
    assert sha(io.read(17179869184-4096,4096))==plan['guard']['alternate_sha256']
    overlay=ReadOnlyOverlay(io,patches);remote=Remote(overlay);h=HFS(stream=remote,size=17179869184)
    extracted={}
    try:
        for name,r in install['rows'].items():
            file=h.paths[r['path']];fork=file['data']
            assert file['id']==r['cnid'] and (file['uid'],file['gid'],file['mode'])==(0,0,r['mode'])
            assert fork['logical']==r['old_logical'] and fork['blocks']==r['data_blocks']
            assert fork['extents']==[[r['data_block'],r['data_blocks']]]
            data=h.content(r['path']);assert sha(data)==r['old_file_sha256']
            assert sha(overlay.read(r['data_block']*4096,r['data_blocks']*4096))==r['old_data_sha256']
            extracted[name]=dict(original_contents_and_allocation=True,cnid=file['id'],logical=len(data),blocks=fork['blocks'])
        bitmap=h.fork_read(h.special['allocation'])
        assert h.blocks-sum(b.bit_count() for b in bitmap)==struct.unpack_from('>I',h.header,48)[0]==404885
        assert all(bitmap[n//8]&(1<<(7-n%8)) for n in range(3817892,3817896))
    finally:h.close()
    assert not (folder/'approval.json').exists() and not (folder/'execute-claim.json').exists()
    inputs=[Path(__file__),WORK/'tools/restore-queue337-trim.py',WORK/'tools/test-queue337-trim-rescue.py',
            folder/'rescue-plan.json',folder/'model-result.json',folder/'actual-layout.c',
            WORK/'docs/gauguin-queue-loss-337-trim-rescue-20261116.md']
    result=dict(state='reviewed-0337-trim-rescue',plan_sha256=sha(raw),model_passed=True,
        independent_metadata_review_passed=True,actual_C_layout=layout,layout_command=command,
        exact_metadata_differences=diffs,virtual_original_files=extracted,
        forward_bytes=10313728,including_failure_rollback_bytes=20627456,
        alternate_header_unchanged=True,unmounted_attribute_unchanged=True,
        virtual_HFS_bitmap_free_count_agrees=True,no_device_mutation_method_in_overlay=True,
        frozen_trial_result_preserved=True,device_writes=0,device_boots=0,
        input_pins={str(p):sha(p.read_bytes()) for p in inputs})
    with (folder/'independent-review.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','layout_command','virtual_original_files','exact_metadata_differences')},indent=2))


if __name__=='__main__':main()
