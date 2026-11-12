#!/usr/bin/env python3
"""Prepare the isolated ordered CA desktop frontend from eight pinned inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True,
                        help='Pinned eight-file frontend prerequisite audit')
    parser.add_argument('--out', type=Path, required=True,
                        help='Fresh preparation directory')
    args = parser.parse_args()
    audit_path = args.audit.resolve()
    audit = json.loads(audit_path.read_text())
    baseline_receipt = Path(audit['source_receipt'])
    baseline = json.loads(baseline_receipt.read_text())
    source = Path(baseline['source'])
    patch = repo / 'graphics/hakios-metal-ca/patches/0010-owned-desktop-commit-order.patch'
    target = Path('userland/src/HakiosMetalCA.m')
    assert audit['state'] == 'frontend-prerequisite-source-audited-not-implemented'
    assert baseline['state'] == 'prepared-gauguin-desktop-Metal-frontend-candidate'
    assert baseline['upstream_revision'] == '63fc2b4633bac3af8e57dadab9f5a8d4cb940438'
    assert len(audit['source_pins']) == 8
    assert audit['source_pins'][str(source / target)] == '9cdd4c1f28c6b967ea2acac60bd78da9d33bd7b20ca1680e27997fe5680e94b1'
    assert set(audit['source_pins']) == {str(path) for path in source.rglob('*') if path.is_file()}
    for name, digest in audit['source_pins'].items():
        assert sha(Path(name)) == digest, name
    assert not args.out.exists(), 'preparation output must be fresh'

    out = args.out.resolve()
    copied = out / 'source'
    shutil.copytree(source, copied)
    with (out / 'patch.log').open('x') as log:
        subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1',
                        '-d', str(copied), '-i', str(patch)],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    outputs = {str(path.relative_to(copied)): sha(path)
               for path in copied.rglob('*') if path.is_file()}
    assert len(outputs) == 8
    for name, digest in audit['source_pins'].items():
        rel = str(Path(name).relative_to(source))
        assert outputs[rel] != digest if rel == str(target) else outputs[rel] == digest
    text = (copied / target).read_text()
    assert 'hakiosAdmit:' in text and 'hakiosMarkScheduled' in text
    assert '_sent' not in text and 'hakiosDeferring' not in text
    assert all(sha(Path(name)) == digest for name, digest in audit['source_pins'].items())
    pins = {str(path): sha(path) for path in [Path(__file__).resolve(), audit_path,
                                              baseline_receipt, patch]}
    pins.update(audit['source_pins'])
    result = dict(state='prepared-owned-C4-desktop-frontend', profile='gauguin-ca-owned-c4',
                  source=str(copied), base_source=str(source),
                  patch_sha256=sha(patch), source_pins=outputs, input_pins=pins,
                  device_commands=0, installed=False, hardware_qualified=False)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items()
                      if key not in ('input_pins', 'source_pins')}, indent=2))


if __name__ == '__main__':
    main()
