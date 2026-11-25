#!/usr/bin/env python3
"""Prepare exact0341 baselines and reversible0342 diagnostic scopes."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from core_io342_patch import patch,reverse

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/io-path-342'
PRIOR=MAIN/'research/tmp/gauguin-program-io-worktree-20261117/research/tmp/program-io-341'
SCOUT=MAIN/'research/tmp/io-path342-scout'
UNITS=('c_api','command','render','gpu','iokit_transport')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=BASE/'prepared-v3');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    budget=json.loads((BASE/'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes']==2400000000
    prior=json.loads((PRIOR/'prepared-v2/result.json').read_text());terminal=json.loads((PRIOR/'execution/result.json').read_text())
    assert terminal['state']=='CR341-lossless-wait-execution-observed-root-restored' and terminal['restored'] and terminal['independent_restore_verified']
    assert sha(PRIOR/'execution/result.json')=='f80d8a67cab334815d16a02cb3a14e09251faaa3aa8a294bfb51aed6c06d12ed'
    ready=json.loads((PRIOR/'ready.json').read_text());assert ready['pin_count']==24906
    pins=dict(ready['input_pins']);pins[str(PRIOR/'ready.json')]=sha(PRIOR/'ready.json')
    paths=[Path(__file__),WORK/'tools/core_io342_patch.py',BASE/'storage-whole-batch-admission.json',BASE/'storage-whole-batch-components.json',
        PRIOR/'execution/result.json',PRIOR/'execution/independent-restore.json',PRIOR/'post-analysis/comparison-summary.json',PRIOR/'post-analysis/verified-results.json',
        SCOUT/'archived-build-logs-v1/retirement-plan.json',SCOUT/'archived-build-logs-v1/result.json',SCOUT/'archive_build_logs342.py',SCOUT/'archive-stage-admission.json',SCOUT/'archive-protected-closure.json']
    paths+=list((SCOUT/'archived-build-logs-v1').glob('*.gz'))
    for name in ('Recording342.hpp','Profiling342.hpp','Reuse342.hpp','Allocation342.hpp','Phase342.hpp'):paths.append(WORK/'graphics/gauguin-io-path'/name)
    for p in paths:pins[str(p.resolve())]=sha(p)
    for p,h in pins.items():assert sha(p)==h,p
    out.mkdir();sources={}
    for variant in ('baseline','candidate'):
        dest=out/variant;dest.mkdir();sources[variant]=str(dest)
        for name,h in prior['source_pins']['candidate'].items():
            src=Path(prior['sources']['candidate'])/name;assert sha(src)==h
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
    counts={}
    for unit in UNITS:
        path=out/'candidate/src'/(unit+'.cpp');original=path.read_text();candidate,edits=patch(original,'src/'+unit+'.cpp')
        reverse(original,candidate,edits);path.write_text(candidate);counts[unit]=len(edits)
    for name in ('Recording342.hpp','Profiling342.hpp','Reuse342.hpp','Allocation342.hpp','Phase342.hpp'):shutil.copyfile(WORK/'graphics/gauguin-io-path'/name,out/'candidate/src'/name)
    for variant in ('frontend-baseline','frontend-candidate'):
        dest=out/variant;dest.mkdir();sources[variant]=str(dest)
        for name,h in prior['source_pins']['frontend-candidate'].items():
            src=Path(prior['sources']['frontend-candidate'])/name;assert sha(src)==h;shutil.copyfile(src,dest/name)
    for name in ('GauguinC4QueueTrace.h','GauguinQueue337.h','GauguinAsync338.h'):
        path=out/'frontend-candidate'/name;s=path.read_text();new=s
        for tag in ('C4Q','Q','N'):new=new.replace('GAUGUIN '+tag+'341:','GAUGUIN '+tag+'342:')
        assert new!=s;path.write_text(new)
    result=dict(state='prepared0342-user-IO-identity-and-program-allocation-stages',sources=sources,
        source_pins={v:{str(p.relative_to(dest)):sha(p) for p in Path(dest).rglob('*') if p.is_file()} for v,dest in sources.items()},
        input_pins=pins,reversible_edit_counts=counts,recompiled_units=list(UNITS),
        worker_State_owns_CPU_workspace=True,job_shape_unchanged=True,scratch_reentrant_local_fallback=True,
        retained_vector_limits=dict(bindings=128,BO_descriptors=1024,index_buckets=2048),
        stable_first_BO_order_command_index0_and_write_flag_merge=True,original_GPU_ownership_captures_preserved=True,
        GPU_cache_slots=32,GPU_cache_maximum_bytes=16*1048576,new_GPU_calls=0,new_threads=0,new_CPU_jobs=0,
        core_rows_max=4096,core_line_bytes_max=8192,public_C_API_338_entrypoints_retained=True,
        common_draw_phases=['entry','vertex_bindings','fragment_bindings','argument_members','draw_state','render_body','resource_keep','exit'],
        render_phases=['entry_freshen','null_private','program_table','pass_setup','encode','packets','resource_uses','exit'],
        GPU_submit_phases=['entry','BO_list','descriptor','transport','publication'],
        actual_IOConnect_begin_end=True,diagnostic_only=True,CPU_clock_queries_per_traced_IO=2,
        execution_and_off_CPU_bounds_include_sampling_envelope=True,IO_lock_vs_runnable_wait_not_classified=True,
        GPU_and_buffer_reuse_algorithms_unchanged=True,fixed337_kernel_helper_SB_reused=False,SB337_reused=True,new_kernel342_required=True,program_newBO_stages=["validate_and_metadata","GemNew","GemInfo","map","publication","failure_cleanup"],kernel_thread_identity_join=True,
        device_commands=0,device_writes=0,device_boots=0,physical_FPS_qualified=False)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','source_pins')},indent=2))


if __name__=='__main__':main()
