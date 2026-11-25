#!/usr/bin/env python3
"""Build native Core and kernel from the qualified 0345 products."""
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
import argparse
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory

from core343_scope import MAIN, WORK, load, require, sha
from kernel_banner import one_banner

helper = import_module('build-frame345')
BASE = WORK / 'research/tmp/frame-346'
P345 = MAIN / 'research/tmp/gauguin-frame-345-worktree-20261119/research/tmp/frame-345'
P344 = helper.P344
P343 = MAIN / 'research/tmp/gauguin-runtime-issue-worktree-20261119/research/tmp/runtime-issue-343'


def core():
    previous = P345 / 'core-native/result.json'
    old = load(previous)
    patch = WORK / 'graphics/gauguin-program-io/0346-program-slabs.patch'
    build = helper.Build(BASE/'core-native','result.json',patch,previous)
    template = P344/'core-native/result.json'
    build.pin(template)
    original = Path(old['binary'])
    build.pin(original,old['binary_sha256'])
    source = Path(old['source'])
    for name,digest in old['source_pins'].items():
        build.pin(source/name,digest)
    helper.stage_source(source,build.source,old['source_pins'])
    build.apply()
    steps = {s['name']:s['argv'] for s in load(template)['steps'] if s['exit']==0}
    previous_link = next(s['argv'] for s in old['steps'] if s['name']=='link')
    objects = [Path(arg) for arg in previous_link if arg.endswith('.o')]
    require(len(objects)==len({p.stem for p in objects})==12,'Core TU scope changed')
    template_source = load(template)['source']
    for path in (arg for arg in previous_link if arg.endswith('.a')):
        build.pin(Path(path),old['input_pins'].get(path))

    def compile_object(path):
        args = [arg.replace(template_source,str(build.source)) for arg in steps['compile-'+path.stem]]
        args[args.index('-o')+1] = str(build.out/path.name)
        build.run('compile-'+path.stem,args)

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(compile_object,objects))
    binary = build.out/original.name
    public = build.run('0345-public-exports',['nm','-gUj',str(original)])
    export_list = build.out/'previous-exports.txt'
    export_list.write_bytes(public)
    link = [str(build.out/Path(arg).name) if arg.endswith('.o') else
            arg.replace(template_source,str(build.source)) for arg in previous_link]
    link[link.index('-o')+1] = str(binary)
    build.run('link',link+['-Wl,-exported_symbols_list,'+str(export_list)])
    build.run('strip',['xcrun','strip','-x',str(binary)])
    build.run('sign',['codesign','--force','--sign','-',str(binary)])
    build.run('verify',['codesign','--verify','--strict',str(binary)])
    for kind,argv in (('imports',['nm','-m','-u']),('exports',['nm','-gUj']),
                      ('loads',['otool','-L']),('platform',['vtool','-show-build'])):
        a = build.run('0345-'+kind,[*argv,str(original)]).splitlines()
        b = build.run('0346-'+kind,[*argv,str(binary)]).splitlines()
        if kind=='exports':
            a,b=set(a),set(b)
        elif kind in ('loads','platform'):
            a,b=a[1:],b[1:]
        require(a==b,'Core ABI differs: '+kind)
    require(original.stat().st_size==7_975_792 and binary.stat().st_size==7_992_224,
            'Core logical length differs from the reviewed descriptor')
    build.finish('0346-native-core-signed',binary=str(binary),bytes=binary.stat().st_size,
                 binary_sha256=sha(binary),source_pins={name:sha(build.source/name) for name in old['source_pins']},
                 matching_imports_exports_loads_and_platform=True,compiled_tus=len(objects))


def kernel():
    previous = P345/'native-kernel/build-manifest.json'
    old = load(previous)
    patch = WORK/'xnu/patches/0256-gauguin-join-ring-and-doorbell-guards.patch'
    clock_patch = WORK/'xnu/patches/0255-gauguin-display-ahb-hardware-gating.patch'
    build = helper.Build(BASE/'native-kernel','build-manifest.json',patch,previous)
    build.pin(clock_patch)
    original = Path(old['kernel'])
    build.pin(original,old['kernel_sha256'])
    source = Path(old['source'])
    names = sorted(str(p.relative_to(source)) for p in source.rglob('*') if p.is_file())
    for name in names:
        build.pin(source/name)
    helper.stage_source(source,build.source,names)
    build.run('apply-hwcg',['patch','-p1','-F','0','-i',str(clock_patch)],build.source)
    build.apply()
    steps = {s['name']:s for s in old['steps'] if s['exit']==0}
    link=steps['0345-link']
    argv=link['argv']
    filelist=Path(argv[argv.index('-filelist')+1])
    build.pin(filelist)
    inputs=filelist.read_text().splitlines()
    for path in inputs:
        build.pin(Path(path),old['input_pins'].get(path))
    version_path=previous.parent/'version.c'
    build.pin(version_path)
    version=version_path.read_text()
    require(version.count(old['identity'])==2,'ambiguous 0345 identity')
    identity='xnu-local346-'+hashlib.sha256((old['kernel_sha256']+sha(clock_patch)+sha(patch)).encode()).hexdigest()[:32]

    def relink(label,command,target):
        with TemporaryDirectory(prefix=label+'-',dir=build.out) as temp:
            raw=str(Path(temp)/'kernel.unstripped')
            command=list(command)
            command[command.index('-o')+1]=raw
            build.run(label+'-link',command,link['cwd'])
            build.run(label+'-strip',['xcrun','strip','-S',raw,'-o',str(target)])
            return sha(raw)

    with TemporaryDirectory(prefix='reproduce-',dir=build.out) as temp:
        reproduced=Path(temp)/'0345.kernel'
        relink('0345',argv,reproduced)
        require(helper.normalized_uuid(reproduced.read_bytes())==helper.normalized_uuid(original.read_bytes()),
                '0345 kernel differs after normalizing LC_UUID')
    runtime_manifest=P343/'kernel-native/build-manifest.json'
    build.pin(runtime_manifest)
    runtime=next(s for s in load(runtime_manifest)['steps'] if s['label']=='candidate-runtime-compile')
    replacements={}
    for record,unit in ((steps['compile-1-gauguin_ui_trace_board'],'gauguin_ui_trace_board'),
                        (runtime,'gauguin_gpu_runtime')):
        args=list(record.get('argv',record.get('arguments')))
        obj=build.out/(unit+'.o')
        previous_obj=args[args.index('-o')+1]
        matches=[i for i,a in enumerate(args) if a.endswith('/'+unit+'.c')]
        require(len(matches)==1 and inputs.count(previous_obj)==1,'kernel object dependency differs: '+unit)
        args[matches[0]]=str(build.source/'bsd/dev'/(unit+'.c'))
        args[args.index('-o')+1]=str(obj)
        if '-MF' in args:
            args[args.index('-MF')+1]=str(obj.with_suffix('.d'))
        build.run('compile-'+unit,args,record['cwd'])
        replacements[previous_obj]=str(obj)
    (build.out/'candidate.filelist').write_text(''.join(replacements.get(p,p)+'\n' for p in inputs))
    (build.out/'version.c').write_text(version.replace(old['identity'],identity))
    step=steps['version']
    build.run('version',[x.replace(str(version_path.with_suffix('')),str(build.out/'version'))
                         for x in step['argv']],step['cwd'])
    candidate=list(argv)
    candidate[candidate.index('-filelist')+1]=str(build.out/'candidate.filelist')
    candidate[candidate.index(str(version_path.with_suffix('.o')))]=str(build.out/'version.o')
    binary=build.out/'candidate.kernel'
    raw= relink('0346',candidate,binary)
    require(not build.run('undefined',['xcrun','nm','-ju',str(binary)]).strip(),'undefined native kernel symbols')
    banner=one_banner(binary.read_bytes()).decode()
    require(identity in banner and old['identity'] not in banner,'native version differs')
    build.finish('0346-native-ARM64-linked',kernel=str(binary),kernel_sha256=sha(binary),
                 kernel_bytes=binary.stat().st_size,unstripped_sha256=raw,identity=identity,kernel_banner=banner,
                 object_replacements=replacements,baseline_reproduced_except_uuid=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('component',choices=('core','kernel'))
    {'core':core,'kernel':kernel}[parser.parse_args().component]()
