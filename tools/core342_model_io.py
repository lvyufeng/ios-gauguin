"""Actual metadata snapshot overlay; model writes never reach its base file."""
from pathlib import Path
import hashlib
import json
import subprocess
import zlib
from core342_slots import split_allocation

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/io-path-342'


def sha(data):return hashlib.sha256(data).hexdigest()


class Snapshot:
    def __init__(self,base=BASE,*,resources=None):
        folder=base/'metadata-snapshot';self.result=json.loads((folder/'result.json').read_text())
        self.parts=[]
        for part in self.result['parts']:
            compressed=(folder/part['file']).read_bytes();assert sha(compressed)==part['compressed_sha256']
            decoder=zlib.decompressobj();data=decoder.decompress(compressed,part['bytes']+1)+decoder.flush()
            assert decoder.eof and not decoder.unused_data and len(data)==part['bytes'] and sha(data)==part['sha256']
            self.parts.append((part['offset'],data))
        self.backup = None
        if resources is None:
            backup=json.loads((MAIN/'research/tmp/metal-hardware-20261112/backup/result.json').read_text())
            self.backup=Path(backup['backup']);assert self.backup.stat().st_size==17179869184
        else:
            receipt = json.loads(resources.read_text())
            assert receipt['root_header_sha256'] == self.result['root_header_sha256']
            for row in receipt['ranges']:
                data = (resources.parent / row['file']).read_bytes()
                assert len(data) == row['bytes'] and sha(data) == row['sha256']
                assert row['offset'] % 4096 == len(data) % 4096 == 0
                self.parts.append((row['offset'], data))
        capture=json.loads((base/'slot-capture/result.json').read_text())
        names={row['path']:name for name,row in json.loads((base/'slot-delta/install-plan.json').read_text())['rows'].items()}
        for path,row in capture['files'].items():
            data=(base/'slot-capture'/(names[path]+'-old-data.bin')).read_bytes()
            assert sha(data)==row['data_alloc_sha256']
            extents = row.get('data_extents', [[row['data_block'], row['data_blocks']]])
            self.parts.extend((start*4096,part) for start,part in split_allocation(extents,data))
        intervals=sorted((at,at+len(data)) for at,data in self.parts)
        assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
        self.misc=(folder/'misc-original.bin').read_bytes()

    def io(self):return ModelIO(self)


class ModelIO:
    model_only=True
    adb=['MODEL-NO-DEVICE']
    def __init__(self,snapshot):
        self.snapshot=snapshot;self.base=snapshot.backup.open('rb') if snapshot.backup else None;self.changes={}
        self.writes=0;self.bytes=0;self.fail_at=None;self.rollback_fail=False;self.failed=False;self.rollback_failed=False
    def close(self):
        if self.base is not None:
            self.base.close()
    def identity(self):return dict(state='recovery',product='gauguin',partition_bytes=114919714816,unmounted=True,no_holders=True)
    def read(self,offset,n):
        assert offset%4096==n%4096==0 and 0<=offset<offset+n<=17179869184
        present = None
        if self.base is None:
            result = bytearray(n)
            present = bytearray(n // 4096)
        else:
            self.base.seek(offset);result=bytearray(self.base.read(n));assert len(result)==n
        for at,data in self.snapshot.parts:
            lo=max(at,offset);hi=min(at+len(data),offset+n)
            if lo<hi:
                result[lo-offset:hi-offset]=data[lo-at:hi-at]
                if present is not None:
                    present[(lo-offset)//4096:(hi-offset)//4096] = b'\x01' * ((hi-lo)//4096)
        for at in range(offset,offset+n,4096):
            if at in self.changes:
                result[at-offset:at-offset+4096]=self.changes[at]
                if present is not None:
                    present[(at-offset)//4096] = 1
        if present is not None and not all(present):
            missing = offset + present.index(0) * 4096
            raise ValueError(f'uncaptured model block at {missing}')
        return bytes(result)
    def overwrite(self,offset,data):
        first=offset//4096*4096;end=(offset+len(data)+4095)//4096*4096
        if first == offset and end == offset + len(data):
            raw = data
        else:
            raw=bytearray(self.read(first,end-first));raw[offset-first:offset-first+len(data)]=data
        for at in range(first,end,4096):self.changes[at]=bytes(raw[at-first:at-first+4096])
    def write(self,offset,data):
        self.writes+=1;self.bytes+=len(data)
        if self.writes==self.fail_at:
            self.overwrite(offset,data[:max(1,len(data)//2)]);self.failed=True
            raise OSError('model partial forward write')
        if self.failed and self.rollback_fail and not self.rollback_failed:
            self.overwrite(offset,bytes([data[0]^1]));self.rollback_failed=True
            raise OSError('model partial rollback failure')
        self.overwrite(offset,data)
    def sync(self):pass
    def run(self,argv):
        assert argv[:1]==self.adb and 'if=/dev/block/by-name/misc' in argv[-1]
        return subprocess.CompletedProcess(argv,0,stdout=self.snapshot.misc,stderr=b'')
