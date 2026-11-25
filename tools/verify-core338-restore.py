#!/usr/bin/env python3
"""Independent, read-only HFS/misc verification after the0338 writer exits."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from core338_hfs import checksum

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def verify(io,plan_dir,HFS,Remote,read_misc,expected_header=None,expected_alternate=None):
    raw=(plan_dir/'install-plan.json').read_bytes();plan=json.loads(raw)
    assert plan['state']=='prepared-six-file-core338-delta' and len(plan['rows'])==6
    identity=io.identity()
    assert identity['state']=='recovery' and identity['product']=='gauguin'
    assert identity['partition_bytes']==114919714816 and identity['unmounted'] and identity['no_holders']
    header=io.read(0,4096);alternate=io.read(17179869184-4096,4096)
    assert expected_header is None or sha(header)==expected_header
    assert expected_alternate is None or sha(alternate)==expected_alternate
    remote=Remote(io);hfs=HFS(stream=remote,size=17179869184);files={}
    try:
        bitmap=hfs.fork_read(hfs.special['allocation'])
        free=hfs.blocks-sum(byte.bit_count() for byte in bitmap)
        assert free==struct.unpack_from('>I',header,1072)[0]
        for name,row in plan['rows'].items():
            file=hfs.paths[row['path']];fork=file['data']
            assert file['type']==2 and not file['flags']&0x20 and file['id']==row['cnid']
            assert (file['uid'],file['gid'],file['mode'])==(0,0,row['mode'])
            assert fork['logical']==row['old_logical'] and fork['blocks']==row['data_blocks']
            assert fork['extents']==[[row['data_block'],row['data_blocks']]]
            assert file['resource']['logical']==file['resource']['blocks']==0 and not file['resource']['extents']
            assert sha(hfs.content(row['path']))==row['old_file_sha256']
            allocated=io.read(row['data_block']*4096,row['data_blocks']*4096)
            assert sha(allocated)==row['old_data_sha256']
            assert all(bitmap[n//8]&(1<<(7-n%8)) for n in range(row['data_block'],row['data_block']+row['data_blocks']))
            files[row['path']]=dict(original_logical_and_allocated_bytes_match=True,cnid=file['id'],fork=fork)
    finally:hfs.close()
    # Independently check the empty journal header, without accepting a pending
    # transaction or borrowing the writer's in-memory verification verdict.
    info=io.read(3170646*4096,4096)
    assert struct.unpack_from('>I',header,1036)[0]==3170646 and struct.unpack_from('>I',info,0)[0]==1
    offset,size=struct.unpack_from('>QQ',info,36);assert (offset,size)==(12978577408,8388608)
    journal=io.read(offset,4096);magic,endian,start,end,actual_size,blhdr,ck,jhdr=struct.unpack_from('<IIQQQIII',journal)
    assert magic==0x4a4e4c78 and endian==0x12345678 and start==end and 512<=start<=size and start%512==0
    assert (actual_size,blhdr,jhdr)==(size,94208,512)
    checked=bytearray(journal[:44]);checked[36:40]=bytes(4);assert checksum(checked)==ck
    misc=read_misc()
    assert len(misc)==4096 and sha(misc)=='ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7'
    assert io.read(0,4096)==header and io.read(offset,4096)==journal
    return dict(state='independently-verified-six-original-files-misc-and-empty-journal',
        install_plan_sha256=sha(raw),root_header_sha256=sha(header),alternate_sha256=sha(alternate),
        files=files,free_blocks=free,all_original_slot_bits_allocated=True,journal_empty=True,
        misc_original_4096_bytes_match=True,catalog_read_bytes=remote.bytes,device_writes=0,device_boots=0)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--expected-header');ap.add_argument('--expected-alternate');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112'),str(MAIN/'tools')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    from recovery_marker import READ
    io=RecoveryIO()
    result=verify(io,BASE/'slot-delta',HFS,Remote,lambda:io.run(io.adb+['exec-out',READ]).stdout,a.expected_header,a.expected_alternate)
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))


if __name__=='__main__':main()
