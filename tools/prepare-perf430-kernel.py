#!/usr/bin/env python3
"""Prepare fixed native430/BW8 opt-in on the verified PERF325 source union."""
from pathlib import Path
import difflib,hashlib,json,shutil
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/perf430-326'
BASE=MAIN/'research/tmp/gauguin-perf355-worktree-20261115/research/tmp/perf355-325'
POLICY=MAIN/'research/tmp/gauguin-map-query-worktree-20261115/research/tmp/map-query-324'
PARENT=BASE/'local-link/build-manifest.json'
CHANGED=('bsd/dev/gauguin_gmu_firmware.c','bsd/dev/gauguin_gmu_firmware.h','bsd/dev/gauguin_gmu_board.c')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def instrument(name,raw):
 original=raw
 pairs=[('profile355','profile430'),('dcvs355','dcvs430'),('355MHz','430MHz'),('for355','for430'),
        ('profile!=2','profile!=3'),('profile==2','profile==3'),('gpf=2','gpf=3'),
        ('0x30000002','0x30000003'),('0x00007007','0x00008008'),('0x7007','0x8008'),
        ('perf_index=2 hz=355000000 bw_index=7 Bps=3072000000','perf_index=3 hz=430000000 bw_index=8 Bps=4068000000'),
        ('perf=30000002 bw=00007007','perf=30000003 bw=00008008'),
        ('level4 -> PERF2/430MHz/BW7','level3 -> PERF3/430MHz/BW8'),
        ('PERF2/BW7','PERF3/BW8'),('ARC128/GX2/MX3','ARC192/GX3/MX4'),
        ('BW7 is3072000000Bps','BW8 is4068000000Bps')]
 edits=[]
 for before,after in pairs:
  if before in raw:
   assert after not in raw,(name,after)
   raw=raw.replace(before,after);edits.append((before,after))
 undone=raw
 for before,after in reversed(edits):undone=undone.replace(after,before)
 assert undone==original and raw!=original
 return raw

def main():
 assert sha(PARENT)=='204afc78c21d332e8c4139b0639d55e04c77c4054c0151aa3fd3677bc2c88296'
 parent=json.loads(PARENT.read_text());source=Path(parent['source_union']['base']);overlay=Path(parent['source_union']['overlay'])
 budget=json.loads((STATE/'storage-whole-batch-admission.json').read_text());assert budget['admitted'] and budget['planned_batch_bytes']==800000000
 policy=json.loads((POLICY/'gpu-policy-readback/result.json').read_text());assert policy['state']=='readonly-current-native-GPU-policy-matches-retained-DT'
 p=policy['active_rows'][3]['properties'];assert p['qcom,gpu-freq']==[430000000] and p['qcom,bus-freq']==[8] and p['qcom,bus-min']==[7] and p['qcom,bus-max']==[10]
 pins={str(PARENT):sha(PARENT),str(POLICY/'gpu-policy-readback/result.json'):sha(POLICY/'gpu-policy-readback/result.json')}
 out=STATE/'kernel-source';assert not out.exists();out.mkdir()
 def original(name):return overlay/name if (overlay/name).is_file() else source/name
 support=set(p.relative_to(overlay) for p in overlay.rglob('*') if p.is_file())
 support.update(p.relative_to(source) for pattern in ('gauguin_*.c','gauguin_*.h','cmd_db_snapshot.c','cmd_db_snapshot.h') for p in (source/'bsd/dev').glob(pattern))
 for name in sorted(support|set(map(Path,CHANGED))):
  src=original(name);assert sha(src)==parent['input_pins'][str(src)]['sha256'],src
  dst=out/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);pins[str(src)]=sha(src)
 patch=''
 for name in CHANGED:
  raw=original(name).read_text();modified=instrument(name,raw);(out/name).write_text(modified)
  patch+=''.join(difflib.unified_diff(raw.splitlines(True),modified.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
 pp=WORK/'xnu/patches/0240-gauguin-native430-dcvs-profile.patch';assert not pp.exists();pp.write_text(patch)
 result=dict(state='prepared-PERF326-source-only',parent_manifest_sha256=sha(PARENT),source=str(out),changed_files=list(CHANGED),patch=str(pp),patch_sha256=sha(pp),source_change_reversible=True,context_and_receipt_layout_unchanged=True,default_profile_unchanged=True,profile=dict(argument='gpf=3',frequency_hz=430000000,perf_index=3,bw_index=8,bandwidth_bytes_per_second=4068000000),input_pins=pins,new_GPU_commands=0,new_threads=0,device_commands=0)
 (STATE/'source-preparation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
