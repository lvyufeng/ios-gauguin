#!/usr/bin/env python3
"""Reproduce fixed337, then replace only its driver object and version for342."""
import argparse,datetime,hashlib,json,struct,subprocess
from pathlib import Path
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/io-path-342'
PRIOR=MAIN/'research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def normalized(data):
    data=bytearray(data);at=32;found=0
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        cmd,size=struct.unpack_from('<II',data,at);assert size>=8 and at+size<=len(data)
        if cmd==0x1b:assert size==24;data[at+8:at+24]=bytes(16);found+=1
        at+=size
    assert found==1;return data

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=BASE/'kernel-link-v4');a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    parent_path=PRIOR/'local-link/build-manifest.json';parent=json.loads(parent_path.read_text())
    prepared_path=BASE/'kernel-prepared-v8/result.json';prepared=json.loads(prepared_path.read_text());source=Path(prepared['source'])
    native_path=BASE/'kernel-native-v4/result.json';native=json.loads(native_path.read_text())
    assert native['state']=='0342-native-ARM64-driver-baseline337-object-exact' and native['inputs_unchanged']
    assert native['baseline_object_bytes_identical'] and parent['inputs_unchanged']
    pins={p:v['sha256'] for p,v in parent['input_pins'].items()}
    for p,v in parent['input_pins'].items():assert sha(p)==v['sha256'] and Path(p).stat().st_mtime_ns==v['mtime_ns'],p
    for value in (prepared,native):
        for p,h in value['input_pins'].items():assert sha(p)==h;pins[p]=h
    for p in (Path(__file__),parent_path,prepared_path,native_path,Path(parent['kernel']['path']),Path(parent['unstripped']['path'])):pins[str(p)]=sha(p)
    for value in native['objects'].values():assert sha(value['path'])==value['sha256'];pins[value['path']]=value['sha256']
    base=Path(parent['source_union']['base']);previous=Path(parent['source_union']['overlay']);entries=[];changed=[];prior_names=set()
    for name,kind,digest in parent['source_union']['entries']:
        old=previous/name if (previous/name).is_file() else base/name;assert sha(old)==digest
        p=source/name if (source/name).is_file() else base/name;current=sha(p);entries.append([name,kind,current]);prior_names.add(name);pins[str(p)]=current
        if current!=digest:changed.append(name)
    for name in prepared['changed_files']:
        if name not in prior_names:entries.append([name,'file',sha(source/name)]);changed.append(name);pins[str(source/name)]=sha(source/name)
    assert set(changed)==set(prepared['changed_files'])
    original_filelist=Path(parent['link_command'][parent['link_command'].index('-filelist')+1]);inputs=original_filelist.read_text().splitlines()
    old_driver=[p for p in inputs if Path(p).name=='0-GauguinGPU.o'];assert len(old_driver)==1
    assert sha(old_driver[0])==native['objects']['baseline']['sha256'];pins[str(original_filelist)]=sha(original_filelist)
    out.mkdir();result=dict(state='0342-kernel-relink-running',steps=[],input_pins=pins,products={},device_commands=0)
    def save():(out/'build-manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    def run(args,label,cwd):
        p=subprocess.run(args,cwd=cwd,capture_output=True,timeout=240);(out/(label+'.log')).write_bytes(p.stdout+p.stderr)
        result['steps'].append(dict(label=label,arguments=args,cwd=str(cwd),exit=p.returncode));save();assert p.returncode==0,(label,p.stderr[-2000:])
    cwd=Path(parent['version_compile'][-1]).parent # No input lookup depends on this working directory.
    identity=prepared['identity'];old_identity=parent['build_identity']['id']
    try:
        for variant in ('baseline','candidate'):
            args=list(parent['link_command']);raw=out/(variant+'.unstripped');kernel=out/(variant+'.kernel')
            args[args.index('-o')+1]=str(raw)
            if variant=='candidate':
                version=(PRIOR/'local-link/version.c').read_text();assert version.count(old_identity)==2
                (out/'version.c').write_text(version.replace(old_identity,identity))
                compile_args=[v.replace(str(PRIOR/'local-link/version'),str(out/'version')) for v in parent['version_compile']]
                run(compile_args,'candidate-version',cwd)
                old_version=str(PRIOR/'local-link/version.o');assert args.count(old_version)==1
                args[args.index(old_version)]=str(out/'version.o')
                filelist=out/'candidate.filelist';filelist.write_text('\n'.join(native['objects']['candidate']['path'] if p==old_driver[0] else p for p in inputs)+'\n')
                args[args.index('-filelist')+1]=str(filelist)
            run(args,variant+'-link',cwd);run(['xcrun','strip','-S',str(raw),'-o',str(kernel)],variant+'-strip',cwd)
            if variant=='baseline':
                assert normalized(raw.read_bytes())==normalized(Path(parent['unstripped']['path']).read_bytes())
                assert normalized(kernel.read_bytes())==normalized(Path(parent['kernel']['path']).read_bytes())
            result['products'][variant]=dict(kernel=str(kernel),kernel_bytes=kernel.stat().st_size,kernel_sha256=sha(kernel),
                unstripped=str(raw),unstripped_bytes=raw.stat().st_size,unstripped_sha256=sha(raw));save()
        import sys;sys.path.insert(0,str(WORK/'tools'));from kernel_banner import one_banner
        banner=one_banner(Path(result['products']['candidate']['kernel']).read_bytes()).decode();assert identity in banner and old_identity not in banner
        result.update(state='0342-linked-exact337-baseline-and-one-driver-diagnostic-replacement',
            baseline_raw_and_stripped_equal_except_LC_UUID=True,identity=identity,kernel_banner=banner,
            parent_manifest=str(parent_path),source_union=dict(base=str(base),overlay=str(source),entries=entries),
            changed_from337=changed,actual_implementation_object_replacements=1,version_change_only_identity=True,
            created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hardware_qualified=False)
    except BaseException as error:result.update(state='0342-kernel-relink-failed',error=repr(error));raise
    finally:result['inputs_unchanged']=all(sha(p)==h for p,h in pins.items());save()
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','steps','source_union')},indent=2))
if __name__=='__main__':main()
