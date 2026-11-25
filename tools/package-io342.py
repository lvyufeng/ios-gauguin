"""Package 0337 concurrent collectors with the unchanged0336 boot command.

The payload is kept in memory and written once inside the boot image, avoiding
a redundant disk copy under the project cap. This script never touches a phone.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import struct
import sys

R = Path(__file__).resolve().parents[1]
W = R/'research/tmp/io-path-342'
MAIN = Path('/Users/baai/Project/ios-gauguin')
W303 = MAIN/'research/tmp/gauguin-issued-fence-worktree-20261112'
W300 = MAIN/'research/tmp/gauguin-present-trace-worktree-20261112'
W219 = MAIN/'research/tmp/gauguin-swipe219-worktree-20261110'
OLD_PATH = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/ui337-image.json')
REVIEW_PATH = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/ui337-review.json')
BASE_PATH = W300/'research/tmp/dsh-present-native/image-result298.json'
MANIFEST_PATH = W/'kernel-link-v4/build-manifest.json'
IMAGE = W/'io342-v4-image.img'
RESULT = W/'io342-v4-image.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


assert not IMAGE.exists() and not RESULT.exists()
assert sha(OLD_PATH) == '224af481d4423e6162781c81ed10027ba77062b66f898f65ebf990d329bd4b44'
assert sha(REVIEW_PATH) == '022b26ca9a9812136123533f22e6b8a95fab68844ea0c963dd2d604041a5e9d3'
old = json.loads(OLD_PATH.read_text())
base = json.loads(BASE_PATH.read_text())
manifest = json.loads(MANIFEST_PATH.read_text())
assert manifest['state']=='0342-linked-exact337-baseline-and-one-driver-diagnostic-replacement'
assert manifest['inputs_unchanged'] and manifest['baseline_raw_and_stripped_equal_except_LC_UUID']
assert sha(MANIFEST_PATH)=='36a8c331f2925cad8c6d5e0f3ab87bf39caf6a00e2db01b07bcf5a54513e3e36'
kernel = Path(manifest['products']['candidate']['kernel'])
assert sha(kernel) == manifest['products']['candidate']['kernel_sha256']
old_image = Path(old['image'])
assert sha(old_image) == old['image_sha256'] == '765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
shim = W219/'research/tmp/p3-low-pas-default-20261106-build/Image'
dtb = W219/'research/tmp/p0-ci-0100-20261105-wrapper/dtb'
adt_path = W219/'research/tmp/dsh-ui-0219-once-swipe/managed-6g.adt'
fw = W219/'research/tmp/p3-gpu-inventory-20261105/firmware'
firmwares = {
    'NovatekFirmware': W219/'research/tmp/gauguin-novatek-reference/novatek_nt36672c_j17_fw01.bin',
    'A615ZapMDT': fw/'a615_zap.mdt', 'A619GMUFirmware': fw/'a619_gmu.bin',
    'A630SQEFirmware': fw/'a630_sqe.fw', 'A615ZapCode': fw/'a615_zap.b02',
}
assert sha(shim) == base['shim_sha256'] and sha(dtb) == base['dtb_sha256']
for name, path in firmwares.items():
    assert sha(path) == next(item['source_sha256'] for item in base['assets'] if item['name'] == name)
parser_path = W219/'research/tmp/dsh-0174/pack_native0174.py'
inputs = [Path(__file__).resolve(), OLD_PATH, REVIEW_PATH, BASE_PATH, MANIFEST_PATH,
          kernel, old_image, shim, dtb, adt_path, parser_path,
          R/'tools/mkpayload.py', R/'tools/adt.py', R/'tools/kernel_banner.py', *firmwares.values()]
pins = {str(p): {'sha256': sha(p), 'mtime_ns': p.stat().st_mtime_ns} for p in inputs}
for name in ['mkpayload.py', 'adt.py', 'kernel_banner.py']:
    assert sha(R/'tools'/name) == sha(W303/'tools'/name), name
spec = importlib.util.spec_from_file_location('bootparts316', parser_path)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
parts = parser.parts(old_image)
assert parts['kernel'] == shim.read_bytes() and parts['dtb'] == dtb.read_bytes()
assert len(old['command'].encode()) == 607 and 'gsp=328' in old['command'].split()
assert old['command'].split().count('sweetgpumap=1')==1 and old['command'].split().count('gpf=4')==1
command=old['command']
assert len(command.encode())==607 and command.split().count('sweetgpumap=1')==1
assert command.split().count('gpf=4') == 1 and command.split().count('gsp=328') == 1
assert 'sbp=1' in command.split()
assert 'swp=3' in command.split() and 'sweetgpuasync=1' in command.split() and 'sweetnvt=0' in command.split()
sys.path.insert(0, str(R/'tools'))
import mkpayload
from kernel_banner import one_banner
blob, info = mkpayload.build(kernel, adt_path, command, None, firmwares['NovatekFirmware'],
    pas_reservation=True, zap_mdt_path=firmwares['A615ZapMDT'],
    gmu_firmware_path=firmwares['A619GMUFirmware'], sqe_firmware_path=firmwares['A630SQEFirmware'],
    zap_code_path=firmwares['A615ZapCode'])
assert blob[:8] == b'SWEETXNU' and blob[0x48:0x2a8].rstrip(b'\0') == command.encode()
assert one_banner(blob).decode() == manifest['kernel_banner']
assert info['ramdisk'] is None and info['low_pas_request']['state'] == 'pending-runtime-validation'
assert struct.unpack_from('<2Q', blob, 0x38) == (base['managed_RAM_base'], base['managed_RAM_bytes'])
header = bytearray(parts['header'])
page = struct.unpack_from('<I', header, 36)[0]
assert page == len(header) == 4096
struct.pack_into('<I', header, 16, len(blob))
expected_size = page + sum((len(data)+page-1)//page*page for data in [parts['kernel'], blob, parts['dtb']])
link_bytes = sum(p.stat().st_size for p in (W/'kernel-link-v4').rglob('*') if p.is_file())
assert link_bytes + expected_size + 1_000_000 <= 200_000_000
with IMAGE.open('xb') as stream:
    stream.write(header)
    for data in [parts['kernel'], blob, parts['dtb']]:
        stream.write(data)
        stream.write(bytes(-len(data) % page))
    stream.flush()
    os.fsync(stream.fileno())
assert IMAGE.stat().st_size == expected_size
new = parser.parts(IMAGE)
assert new['geometry'] == parts['geometry'] and new['kernel'] == parts['kernel'] and new['dtb'] == parts['dtb']
assert new['header'] == bytes(header) and new['ramdisk'] == blob
assert all(sha(name) == pin['sha256'] and Path(name).stat().st_mtime_ns == pin['mtime_ns'] for name, pin in pins.items())
result = {
    'state': 'offline-io-path342-candidate', 'image': str(IMAGE),
    'image_sha256': sha(IMAGE), 'image_bytes': expected_size,
    'payload_sha256': hashlib.sha256(blob).hexdigest(), 'payload_bytes': len(blob), 'separate_payload_file': False,
    'kernel_sha256': sha(kernel), 'kernel_banner': manifest['kernel_banner'],
    'build_identity': manifest['identity'], 'project_revision': None,
    'command': command, 'command_sha256': hashlib.sha256(command.encode()).hexdigest(),
    'command_changes_from_0337': [], 'baseline_image_sha256': old['image_sha256'],
    'manifest': str(MANIFEST_PATH), 'manifest_sha256': sha(MANIFEST_PATH),
    'input_pins': pins, 'inputs_unchanged': True, 'build_method': 'verified-local-incremental-link',
    'booted': False, 'device_writes': 0, 'physical_fps_qualified': False, 'physical_touch_qualified': False,
    'scope': 'Bounded driver phase/CPU diagnostics; original FIFO/cache/fence/escrow and565/BW9/UI sampling retained; new individual342 approval required',
}
RESULT.write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({key: result[key] for key in ['state', 'image_sha256', 'image_bytes', 'kernel_sha256', 'build_identity', 'command_changes_from_0337', 'inputs_unchanged', 'booted']}, indent=2))
