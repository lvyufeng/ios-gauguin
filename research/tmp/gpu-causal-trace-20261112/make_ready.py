#!/usr/bin/env python3
"""Pin the exact 301 image, read-only preflight and one-shot executor."""
from pathlib import Path
import hashlib
import json

M = Path('/Users/baai/Project/ios-gauguin')
W = Path(__file__).resolve().parent
R = W.parents[2]
C = W/'device-candidate'
CAP = W/'current-capture'
BACKUP = M/'research/tmp/metal-hardware-20261112/backup/iosroot-current.hfsx'
builds = list((R/'.deps-cache/p0-20261105/build301-causal-trace/runs').glob('gauguin.*/build-manifest.json'))
assert len(builds) == 1, builds
paths = [
    W/'trial-plan.json', W/'current-capture-profile.json',
    W/'candidate-capture-expectations.json', W/'storage-trial-admission.json',
    W/'prepare_delta.py', W/'test_delta.py', W/'metal_ca_c5_delta.py',
    W/'execute_trial.py', W/'delta-model/result.json',
    R/'research/tmp/ui301-image.img', R/'research/tmp/ui301-image.json',
    R/'research/tmp/ui301-review.json', R/'research/tmp/ui301-payload.bin',
    R/'research/tmp/ui301-package.py', R/'research/tmp/ui301-review.py',
    R/'research/tmp/ui301-native-v2/result.json', R/'research/tmp/ui301-host-v4/result.json',
    R/'research/tmp/ui301-kernel-out/System/Library/Kernels/kernel.development.gauguin',
    builds[0], R/'xnu/patches/0224-gauguin-causal-ui-trace.patch',
    R/'xnu/patches/series', R/'tools/ui_trace_log.py', R/'tools/xnu-check-tu.py',
    M/'research/tmp/metal-ca-c4-20261112/native-final-v3/GauguinMetalDesktop.bundle/GauguinMetalDesktop',
    M/'tools/recovery_marker.py', M/'tools/storage-budget.py',
    M/'research/tmp/dsh-0175/local_hfs175v3.py',
    M/'research/tmp/dsh-0175/write_root_delta175v2.py',
    M/'research/tmp/metal-hardware-repeat2-20261112/capture_owned.py',
    M/'research/tmp/dsh-0174/observe_ready_fastboot174.sh',
    M/'tools/sweet-log-pull.sh', M/'tools/kernel_banner.py', BACKUP,
    *sorted(p for p in CAP.iterdir() if p.is_file()),
    *sorted(p for p in C.iterdir() if p.is_file()),
]
assert all(p.is_file() for p in paths)
assert len(paths) == len({p.resolve() for p in paths})

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()

pins = {str(p.resolve()):sha(p) for p in paths}
assert pins[str(BACKUP)] == 'a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608'
plan = json.loads((W/'trial-plan.json').read_text())
image = json.loads((R/'research/tmp/ui301-image.json').read_text())
review = json.loads((R/'research/tmp/ui301-review.json').read_text())
capture = json.loads((CAP/'result.json').read_text())
manifest = json.loads(builds[0].read_text())
storage = json.loads((W/'storage-trial-admission.json').read_text())
assert plan['image_sha256'] == image['image_sha256'] == review['image_sha256'] == sha(R/'research/tmp/ui301-image.img')
assert plan['install_plan_sha256'] == sha(C/'install-plan.json')
assert plan['root_before_sha256'] == capture['root_header_sha256']
assert plan['boot_command'] == image['command'] and len(plan['boot_command'].encode()) == 601
assert manifest['state'] == 'built' and manifest['make_exit'] == 0
assert manifest['kernel']['sha256'] == image['kernel_sha256']
assert storage['admitted'] and storage['current_accounted_bytes']+storage['planned_batch_bytes'] <= storage['limit_bytes']
assert not (W/'approval.json').exists() and not (W/'execution').exists()
ready = dict(state='ready-causal-ui-one-shot',
    plan_sha256=sha(W/'trial-plan.json'),
    install_plan_sha256=plan['install_plan_sha256'],
    image_sha256=plan['image_sha256'],
    root_header_sha256=plan['root_before_sha256'],
    old_full_backup_sha256=pins[str(BACKUP)],
    input_pins=pins, pin_count=len(pins),
    approval_pending=True,device_writes=0,boot_attempts=0)
with (W/'ready.json').open('x') as stream:
    json.dump(ready,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(state=ready['state'],ready_sha256=sha(W/'ready.json'),
    plan_sha256=ready['plan_sha256'],pin_count=len(pins),
    approval_pending=True,device_writes=0),indent=2))
