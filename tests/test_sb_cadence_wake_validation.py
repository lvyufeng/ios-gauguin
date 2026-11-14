from pathlib import Path
import hashlib,importlib.util,json
WORK=Path(__file__).resolve().parents[1];W=WORK/'research/tmp/sb-cadence-312';p=WORK/'tools/run-sb-cadence-trial.py';spec=importlib.util.spec_from_file_location('wake_trial310',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows=['SWEET FB POWER: state=2 tick=100; requested, panel unqualified','SWEET UI WAKE: power press tick=101 state=off','SWEET UI WAKE: power release tick=102; one pair only','SWEET FB POWER: state=1 tick=103; requested, panel unqualified','SWEET UI WAKE: display-on confirmed tick=110; begin workload']
for i in range(13):rows += [f'SWEET UI SCRIPT: begin stroke={i} tick={111+i*10} origin=synthetic',f'SWEET UI SCRIPT: end stroke={i} tick={112+i*10} events=34; HID return only']
valid='\n'.join(rows);assert m.validate_wake_log(valid)=={'button_pairs':1,'first_stroke_tick':111,'last_release_tick':232}
already='\n'.join(x for x in rows if 'power press' not in x and 'power release' not in x);assert m.validate_wake_log(already)['button_pairs']==0
bad=[valid.replace('display-on confirmed tick=110','display-on confirmed tick=115'),valid.replace('power release tick=102','power release tick=999'),valid.replace('power press tick=101','power press tick=999'),valid+'\nSWEET FB POWER: state=2 tick=200; requested, panel unqualified',valid.replace('state=1 tick=103','state=2 tick=103'),valid.replace('end stroke=12','end stroke=11'),valid.replace('begin stroke=4','begin stroke=5'),valid.replace('end stroke=0 tick=112','end stroke=0 tick=150'),valid.replace('end stroke=0 tick=112','end stroke=0 tick=109'),'\n'.join(x for x in rows if 'power release' not in x),valid+'\n'+rows[1],valid+'\n'+rows[4]]
for log in bad:
 try:m.validate_wake_log(log)
 except ValueError:pass
 else:raise AssertionError('invalid wake log accepted')
result={'state':'passed-display-on-log-validation','positive_cases':2,'negative_cases':len(bad),'executor_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'device_commands':0}
(W/'wake-validation-test.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
