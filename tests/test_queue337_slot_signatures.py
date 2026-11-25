#!/usr/bin/env python3
"""Verify signed logical files read from an actual-root installation model."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,tempfile

WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/queue-loss-337'
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
M=load('slot337_install_model',WORK/'tests/test_sb_cadence_install_model.py')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    physical=M.RESTORE_TEST.ReadonlyCache(M.RecoveryIO())
    model=M.ModelIO(physical,[]);plan_dir=BASE/'slot-delta';capture_dir=BASE/'slot-capture'
    plan=json.loads((plan_dir/'install-plan.json').read_text())
    approval=dict(approved=True,one_shot=True,allow_install=True,allow_rollback=True,
                  fixture_only=True,plan_sha256=sha(plan_dir/'install-plan.json'))
    result=M.INSTALL.install(plan_dir,capture_dir,approval,model,M.HFS,M.Remote,lambda _:None)
    assert result['state']=='install-applied-and-HFSX-verified' and model.model_only
    h=M.HFS(stream=M.Remote(model),size=17179869184);checks=[]
    try:
        with tempfile.TemporaryDirectory(prefix='signed-slots-',dir=BASE)as temp:
            root=Path(temp)
            for name in ('eagl','c4','admission','core'):
                r=plan['rows'][name];data=h.content(r['path'])
                assert len(data)==r['new_logical'] and hashlib.sha256(data).hexdigest()==r['new_file_sha256']
                assert h.paths[r['path']]['data']['extents']==[[r['data_block'],r['data_blocks']]]
                if name=='c4':
                    target=root/'GauguinMetalDesktop.bundle';target.mkdir()
                    binary=target/'GauguinMetalDesktop';binary.write_bytes(data)
                    (target/'Info.plist').write_bytes(h.content('/System/Library/Extensions/GauguinMetalDesktop.bundle/Info.plist'))
                    (target/'_CodeSignature').mkdir()
                    (target/'_CodeSignature/CodeResources').write_bytes(h.content('/System/Library/Extensions/GauguinMetalDesktop.bundle/_CodeSignature/CodeResources'))
                else:target=root/(name+'.dylib');target.write_bytes(data)
                proc=subprocess.run(['codesign','--verify','--strict',str(target)],capture_output=True,text=True)
                (BASE/(name+'-modeled-signature.log')).write_text(proc.stdout+proc.stderr)
                assert proc.returncode==0,(name,proc.stderr)
                checks.append(dict(name=name,logical=len(data),sha256=r['new_file_sha256'],signature_verified=True,extents_unchanged=True))
    finally:h.close()
    paths=[Path(__file__),plan_dir/'install-plan.json',capture_dir/'result.json',
           WORK/'tools/sb-cadence-slot-install-io.py',WORK/'tests/test_sb_cadence_install_model.py',WORK/'tests/test_sb_cadence_restore_model.py']
    receipt=dict(state='Q337-four-modeled-logical-signatures-verified',checks=checks,
                 modeled_writes=model.writes,device_writes=0,device_boots=0,
                 input_pins={str(p):sha(p)for p in paths},runtime_qualified=False)
    (BASE/'slot-signature-review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['state'])
if __name__=='__main__':main()
