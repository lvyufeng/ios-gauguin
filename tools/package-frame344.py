#!/usr/bin/env python3
"""Build and verify the offline 0344 wrapper and its kernel-scoped helper."""

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from mkpayload import build
from kernel_banner import one_banner
from core343_scope import MAIN, WORK, load, require, sha


BASE = WORK / 'research/tmp/frame-344'
P343 = MAIN / 'research/tmp/gauguin-runtime-issue-worktree-20261119/research/tmp/runtime-issue-343'
W219 = MAIN / 'research/tmp/gauguin-swipe219-worktree-20261110/research/tmp'


def parts(data):
    require(data[:8] == b'ANDROID!' and len(data) >= 4096, 'invalid boot header')
    ks, ka, rs, ra, second, _, _, page, ver, _ = struct.unpack_from('<10I', data, 8)
    dtbo, dtbo_at, header, dtb, dtb_addr = struct.unpack_from('<IQIQQ', data, 1632)
    require((ka, ra, second, page, ver, dtbo, dtbo_at, header, dtb_addr) ==
            (0x8000, 0x1000000, 0, 4096, 2, 0, 0, 1660, 0x1f00000), 'unexpected wrapper geometry')
    parts = [data[:page]]
    start = page
    for size in (ks, rs, dtb):
        end = start + size
        rounded = end + (-end % page)
        require(size > 0 and rounded <= len(data) and not any(data[end:rounded]), 'bad payload or padding')
        parts.append(data[start:end])
        start = rounded
    require(start == len(data), 'trailing wrapper data')
    return parts


def boot_image(old, manifest, *, base=BASE, trial='0344', enable_frame_line_counter=False, frame_capture_mode=None,
               scripted_motion=False, private_scanout_shim=None, command_profile=None,
               private_scanout_slot_bytes=None):
    kernel = Path(manifest['kernel'])
    require(sha(kernel) == manifest['kernel_sha256'], 'linked candidate differs')
    old_manifest = load(P343 / 'kernel-native/build-manifest.json')
    original = Path(old_manifest['products']['candidate']['kernel'])
    adt = W219 / 'dsh-ui-0219-once-swipe/managed-6g.adt'
    fw = W219 / 'p3-gpu-inventory-20261105/firmware'
    assets = dict(
        zap_mdt_path=fw/'a615_zap.mdt', gmu_firmware_path=fw/'a619_gmu.bin',
        sqe_firmware_path=fw/'a630_sqe.fw', zap_code_path=fw/'a615_zap.b02',
    )
    nvt = W219/'gauguin-novatek-reference/novatek_nt36672c_j17_fw01.bin'
    for path in (adt, nvt, *assets.values()):
        require(sha(path) == old['input_pins'][str(path)]['sha256'], 'asset input changed')
    before = Path(old['image']).read_bytes()
    require(hashlib.sha256(before).hexdigest() == old['image_sha256'], 'baseline wrapper differs')
    header, shim, old_payload, dtb = parts(before)
    rebuilt, _ = build(original, adt, old['command'], None, nvt, pas_reservation=True, **assets)
    require(rebuilt == old_payload, '0343 fixed payload failed exact reproduction')
    require(old['command'].split().count('sweetfb_stats=1') == 1, 'ambiguous boot argument change')
    if frame_capture_mode is None:
        frame_capture_mode = 3 if enable_frame_line_counter else 2
    else:
        require(not enable_frame_line_counter and frame_capture_mode in (2,3,4,5,6,7,8,9), 'ambiguous scanout capture mode')
    cmd = old['command'].replace('sweetfb_stats=1', f'sweetfb_stats={frame_capture_mode}')
    if scripted_motion:
        require(cmd.split().count('swp=3')==1, 'ambiguous scripted motion opt-in')
        cmd = cmd.replace('swp=3','swp=4')
    if command_profile is not None:
        cmd = command_profile(cmd)
    if frame_capture_mode != 2:
        require(cmd.split().count('sweetfb_hz=60') == 1,
                'counter capture requires a unique 60 Hz mode')
    slots = {} if private_scanout_slot_bytes is None else {'dpu_slot_bytes':private_scanout_slot_bytes}
    payload, info = build(kernel, adt, cmd, None, nvt, pas_reservation=True,
                          dpu_buffers=private_scanout_shim is not None, **slots, **assets)
    require(payload[0x48:0x2a8].rstrip(b'\0') == cmd.encode() and
            one_banner(payload).decode() == manifest['kernel_banner'], 'candidate payload identity differs')
    require(info['low_pas_request']['state'] == 'pending-runtime-validation', 'LowPAS layout differs')
    header = bytearray(header)
    if private_scanout_shim is not None:
        shim = private_scanout_shim.read_bytes()
        require(0 < len(shim) < 0x100000 and info['dpu_buffer_request']['slots']==2,
                'private scanout shim or padding differs')
        if private_scanout_slot_bytes is not None:
            require(info['dpu_buffer_request']['bytes_per_slot']==private_scanout_slot_bytes,
                    'private scanout slot length differs')
        struct.pack_into('<I',header,8,len(shim))
    struct.pack_into('<I', header, 16, len(payload))
    image = bytes(header) + b''.join(data + bytes(-len(data) % 4096) for data in (shim, payload, dtb))
    require(parts(image) == [bytes(header), shim, payload, dtb], 'wrapper re-read differs')
    output = base/f'frame{trial.removeprefix("0")}-image.img'
    with output.open('xb') as stream:
        stream.write(image)
    return dict(state=trial+'-offline-image-verified', image=str(output), image_sha256=sha(output),
                image_bytes=len(image), command=cmd, build_identity=manifest['identity'],
                kernel_sha256=sha(kernel), kernel_banner=manifest['kernel_banner'],
                baseline_reproduced=True, booted=False,
                input_pins={str(path):sha(path) for path in (kernel, original, adt, nvt, *assets.values(),
                    *((private_scanout_shim,) if private_scanout_shim is not None else ()))})


def retarget_edr_identity(data, before, after):
    require(data[:4] == bytes.fromhex('cffaedfe') and len(before) == len(after) and
            data.count(before) == 1 and after not in data, 'EDR candidate C string differs')
    identity = data.index(before)
    require(data[identity-1:identity] == b'\0' and data[identity+len(before):identity+len(before)+1] == b'\0',
            'EDR identity is not a complete C string')
    count, length = struct.unpack_from('<II', data,16)
    cursor = 32
    cstrings, signatures = [], []
    for _ in range(count):
        command, size = struct.unpack_from('<II',data,cursor)
        require(8 <= size <= 32+length-cursor, 'invalid Mach-O command')
        if command == 0x19:
            segment = data[cursor+8:cursor+24].rstrip(b'\0')
            sections = struct.unpack_from('<I',data,cursor+64)[0]
            require(size == 72+80*sections, 'invalid Mach-O segment')
            for i in range(sections):
                offset = cursor+72+80*i
                section = data[offset:offset+16].rstrip(b'\0')
                if segment == b'__TEXT' and section == b'__cstring':
                    span, start = struct.unpack_from('<QI',data,offset+40)
                    cstrings.append((start,start+span))
        elif command == 0x1d:
            require(size == 16, 'invalid Mach-O signature command')
            start, span = struct.unpack_from('<II',data,cursor+8)
            signatures.append((start,start+span))
        cursor += size
    require(cursor == 32+length and len(cstrings) == len(signatures) == 1, 'EDR Mach-O layout differs')
    start, end = cstrings[0]
    signature_start, signature_end = signatures[0]
    require(cursor <= start < identity and identity+len(before)<end <= signature_start and signature_end == len(data),
            'EDR identity or signature layout differs')
    return data[:identity]+after+data[identity+len(before):], signature_start


def edr(image, *, base=BASE, trial='0344', signed_reference=None, profile=None):
    previous = P343/'edr-native'
    reference = load(previous/'result.json')
    binary = Path(reference['binary'])
    require(reference['inputs_unchanged'] and sha(binary) == reference['binary_sha256'], 'EDR baseline differs')
    old_identity, identity = reference['kernel_identity'], image['build_identity']
    if profile is not None:
        require(signed_reference is not None and profile == ('gpf=4','gpf=5') and
                image['command'].split().count(profile[1]) == 1 and profile[0] not in image['command'].split(),
                'EDR performance opt-in differs from the image')
    out = base/'edr-native'
    src = out/'sources'
    src.mkdir(parents=True)
    old_src = previous/'sources'
    for path in sorted(old_src.iterdir()):
        data = path.read_bytes()
        if path.name == 'EDRDefaultCore.h':
            require(data.count(old_identity.encode()) == 1, 'EDR identity scope differs')
            data = data.replace(old_identity.encode(), identity.encode())
            if profile is not None:
                before, after = (word.encode() for word in profile)
                require(data.count(before) == 1 and after not in data, 'EDR source opt-in differs')
                data = data.replace(before, after).replace(b'native565', b'native650')
        (src/path.name).write_bytes(data)

    def run(label, argv):
        process = subprocess.run(argv, cwd=WORK, capture_output=True, timeout=120)
        (out/(label+'.log')).write_bytes(process.stdout+process.stderr)
        process.check_returncode()
        return process.stdout

    tag = f'edr{trial.removeprefix("0")}'
    host = out/(tag+'_host.c')
    fixture = (previous/'edr343_host.c').read_text()
    require(fixture.count(old_identity) == 1, 'EDR test identity is ambiguous')
    fixture = fixture.replace(old_identity, identity)
    if profile is not None:
        fixture = fixture.replace(*profile).replace('native565', 'native650')
        old_case = '"gmt=2 gsp=328 sweetgpumap=1 gpf=3",'
        require(fixture.count(old_case) == 1, 'EDR negative scope fixture differs')
        fixture = fixture.replace(old_case, old_case.replace('gpf=3', profile[0]))
    host.write_text(fixture)
    runner = out/(tag+'-host')
    run('host-compile', ['xcrun','clang','-std=gnu11','-O1','-g','-fblocks','-Wall','-Wextra',
                         '-Werror','-fsanitize=address,undefined',str(host),'-o',str(runner)])
    checks = json.loads(run('host-test', [str(runner)]))
    require(checks['checks'] == 2145 and checks['device_commands'] == 0, 'EDR host checks differ')
    target = out/binary.name
    provenance = {}
    identity_patch = signed_reference is not None and profile is None
    if signed_reference is not None:
        receipt = load(signed_reference)
        donor = Path(receipt['binary'])
        require(sha(donor)==receipt['binary_sha256'] and donor.name==target.name and
                receipt['scope_checks']==checks['checks'], 'signed EDR donor differs')
        run('verify-donor', ['codesign','--verify','--strict',str(donor)])
        provenance = dict(identity_only_retarget=identity_patch,
            input_pins={str(signed_reference):sha(signed_reference),str(donor):sha(donor)})
    if identity_patch:
        retargeted, signature_start = retarget_edr_identity(donor.read_bytes(),receipt['kernel_identity'].encode(),identity.encode())
        with target.open('xb') as file:
            file.write(retargeted)
    else:
        command = next(step['argv'] for step in reference['steps'] if step['label']=='candidate-compile')
        argv = [arg.replace(str(old_src),str(src)) for arg in command]
        argv[argv.index('-o')+1] = str(target)
        if profile is not None:
            # The compiler may embed a boot argument comparison in code.
            # Recompile the full helper and an old-profile instruction control.
            old_sdk = Path(argv[argv.index('-isysroot')+1])
            if not old_sdk.is_dir():
                argv[argv.index('-isysroot')+1] = str(old_sdk.parent/'iPhoneOS27.2.sdk')
            control = out/'profile-control'
            control.mkdir()
            for path in src.iterdir():
                data = path.read_bytes()
                if path.name=='EDRDefaultCore.h':
                    data = data.replace(profile[1].encode(),profile[0].encode())
                (control/path.name).write_bytes(data)
            old_profile = out/'gpf4-control.dylib'
            old_argv = [arg.replace(str(src),str(control)) for arg in argv]
            old_argv[old_argv.index('-o')+1] = str(old_profile)
            run('compile-profile-control',old_argv)
        run('compile',argv)
        if profile is not None:
            before = run('control-text',['xcrun','otool','-t',str(old_profile)])
            after = run('candidate-text',['xcrun','otool','-t',str(target)])
            provenance.update(profile_source_compiled=True,retargeted_optin=list(profile),
                profile_control=str(old_profile),profile_control_sha256=sha(old_profile),
                profile_text_control_sha256=hashlib.sha256(before).hexdigest(),
                profile_text_candidate_sha256=hashlib.sha256(after).hexdigest())
    run('sign', ['codesign','--force','--sign','-',str(target)])
    run('verify', ['codesign','--verify','--strict',str(target)])
    if identity_patch:
        require(target.read_bytes()[:signature_start]==retargeted[:signature_start],
                'EDR bytes outside the signing blob differ from the exact retarget')
    for name, options in (('imports', ['nm','-m','-u']), ('exports', ['nm','-gU']), ('loads', ['otool','-L'])):
        a = run('0343-'+name, [*options, str(binary)]).decode().splitlines()
        b = run(trial+'-'+name, [*options, str(target)]).decode().splitlines()
        if name == 'loads':
            a, b = a[1:], b[1:]
            if profile is not None:
                a, b = ([line.split(' (compatibility version',1)[0] for line in rows] for rows in (a,b))
        if name == 'exports':
            a, b = [[row.split()[-1] for row in rows if row.strip()] for rows in (a, b)]
        require(a == b, 'EDR ABI differs: ' + name)
    require((target.stat().st_size == binary.stat().st_size or profile is not None) and identity.encode() in target.read_bytes(),
            'EDR size or identity differs')
    return dict(state=trial+'-edr-signed', binary=str(target), binary_sha256=sha(target),
                binary_bytes=target.stat().st_size, kernel_identity=identity, scope_checks=checks['checks'], **provenance)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kernel-receipt', required=True, type=Path)
    args = parser.parse_args()
    manifest = load(args.kernel_receipt)
    require(manifest['state'] == '0344-native-ARM64-linked' and manifest['inputs_unchanged'], 'unqualified build')
    image = boot_image(load(P343/'runtime343-image.json'), manifest)
    image['kernel_manifest'] = str(args.kernel_receipt.resolve())
    result = edr(image)
    for path, record in ((BASE/'frame344-image.json',image), (BASE/'edr-native/result.json',result)):
        with path.open('x') as stream:
            json.dump(record, stream, indent=2)
            stream.write('\n')
    print(json.dumps(dict(image=image['image_sha256'], edr=result['binary_sha256'],
                          image_bytes=image['image_bytes'], checks=result['scope_checks'])))


if __name__ == '__main__':
    main()
