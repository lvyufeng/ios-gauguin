#!/usr/bin/env python3
"""Prepare immutable SURF334/Q337 baselines and a reversible 0338 candidate."""
from pathlib import Path
import hashlib
import json
import shutil
import argparse
from core_async338_patch import core,frontend,check_reverse,HEADER,SOURCE

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/core-async-338'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
SURFACE=MAIN/'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=BASE/'prepared-v1')
    out=parser.parse_args().out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    budget=json.loads((BASE/'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes']==1800000000
    old=json.loads((SURFACE/'prepared-v1/result.json').read_text())
    native=json.loads((SURFACE/'native-v2/result.json').read_text())
    front=json.loads((PRIOR/'c4-native-v2/result.json').read_text())
    baseline=Path(old['sources']['candidate'])
    pins={str(baseline/p):digest for p,digest in old['source_pins']['candidate'].items()}
    for p in [Path(__file__),WORK/'tools/core_async338_patch.py',WORK/'graphics/gauguin-core-async/Recording338.hpp',
              WORK/'graphics/gauguin-core-async/GauguinAsync338.h',BASE/'storage-whole-batch-admission.json',
              BASE/'storage-whole-batch-components.json',SURFACE/'prepared-v1/result.json',SURFACE/'native-v2/result.json',
              PRIOR/'c4-native-v2/result.json',PRIOR/'trim-rescue/independent-six-file-restore.json',
              PRIOR/'trim-rescue/independent-metadata-restore.json',PRIOR/'recovered-analysis/collection-analysis.json',
              Path(native['products']['candidate']['binary']),Path(front['products']['candidate']['binary'])]:
        pins[str(p)]=sha(p)
    assert native['products']['candidate']['sha256']=='dc26b7b613345f84d2e8e2636a1948be75b3d400418291e3b2281176a4070954'
    assert front['products']['candidate']['sha256']=='d4e46b8e8541d3a674a6e814170b27d4d930b5d301f25dc016b5f7c9da34b6f3'
    fronts=PRIOR/'c4-native-v2/sources'
    for p in fronts.iterdir():
        if p.is_file():pins[str(p)]=sha(p)
    assert all(sha(p)==digest for p,digest in pins.items())
    out.mkdir()
    for variant in ('baseline','candidate'):
        for name in old['source_pins']['candidate']:
            target=out/variant/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(baseline/name,target)
    edits={}
    for name in (HEADER,SOURCE):
        p=out/'candidate'/name;original=p.read_text();changed,changes=core(original,name)
        check_reverse(original,changed,changes);p.write_text(changed);edits[name]=len(changes)
    shutil.copyfile(WORK/'graphics/gauguin-core-async/Recording338.hpp',out/'candidate/src/Recording338.hpp')
    for variant in ('frontend-baseline','frontend-candidate'):
        dest=out/variant;dest.mkdir()
        for p in fronts.iterdir():
            if p.is_file():shutil.copyfile(p,dest/p.name)
    dest=out/'frontend-candidate'
    p=dest/'HakiosMetalCA.m';original=p.read_text();changed,changes=frontend(original)
    check_reverse(original,changed,changes);p.write_text(changed);edits['HakiosMetalCA.m']=len(changes)
    # New wire tags prevent legacy status-drain interpretation of async return.
    for name in ('GauguinC4QueueTrace.h','GauguinQueue337.h'):
        p=dest/name;s=p.read_text();assert 'GAUGUIN ' in s
        p.write_text(s.replace('GAUGUIN C4Q321:','GAUGUIN C4Q338:').replace('GAUGUIN Q337:','GAUGUIN Q338:'))
    shutil.copyfile(WORK/'graphics/gauguin-core-async/GauguinAsync338.h',dest/'GauguinAsync338.h')
    sources={name:str(out/name) for name in ('baseline','candidate','frontend-baseline','frontend-candidate')}
    result=dict(state='prepared-0338-core-job-timing-and-recorded-notification',sources=sources,
        source_pins={name:{str(p.relative_to(path)):sha(p) for p in Path(path).rglob('*') if p.is_file()}
                     for name,path in sources.items()},input_pins=pins,reversible_edit_counts=edits,
        core_changed_files=[HEADER,SOURCE,'src/Recording338.hpp'],new_core_exports=['hakios_metal_cb_trace338','hakios_metal_cb_notify_recorded338'],
        fixed337_kernel_helper_SB_reused=True,core_commit_post_order_unchanged=True,
        completion_FIFO_unchanged=True,notification_enqueue_failure_synchronously_drains=True,
        frontend_notification_lease_separate=True,additional_CPU_jobs_per_commit=1,
        additional_GPU_submissions=0,additional_threads=0,core_trace_limit=4096,core_trace_line_max=512,
        notification_trace_limit=4096,notification_line_max=128,
        C4_phase4_semantics='notification admission returned, value0 reserved; no synchronous status snapshot',
        core_clock='mach_absolute_time scaled to integer ns, same epoch as C4 rounded us',
        device_commands=0,physical_FPS_qualified=False)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','source_pins')},indent=2))


if __name__=='__main__':main()
