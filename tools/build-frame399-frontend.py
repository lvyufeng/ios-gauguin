#!/usr/bin/env python3
"""Build the bounded renderer-target receipt over the deployed C4 control."""

import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import MAIN,WORK,load,require,sha

BASE = WORK/'research/tmp/frame-399'
P398 = MAIN/'research/tmp/gauguin-frame398-renderer-performance-core-worktree-20261123/research/tmp/frame-398'
REFERENCE = (MAIN/'research/tmp/gauguin-io-path-worktree-20261117/research/tmp/io-path-342'
             /'frontend-native-v2/result.json')
PADDING = (MAIN/'research/tmp/gauguin-c4-tail-rescue-worktree-20261121/research/tmp'
           /'c4-full-allocation-reproduced-2/allocation-padding.c')
DEVELOPER = Path('/Applications/Xcode.app/Contents/Developer')
CLANG = DEVELOPER/'Toolchains/XcodeDefault.xctoolchain/usr/bin/clang'
SDK = DEVELOPER/'Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.2.sdk'
VERIFY_TOOLS = Path('/Library/Developer/CommandLineTools/usr/bin')
METHOD = '''- (void)hakiosObserveDisplayTarget399:(HakiosMetalTexture *)texture
{
    if (!texture || !gauguin_async338_scope(_createdAt)) return;
    IOSurfaceRef surface = [texture iosurface];
    if (!surface) return;
    const uint32_t sid = IOSurfaceGetID(surface);
    if (!sid) return;
    uint64_t tid = 0;
    if (pthread_threadid_np(NULL, &tid) || !tid) return;

    bool unique = false;
    for (unsigned i = 0; i < 4; ++i) {
        uint32_t seen = __atomic_load_n(&_observedDisplaySurfaces399[i], __ATOMIC_RELAXED);
        if (!seen && __atomic_compare_exchange_n(&_observedDisplaySurfaces399[i], &seen,
                sid, false, __ATOMIC_RELAXED, __ATOMIC_RELAXED)) {
            unique = true;
            break;
        }
        if (seen == sid) return;
    }
    if (!unique) return;

    static unsigned count;
    unsigned ordinal = __atomic_load_n(&count, __ATOMIC_RELAXED);
    do {
        if (ordinal > 2048u) return;
    } while (!__atomic_compare_exchange_n(&count, &ordinal, ordinal + 1, true,
                                         __ATOMIC_RELAXED, __ATOMIC_RELAXED));
    if (ordinal == 2048u) {
        fprintf(stderr, "GAUGUIN WRITER399: limit=2048\\n");
        return;
    }
    const uint64_t tick = mach_absolute_time();
    const unsigned layout = ([texture hakiosIsTurned] ? 1u : 0u) | ([texture hakiosIsShadow] ? 2u : 0u);
    fprintf(stderr, "GAUGUIN WRITER399: object=%p made=%llu tick=%llu tid=%llu surface=%u layout=%u\\n",
        self, (unsigned long long)gauguin_async338_us(_createdAt), (unsigned long long)tick,
        (unsigned long long)tid, sid, layout);
}

'''


def instrument(source):
    def insert(raw, original, replacement):
        require(raw.count(original) == 1, 'C4 recording anchor differs')
        return raw.replace(original,replacement,1)
    source = insert(source,'#include "GauguinAsync338.h"',
                    '#include "GauguinAsync338.h"\n#include <pthread.h>')
    source = insert(source,'@interface HakiosMetalCommandBuffer : _MTLCommandBuffer {',
                    '@interface HakiosMetalCommandBuffer : _MTLCommandBuffer {\n'
                    '@private\n\tuint32_t _observedDisplaySurfaces399[4];\n@protected')
    at = '- (id)renderCommandEncoderWithDescriptor:(MTLRenderPassDescriptor *)descriptor\n{'
    source = insert(source,at,METHOD+at)
    at = '\t\t[encoder hakiosTakeResolves:descriptor];   /* hm_read_render_pass judged them */\n\t\treturn encoder;'
    source = insert(source,at,at.replace('\t\treturn encoder;',
                     '\t\tif (encoder) [self hakiosObserveDisplayTarget399:texture];\n\t\treturn encoder;'))
    at = ('\treturn [[[HakiosMetalParallelRenderCommandEncoder alloc] initWithHakiosCommandBuffer:self pass:&pass '
          'colorTexture:texture\n\t\t\t\t\t\t\t\t\t\t\tdescriptor:descriptor] autorelease];')
    source = insert(source,at,at.replace('\treturn [[[', '\tHakiosMetalParallelRenderCommandEncoder *encoder = [[[')
                    +'\n\tif (encoder) [self hakiosObserveDisplayTarget399:texture];\n\treturn encoder;')
    return source


def build():
    budget = load(BASE/'frontend-development-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==218_000_000 and
            budget['current_accounted_bytes']+budget['planned_batch_bytes'] <= budget['limit_bytes'],
            '0399 C4 build and active trial exceed storage')
    receipt_path = P398/'c4-native/result.json'
    installed, prior = map(load,(receipt_path,REFERENCE))
    control = Path(installed['binary'])
    require(sha(control)==installed['binary_sha256'] and SDK.is_dir() and CLANG.is_file() and
            all(sha(p)==digest for p,digest in prior['input_pins'].items()),'C4 toolchain or inputs differ')
    old = Path(prior['products']['candidate']['binary'])
    historical, = (entry['argv'] for entry in prior['steps'] if entry['name']=='candidate-compile' and entry['exit']==0)
    require(historical[:4]==['xcrun','--sdk','iphoneos','clang'] and
            historical[historical.index('-o')+1]==str(old),'C4 compile invocation differs')
    frontend, = (Path(arg) for arg in historical if arg.endswith('/HakiosMetalCA.m'))
    out = BASE/'c4-native'
    out.mkdir()
    changed = out/frontend.name
    changed.write_text(instrument(frontend.read_text()))
    inputs = {str(p):sha(p) for p in (Path(__file__),receipt_path,REFERENCE,control,PADDING,CLANG,frontend)}
    inputs.update(prior['input_pins'])
    def compile_variant(name, target_frontend):
        bundle = out/name/control.parent.name
        bundle.mkdir(parents=True)
        shutil.copyfile(control.parent/'Info.plist',bundle/'Info.plist')
        binary = bundle/control.name
        command = [str(CLANG),*historical[4:]]
        command[command.index('-isysroot')+1] = str(SDK)
        output = command.index('-o')
        command[output+1] = str(binary)
        command[output:output] = [str(PADDING)]
        if target_frontend != frontend:
            command[command.index(str(frontend))] = str(target_frontend)
            command.insert(command.index(str(target_frontend)),'-I'+str(frontend.parent))
        for stage,args in (('compile',command),('sign',['codesign','--force','--sign','-',str(bundle)]),
                           ('verify',['codesign','--verify','--strict',str(bundle)])):
            result = subprocess.run(args,capture_output=True,timeout=120)
            path = out/f'{name}-{stage}.log'
            path.write_bytes(result.stdout+result.stderr)
            require(result.returncode==0,'C4 '+stage+' failed. See '+str(path))
        return binary
    rebuilt = compile_variant('control',frontend)
    require(sha(rebuilt)==installed['binary_sha256'],'deployed C4 did not reproduce byte-for-byte')
    candidate = compile_variant('candidate',changed)
    require(104*4096 < candidate.stat().st_size <= 105*4096,'C4 no longer occupies the exact allocated extent')
    for cmd in (['nm','-gUj'],['otool','-L'],['vtool','-show-build']):
        def lines(path):
            output = subprocess.check_output([str(VERIFY_TOOLS/cmd[0]),*cmd[1:],str(path)],timeout=30).splitlines()
            return set(output) if cmd[0]=='nm' else output[1:]
        require(lines(candidate)==lines(rebuilt),'C4 exports, platform or loads changed')
    imports = lambda binary:set(subprocess.check_output([str(VERIFY_TOOLS/'nm'),'-ju',str(binary)],timeout=30).splitlines())
    added = imports(candidate)-imports(rebuilt)
    require(added <= {b'_pthread_threadid_np'} and imports(rebuilt) <= imports(candidate) and
            all(sha(control.parent/name)==sha(candidate.parent/name) for name in ('Info.plist','_CodeSignature/CodeResources')),
            'C4 imports or resources differ outside the thread receipt')
    result = dict(state='0399-signed-C4-render-target-observer',binary=str(candidate),binary_sha256=sha(candidate),
                  bytes=candidate.stat().st_size,reconstructed_control_sha256=sha(rebuilt),strict_signature=True,
                  source=str(changed),source_sha256=sha(changed),device_commands=0,input_pins=inputs)
    with (out/'result.json').open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    return {k:v for k,v in result.items() if k!='input_pins'}


if __name__ == '__main__':
    print(json.dumps(build(),indent=2))
