#!/usr/bin/env python3
"""Independently read back the original four files and misc after restoration."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/sb-cadence-312'


def sha(data):return hashlib.sha256(data).hexdigest()


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    assert args.out.resolve().is_relative_to(STATE) and not args.out.exists()
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
                  str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112'),str(MAIN/'tools')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    from recovery_marker import READ
    plan_raw=(STATE/'slot-delta/install-plan.json').read_bytes()
    plan=json.loads(plan_raw)
    assert plan['state']=='prepared-four-file-SpringBoard-cadence-delta' and len(plan['rows'])==4
    io=RecoveryIO();identity=io.identity()
    assert identity['state']=='recovery' and identity['product']=='gauguin'
    assert identity['unmounted'] and identity['no_holders'] and identity['partition_bytes']==114919714816
    header=io.read(0,4096)
    remote=Remote(io);hfs=HFS(stream=remote,size=17179869184)
    files={}
    try:
        for name,row in plan['rows'].items():
            file=hfs.paths[row['path']];fork=file['data']
            assert file['type']==2 and not file['flags']&0x20 and file['id']==row['cnid']
            assert (file['uid'],file['gid'],file['mode'])==(0,0,row['mode'])
            assert fork['logical']==row['old_logical'] and fork['blocks']==row['data_blocks']
            assert fork['extents']==[[row['data_block'],row['data_blocks']]]
            assert sha(hfs.content(row['path']))==row['old_file_sha256']
            allocated=io.read(row['data_block']*4096,row['data_blocks']*4096)
            assert sha(allocated)==row['old_data_sha256']
            files[row['path']]={'original_logical_and_allocated_bytes_match':True,'cnid':file['id'],'fork':fork}
    finally:hfs.close()
    misc=io.run(io.adb+['exec-out',READ]).stdout
    assert len(misc)==4096 and sha(misc)=='ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7'
    assert io.read(0,4096)==header
    result=dict(state='independently-verified-four-original-files-and-misc',
        install_plan_sha256=sha(plan_raw),root_header_sha256=sha(header),files=files,
        misc_original_4096_bytes_match=True,catalog_read_bytes=remote.bytes,device_writes=0,device_boots=0)
    with args.out.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))


if __name__=='__main__':main()
