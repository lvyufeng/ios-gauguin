#!/usr/bin/env python3
"""Materialize the pinned ownership+FQ322+SC323 baseline and scratch candidate."""
from pathlib import Path
import hashlib
import json
import shutil
from draw_scratch_patch import instrument

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
STATE = WORK/'research/tmp/draw-scratch-329'
OWNER = MAIN/'research/tmp/gauguin-metal-ownership-worktree-20261112/research/tmp/metal-ownership-v1/implementation-20261112'
FQ = MAIN/'research/tmp/gauguin-fault-cache-worktree-20261115/research/tmp/fault-cache-322/native-v2'
SC = MAIN/'research/tmp/gauguin-stage-cache-worktree-20261115/research/tmp/stage-cache-323/native-v1'
PRIOR = MAIN/'research/tmp/gauguin-gesture-sample-worktree-20261115/research/tmp/gesture-sample-328'


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    out = STATE/'prepared-v1'
    assert not out.exists()
    admission = json.loads((PRIOR/'storage-next329-after-cleanup.json').read_text())
    assert admission['admitted'] and admission['planned_batch_bytes'] == 900000000
    receipt = OWNER/'candidate-v3-prepared/result.json'
    r = json.loads(receipt.read_text()); source = Path(r['source'])
    assert r['profile'] == 'a619-ownership' and len(r['source_pins']) == 228
    pins = {str(source/p): h for p,h in r['source_pins'].items()}
    for p in [receipt, FQ/'result.json', SC/'result.json', Path(__file__), WORK/'tools/draw_scratch_patch.py',
              PRIOR/'cleanup329-plan.json', PRIOR/'cleanup329-result.json', PRIOR/'storage-next329-after-cleanup.json']:
        pins[str(p)] = sha(p)
    replacements = {}
    for folder, unit, header in [(FQ,'iokit_transport','GauguinFaultQueryCache.hpp'), (SC,'compiler','GauguinStageCacheTrace.hpp')]:
        info = json.loads((folder/'result.json').read_text())
        path = Path(info['source'])
        assert path == folder/'sources'/f'{unit}.cpp'
        replacements['src/'+path.name] = path
        h = path.parent/header
        assert h.is_file(), h
        replacements['src/'+h.name] = h
        for p in [path,h]: pins[str(p)] = sha(p)
    assert all(sha(p) == h for p,h in pins.items())
    out.mkdir(parents=True)
    for variant in ('baseline','candidate'):
        dest = out/variant
        for name in r['source_pins']:
            p = dest/name; p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,p)
        for name,p in replacements.items():shutil.copyfile(p,dest/name)
    candidate = out/'candidate'
    header = candidate/'include/hakios-metal/command.hpp'; draw = candidate/'src/render.cpp'
    changed = instrument(header.read_text(),draw.read_text())
    header.write_text(changed[0]);draw.write_text(changed[1])
    changed_names = [str(p.relative_to(candidate)) for p in candidate.rglob('*') if p.is_file() and sha(p) != sha(out/'baseline'/p.relative_to(candidate))]
    assert sorted(changed_names) == ['include/hakios-metal/command.hpp','src/render.cpp']
    result = dict(state='prepared-DR329-bounded-draw-scratch', input_pins=pins,
        source_pins={v:{str(p.relative_to(out/v)):sha(p) for p in (out/v).rglob('*') if p.is_file()} for v in ('baseline','candidate')},
        sources={v:str(out/v) for v in ('baseline','candidate')}, changed_files=changed_names,
        cache_build_tag='8a71fe61aded108fa9ba5a22',maximum_retained_scratch_bytes_per_CB=65536,
        additional_GPU_commands=0,additional_threads=0,device_commands=0,physical_FPS_qualified=False)
    assert all(sha(p) == h for p,h in pins.items())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','source_pins')},indent=2))


if __name__ == '__main__':main()
