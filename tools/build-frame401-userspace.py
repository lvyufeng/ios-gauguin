#!/usr/bin/env python3
"""Sign matching Core and C4 builds for the exact in-render producer cookie."""

from importlib import import_module
import json
from pathlib import Path
import re
import shutil
import subprocess

from frame366_scope import MAIN, load, require, sha

stage = import_module('stage-frame401-producer')
core_tools = import_module('check-frame389-core')
front_tools = import_module('build-frame399-frontend')
BASE = stage.BASE
P394 = MAIN/'research/tmp/gauguin-frame394-compositor-qos-worktree-20261123/research/tmp/frame-394'
CORE_CONTROL = P394/'core-native/result.json'
C4_CONTROL = stage.P400/'c4-native/result.json'
EXPORT = '_hakios_metal_cb_bind_display_producer401'


def save(path, data):
    with path.open('x') as f:
        json.dump(data,f,indent=2)
        f.write('\n')


def symbols(path, *options):
    return set(subprocess.check_output([str(front_tools.VERIFY_TOOLS/'nm'),*options,str(path)],
        text=True,timeout=30).splitlines())


def dependencies(path):
    return subprocess.check_output([str(front_tools.VERIFY_TOOLS/'otool'),'-L',str(path)],
        text=True,timeout=30).splitlines()[1:]


def build_core():
    receipt = load(CORE_CONTROL)
    baseline = Path(receipt['binary'])
    require(sha(baseline)==receipt['binary_sha256'] and all(
        sha(path)==digest for path,digest in receipt['input_pins'].items()),'0394 Core control differs')
    original = Path(load(core_tools.BASE346/'result.json')['source'])
    recipe = load(core_tools.BASE346/'result.json')
    out = BASE/'core-native'
    out.mkdir()

    def arguments(label):
        step, = (row for row in recipe['steps'] if row['name']==label and row['exit']==0)
        args = list(step['argv'][4:])
        args[args.index('-isysroot')+1] = str(core_tools.IOS_SDK)
        return args

    path_c = baseline.parent/'source/src/c_api.cpp'
    path_gpu = original/'src/gpu.cpp'
    header = stage.ROOT/'ProducerTransport401.h'
    require(sha(path_c)==receipt['input_pins'][str(path_c)] and sha(path_gpu)==recipe['source_pins']['src/gpu.cpp'],
        'Core producer inputs differ')
    origins = {'c_api':(path_c,stage.core_binding), 'gpu':(path_gpu,stage.submit_binding)}
    pins = {p:sha(p) for p in (Path(__file__),Path(stage.__file__),stage.DEVELOPMENT,CORE_CONTROL,baseline,
        core_tools.BASE346/'result.json',path_c,path_gpu,header,baseline.parent/'c_api.o')}
    for unit,(before, transform) in origins.items():
        after = out/before.name
        after.write_text(transform(before.read_text()))
        args = arguments('compile-'+unit)
        args[args.index(str(original/'src'/before.name))] = str(after)
        args[args.index('-o')+1] = str(out/(unit+'.o'))
        core_tools.run([str(core_tools.IOS_CLANG),'-I'+str(stage.ROOT),'-I'+str(original/'src'),*args],
            out/('compile-'+unit+'.log'))

    previous_objects = core_tools.REFERENCE.parent
    exports = previous_objects/'exports.txt'
    scoped_exports = out/'exports.txt'
    require(EXPORT not in exports.read_text().splitlines(),'0401 producer symbol already exported')
    scoped_exports.write_text(exports.read_text().rstrip()+'\n'+EXPORT+'\n')
    pins[exports] = sha(exports)
    control = out/'reference-relinked.dylib'
    candidate = out/baseline.name
    for binary in (control,candidate):
        args = arguments('link')
        args[args.index('-o')+1] = str(binary)
        for i,arg in enumerate(args):
            if arg.endswith('.o'):
                name = Path(arg).name
                if name in ('c_api.o','gpu.o') and binary==candidate:
                    obj = out/name
                elif name=='c_api.o':
                    obj = baseline.parent/name
                else:
                    obj = previous_objects/('reference-render.o' if name=='render.o' else name)
                args[i] = str(obj)
                pins[obj] = sha(obj)
            elif arg.endswith('.a'):
                pins[Path(arg)] = sha(arg)
            elif arg.startswith('-Wl,-exported_symbols_list,'):
                args[i] = '-Wl,-exported_symbols_list,'+str(exports if binary==control else scoped_exports)
        core_tools.run([str(core_tools.IOS_CLANG),*args],out/(binary.stem+'-link.log'))
        core_tools.run(['xcrun','strip','-x',str(binary)])
        info = core_tools.run(['codesign','-dv',str(baseline)]).stderr
        identifier, = re.findall(rb'^Identifier=(.+)$',info,re.M)
        core_tools.run(['codesign','--force','--sign','-','--identifier',identifier.decode(),str(binary)])
        core_tools.run(['codesign','--verify','--strict',str(binary)])
    require(sha(control)==receipt['binary_sha256'] and 0<candidate.stat().st_size<=2053*4096 and
        symbols(candidate,'-gUj')==symbols(control,'-gUj')|{EXPORT} and
        dependencies(candidate)==dependencies(control),
        '0401 Core reconstruction, extents or exported producer ABI differs')
    result = dict(state='0401-private-producer-Core-signed',binary=str(candidate),bytes=candidate.stat().st_size,
        binary_sha256=sha(candidate),reconstructed_control_sha256=sha(control),signature_verified=True,
        added_symbols=[EXPORT],device_commands=0,input_pins={str(p):digest for p,digest in pins.items()})
    save(out/'result.json',result)
    return result


def build_frontend(core):
    receipt = load(C4_CONTROL)
    control = Path(receipt['binary'])
    recipe = load(front_tools.REFERENCE)
    require(sha(control)==receipt['binary_sha256'] and all(
        sha(p)==digest for p,digest in recipe['input_pins'].items()),'0401 C4 control differs')
    historical, = (row['argv'] for row in recipe['steps'] if row['name']=='candidate-compile' and row['exit']==0)
    source, = (Path(p) for p in historical if p.endswith('/HakiosMetalCA.m'))
    core_arg, = (arg for arg in historical if arg.endswith('/libGauguinMetalCore.dylib'))
    helpers = front_tools.VERIFY_TOOLS
    out = BASE/'c4-native'
    out.mkdir()
    edited = out/source.name
    edited.write_text(stage.frontend_binding(source.read_text()))

    def variant(name, new):
        bundle = out/name/control.parent.name
        bundle.mkdir(parents=True)
        shutil.copyfile(control.parent/'Info.plist',bundle/'Info.plist')
        binary = bundle/control.name
        command = [str(front_tools.CLANG),*historical[4:]]
        command[command.index('-isysroot')+1] = str(front_tools.SDK)
        index = command.index('-o')
        command[index+1] = str(binary)
        command[index:index] = [str(front_tools.PADDING)]
        if new:
            command[command.index(core_arg)] = core['binary']
            index = command.index(str(source))
            command[index:index+1] = ['-I'+str(source.parent),str(edited)]
        for label, argv in (
            ('compile',command),('sign',['codesign','--force','--sign','-',str(bundle)]),
            ('verify',['codesign','--verify','--strict',str(bundle)]),
        ):
            core_tools.run(argv,out/(name+'-'+label+'.log'))
        return binary

    rebuilt = variant('control',False)
    candidate = variant('candidate',True)
    require(sha(rebuilt)==receipt['binary_sha256'] and 104*4096<candidate.stat().st_size<=105*4096 and
        symbols(candidate,'-gUj')==symbols(rebuilt,'-gUj') and
        symbols(candidate,'-ju')==symbols(rebuilt,'-ju')|{EXPORT} and
        dependencies(candidate)==dependencies(rebuilt) and
        all(sha(candidate.parent/name)==sha(control.parent/name) for name in ('Info.plist','_CodeSignature/CodeResources')),
        '0401 C4 signature, extents, dependencies or declared producer ABI differs')
    pins = {str(p):sha(p) for p in (Path(__file__),Path(stage.__file__),C4_CONTROL,front_tools.REFERENCE,source,
        front_tools.PADDING,control,Path(core['binary']),BASE/'core-native/result.json',helpers/'otool',helpers/'nm')}
    result = dict(state='0401-direct-render-target-C4-signed',binary=str(candidate),bytes=candidate.stat().st_size,
        binary_sha256=sha(candidate),source=str(edited),source_sha256=sha(edited),
        reconstructed_control_sha256=sha(rebuilt),strict_signature=True,device_commands=0,input_pins=pins)
    save(out/'result.json',result)
    return result


if __name__=='__main__':
    stage.admit()
    core = build_core()
    frontend = build_frontend(core)
    print(json.dumps({label:{k:v for k,v in result.items() if k!='input_pins'}
                      for label,result in (('Core',core),('C4',frontend))},indent=2))
