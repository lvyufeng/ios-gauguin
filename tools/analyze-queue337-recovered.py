#!/usr/bin/env python3
"""Run the frozen analysis tail after separately verified supplemental restore.

No device entry point. Original trial result/captures are immutable inputs;
observations are saved separately with the original failure and recovery pins.
"""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path

WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/queue-loss-337'
ORIGINAL=BASE/'execution'
RESCUE=BASE/'trim-rescue'
OUT=BASE/'recovered-analysis'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load(path):return json.loads(path.read_text())


def main():
    proof=load(RESCUE/'prelaunch-consent-proof.json')
    assert sha(ORIGINAL/'result.json')==proof['original_frozen_result_sha256']
    terminal=load(ORIGINAL/'result.json')
    assert terminal['state']=='trial-incomplete-or-failed' and not terminal['restored']
    assert terminal['boot_attempts']==1 and terminal['observer_exit']==0
    restored=load(RESCUE/'execution/result.json')
    assert restored['state']=='0337-six-files-and-original-C4-allocation-restored'
    assert restored['forward_bytes']==10313728 and restored['rollback_bytes']==0
    independent=load(RESCUE/'independent-six-file-restore.json')
    metadata=load(RESCUE/'independent-metadata-restore.json')
    assert independent['state']=='independently-verified-six-original-files-and-misc'
    assert metadata['state']=='independently-verified-0337-supplemental-metadata-restoration'
    assert independent['root_header_sha256']==metadata['root_header_sha256']
    assert metadata['journal_empty'] and metadata['C4_original_four_tail_blocks_allocated']
    assert metadata['original_trial_result_sha256']==sha(ORIGINAL/'result.json')
    before=load(ORIGINAL/'fresh-before/result.json')
    after=load(ORIGINAL/'post-capture/result.json')
    assert terminal['springboard_log_prefix_preserved']
    assert all(terminal['other_log_prefix_preserved'].values())
    aliases={'kernel.log':ORIGINAL/'kernel.log'}
    log_paths=('/private/var/tmp/gauguin-gles180.log','/private/var/tmp/gauguin-gles180.stderr.log',
               '/private/var/log/backboardd.log','/private/var/log/springboard.log')
    prefix_checks={}
    for path in log_paths:
        old=ORIGINAL/'fresh-before'/before['files'][path]['output']
        new=ORIGINAL/'post-capture'/after['files'][path]['output']
        a,b=old.read_bytes(),new.read_bytes()
        assert b.startswith(a),path
        tail=ORIGINAL/(before['files'][path]['output']+'.current')
        assert tail.read_bytes()==b[len(a):],path
        aliases[tail.name]=tail
        prefix_checks[path]=dict(before_sha256=sha(old),after_sha256=sha(new),tail_sha256=sha(tail),prefix_preserved=True)
    aliases['springboard-new.log']=ORIGINAL/'springboard-new.log'
    source=WORK/'tools/run-sb-cadence-trial.py';ready=load(BASE/'ready.json')
    # Same exact code and all frozen dependencies as the consumed trial.
    for p,digest in ready['input_pins'].items():assert sha(Path(p))==digest,p
    tree=ast.parse(source.read_text())
    main_function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main')
    trial=next(n for n in main_function.body if isinstance(n,ast.Try))
    first=next(i for i,n in enumerate(trial.body)
               if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and
               'observer failed or kernel log absent' in ast.unparse(n))
    tail=trial.body[first:]
    assert 'strict cadence analysis rejected' in ast.unparse(tail[-1])
    assert all(not isinstance(n,ast.Return) for n in tail)
    forbidden={'capture_as','recovery_for_rollback','set_recovery_marker','marker_rollback','static_compare',
               'RecoveryIO','HFS','Remote','main','fastboot_identity','authorization'}
    calls={n.func.id for root in tail for n in ast.walk(root)
           if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)}
    assert not calls & forbidden
    assert not any(isinstance(n,ast.Name) and n.id in ('subprocess','os','signal','io','child')
                   for root in tail for n in ast.walk(root))
    spec=importlib.util.spec_from_file_location('frozen_recovered337',source)
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    namespace=dict(runner.__dict__)
    for name,leaf in [('rate_log','analyze-sb-rate-log.py'),('ui_log','ui_trace_log.py'),
                      ('joint_log','analyze-sb-cadence.py'),('stack_log','analyze-sb-stack-log.py'),
                      ('process_log','analyze-process-samples328.py')]:
        namespace[name]=runner.module('recovered_'+name,WORK/'tools'/leaf)
    result=dict(state='post-recovery-analysis-starting',original_trial_state=terminal['state'],
                original_trial_error=terminal.get('error'),original_trial_result_sha256=sha(ORIGINAL/'result.json'),
                restored=True,restored_by='separately-authorized-0337-trim-supplement',boot_attempts=1,
                springboard_log_prefix_preserved=True,other_log_prefix_preserved=terminal['other_log_prefix_preserved'],
                physical_FPS_qualified=False,device_commands=0)
    assert not OUT.exists();OUT.mkdir()
    for name,p in aliases.items():os.link(p,OUT/name)
    written=0
    def save(path,value):
        nonlocal written
        assert path.parent==OUT and not path.exists()
        raw=(json.dumps(value,indent=2)+'\n').encode();written+=len(raw)
        assert written<=48*1048576,'postanalysis output exceeds admitted batch'
        with path.open('xb') as f:f.write(raw)
    pins=[Path(__file__),source,BASE/'ready.json',BASE/'trial-plan.json',ORIGINAL/'result.json',
          RESCUE/'execution/result.json',RESCUE/'independent-six-file-restore.json',
          RESCUE/'independent-metadata-restore.json',*aliases.values()]
    save(OUT/'provenance.json',dict(state='0337-supplemental-restoration-precedes-frozen-analysis',
         original_result_preserved=True,analysis_first_line=tail[0].lineno,analysis_last_line=tail[-1].end_lineno,
         permitted_named_calls=sorted(calls),prefix_checks=prefix_checks,
         input_pins={str(p):sha(p) for p in pins},device_commands=0))
    namespace.update(EXEC=OUT,code=0,before=before,plan=load(BASE/'trial-plan.json'),result=result,save=save)
    try:
        exec(compile(ast.fix_missing_locations(ast.Module(body=tail,type_ignores=[])),str(source),'exec'),namespace)
    except (Exception,KeyboardInterrupt) as error:
        result.update(state='post-recovery-analysis-failed',analysis_error=repr(error))
    result['original_trial_result_unchanged']=sha(ORIGINAL/'result.json')==proof['original_frozen_result_sha256']
    assert result['original_trial_result_unchanged']
    save(OUT/'result.json',result)
    print(json.dumps(result,indent=2))
    if result['state']!='Q337-lossless-queue-CPU-observed-root-restored':raise SystemExit(1)


if __name__=='__main__':main()
