#!/usr/bin/env python3
"""Freeze the complete 0315 trial and rollback before requesting approval."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/sb-stack-315'
BASE314=MAIN/'research/tmp/gauguin-sb-spawn-worktree-20261114/research/tmp/sb-spawn-314'
W301=MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112'
BACKUP=MAIN/'research/tmp/metal-hardware-20261112/backup/iosroot-current.hfsx'
RESERVE=402653184


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def save(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')


def main():
    assert not any((STATE/name).exists() for name in ('trial-plan.json','ready.json','approval.json','execution'))
    install_path=STATE/'slot-delta/install-plan.json'
    image_path=BASE314/'ui314-image.json';review_path=BASE314/'ui314-review.json'
    manifest_path=BASE314/'local-link/build-manifest.json'
    install,image,review,manifest=[json.loads(p.read_text()) for p in (install_path,image_path,review_path,manifest_path)]
    assert install['state']=='prepared-four-file-SpringBoard-cadence-delta'
    assert install['install_write_bytes']==1814528 and install['changed_ranges']==8
    assert install['root_header_sha256']=='3c5af5b175dabaa759a1ff22523a103d30cfe375a421f7757a2f37f80fea672e'
    assert image['state']=='offline-SpringBoard-spawn-candidate'
    assert review['state']=='reviewed-offline-SpringBoard-spawn314-image'
    assert sha(image['image'])==image['image_sha256']==review['image_sha256']=='1e78df251263cdb2c524631d3c27f9db93391fd0134a7ef9e01e4e7d4dd19428'
    assert sha(manifest_path)==image['manifest_sha256']
    assert image['kernel_sha256']==manifest['kernel']['sha256']==review['kernel_sha256']
    assert image['kernel_banner']==manifest['kernel_banner']
    assert manifest['inputs_unchanged'] and review['undefined_symbols_unchanged']
    assert all(token in image['command'].split() for token in ('sbp=1','swp=3','sweetgpuasync=1','sweetfb_hz=60','touch_lat=1','sweetnvt=0'))
    assert len(image['command'].encode())==593
    batch=json.loads((STATE/'storage-trial-batch-admission.json').read_text())
    assert batch['admitted'] and batch['planned_batch_bytes']==450000000
    native_path=STATE/'native-v3/result.json';native=json.loads(native_path.read_text())
    assert native['state']=='native-iOS16-SpringBoard-timing-stack-probe-not-device-qualified'
    assert native['sha256']==sha(native['binary'])==install['rows']['eagl']['new_file_sha256']=='10683efc71f95f1a79563727cfef10374df8d1ec94f6249a83328b7d6660683b'
    assert install['binary_receipt_sha256']==sha(native_path)
    assert native['main_thread_sampling'] and native['maximum_samples']==64 and native['maximum_stack_frames']==16
    abi=json.loads((STATE/'abi-v3/result.json').read_text())
    assert abi['binary_sha256']==native['sha256'] and not abi['missing_imports'] and abi['checked_imports']==69
    for receipt in (native,json.loads((STATE/'reused-image.json').read_text()),
                    json.loads((STATE/'stack-host-v2/result.json').read_text()),
                    json.loads((STATE/'observer-host-v3.json').read_text()),
                    json.loads((STATE/'stack-log-host-v1.json').read_text())):
        for path,digest in receipt['input_pins'].items():assert sha(path)==digest,path
    model_paths=[STATE/'install-model-review.json',STATE/'restore-model-review.json']
    for path in model_paths:
        model=json.loads(path.read_text())
        assert model['state'].startswith('passed-') and model['base_plan_sha256']==sha(install_path)
        assert model['device_writes']==0 and model['rollback_verified'] and model['partial_write_failure_tested']
        for name,digest in model['input_pins'].items():assert sha(name)==digest,name
    misc=W301/'research/tmp/gpu-causal-trace-20261112/device-candidate/misc-before.bin'
    assert misc.read_bytes()==bytes(4096)
    assert sha(BACKUP)=='a11ef472d1625485d48741a35bc9440ad44dd3f4c97894434fb726d2dc7c9608'
    # Bound all three full captures plus duplicated log tails and rollback files.
    helper=WORK/'tools/capture-sb-cadence-root.py'
    spec=importlib.util.spec_from_file_location('bounded_capture',helper)
    capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
    per_capture=sum(capture.FILE_LIMITS.get(path,1048576) for path in capture.PATHS)
    log_bound=4*8388608
    bound=dict(full_captures=3,per_capture_max_bytes=per_capture,
        extra_log_copies_max_bytes=log_bound+3*8388608,
        kernel_dump_max_bytes=1025*4096+3*1024*4096,rollback_temp_max_bytes=4*1814528,
        metadata_max_bytes=33554432,reserve_bytes=RESERVE)
    bound['worst_case_bytes']=3*per_capture+bound['extra_log_copies_max_bytes']+bound['kernel_dump_max_bytes']+4*1814528+33554432
    bound['kernel_text_encoding']='UTF-8 replacement: at most3 outputbytes per ringbyte; raw1025blocks included'
    assert bound['worst_case_bytes']==385363808 and bound['worst_case_bytes']<RESERVE
    save(STATE/'storage-bound.json',bound)
    budget=subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),'--planned-bytes',str(RESERVE)],capture_output=True,text=True,timeout=180,check=True)
    admission=json.loads(budget.stdout);assert admission['admitted']
    save(STATE/'storage-trial-admission.json',admission)
    observer=MAIN/'research/tmp/dsh-0174/observe_ready_fastboot174.sh'
    plan=dict(state='prepared-SpringBoard-stack315-one-shot',image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_banner=image['kernel_banner'],boot_command=image['command'],observer_helper=str(observer),
        service_seconds=600,observer_seconds=780,root_header_sha256=install['root_header_sha256'],install_plan_sha256=sha(install_path),
        misc_before_sha256=sha(misc),misc_write_bytes=13,maximum_host_misc_write_bytes=26,
        temporary_boots=1,boot_retries=0,install_userdata_bytes=1814528,
        normal_restore_userdata_bytes=1814528,normal_userdata_write_bytes=3629056,maximum_userdata_write_bytes=9072640,
        failed_restore_retry_limit=1,retry_only_after_verified_rollback=True,maximum_fastboot_reboot_recovery_fallbacks=1,
        storage_reserve_bytes=RESERVE,observer_python_utf8=True,
        main_thread_sampling=dict(version=315,start_us=220000000,end_us=270000000,period_us=1000000,min_turn_us=250000,budget_us=2000,max_samples=64,depth=16,stack_window_bytes=65536,hard_realtime_pause_limit=False),
        springboard_log_path='/private/var/log/springboard.log',
        no_new_files_or_HFSX_allocations=True,changed_root_files=[r['path'] for r in install['rows'].values()],
        wake_button_pairs_max=1,require_display_on=True,scripted_strokes=13,scripted_reports=442,async_compositor=True,
        input_origin='synthetic',protected_SpringBoard_exec_insertion=True,diagnostic_only=True,physical_FPS_qualified=False,needs_separate_user_approval=True,
        device_writes=0,boot_attempts=0)
    plan_path=STATE/'trial-plan.json';save(plan_path,plan)
    pins=[plan_path,STATE/'storage-bound.json',STATE/'storage-trial-admission.json',STATE/'storage-trial-batch-admission.json',
          install_path,STATE/'slot-capture/result.json',image_path,review_path,Path(image['image']),manifest_path,*model_paths,misc,BACKUP,observer,
          STATE/'expected-baseline.json',STATE/'capture-profile.json',native_path,Path(native['binary']),STATE/'abi-v3/result.json',
          STATE/'observer-host-v3.json',STATE/'stack-host-v2/result.json',STATE/'stack-log-host-v1.json',STATE/'source-review.json',STATE/'reused-image.json',
          BASE314/'native-v1/result.json',BASE314/'patch-replay.json',BASE314/'exec-host-v1/result.json',
          MAIN/'tools/sweet-log-pull.sh',MAIN/'tools/sweet-log.py',MAIN/'tools/kernel_banner.py',MAIN/'tools/recovery_marker.py',MAIN/'tools/storage-budget.py',
          MAIN/'research/tmp/dsh-0175/local_hfs175v3.py',MAIN/'research/tmp/dsh-0175/write_root_delta175v2.py',W301/'research/tmp/gpu-causal-trace-20261112/metal_ca_c5_delta.py',
          WORK/'tools/analyze-sb-rate-log.py',WORK/'tools/analyze-sb-stack-log.py',WORK/'tools/analyze-ui-timeline.py',WORK/'tools/ui_trace_log.py',WORK/'tools/sb_cadence_launch.py',
          WORK/'graphics/gauguin-sb-rate-trace/SBRateTrace.m',*sorted((WORK/'graphics/gauguin-sb-rate-trace').glob('SBStack*.h'))]
    pins.extend(sorted((WORK/'tools').glob('*sb-cadence*.py')))
    for name in install['rows']:
        for folder,kind in [('slot-capture','old'),('slot-delta','new')]:
            pins.extend(STATE/folder/(name+'-'+kind+'-'+part+'.bin') for part in ('data','catalog'))
    pins=sorted(set(p.resolve() for p in pins));assert all(p.is_file() for p in pins)
    hashes={str(p):sha(p) for p in pins}
    assert all(sha(name)==digest for name,digest in hashes.items())
    ready=dict(state='ready-SpringBoard-stack315-one-shot',trial_plan_sha256=sha(plan_path),install_plan_sha256=sha(install_path),image_sha256=image['image_sha256'],root_header_sha256=install['root_header_sha256'],input_pins=hashes,pin_count=len(hashes),approval_pending=True,device_writes=0,boot_attempts=0)
    save(STATE/'ready.json',ready)
    print(json.dumps({k:v for k,v in ready.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
