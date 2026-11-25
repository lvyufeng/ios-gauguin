#!/usr/bin/env python3
"""Verify the actual driver methods for reuse during unrelated GPU work."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-397'
P393 = MAIN/'research/tmp/gauguin-frame393-ca-members-worktree-20261123/research/tmp/frame-393'
P391 = MAIN/'research/tmp/gauguin-frame391-pending-swap-worktree-20261123/research/tmp/frame-391'
P394 = MAIN/'research/tmp/gauguin-frame394-compositor-qos-worktree-20261123/research/tmp/frame-394'
PATCH = WORK/'graphics/gauguin-program-io/0397-reuse-buffer-during-unrelated-GPU-work.patch'
FIXTURE = WORK/'tests/fixtures/frame397_resident_buffer.cpp'
CONTROL = P393/'native-kernel/build-manifest.json'
IMAGE = BASE/'frame397-image.json'
TU = Path('iokit/Kernel/arm/GauguinGPU.cpp')


def method(source, name):
    start, = re.finditer(r'^\S[^\n]*\b'+re.escape(name)+r'\([^{};]*\)(?: const)?\n\{', source, re.M)
    return source[start.start():source.index('\n}', start.end())+2]


def host():
    source = Path(load(CONTROL)['source'])
    audit = load(P394/'0395-BO-overlap.json')
    require(audit['counts'] == dict(cached_immediate=72, fresh_immediate=19, cached_waited=10) and
        all(len(r['observed_EOP_in_pending_gate']) == 1 for r in audit['waited']) and
        all(sha(p) == digest for p,digest in audit['input_pins'].items()), '0395 allocation trace does not reproduce')
    with TemporaryDirectory(prefix='397-reuse-', dir=BASE) as temporary:
        folder = Path(temporary)
        target = folder/TU
        target.parent.mkdir(parents=True)
        target.write_bytes((source/TU).read_bytes())
        subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)], cwd=folder, check=True, capture_output=True, timeout=30)
        text = target.read_text()
        specs = ('GauguinGPUUserClient::takeCached335', 'GauguinGPUUserClient::pendingOwner397',
                 'validResidentRange397', 'GauguinGPUUserClient::disjointPending397', 'validAllocation397',
                 'GauguinGPUUserClient::publishCached397', 'GauguinGPUUserClient::reusePending397')
        (folder/'Frame397Methods.inc').write_text('\n\n'.join(method(text, name) for name in specs)+'\n')
        types = re.findall(r'^struct gpu_(?:buffer|queue) \{.*?\};', text, re.M | re.S)
        require(len(types)==2, 'GPU backing structure differs')
        (folder/'Frame397Buffers.inc').write_text('\n'.join(types)+'\n')
        dispatch = method(text, 'GauguinGPUUserClient::externalMethod')
        order = ('if(fClosed||!fBuffers||gOwner!=this)', 'if(selector==0x42&&reusePending397(r.make))',
                 'if(fAsync&&fPendingCount&&!passive)', 'result=finishPending(true,true);', 'switch(selector)')
        offsets = [dispatch.index(fragment) for fragment in order]
        require(offsets==sorted(offsets) and dispatch.count('reusePending397(')==1 and
            'case 0x42:' in dispatch and 'publishCached397(b,n,r.make,false);' in dispatch,
            'pending reuse bypassed its normal request entry or fallback')
        args = ['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror', '-fsanitize=address,undefined',
                '-fno-sanitize-recover=all','-I'+str(folder),'-I'+str(source/'bsd/dev'),str(FIXTURE),'-o',str(folder/'check')]
        result = subprocess.run(args, capture_output=True, text=True, timeout=60)
        require(result.returncode==0, 'resident buffer fixture compile failed: '+result.stderr[-2200:])
        subprocess.run([str(folder/'check')], check=True, timeout=20)
    return dict(state='0397-resident-BO-overlap-host-verified', exact_cases=25, ASan_UBSan=True, device_commands=0,
        patch_sha256=sha(PATCH), observed_waited_hot_allocations=10,
        input_pins={str(p):sha(p) for p in (Path(__file__), CONTROL, source/TU, FIXTURE, P394/'0395-BO-overlap.json')})


def native():
    budget = load(BASE/'rebuild-admission.json')
    offline = load(BASE/'offline.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==278_000_000 and
        budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'] and
        offline['patch_sha256']==sha(PATCH) and offline['exact_cases']==25 and not offline['device_commands'],
        '0397 budget, effects or verification differ')
    build = import_module('build-frame347')
    out = BASE/'native-kernel'
    build.link_scanout(CONTROL,out,parent_trial='0393',trial='0397',patches=(PATCH,),
        extra_units=(('GauguinGPU',P391/'native-kernel/build-manifest.json','compile-GauguinGPU'),),
        recompile_scanout=False,compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    manifest = load(out/'build-manifest.json')
    require(manifest['inputs_unchanged'] and manifest['baseline_reproduced_except_uuid'] and
            len(manifest['object_replacements'])==1, '0397 changed multiple kernel objects')
    old,new = next(iter(manifest['object_replacements'].items()))
    imports = lambda path: set(subprocess.check_output(['xcrun','nm','-uj',path],timeout=30).splitlines())
    require(Path(new).stem=='GauguinGPU' and imports(old)==imports(new), '0397 introduced a new kernel dependency')
    return dict(kernel_sha256=manifest['kernel_sha256'], identity=manifest['identity'], device_commands=0)


def package():
    budget = load(BASE/'package-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==266_000_000 and
        budget['current_accounted_bytes']+budget['planned_batch_bytes']<=budget['limit_bytes'],
        '0397 image and concurrent runtime exceed storage')
    pack = import_module('package-frame344')
    prior = import_module('prepare-frame393')
    native_path = BASE/'native-kernel/build-manifest.json'
    native = load(native_path)
    require(native['state']=='0397-native-ARM64-linked' and native['inputs_unchanged'] and
        native['input_pins'][str(PATCH)]==sha(PATCH)==load(BASE/'offline.json')['patch_sha256'],
        '0397 native GPU method differs from the verified source')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial='0397',
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=prior.previous.previous.previous.prior388.SHIM,
        command_profile=prior.previous.command_profile)
    control = load(P393/'trial-plan.json')
    old,new = (pack.parts(Path(path).read_bytes()) for path in (control['image'],image['image']))
    require(old[0][:16]==new[0][:16] and old[0][20:]==new[0][20:] and old[1]==new[1] and old[3]==new[3] and
        control['boot_command']==image['command'] and image['command'].split().count('sweetgpumap=1')==1,
        '0397 wrapper, DTB or boot command differs')
    admission = pack.edr(image,base=BASE,trial='0397',signed_reference=P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
    machine = import_module('check-frame395-edr')
    donor_path = P393/'edr-native/result.json'
    donor = load(donor_path)
    require(sha(donor['binary'])==donor['binary_sha256'] and
        machine.native_words(admission['binary'])==machine.native_words(donor['binary']), '0397 EDR machine code differs')
    admission['input_pins'].update({str(donor_path):sha(donor_path),donor['binary']:donor['binary_sha256']})
    admission['matching_0393_machine_code'] = True
    image['kernel_manifest'] = str(native_path)
    prior.save(BASE/'edr-native/result.json',admission)
    prior.save(IMAGE,image)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('host','native','package'))
    print(json.dumps(globals()[parser.parse_args().stage](), indent=2))
