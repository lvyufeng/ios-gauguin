#!/usr/bin/env python3
"""Prepare the installed KEY331 core and the surface-retirement repair."""
from pathlib import Path
import hashlib,json,shutil
from surface_retire_patch import HEADER,SOURCE,transform
WORK=Path(__file__).resolve().parents[1];MAIN=Path('/Users/baai/Project/ios-gauguin')
STATE=WORK/'research/tmp/surface-retire-334'
PRIOR=MAIN/'research/tmp/gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'
CORE=MAIN/'research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    out=STATE/'prepared-v1';assert not out.exists()
    admission=json.loads((STATE/'storage-whole-batch-admission.json').read_text());assert admission['admitted'] and admission['planned_batch_bytes']==800000000
    assert sha(PRIOR/'ready.json')=='4467a84fa2f1372fa07693d4ed68feb1b813ad8d56247971734a9dc7930a1bac'
    restored=json.loads((PRIOR/'execution/independent-restore.json').read_text());assert restored['state']=='independently-verified-six-original-files-and-misc' and restored['root_header_sha256']=='2083806fcadb51c5624b0fb78cfc4f4176699bf7727f5ca543ae5c090b4ebd46'
    terminal=json.loads((PRIOR/'execution/result.json').read_text());assert terminal['restored'] and terminal['state']=='trial-incomplete-or-failed'
    old=json.loads((CORE/'prepared-v1/result.json').read_text());source=Path(old['sources']['candidate']);source_pins=old['source_pins']['candidate']
    assert len(source_pins)==230
    native=json.loads((CORE/'core-native-v1/result.json').read_text());assert native['products']['candidate']['sha256']=='1e48b6f1b375519af151db4d09ccf368a56c969cd8ae8305a48c540a2e0eb681'
    pins={str(source/p):h for p,h in source_pins.items()}
    for p in [Path(__file__),WORK/'tools/surface_retire_patch.py',STATE/'storage-whole-batch-admission.json',STATE/'storage-whole-batch-components.json',CORE/'prepared-v1/result.json',CORE/'core-native-v1/result.json',PRIOR/'ready.json',PRIOR/'cleanup334-plan.json',PRIOR/'cleanup334-result.json',PRIOR/'execution/result.json',PRIOR/'execution/independent-restore.json',PRIOR/'surface-race-repro-v1/result.json',PRIOR/'surface-race-fixture.cpp',PRIOR/'hakios-command-reference.json']:
        pins[str(p)]=sha(p)
    assert all(sha(p)==h for p,h in pins.items())
    out.mkdir(parents=True)
    for variant in ('baseline','candidate'):
        for name in source_pins:
            dest=out/variant/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,dest)
    for name in (HEADER,SOURCE):
        dest=out/'candidate'/name;dest.write_text(transform(name,dest.read_text()))
    changed=sorted(str(p.relative_to(out/'candidate')) for p in (out/'candidate').rglob('*') if p.is_file() and sha(p)!=sha(out/'baseline'/p.relative_to(out/'candidate')))
    assert changed==sorted([HEADER,SOURCE])
    result=dict(state='prepared-SURF334-surface-retirement-repair',sources={v:str(out/v) for v in ('baseline','candidate')},source_pins={v:{str(p.relative_to(out/v)):sha(p) for p in (out/v).rglob('*') if p.is_file()} for v in ('baseline','candidate')},changed_files=changed,input_pins=pins,cache_build_tag='8a71fe61aded108fa9ba5a22',expired_entry_wait_releases_cache_mutex=True,old_handle_closed_before_reimport=True,new_ownership_published_after_fallible_allocations=True,Buffer_layout_unchanged=True,diagnostic_wait_pairs_max=64,diagnostic_record_max_bytes=128,additional_threads=0,additional_GPU_submissions=0,reimport_uses_existing_surface_API=True,hardware_cause_of_prior_handle774_proven=False,device_commands=0,physical_FPS_qualified=False)
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','source_pins')},indent=2))
if __name__=='__main__':main()
