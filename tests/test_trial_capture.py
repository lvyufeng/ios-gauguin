#!/usr/bin/env python3
"""Replay the actual 0282 empty-stdout capture and reject damaged evidence."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import shutil
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['before', 'after', 'expected', 'directories', 'out']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / 'tools'))
    from trial_capture import LOG_PATHS, validate_capture
    read = lambda path: json.loads(path.read_text())
    before, after = read(args.before), read(args.after)
    expected, directories = read(args.expected), read(args.directories)
    proof = validate_capture(expected, directories, before, args.before.parent, after, args.after.parent)
    assert proof['static_files_retained'] == 24 and proof['full_old_log_prefixes_retained'] == 3
    assert proof['tails'][LOG_PATHS[0]] == b''
    assert proof['tails'][LOG_PATHS[1]] == b'GAUGUIN ROUTER247 FAIL phase=target code=0\n'
    args.out.mkdir(exist_ok=False)
    negative = []
    bad = copy.deepcopy(after)
    static = next(name for name in expected if name not in LOG_PATHS)
    bad['files'][static]['uid'] = 501
    try:
        validate_capture(expected, directories, before, args.before.parent, bad, args.after.parent)
    except ValueError as error:
        assert str(error) == 'file owner/mode differs: ' + static
        negative.append('static-owner-mismatch')
    else:
        raise AssertionError('accepted changed static owner')
    copied = args.out / 'bad-prefix'
    copied.mkdir()
    for row in after['files'].values():
        shutil.copyfile(args.after.parent / row['output'], copied / row['output'])
    bad = copy.deepcopy(after)
    row = bad['files'][LOG_PATHS[0]]
    file = copied / row['output']
    data = bytearray(file.read_bytes())
    data[0] ^= 1
    file.write_bytes(data)
    row['sha256'] = hashlib.sha256(data).hexdigest()
    try:
        validate_capture(expected, directories, before, args.before.parent, bad, copied)
    except ValueError as error:
        assert str(error) == 'complete old log prefix differs: ' + LOG_PATHS[0]
        negative.append('old-prefix-corrupted-with-consistent-file-hash')
    else:
        raise AssertionError('accepted corrupt full old prefix')
    result = dict(state='actual282-empty-stdout-retains-complete-capture-evidence',
                  static_files_retained=24, full_old_log_prefixes_retained=3,
                  directory_owner_modes_retained=4, log_growth_bytes=proof['log_growth_bytes'],
                  negative_controls=negative, replay_only=True, device_operations=0,
                  runtime_success_inferred=False)
    with (args.out / 'result.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
