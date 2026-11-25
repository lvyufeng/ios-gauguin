#!/usr/bin/env python3
"""Reproduce C4 and add one explicit fixed-path loader after first completion."""
from pathlib import Path
import argparse,hashlib,json,shutil,struct,subprocess
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
RECEIPT=MAIN/'research/tmp/metal-ca-c4-20261112/native-final-v3/result.json'
OLD_SHA='560284ddda16936df1dd9c6003c8ef4c31096a7c41fcd72ade1051db8411d1d5'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 out=a.out.resolve();assert out.is_relative_to(WORK/'research/tmp')and not out.exists()
 old=json.loads(RECEIPT.read_text());source=Path(old['source']);bundle=Path(old['bundle'])
 assert old['sha256']==sha(old['binary'])==OLD_SHA and old['bytes']==428720
 for p,digest in old['input_pins'].items():assert sha(p)==digest,p
 loader=WORK/'graphics/gauguin-edr-loader/GauguinEDRLoader.h'
 pins={**old['input_pins'],str(RECEIPT):sha(RECEIPT),str(Path(__file__).resolve()):sha(Path(__file__)),str(loader):sha(loader),str(Path(old['binary'])):OLD_SHA}
 for name in ('Info.plist','_CodeSignature/CodeResources'):pins[str(bundle/name)]=sha(bundle/name)
 out.mkdir(parents=True);sources=out/'sources';sources.mkdir()
 local=[]
 for p in old['input_pins']:
  p=Path(p)
  if p.parent==source.parent and p.suffix in ('.m','.h'):
   q=sources/p.name;q.write_bytes(p.read_bytes());local.append(q)
 assert len(local)==8
 (sources/loader.name).write_bytes(loader.read_bytes())
 raw=source.read_text();anchor='\t[self release];\n}\n\n- (void)hakiosTurnAtCommit:'
 assert raw.count(anchor)==1
 replacement=('\t[self release];\n'
  '\tif (!__atomic_load_n(&gauguin_edr_loader_attempted, __ATOMIC_ACQUIRE)) {\n'
  '\t\t@autoreleasepool {\n\t\t\tgauguin_edr_load_after_completion();\n\t\t}\n\t}\n'
  '}\n\n- (void)hakiosTurnAtCommit:')
 changed=raw.replace(anchor,replacement)
 changed='#include "GauguinEDRLoader.h"\n'+changed
 assert changed.replace('#include "GauguinEDRLoader.h"\n','',1).replace(replacement,anchor)==raw
 (sources/source.name).write_text(changed)
 result=dict(state='C4-EDR318-native-build-started',input_pins=pins,products={},steps=[],device_commands=0,runtime_qualified=False)
 def run(argv,label):
  with(out/(label+'.log')).open('x')as f:r=subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT)
  result['steps'].append(dict(label=label,argv=argv,exit=r.returncode));assert r.returncode==0,label
 try:
  for variant in ('baseline','candidate'):
   dest=out/variant/'GauguinMetalDesktop.bundle';dest.mkdir(parents=True)
   shutil.copyfile(bundle/'Info.plist',dest/'Info.plist');binary=dest/'GauguinMetalDesktop'
   argv=list(old['compiler_argv']);argv[argv.index('-o')+1]=str(binary)
   if variant=='candidate':
    argv=[str(sources/Path(x).name)if x.endswith('.m')and Path(x).parent==source.parent else x for x in argv]
    argv.insert(argv.index('-o'),'-fmacro-prefix-map='+str(sources)+'='+str(source.parent))
   run(argv,variant+'-compile');run(['codesign','--force','--sign','-',str(dest)],variant+'-sign')
   run(['codesign','--verify','--strict',str(dest)],variant+'-verify')
   run(['nm','-m','-u',str(binary)],variant+'-imports');run(['otool','-L',str(binary)],variant+'-loads')
   assert sha(dest/'Info.plist')==sha(bundle/'Info.plist') and sha(dest/'_CodeSignature/CodeResources')==sha(bundle/'_CodeSignature/CodeResources')
   data=binary.read_bytes();h=struct.unpack_from('<8I',data);assert h[:2]==(0xfeedfacf,0x100000c)and h[3]==8
   at=32;platform=[]
   for _ in range(h[4]):
    tag,n=struct.unpack_from('<II',data,at);assert n>=8 and at+n<=32+h[5]
    if tag==0x32:platform.append(struct.unpack_from('<III',data,at+8))
    at+=n
   assert at==32+h[5]and len(platform)==1 and platform[0][:2]==(2,0x100000)
   result['products'][variant]=dict(binary=str(binary),sha256=sha(binary),bytes=len(data),platform=platform[0],resources_unchanged=True)
   if variant=='baseline':assert sha(binary)==OLD_SHA,'C4 baseline reproduction differs'
  before=(out/'baseline-imports.log').read_text();after=(out/'candidate-imports.log').read_text()
  result['imports_unchanged']=before==after
  result['added_import_lines']=sorted(set(after.splitlines())-set(before.splitlines()))
  result['actual_OS_import_qualification_pending']=not result['imports_unchanged']
  assert result['products']['candidate']['bytes']<=105*4096,'C4 candidate exceeds original allocation'
  result.update(state='native-C4-EDR318-baseline-reproduced-candidate-signed',existing_allocation_bytes=105*4096,
    original_completion_and_release_before_loader=True,source_change_reversible=True,
    first_load_autorelease_pool=True,later_callbacks_skip_pool=True,
    source=str(sources/source.name),loader_header_sha256=sha(loader))
 except Exception as error:
  result.update(state='C4-EDR318-native-build-failed',error=repr(error));raise
 finally:
  result['inputs_unchanged']=all(sha(p)==v for p,v in pins.items())
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items()if k not in ('input_pins','steps')},indent=2))
if __name__=='__main__':main()
