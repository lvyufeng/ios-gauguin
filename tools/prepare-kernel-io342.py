#!/usr/bin/env python3
"""Stage/replay the exact337 driver plus bounded342 diagnostics, no device IO."""
import argparse,difflib,hashlib,json,shutil,subprocess
from pathlib import Path
from kernel_io342_patch import patch,reverse

MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/io-path-342'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
GPU='iokit/Kernel/arm/GauguinGPU.cpp'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=BASE/'kernel-prepared-v8');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    admission=json.loads((BASE/'storage-whole-batch-admission.json').read_text())
    assert admission['admitted'] and admission['planned_batch_bytes']==2400000000
    manifest=json.loads((PRIOR/'local-link/build-manifest.json').read_text())
    original=Path(manifest['source_union']['overlay']);base=Path(manifest['source_union']['base'])
    expected={n:h for n,k,h in manifest['source_union']['entries'] if k=='file'}
    pins={str(p):sha(p) for p in (Path(__file__),WORK/'tools/kernel_io342_patch.py',PRIOR/'local-link/build-manifest.json',BASE/'storage-whole-batch-admission.json')}
    for p in original.rglob('*'):
        if p.is_file():assert sha(p)==expected[str(p.relative_to(original))];pins[str(p)]=sha(p)
    for leaf in ('Phase342.hpp','Kernel342.hpp'):pins[str(WORK/'graphics/gauguin-io-path'/leaf)]=sha(WORK/'graphics/gauguin-io-path'/leaf)
    before=(original/GPU).read_text();after,edits=patch(before);reverse(before,after,edits)
    out.mkdir();source=out/'kernel-source';shutil.copytree(original,source)
    (source/GPU).write_text(after)
    changes=[GPU]
    for leaf in ('Phase342.hpp','Kernel342.hpp'):
        dest=source/'iokit/Kernel/arm'/leaf;shutil.copyfile(WORK/'graphics/gauguin-io-path'/leaf,dest);changes.append(str(dest.relative_to(source)))
    # 337 reused the336 driver object, whose BO event IDs were31/32. Its
    # collector overlay omitted those names; restore declarations only.
    ui='bsd/dev/gauguin_ui_trace.h';text=(source/ui).read_text()
    old='    GUT_SYNTHETIC=30 /* explicit origin marker for a generated report ID */'
    assert text.count(old)==1
    (source/ui).write_text(text.replace(old,old+',\n    GUT_BO_ALLOC333=31, GUT_BO_REUSE335=32'))
    changes.append(ui)
    diff=[]
    for name in changes:
        old=(original/name).read_text().splitlines(True) if (original/name).exists() else []
        diff.extend(difflib.unified_diff(old,(source/name).read_text().splitlines(True),fromfile='a/'+name if old else '/dev/null',tofile='b/'+name))
    path=WORK/'xnu/patches/0250-gauguin-IO-CPU-phase-trace.patch';path.write_text(''.join(diff))
    series=WORK/'xnu/patches/series'
    if series.read_text().splitlines()[-1]!=path.name:
        assert series.read_text().splitlines()[-1]=='0249-gauguin-concurrent-ui-trace.patch'
        series.write_text(series.read_text().rstrip()+'\n'+path.name+'\n')
    replay=out/'replay';replay.mkdir()
    for name in changes:
        if (original/name).exists():
            (replay/name).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(original/name,replay/name)
    p=subprocess.run(['patch','--batch','-p1','-i',str(path)],cwd=replay,capture_output=True)
    (out/'patch-replay.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
    assert all((source/n).read_bytes()==(replay/n).read_bytes() for n in changes)
    digest=hashlib.sha256(b''.join((source/n).read_bytes() for n in changes)).hexdigest()
    identity='xnu-local342-'+digest[:32]
    value=dict(state='prepared0342-reversible-driver-stage-diagnostics',source=str(source),base_source=str(base),
        parent_manifest=str(PRIOR/'local-link/build-manifest.json'),identity=identity,changed_files=changes,
        original_driver_restored_by_reverse=True,patch_sha256=sha(path),source_pins={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()},
        input_pins=pins,inputs_unchanged=all(sha(p)==h for p,h in pins.items()),
        request_validation_GPU_operations_lock_fence_escrow_cache_unchanged=True,
        new_GPU_operations=0,new_threads=0,record_capacity=4096,capture_window_ns=[210000000000,270000000000],
        CPU_mach_ticks_converted_to_nanoseconds=True,device_commands=0)
    assert value['inputs_unchanged']
    (out/'result.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items() if k not in ('input_pins','source_pins')},indent=2))

if __name__=='__main__':main()
