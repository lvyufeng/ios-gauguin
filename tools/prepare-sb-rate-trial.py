#!/usr/bin/env python3
"""Pin a separate one-shot SpringBoard observer trial; never open device IO."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
STATE = WORK/'research/tmp/sb-rate-20261112'
W301 = MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112'
BACKUP = MAIN/'research/tmp/metal-hardware-20261112/backup/iosroot-current.hfsx'
RESERVE = 1073741824


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')


def main():
    plan_path,ready_path,admission_path=(STATE/'trial-plan.json',STATE/'ready.json',
                                         STATE/'storage-trial-admission.json')
    assert not any(path.exists() for path in (plan_path,ready_path,admission_path,
                                               STATE/'approval.json',STATE/'execution'))
    install_path = STATE/'slot-delta-v2/install-plan.json'
    image_result_path = STATE/'image304-v1/result.json'
    image_review_path = STATE/'image304-review-v1.json'
    misc_path = W301/'research/tmp/gpu-causal-trace-20261112/device-candidate/misc-before.bin'
    build_manifest = WORK/'.deps-cache/p0-20261105/build304-sb-policy/runs/gauguin.HGK85Q/build-manifest.json'
    install,image,review,manifest=[json.loads(path.read_bytes()) for path in
                                   (install_path,image_result_path,image_review_path,build_manifest)]
    assert install['state']=='prepared-offline-existing-slot-SpringBoard-observer-delta'
    assert install['changed_ranges']==6 and install['install_write_bytes']==1380352
    assert install['normal_install_restore_userdata_bytes']==2760704
    assert install['root_header_sha256']=='6e272d2e11ae716993301df334c35eeb5498b0a77adbccd965f924e28a5e77e4'
    assert image['state']=='offline-SpringBoard-rate-observer-image-not-device-qualified'
    assert image['image_sha256']==review['image_sha256']==sha(Path(image['image']))
    assert image['image_sha256']=='a11b7b7424af91803295d3cb1338e6084b69c9af7ff97ab28d7c500f2b9ea804'
    assert image['kernel_sha256']==manifest['kernel']['sha256']
    assert image['kernel_banner']==manifest['kernel_banner']
    assert review['state']=='independent-offline-SpringBoard-rate-image-review'
    assert (review['adt_unchanged_except_firmware_pa_and_PAS_tail'] and
            review['firmware_content_padding_unchanged'] and
            review['new_policy_symbols_in_kernel'])
    assert 'sweet_sb_rate_probe=1' in image['command'].split()
    assert 'sweetfb_hz=60' in image['command'].split() and 'touch_lat=1' in image['command'].split()
    assert len(image['command'].encode())==604
    assert misc_path.read_bytes()==bytes(4096)
    assert sha(misc_path)=='ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7'
    assert sha(BACKUP)=='a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608'
    budget = subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),
                             '--planned-bytes',str(RESERVE)],capture_output=True,
                            text=True,timeout=120,check=True)
    admission=json.loads(budget.stdout)
    assert admission['admitted'] and admission['current_accounted_bytes']+RESERVE<=500000000000
    save(admission_path,admission)
    observer = MAIN/'research/tmp/dsh-0174/observe_ready_fastboot174.sh'
    plan = {'state':'prepared-SpringBoard-rate-observer-one-shot',
            'image':image['image'],'image_sha256':image['image_sha256'],
            'image_bytes':image['image_bytes'],'kernel_banner':image['kernel_banner'],
            'boot_command':image['command'],'observer_helper':str(observer),
            'service_seconds':600,'observer_seconds':780,
            'root_header_sha256':install['root_header_sha256'],
            'install_plan_sha256':sha(install_path),
            'misc_before_sha256':sha(misc_path),'misc_write_bytes':13,
            'temporary_boots':1,'boot_retries':0,
            'install_userdata_bytes':1380352,'normal_restore_userdata_bytes':1380352,
            'normal_userdata_write_bytes':2760704,
            'maximum_userdata_write_bytes':6901760,
            'failed_restore_retry_limit':1,
            'retry_only_after_verified_rollback':True,
            'maximum_fastboot_reboot_recovery_fallbacks':1,
            'storage_reserve_bytes':RESERVE,
            'springboard_log_path':'/private/var/log/springboard.log',
            'no_new_files_or_HFSX_allocations':True,
            'changed_root_files':[row['path'] for row in install['rows'].values()],
            'observer_activation':'SWEET SB RATE: active',
            'diagnostic_only':True,'physical_FPS_qualified':False,
            'needs_separate_user_approval':True,
            'recommended_after_0301_diagnostic':True,
            'device_writes':0,'boot_attempts':0}
    save(plan_path,plan)
    pins=[plan_path,admission_path,install_path,STATE/'slot-capture-v2/result.json',
          image_result_path,image_review_path,Path(image['image']),build_manifest,
          STATE/'install-model-review-v2.json',STATE/'restore-model-review-v5.json',
          misc_path,BACKUP,observer,MAIN/'tools/sweet-log-pull.sh',
          MAIN/'tools/kernel_banner.py',MAIN/'tools/recovery_marker.py',
          MAIN/'tools/storage-budget.py',MAIN/'research/tmp/dsh-0175/local_hfs175v3.py',
          MAIN/'research/tmp/dsh-0175/write_root_delta175v2.py',
          MAIN/'research/tmp/metal-hardware-repeat2-20261112/capture_owned.py',
          W301/'research/tmp/gpu-causal-trace-20261112/current-capture-profile.json',
          WORK/'tools/run-sb-rate-trial.py',WORK/'tools/sb-rate-slot-install-io.py',
          WORK/'tools/sb-rate-slot-restore-io.py',WORK/'tools/build-sb-rate-restore.py',
          WORK/'tools/analyze-sb-rate-log.py',WORK/'tools/ui_trace_log.py',
          Path(__file__).resolve()]
    for name in install['rows']:
        pins.extend((STATE/'slot-capture-v2'/(name+'-old-data.bin'),
                     STATE/'slot-capture-v2'/(name+'-old-catalog.bin'),
                     STATE/'slot-delta-v2'/(name+'-new-data.bin'),
                     STATE/'slot-delta-v2'/(name+'-new-catalog.bin')))
    assert len(pins)==len(set(path.resolve() for path in pins)) and all(path.is_file() for path in pins)
    pin_hashes={str(path.resolve()):sha(path) for path in pins}
    assert all(sha(Path(path))==digest for path,digest in pin_hashes.items())
    ready={'state':'ready-SpringBoard-rate-one-shot',
           'trial_plan_sha256':sha(plan_path),
           'install_plan_sha256':plan['install_plan_sha256'],
           'image_sha256':plan['image_sha256'],
           'root_header_sha256':plan['root_header_sha256'],
           'input_pins':pin_hashes,'pin_count':len(pin_hashes),
           'approval_pending':True,'device_writes':0,'boot_attempts':0}
    save(ready_path,ready)
    print(json.dumps({'state':ready['state'],'ready_sha256':sha(ready_path),
                      'trial_plan_sha256':ready['trial_plan_sha256'],
                      'install_plan_sha256':ready['install_plan_sha256'],
                      'image_sha256':ready['image_sha256'],
                      'pin_count':ready['pin_count'],'device_writes':0},indent=2))


if __name__=='__main__':
    main()
