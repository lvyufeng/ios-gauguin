#!/usr/bin/env python3
"""Verify the stock CPU split, the idle preference, and the native build."""

import argparse
from importlib import import_module
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-398'
P397 = MAIN/'research/tmp/gauguin-frame397-resident-buffer-overlap-worktree-20261123/research/tmp/frame-397'
P394 = MAIN/'research/tmp/gauguin-frame394-compositor-qos-worktree-20261123/research/tmp/frame-394'
P393 = MAIN/'research/tmp/gauguin-frame393-ca-members-worktree-20261123/research/tmp/frame-393'
P391 = MAIN/'research/tmp/gauguin-frame391-pending-swap-worktree-20261123/research/tmp/frame-391'
FULL = (MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/.deps-cache/p0-20261105'
        /'build301-causal-trace/runs/gauguin.VUngMR/build-manifest.json')
CONTROL = P397/'native-kernel/build-manifest.json'
IMAGE = BASE/'frame398-image.json'
FDT = MAIN/'research/tmp/dsh-0139/policy-capture/10.bin'
PATCH = WORK/'graphics/gauguin-program-io/0398-prefer-idle-performance-core-for-compositor.patch'
FIXTURE = WORK/'tests/fixtures/frame398_cpu_preference.cpp'
SCHED = Path('osfmk/kern/sched_prim.c')
GPU = Path('iokit/Kernel/arm/GauguinGPU.cpp')


def stock_topology():
    rows = []
    for cpu in range(8):
        node = '/cpus/cpu@'+format(cpu<<8,'x')
        def property_value(kind,name):
            return subprocess.check_output(['fdtget','-t',kind,str(FDT),node,name],text=True,timeout=20).split()
        registers = tuple(int(x,16) for x in property_value('x','reg'))
        domain = tuple(int(x,16) for x in property_value('x','qcom,freq-domain'))
        capacity, = map(int, property_value('u','capacity-dmips-mhz'))
        want = (1,2,1894) if cpu>=6 else (0,6,1024)
        require(registers==(0,cpu<<8) and domain[1:]+(capacity,)==want, 'stock Android CPU capacity split differs')
        rows.append(dict(cpu=cpu,mpidr=registers[1],domain=domain[1],capacity=capacity))
    return rows


def sources():
    return {SCHED:Path(load(FULL)['source']['path'])/SCHED, GPU:Path(load(CONTROL)['source'])/GPU}


def host():
    stock = stock_topology()
    paths = sources()
    with TemporaryDirectory(prefix='398-idle-policy-',dir=BASE) as temporary:
        folder = Path(temporary)
        for name, path in paths.items():
            target = folder/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(path.read_bytes())
        subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)],cwd=folder,check=True,capture_output=True,timeout=30)
        scheduler,gpu = ((folder/name).read_text() for name in (SCHED,GPU))
        function = import_module('check-frame391').function
        driver = import_module('check-frame397').method
        methods = [function(scheduler,name) for name in ('gauguin_display_idle_performance_cpu','gauguin_display_preferred_cpu')]
        methods.append(driver(gpu,'observeDisplayIssueCpu398'))
        (folder/'Frame398Methods.inc').write_text('\n\n'.join(methods)+'\n')
        dispatch = function(scheduler,'thread_setrun')
        order = ('if (thread->bound_processor == PROCESSOR_NULL)', 'pset_lock(starting_pset)',
                 'gauguin_display_preferred_cpu(starting_pset, processor_hint, thread)',
                 'SCHED(choose_processor)(starting_pset, processor_hint, thread)', 'processor_setrun(processor, thread, options)')
        require([dispatch.index(s) for s in order]==sorted(dispatch.index(s) for s in order) and
            'if (ok && fAsync && sweet_frame344_clock()) {\n            if (fCompositor) observeDisplayIssueCpu398(fPendingDisplayTicket);' in gpu and
            gpu.count('__atomic_store_n(&gauguin_display_thread_398,0,__ATOMIC_RELEASE)')==3,
            'CPU preference is absent from the existing scheduling, issue, close or fault path')
        result = subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I'+str(folder),str(FIXTURE),'-o',str(folder/'test')],capture_output=True,text=True,timeout=60)
        require(result.returncode==0,'performance-core fixture failed to compile: '+result.stderr[-2000:])
        subprocess.run([str(folder/'test')],check=True,timeout=20)
    return dict(state='0398-idle-performance-placement-host-verified', ASan_UBSan=True, stock_topology=stock,
        device_commands=0, patch_sha256=sha(PATCH), input_pins={str(p):sha(p) for p in (FDT,PATCH,FIXTURE,*paths.values())})


def scheduler_recipe():
    m = load(FULL)
    source, build = Path(m['source']['path']),Path(m['build_root'])
    obj = build/'obj-gauguin-macos'
    cwd = obj/'DEVELOPMENT_ARM64_GAUGUIN/osfmk/DEVELOPMENT'
    makefile, unit = cwd/'Makefile',source/SCHED
    original = cwd/'sched_prim.o'
    dependency, types = cwd/'sched_prim.d',source/'osfmk/libsa/types.h'
    pins = {str(p):sha(p) for p in (unit,original,makefile,dependency,types,FULL)}
    require(m['state']=='built' and m['machine']=='gauguin' and m['make_exit']==0 and
        m['configuration']=='DEVELOPMENT' and
        pins[str(unit)]==next(h for n,_,h in m['source']['entries'] if n==str(SCHED)), 'scheduler donor differs')
    env = dict(os.environ,SDKROOT_RESOLVED=m['sdk']['path'],HOST_SDKROOT_RESOLVED=m['host_sdk']['path'],
        SDKVERSION=m['environment']['SDKVERSION'],PLATFORM='MacOSX')
    for key in ('MAKEFLAGS','MFLAGS','MAKELEVEL','MAKEOVERRIDES'):
        env.pop(key,None)
    args = ['/usr/bin/make','-n','-W',str(unit),'-f',str(makefile),'sched_prim.o',f'SRCROOT={source}',f'SOURCE_DIR={source}',
        f'SOURCE={source}/',f'OBJROOT={obj}',f'SYMROOT={build}/sym-gauguin-macos',f'DSTROOT={BASE}/unused-install',
        f'OBJPATH={cwd}',f'TARGET={cwd}','RELATIVE_SOURCE_PATH=osfmk','CURRENT_KERNEL_CONFIG=DEVELOPMENT',
        'CURRENT_ARCH_CONFIG=ARM64','CURRENT_MACHINE_CONFIG=GAUGUIN','CURRENT_BUILD_CONFIG=DEVELOPMENT^ARM64^GAUGUIN',
        'BUILD_WERROR=0','BUILD_LTO=0','VERBOSE=YES','CONCISE=0','KDKROOT=',
        'RC_DARWIN_KERNEL_VERSION='+m['environment']['RC_DARWIN_KERNEL_VERSION']]
    result = subprocess.run(args,cwd=cwd,env=env,capture_output=True,text=True,timeout=60)
    require(result.returncode==0,'original scheduler compile recipe unavailable: '+result.stderr[-1600:])
    commands = (shlex.split(line) for line in result.stdout.splitlines() if str(unit) in line and ' -c ' in line)
    command, = (words for words in commands if Path(words[0]).name=='clang')
    require(command.count(str(unit))==1 and '-DMACH_KERNEL_PRIVATE' in command and '-DGAUGUIN' in command and
        all(sha(p)==h for p,h in pins.items()), 'unexpected scheduler compile flags or modified donor')
    # The component make normally prefixes SOURCE with osfmk. Confirm the
    # actual original dependency before reconstructing the component include.
    require(str(types) in dependency.read_text(),'missing original scheduler libsa dependency')
    command[command.index('-I'+str(source/'libsa'))]='-I'+str(types.parent)
    command[command.index('-MF')+1]=str(cwd/'sched_prim.d')
    if '-o' in command:
        require(Path(command[command.index('-o')+1]).name==original.name, 'unexpected scheduler object')
        command[command.index('-o')+1]=str(original)
    else:
        command.extend(('-o',str(original)))
    path = BASE/'scheduler-recipe.json'
    data = dict(state='scheduler-compile-from-original-makefile',device_commands=0, input_pins=pins,
        steps=[dict(name='compile-sched_prim',argv=command,cwd=str(cwd),exit=0)])
    import_module('prepare-frame393').save(path,data)
    return path


def native():
    budget = load(P394/'CPU-placement-development-admission.json')
    offline = load(BASE/'offline.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==278_000_000 and
        budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'] and
        offline['patch_sha256']==sha(PATCH) and offline['ASan_UBSan'] and not offline['device_commands'],
        '0398 native build exceeds its budget or verified source')
    recipe = scheduler_recipe()
    output = BASE/'native-kernel'
    import_module('build-frame347').link_scanout(CONTROL,output,parent_trial='0397',trial='0398',patches=(PATCH,),
        extra_units=(('sched_prim',recipe,'compile-sched_prim'),('GauguinGPU',CONTROL,'compile-GauguinGPU')),
        extra_sources={str(SCHED):sources()[SCHED]},recompile_scanout=False,
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    m = load(output/'build-manifest.json')
    require(m['inputs_unchanged'] and m['baseline_reproduced_except_uuid'] and
        {Path(p).stem for p in m['object_replacements'].values()}=={'sched_prim','GauguinGPU'}, '0398 link effects differ')
    imports = lambda p:set(subprocess.check_output(['xcrun','nm','-uj',p],timeout=30).splitlines())
    added = {Path(new).stem:sorted(s.decode() for s in imports(new)-imports(old))
             for old,new in m['object_replacements'].items()}
    require(added=={'sched_prim':['_gauguin_display_preferred_dispatches_398',
        '_gauguin_display_thread_398','_sweet_frame344_clock'],
        'GauguinGPU':['_cpu_number','_ml_get_cpu_number','_ml_get_max_cpu_number']}, '0398 unexpected kernel dependencies')
    return dict(kernel_sha256=m['kernel_sha256'],identity=m['identity'], added_links=added, device_commands=0)


def object_text(path):
    data = path.read_bytes()
    require(struct.unpack_from('<II',data)==(0xfeedfacf,0x0100000c),'scheduler object is not ARM64 Mach-O')
    offset = 32
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        command,size = struct.unpack_from('<II',data,offset)
        if command==0x19:
            section_count, = struct.unpack_from('<I',data,offset+64)
            for i in range(section_count):
                section, segment, _, length, start = struct.unpack_from('<16s16sQQI',data,offset+72+80*i)
                if section.rstrip(b'\0')==b'__text' and segment.rstrip(b'\0')==b'__TEXT':
                    return data[start:start+length]
        offset += size
    raise ValueError('original scheduler object has no text')


def control_text():
    import hashlib
    recipe = load(BASE/'scheduler-recipe.json')['steps'][0]
    with TemporaryDirectory(prefix='398-control-',dir=BASE) as temporary:
        to = Path(temporary)/'sched_prim.o'
        cmd = recipe['argv'].copy()
        original = Path(cmd[cmd.index('-o')+1])
        cmd[cmd.index('-o')+1] = str(to)
        cmd[cmd.index('-MF')+1] = str(to.with_suffix('.d'))
        result = subprocess.run(cmd,cwd=recipe['cwd'],capture_output=True,text=True,timeout=90)
        require(result.returncode==0,'original scheduler recipe does not compile: '+result.stderr[-1400:])
        old,new = map(object_text,(original,to))
        require(old==new,'original and reproduced scheduler instructions differ')
        return dict(bytes=len(old),sha256=hashlib.sha256(old).hexdigest(),exact_ARM64_text=True,device_commands=0)


def package():
    budget = load(BASE/'complete-batch-admission.json')
    remaining = budget['planned_batch_bytes']
    require(budget['admitted'] and remaining==375_000_000 and
        budget['current_accounted_bytes']+remaining<=budget['limit_bytes'], '0398 package exceeds storage')
    terminal = load(P397/'execution/result.json')
    require(terminal['restored'] and terminal['independent_restore_verified'] and not terminal['stable_60_fps_observed'],
        '0397 must be independently restored with an unfinished 60 fps target')
    require(load(BASE/'scheduler-control-text.json')==control_text(),'0398 original scheduler control receipt differs')
    pack = import_module('package-frame344')
    setup = import_module('prepare-frame393')
    native_path = BASE/'native-kernel/build-manifest.json'
    native = load(native_path)
    require(native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH)==load(BASE/'offline.json')['patch_sha256'],
        '0398 staged native scheduler differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial='0398',
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=setup.previous.previous.previous.prior388.SHIM,
        command_profile=setup.previous.command_profile)
    parent = load(P397/'trial-plan.json')
    old,new = (pack.parts(Path(path).read_bytes()) for path in (parent['image'],image['image']))
    require(old[0][:16]==new[0][:16] and old[0][20:]==new[0][20:] and old[1]==new[1] and old[3]==new[3] and
        image['command']==parent['boot_command'],'0398 boot command, wrapper or DTB differs')
    admission = pack.edr(image,base=BASE,trial='0398',signed_reference=P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
    donor_path = P397/'edr-native/result.json'
    donor = load(donor_path)
    machine = import_module('check-frame395-edr')
    require(sha(donor['binary'])==donor['binary_sha256'] and machine.native_words(admission['binary'])==machine.native_words(donor['binary']),
        '0398 signed GPU-point machine code differs from 0397')
    admission['matching_0397_machine_code'] = True
    admission['input_pins'].update({str(donor_path):sha(donor_path),donor['binary']:donor['binary_sha256']})
    image['kernel_manifest'] = str(native_path)
    setup.save(BASE/'edr-native/result.json',admission)
    setup.save(IMAGE,image)
    return {k:image[k] for k in ('image_sha256','image_bytes','build_identity')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('host','native','control_text','package'))
    print(json.dumps(globals()[parser.parse_args().stage](),indent=2))
