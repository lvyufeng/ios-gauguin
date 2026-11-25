#!/usr/bin/env python3
"""Prepare the queue337 collector overlay without modifying frozen 0336 inputs."""
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import shutil
import subprocess

WORK=Path(__file__).resolve().parents[1]
MAIN=Path('/Users/baai/Project/ios-gauguin')
PARENT=MAIN/'research/tmp/gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336'
PATCH='0249-gauguin-concurrent-ui-trace.patch'
FILES=['bsd/dev/gauguin_ui_trace.c','bsd/dev/gauguin_ui_trace.h','bsd/dev/gauguin_ui_trace_board.c']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    out=ap.parse_args().out.resolve();assert out.is_relative_to(WORK/'research/tmp')and not out.exists()
    manifest=PARENT/'local-link/build-manifest.json';m=json.loads(manifest.read_text())
    assert m['inputs_unchanged'] and m['baseline_relink_identical_except_LC_UUID']
    base=Path(m['source_union']['base']);overlay=Path(m['source_union']['overlay'])
    entries={p:h for p,k,h in m['source_union']['entries']if k=='file'}
    pins={str(p):sha(p)for p in [manifest,Path(__file__)]}
    diff=[]
    for name in FILES:
        old=overlay/name if (overlay/name).exists()else base/name
        assert sha(old)==entries[name]
        new=WORK/'xnu/overlays/queue337'/name
        for p in (old,new):pins[str(p)]=sha(p)
        diff.extend(difflib.unified_diff(old.read_text().splitlines(True),new.read_text().splitlines(True),
                                       fromfile='a/'+name,tofile='b/'+name))
    for p in overlay.rglob('*'):
        if p.is_file():assert sha(p)==entries[str(p.relative_to(overlay))];pins[str(p)]=sha(p)
    patch=WORK/'xnu/patches'/PATCH;raw=''.join(diff)
    if patch.exists():assert patch.read_text()==raw
    else:patch.write_text(raw)
    series=WORK/'xnu/patches/series';lines=series.read_text().splitlines()
    if PATCH not in lines:
        assert lines[-1]=='0248-gauguin-cache-full-replacement.patch';series.write_text(series.read_text().rstrip()+'\n'+PATCH+'\n')
    out.mkdir(parents=True);audit=out/'replay';audit.mkdir()
    for name in FILES:
        old=overlay/name if (overlay/name).exists()else base/name
        target=audit/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old,target)
    proc=subprocess.run(['patch','--batch','-p1','-i',str(patch)],cwd=audit,text=True,capture_output=True)
    (out/'patch-replay.log').write_text(proc.stdout+proc.stderr);assert proc.returncode==0
    for name in FILES:assert (audit/name).read_bytes()==(WORK/'xnu/overlays/queue337'/name).read_bytes()
    candidate=out/'kernel-source';shutil.copytree(overlay,candidate)
    for name in FILES:
        target=candidate/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(audit/name,target)
    assert all(sha(p)==h for p,h in pins.items())
    result=dict(state='prepared-0337-collector-overlay-patch-replayed',source=str(candidate),
                patch_sha256=sha(patch),changed_files=FILES,input_pins=pins,inputs_unchanged=True,
                BO_cache_policy_unchanged=True,wire_version=2,capacity=4096,new_threads=0,
                device_commands=0,boot_image_built=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['state'])
if __name__=='__main__':main()
