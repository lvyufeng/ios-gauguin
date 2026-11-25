#!/usr/bin/env python3
"""Recheck the native render anchors and compile the identity-only XNU adapter."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-401'
ADMISSION = (MAIN/'research/tmp/gauguin-frame400-staged-blank-worktree-20261123'
            /'research/tmp/frame-400/ownership-development-admission.json')
RAW = (MAIN/'research/tmp/gauguin-native-ca-trace-worktree-20261122/research/tmp'
       /'frame-374/native-source-check.json')
P393 = MAIN/'research/tmp/gauguin-frame393-ca-members-worktree-20261123/research/tmp/frame-393'
CONTROL = P393/'native-kernel/build-manifest.json'
ROOT = WORK/'graphics/gauguin-ca-timeline'
NAMES = {
    'RenderProducer401.h':'gauguin_render_producer401.h',
    'KernelProducer401.h':'gauguin_kernel_producer401.h',
}


def inspect_native_sites():
    source = load(RAW)
    require(source['uuid']=='9e40b2eb260c3af1ae45a1a551a8c1b9','native CA cache UUID differs')
    render, = (entry for symbol,entry in source['trace_sites'].items() if 'render_for_time' in symbol)
    by_site = {int(site['call'],16):{int(address,16):instruction for address,instruction in site['instructions']}
               for site in render['sites']}
    begin = by_site[0x1884f4f38]
    end = by_site[0x1884f6b78]
    require([begin[p] for p in (0x1884f4f24,0x1884f4f28)]==['mov\tw0, #0xd','movk\tw0, #0x31ca, lsl #16'] and
            [end[p] for p in (0x1884f6b60,0x1884f6b64,0x1884f6b68)]==
            ['mov\tw8, #0xd','movk\tw8, #0x31ca, lsl #16','add\tw0, w8, #0x1'] and
            begin[0x1884f4f38].startswith('bl\t') and end[0x1884f6b78].startswith('bl\t'),
            'native begin/end debug site instructions differ')
    return dict(begin_return_pc=0x1884f4f3c,end_return_pc=0x1884f6b7c,cache_uuid=source['uuid'])


def patch_kdebug(source):
    old = '#include "../dev/gauguin_frame385_observer.h"'
    marker = 'f375_record_at(kind, uap->arg1, uap->arg2, uap->arg3, uap->arg4, tick);'
    require(source.count(old)==source.count(marker)==1,'native CA observer anchors differ')
    return source.replace(old,old+'\n#include "../dev/gauguin_kernel_producer401.h"').replace(
        marker,marker+'\n\t\tf401_native_render(identity, kind, tick);')


def verify():
    admission = load(ADMISSION)
    require(admission['admitted'] and admission['planned_batch_bytes']==238_000_000,
            '0401 source worktree and active 0399 reservation exceed the budget')
    sites = inspect_native_sites()
    original = load(CONTROL)
    source = Path(original['source'])
    old = source/'bsd/kern/kdebug.c'
    recipe, = (entry for entry in original['steps'] if entry.get('name')=='compile-kdebug' and entry['exit']==0)
    with TemporaryDirectory(prefix='401-callback-',dir=BASE) as name:
        stage = Path(name)
        existing = [str(path.relative_to(source)) for path in (source/'bsd/dev').glob('*.h')]
        import_module('build-frame345').stage_source(source,stage,existing)
        for input_name,output in NAMES.items():
            (stage/'bsd/dev'/output).write_bytes((ROOT/input_name).read_bytes())
        unit = stage/'bsd/kern/kdebug.c'
        unit.parent.mkdir(parents=True)
        unit.write_text(patch_kdebug(old.read_text()))
        command = recipe['argv'].copy()
        command[0] = '/Library/Developer/CommandLineTools/usr/bin/clang'
        command[command.index(str(old))] = str(unit)
        command[command.index('-o')+1] = str(stage/'kdebug.o')
        command[command.index('-MF')+1] = str(stage/'kdebug.d')
        result = subprocess.run(command,cwd=recipe['cwd'],capture_output=True,timeout=60)
        (BASE/'compile-callback.log').write_bytes(result.stdout+result.stderr)
        require(result.returncode==0,'0401 callback did not compile: '+result.stderr[-1800:].decode(errors='replace'))
    return dict(state='0401-exact-CA-producer-callback-cross-compiled',sites=sites,device_commands=0,
                input_pins={str(path):sha(path) for path in (ADMISSION,RAW,CONTROL,old,*(ROOT/p for p in NAMES))})


if __name__=='__main__':
    print(json.dumps(verify(),indent=2))
