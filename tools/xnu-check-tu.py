#!/usr/bin/env python3
"""Compile selected C/IOKit C++ candidates with a successful native recipe.

Checks the current generated-header provenance, obtains real clang/clang++
commands with make -n, and writes ONLY into a fresh ignored output directory.
Each --file is relative to the candidate tree; unchanged files may be copied
there to see a changed adjacent private header. No link or hardware claim.
"""
import argparse,hashlib,json,os,shlex,struct,subprocess
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--candidate-root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--file',action='append',required=True)
    args=ap.parse_args();manifest_path=args.manifest.resolve();ref=json.loads(manifest_path.read_text())
    assert ref['state']=='built' and ref['make_exit']==0 and ref['machine']=='gauguin' and ref['configuration']=='DEVELOPMENT'
    source=Path(ref['source']['path']);build=Path(ref['build_root']);candidate=args.candidate_root.resolve();out=args.out.resolve()
    repo=Path(__file__).resolve().parent.parent
    assert out.is_relative_to(repo/'research/tmp') or out.is_relative_to(repo/'.deps-cache')
    out.mkdir(parents=True,exist_ok=False)
    checked=0
    for name,kind,pin in ref['source']['entries']:
        if kind!='symlink' and (name.endswith(('.h','.defs')) or name.startswith(('config/','makedefs/'))):
            assert sha(source/name)==pin,('stale header/config context',name)
            checked+=1
    candidates=[p for p in candidate.rglob('*') if p.is_file()]
    pins={str(p):sha(p) for p in [manifest_path,Path(__file__).resolve(),*candidates]}
    env=dict(os.environ,SDKROOT_RESOLVED=ref['sdk']['path'],HOST_SDKROOT_RESOLVED=ref['host_sdk']['path'],
        SDKVERSION=ref['environment']['SDKVERSION'],PLATFORM='MacOSX')
    for key in ('MAKEFLAGS','MFLAGS','MAKELEVEL','MAKEOVERRIDES'):env.pop(key,None)
    obj=build/'obj-gauguin-macos';records=[];protected={};recipes={}
    result={'state':'starting','reference_manifest':str(manifest_path),'reference_sha256':sha(manifest_path),
        'header_config_inputs':checked,'input_pins':pins,'results':records,'hardware_qualified':False}
    def save():
        result['inputs_unchanged']=all(sha(Path(p))==pin for p,pin in pins.items())
        result['reference_files_unchanged']=all((sha(Path(p)),Path(p).stat().st_mtime_ns)==state for p,state in protected.items())
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    try:
        for number,name in enumerate(args.file):
            path=candidate/name;assert path.is_file() and not Path(name).is_absolute() and '..' not in Path(name).parts
            language='c++' if path.suffix=='.cpp' else 'c';assert language=='c++' or path.suffix=='.c'
            component_name='iokit' if language=='c++' else 'bsd'
            component=obj/f'DEVELOPMENT_ARM64_GAUGUIN/{component_name}/DEVELOPMENT'
            target='SweetSurface.cpo' if language=='c++' else 'sweet_touch.o'
            baseline='iokit/Kernel/arm/SweetSurface.cpp' if language=='c++' else 'bsd/dev/sweet_touch.c'
            makefile=component/'Makefile'
            assert makefile.read_text().splitlines()[0]=='SOURCE_DIR='+str(source),'generated makefile belongs to another recipe'
            if language not in recipes:
                for leaf in ('Makefile','.CFLAGS','.CXXFLAGS',target,target.rsplit('.',1)[0]+'.d','meta_features.h'):
                    p=component/leaf
                    if p.is_file():protected[str(p)]=(sha(p),p.stat().st_mtime_ns)
                dry_args=['/usr/bin/make','-n','-f',str(makefile),target,f'SRCROOT={source}',f'SOURCE_DIR={source}',
                    f'SOURCE={source}/',f'OBJROOT={obj}',f'SYMROOT={build}/sym-gauguin-macos',f'DSTROOT={out}/unused-install',
                    f'OBJPATH={component}',f'TARGET={component}',f'RELATIVE_SOURCE_PATH={component_name}',
                    'CURRENT_KERNEL_CONFIG=DEVELOPMENT','CURRENT_ARCH_CONFIG=ARM64','CURRENT_MACHINE_CONFIG=GAUGUIN',
                    'CURRENT_BUILD_CONFIG=DEVELOPMENT^ARM64^GAUGUIN','BUILD_WERROR=0','BUILD_LTO=0','VERBOSE=YES','CONCISE=0','KDKROOT=',
                    'RC_DARWIN_KERNEL_VERSION='+ref['environment']['RC_DARWIN_KERNEL_VERSION']]
                dry=subprocess.run(dry_args,cwd=component,env=env,text=True,capture_output=True)
                (out/f'{component_name}-make-dryrun.log').write_text(dry.stdout+'\n'+dry.stderr)
                assert dry.returncode==0,('make dry-run',component_name,dry.returncode)
                commands=[]
                for line in dry.stdout.splitlines():
                    if str(source/baseline) not in line or ' -c ' not in line:continue
                    words=shlex.split(line)
                    if words and Path(words[0]).name in ('clang','clang++'):commands.append(words)
                assert len(commands)==1,('expected one genuine compile command',language,len(commands))
                recipes[language]=(commands[0],baseline,component)
            template,baseline,cwd=recipes[language];command=template.copy()
            original=str(source/baseline);assert command.count(original)==1
            command[command.index(original)]=str(path)
            for flag in ('-MF','-o','-MJ'):
                while flag in command:
                    index=command.index(flag);del command[index:index+2]
            object_path=out/(str(number)+'-'+path.stem+'.o')
            command[1:1]=['-I',str(candidate/'iokit')]
            command+=['-I',str(candidate/'bsd/dev'),'-I',str(source/'bsd/dev'),
                '-MF',str(object_path.with_suffix('.d')),'-o',str(object_path)]
            proc=subprocess.run(command,cwd=cwd,env=env,text=True,capture_output=True)
            (out/(str(number)+'-'+path.stem+'.log')).write_text(proc.stdout+proc.stderr)
            row={'file':name,'language':language,'arguments':command,'cwd':str(cwd),'exit':proc.returncode}
            records.append(row);save()
            assert proc.returncode==0,('compile failed',name,proc.returncode)
            header=struct.unpack('<8I',object_path.read_bytes()[:32]);assert header[:2]==(0xfeedfacf,0x100000c) and header[3]==1
            row.update(object=str(object_path),object_sha256=sha(object_path),object_bytes=object_path.stat().st_size)
        result['state']='passed-native-ARM64-selected-TUs';save()
        assert result['inputs_unchanged'] and result['reference_files_unchanged']
    except Exception as e:result.update(state='failed',error=repr(e));save();raise
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','results')},indent=2))
if __name__=='__main__':main()
