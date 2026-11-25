#!/usr/bin/env python3
"""Continue the unchanged 0335 trial after its proven no-device preflight.

No boot or installation has occurred. Preserve the failed preflight instead of
discarding its claim. Exactly one continuation is available, only after recovery
returns; all original authorization, input, budget and device checks still run.
"""
from pathlib import Path
import errno
import hashlib
import importlib.util
import json
import os
import subprocess

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-335'
READY = '631689d09a9cc19a3ea9752f920d6d323153148de20b88d6325adee9c23984e8'
APPROVAL = '2dc7cb598322c16716866dc5af9d381b6733e84da4d32b108e0ad189a5505b57'
FAILED = {
    'result.json': 'de3ddec9cef321fbe08378ad17cec16166fc639c9d6dc4bbfc868ca1b7e18141',
    'claim.json': 'd142f07faf8cd231a855614387089a4d504e3df56b8f04c38c22954a505e9cf9',
    'storage-preflight.json': 'eb3f2e8813ab54c02be20ddbf21cd76adb4988923d4e3d35edcf520cd5a325dd',
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def load(path):
    return json.loads(Path(path).read_text())


def process_alive(pid):
    try:
        os.kill(pid, 0)
    except OSError as error:
        if error.errno == errno.ESRCH:
            return False
        raise
    return True


def verify_failed_preflight(base, alive=process_alive):
    execution = base / 'execution'
    require(not (base / 'preflight-no-device').exists(), 'one preflight continuation already claimed')
    require(execution.is_dir() and not execution.is_symlink(), 'failed execution directory absent')
    require({p.name for p in execution.iterdir()} == set(FAILED),
            'preflight has capture, install, progress, boot or additional artifacts')
    for name, digest in FAILED.items():
        path = execution / name
        require(path.is_file() and not path.is_symlink() and sha(path) == digest,
                'failed preflight proof differs: ' + name)
    result, claim = load(execution / 'result.json'), load(execution / 'claim.json')
    require(result['state'] == 'trial-incomplete-or-failed' and
            result['error'] == "Refused('one recovery device required')" and
            result['partition_write_phase'] == 'none' and result['boot_attempts'] == 0 and
            result['recovery_fallbacks'] == 0 and
            all(result[k] is False for k in ('installed', 'restored', 'restore_attempted',
                                            'misc_marker_written', 'boot_started')),
            'failure was not the initial no-device preflight')
    require(claim['approval_sha256'] == APPROVAL and type(claim['pid']) is int and
            claim['pid'] > 1 and not alive(claim['pid']), 'previous owner live or approval differs')
    return dict(failed_pins={str(execution / n): d for n, d in FAILED.items()},
                previous_pid=claim['pid'], actual_device_writes=0, boot_attempts=0,
                misc_marker_written=False)


def archive_failed_preflight(base, audit, alive=process_alive):
    # Recheck immediately before the reversible, local-only archive operation.
    require(verify_failed_preflight(base, alive) == audit, 'preflight changed before archive')
    archive = base / 'preflight-no-device'
    archive.mkdir(exist_ok=False)
    (base / 'execution').rename(archive / 'execution')
    for name, digest in FAILED.items():
        require(sha(archive / 'execution' / name) == digest, 'archived proof differs')
    return archive


def recovery_available():
    result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
    require(result.returncode == 0, 'ADB enumeration failed; original claim preserved')
    rows = [line.split() for line in result.stdout.splitlines()[1:] if len(line.split()) == 2]
    require(len(rows) == 1 and rows[0][1] == 'recovery',
            'connect the one phone in TWRP; original claim preserved')


def main():
    require(sha(BASE / 'ready.json') == READY and sha(BASE / 'approval.json') == APPROVAL,
            'original user-approved trial differs')
    ready = load(BASE / 'ready.json')
    runner = WORK / 'tools/run-sb-cadence-trial.py'
    require(sha(runner) == ready['input_pins'][str(runner)], 'frozen executor differs')
    audit = verify_failed_preflight(BASE)
    recovery_available()
    # No new approval, image, launch or partition operation is introduced here.
    # The original executor performs its complete authorization and 16,983-pin
    # verification, new storage admission and fresh device preflight again.
    archive = archive_failed_preflight(BASE, audit)
    audit.update(state='0335-initial-no-device-preflight-preserved-before-single-continuation',
                 ready_sha256=READY, approval_sha256=APPROVAL, wrapper_sha256=sha(Path(__file__)),
                 unchanged_frozen_executor_sha256=sha(runner), boot_retries=0,
                 additional_device_writes=0)
    with (archive / 'resume-audit.json').open('x') as stream:
        json.dump(audit, stream, indent=2)
        stream.write('\n')
    spec = importlib.util.spec_from_file_location('frozen_335_executor', runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main()


if __name__ == '__main__':
    raise SystemExit(main())
