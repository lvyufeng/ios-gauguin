#!/usr/bin/env python3
"""Preserve actual326 errors under331 analysis; old430 profile is explicitly unqualified."""
from pathlib import Path
import ast,hashlib,importlib.util,json,textwrap
W=Path(__file__).resolve().parents[1];B=W/'research/tmp/key-perf565-331';E=Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-perf430-worktree-20261115/research/tmp/perf430-326/execution')
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def mod(name):
 spec=importlib.util.spec_from_file_location(name,W/'tools'/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
runner=mod('run-sb-cadence-trial');source=W/'tools/run-sb-cadence-trial.py';raw=source.read_text();a=raw.index("        kernel=(EXEC/'kernel.log').read_text");z=raw.index('\n    except (Exception,KeyboardInterrupt) as error:',a);body=textwrap.dedent(raw[a:z]);tree=ast.parse(body)
for node in ast.walk(tree):
 if isinstance(node,ast.Name):assert node.id not in {'io','RecoveryIO','subprocess','os','install_core','restore_core','restore_build','capture_as'}
original=sha(E/'result.json');assert load(E/'result.json')['restored'];assert load(E/'independent-restore.json')['state']=='independently-verified-six-original-files-and-misc'
saved={}
def save(path,value):
 assert path.parent==E and path.name not in saved;saved[path.name]=value
scope=dict(EXEC=E,WORK=W,plan=load(E.parent/'trial-plan.json'),result={'restored':True},before=load(E/'fresh-before/result.json'),json=json,require=runner.require,module=runner.module,save=save,
 rate_log=mod('analyze-sb-rate-log'),ui_log=mod('ui_trace_log'),joint_log=mod('analyze-sb-cadence'),stack_log=mod('analyze-sb-stack-log'),process_log=mod('analyze-process-samples328'))
for name in ('validate_wake_log','classify_observer','classify_stacks','classify_process_samples','inspect_edr_activation','classify_edr','inspect_fault_query_cache'):scope[name]=getattr(runner,name)
try:exec(compile(tree,str(source),'exec'),scope)
except ValueError as error:assert str(error)=='malformed tl: M record'
else:raise AssertionError('negative326 GPU durations incorrectly accepted')
assert not saved['native-perf-analysis.json']['active']
assert not saved['submit-reject-analysis.json']['diagnostic_coverage_qualified']
assert saved['submit-reject-analysis.json']['counters']['failures']==32
assert saved['submit-reject-analysis.json']['errors']=={'failure_count_mismatch':1}
assert scope['result']['submit_reject_analysis']['records']==0 and not scope['result']['native_performance_profile']['active']
assert not saved['process-sample-analysis.json']['complete'] and saved['process-sample-analysis.json']['parse_error']
assert 'cadence-analysis.json'not in saved and sha(E/'result.json')==original
paths=[Path(__file__),source,W/'tools/analyze-submit-reject-log.py',W/'tools/analyze-native-perf-log.py',W/'tools/analyze-process-samples328.py',E/'result.json',E/'independent-restore.json',E/'kernel.log',E/'springboard-new.log',E/'backboardd.log.current',E/'fresh-before/result.json',E.parent/'trial-plan.json']
r=dict(state='KEYPERF331-diagnostics-and-samples-saved-before-observed-negative-timeline-failure',actual326_failure_fixture=True,old430_request_not_accepted_as565=True,fixture_is_not_331_runtime=True,output_files_written_by_analyzed_segment=0,saves_intercepted_in_memory=list(saved),strict_negative_M_refusal_preserved=True,missing_diagnostics_not_false_qualified=True,original326_result_unchanged=True,input_pins={str(p):sha(p)for p in paths},device_commands=0)
with(B/'analysis-order-test.json').open('x')as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in r.items()if k!='input_pins'},indent=2))
