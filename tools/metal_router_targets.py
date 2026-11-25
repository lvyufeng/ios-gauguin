#!/usr/bin/env python3
"""Check a router and its two actual captured targets before a volume proposal."""
from pathlib import Path
import argparse
import hashlib
import json

ROUTER = '/usr/libexec/gauguin-gpu-probe-router'
TARGETS = {
    'retained': ('/usr/libexec/gauguin-metal-frontend-probe', '--metal230'),
    'bootstrap': ('/usr/libexec/gauguin-metal-bootstrap', '--bootstrap245'),
}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_router_receipt(path):
    receipt = json.loads(Path(path).read_text())
    need(receipt['inputs_unchanged'] is True, 'router inputs changed')
    need(sha(receipt['binary']) == receipt['sha256'], 'router binary differs')
    for name, digest in receipt['input_pins'].items():
        need(sha(name) == digest, 'router input differs: ' + name)
    return receipt


def validate_target_capture(receipt, capture, directory):
    """Match actual bytes and HFS ownership to every embedded target tuple.

    The captured HFS reader does not expose link counts. Runtime fstat still
    checks nlink == 1; this check does not claim to replace that check.
    """
    directory = Path(directory)
    specs = receipt['targets']
    need(len(specs) == len(TARGETS), 'wrong router target count')
    need({s['kind'] for s in specs} == set(TARGETS), 'wrong router target set')
    rows = [(ROUTER, receipt['bytes'], receipt['sha256'])]
    for spec in specs:
        need((spec['path'], spec['argument']) == TARGETS[spec['kind']], 'wrong target path/argument')
        rows.append((spec['path'], spec['bytes'], spec['sha256']))
    checked = []
    for path, size, digest in rows:
        row = capture['files'][path]
        need(row['present'] is True, 'missing target: ' + path)
        need((row['uid'], row['gid'], row['mode']) == (0, 0, 0o100755), 'target ownership/mode differs: ' + path)
        need((row['bytes'], row['sha256']) == (size, digest), 'target binding differs: ' + path)
        name = row['output']
        need(isinstance(name, str) and Path(name).name == name and name not in ('', '.', '..'), 'unsafe capture filename')
        file = directory / name
        need(not file.is_symlink() and file.is_file(), 'capture is not a regular file')
        need(file.stat().st_size == size and sha(file) == digest, 'captured target bytes differ: ' + path)
        checked.append(dict(path=path, bytes=size, sha256=digest))
    return dict(state='actual-router-and-both-targets-match', checked=checked,
                runtime_nlink_check_still_required=True, device_operations=0,
                hardware_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--router-receipt', type=Path, required=True)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--capture-dir', type=Path, required=True)
    args = parser.parse_args()
    result = validate_target_capture(load_router_receipt(args.router_receipt),
                                     json.loads(args.capture.read_text()), args.capture_dir)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
