#!/usr/bin/env python3
"""Focused trace-kernel checks for a clean staged tree; no device or OS image."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,time
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();repo=Path(__file__).resolve().parents[1]
    source=a.source.resolve();out=a.out.resolve();assert(source/'bsd/dev/gauguin_ui_trace.c').is_file()
    assert not out.exists();out.mkdir(parents=True)
    files=[Path(__file__),repo/'xnu/patches/series',repo/'xnu/patches/0216-gauguin-bounded-ui-trace.patch',
           repo/'xnu/patches/0217-gauguin-inherited-scan-timing.patch',
           repo/'xnu/patches/0218-gauguin-pre-mount-scan-log.patch']
    files += [p for directory in [source/'bsd/dev',source/'iokit/Kernel/arm',repo/'tests',repo/'tools']for p in directory.rglob('*')if p.is_file()and '__pycache__'not in p.parts]
    pins={str(p):sha(p)for p in files};rows=[];start=time.monotonic()
    jobs=[('trace',[sys.executable,repo/'tests/test_ui_trace.py','--source',source,'--out',out/'trace']),
          ('command',[sys.executable,repo/'tests/test_trace_boot_profile.py','-v']),
          ('scan',[sys.executable,repo/'tests/test_scan_timing.py','--source',source]),
          ('scan-log',[sys.executable,repo/'tests/test_scan_log_record.py','--source',source]),
          ('ufs-ownership',[sys.executable,repo/'tests/test_ufs_ownership.py']),
          ('ufs-completion',[sys.executable,repo/'tests/test_ufs_completion.py']),
          ('ufs-panic-logging',[sys.executable,repo/'tests/test_ufs_panic_logging.py']),
          ('ufs-marks',[sys.executable,repo/'tests/test_mark_writes.py']),
          ('hid',[sys.executable,repo/'tests/test_hid_touch_frames.py']),
          ('nvt',[sys.executable,repo/'tests/test_nvt_runtime.py']),
          ('gpu',[sys.executable,repo/'tests/test_metal_compositor_input.py','--source',source,'--out',out/'gpu','--trace-capture'])]
    result={'state':'running','scope':'focused UI trace regression lane; not all repository host tests','input_pins':pins,'jobs':rows,'hardware_qualified':False}
    env=dict(os.environ,XNU_SOURCE=str(source),PYTHONDONTWRITEBYTECODE='1',
             ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    def save():
        result.update(inputs_unchanged=all(sha(Path(n))==h for n,h in pins.items()),elapsed_seconds=time.monotonic()-start)
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        for name,argv in jobs:
            log=out/(name+'.log')
            with log.open('x')as stream:p=subprocess.run(list(map(str,argv)),cwd=repo,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
            rows.append({'name':name,'exit':p.returncode,'log':str(log),'log_sha256':sha(log)});save()
            assert p.returncode==0,(name,p.returncode)
        result['state']='passed-focused-ui-kernel-checks';save();assert result['inputs_unchanged']
    except Exception as e:result.update(state='failed',error=repr(e));save();raise
    print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
