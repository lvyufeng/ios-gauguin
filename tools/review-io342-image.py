"""Independently inspect 0342's wrapper, Mach-O bytes, assets and linked symbols."""
from pathlib import Path
import hashlib
import json
import struct
import subprocess
import sys

R = Path(__file__).resolve().parents[1]
W = R/'research/tmp/io-path-342'
MAIN = Path('/Users/baai/Project/ios-gauguin')
W303 = MAIN/'research/tmp/gauguin-issued-fence-worktree-20261112'
sys.path.insert(0, str(R/'tools'))
import adt
from kernel_banner import one_banner


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def boot_parts(path):
    # Deliberately do not use either the packer or its legacy wrapper parser.
    data = Path(path).read_bytes()
    assert data[:8] == b'ANDROID!'
    ks, ka, rs, ra, ss, sa, tags, page, version, os_version = struct.unpack_from('<10I', data, 8)
    assert (ka, ra, ss, page, version) == (0x8000, 0x1000000, 0, 4096, 2)
    assert struct.unpack_from('<Q', data, 1632)[0] == 0
    assert struct.unpack_from('<I', data, 1644)[0] == 1660
    dtb_size, dtb_address = struct.unpack_from('<2Q', data, 1648)
    assert dtb_address == 0x1f00000
    pieces = {'header': data[:page]}
    offset = page
    for name, size in [('shim', ks), ('payload', rs), ('dtb', dtb_size)]:
        end = offset + size
        padded_end = (end+page-1)//page*page
        assert 0 < size and padded_end <= len(data)
        pieces[name] = data[offset:end]
        assert data[end:padded_end] == bytes(padded_end-end)
        offset = padded_end
    assert offset == len(data)
    return pieces


new_path = W/'io342-v4-image.json'
old_path = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-queue-loss-worktree-20261116/research/tmp/queue-loss-337/ui337-image.json')
new = json.loads(new_path.read_text())
old = json.loads(old_path.read_text())
assert sha(old_path) == '224af481d4423e6162781c81ed10027ba77062b66f898f65ebf990d329bd4b44'
assert sha(old['image']) == old['image_sha256'] == '765e7c7cc2efb84d24ee1404f94b3f866dcf98e04e6a755d53a808b35a3841f3'
assert sha(new['image']) == new['image_sha256']
assert sha(new['manifest']) == new['manifest_sha256']
manifest = json.loads(Path(new['manifest']).read_text())
assert manifest['identity']==new['build_identity']
base_path = MAIN/'research/tmp/gauguin-present-trace-worktree-20261112/research/tmp/dsh-present-native/image-result298.json'
base = json.loads(base_path.read_text())
before, after = boot_parts(old['image']), boot_parts(new['image'])
assert before['shim'] == after['shim'] and before['dtb'] == after['dtb']
assert before['header'][:16] == after['header'][:16] and before['header'][20:] == after['header'][20:]
op, np = before['payload'], after['payload']
assert op[:8] == np[:8] == b'SWEETXNU'
assert struct.unpack_from('<I', np, 8)[0] == 1
assert hashlib.sha256(np).hexdigest() == new['payload_sha256'] and len(np) == new['payload_bytes']
assert np[0x48:0x2a8].rstrip(b'\0').decode() == new['command']
assert old['command'].split().count('sweetgpumap=1')==1 and old['command'].split().count('gpf=4')==1
assert new['command'] == old['command']
assert op[0x48:0x2a8].rstrip(b'\0').decode() == old['command']
assert np[0x48:0x2a8] == new['command'].encode()+bytes(608-len(new['command'].encode()))
assert len(new['command'].encode()) == 607
nh, oh = struct.unpack_from('<7Q', np, 16), struct.unpack_from('<7Q', op, 16)
assert nh[5:] == oh[5:]
count = struct.unpack_from('<I', np, 12)[0]
assert count == 15
segments = [struct.unpack_from('<4Q', np, 0x2a8+i*32) for i in range(count)]
raw_path = Path(manifest['products']['candidate']['kernel'])
raw = raw_path.read_bytes()
assert sha(raw_path) == new['kernel_sha256'] == manifest['products']['candidate']['kernel_sha256']
assert struct.unpack_from('<II', raw) == (0xfeedfacf, 0x100000c)
offset, kernel_segments, entry, fixups = 32, [], None, 0
executable_ranges = []
for _ in range(struct.unpack_from('<I', raw, 16)[0]):
    command, size = struct.unpack_from('<II', raw, offset)
    assert size >= 8 and offset+size <= len(raw)
    if command == 0x19:
        va, vm, file_offset, file_size = struct.unpack_from('<4Q', raw, offset+24)
        if vm:
            kernel_segments.append((va, vm, file_offset, file_size))
            if struct.unpack_from('<I', raw, offset+60)[0] & 4:
                executable_ranges.append((va, va+file_size))
    elif command == 5:
        entry = struct.unpack_from('<Q', raw, offset+16+32*8)[0]
    elif command == 0x80000034:
        fixups += 1
    offset += size
assert len(kernel_segments) == 10 and nh[1] == entry and fixups == 0
for (va, vm, pos, size), (kva, kvm, kpos, ksize) in zip(segments[:10], kernel_segments):
    assert (va, vm, size) == (kva, kvm, ksize)
    assert np[pos:pos+size] == raw[kpos:kpos+ksize]
assert nh[0] == kernel_segments[0][0] & ~(0x2000000-1)
last_va, last_pos = nh[0], 0x2a8+count*32
for va, vm, pos, size in segments:
    assert va >= last_va and pos >= last_pos and 0 < size <= vm and pos+size <= nh[2]
    assert pos%8 == 0 and np[last_pos:pos] == bytes(pos-last_pos)
    assert nh[5] <= nh[5]+va-nh[0] and nh[5]+va-nh[0]+vm <= nh[5]+nh[6]
    last_va, last_pos = va+vm, pos+size
assert nh[4] == last_va
oroot, _ = adt.parse(op[oh[2]:oh[2]+oh[3]])
nroot, _ = adt.parse(np[nh[2]:nh[2]+nh[3]])


def flatten(node, path=None):
    path = '' if path is None else path+'/'+node.name
    values = {path+'/'+name: value for name, _, value in node.props}
    for child in node.children:
        values.update(flatten(child, path))
    return values


ov, nv = flatten(oroot), flatten(nroot)
assert set(ov) == set(nv)
changed = {key for key in ov if ov[key] != nv[key]}
allowed = {'/chosen/memory-map/'+item['name'] for item in base['assets']} | {'/chosen/LowPASRequest'}
assert changed <= allowed
assets = []
for (va, vm, pos, size), item in zip(segments[10:], base['assets']):
    pa, data, name = nh[5]+va-nh[0], np[pos:pos+size], item['name']
    assert vm == size == item['reserved']
    assert hashlib.sha256(data[:item['raw']]).hexdigest() == item['source_sha256']
    assert data[item['raw']:] == bytes(size-item['raw'])
    old_pa, old_size = struct.unpack('<2Q', ov['/chosen/memory-map/'+name])
    new_pa, new_size = struct.unpack('<2Q', nv['/chosen/memory-map/'+name])
    assert (new_pa, new_size) == (pa, old_size) and item['raw'] <= new_size <= size
    assets.append({'name': name, 'pa': pa, 'previous_pa': old_pa, 'raw': item['raw'], 'reserved': size})
magic, version, flags, tail, tail_bytes, region, alignment, total, reserved = struct.unpack_from('<8sII6Q', nv['/chosen/LowPASRequest'])
assert magic == b'LPASREQ1' and version == 1 and flags == reserved == 0
assert tail_bytes == 0x200000 and region == alignment == 0x100000
assert total == len(np) and tail+tail_bytes == total and tail%16384 == 0
assert tail >= nh[2]+nh[3] and not any(np[tail:])
assert one_banner(np).decode() == new['kernel_banner'] == manifest['kernel_banner']
assert new['build_identity'] in new['kernel_banner']

# Check real linked symbols and compare unresolved names against the fixed parent.
old_manifest = json.loads(Path(old['manifest']).read_text())
old_kernel = Path(old_manifest['kernel']['path'])
def nm(*args):
    return subprocess.check_output(['xcrun', 'nm', *map(str, args)], text=True)
old_undefined = sorted(nm('-u', old_kernel).splitlines())
new_undefined = sorted(nm('-u', raw_path).splitlines())
assert old_undefined == new_undefined
definitions = nm(raw_path)
symbols = ['copyTraceState', 'IOHIDEventServiceUserClient12initWithTask', '_sweet_amfi_policy_register', '_sweet_sb_inject_subject', '_sweet_sample_start', '_sweet_sample_task','_sweet_gpu_runtime_pending_metadata','_gmf_bootstrap_dcvs565_once']
symbols += ['_gut_record', '_gut_report', '_gut_read', 'invalidateHeldRetryLocked', 'finishHeldFrameEP14sweet_fb_frameb','_thread_tid']
assert b'SWEET BC335: enabled slots=32 bytes=16777216 max_bo=1048576 zero=1' in raw
assert b'SWEET FB RETRY332: enabled max_retries=8; GPU read guards retained' in raw
assert b'SWEET FB RETRY332: requeued=%llu newer=%llu canceled=%llu exhausted=%llu; max_retries=8' in raw
assert b'SWEET SB DYLD PROBE' in raw and b'SWEET SB INJECT' in raw and b'sbp\x00' in raw
assert manifest['actual_implementation_object_replacements']==1 and manifest['baseline_raw_and_stripped_equal_except_LC_UUID']
assert b'SWEET IO342: begin version=1' in raw and b'SWEET IO342: row' in raw
symbols+=['_thread_get_runtime_self','_sweet_log_append']
assert b'version=2 count=' in raw
assert b'SWEET GPU MAP324: enabled=' in raw and b'sweetgpumap\x00' in raw
assert b'perf_index=4 hz=565000000 bw_index=9 Bps=5412000000' in raw and b'gpf\x00' in raw
assert b'SWEET GS328: %08x %016llx' in raw and b'SWEET GS328: limit=64 coverage=incomplete' in raw
assert b'SWEET GPU SUBMIT327: seq=' not in raw
assert b'SMP316 armed' in raw and b'SMP328 armed' in raw and b'SMP%d end cycle=' in raw and b'gsp\x00' in raw
assert b'SMP328 refused: reason=deadline cycle=' in raw
assert b'caller=%d flags=%x init=%u shadow=%u ppid=%d' in raw
found = []
for name in symbols:
    matches = [line for line in definitions.splitlines() if name in line]
    assert len(matches) == 1, (name, matches)
    # Kernel functions live in __TEXT_EXEC; nm labels that section S rather
    # than T. Verify their actual addresses against Mach-O execute protection.
    address = int(matches[0].split()[0], 16)
    assert any(start <= address < end for start, end in executable_ranges)
    found.append(matches[0])
result = {
    'state': 'reviewed-offline-io-path342-image', 'image_sha256': new['image_sha256'],
    'kernel_sha256': new['kernel_sha256'], 'outer_header_changes_limited_to_payload_size': True,
    'shim_dtb_and_padding_verified': True, 'raw_MachO_segment_bytes_verified': True,
    'chained_fixups': fixups, 'command_bytes': 607, 'command_changes_from_0337': new['command_changes_from_0337'],
    'adt_changes': sorted(changed), 'assets': assets, 'low_pas_request_checked': True,
    'linked_patch_symbols': found, 'undefined_symbols_unchanged': True,
    'undefined_symbol_count': len(new_undefined), 'device_writes': 0, 'booted': False,
    'physical_fps_qualified': False, 'script_sha256': sha(Path(__file__).resolve()),
}
(W/'io342-v4-review.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
