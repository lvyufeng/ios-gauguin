"""Qualify immutable local log aliases and the capture bounds that budget them."""
import hashlib,importlib.util,json,tempfile
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
path=WORK/'tools/run-sb-cadence-trial.py'
spec=importlib.util.spec_from_file_location('trial',path)
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
with tempfile.TemporaryDirectory(prefix='edr320-log-alias-') as folder:
    p=Path(folder);original=p/'captured.log';data=b'complete unchanged capture\n'*200
    original.write_bytes(data)
    for name in ('before.log','after.log','current.log'):
        runner.link_saved_log(original,p/name)
        assert (p/name).stat().st_ino==original.stat().st_ino
        assert (p/name).read_bytes()==data
    assert original.stat().st_nlink==4
    try:runner.link_saved_log(original,p/'before.log')
    except FileExistsError:pass
    else:raise AssertionError('existing output overwritten')
    assert original.read_bytes()==data
capture_path=WORK/'tools/capture-sb-cadence-root.py'
spec=importlib.util.spec_from_file_location('capture',capture_path)
capture=importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
assert capture.FILE_LIMITS['/private/var/log/springboard.log']==41943040
assert capture.FILE_LIMITS['/private/var/log/backboardd.log']==23068672
assert sum(capture.FILE_LIMITS.get(path,1048576)for path in capture.PATHS)==137919024
result=dict(state='passed-immutable-log-hardlinks-and-expanded-capture-bounds',
    aliases=3,no_log_truncation=True,existing_output_refused=True,device_commands=0,
    executor_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    capture_sha256=hashlib.sha256(capture_path.read_bytes()).hexdigest())
out=WORK/'research/tmp/queue-loss-337/log-storage-test.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result,indent=2))
