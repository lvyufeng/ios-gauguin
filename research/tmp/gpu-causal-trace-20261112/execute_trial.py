"""One separately approved causal UI trace boot and C4 restoration."""
from pathlib import Path
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time

W = Path(__file__).resolve().parent
R = W.parents[2]
MAIN = Path('/Users/baai/Project/ios-gauguin')
E = W / 'execution'
sys.path[:0] = [str(W),str(R/'tools'),str(MAIN/'tools'),str(MAIN/'research/tmp/dsh-0175'),
                str(MAIN/'research/tmp/metal-hardware-repeat2-20261112')]
import ui_trace_log
from metal_ca_c5_delta import approval_gate, install, prepare_restore, restore, Remote, TARGET
from local_hfs175v3 import HFS
from write_root_delta175v2 import RecoveryIO
from recovery_marker import READ, WRITE, MARKER, set_recovery_marker
from capture_owned import capture

LOGS = ['/private/var/tmp/gauguin-gles180.log',
        '/private/var/tmp/gauguin-gles180.stderr.log',
        '/private/var/log/backboardd.log']

def load(path): return json.loads(path.read_text())
def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
def need(ok,message):
    if not ok: raise ValueError(message)
def save(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')

def compare(a,b,allow_logs=False):
    need(set(a['files'])==set(b['files']) and a['directories']==b['directories'],
         'capture file/directory set changed')
    for path,old in a['files'].items():
        new=b['files'][path]
        need(new['present'] and all(new[k]==old[k] for k in ('uid','gid','mode')),
             'file metadata changed: '+path)
        if allow_logs and path in LOGS: continue
        need(all(new[k]==old[k] for k in ('bytes','sha256','fork')),
             'static file changed: '+path)

def capture_as(name,phase,header):
    cfg=load(W/'current-capture-profile.json')
    cfg['out']=str((E/name).relative_to(MAIN))
    cfg['phase']=phase
    cfg['expected_header_sha256']=header
    return capture(cfg)

def validate_preinstall_catalog(io,install_plan):
    remote=Remote(io);h=HFS(stream=remote,size=17179869184)
    try:
        row=h.paths[TARGET]
        need(row['id']==install_plan['file_cnid'] and row['type']==2 and
             row['data']['logical']==install_plan['old_file_bytes'] and
             row['data']['extents']==[[install_plan['data_start_block'],105]],
             'live preinstall file identity/fork changed')
        spans=list(h.spans(h.catalog,row['catalog_bsd_offset']+56,8))
        need(len(spans)==1 and spans[0][1]==8,'live catalog length field split')
        block,offset=divmod(spans[0][0],4096)
        need((block,offset)==(install_plan['catalog_start_block'],
                              install_plan['catalog_field_offset']),
             'live catalog leaf moved; no stale write')
    finally:h.close()

def validate_current(stdout,stderr,backboard,kernel,plan,trace):
    private=plan['core_runtime_path']
    need('refused: owned desktop core path' not in backboard,
         'desktop rejected a wrong core path')
    need(backboard.count('owned desktop core loaded from '+private+'\n')>=1,
         'desktop did not attest the private owned core path')
    need('owned frontend records on the core FIFO and admits every commit on one frontend FIFO'
         in backboard,'new frontend admission path did not run')
    fps=re.findall(r'fps: [0-9.]+ frames/s over [0-9.]+ s \((\d+) presented, (\d+) command buffers\)',backboard)
    need(fps and sum(int(row[1]) for row in fps)>0,
         'new desktop frontend has no completed command-buffer window')
    need('GAUGUIN METAL245 RESULT PASS' in stdout and
         'GAUGUIN METAL223 RESULT PASS' in stdout,
         'retained root bootstrap did not finish')
    closes=[tuple(map(int,row)) for row in re.findall(
        r'SWEET METAL245: root close ready=(\d+) jobs=(\d+) fence=(\d+) epoch=(\d+) clean=(\d+)',kernel)]
    need(closes and closes[0][0]==1 and closes[0][1]==8 and closes[0][2]>0 and closes[0][4]==1,
         'retained root owner did not close cleanly')
    service=[tuple(map(int,row)) for row in re.findall(
        r'SWEET GPU SERVICE: final renewals=(\d+) submitted=(\d+) completed=(\d+) shadow=(\d+); quarantined, no further refresh',kernel)]
    need(len(service)==1 and service[0][1]==service[0][2] and service[0][1]>8,
         'GPU service did not complete desktop-period work')
    need('SWEET FB CLOCK: enabled software_us=16667' in kernel and
         'SWEET FB STATS: enabled; CPU timing only, panel unqualified' in kernel,
         '60 Hz software clock or CPU copy profiling was not active')
    perf=[tuple(map(int,row)) for row in re.findall(
        r'SWEET GPU PERF: submits=(\d+) submit_ns=(\d+) submit_checks=(\d+) submit_check_ns=(\d+) pending=(\d+)',kernel)]
    need(len(perf)==1 and perf[0][0]==service[0][1] and perf[0][4]==0,
         'new native submit/check profile missing or incomplete')
    copies=[tuple(map(int,row)) for row in re.findall(
        r'SWEET FB STATS: attempts=(\d+) copied=(\d+) zero=(\d+) invalid=(\d+) bytes=(\d+) layers=(\d+) guards=(\d+) refused=(\d+); CPU, not scanout',kernel)]
    need(copies and copies[-1][0]>0 and copies[-1][1]>0 and copies[-1][4]>0,
         'no successful CPU copy statistics in current kernel log')
    notify=re.findall(r'SWEET FB NOTIFY: client=(\d+) port=(\d+) registrations=(\d+) callbacks=([0-9a-f]+) sent=(\d+) failed=(\d+) type3=(\d+)/(\d+) type5=(\d+)/(\d+)',kernel)
    need(notify,'new framebuffer notification counters absent')
    touch=re.findall(r'SWEET HID TRACE: changed=(\d+) edge=(\d+) position=(\d+) max_callback_ticks=(\d+) last_callback_ticks=(\d+)',kernel)
    timeline=re.findall(r'timeline: made [0-9.]+ committed [0-9.]+ done [0-9.]+ gpu [0-9.]+',backboard)
    metal_touch_timeline=re.findall(r'tl: M made [0-9.]+ committed [0-9.]+ done [0-9.]+ gpu [0-9.]+',backboard)
    need(trace['header']['count']>0 and trace['queue_links'],
         'selected gesture has no complete HID queue trace')
    need(metal_touch_timeline, 'C4 touch_lat command-buffer clock missing')
    return dict(state='owned-C4-causal-ui-diagnostic-observed',
                private_core_path_attested=True,root_close=closes[0],
                service=dict(zip(('renewals','submitted','completed','shadow'),service[0])),
                native_submit_profile=dict(zip(('submits','submit_ns','full_health_checks',
                    'overlap_check_ns','pending'),perf[0])),
                latest_copy_prefix=dict(zip(('attempts','copied','zero','invalid','bytes',
                    'layers','guards','refused'),copies[-1])),
                physical_contact_transitions=len(re.findall(r'SWEET NVT: observed contact mask=[01]',kernel)),
                fps_windows=len(fps),command_buffers_in_fps_windows=sum(int(row[1]) for row in fps),
                presented_drawable_events=sum(int(row[0]) for row in fps),
                notification_summary_records=len(notify),
                notification_port_registrations=len(re.findall(r'SWEET FB NOTIFY: .* port registration type=',kernel)),
                hid_changed_log_records=len(touch),
                last_hid_changed=int(touch[-1][0]) if touch else 0,
                metal_timeline_records=len(timeline),
                metal_touch_timeline_records=len(metal_touch_timeline),
                ui_trace_events=trace['header']['count'],
                ui_trace_lost=trace['header']['lost'],
                ui_trace_reason=trace['header']['reason'],
                hid_queue_links=len(trace['queue_links']),
                hid_queue_enqueued=sum(row['enqueued'] for row in trace['queue_links']),
                desktop_pixels_qualified=False,physical_FPS_qualified=False,
                high_refresh_qualified=False)

def restore_preboot_marker(io,before):
    actual=io.run(io.adb+['exec-out',READ]).stdout
    need(actual==MARKER+before[len(MARKER):],
         'misc changed since marker write; no stale marker rollback')
    io.run(io.adb+['exec-in',WRITE],data=before[:len(MARKER)])
    need(io.run(io.adb+['exec-out',READ]).stdout==before,
         'preboot marker restoration readback failed')
    return dict(state='preboot-misc-marker-restored',bytes=len(MARKER))

def recovery_for_rollback(consent,state):
    try:
        return RecoveryIO()
    except Exception as original:
        need(consent.get('allow_recovery_fallback') is True,
             'recovery fallback was not approved')
        found=subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=5)
        rows=[line.split() for line in found.stdout.splitlines() if line.strip()]
        if not (len(rows)==1 and len(rows[0])>=2 and rows[0][1]=='fastboot'):
            raise RuntimeError('neither recovery nor one fastboot device available') from original
        serial=rows[0][0]
        product=subprocess.run(['fastboot','-s',serial,'getvar','product'],
                               capture_output=True,text=True,timeout=5)
        need(product.returncode==0 and 'product: gauguinpro' in product.stdout+product.stderr,
             'rollback fastboot product differs')
        need(state['attempts']==0,'recovery fallback already used; no retry')
        state['attempts']+=1
        reboot=subprocess.run(['fastboot','-s',serial,'reboot','recovery'],
                              capture_output=True,text=True,timeout=10)
        need(reboot.returncode==0,'fastboot recovery fallback failed')
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            try: return RecoveryIO()
            except Exception: time.sleep(2)
        raise RuntimeError('recovery did not return after bounded fallback')

def main():
    plan_path=W/'trial-plan.json'
    ready_path=W/'ready.json'
    approval_path=W/'approval.json'
    plan=load(plan_path)
    ready=load(ready_path)
    need(ready['state']=='ready-causal-ui-one-shot' and
         ready['plan_sha256']==sha(plan_path), 'trial plan is not the reviewed version')
    need(approval_path.exists(), 'no individual approval; zero device IO')
    consent=load(approval_path)
    approval_gate(consent,ready['install_plan_sha256'])
    need(consent.get('fixture_only') is not True and
         consent.get('trial_plan_sha256')==ready['plan_sha256'] and
         consent.get('image_sha256')==plan['image_sha256'] and
         consent.get('source')=='actual-user-causal-ui-trial-reply' and
         consent.get('allow_recovery_fallback') is True and
         isinstance(consent.get('user_answer'),str) and consent['user_answer'].strip() and
         consent.get('user_answer_sha256')==hashlib.sha256(consent['user_answer'].encode()).hexdigest() and
         isinstance(consent.get('question_item_id'),str) and consent['question_item_id'],
         'individual user reply is not bound to this trial')
    need(plan['state']=='prepared-causal-ui-C4-desktop-one-shot' and
         plan['install_plan_sha256']==ready['install_plan_sha256'] and
         plan['temporary_boots']==1 and plan['boot_retries']==0 and
         plan['install_bytes']==434176 and plan['restore_bytes']==434176 and
         plan['misc_write_bytes']==13 and
         plan['postboot_restore_attempts']==2 and
         plan['failed_restore_retry_limit']==1 and
         plan['maximum_userdata_write_bytes']==2170880 and
         plan['retry_only_after_verified_rollback'] is True,
         'unexpected trial scope')
    for path,digest in ready['input_pins'].items():
        need(sha(path)==digest,'reviewed input changed: '+path)
    need(not E.exists(), 'one-shot execution has already been claimed')
    admitted=load(W/'storage-trial-admission.json')
    need(admitted['admitted'] is True and admitted['planned_batch_bytes']==1073741824,
         'reviewed trial storage reserve differs')
    current_budget=subprocess.run([sys.executable,str(MAIN/'tools/storage-budget.py'),
                                   '--planned-bytes','1073741824'],
                                  capture_output=True,text=True,timeout=120)
    need(current_budget.returncode==0 and json.loads(current_budget.stdout)['admitted'] is True,
         'fresh trial storage reserve no longer admitted')
    E.mkdir(exist_ok=False)
    claim=dict(pid=os.getpid(),started=time.time(),trial_plan_sha256=ready['plan_sha256'],
               install_plan_sha256=ready['install_plan_sha256'],approval_sha256=sha(approval_path))
    save(E/'claim.json',claim)
    save(E/'storage-preflight.json',json.loads(current_budget.stdout))
    result=dict(state='preflight',boot_attempts=0,partition_write_phase='none')
    def report(row):
        with (E/'progress.jsonl').open('a') as stream:
            json.dump(row,stream)
            stream.write('\n');stream.flush();os.fsync(stream.fileno())
    installed=marker_written=boot_started=restored=restore_attempted=False
    recovery_fallback_state=dict(attempts=0)
    before_misc=None
    install_plan=load(W/'device-candidate/install-plan.json')
    candidate=W/'device-candidate'
    try:
        baseline=load(W/'current-capture/result.json')
        fresh=capture_as('fresh-before','before-boot',plan['root_before_sha256'])
        compare(baseline,fresh)
        io=RecoveryIO()
        before_misc=(candidate/'misc-before.bin').read_bytes()
        need(io.run(io.adb+['exec-out',READ]).stdout==before_misc and
             sha(candidate/'misc-before.bin')==plan['misc_before_sha256'],
             'misc preimage changed')
        validate_preinstall_catalog(io,install_plan)
        installed_receipt=install(install_plan,ready['install_plan_sha256'],candidate,
                                  consent,io,report)
        if installed_receipt['state']=='applied-and-readback-verified':
            installed=True
            result['partition_write_phase']='installed'
        else:
            result['partition_write_phase']=installed_receipt['state']
        save(E/'install-result.json',installed_receipt)
        need(installed_receipt['state']=='applied-and-readback-verified',
             'installation failed or rolled back')
        active=capture_as('installed-capture','before-boot',plan['root_before_sha256'])
        expected=load(W/'candidate-capture-expectations.json')
        compare(expected,active)
        marker=set_recovery_marker(io,dict(misc_recovery_marker_approved=True,
                                          allow_rollback=True,
                                          misc_backup_sha256=plan['misc_before_sha256']),
                                   before_misc)
        marker_written=True
        save(E/'marker-result.json',marker)
        io.run(io.adb+['reboot','bootloader'])
        deadline=time.monotonic()+45
        serial=None
        while time.monotonic()<deadline:
            output=subprocess.run(['fastboot','devices'],capture_output=True,text=True,timeout=5)
            devices=[line.split() for line in output.stdout.splitlines() if line.strip()]
            if devices:
                need(len(devices)==1 and len(devices[0])>=2 and devices[0][1]=='fastboot',
                     'ambiguous fastboot devices')
                serial=devices[0][0]
                break
            time.sleep(1)
        need(serial is not None,'fastboot did not become ready; no retry')
        product=subprocess.run(['fastboot','-s',serial,'getvar','product'],
                               capture_output=True,text=True,timeout=5)
        need(product.returncode==0 and 'product: gauguinpro' in product.stdout+product.stderr,
             'wrong fastboot product')
        with (E/'observer.log').open('x') as log:
            child=subprocess.Popen(['bash',plan['observer_helper'],plan['image'],
                                    str(E/'kernel.log'),str(plan['observer_seconds'])],
                                   stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            boot_started=True
            result['boot_attempts']=1
            save(E/'observer-process.json',dict(pid=child.pid,pgid=child.pid,
                                                image_sha256=plan['image_sha256'],boot_attempts=1))
            try: code=child.wait(timeout=plan['observer_seconds']+80)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGTERM)
                child.wait(timeout=10)
                raise RuntimeError('observer timed out; no boot retry')
        result['observer_exit']=code
        if code==5:
            boot_started=False
        need(code!=5,'fastboot boot was refused before temporary launch')
        ps=subprocess.run(['ps','-axo','pid=,pgid=,comm='],capture_output=True,text=True,check=True)
        need(not [line for line in ps.stdout.splitlines()
                  if len(line.split(None,2))==3 and line.split(None,2)[1]==str(child.pid)],
             'observer process group remains live')
        after=capture_as('post-capture','after-boot',None)
        compare(active,after,allow_logs=True)
        tails={}
        for path in LOGS:
            earlier=(E/'installed-capture'/active['files'][path]['output']).read_bytes()
            later=(E/'post-capture'/after['files'][path]['output']).read_bytes()
            need(later.startswith(earlier),'old log prefix changed: '+path)
            tail=later[len(earlier):]
            tails[path]=tail.decode(errors='replace')
            (E/(active['files'][path]['output']+'.current')).write_bytes(tail)
        io=RecoveryIO()
        dynamic=prepare_restore(install_plan,ready['install_plan_sha256'],candidate,
                                consent,io,E/'restore-inputs',HFS)
        restored_receipt=restore(install_plan,ready['install_plan_sha256'],dynamic,
                                 E/'restore-inputs',candidate,consent,io,report)
        restore_attempted=True
        save(E/'restore-result.json',restored_receipt)
        if restored_receipt['state']=='write-failed-rollback-verified':
            io=recovery_for_rollback(consent,recovery_fallback_state)
            retry_dynamic=prepare_restore(install_plan,ready['install_plan_sha256'],candidate,
                                          consent,io,E/'retry-restore-inputs',HFS)
            restored_receipt=restore(install_plan,ready['install_plan_sha256'],retry_dynamic,
                                     E/'retry-restore-inputs',candidate,consent,io,report)
            save(E/'retry-restore-result.json',restored_receipt)
        if restored_receipt['state']=='applied-and-readback-verified':
            restored=True
            result['partition_write_phase']='desktop-restored'
        else:
            result['partition_write_phase']=restored_receipt['state']
        need(restored_receipt['state']=='applied-and-readback-verified',
             'postboot restoration failed or rolled back')
        final=capture_as('restored-capture','after-boot',after['root_header_sha256'])
        compare(baseline,final,allow_logs=True)
        for path in LOGS:
            need(final['files'][path]['sha256']==after['files'][path]['sha256'],
                 'log changed while restoring desktop bundle')
        need(code==0 and (E/'kernel.log').is_file(),
             'observer did not qualify this kernel boot')
        kernel=(E/'kernel.log').read_text(errors='replace')
        trace=ui_trace_log.parse(kernel)
        save(E/'ui-trace.json',trace)
        validation=validate_current(tails[LOGS[0]],tails[LOGS[1]],tails[LOGS[2]],
                                    kernel,plan,trace)
        save(E/'validation.json',validation)
        result.update(state='causal-ui-diagnostic-observed-launch-restored',validation=validation)
    except (Exception,KeyboardInterrupt) as error:
        result.update(state='trial-incomplete-or-failed',error=repr(error))
        if installed and not restored and not restore_attempted:
            try:
                io=recovery_for_rollback(consent,recovery_fallback_state)
                restore_attempted=True
                dynamic=prepare_restore(install_plan,ready['install_plan_sha256'],candidate,
                                        consent,io,E/'fallback-restore-inputs',HFS)
                fallback=restore(install_plan,ready['install_plan_sha256'],dynamic,
                                 E/'fallback-restore-inputs',candidate,consent,io,report)
                save(E/'fallback-restore-result.json',fallback)
                restored=fallback['state']=='applied-and-readback-verified'
                if restored: result['partition_write_phase']='desktop-restored-after-failure'
            except (Exception,KeyboardInterrupt) as problem:
                result['fallback_restore_error']=repr(problem)
        if marker_written and not boot_started and before_misc is not None:
            try:
                io=recovery_for_rollback(consent,recovery_fallback_state)
                result['preboot_marker_restore']=restore_preboot_marker(io,before_misc)
            except (Exception,KeyboardInterrupt) as problem:
                result['preboot_marker_restore_error']=repr(problem)
    result.update(installed=installed,restored=restored,
                  restore_attempted=restore_attempted,
                  misc_marker_written=marker_written,
                  boot_started=boot_started,
                  recovery_fallbacks=recovery_fallback_state['attempts'],
                  finished=time.time())
    save(E/'result.json',result)
    print(json.dumps(result,indent=2),flush=True)
    return 0 if result['state']=='causal-ui-diagnostic-observed-launch-restored' else 1

if __name__=='__main__': raise SystemExit(main())
