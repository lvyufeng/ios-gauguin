#!/usr/bin/env python3
"""Prepare bounded CPU allocation phases over the verified 0332 kernel."""
from pathlib import Path
import difflib,hashlib,json,shutil
from bo_allocation333_patch import GPU,HEADER,transform
WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/bo-allocation-333'
PARENT=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-present-retry-worktree-20261116/research/tmp/present-retry-332')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    budget=json.loads((STATE/'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes']==800000000
    assert sha(PARENT/'ready.json')=='e28d920ead32342b01e186d4efde1b96be96a2742fb3d690104fee234550d89b'
    manifest_path=PARENT/'local-link/build-manifest.json'
    assert sha(manifest_path)=='bd600d5f04319ccc59ebff3acf14eb3512d7e6aae9bb625cc84ed04a03a2bcc6'
    m=json.loads(manifest_path.read_text());base=Path(m['source_union']['base']);overlay=Path(m['source_union']['overlay'])
    entries={name:digest for name,kind,digest in m['source_union']['entries'] if kind=='file'}
    out=STATE/'kernel-source';assert not out.exists()
    inputs=[Path(__file__),WORK/'tools/bo_allocation333_patch.py',STATE/'storage-whole-batch-admission.json',PARENT/'ready.json',manifest_path]
    for path in overlay.rglob('*'):
        if path.is_file():
            assert sha(path)==entries[str(path.relative_to(overlay))]
            inputs.append(path)
    before={}
    for name in (GPU,HEADER):
        p=overlay/name if (overlay/name).is_file() else base/name
        assert sha(p)==entries[name];inputs.append(p);before[name]=p.read_text()
    pins={str(p.resolve()):sha(p) for p in inputs}
    shutil.copytree(overlay,out);diff=[]
    for name in (GPU,HEADER):
        after,edits=transform(name,before[name]);dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(after)
        diff.extend(difflib.unified_diff(before[name].splitlines(True),after.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
    patch=WORK/'xnu/patches/0246-gauguin-bo-allocation-phases.patch'
    with patch.open('x') as f:f.write(''.join(diff))
    series=WORK/'xnu/patches/series';assert series.read_text().rstrip().endswith('0245-gauguin-pending-present-retry.patch')
    series.write_text(series.read_text().rstrip()+'\n'+patch.name+'\n')
    assert all(sha(p)==d for p,d in pins.items())
    result=dict(state='prepared-BO333-CPU-allocation-phases',source=str(out),parent_manifest_sha256=sha(manifest_path),changed_files=[GPU,HEADER],source_change_reversible=True,patch=str(patch),patch_sha256=sha(patch),maximum_trace_records_per_new_BO=6,trace_capacity_unchanged=4096,trace_window_seconds_unchanged=4,new_GPU_commands=0,new_MMIO_reads=0,new_threads=0,new_allocations_in_producer=0,original_validators_waits_ownership_preserved=True,thread_identifier_numeric_only=True,input_pins=pins,inputs_unchanged=True,device_commands=0)
    with (STATE/'source-preparation.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
