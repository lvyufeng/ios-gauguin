#!/usr/bin/env python3
"""Compile the exact original/candidate descriptor methods with mocked IOKit."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/map-query-324'
MAIN=Path('/Users/baai/Project/ios-gauguin')
BASE=MAIN/'research/tmp/gauguin-issued-fence-worktree-20261112/.deps-cache/p0-20261105/source310-display-wake'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def method(p):
 s=p.read_text();a=s.index('IOReturn GauguinGPUUserClient::clientMemoryForType(');z=s.index('\nIOReturn GauguinGPUUserClient::surface(',a);return s[a:z]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True,type=Path);out=ap.parse_args().out.resolve()
 assert out.is_relative_to(STATE) and not out.exists()
 source=STATE/'kernel-source';old=BASE/'iokit/Kernel/arm/GauguinGPU.cpp';new=source/'iokit/Kernel/arm/GauguinGPU.cpp';board=source/'bsd/dev/gauguin_gmu_board.c';header=source/'bsd/dev/gauguin_gpu_runtime.h'
 assert sha(old)=='ef67af612ee49223f50f44c529da317cbb15a7dd03d4391f8bd9d3dce53eb093'
 s=board.read_text();a=s.index('bool sweet_gpu_runtime_pending_metadata(');z=s.index('bool sweet_gpu_runtime_ready(void)',a)
 fixture=WORK/'tests/fixtures/unrelated_map_host.cpp';raw=fixture.read_text().replace('// EXTRACT_PREDICATE',s[a:z]).replace('// EXTRACT_BASELINE',method(old).replace('::clientMemoryForType(', '::baseline(')).replace('// EXTRACT_CANDIDATE',method(new).replace('::clientMemoryForType(', '::candidate('))
 out.mkdir();cpp=out/'actual.cpp';cpp.write_text(raw);binary=out/'check'
 args=['xcrun','--sdk','macosx','clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(header.parent),str(cpp),'-o',str(binary)]
 with (out/'compile.log').open('x')as f:p=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
 assert p.returncode==0,'compile.log'
 env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
 with (out/'run.log').open('x')as f:p=subprocess.run([str(binary)],stdout=f,stderr=subprocess.STDOUT,env=env)
 assert p.returncode==0,'run.log'
 result=json.loads((out/'run.log').read_text());result.update(sanitizers='ASan+UBSan',source_sha256=sha(new),predicate_source_sha256=sha(board),fixture_sha256=sha(fixture),input_pins={str(p):sha(p)for p in (old,new,board,header,fixture,Path(__file__),WORK/'tools/prepare-map-query-kernel.py')})
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
