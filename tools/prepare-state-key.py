#!/usr/bin/env python3
"""Prepare the restored DL330 baseline and stack-state-key candidate locally."""
from pathlib import Path
import hashlib,json,shutil
from state_key_patch import instrument

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/key-perf565-331'
PRIOR=MAIN/'research/tmp/gauguin-direct-load-worktree-20261116/research/tmp/direct-load-330'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    out=STATE/'prepared-v1';assert not out.exists()
    admission=json.loads((PRIOR/'storage-next331-admission.json').read_text())
    assert admission['admitted'] and admission['planned_batch_bytes']==900000000
    assert json.loads((PRIOR/'execution/independent-restore.json').read_text())['state']=='independently-verified-six-original-files-and-misc'
    previous=PRIOR/'prepared-v1/result.json';old=json.loads(previous.read_text());source=Path(old['sources']['candidate']);source_pins=old['source_pins']['candidate']
    pins={str(source/p):h for p,h in source_pins.items()}
    for p in [previous,PRIOR/'storage-next331-admission.json',PRIOR/'cleanup331-plan.json',PRIOR/'cleanup331-result.json',PRIOR/'execution/independent-restore.json',PRIOR/'execution/result.json',PRIOR/'native-v1/result.json',Path(__file__),WORK/'tools/state_key_patch.py']:pins[str(p)]=sha(p)
    assert len(source_pins)==230 and all(sha(p)==h for p,h in pins.items())
    out.mkdir(parents=True)
    for v in ('baseline','candidate'):
        for name in source_pins:
            dest=out/v/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
    render=out/'candidate/src/render.cpp';render.write_text(instrument(render.read_text()))
    changed=sorted(str(p.relative_to(out/'candidate')) for p in (out/'candidate').rglob('*') if p.is_file() and sha(p)!=sha(out/'baseline'/p.relative_to(out/'candidate')))
    assert changed==['src/render.cpp']
    result=dict(state='prepared-KEY331-stack-state-key',input_pins=pins,sources={v:str(out/v) for v in ('baseline','candidate')},
        source_pins={v:{str(p.relative_to(out/v)):sha(p) for p in (out/v).rglob('*') if p.is_file()} for v in ('baseline','candidate')},changed_files=changed,
        cache_build_tag='8a71fe61aded108fa9ba5a22',retains_DR329_scratch=True,retains_DL330_direct_constants=True,
        maximum_stack_key_bytes=1024,additional_GPU_commands=0,additional_threads=0,device_commands=0,physical_FPS_qualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','source_pins')},indent=2))
if __name__=='__main__':main()
