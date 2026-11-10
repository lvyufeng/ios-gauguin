#!/usr/bin/env python3
"""Assemble the desktop candidate locally; never install or access a phone."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,plistlib,shutil,struct,subprocess,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mkpayload import BOOT_LINE_LENGTH,encode_cmdline

SOURCE='2e62225c17d0886bdd018a13fd1e958f9def5c8dabc7f888e07a79f7da6ca80f'
HASHES=dict(core='8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1',
            frontend='b7fcc72fc69a0ed429effecdf1b6b1ef071bc17a582832a32c3f95b52ea56acc',
            retained='26d09095687544b44af83232fd850c8d8c0d2149a7c17b87b7a0500b697bca3b',
            bootstrap='2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c',
            router='a32f77cbbac5583fb681c037ab77cb2f16e304dc85006e5762bf3da1ab96c101')
ROOT_JOB='/System/Library/LaunchDaemons/org.gauguin.gpu-probe.plist'
BBS_JOB='/System/Library/LaunchDaemons/com.apple.backboardd.plist'
CACHE='/System/Library/xpc/launchd.plist'
BUNDLE='/System/Library/Extensions/GauguinMetalDesktop.bundle'
MOBILE_CACHE='/private/var/mobile/Library/Caches/gauguin-metal244'

def need(value,message):
    if not value:raise ValueError(message)
def sha(p):
    with Path(p).open('rb')as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def regular(p):
    p=Path(p);need(p.is_file()and not p.is_symlink(),'regular file required: '+str(p));return p
def read_proofs(recipe):
    need(recipe['schema']==249 and set(recipe['receipts'])=={
        'core','frontend','retained','bootstrap','router','launch','system','kernel','base','base_acceptance'},'recipe schema/receipts')
    proofs={};pins={}
    for name,row in recipe['receipts'].items():
        p=regular(row['path']).resolve();need(sha(p)==row['sha256'],'receipt digest: '+name)
        x=json.loads(p.read_text());proofs[name]=x;pins[str(p)]=sha(p)
        for n,h in x.get('input_pins',{}).items():
            need(Path(n).is_file()and sha(n)==h,'stale native input: '+n);pins[str(Path(n).resolve())]=h
    return proofs,pins
def boot_profile(base):
    need(base['image_sha256']=='7357a0abf1894969d1b67b2000fcf2e1e928adb2583bf02bb9850cfea6b99956','physical239 base image')
    command=base['command'];need(len(command.encode())==base['command_bytes']==607,'qualified base command')
    # The exact desktop selectors enable held frames and the phase clock in
    # the paired kernel. Keep board/health tokens within the unchanged ABI.
    words=command.split();overrides=dict(sweet_dyld_probe=1,sweeteagl=2,gmt=2,sweetfb_hz=60)
    key=lambda word:word.split('=',1)[0]
    kept=[word for word in words if key(word)not in overrides]
    result=kept+[name+'='+str(value)for name,value in overrides.items()]
    for name,value in overrides.items():need(result.count(name+'='+str(value))==1,'duplicate desktop argument')
    result=' '.join(result);need(0<len(encode_cmdline(result))<BOOT_LINE_LENGTH,'bounded boot arguments')
    need([word for word in result.split()if key(word)not in overrides]==kept,'board arguments changed')
    return result,overrides
def macho(p):
    b=regular(p).read_bytes();need(len(b)>=32,'truncated Mach-O')
    h=struct.unpack_from('<8I',b);need(h[0]==0xfeedfacf and h[1]==0x100000c,'ARM64 Mach-O required')
    need(32+h[5]<=len(b)and h[4]<=4096,'load-command bounds')
    at=32;deps=[];rpaths=[];identity=[];platform=[]
    for _ in range(h[4]):
        cmd,n=struct.unpack_from('<II',b,at);need(n>=8 and at+n<=32+h[5],'command bounds')
        if cmd in [0xc,0xd,0x80000018,0x8000001f,0x80000023,0x8000001c]:
            need(n>=12,'string command bounds');off=struct.unpack_from('<I',b,at+8)[0]
            need(12<=off<n,'string offset');end=b.find(b'\0',at+off,at+n);need(end>=0,'unterminated install name')
            s=b[at+off:end].decode()
            (identity if cmd==0xd else rpaths if cmd==0x8000001c else deps).append(s)
        if cmd==0x32:
            need(n>=24,'build-version bounds');platform.append(struct.unpack_from('<II',b,at+8))
        at+=n
    need(at==32+h[5],'load-command total')
    return dict(filetype=h[3],dependencies=deps,rpaths=rpaths,identity=identity,platform=platform)
def validate_contract(x,repo):
    boot_profile(x['base'])
    need(x['base_acceptance']['state']=='accepted239-root-only-five-task-RO-inputs-after-original-VA-release'and
         x['base_acceptance']['observer_exit']==0 and x['base_acceptance']['input_RO_hardware_qualified'],'physical base acceptance')
    for name in HASHES:
        need(x[name]['sha256']==HASHES[name],'qualified binary identity: '+name)
    need(x['core']['state']=='linked-iOS16-A619-Metal-core-with-AIR-NIR-IR3','core state')
    f=x['frontend'];need(f['desktop_candidate']and not f['diagnostic_root_only'],'desktop frontend')
    need(f['discovery_install']==dict(bundle=BUNDLE,MetalPluginName='GauguinMetalDesktop',
        MetalPluginClassName='GauguinDesktopMetalDevice'),'discovery contract')
    need(f['core_sha256']==HASHES['core']and f['cache']==MOBILE_CACHE,'frontend core/cache')
    need(f['pipeline_cache']==MOBILE_CACHE+'/pipelinelib','private pipeline cache')
    b=x['bootstrap'];need(b['expected_jobs']==8 and b['alarm_seconds']==30 and b['initial_delay_seconds']==0,'finite bootstrap')
    need(b['required_kernel_selector']==0x7c and b['requires_clean_armed_owner_close'],'bootstrap wire')
    need(b['core_sha256']==HASHES['core'],'bootstrap core')
    targets={z['kind']:z for z in x['router']['targets']}
    for kind,path,arg,digest in [
        ('retained','/usr/libexec/gauguin-metal-frontend-probe','--metal230',HASHES['retained']),
        ('bootstrap','/usr/libexec/gauguin-metal-bootstrap','--bootstrap245',HASHES['bootstrap'])]:
        need(targets[kind]['path']==path and targets[kind]['argument']==arg and targets[kind]['sha256']==digest,'SETEXEC target')
    need(x['router']['requires_0240_installed'],'0240 prerequisite')
    launch=x['launch'];need(launch['state']=='local-desktop-launch-plists-not-volume-or-installation','launch template state')
    need(launch['total_jobs']==531 and launch['unchanged_jobs']==529 and launch['all_labels_preserved'],'launch scope')
    need(launch['retained_admission_marker']and launch['root_memory_policy_label']=='org.gauguin.gpu-probe','fallback/memory label')
    need(launch['router_sha256']==HASHES['router']and set(launch['files'])=={ROOT_JOB,BBS_JOB,CACHE},'launch router/files')
    need(len(launch['preserved_policy_files'])==2 and not launch['volume_staged'],'policy preservation/local only')
    values={}
    for dest,row in launch['files'].items():
        p=regular(row['path']);need(sha(p)==row['sha256']and p.stat().st_size==row['bytes'],'launch file identity')
        need(row['target_uid']==row['target_gid']==0 and row['target_mode']==0o100644,'launch target metadata')
        values[dest]=plistlib.loads(p.read_bytes())
    need(values[ROOT_JOB]['ProgramArguments']==['/usr/libexec/gauguin-gpu-probe-router','--route247'],'root argv')
    env=values[BBS_JOB]['EnvironmentVariables']
    need('DYLD_INSERT_LIBRARIES'not in env and env['GAUGUIN_EAGL_MODE']=='admission','desktop/fallback environment')
    jobs=values[CACHE]['LaunchDaemons'];need(len(jobs)==531,'cache job count')
    need(jobs[ROOT_JOB]==values[ROOT_JOB],'cached root job')
    need('DYLD_INSERT_LIBRARIES'not in jobs[BBS_JOB]['EnvironmentVariables'],'cached desktop environment')
    need(jobs[BBS_JOB]['EnvironmentVariables']['GAUGUIN_EAGL_MODE']=='admission','cached fallback marker')
    system=x['system'];need(system['state']=='readonly-system-prerequisites-from-verified-pre240-backup'and system['OS_build']=='20H392','system contract')
    q='/System/Library/Frameworks/QuartzCore.framework/default.metallib'
    need(system['files'][q]['bytes']==1014944 and system['files'][q]['sha256']=='11c74cc42ce5137b73d44d427f75764f886656d4ddb374422d56b609ed2762d9','matched QuartzCore library')
    for suffix,size,digest in [('functions',3587004,'630a35690da4d48f6d88e99a136035d38cedfac745237b911e66ce64b5ee18e9'),
                               ('pipelines.desc',1593060,'a6a43ffb97c3461389c71437d5dd16e42fa2ac3f3ed826340c3802407bda27bb')]:
        row=system['files']['/System/Library/Frameworks/QuartzCore.framework/default.pipelinelib/'+suffix]
        need(row['present']and row['uid']==row['gid']==0 and row['bytes']==size and row['sha256']==digest,'matched pipeline assets')
    parent=system['files']['/private/var/mobile/Library/Caches']
    need(parent['present']and parent['uid']==parent['gid']==501 and parent['mode']&0o300==0o300,'writable mobile cache parent')
    need(system['fresh_post240_capture_required'],'fresh post240 system check')
    k=x['kernel'];need(k['state']=='qualified-native249-complete-desktop-candidate-not-phone-qualified','complete kernel qualification')
    need(k['source_sha256']==SOURCE and k['source_files']==5332 and k['active_patches']==206,'kernel source identity')
    need(k['make_exit']==0 and k['final_kernel_produced']and k['build_inputs_verified']and k['sdk_recorded_inputs_verified'],'kernel provenance')
    kp=repo/k['kernel_path'];need(kp.resolve().is_relative_to(repo.resolve()),'repository-local kernel')
    need(sha(regular(kp))==k['kernel_sha256']and kp.stat().st_size==k['kernel_bytes'],'kernel identity')
    return values
def assemble(recipe_path,out):
    repo=Path(__file__).resolve().parents[1];recipe_path=regular(recipe_path).resolve()
    recipe=json.loads(recipe_path.read_text());x,pins=read_proofs(recipe);validate_contract(x,repo)
    need(not out.exists()and out.resolve().is_relative_to(repo/'research/tmp'),'fresh private output required')
    paths=dict(core=Path(x['core']['library']),frontend=Path(x['frontend']['binary']),
               retained=Path(x['retained']['probe']),bootstrap=Path(x['bootstrap']['binary']),router=Path(x['router']['binary']))
    destinations=dict(core='/usr/local/lib/gauguin/libGauguinMetalCore.dylib',frontend=BUNDLE+'/GauguinMetalDesktop',
        retained='/usr/libexec/gauguin-metal-frontend-probe',bootstrap='/usr/libexec/gauguin-metal-bootstrap',router='/usr/libexec/gauguin-gpu-probe-router')
    loads={}
    for name,p in paths.items():
        need(sha(regular(p))==HASHES[name],'binary bytes: '+name)
        row=macho(p);need(row['filetype']==(6 if name=='core'else 8 if name=='frontend'else 2),'Mach-O type')
        need(row['platform']==[(2,16<<16)],'native iOS16 platform')
        if name=='core':need(row['identity']==['@rpath/libGauguinMetalCore.dylib'],'core install name')
        for dependency in row['dependencies']:
            if dependency.startswith('@rpath/'):
                need(dependency=='@rpath/libGauguinMetalCore.dylib'and '/usr/local/lib/gauguin'in row['rpaths'],'private dependency resolution')
            else:need(dependency.startswith(('/System/Library/','/usr/lib/')),'unexpected dependency')
        loads[name]=row
    bundle=paths['frontend'].parent
    info=plistlib.loads(regular(bundle/'Info.plist').read_bytes())
    need(info['CFBundleExecutable']=='GauguinMetalDesktop'and info['NSPrincipalClass']=='GauguinDesktopMetalDevice','bundle class/executable')
    subprocess.run(['codesign','--verify','--strict',str(bundle)],check=True,capture_output=True)
    for name in ['core','retained','bootstrap','router']:
        subprocess.run(['codesign','--verify','--strict',str(paths[name])],check=True,capture_output=True)
    out.mkdir(parents=True,exist_ok=False);files={}
    def copy_file(source,dest,mode):
        path=PurePosixPath(dest);need(path.is_absolute()and '..'not in path.parts and dest not in files,'target path collision')
        target=out/'root'/str(path).lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(regular(source),target);target.chmod(mode)
        need(sha(target)==sha(source),'copy identity');pins[str(Path(source).resolve())]=sha(source)
        files[dest]=dict(path=str(target),bytes=target.stat().st_size,sha256=sha(target),target_uid=0,target_gid=0,target_mode=0o100000|mode)
    for name,p in paths.items():copy_file(p,destinations[name],0o755)
    copy_file(bundle/'Info.plist',BUNDLE+'/Info.plist',0o644)
    copy_file(bundle/'_CodeSignature/CodeResources',BUNDLE+'/_CodeSignature/CodeResources',0o644)
    subprocess.run(['codesign','--verify','--strict',str(out/'root'/BUNDLE.lstrip('/'))],check=True,capture_output=True)
    directory=out/'root'/MOBILE_CACHE.lstrip('/');directory.mkdir(parents=True);directory.chmod(0o700)
    (directory/'pipelinelib').mkdir();(directory/'pipelinelib').chmod(0o700)
    templates={}
    for dest,row in x['launch']['files'].items():
        target=out/'launch-templates'/dest.lstrip('/');target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(row['path'],target)
        templates[dest]=dict(path=str(target),sha256=sha(target),requires_post240_regeneration=True)
    kernel_source=repo/x['kernel']['kernel_path'];kernel=out/'kernel/kernel.development.gauguin'
    kernel.parent.mkdir();shutil.copyfile(kernel_source,kernel);pins[str(kernel_source)]=sha(kernel_source)
    pins[str(recipe_path)]=sha(recipe_path);pins[str(Path(__file__).resolve())]=sha(Path(__file__).resolve())
    need(all(sha(n)==h for n,h in pins.items()),'inputs changed during assembly')
    command,overrides=boot_profile(x['base'])
    result=dict(state='complete-local-desktop-candidate-not-volume-or-phone-qualified',files=files,
        directories={MOBILE_CACHE:dict(target_uid=501,target_gid=501,target_mode=0o40700),
                     MOBILE_CACHE+'/pipelinelib':dict(target_uid=501,target_gid=501,target_mode=0o40700),
                     BUNDLE:dict(target_uid=0,target_gid=0,target_mode=0o40755),
                     BUNDLE+'/_CodeSignature':dict(target_uid=0,target_gid=0,target_mode=0o40755)},
        kernel=dict(path=str(kernel),bytes=kernel.stat().st_size,sha256=sha(kernel),source_sha256=SOURCE,build_head=x['kernel']['committed_head']),
        dependencies=loads,launch_templates=templates,system_prerequisites=x['system'],
        software_boot_argument_overrides=overrides,command=command,command_bytes=len(command.encode()),
        physical_base_image_sha256=x['base']['image_sha256'],
        requires_deduplicated_boot_key_replacement=True,qualified_board_arguments_must_be_preserved=True,
        parent_directory_metadata_must_be_preserved=True,payload_owner_is_not_installation_owner=True,physical_refresh_qualified=False,
        requires_0240_installed_and_paired_trial=True,requires_fresh_post240_capture=True,
        existing_logs_and_unrelated_jobs_must_be_preserved=True,volume_staged=False,installation_ready=False,
        installed=False,hardware_qualified=False,device_commands=0,input_pins=pins,inputs_unchanged=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items()if k in ['state','kernel','requires_fresh_post240_capture','volume_staged','installation_ready','hardware_qualified']},indent=2))
    return result
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--recipe',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args();assemble(a.recipe,a.out.resolve())
if __name__=='__main__':main()
