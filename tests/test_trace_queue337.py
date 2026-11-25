#!/usr/bin/env python3
"""Compile actual 0337 producer queues under memory and race sanitizers."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import subprocess

REPO=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    source=REPO/'xnu/overlays/queue337/bsd/dev'
    fixture=REPO/'tests/fixtures/trace_queue337_host.c'
    board=REPO/'tests/fixtures/trace337_board.c'
    inputs=[Path(__file__),fixture,board,REPO/'tests/fixtures/test_ui_trace_board_shim.h',
            REPO/'graphics/gauguin-sb-rate-trace/SBTraceQueue.h',
            source/'gauguin_ui_trace.c',source/'gauguin_ui_trace.h',source/'gauguin_ui_trace_board.c',REPO/'tools/ui_trace_log.py']
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={str(p):sha(p)for p in inputs};steps=[]
    for name,sanitizer in [('memory','address,undefined'),('race','thread')]:
        executable=out/name
        command=['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g',
                 '-fsanitize='+sanitizer,'-fno-omit-frame-pointer','-pthread',
                 '-I'+str(source),'-I'+str(REPO/'graphics/gauguin-sb-rate-trace'),
                 str(fixture),str(source/'gauguin_ui_trace.c'),'-o',str(executable)]
        for label,argv in [('compile',command),('run',[str(executable)])]:
            with (out/(name+'-'+label+'.log')).open('x')as stream:
                proc=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=55,
                    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',
                             UBSAN_OPTIONS='halt_on_error=1',TSAN_OPTIONS='halt_on_error=1'))
            steps.append(dict(name=name+'-'+label,exit=proc.returncode,argv=argv))
            assert proc.returncode==0,steps[-1]
    spec=importlib.util.spec_from_file_location('ui337',REPO/'tools/ui_trace_log.py')
    ui=importlib.util.module_from_spec(spec);spec.loader.exec_module(ui)
    command=['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g',
             '-fsanitize=address,undefined','-I'+str(source),'-I'+str(REPO/'tests/fixtures'),
             '-DGUT_BOARD_SOURCE="'+str(source/'gauguin_ui_trace_board.c')+'"',
             str(board),str(source/'gauguin_ui_trace.c'),'-o',str(out/'board')]
    for label,argv in [('board-compile',command)]+[(case,[str(out/'board'),case])for case in ('off','bad','profile','alloc','capture','loss')]:
        with (out/(label+'.log')).open('x')as stream:
            proc=subprocess.run(argv,stdout=stream,stderr=subprocess.STDOUT,timeout=30)
        steps.append(dict(name=label,argv=argv,exit=proc.returncode));assert proc.returncode==0,label
    printed=ui.parse((out/'capture.log').read_text())
    assert printed['header']['version']==2 and len(printed['events'])==15 and not printed['contention_seen']
    assert ui.parse((out/'loss.log').read_text())['header']['lost']==1
    capture='\n'.join([
      'SWEET UI254 H: version=2 count=3 reason=1 lost=0 start=100 end=1000 numer=125 denom=3 which=1 gestures=1',
      'SWEET UI254 E: seq=1 tick=100 kind=1 id=1 pid=0 flags=0 a=98 b=99 c=1',
      'SWEET UI254 E: seq=2 tick=110 kind=10 id=10 pid=7 flags=0 a=0 b=0 c=0',
      'SWEET UI254 E: seq=3 tick=109 kind=10 id=11 pid=7 flags=0 a=0 b=0 c=0',
      'SWEET UI254 F: count=3 lost=0; CPU-clock capture only'])
    assert len(ui.parse(capture)['events'])==3
    try:ui.parse(capture.replace('version=2','version=1'))
    except ValueError as error:assert str(error)=='CPU clock regressed'
    else:raise AssertionError('legacy ordering check was weakened')
    assert all(sha(Path(p))==h for p,h in pins.items())
    result=dict(state='0337-actual-queues-ASan-UBSan-TSan-passed',steps=steps,input_pins=pins,
                inputs_unchanged=True,device_commands=0,hardware_qualified=False,
                note='Capacity and report/control contention remain explicit losses; normal record writers and logger have no shared producer trylock. Version2 sequences are reservation order, not global tick order.')
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['state'])

if __name__=='__main__':main()
