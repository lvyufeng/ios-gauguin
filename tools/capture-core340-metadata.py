#!/usr/bin/env python3
"""Read-only compressed metadata overlay for actual HFS rollback models."""
from pathlib import Path
import hashlib
import json
import sys
import zlib
from core340_hfs import inspect_journal,sha,BLOCK,VOLUME

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/draw-submit-340'


def main():
    out=BASE/'metadata-snapshot';assert not out.exists()
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
                 str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    io=RecoveryIO();identity=io.identity()
    assert identity['state']=='recovery' and identity['product']=='gauguin' and identity['unmounted'] and identity['no_holders']
    header=io.read(0,BLOCK)
    expected=json.loads((BASE/'current-root-capture/result.json').read_text())
    assert sha(header)==expected['root_header_sha256']=='46114302d51d798551816ddd5b4965182cc66e76a8d98ae04e176e6c08b16a8a'
    journal,_,_,info,raw=inspect_journal(io,header,require_empty=True)
    h=HFS(stream=Remote(io),size=VOLUME);ranges=[(0,BLOCK,'primary'),(VOLUME-BLOCK,BLOCK,'alternate'),
        (journal['info_block']*BLOCK,BLOCK,'journal-info'),(journal['offset'],journal['size'],'journal')]
    try:
        for name,fork in h.special.items():
            for position,n in h.spans(fork,0,fork['logical']):
                assert position%BLOCK==0
                ranges.append((position,(n+BLOCK-1)//BLOCK*BLOCK,name))
    finally:h.close()
    intervals=sorted((at,at+n) for at,n,_name in ranges)
    assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
    out.mkdir();parts=[];stored=0
    for at,n,name in ranges:
        for delta in range(0,n,8*1048576):
            count=min(8*1048576,n-delta);data=io.read(at+delta,count);compressed=zlib.compress(data,6)
            stored+=len(compressed);assert stored<=30*1048576
            filename=str(len(parts))+'.zlib';(out/filename).write_bytes(compressed)
            parts.append(dict(offset=at+delta,bytes=count,kind=name,file=filename,
                sha256=sha(data),compressed_sha256=sha(compressed),compressed_bytes=len(compressed)))
    assert io.read(0,BLOCK)==header
    misc=io.run(io.adb+['exec-out','dd if=/dev/block/by-name/misc bs=4096 count=1 2>/dev/null']).stdout
    assert len(misc)==BLOCK and sha(misc)=='ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7'
    (out/'misc-original.bin').write_bytes(misc)
    result=dict(state='readonly0340-complete-special-metadata-overlay',parts=parts,
        root_header_sha256=sha(header),journal=journal,uncompressed_bytes=sum(p['bytes'] for p in parts),
        compressed_bytes=stored,maximum_compressed_bytes=30*1048576,
        input_pins={str(Path(__file__)):sha(Path(__file__).read_bytes()),
                    str(WORK/'tools/core340_hfs.py'):sha((WORK/'tools/core340_hfs.py').read_bytes())},
        device_writes=0,device_boots=0)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','parts','journal')},indent=2))


if __name__=='__main__':main()
