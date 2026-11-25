"""Actual metadata snapshot overlay; model writes never reach its base file."""
from pathlib import Path
import hashlib
import json
import subprocess
import zlib

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/draw-submit-340'


def sha(data):return hashlib.sha256(data).hexdigest()


class Snapshot:
    def __init__(self):
        folder=BASE/'metadata-snapshot';self.result=json.loads((folder/'result.json').read_text())
        self.parts=[]
        for part in self.result['parts']:
            compressed=(folder/part['file']).read_bytes();assert sha(compressed)==part['compressed_sha256']
            decoder=zlib.decompressobj();data=decoder.decompress(compressed,part['bytes']+1)+decoder.flush()
            assert decoder.eof and not decoder.unused_data and len(data)==part['bytes'] and sha(data)==part['sha256']
            self.parts.append((part['offset'],data))
        backup=json.loads((MAIN/'research/tmp/metal-hardware-20261112/backup/result.json').read_text())
        self.backup=Path(backup['backup']);assert self.backup.stat().st_size==17179869184
        capture=json.loads((BASE/'slot-capture/result.json').read_text())
        names={row['path']:name for name,row in json.loads((BASE/'slot-delta/install-plan.json').read_text())['rows'].items()}
        for path,row in capture['files'].items():
            data=(BASE/'slot-capture'/(names[path]+'-old-data.bin')).read_bytes()
            assert sha(data)==row['data_alloc_sha256'];self.parts.append((row['data_block']*4096,data))
        intervals=sorted((at,at+len(data)) for at,data in self.parts)
        assert all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:]))
        self.misc=(folder/'misc-original.bin').read_bytes()

    def io(self):return ModelIO(self)


class ModelIO:
    model_only=True
    adb=['MODEL-NO-DEVICE']
    def __init__(self,snapshot):
        self.snapshot=snapshot;self.base=snapshot.backup.open('rb');self.changes={}
        self.writes=0;self.bytes=0;self.fail_at=None;self.rollback_fail=False;self.failed=False;self.rollback_failed=False
    def close(self):self.base.close()
    def identity(self):return dict(state='recovery',product='gauguin',partition_bytes=114919714816,unmounted=True,no_holders=True)
    def read(self,offset,n):
        assert offset%4096==n%4096==0 and 0<=offset<offset+n<=17179869184
        self.base.seek(offset);result=bytearray(self.base.read(n));assert len(result)==n
        for at,data in self.snapshot.parts:
            lo=max(at,offset);hi=min(at+len(data),offset+n)
            if lo<hi:result[lo-offset:hi-offset]=data[lo-at:hi-at]
        for at in range(offset,offset+n,4096):
            if at in self.changes:result[at-offset:at-offset+4096]=self.changes[at]
        return bytes(result)
    def overwrite(self,offset,data):
        first=offset//4096*4096;end=(offset+len(data)+4095)//4096*4096
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
