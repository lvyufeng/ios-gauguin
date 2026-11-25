#!/usr/bin/env python3
"""Fresh immutable0338 baselines and exact reversible0339 diagnostics."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from core_prof339_patch import patch,check_reverse

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-prof-339'
PRIOR=MAIN/'research/tmp/gauguin-core-async-worktree-20261117/research/tmp/core-async-338'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=BASE/'prepared-v1');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    budget=json.loads((BASE/'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes']==1200000000
    parent=json.loads((PRIOR/'prepared-v2/result.json').read_text())
    terminal=json.loads((PRIOR/'execution/result.json').read_text())
    assert terminal['restored'] and terminal['independent_restore_verified'] and terminal['boot_attempts']==1
    assert terminal['state']=='CR338-lossless-wait-execution-observed-root-restored'
    assert sha(PRIOR/'execution/result.json')=='ee981567271346686514c106a56817bb59297498c0e84207687f122b48cb3e4f'
    ready=json.loads((PRIOR/'ready.json').read_text())
    pins=dict(ready['input_pins']);pins[str(PRIOR/'ready.json')]=sha(PRIOR/'ready.json')
    for p in (Path(__file__),WORK/'tools/core_prof339_patch.py',WORK/'graphics/gauguin-core-prof/Recording339.hpp',
        BASE/'storage-whole-batch-admission.json',BASE/'storage-whole-batch-components.json',
        PRIOR/'execution/result.json',PRIOR/'execution/independent-restore.json',
        PRIOR/'post-analysis/comparison-summary.json',PRIOR/'critical-path/result.json'):
        pins[str(p.resolve())]=sha(p)
    for p,h in pins.items():assert sha(p)==h,p
    out.mkdir();sources={}
    for variant in ('baseline','candidate'):
        dest=out/variant;dest.mkdir();sources[variant]=str(dest)
        for name,h in parent['source_pins']['candidate'].items():
            src=Path(parent['sources']['candidate'])/name;assert sha(src)==h
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
    changes={};classification={}
    for name in ('src/c_api.cpp','src/command.cpp'):
        target=out/'candidate'/name;old=target.read_text();new,edits,audit=patch(old,name)
        check_reverse(old,new,edits);target.write_text(new);changes[name]=len(edits)
        classification.update(audit)
    shutil.copyfile(WORK/'graphics/gauguin-core-prof/Recording339.hpp',out/'candidate/src/Recording339.hpp')
    for variant in ('frontend-baseline','frontend-candidate'):
        dest=out/variant;dest.mkdir();sources[variant]=str(dest)
        for name,h in parent['source_pins']['frontend-candidate'].items():
            src=Path(parent['sources']['frontend-candidate'])/name;assert sha(src)==h
            shutil.copyfile(src,dest/name)
    for name in ('GauguinC4QueueTrace.h','GauguinQueue337.h','GauguinAsync338.h'):
        target=out/'frontend-candidate'/name;s=target.read_text()
        changed=s.replace('GAUGUIN C4Q338:','GAUGUIN C4Q339:').replace('GAUGUIN Q338:','GAUGUIN Q339:').replace('GAUGUIN N338:','GAUGUIN N339:')
        assert changed!=s,name;target.write_text(changed)
    result=dict(state='prepared0339-core-category-and-submit-phase-diagnostics',sources=sources,
        source_pins={v:{str(p.relative_to(dest)):sha(p) for p in Path(dest).rglob('*') if p.is_file()} for v,dest in sources.items()},
        input_pins=pins,reversible_edit_counts=changes,category_call_audit=classification,
        category_order=['control','bindings','render','clear','compute','transfer_append','commit','notification'],
        submit_stage_order=['entry','pass_tail','command_BO','command_copy','queue_lock','fault_query','native_submit','publication'],
        core_line_max_bytes=2048,core_records_max=4096,one_core_row_per_commit=True,
        no_new_per_job_allocation=True,scheduling_and_resource_captures_unchanged=True,
        public_API_338_entrypoints_retained=True,new_GPU_calls=0,new_threads=0,
        diagnostic_only=True,performance_optimization_claim=False,fixed337_kernel_helper_SB_reused=True,
        device_commands=0,physical_FPS_qualified=False)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','source_pins')},indent=2))


if __name__=='__main__':main()
