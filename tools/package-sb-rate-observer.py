#!/usr/bin/env python3
"""Package an offline SpringBoard observer boot image from a built kernel."""

import argparse
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
W301 = MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112'
SWIPE = MAIN/'research/tmp/gauguin-swipe219-worktree-20261110'
FW = SWIPE/'research/tmp/p3-gpu-inventory-20261105/firmware'
FIRMWARES = {
    'NovatekFirmware': SWIPE/'research/tmp/gauguin-novatek-reference/novatek_nt36672c_j17_fw01.bin',
    'A615ZapMDT': FW/'a615_zap.mdt',
    'A619GMUFirmware': FW/'a619_gmu.bin',
    'A630SQEFirmware': FW/'a630_sqe.fw',
    'A615ZapCode': FW/'a615_zap.b02',
}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--kernel',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    manifest_path,kernel,out = args.manifest.resolve(),args.kernel.resolve(),args.out.resolve()
    assert out.is_relative_to(REPO/'research/tmp') and not out.exists()
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest['state'] == 'built' and manifest['make_exit'] == 0
    assert manifest['machine'] == 'gauguin' and manifest['configuration'] == 'DEVELOPMENT'
    assert manifest['source']['path'] == str(REPO/'.deps-cache/p0-20261105/source304-sb-policy')
    assert sha(kernel) == manifest['kernel']['sha256']
    patch = REPO/'xnu/patches/0226-gauguin-springboard-dyld-rate-observer.patch'
    assert sha(patch) == '4dbca60cf2194256abb32da2d12e0adce20d5f7049ad8cef38d9495acc0af6e9'
    previous_path = W301/'research/tmp/ui301-image.json'
    previous = json.loads(previous_path.read_bytes())
    old_image = W301/'research/tmp/ui301-image.img'
    assert sha(old_image) == previous['image_sha256']
    assert previous['kernel_sha256'] == '8f8ddd92b49d08e166692da2e89c2ab271609d04bd1dbe2fd2f378215ffdaa42'
    assert previous['command'].count(' metal_fps=timeline') == 1
    assert 'sweet_sb_rate_probe=' not in previous['command']
    command = previous['command'].replace(' metal_fps=timeline','')+' sweet_sb_rate_probe=1'
    assert len(previous['command'].encode()) == 601 and len(command.encode()) == 604
    assert all(token in command.split() for token in ('sweettrace=2','touch_lat=1',
                                                      'sweetfb_hz=60','sweet_sb_rate_probe=1'))
    assert 'metal_fps=timeline' not in command.split()
    sys.path.insert(0,str(REPO/'tools'))
    import mkpayload
    from kernel_banner import one_banner
    assert len(command.encode()) < mkpayload.BOOT_LINE_LENGTH
    base_result = json.loads((MAIN/'research/tmp/gauguin-present-trace-worktree-20261112/research/tmp/dsh-present-native/image-result298.json').read_bytes())
    shim = SWIPE/'research/tmp/p3-low-pas-default-20261106-build/Image'
    dtb = SWIPE/'research/tmp/p0-ci-0100-20261105-wrapper/dtb'
    adt = SWIPE/'research/tmp/dsh-ui-0219-once-swipe/managed-6g.adt'
    assert sha(shim) == base_result['shim_sha256'] and sha(dtb) == base_result['dtb_sha256']
    for name,path in FIRMWARES.items():
        item = next(item for item in base_result['assets'] if item['name'] == name)
        assert sha(path) == item['source_sha256']
    parser_path = SWIPE/'research/tmp/dsh-0174/pack_native0174.py'
    spec = importlib.util.spec_from_file_location('bootparts',parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    old = parser.parts(old_image)
    assert old['kernel'] == shim.read_bytes() and old['dtb'] == dtb.read_bytes()
    blob,info = mkpayload.build(kernel,adt,command,None,FIRMWARES['NovatekFirmware'],
        pas_reservation=True,zap_mdt_path=FIRMWARES['A615ZapMDT'],
        gmu_firmware_path=FIRMWARES['A619GMUFirmware'],
        sqe_firmware_path=FIRMWARES['A630SQEFirmware'],
        zap_code_path=FIRMWARES['A615ZapCode'])
    assert blob[:8] == b'SWEETXNU' and blob[0x48:0x2a8].rstrip(b'\0') == command.encode()
    assert one_banner(blob).decode() == manifest['kernel_banner']
    assert info['ramdisk'] is None and info['low_pas_request']['state'] == 'pending-runtime-validation'
    assert struct.unpack_from('<2Q',blob,0x38) == (base_result['managed_RAM_base'],base_result['managed_RAM_bytes'])
    out.mkdir(parents=True)
    payload,image = out/'payload.bin',out/'image.img'
    with payload.open('xb') as stream:
        stream.write(blob);stream.flush();os.fsync(stream.fileno())
    subprocess.run([sys.executable,str(REPO/'tools/mkbootimg2.py'),str(image),
        '--kernel',str(shim),'--ramdisk',str(payload),'--dtb',str(dtb),
        '--cmdline','console=null','--os-version','17.0.0','--os-patch-level','2035-06'],check=True)
    new = parser.parts(image)
    assert new['kernel'] == old['kernel'] and new['dtb'] == old['dtb']
    assert new['geometry'] == old['geometry'] and new['header'][64:576] == old['header'][64:576]
    assert new['ramdisk'] == blob and one_banner(blob).decode() == manifest['kernel_banner']
    pins = {str(path):sha(path) for path in [manifest_path,kernel,patch,previous_path,old_image,
        shim,dtb,adt,parser_path,REPO/'tools/mkpayload.py',REPO/'tools/mkbootimg2.py',
        Path(__file__).resolve(),*FIRMWARES.values()]}
    assert all(sha(Path(path)) == digest for path,digest in pins.items())
    result = {'state':'offline-SpringBoard-rate-observer-image-not-device-qualified',
              'image':str(image),'image_sha256':sha(image),'image_bytes':image.stat().st_size,
              'payload_sha256':sha(payload),'kernel_sha256':sha(kernel),
              'kernel_banner':manifest['kernel_banner'],
              'build_identity':manifest['build_identity']['id'],
              'patch_sha256':sha(patch),'command':command,
              'command_sha256':hashlib.sha256(command.encode()).hexdigest(),
              'baseline_image_sha256':previous['image_sha256'],
              'input_pins':pins,'inputs_unchanged':True,
              'booted':False,'device_writes':0,'physical_fps_qualified':False}
    with (out/'result.json').open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps({key:value for key,value in result.items() if key!='input_pins'},indent=2))


if __name__ == '__main__':
    main()
