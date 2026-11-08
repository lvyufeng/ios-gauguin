#!/usr/bin/env python3
"""Compile the real libdrm shim with one typed IOKit boundary; retain RED/GREEN."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tempfile
repo=Path(__file__).resolve().parent.parent
ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,default=os.environ.get('MESA_SOURCE'));ap.add_argument('--old-source',type=Path);ap.add_argument('--out',type=Path);a=ap.parse_args()
assert a.source,'--source or MESA_SOURCE is required'
temporary=tempfile.TemporaryDirectory(prefix='mesa-queue-') if not a.out else None
out=Path(temporary.name) if temporary else a.out.resolve();out.mkdir(exist_ok=temporary is not None)
fixture=repo/'tests/fixtures/mesa_queue_fences.c'
sdk=Path(subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip())
compiler=subprocess.check_output(['xcrun','--sdk','macosx','--find','clang'],text=True).strip()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
paths=[Path(__file__),fixture,sdk/'SDKSettings.json'];sources=[('new',a.source.resolve())]
if a.old_source:sources.insert(0,('old',a.old_source.resolve()))
for mode,source in sources:
    paths += [source/'src/hakios-drm/hakios.drm.c',source/'src/hakios-drm/xf86drm.h',*list((source/'include/drm-uapi').glob('*.h'))]
pins={str(p):sha(p) for p in paths};result={'state':'running','input_pins':pins,'runs':[],'scope':'actual source/typed IOKit host boundary only; no GPU hardware qualification'}
def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
save()
env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
for mode,source in sources:
    c=source/'src/hakios-drm/hakios.drm.c';assert fixture.read_text().count('@SOURCE@')==1
    unit=out/(mode+'.c');unit.write_text(fixture.read_text().replace('@SOURCE@','#include '+json.dumps(str(c))))
    cmd=[compiler,'-isysroot',str(sdk),'-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(source/'include'),str(unit),'-framework','IOKit','-framework','CoreFoundation','-o',str(out/mode)]
    p=subprocess.run(cmd,env=env,capture_output=True);(out/(mode+'-compile.stdout')).write_bytes(p.stdout);(out/(mode+'-compile.stderr')).write_bytes(p.stderr)
    result['runs'].append({'mode':mode,'compile_argv':cmd,'compile_exit':p.returncode});save();assert p.returncode==0,p.stderr
    p=subprocess.run([str(out/mode),'common' if mode=='old' else 'all'],env=env,capture_output=True);(out/(mode+'-run.stdout')).write_bytes(p.stdout);(out/(mode+'-run.stderr')).write_bytes(p.stderr)
    result['runs'][-1]['run_exit']=p.returncode;save()
    if mode=='old':assert p.returncode!=0 and b'Assertion failed:' in p.stderr and b'poll(a,1)==0' in p.stderr,p.stderr
    else:assert p.returncode==0,p.stderr
assert pins=={str(p):sha(p) for p in paths},'inputs changed'
result.update(state='passed-actual-Mesa-queue-fences-RED-GREEN' if a.old_source else 'passed-actual-Mesa-queue-fences-GREEN',inputs_unchanged=True);save();print(json.dumps(result,indent=2))
