#!/usr/bin/env python3
"""Host-only actual saved-log pipeline and mocked one-shot control-flow faults."""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io as textio
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import types
from unittest.mock import patch
from core342_scope import BASE,MAIN,WORK,PRIOR,PARENT,APPROVAL_FLAGS,expected_plan,load,sha
import core342_log as CORE


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


RUN=module('one_shot_pipeline340',WORK/'tools/run-core342-trial.py')
ANALYZE=module('saved_pipeline340',WORK/'tools/analyze-core342.py')


def save(path,value):
    with path.open('x') as f:json.dump(value,f,indent=2);f.write('\n')


def analysis_fixture(out,plan,checks):
    """Only timestamps/IDs are synthesized; never evidence from a0342 boot."""
    original=PRIOR/'execution';before=load(original/'fresh-before/result.json')
    text=(original/'backboardd.log.current').read_text()
    old=module('actual_old_c4_control340',WORK/'tools/analyze-c4-queue-log.py').analyze(text)
    ids=module('actual_old_q_control340',WORK/'tools/analyze-queue337.py').analyze(text)
    assert old['coverage_qualified'] and ids['coverage_qualified']
    keys={(r['object'],r['made_us']):r for r in ids['buffers']}
    converted=text.replace('GAUGUIN C4Q321:','GAUGUIN C4Q342:').replace('GAUGUIN Q337:','GAUGUIN Q342:')
    converted=re.sub(r'(GAUGUIN C4Q342: phase=4 object=0x[0-9a-f]+ start_us=\d+ end_us=\d+ value=)\d+',r'\g<1>0',converted)
    synthetic=[];detail=module('synthetic341_detail',WORK/'tests/test_core341_log.py');extra=module('synthetic342_detail',WORK/'tests/test_core342_log.py')
    for index,row in enumerate(sorted(old['buffers'],key=lambda r:(r['times_us'][2],keys[r['object'],r['made_us']]['ticket'])),1):
        ident=keys[row['object'],row['made_us']];t=row['times_us'];obj=row['object'];made=row['made_us']
        # Zero-duration model core jobs preserve the old independent frontend
        # timestamps without inventing real core execution measurements.
        tick=t[2]*1000
        fine={k:(0 if n==1 else [0]*n) for k,n in CORE.OLD.OLD.FIELDS}
        fine.update(draw_calls=1,draw_ok=1,render_calls=1,render_ok=1,draw_reuse=[1,0,0,0],
            draw_max_job=2*index-1,draw_max_start_ns=tick,draw_max_end_ns=tick,
            gpu_calls=1,gpu_ok=1,gpu_begin_ns=tick,gpu_end_ns=tick,submit_reuse=[1,0,0,0],
            io_calls=1,io_begin_ns=tick,io_end_ns=tick,bo_unique=1,bo_mode=1)
        suffix=''.join(' '+k+'='+(','.join(map(str,fine[k])) if n!=1 else str(fine[k])) for k,n in CORE.OLD.OLD.FIELDS)
        miss=index==len(old['buffers'])//2
        detail_values=detail.extra_values(tick=tick,job=2*index-1)
        if miss:
            detail_values.update(address_counts=[2,1,1],resident_counts=[1,1,0],
                program_counts=[1,1,1,0,1,0,1,0,0,0,0,0,0,0],
                resident_max=[2*index-1,tick,tick,0,0,0,0,0])
        suffix+=''.join(' '+k+'='+ (str(detail_values[k]) if k=='detail_flags' else ','.join(map(str,detail_values[k]))) for k,n in CORE.OLD.FIELDS)
        suffix+=extra.suffix(tick=tick,job=2*index-1,index=index,program_miss=miss)

        synthetic += [f'GAUGUIN CR342: object={obj} made_us={made} queue={ident["queue"]} ticket={ident["ticket"]} job={2*index} enq_ns={tick} start_ns={tick} end_ns={tick} busy_wait_ns=0 jobs=2 own_exec_ns=0 sum_queue_ns=0 max_queue_ns=0 state=3 failed=0 counts=0,0,1,0,0,0,1,0 exec_ns=0,0,0,0,0,0,0,0 wait_ns=0,0,0,0,0,0,0,0 max_exec_ns=0,0,0,0,0,0,0,0 max_class=2 max_job={2*index-1} max_enq_ns={tick} max_start_ns={tick} max_end_ns={tick} submit_mask=255 submit_outcome=0 submit_begin_ns={tick} submit_end_ns={tick} submit_ns=0,0,0,0,0,0,0,0 flags=0'+suffix,
            f'GAUGUIN N342: object={obj} made_us={made} tick_us={max(t[4],t[7])+10} state=4']
    converted+='\n'+'\n'.join(synthetic)+'\n'
    core=CORE.analyze(converted);assert core['coverage_qualified'],core['errors']
    proof=dict(state='independently-verified-six-original-files-misc-and-empty-journal',
        install_plan_sha256=plan['install_plan_sha256'],misc_original_4096_bytes_match=True,
        journal_empty=True,all_original_slot_bits_allocated=True,fixture_only=True,
        source='host-synthetic-wires-not-a-0342-device-observation')
    folder=out/'saved-analysis-fixture';folder.mkdir()
    kernel_rows=[]
    for r in core['rows']:
        tid,q,h,offset,words,fence=r['io_identity']
        kernel_rows.append(extra.kernel_row(70,r['io_begin_ns'],h,4*words,q,fence,r['bo_unique'],1,zero=True))
        if r['newbo_counts'][0]:
            for selector in (66,67,256):kernel_rows.append(extra.kernel_row(selector,r['newbo_max'][4],100,0 if selector==67 else 4096,zero=True))
    prior_kernel=(original/'kernel.log').read_text()
    prior_banner=load(PRIOR/'trial-plan.json')['kernel_banner']
    kernel,raw=extra.kernel_stream(kernel_rows,prior_kernel.replace(prior_banner,plan['kernel_banner']))
    (folder/'kernel.log').write_text(kernel);(folder/'kernel.log.bin').write_bytes(raw)
    os.link(original/'springboard-new.log',folder/'springboard-new.log')

    (folder/(before['files']['/private/var/log/backboardd.log']['output']+'.current')).write_text(converted)
    save(folder/'independent-restore.json',proof)
    result=dict(restored=True,independent_restore_verified=True,springboard_log_prefix_preserved=True,
        other_log_prefix_preserved={p:True for p in RUN.module('old_paths340',WORK/'tools/run-sb-cadence-trial.py').LOG_PATHS},
        fixture_only=True,source=proof['source'])
    ANALYZE.analyze_saved(folder,plan,result,before,0)
    assert result['state']=='CR342-lossless-wait-execution-observed-root-restored',result['state']
    assert result['legacy_observation_state']=='BC336-cache-reuse-observed-root-restored'
    assert result['collection_analysis']['coverage_qualified'] and not result['physical_FPS_qualified']
    assert 'core_status_drain' not in result['queue_analysis']['stage_us']
    save(folder/'model-result.json',result)
    checks.append('all-inherited-configuration-gates-and-new342-analysis-pipeline-synthetic-positive')
    bad=dict(result,independent_restore_verified=False)
    try:ANALYZE.analyze_saved(folder,plan,bad,before,0)
    except ValueError:pass
    else:raise AssertionError('analysis before independent restoration')
    checks.append('analysis-refuses-unverified-restoration-before-decoder-IO')
    sb=(original/'springboard-new.log').read_text()
    allocation=load(original.parent/'recovered-analysis/bo-allocation-analysis.json')
    collection=module('collection_for_faults340',WORK/'tools/collection342.py')
    cases={'prefix-loss':(kernel,converted,sb,False),
        'missing-core-row':(kernel,'\n'.join(l for l in converted.splitlines() if l!=synthetic[0]),sb,True),
        'kernel-limit':(kernel.replace('lost=0','lost=1',1),converted,sb,True),
        'wrong-SB-constructor':(kernel,converted,sb.replace('constructor=337','constructor=336'),True),
        'notice-limit':(kernel,converted+'GAUGUIN N342: limit=4096 coverage=incomplete\n',sb,True),
        'fine-IO-missing':(kernel,converted.replace('io_calls=1','io_calls=0'),sb,True),
        'warm-reuse-unobserved':(kernel,converted.replace('submit_reuse=1,0,0,0','submit_reuse=1,0,1,0'),sb,True),
        'CPU-accounting-missing':(kernel,converted.replace('cpu_counts=1,1,2','cpu_counts=0,0,0'),sb,True),
        'detail-clock-error':(kernel,converted.replace('detail_flags=0','detail_flags=2'),sb,True),
        'kernel-IO-stream-missing':('\n'.join(l for l in kernel.splitlines() if not l.startswith('SWEET IO342:')),converted,sb,True),
        'kernel-IO-byte-limit':(kernel.replace('byte_limited=0','byte_limited=1'),converted,sb,True),
        'kernel-IO-identity':(kernel.replace('tid=1234','tid=1235'),converted,sb,True),
        'kernel-program-map-missing':('\n'.join(l for l in kernel.splitlines() if 'selector=256 ' not in l),converted,sb,True)}
    for label,(k,b,s,prefix) in cases.items():
        parsed=CORE.analyze(b);c=collection.analyze(k,b,s,prefix,allocation,parsed['lifecycle'],parsed['identity'],parsed,ANALYZE.KERNEL.parse(k,raw),ANALYZE.KERNEL.join(ANALYZE.KERNEL.parse(k,raw),parsed,(220000000,270000000)))
        assert not c['coverage_qualified'],label
        verdict=ANALYZE.interpret(c,'BC336-cache-reuse-observed-root-restored',parsed,(220000000,270000000))
        assert verdict['state']=='CR342-interpretation-withheld' and 'full_window_metrics' not in verdict
        checks.append(label+'-withholds-interpretation')
    assert result['queue_backlog_analysis']['full_script_window']['count']>result['queue_backlog_analysis']['BO_capture_window']['count']
    assert result['queue_backlog_analysis']['full_script_window']['start_us']==result['collection_analysis']['script_window_us'][0]
    checks.append('full13stroke-window-distinct-from-kernel4s-BO-capture')
    tail=result['queue_backlog_analysis']['completion_tail']
    assert abs(sum(tail['component_sums_us'].values())-tail['CB_elapsed_sum_us'])<.001
    assert sum(tail['wait_category_sums_us'].values())==sum(tail['submit_phase_sums_us'].values())==0
    checks.append('per-CB-and-completion-tail-additive-path-with-separate-category-and-submit-partitions')
    # Independently reproduce the raw0340 baseline; never convert it into342 evidence.
    old_core=CORE.OLD.analyze((PARENT/'execution/backboardd.log.current').read_text())
    bounds=load(PARENT/'execution/collection-analysis.json')['script_window_us']
    matched=[r for r in old_core['rows'] if bounds[0]<=r['made_us']<bounds[1]]
    assert old_core['coverage_qualified'] and len(matched)==718
    assert CORE.stats([r['commit_done_us'] for r in matched])['p95']==57606
    checks.append('raw0341-fullscript718CB-p9557606us-reproduced')
    c=result['collection_analysis']
    assert ANALYZE.interpret(c,'MAP324-descriptor-fastpath-unqualified-root-restored',core,(220000000,270000000))['reason']=='legacy-configuration-unqualified'
    checks.append('legacy-configuration-rejection-cannot-be-overridden-by-lossless342-wires')
    return dict(complete_cb_count=core['complete_count'],synthetic_core_job_durations_are_zero=True,
        real0342_performance_evidence=False,original_kernel_fixture_scope_relabelled_and_extended=True,original_SB_bytes_unchanged=True)


def control_fixture(out,plan,label,checks):
    """Call the actual main; every device constructor and effect is mocked."""
    folder=out/('flow-'+label);folder.mkdir();execution=folder/'execution'
    (folder/'metadata-snapshot').mkdir();(folder/'metadata-snapshot/misc-original.bin').write_bytes(bytes(4096))
    save(folder/'approval.json',dict(fixture_only=True,source='CONTROL-FLOW-FIXTURE-NOT-USER-CONSENT'))
    save(folder/'trial-plan.json',dict(fixture_only=True));save(folder/'capture-profile.json',dict(files={}))
    events=[];legacy=RUN.module('control_paths340',WORK/'tools/run-sb-cadence-trial.py')
    prefix=b'before\n'
    files={p:dict(output='log-'+str(i),present=True,uid=0,gid=0,mode=0o100644,
                  bytes=len(prefix),sha256=hashlib.sha256(prefix).hexdigest(),fork={}) for i,p in enumerate(legacy.LOG_PATHS)}
    baseline=dict(files=files,directories={},root_header_sha256=plan['root_header_sha256'])
    save(folder/'expected-baseline.json',baseline)
    class DisabledDevice:
        adb=['DISABLED-HOST-FIXTURE']
        def write(self,offset,data):events.append('userdata-write')
        def run(self,argv,**kwargs):
            if argv[-1]=='bootloader':events.append('reboot-command-mocked')
            return subprocess.CompletedProcess(argv,0,stdout=bytes(4096),stderr=b'')
    suffix_capture = module('capture-suffix-fixture342',WORK/'tools/capture-core342-root.py')
    def capture(profile,*,save_files=True,save_paths=None,prefix_files=None):
        name=Path(profile['out']).name;events.append('capture-'+name)
        if (label=='post-capture-failure' and name=='post-capture') or (label=='final-capture-failure' and name=='restored-capture'):
            raise ValueError('model capture failure')
        target=MAIN/profile['out'];target.mkdir();r=copy.deepcopy(baseline)
        if prefix_files is not None:r['verified_suffixes']={}
        for path,row in r['files'].items():
            if save_files and (save_paths is None or path in save_paths):
                raw=prefix if name=='fresh-before' else prefix+b'model\n'
                if name=='post-capture' and p_mismatch(path):raw=b'different\nmodel\n'
                if prefix_files is None:
                    (target/row['output']).write_bytes(raw)
                else:
                    r['verified_suffixes'][path]=suffix_capture.BASE.save_verified_suffix(
                        target/row['output'],raw,prefix_files[path])
                    row['bytes']=len(raw)
        return r
    def p_mismatch(path):
        return label in ('hash-prefix-mismatch','suffix-prefix-mismatch') and path==legacy.SPRINGBOARD_LOG
    def install(*args):
        events.append('install');args[3].write(4096,bytes(4096))
        return dict(state='install-failed-rollback-verified' if label=='install-rollback' else 'install-applied-and-HFSX-verified')
    def marker(device,approval,backup):
        events.append('marker');device.run(device.adb+['exec-in','MODEL-WRITE-MISC'],data=b'boot-recovery');return dict(state='mock-marker')
    def marker_rollback(device,backup,*unused):
        events.append('marker-rollback');device.run(device.adb+['exec-in','MODEL-WRITE-MISC'],data=backup[:13])
    def observe(unused,result,old,observer_output):
        assert observer_output==execution
        events.append('observe');result.update(boot_attempts=1,boot_started=True)
        if label=='observer-before-launch-failure':result['boot_started']=False;raise ValueError('model boot rejection')
        if label=='observer-owner-alive':result['observer_group_clear']=False;raise ValueError('model live owner')
        return 0
    def restore(plan_dir,capture_dir,approval,device,HFS,Remote,target,report):
        events.append('restore')
        if label=='restore-preparation-refusal':raise ValueError('model unsupported journal')
        device.write(8192,bytes(4096));target.mkdir()
        save(target/'restore-plan.json',dict(expected_header_sha256='fixture',alternate_sha256='fixture'))
        return dict(state='restore-failed-rollback-verified' if label=='restore-rollback' else 'restore-applied-and-readback-verified')
    def verify(*args):
        events.append('independent-readback')
        if label=='independent-failure':raise ValueError('model independent readback failure')
        return dict(root_header_sha256='fixture',state='independently-verified-six-original-files-misc-and-empty-journal')
    def analyze(exec_dir,p,result,before,code):
        events.append('analysis');assert result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed']
        if p.get('hash_only_static_files'):
            for path,row in files.items():
                name=row['output']
                assert not (exec_dir/'fresh-before'/name).exists() and not (exec_dir/'restored-capture'/name).exists()
                tail=exec_dir/(name+'.current')
                if p_mismatch(path):
                    assert not result['other_log_prefix_preserved'][path]
                    assert tail.samefile(exec_dir/'post-capture'/name)
                else:
                    assert result['other_log_prefix_preserved'][path] and tail.read_bytes()==b'model\n'
        result['state']='CR342-lossless-wait-execution-observed-root-restored'
    old_helpers=types.SimpleNamespace(LOG_PATHS=legacy.LOG_PATHS,SPRINGBOARD_LOG=legacy.SPRINGBOARD_LOG,
        static_compare=legacy.static_compare,link_saved_log=legacy.link_saved_log,
        recovery_for_rollback=lambda make,approval,state:make(),marker_rollback=marker_rollback)
    modules={'unchanged_boot_recovery_helpers340':old_helpers,'capture342':types.SimpleNamespace(capture=capture),
        'independent342':types.SimpleNamespace(verify=verify),'analyze340':types.SimpleNamespace(analyze_saved=analyze)}
    imports={'write_root_delta175v2':types.SimpleNamespace(RecoveryIO=DisabledDevice),
        'local_hfs175v3':types.SimpleNamespace(HFS=None),'metal_ca_c5_delta':types.SimpleNamespace(Remote=None),
        'recovery_marker':types.SimpleNamespace(READ='MODEL-READ-MISC',WRITE='MODEL-WRITE-MISC',MARKER=b'boot-recovery',set_recovery_marker=marker)}
    real_save=RUN.save;failed_receipt=False
    def receipt(path,value):
        nonlocal failed_receipt
        if label=='restore-receipt-failure' and path.name=='restore-result.json' and not failed_receipt:
            failed_receipt=True;raise OSError('model receipt storage failure')
        return real_save(path,value)
    with patch.object(RUN,'BASE',folder),patch.object(RUN,'EXEC',execution),\
        patch.object(RUN,'authorization',return_value=(plan,dict(trial_plan_sha256='fixture'),dict(fixture_only=True),dict(admitted=True))),\
        patch.object(RUN,'module',side_effect=lambda name,path:modules[name]),\
        patch.object(RUN.INSTALL,'install',side_effect=install),patch.object(RUN.RESTORE,'apply',side_effect=restore),\
        patch.object(RUN,'observe_once',side_effect=observe),patch.object(RUN,'save',side_effect=receipt),\
        patch.dict(sys.modules,imports),contextlib.redirect_stdout(textio.StringIO()):
        code=RUN.main()
    result=load(execution/'result.json')
    assert events.count('restore')<=1 and events.count('observe')<=1
    assert result['attempted_userdata_bytes']<=30961664 and result['attempted_misc_bytes']<=26
    if label in ('success','hash-prefix-mismatch','suffix-success'):
        assert code==0 and events.index('restore')<events.index('independent-readback')<events.index('analysis')
    else:assert code!=0 and 'analysis' not in events
    if label=='suffix-prefix-mismatch':
        assert result['state'].endswith('log-prefix-mismatch-root-restored')
        assert result['restored'] and result['independent_restore_verified']
        assert not (execution/'springboard-new.log').exists()
    if label=='suffix-success':
        for path,row in files.items():
            name=row['output']
            assert (execution/(name+'.current')).samefile(execution/'post-capture'/name)
    if label=='post-capture-failure':assert result['restored'] and result['independent_restore_verified']
    if label in ('restore-rollback','restore-preparation-refusal'):
        assert result['restore_attempted'] and not result['restored'] and 'independent-readback' not in events
    if label in ('independent-failure','restore-receipt-failure'):assert result['restored'] and not result['independent_restore_verified']
    if label=='observer-before-launch-failure':assert result['restored'] and events.count('marker-rollback')==1 and result['attempted_misc_bytes']==26
    if label=='observer-owner-alive':assert 'restore' not in events and result['boot_attempts']==1
    if label=='install-rollback':assert 'restore' not in events and result['boot_attempts']==0
    save(folder/'fixture-control-proof.json',dict(fixture_only=True,events=events,all_device_effects_mocked=True,native_device_commands=0))
    checks.append('actual-executor-control-'+label)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists();out.mkdir()
    assert not (BASE/'approval.json').exists() and not (BASE/'execution').exists()
    checks=[]
    with patch.object(RUN.subprocess,'run',side_effect=AssertionError('unexpected command before consent')):
        try:RUN.authorization()
        except ValueError as error:assert 'approval absent' in str(error)
        else:raise AssertionError('missing consent accepted')
    checks.append('missing-approval-refused-before-any-subprocess-or-execution-claim')
    plan=expected_plan();old_approval=load(PRIOR/'approval.json')
    ready=dict(install_plan_sha256=plan['install_plan_sha256'],trial_plan_sha256='fixture-only')
    for label,approval in [('consumed337',old_approval),('consumed338',load(MAIN/'research/tmp/gauguin-core-async-worktree-20261117/research/tmp/core-async-338/approval.json')),('consumed339',load(MAIN/'research/tmp/gauguin-core-prof-worktree-20261117/research/tmp/core-prof-339/approval.json')),('consumed340',load(MAIN/'research/tmp/gauguin-draw-submit-worktree-20261117/research/tmp/draw-submit-340/approval.json')),('consumed341',load(PARENT/'approval.json')),('fixture',dict(fixture_only=True))]:
        try:RUN.check_consent(approval,ready,plan)
        except ValueError:pass
        else:raise AssertionError('accepted '+label)
        checks.append(label+'-consent-refused')
    class Raw:
        adb=['DISABLED'];calls=0
        def write(self,offset,data):self.calls+=1;raise OSError('partial requested write')
        def run(self,*args,**kwargs):self.calls+=1;return None
    counters=dict(userdata_bytes=30961664-4096,misc_bytes=0);raw=Raw()
    bounded=RUN.BoundedIO(raw,counters,'READ','WRITE',b'boot-recovery',bytes(4096))
    try:bounded.write(4096,bytes(4096))
    except OSError:pass
    assert counters['userdata_bytes']==30961664 and raw.calls==1
    try:bounded.write(4096,bytes(4096))
    except ValueError:pass
    else:raise AssertionError('write cap exceeded')
    assert raw.calls==1
    bounded.run(raw.adb+['exec-in','WRITE'],data=b'boot-recovery')
    replacement=RUN.BoundedIO(raw,counters,'READ','WRITE',b'boot-recovery',bytes(4096))
    replacement.run(raw.adb+['exec-in','WRITE'],data=bytes(13))
    for argv,kwargs in [(raw.adb+['exec-in','WRITE'],dict(data=bytes(13))),(raw.adb+['reboot','system'],{})]:
        try:replacement.run(argv,**kwargs)
        except ValueError:pass
        else:raise AssertionError('misc cap/direct command guard')
    assert raw.calls==3 and counters['misc_bytes']==26
    checks.append('attempted-write-caps-include-partials-and-survive-IO-replacement')
    for label in ('success','post-capture-failure','restore-preparation-refusal','restore-rollback',
        'independent-failure','final-capture-failure','observer-before-launch-failure','observer-owner-alive',
        'install-rollback','restore-receipt-failure'):
        control_fixture(out,plan,label,checks)
    analysis=analysis_fixture(out,plan,checks)
    paths=[Path(__file__),WORK/'tools/run-core342-trial.py',WORK/'tools/analyze-core342.py',
        WORK/'tools/core342_scope.py',WORK/'tools/core342_log.py',WORK/'tools/collection342.py',
        WORK/'tools/kernel342_log.py',WORK/'tools/phase342_log.py',WORK/'tools/core341_log.py',
        WORK/'tools/capture-core342-root.py',WORK/'tests/test_core342_log.py',BASE/'slot-delta/install-plan.json',PRIOR/'execution/result.json',
        PARENT/'execution/backboardd.log.current',PARENT/'execution/collection-analysis.json',PARENT/'execution/result.json']
    result=dict(state='0342-executor-analysis-collection-order-host-models-passed',checks=checks,
        input_pins={str(p):sha(p) for p in paths},saved_analysis_fixture=analysis,
        fixture_authorization_never_native=True,device_commands=0,device_writes=0,boot_attempts=0,
        physical_FPS_qualified=False)
    save(out/'result.json',result);print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__=='__main__':main()
