#!/usr/bin/env python3
"""Reproduce EDR336, changing only its kernel identity scope for the fixed Q337 image."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from surface_signature_compare import compare_signature_reservations
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/queue-loss-337'
OLD=MAIN/'research/tmp/gauguin-cache-adapt-worktree-20261116/research/tmp/bo-reuse-336/edr-native-v1'
EXPECTED='60a90e85a452fa9e2171aa572158f225a9a48a781d5c8a5dcdb424546271b0a5'
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);out=ap.parse_args().out.resolve()
 assert out.is_relative_to(STATE) and not out.exists()
 old=json.loads((OLD/'result.json').read_text());assert old['state']=='native-EDR336-kernel-scope-canonical-baseline-candidate-signed'
 assert sha(old['products']['candidate']['binary'])==old['products']['candidate']['sha256']==EXPECTED
 identity=json.loads((STATE/'kernel-identity.json').read_text())['identity'];image=json.loads((STATE/'ui337-image.json').read_text())
 assert image['build_identity']==identity and image['command'].split().count('sweetgpumap=1')==1 and image['command'].split().count('gpf=4')==1
 source=WORK/'graphics/gauguin-edr-default'
 for name in ('EDRDefault.c','EDRDefaultContract.h'):assert sha(source/name)==sha(OLD/'sources'/name)
 before=(OLD/'sources/EDRDefaultCore.h').read_text();after=(source/'EDRDefaultCore.h').read_text()
 assert before[:before.index('/* BC336 requires')] == after[:after.index('/* Q337 requires')]
 assert before[before.index('enum geq_result {'):] == after[after.index('enum geq_result {'):]
 assert identity in after and 'sweetgpumap=1' in after and 'gpf=4' in after and 'xnu-local336-' not in after and 'gsp=328' in after and 'gsp=316' not in after
 pins=dict(old['input_pins'])
 for p in (OLD/'result.json',Path(old['products']['candidate']['binary']),*list((OLD/'sources').glob('*')),
           *list(source.glob('*')),Path(__file__),WORK/'tools/surface_signature_compare.py',STATE/'kernel-identity.json',STATE/'ui337-image.json',STATE/'ui337-review.json',STATE/'edr-host-v1/result.json'):
  pins[str(p.resolve())]=sha(p)
 for p,d in pins.items():assert sha(p)==d,p
 argv=next(r['argv'] for r in old['steps'] if r['label']=='candidate-compile')
 old_source=str(OLD/'sources/EDRDefault.c');assert argv.count(old_source)==1
 out.mkdir();(out/'sources').mkdir()
 for p in source.glob('*'):
  if p.is_file():shutil.copyfile(p,out/'sources'/p.name)
 result=dict(state='EDR337-scope-build-started',input_pins=pins,products={},steps=[],device_commands=0)
 def run(command,label):
  with (out/(label+'.log')).open('x')as f:p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT)
  result['steps'].append(dict(label=label,argv=command,exit=p.returncode));assert p.returncode==0,label
 try:
  for variant in ('baseline','candidate'):
   dest=out/variant;dest.mkdir();binary=dest/'libGauguinEAGLAdmission.dylib';command=list(argv);command[command.index('-o')+1]=str(binary)
   if variant=='candidate':command[command.index(old_source)]=str(out/'sources/EDRDefault.c')
   run(command,variant+'-compile');run(['codesign','--force','--sign','-',str(binary)],variant+'-sign');run(['codesign','--verify','--strict',str(binary)],variant+'-verify')
   for args,label in ((['otool','-L'],'loads'),(['nm','-m','-u'],'imports'),(['nm','-gU'],'exports')):run([*args,str(binary)],variant+'-'+label)
   result['products'][variant]=dict(binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary))
   if variant=='baseline':
    installed=Path(old['products']['candidate']['binary'])
    run(['codesign','--verify','--strict',str(installed)],'installed-verify')
    comparison=compare_signature_reservations(installed.read_bytes(),binary.read_bytes())
    comparison.update(original_sha256=EXPECTED,rebuilt_initial_sha256=sha(binary))
    reference=out/'signature-reference'/binary.name;reference.parent.mkdir();shutil.copyfile(installed,reference)
    for label,path in [('reference',reference),('baseline',binary)]:
     run(['codesign','--remove-signature',str(path)],label+'-remove-signature')
     run(['codesign','--force','--sign','-',str(path)],label+'-canonical-sign')
     run(['codesign','--verify','--strict',str(path)],label+'-canonical-verify')
    assert reference.read_bytes()==binary.read_bytes(),'canonical EDR baseline differs'
    assert sha(installed)==EXPECTED
    comparison.update(canonical_signed_bytes_identical=True,installed_input_unchanged=True,canonical_sha256=sha(binary))
    result['baseline_reproduction']=comparison
    result['products'][variant].update(bytes=binary.stat().st_size,sha256=sha(binary))
  assert (out/'baseline-imports.log').read_bytes()==(out/'candidate-imports.log').read_bytes()
  assert (out/'baseline-loads.log').read_text().splitlines()[1:]==(out/'candidate-loads.log').read_text().splitlines()[1:]
  exported=lambda n:{r.split()[-1]for r in (out/(n+'-exports.log')).read_text().splitlines() if r.strip()}
  assert exported('baseline')==exported('candidate')
  assert result['products']['candidate']['bytes']<=73728
  result.update(state='native-EDR337-kernel-scope-canonical-baseline-candidate-signed',
   kernel_identity=identity,image_sha256=image['image_sha256'],required_optin='gpf=4',required_mapping_optin='sweetgpumap=1',required_sampling_optin='gsp=328',
   private_data_pointer_bytes=8,pointer_write_and_once_contract_unchanged=True,imports_unchanged=True,exports_unchanged=True,loads_unchanged=True,
   existing_allocation_bytes=73728,additional_threads=0,code_change='only geq_scope identity and boot opt-in',installed=False)
 except Exception as e:result.update(state='EDR337-scope-build-failed',error=repr(e));raise
 finally:
  result['inputs_unchanged']=all(sha(p)==d for p,d in pins.items());(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps')},indent=2))
if __name__=='__main__':main()
