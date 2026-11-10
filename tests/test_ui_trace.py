#!/usr/bin/env python3
"""Actual bounded trace core/board; typed clock/allocator and printed-log oracle."""
import argparse,hashlib,importlib.util,json,os,subprocess,tempfile
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def extract_new_files(out):
    text=(REPO/'xnu/patches/0216-gauguin-bounded-ui-trace.patch').read_text()
    for name in ('gauguin_ui_trace.h','gauguin_ui_trace.c','gauguin_ui_trace_board.c'):
        marker='--- /dev/null\n+++ b/bsd/dev/'+name+'\n';assert text.count(marker)==1
        chunk=text.split(marker)[1].split('\n--- ')[0].splitlines()
        lines=[]
        for line in chunk:
            if line.startswith('@@'):continue
            assert line.startswith('+'),line
            lines.append(line[1:])
        (out/name).write_text('\n'.join(lines)+'\n')
    return out

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path)
    ap.add_argument('--out',type=Path);a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='ui254-') as tmp:
        root=Path(tmp);out=a.out.resolve() if a.out else root/'out';out.mkdir(parents=True,exist_ok=False)
        source=a.source or (Path(os.environ['XNU_SOURCE']) if 'XNU_SOURCE' in os.environ else None)
        d=source/'bsd/dev' if source else extract_new_files(root)
        fixtures=REPO/'tests/fixtures'
        paths=[Path(__file__),REPO/'tools/ui_trace_log.py',REPO/'xnu/patches/0216-gauguin-bounded-ui-trace.patch',
               *[d/n for n in ('gauguin_ui_trace.c','gauguin_ui_trace.h','gauguin_ui_trace_board.c')],
               *[fixtures/n for n in ('test_ui_trace_core.c','test_ui_trace_board.c','test_ui_trace_board_shim.h')]]
        pins={str(p):sha(p) for p in paths};records=[]
        env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
        def run(args,name):
            with (out/(name+'.log')).open('x') as f:
                p=subprocess.run(list(map(str,args)),env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120)
            records.append({'name':name,'exit':p.returncode});assert p.returncode==0,(name,p.returncode)
        cc=os.environ.get('CC','cc');flags=['-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g',
             '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(d),'-I'+str(fixtures)]
        run([cc,*flags,'-pthread',fixtures/'test_ui_trace_core.c',d/'gauguin_ui_trace.c','-o',out/'core'],'compile-core')
        run([out/'core'],'core')
        run([cc,*flags,'-DGUT_BOARD_SOURCE="'+str(d/'gauguin_ui_trace_board.c')+'"',
             fixtures/'test_ui_trace_board.c',d/'gauguin_ui_trace.c','-o',out/'board'],'compile-board')
        for case in ('off','bad','profile','alloc','capture','loss'):run([out/'board',case],case)
        spec=importlib.util.spec_from_file_location('ui_log',REPO/'tools/ui_trace_log.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        log=(out/'capture.log').read_text();result=mod.parse(log)
        assert len(result['events'])==15 and not result['unpaired_endpoints'] and not result['contention_seen']
        assert sorted(s['elapsed_ns']for s in result['spans'])==[2083,12500,12500,41666,41666]
        assert mod.parse((out/'loss.log').read_text())['contention_seen']
        bad=[log.replace('version=1','version=2'),log.replace('numer=125','numer=0'),
             log.replace('seq=2 ','seq=1 '),log.replace('kind=2 ','kind=999 '),
             log.replace('count=15','count=14',1),log.replace('tick=1000100','tick=999999'),
             log[:log.index('SWEET UI254 F:')],log+log,
             log.replace('flags=1 a=900000','flags=0 a=18446744073709551616')]
        for candidate in bad:
            try:mod.parse(candidate)
            except ValueError:pass
            else:raise AssertionError('malformed capture accepted')
        assert all(sha(Path(p))==h for p,h in pins.items())
        summary={'state':'passed-actual-core-and-board-host','runs':records,'log_mutations_rejected':len(bad),
                 'input_pins':pins,'inputs_unchanged':True,'hardware_qualified':False,
                 'scope':'atomic prefix, bounded allocation, actual print/decode; hardware and framework calls are not run'}
        (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps({k:v for k,v in summary.items()if k not in ('input_pins','runs')}))
if __name__=='__main__':main()
