#!/usr/bin/env python3
"""Separately approved0339 one-shot; bounded writes, no forward restore retry."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from core339_scope import MAIN,WORK,BASE,PRIOR,APPROVAL_FLAGS,expected_plan,load,sha
import core339_install as INSTALL
import core339_restore as RESTORE

EXEC=BASE/'execution'


def require(ok,why):
    if not ok:raise ValueError(why)


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def save(path,value):
    raw=(json.dumps(value,indent=2)+'\n').encode()
    require(len(raw)<=2*1048576,'bounded trial receipt exceeded2MiB')
    with path.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())


def check_consent(approval,ready,plan):
    require(all(approval.get(k) is True for k in APPROVAL_FLAGS) and
        approval.get('fixture_only') is not True and
        approval.get('source')=='actual-user-core339-trial-reply' and
        approval.get('plan_sha256')==ready['install_plan_sha256'] and
        approval.get('trial_plan_sha256')==ready['trial_plan_sha256'] and
        approval.get('image_sha256')==plan['image_sha256'] and
        approval.get('provenance') in ('direct-user-message','async-question-reply') and
        (approval.get('provenance')!='async-question-reply' or
            isinstance(approval.get('question_item_id'),str) and bool(approval['question_item_id'])) and
        isinstance(approval.get('user_answer'),str) and bool(approval['user_answer'].strip()) and
        approval.get('user_answer_sha256')==hashlib.sha256(approval['user_answer'].encode()).hexdigest(),
        'new exact-scope actual user0339 reply required; previous and fixture grants cannot authorize this trial')


def authorization():
    # All filesystem/consent/pin/budget checks precede imports that construct
    # RecoveryIO and precede the exclusive execution directory claim.
    require(not EXEC.exists(),'0339 one-shot already claimed; never retry this execution')
    require((BASE/'approval.json').exists(),'0339 individual approval absent; zero device commands')
    plan,ready=load(BASE/'trial-plan.json'),load(BASE/'ready.json')
    require(ready['state']=='ready-core339-one-shot' and ready['pin_count']==len(ready['input_pins']) and
        ready['trial_plan_sha256']==sha(BASE/'trial-plan.json') and
        ready['install_plan_sha256']==sha(BASE/'slot-delta/install-plan.json') and
        plan==expected_plan(),'frozen0339 exact plan differs')
    approval=load(BASE/'approval.json');check_consent(approval,ready,plan)
    review=load(BASE/'final-review.json')
    require(review['state']=='reviewed-core339-one-shot' and review['ready_sha256']==sha(BASE/'ready.json') and
        review['all_pins_unchanged'] and review['restoration_precedes_analysis'] and
        review['collection_precedes_interpretation'],'independent frozen review missing or changed')
    for pins in (ready['input_pins'],review['input_pins']):
        for path,digest in pins.items():require(sha(path)==digest,'frozen input changed: '+path)
    require(sha(plan['image'])==plan['image_sha256'] and plan['observer_helper'] in ready['input_pins'],
        'fixed337 image/observer not pinned')
    budget=subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),'--planned-bytes','760000000'],
        capture_output=True,text=True,timeout=600)
    require(budget.returncode==0 and json.loads(budget.stdout)['admitted'] is True,
        'complete runtime batch no longer fits storage cap')
    return plan,ready,approval,json.loads(budget.stdout)


class BoundedIO:
    """Shared attempted-byte counters survive recovery handle replacement."""
    def __init__(self,raw,counters,read_misc,write_misc,marker,misc_original):
        self.raw=raw;self.counters=counters;self.read_misc=read_misc;self.write_misc=write_misc
        self.marker=marker;self.misc_original=misc_original
    def __getattr__(self,name):return getattr(self.raw,name)
    def write(self,offset,data):
        require(offset%4096==len(data)%4096==0 and 0<=offset<offset+len(data)<=17179869184,
            'userdata write outside root volume')
        require(self.counters['userdata_bytes']+len(data)<=30961664,'attempted userdata write cap exceeded')
        self.counters['userdata_bytes']+=len(data);self.raw.write(offset,data)
    def run(self,argv,**kwargs):
        if argv==self.adb+['exec-in',self.write_misc]:
            data=kwargs.get('data')
            require(data in (self.marker,self.misc_original[:13]) and len(data)==13 and
                self.counters['misc_bytes']+13<=26,'misc marker scope or write cap exceeded')
            self.counters['misc_bytes']+=13
        else:
            require('data' not in kwargs and argv in (self.adb+['exec-out',self.read_misc],self.adb+['reboot','bootloader']),
                'unexpected direct device command')
        return self.raw.run(argv,**kwargs)


def observe_once(plan,result,legacy):
    legacy.fastboot_identity()
    result['boot_attempts']=1 # Consume the sole launch even if Popen fails.
    child=None
    with (EXEC/'observer.log').open('x') as log:
        try:
            child=subprocess.Popen(['bash',plan['observer_helper'],plan['image'],str(EXEC/'kernel.log'),
                str(plan['observer_seconds'])],stdout=log,stderr=subprocess.STDOUT,start_new_session=True,
                env=dict(os.environ,PYTHONUTF8='1'))
            result['boot_started']=True
            save(EXEC/'observer-process.json',dict(pid=child.pid,pgid=child.pid,
                image_sha256=plan['image_sha256'],boot_attempts=1))
            try:code=child.wait(timeout=plan['observer_seconds']+80)
            except subprocess.TimeoutExpired:raise RuntimeError('observer timeout; no temporary boot retry')
        finally:
            if child is not None:
                # The pinned helper has its own group. Terminate only this
                # task's surviving group before touching recovery again.
                def members():
                    ps=subprocess.run(['ps','-axo','pid=,pgid=,stat='],capture_output=True,text=True,check=True)
                    return [r for line in ps.stdout.splitlines() if len(r:=line.split())==3 and
                        r[1]==str(child.pid) and not r[2].startswith('Z')]
                for sig in (signal.SIGTERM,signal.SIGKILL):
                    if not members():break
                    try:os.killpg(child.pid,sig)
                    except ProcessLookupError:pass
                    try:child.wait(timeout=5)
                    except subprocess.TimeoutExpired:pass
                    deadline=time.monotonic()+5
                    while members() and time.monotonic()<deadline:time.sleep(.1)
                result['observer_group_clear']=not members()
                require(result['observer_group_clear'],'observer owner remains; recovery IO withheld')
    result['observer_exit']=code
    if code==5:result['boot_started']=False
    require(code!=5,'fixed image boot failed before temporary launch; no boot retry')
    return code


def main(check_only=False):
    try:plan,ready,approval,budget=authorization()
    except (Exception,KeyboardInterrupt) as error:
        print('0339 gate refused before device IO: '+repr(error),flush=True);return 2
    if check_only:
        print('0339 exact-scope consent and frozen inputs accepted; device IO not invoked');return 0
    sys.path[:0]=[str(MAIN/'research/tmp/dsh-0175'),
        str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112'),
        str(MAIN/'tools')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    from recovery_marker import READ,WRITE,MARKER,set_recovery_marker
    legacy=module('unchanged_boot_recovery_helpers339',WORK/'tools/run-sb-cadence-trial.py')
    capture=module('capture339',WORK/'tools/capture-core339-root.py').capture
    independent=module('independent339',WORK/'tools/verify-core339-restore.py')
    analyze=module('analyze339',WORK/'tools/analyze-core339.py').analyze_saved
    misc_original=(BASE/'metadata-snapshot/misc-original.bin').read_bytes()
    require(len(misc_original)==4096 and hashlib.sha256(misc_original).hexdigest()==plan['misc_before_sha256'],
        'pinned misc preimage differs')
    EXEC.mkdir(exist_ok=False)
    save(EXEC/'claim.json',dict(pid=os.getpid(),started=time.time(),trial_plan_sha256=sha(BASE/'trial-plan.json'),
        approval_sha256=sha(BASE/'approval.json')))
    save(EXEC/'storage-preflight.json',budget)
    counters=dict(userdata_bytes=0,misc_bytes=0);fallback={'attempts':0}
    result=dict(state='preflight',boot_attempts=0,boot_started=False,installed=False,restored=False,
        restore_attempted=False,independent_restore_verified=False,misc_marker_written=False,
        partition_write_phase='none',physical_FPS_qualified=False,observer_group_clear=True)
    def report(row):
        with (EXEC/'progress.jsonl').open('a') as f:
            json.dump(row,f);f.write('\n');f.flush();os.fsync(f.fileno())
    def make_io():return BoundedIO(RecoveryIO(),counters,READ,WRITE,MARKER,misc_original)
    def recover():
        require(result['observer_group_clear'],'active observer group prevents recovery access')
        return legacy.recovery_for_rollback(make_io,approval,fallback)
    def capture_as(name,phase,header):
        profile=load(BASE/'capture-profile.json');profile.update(out=str((EXEC/name).relative_to(MAIN)),
            phase=phase,expected_header_sha256=header)
        return capture(profile)
    def restore_and_verify(io):
        require(not result['restore_attempted'],'one forward restore attempt only')
        result['restore_attempted']=True
        restored=RESTORE.apply(BASE/'slot-delta',BASE/'slot-capture',approval,io,HFS,Remote,
            EXEC/'restore-inputs',report)
        result['restored']=restored['state']=='restore-applied-and-readback-verified'
        if result['restored']:result['partition_write_phase']='original-files-restored'
        save(EXEC/'restore-result.json',restored)
        require(result['restored'],'restoration failed; original postboot preimages retained, no forward retry')
        if result['misc_marker_written'] and not result['boot_started']:
            legacy.marker_rollback(io,misc_original,READ,WRITE,MARKER)
            result['preboot_misc_marker_restored']=True
        recipe=load(EXEC/'restore-inputs/restore-plan.json')
        fresh=make_io()
        proof=independent.verify(fresh,BASE/'slot-delta',HFS,Remote,
            lambda:fresh.run(fresh.adb+['exec-out',READ]).stdout,
            recipe['expected_header_sha256'],recipe['alternate_sha256'])
        save(EXEC/'independent-restore.json',proof)
        result['independent_restore_verified']=True
        return proof
    try:
        before=capture_as('fresh-before','before-boot',plan['root_header_sha256'])
        legacy.static_compare(load(BASE/'expected-baseline.json'),before)
        io=make_io()
        require(io.run(io.adb+['exec-out',READ]).stdout==misc_original,'live misc preimage changed')
        installed=INSTALL.install(BASE/'slot-delta',BASE/'slot-capture',approval,io,HFS,Remote,report)
        result['installed']=installed['state']=='install-applied-and-HFSX-verified'
        if result['installed']:result['partition_write_phase']='0339-six-files-installed'
        save(EXEC/'install-result.json',installed)
        require(result['installed'],'install failed or rolled back; no boot')
        marker=set_recovery_marker(io,dict(misc_recovery_marker_approved=True,allow_rollback=True,
            misc_backup_sha256=plan['misc_before_sha256']),misc_original)
        result['misc_marker_written']=True;save(EXEC/'marker-result.json',marker)
        io.run(io.adb+['reboot','bootloader'])
        code=observe_once(plan,result,legacy)
        io=recover()
        after=capture_as('post-capture','after-boot',None)
        log_paths=legacy.LOG_PATHS
        for path in log_paths:
            old=(EXEC/'fresh-before'/before['files'][path]['output']).read_bytes()
            new=(EXEC/'post-capture'/after['files'][path]['output']).read_bytes()
            preserved=new.startswith(old)
            result.setdefault('other_log_prefix_preserved',{})[path]=preserved
            tail=EXEC/(before['files'][path]['output']+'.current')
            tail.write_bytes(new[len(old):] if preserved else new)
            if path==legacy.SPRINGBOARD_LOG:
                result['springboard_log_prefix_preserved']=preserved
                legacy.link_saved_log(tail,EXEC/'springboard-new.log')
        # No decoder executes until the writer and an independent fresh HFS/
        # misc readback have both succeeded. Header may change on tail reclaim.
        proof=restore_and_verify(io)
        final=capture_as('restored-capture','after-boot',proof['root_header_sha256'])
        legacy.static_compare(before,final)
        analyze(EXEC,plan,result,before,code)
    except (Exception,KeyboardInterrupt) as error:
        result.update(state='trial-incomplete-or-failed',error=repr(error))
        if result['installed'] and not result['restored'] and not result['restore_attempted']:
            try:restore_and_verify(recover())
            except (Exception,KeyboardInterrupt) as problem:result['fallback_restore_error']=repr(problem)
        # A failed install or marker helper has its own bounded preimage
        # rollback. Never attempt candidate restoration on a partial install.
    result.update(attempted_userdata_bytes=counters['userdata_bytes'],attempted_misc_bytes=counters['misc_bytes'],
        recovery_fallbacks=fallback['attempts'],finished=time.time())
    save(EXEC/'result.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['state']=='CR339-lossless-wait-execution-observed-root-restored' else 1


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(ap.parse_args().check_gate))
