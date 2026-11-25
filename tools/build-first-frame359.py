#!/usr/bin/env python3
"""Build the SpringBoard first-frame observer for the existing iOS slot."""

import ast
import bisect
import hashlib
from importlib import import_module
import json
from pathlib import Path
import plistlib
import struct
import subprocess
import sys

from frame359_scope import BASE, MAIN, P358, WORK, load, require, sha

DEVELOPER = Path('/Applications/Xcode.app/Contents/Developer')
CLANG = DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
SDK = DEVELOPER/'Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk'


def verify_imports(binary, *, additional_imports=None):
    prior = import_module('build-sb-queue337')
    script = prior.OLD/'qualify_stack_abi.py'
    original = prior.OLD/'abi-v3/result.json'
    previous = load(original)
    require(sha(script)==previous['script_sha256'],'pinned iOS export reader differs')
    manifest = MAIN/'research/tmp/metal-hardware-20261112/backup/result.json'
    backup = load(manifest)
    image = Path(backup['backup'])
    require(sha(image)==backup['backup_sha256']==previous['backup_sha256'],'20H392 backup identity differs')
    inventory_path = MAIN/'research/tmp/dsh-gles-ui-0183/offline-resolved-cache-inventory.json'
    sys.path.insert(0,str(MAIN/'research/tmp/dsh-0175'))
    from local_hfs175v3 import HFS
    volume = HFS(image)
    try:
        version = plistlib.loads(volume.content('/System/Library/CoreServices/SystemVersion.plist'))
        require(version['ProductBuildVersion']=='20H392','wrong runtime build')
        text = script.read_text()
        reader = text[text.index('def forkread'):text.index('probe=Path')]
        tools = dict(h=volume,inventory=load(inventory_path),struct=struct,bisect=bisect,hashlib=hashlib)
        exec(compile(ast.parse(reader),str(script),'exec'),tools)
        require(tools['shards']==previous['cache_shards'],'runtime dyld cache shards differ')
        resolved = []
        for row in tools['native'](binary)['imports']:
            answer = tools['resolve'](row['provider'],row['symbol'])
            require(answer,'unresolved iOS import '+row['symbol'])
            resolved.append(dict(row,resolution=answer))
        added = set(prior.imports(binary))-{(r['symbol'],r['provider'],r['weak']) for r in previous['imports']}
        if additional_imports is None:
            additional_imports = {('_class_getClassMethod','/usr/lib/libobjc.A.dylib',False),
                                  ('_usleep','/usr/lib/libSystem.B.dylib',False)}
        require(added==additional_imports,'unexpected observer import change')
    finally:
        volume.close()
    pins = {str(path):sha(path) for path in (script,original,manifest,inventory_path)}
    pins[str(image)] = backup['backup_sha256']
    return resolved,pins


def main():
    admission = load(BASE/'build-storage-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']>=340_000_000,'whole batch admission is missing')
    source = WORK/'graphics/gauguin-sb-rate-trace/SBRateTrace.m'
    baseline = load(P358/'slot-delta/install-plan.json')['rows']['eagl']
    pins = {str(p):sha(p) for p in (Path(__file__),source,*sorted(source.parent.glob('SB*.h')),
            SDK/'SDKSettings.json',CLANG,P358/'slot-delta/install-plan.json')}
    out = BASE/'sb-native'
    out.mkdir()
    binary = out/'libGauguinSBRateTrace.dylib'
    argv = [str(CLANG),'-target','arm64-apple-ios16.0','-isysroot',str(SDK),'-DGAUGUIN_SB_FIRST_FRAME=1',
            '-std=gnu11','-O2','-fno-objc-arc','-Wall','-Wextra','-Werror','-dynamiclib','-framework',
            'Foundation','-framework','QuartzCore','-framework','UIKit','-lobjc',
            '-Wl,-install_name,'+baseline['path'],str(source),'-o',str(binary)]
    for name,cmd in [('compile',argv),('sign',['codesign','--force','--sign','-',str(binary)]),
                     ('verify',['codesign','--verify','--strict',str(binary)]),
                     ('loads',['otool','-L',str(binary)])]:
        with (out/(name+'.log')).open('x') as log:
            subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    core = import_module('build-hakios-metal')
    require(baseline['path'] in (out/'loads.log').read_text() and binary.stat().st_size<=94_208 and
            binary.stat().st_size<=baseline['data_blocks']*4096,'observer exceeds its reviewed slot')
    imports,abi_pins = verify_imports(binary)
    require(all(sha(path)==value for path,value in pins.items()),'observer source or compiler changed')
    result = dict(state='0359-first-frame-observer-signed',binary=str(binary),binary_sha256=sha(binary),
                  bytes=binary.stat().st_size,compiler_argv=argv,platform=core.ios_version(binary),
                  install_name=baseline['path'],signature_verified=True,runtime_imports_qualified=True,
                  imports=imports,inputs_unchanged=True,input_pins=pins|abi_pins,device_commands=0)
    with (out/'result.json').open('x') as handle:
        json.dump(result,handle,indent=2)
        handle.write('\n')
    return {k:v for k,v in result.items() if k not in ('input_pins','compiler_argv','imports')}


if __name__=='__main__':
    print(json.dumps(main(),indent=2))
