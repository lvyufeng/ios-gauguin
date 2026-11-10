#!/usr/bin/env python3
"""Start one pinned local stage independently of a short-lived DSH session.

This changes process ownership only. Each job retains its existing authorization,
input checks, single-use claims and result reporting. A lost connection never
authorizes a retry. Observe the recorded dispatcher PID and original result.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())


def existing(out):
    result = out / 'result.json'
    if result.exists():
        record = json.loads(result.read_text())
        print(json.dumps(dict(executed_again=False, state='existing-stage-result',
                              result=str(result), inner_exit=record['exit'])))
        return record['exit']
    print(json.dumps(dict(executed_again=False, state='existing-claim-observe-original-only',
                          out=str(out))))
    return 75


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    args = parser.parse_args()
    profile = args.profile.resolve()
    config = json.loads(profile.read_text())
    cwd = Path(config['cwd']).resolve()
    out = Path(config['out']).resolve()
    executor = cwd / 'tools/run-pinned-stage.py'
    if not out.is_relative_to(cwd / 'research/tmp'):
        raise ValueError('stage output must be private')
    resolved_pins = {str((cwd / name).resolve()): pin
                     for name, pin in config['input_pins'].items()}
    if resolved_pins.get(str(executor)) != sha(executor):
        raise ValueError('dispatcher must be explicitly pinned')
    for name, pin in config['input_pins'].items():
        if sha(cwd / name) != pin:
            raise ValueError('stage input changed: ' + name)
    profile_sha = sha(profile)
    out.mkdir(parents=True, exist_ok=True)
    # Both kinds of claims matter: older stages were started synchronously.
    if (out / 'claim.json').exists() or (out / 'launch-claim.json').exists():
        return existing(out)
    record = dict(state='launch-claimed', profile=str(profile),
                  profile_sha256=profile_sha, dispatcher_sha256=sha(executor),
                  launcher_sha256=sha(Path(__file__).resolve()),
                  launcher_pid=os.getpid(),
                  recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    try:
        save(out / 'launch-claim.json', record)
    except FileExistsError:
        return existing(out)
    # No rerun if an older synchronous dispatcher claimed concurrently.
    if (out / 'claim.json').exists():
        return existing(out)
    if sha(profile) != profile_sha:
        raise ValueError('profile changed before launch')
    argv = [sys.executable, str(executor), str(profile)]
    with (out / 'dispatcher.log').open('xb') as log:
        child = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                                 close_fds=True, start_new_session=True)
    record.update(state='started-detached-pinned-stage', dispatcher_pid=child.pid,
                  argv=argv, completion_is_not_proven=True)
    save(out / 'launch.json', record)
    print(json.dumps(record))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
