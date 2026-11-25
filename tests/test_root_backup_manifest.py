#!/usr/bin/env python3
"""Native SHA2 vectors and bounded reconstruction corruption/error controls."""
from pathlib import Path
import hashlib
import os
import struct
import subprocess
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from root_backup_manifest import decode, reconstruct


def main():
    binary = sys.argv[1]; checks = 0
    with tempfile.TemporaryDirectory(prefix='root-backup-manifest-') as temp:
        root = Path(temp); sample = root/'sample'
        for n in [0,1,3,55,56,63,64,65,119,120,127,128,129,4096,1048576,1048577]:
            data = bytes((i*29+17)&255 for i in range(n)); sample.write_bytes(data)
            for piece in [1,63,64,65,1048576] if n < 4096 else [127,1048576]:
                got = subprocess.check_output([binary,'--hash',str(sample),str(piece)],text=True).strip()
                assert got == hashlib.sha256(data).hexdigest(); checks += 1
        chunk = 1048576
        fresh = b''.join(bytes([i+17])*chunk for i in range(4)); sample.write_bytes(fresh+b'extra')
        raw = subprocess.check_output([binary,'--manifest',str(sample),str(len(fresh))])
        scan = decode(raw,volume=len(fresh),partition=len(fresh)+5)
        assert scan['whole'] == hashlib.sha256(fresh).digest()
        assert scan['chunks'] == [hashlib.sha256(fresh[i*chunk:(i+1)*chunk]).digest()for i in range(4)]
        clone = root/'clone'; bad=bytearray(fresh);bad[chunk+3]^=1;bad[2*chunk+4]^=1;clone.write_bytes(bad)
        calls=[]
        def fetch(at,n):calls.append((at,n));return fresh[at:at+n]
        with clone.open('r+b')as f:result=reconstruct(f,scan,fetch,max_changed_bytes=2*chunk)
        assert clone.read_bytes()==fresh and calls==[(chunk,2*chunk)] and result['all_chunks_verified']==4;checks+=3
        for variant in [raw[:-1],raw+b'x',b'BADSCAN!'+raw[8:],raw[:8]+struct.pack('<Q',3*chunk)+raw[16:]]:
            try:decode(variant,volume=len(fresh),partition=len(fresh)+5)
            except ValueError:checks+=1
            else:raise AssertionError('bad manifest accepted')
        for mode in ['budget','reserve','short','changed']:
            clone.write_bytes(bad);calls=[]
            def failfetch(at,n):
                calls.append((at,n))
                return fresh[at:at+n-1]if mode=='short'else bytes([0])*n
            with clone.open('r+b')as f:
                try:reconstruct(f,scan,failfetch,max_changed_bytes=chunk if mode=='budget'else 4*chunk,
                                reserve=lambda n:mode!='reserve')
                except ValueError:checks+=1
                else:raise AssertionError('failure path accepted')
            assert clone.read_bytes()==bad
            if mode in ['budget','reserve']:assert not calls
        wrong=dict(scan,whole=bytes(32));clone.write_bytes(fresh)
        with clone.open('r+b')as f:
            try:reconstruct(f,wrong,fetch)
            except ValueError:checks+=1
            else:raise AssertionError('wrong whole-volume hash accepted')
    print(f'PASS {checks} SHA2 vectors/manifest/reconstruction/corruption/budget checks; no device IO')


if __name__=='__main__':
    main()
