#!/usr/bin/env python3
"""Prepare the bounded completed-owned-BO cache over the exact 0333 overlay."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
from bo_reuse335_patch import GPU, HEADER, transform

WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
BASE = WORK / 'research/tmp/bo-reuse-335'
PARENT = MAIN / 'research/tmp/gauguin-bo-allocation-worktree-20261116/research/tmp/bo-allocation-333'
PRIOR = MAIN / 'research/tmp/gauguin-surface-retire-worktree-20261116/research/tmp/surface-retire-334'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    budget = json.loads((BASE / 'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes'] == 800000000
    assert json.loads((PRIOR / 'execution/independent-restore.json').read_text())['root_header_sha256'] == 'bd32497b0e9a8dbf43d6431b5eb35d76502c44653acfde5add464fd9863e20db'
    manifest = PARENT / 'local-link/build-manifest.json'
    data = json.loads(manifest.read_text())
    assert data['inputs_unchanged'] and data['baseline_relink_identical_except_LC_UUID']
    source = Path(data['source_union']['overlay'])
    entries = {name: digest for name, kind, digest in data['source_union']['entries'] if kind == 'file'}
    pins = {str(p.resolve()): sha(p) for p in [Path(__file__), WORK / 'tools/bo_reuse335_patch.py', manifest,
        BASE / 'storage-whole-batch-admission.json', PRIOR / 'ready.json', PRIOR / 'execution/results-review.json',
        PRIOR / 'cleanup335-plan.json', PRIOR / 'cleanup335-result.json']}
    for path in source.rglob('*'):
        if path.is_file():
            assert sha(path) == entries[str(path.relative_to(source))]
            pins[str(path)] = sha(path)
    out = BASE / 'kernel-source'
    assert not out.exists()
    shutil.copytree(source, out)
    changes = []
    for name in (GPU, HEADER):
        before = (source / name).read_text()
        after, _edits = transform(name, before)
        (out / name).write_text(after)
        changes.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
            fromfile='a/' + name, tofile='b/' + name))
    patch = WORK / 'xnu/patches/0247-gauguin-completed-bo-reuse.patch'
    with patch.open('x') as stream:
        stream.write(''.join(changes))
    series = WORK / 'xnu/patches/series'
    assert series.read_text().rstrip().endswith('0246-gauguin-bo-allocation-phases.patch')
    series.write_text(series.read_text().rstrip() + '\n' + patch.name + '\n')
    assert all(sha(p) == digest for p, digest in pins.items())
    result = dict(state='prepared-BC335-completed-owned-BO-cache', source=str(out),
        parent_manifest_sha256=sha(manifest), changed_files=[GPU, HEADER], source_change_reversible=True,
        patch=str(patch), patch_sha256=sha(patch), cache_slots=32, cache_bytes=16777216,
        max_cached_bo_bytes=1048576, zero_before_new_handle=True, exact_size_and_flags=True,
        IOSurface_excluded=True, exported_descriptor_aliases_excluded=True,
        retains_mapping_only_after_completion=True, residency_count_includes_cache=True,
        allocator_pressure_retry_max=1, new_threads=0, new_GPU_commands=0,
        cache_hit_synchronization_calls=0, cache_hit_PTE_writes=0,
        input_pins=pins, inputs_unchanged=True, device_commands=0)
    with (BASE / 'source-preparation.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
