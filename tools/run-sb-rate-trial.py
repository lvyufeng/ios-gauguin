#!/usr/bin/env python3
"""One separately approved SpringBoard rate-observer boot and exact restoration."""

import hashlib
import importlib.util
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
STATE = WORK/'research/tmp/sb-rate-20261112'
EXEC = STATE/'execution'
LOG_PATHS = ('/private/var/tmp/gauguin-gles180.log',
             '/private/var/tmp/gauguin-gles180.stderr.log',
             '/private/var/log/backboardd.log')
SPRINGBOARD_LOG = '/private/var/log/springboard.log'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def require(ok,why):
    if not ok:
        raise ValueError(why)


def load(path):
    return json.loads(Path(path).read_bytes())


def save(path,data):
    with Path(path).open('x') as stream:
        json.dump(data,stream,indent=2)
        stream.write('\n')


def module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def authorization(plan_path,ready_path,approval_path):
    """All checks here precede device IO and an execution directory claim."""
    plan,ready = load(plan_path),load(ready_path)
    require(ready['state']=='ready-SpringBoard-rate-one-shot' and
            ready['trial_plan_sha256']==sha(plan_path) and
            ready['install_plan_sha256']==sha(STATE/'slot-delta-v2/install-plan.json') and
            ready['image_sha256']==plan['image_sha256'], 'reviewed trial pins differ')
    require(approval_path.exists(), 'no individual SpringBoard trial approval; zero device IO')
    approval = load(approval_path)
    expected = ('approved','one_shot','allow_install','allow_restore','allow_rollback',
                'allow_misc_marker','allow_temporary_boot','allow_recovery_fallback')
    require(all(approval.get(key) is True for key in expected) and
            approval.get('fixture_only') is not True and
            approval.get('plan_sha256')==ready['install_plan_sha256'] and
            approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
            approval.get('image_sha256')==plan['image_sha256'] and
            approval.get('source')=='actual-user-SpringBoard-rate-trial-reply' and
            isinstance(approval.get('question_item_id'),str) and approval['question_item_id'] and
            isinstance(approval.get('user_answer'),str) and approval['user_answer'].strip() and
            approval.get('user_answer_sha256')==hashlib.sha256(approval['user_answer'].encode()).hexdigest(),
            'separate user reply is not bound to this exact trial')
    require(plan['state']=='prepared-SpringBoard-rate-observer-one-shot' and
            plan['install_plan_sha256']==ready['install_plan_sha256'] and
            plan['image_sha256']==sha(plan['image']) and
            plan['observer_helper'] in ready['input_pins'] and
            plan['image'] in ready['input_pins'] and
            plan['temporary_boots']==1 and plan['boot_retries']==0 and
            plan['install_userdata_bytes']==1380352 and
            plan['normal_restore_userdata_bytes']==1380352 and
            plan['normal_userdata_write_bytes']==2760704 and
            plan['maximum_userdata_write_bytes']==6901760 and
            plan['misc_write_bytes']==13 and plan['observer_seconds']==780 and
            plan['failed_restore_retry_limit']==1 and
            plan['maximum_fastboot_reboot_recovery_fallbacks']==1 and
            plan['storage_reserve_bytes']==1073741824 and
            plan['no_new_files_or_HFSX_allocations'] is True and
            plan['diagnostic_only'] is True and
            plan['physical_FPS_qualified'] is False and
            plan['retry_only_after_verified_rollback'] is True,
            'unexpected SpringBoard trial scope')
    require(not EXEC.exists(), 'one-shot execution already claimed')
    for path,digest in ready['input_pins'].items():
        require(sha(path)==digest,'reviewed input changed: '+path)
    budget = subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),
                             '--planned-bytes',str(plan['storage_reserve_bytes'])],
                            capture_output=True,text=True,timeout=120)
    require(budget.returncode==0 and json.loads(budget.stdout)['admitted'] is True,
            'trial storage reserve no longer admitted')
    return plan,ready,approval,json.loads(budget.stdout)


def static_compare(before,after):
    require(set(before['files'])==set(after['files']) and
            before['directories']==after['directories'], 'root file/directory set changed')
    for path,old in before['files'].items():
        new = after['files'][path]
        require(old['present'] and new['present'] and
                all(old[key]==new[key] for key in ('uid','gid','mode')),
                'root file metadata changed: '+path)
        if path not in LOG_PATHS:
            require(all(old[key]==new[key] for key in ('bytes','sha256','fork')),
                    'static root file changed: '+path)


def capture_as(name,phase,header,capture):
    profile = load(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112/current-capture-profile.json')
    profile['out'] = str((EXEC/name).relative_to(MAIN))
    profile['phase'] = phase
    profile['expected_header_sha256'] = header
    return capture(profile)


def read_springboard(io,HFS,Remote):
    remote = Remote(io)
    hfs = HFS(stream=remote,size=17179869184)
    try:
        row = hfs.paths[SPRINGBOARD_LOG]
        require(row['type']==2 and not row['flags']&0x20 and
                row['data']['logical']<=33554432, 'SpringBoard log absent/oversized')
        return hfs.content(SPRINGBOARD_LOG)
    finally:
        hfs.close()


def recovery_for_rollback(RecoveryIO,approval,state):
    try:
        return RecoveryIO()
    except Exception as original:
        require(approval.get('allow_recovery_fallback') is True and state['attempts']==0,
                'recovery fallback not approved or already used')
        found = subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=5)
        rows = [line.split() for line in found.stdout.splitlines() if line.strip()]
        require(len(rows)==1 and len(rows[0])>=2 and rows[0][1]=='fastboot',
                'neither recovery nor one fastboot device available')
        serial = rows[0][0]
        product = subprocess.run(['fastboot','-s',serial,'getvar','product'],
                                 capture_output=True,text=True,timeout=5)
        require(product.returncode==0 and 'product: gauguinpro' in product.stdout+product.stderr,
                'rollback fastboot product differs')
        state['attempts'] += 1
        reboot = subprocess.run(['fastboot','-s',serial,'reboot','recovery'],
                                capture_output=True,text=True,timeout=10)
        require(reboot.returncode==0,'fastboot recovery fallback failed')
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try:return RecoveryIO()
            except Exception:time.sleep(2)
        raise RuntimeError('recovery did not return after bounded fallback') from original


def fastboot_identity():
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        found=subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=5)
        rows=[line.split() for line in found.stdout.splitlines() if line.strip()]
        if rows:
            require(len(rows)==1 and len(rows[0])>=2 and rows[0][1]=='fastboot',
                    'ambiguous fastboot devices')
            serial=rows[0][0]
            product=subprocess.run(['fastboot','-s',serial,'getvar','product'],
                                   capture_output=True,text=True,timeout=5)
            require(product.returncode==0 and 'product: gauguinpro' in product.stdout+product.stderr,
                    'wrong fastboot product')
            return serial
        time.sleep(1)
    raise RuntimeError('fastboot did not become ready; no boot retry')


def marker_rollback(io,before,READ,WRITE,MARKER):
    actual=io.run(io.adb+['exec-out',READ]).stdout
    require(actual==MARKER+before[len(MARKER):],
            'misc changed since marker write; no stale rollback')
    io.run(io.adb+['exec-in',WRITE],data=before[:len(MARKER)])
    require(io.run(io.adb+['exec-out',READ]).stdout==before,
            'preboot misc marker restoration readback failed')


def classify_observer(analysis,prefix_preserved):
    if not prefix_preserved:
        return 'SpringBoard-log-tail-ambiguous-root-restored'
    if not analysis['observer_seen']:
        return 'SpringBoard-observer-not-seen-root-restored'
    if not analysis['records_in_window']:
        return 'SpringBoard-observer-active-no-samples-root-restored'
    return 'SpringBoard-rate-observed-root-restored'


def main():
    plan_path,ready_path,approval_path=(STATE/'trial-plan.json',STATE/'ready.json',
                                        STATE/'approval.json')
    plan,ready,approval,budget=authorization(plan_path,ready_path,approval_path)
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
                 str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112'),
                 str(MAIN/'research/tmp/metal-hardware-repeat2-20261112'),str(MAIN/'tools')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    from capture_owned import capture
    from recovery_marker import READ,WRITE,MARKER,set_recovery_marker
    install_core=module('sb_install',WORK/'tools/sb-rate-slot-install-io.py')
    restore_build=module('sb_restore_build',WORK/'tools/build-sb-rate-restore.py')
    restore_core=module('sb_restore_io',WORK/'tools/sb-rate-slot-restore-io.py')
    rate_log=module('sb_rate_log',WORK/'tools/analyze-sb-rate-log.py')
    ui_log=module('ui_trace_log',WORK/'tools/ui_trace_log.py')
    EXEC.mkdir(exist_ok=False)
    save(EXEC/'claim.json',{'pid':os.getpid(),'started':time.time(),
                            'trial_plan_sha256':ready['trial_plan_sha256'],
                            'approval_sha256':sha(approval_path)})
    save(EXEC/'storage-preflight.json',budget)
    def report(row):
        with (EXEC/'progress.jsonl').open('a') as stream:
            json.dump(row,stream);stream.write('\n')
            stream.flush();os.fsync(stream.fileno())
    result={'state':'preflight','boot_attempts':0,'partition_write_phase':'none'}
    installed=marker_written=boot_started=restored=restore_attempted=False
    fallback={'attempts':0}
    before_misc=None
    base_plan=STATE/'slot-delta-v2'
    capture_dir=STATE/'slot-capture-v2'
    try:
        before=capture_as('fresh-before','before-boot',plan['root_header_sha256'],capture)
        io=RecoveryIO()
        before_sb=read_springboard(io,HFS,Remote)
        (EXEC/'springboard-before.log').write_bytes(before_sb)
        before_misc=(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112/device-candidate/misc-before.bin').read_bytes()
        require(len(before_misc)==4096 and hashlib.sha256(before_misc).hexdigest()==plan['misc_before_sha256'] and
                io.run(io.adb+['exec-out',READ]).stdout==before_misc,
                'misc preimage changed')
        installed_result=install_core.install(base_plan,capture_dir,approval,io,HFS,Remote,report)
        installed=installed_result['state']=='install-applied-and-HFSX-verified'
        save(EXEC/'install-result.json',installed_result)
        require(installed_result['state']=='install-applied-and-HFSX-verified',
                'installation failed or rolled back')
        result['partition_write_phase']='observer-installed'
        marker=set_recovery_marker(io,{'misc_recovery_marker_approved':True,
                                       'allow_rollback':True,
                                       'misc_backup_sha256':plan['misc_before_sha256']},before_misc)
        marker_written=True
        save(EXEC/'marker-result.json',marker)
        io.run(io.adb+['reboot','bootloader'])
        fastboot_identity()
        with (EXEC/'observer.log').open('x') as log:
            child=subprocess.Popen(['bash',plan['observer_helper'],plan['image'],
                                    str(EXEC/'kernel.log'),str(plan['observer_seconds'])],
                                   stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            boot_started=True
            result['boot_attempts']=1
            save(EXEC/'observer-process.json',{'pid':child.pid,'pgid':child.pid,
                                               'image_sha256':plan['image_sha256'],
                                               'boot_attempts':1})
            try:code=child.wait(timeout=plan['observer_seconds']+80)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM)
                child.wait(timeout=10)
                raise RuntimeError('observer timed out; no boot retry')
        result['observer_exit']=code
        if code==5:
            boot_started=False
        require(code!=5,'fastboot boot failed before temporary launch')
        ps=subprocess.run(['ps','-axo','pid=,pgid=,comm='],capture_output=True,text=True,check=True)
        require(not [line for line in ps.stdout.splitlines()
                     if len(line.split(None,2))==3 and line.split(None,2)[1]==str(child.pid)],
                'observer process group remains live')
        io=recovery_for_rollback(RecoveryIO,approval,fallback)
        after_boot=capture_as('post-capture','after-boot',None,capture)
        after_sb=read_springboard(io,HFS,Remote)
        (EXEC/'springboard-after.log').write_bytes(after_sb)
        result['springboard_log_prefix_preserved']=after_sb.startswith(before_sb)
        (EXEC/'springboard-new.log').write_bytes(
            after_sb[len(before_sb):] if result['springboard_log_prefix_preserved'] else after_sb)
        for path in LOG_PATHS:
            old_file=(EXEC/'fresh-before'/before['files'][path]['output']).read_bytes()
            new_file=(EXEC/'post-capture'/after_boot['files'][path]['output']).read_bytes()
            preserved=new_file.startswith(old_file)
            result.setdefault('other_log_prefix_preserved',{})[path]=preserved
            (EXEC/(before['files'][path]['output']+'.current')).write_bytes(
                new_file[len(old_file):] if preserved else new_file)
        dynamic=restore_build.prepare(base_plan,capture_dir,io,HFS,Remote,
                                      EXEC/'restore-inputs')
        restored_result=restore_core.restore(base_plan,EXEC/'restore-inputs',approval,
                                             io,HFS,Remote,report)
        restore_attempted=True
        save(EXEC/'restore-result.json',restored_result)
        if restored_result['state']=='restore-failed-rollback-verified':
            io=recovery_for_rollback(RecoveryIO,approval,fallback)
            dynamic=restore_build.prepare(base_plan,capture_dir,io,HFS,Remote,
                                          EXEC/'retry-restore-inputs')
            restored_result=restore_core.restore(base_plan,EXEC/'retry-restore-inputs',approval,
                                                 io,HFS,Remote,report)
            save(EXEC/'retry-restore-result.json',restored_result)
        require(restored_result['state']=='restore-applied-and-readback-verified',
                'postboot restoration failed or rolled back')
        restored=True;result['partition_write_phase']='original-files-restored'
        final=capture_as('restored-capture','after-boot',after_boot['root_header_sha256'],capture)
        static_compare(before,final)
        require(code==0 and (EXEC/'kernel.log').is_file(),
                'observer failed or kernel log absent')
        kernel=(EXEC/'kernel.log').read_text(errors='replace')
        require(plan['kernel_banner'] in kernel,'kernel banner not from pinned observer image')
        sb_text=(EXEC/'springboard-new.log').read_text(errors='replace')
        parsed=rate_log.parse(sb_text)
        try:
            trace=ui_log.parse(kernel)
            save(EXEC/'ui-trace.json',trace)
            bounds=rate_log.window_from_kernel(kernel)
        except ValueError as problem:
            result['ui_trace_error']=repr(problem)
            bounds=(None,None)
        analysis=rate_log.summarize(parsed,*bounds)
        save(EXEC/'springboard-rate-analysis.json',analysis)
        result['analysis']={'observer_seen':analysis['observer_seen'],
                            'animation_requests':analysis['animation']['count'],
                            'main_turns':analysis['turns']['count'],
                            'lost_rows':analysis['lost_rows_in_log_tail'],
                            'log_tail_qualified':result['springboard_log_prefix_preserved'],
                            'physical_fps_qualified':False}
        result['state']=classify_observer(analysis,result['springboard_log_prefix_preserved'])
    except (Exception,KeyboardInterrupt) as error:
        result.update(state='trial-incomplete-or-failed',error=repr(error))
        if installed and not restored and not restore_attempted:
            try:
                io=recovery_for_rollback(RecoveryIO,approval,fallback)
                restore_attempted=True
                restore_build.prepare(base_plan,capture_dir,io,HFS,Remote,
                                      EXEC/'fallback-restore-inputs')
                fallback_result=restore_core.restore(base_plan,EXEC/'fallback-restore-inputs',
                                                     approval,io,HFS,Remote,report)
                save(EXEC/'fallback-restore-result.json',fallback_result)
                restored=fallback_result['state']=='restore-applied-and-readback-verified'
                if restored:result['partition_write_phase']='original-files-restored-after-failure'
            except (Exception,KeyboardInterrupt) as problem:
                result['fallback_restore_error']=repr(problem)
        if marker_written and not boot_started and before_misc is not None:
            try:
                io=recovery_for_rollback(RecoveryIO,approval,fallback)
                marker_rollback(io,before_misc,READ,WRITE,MARKER)
                result['preboot_misc_marker_restored']=True
            except (Exception,KeyboardInterrupt) as problem:
                result['preboot_misc_restore_error']=repr(problem)
    result.update(installed=installed,restored=restored,
                  restore_attempted=restore_attempted,
                  recovery_fallbacks=fallback['attempts'],
                  misc_marker_written=marker_written,
                  boot_started=boot_started,
                  finished=time.time())
    save(EXEC/'result.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['state']=='SpringBoard-rate-observed-root-restored' else 1


if __name__=='__main__':
    raise SystemExit(main())
