#!/usr/bin/env python3
"""Prepare only the qualified 0336 cache-full replacement over exact0335."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil
from bo_reuse336_patch import transform

WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
BASE = WORK / 'research/tmp/bo-reuse-336'
PARENT = MAIN / 'research/tmp/gauguin-bo-reuse-worktree-20261116/research/tmp/bo-reuse-335'
HOST = PARENT.parent / 'bo-reuse-336/host-v1'
GPU = 'iokit/Kernel/arm/GauguinGPU.cpp'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def main():
    budget = load(BASE / 'storage-whole-batch-admission.json')
    assert budget['admitted'] and budget['planned_batch_bytes'] == 800000000
    assert budget['current_accounted_bytes'] + 800000000 <= 500000000000
    assert sha(HOST / 'result.json') == '52f4fa70a20a07980475b02b5ac6585e401eb4b7674b73c68beaac255664b95d'
    host = load(HOST / 'result.json')
    assert host['state'] == 'BC336-actual-cache-replacement-and-working-set-host-passed'
    assert host['paired_hot_observations_identical'] == 1024 and host['replacement_removals_per_return_max'] == 1
    assert load(PARENT / 'execution/independent-restore.json')['root_header_sha256'] == 'd68f4831dfed2e264140f000a02dd596d2cbc44d5409ac4388bdf23452df19fa'
    manifest = PARENT / 'local-link/build-manifest.json'
    assert sha(manifest) == '3023321fe2584900deb963ec584a46ead1906f885ac5852ac1299ff7d4efee73'
    data = load(manifest)
    assert data['inputs_unchanged'] and data['baseline_relink_identical_except_LC_UUID']
    source = Path(data['source_union']['overlay'])
    entries = {name: digest for name, kind, digest in data['source_union']['entries'] if kind == 'file'}
    pins = dict(host['input_pins'])
    for p in [Path(__file__), WORK / 'tools/bo_reuse336_patch.py', manifest, HOST / 'result.json',
              HOST / 'candidate-GauguinGPU.cpp', BASE / 'storage-whole-batch-admission.json',
              PARENT / 'ready.json', PARENT / 'execution/results-review.json',
              PARENT / 'cleanup336-plan.json', PARENT / 'cleanup336-result.json']:
        pins[str(p.resolve())] = sha(p)
    for path in source.rglob('*'):
        if path.is_file():
            assert sha(path) == entries[str(path.relative_to(source))]
            pins[str(path)] = sha(path)
    assert all(sha(p) == digest for p, digest in pins.items())
    before = (source / GPU).read_text()
    after = transform(before)
    assert after == (HOST / 'candidate-GauguinGPU.cpp').read_text()
    assert transform(after, reverse=True) == before
    out = BASE / 'kernel-source'
    assert not out.exists()
    shutil.copytree(source, out)
    (out / GPU).write_text(after)
    patch = WORK / 'xnu/patches/0248-gauguin-cache-full-replacement.patch'
    with patch.open('x') as stream:
        stream.write(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                     fromfile='a/' + GPU, tofile='b/' + GPU)))
    series = WORK / 'xnu/patches/series'
    assert series.read_text().rstrip().endswith('0247-gauguin-completed-bo-reuse.patch')
    series.write_text(series.read_text().rstrip() + '\n' + patch.name + '\n')
    assert all(sha(p) == digest for p, digest in pins.items())
    result = dict(state='prepared-BC336-bounded-cache-replacement', source=str(out),
        parent_manifest_sha256=sha(manifest), changed_files=[GPU], source_change_reversible=True,
        patch=str(patch), patch_sha256=sha(patch), cache_slots=32, cache_bytes=16777216,
        max_cached_bo_bytes=1048576, replacement_removals_per_return_max=1,
        no_sufficient_single_victim_keeps_original_release_new=True,
        cache_hit_mapping_policy_unchanged=True, IOSurface_and_alias_exclusions_unchanged=True,
        completion_and_failure_escrow_unchanged=True, new_threads=0, new_GPU_commands=0,
        input_pins=pins, inputs_unchanged=True, device_commands=0)
    with (BASE / 'source-preparation.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
