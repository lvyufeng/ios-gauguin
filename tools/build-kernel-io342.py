#!/usr/bin/env python3
"""Reproduce reused336/337 driver object and compile the bounded342 driver."""
import argparse,hashlib,json,subprocess
from pathlib import Path
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/io-path-342'
OLD=MAIN/'research/tmp/gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=BASE/'kernel-native-v4');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    prepared=json.loads((BASE/'kernel-prepared-v8/result.json').read_text());source=Path(prepared['source'])
    old=json.loads((OLD/'kernel-native-v1/result.json').read_text());row=old['results'][0]
    assert row['file']=='iokit/Kernel/arm/GauguinGPU.cpp' and sha(row['object'])==row['object_sha256']
    host=json.loads((BASE/'kernel-host-v8/result.json').read_text());assert host['inputs_unchanged'] and host['parent_candidate_observations_identical']
    pins={str(p):sha(p) for p in (Path(__file__),BASE/'kernel-prepared-v8/result.json',BASE/'kernel-host-v8/result.json',OLD/'kernel-native-v1/result.json',Path(row['object']))}
    for p,h in prepared['input_pins'].items():assert sha(p)==h;pins[p]=h
    for name,h in prepared['source_pins'].items():assert sha(source/name)==h;pins[str(source/name)]=h
    for p,h in old['input_pins'].items():assert sha(p)==h;pins[p]=h
    out.mkdir();result=dict(state='0342-kernel-driver-compiling',steps=[],objects={},input_pins=pins,device_commands=0)
    def save():(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label,cwd=None):
        p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=240);(out/(label+'.log')).write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(label=label,arguments=args,cwd=str(cwd) if cwd else None,exit=p.returncode));save()
        assert p.returncode==0,(label,p.stderr[-2500:])
    try:
        for variant in ('baseline','candidate'):
            args=list(row['arguments']);dest=out/(variant+'-GauguinGPU.o')
            if variant=='candidate':args=[v.replace(str(OLD/'kernel-source'),str(source)) for v in args]
            args[args.index('-o')+1]=str(dest);args[args.index('-MF')+1]=str(out/(variant+'.d'))
            run(args,variant+'-compile',row['cwd'])
            if variant=='baseline':assert sha(dest)==row['object_sha256'],'original driver object differs'
            run(['nm','-u',str(dest)],variant+'-undefined')
            run(['xcrun','llvm-objdump','--macho','--disassemble','--no-show-raw-insn',str(dest)],variant+'-disassembly')
            result['objects'][variant]=dict(path=str(dest),bytes=dest.stat().st_size,sha256=sha(dest))
        prior=set((out/'baseline-undefined.log').read_text().splitlines());current=set((out/'candidate-undefined.log').read_text().splitlines())
        added=sorted(current-prior);assert all(n.strip() in ('_thread_get_runtime_self','_sweet_log_append') for n in added),added
        result.update(state='0342-native-ARM64-driver-baseline337-object-exact',baseline_object_bytes_identical=True,
            identity=prepared['identity'],new_undefined_symbols=added,kernel_CPU_ticks_explicitly_converted=True,
            original_operations_and_ownership_preserved=True,hardware_qualified=False)
    except BaseException as error:result.update(state='0342-kernel-driver-native-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))
if __name__=='__main__':main()
