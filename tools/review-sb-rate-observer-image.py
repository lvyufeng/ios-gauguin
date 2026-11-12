#!/usr/bin/env python3
"""Independently compare the offline SB observer image to the pinned 0301 image."""

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path


MAIN = Path('/Users/baai/Project/ios-gauguin')
SWIPE = MAIN/'research/tmp/gauguin-swipe219-worktree-20261110'
PARSER = SWIPE/'research/tmp/dsh-0174/pack_native0174.py'
ASSETS = MAIN/'research/tmp/gauguin-present-trace-worktree-20261112/research/tmp/dsh-present-native/image-result298.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('baseline_result','candidate_result','manifest','out'):
        ap.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    args = ap.parse_args()
    out = args.out.resolve()
    assert not out.exists()
    old = json.loads(args.baseline_result.read_bytes())
    new = json.loads(args.candidate_result.read_bytes())
    manifest = json.loads(args.manifest.read_bytes())
    base = json.loads(ASSETS.read_bytes())
    spec = importlib.util.spec_from_file_location('bootparts',PARSER)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    old_image,new_image = Path(old['image']),Path(new['image'])
    assert sha(old_image) == old['image_sha256'] and sha(new_image) == new['image_sha256']
    outer_old,outer_new = parser.parts(old_image),parser.parts(new_image)
    assert outer_old['geometry'] == outer_new['geometry']
    assert outer_old['header'][64:576] == outer_new['header'][64:576]
    assert outer_old['kernel'] == outer_new['kernel'] and outer_old['dtb'] == outer_new['dtb']
    payload_old,payload_new = outer_old['ramdisk'],outer_new['ramdisk']
    assert payload_old[:8] == payload_new[:8] == b'SWEETXNU'
    assert payload_old[0x48:0x2a8].rstrip(b'\0') == old['command'].encode()
    assert payload_new[0x48:0x2a8].rstrip(b'\0') == new['command'].encode()
    assert new['command'] == old['command'].replace(' metal_fps=timeline','')+' sweet_sb_rate_probe=1'
    assert len(new['command'].encode()) == 604
    assert hashlib.sha256(new['command'].encode()).hexdigest() == new['command_sha256']
    count = struct.unpack_from('<I',payload_old,12)[0]
    assert count == struct.unpack_from('<I',payload_new,12)[0] == 15
    old_head,new_head = struct.unpack_from('<7Q',payload_old,16),struct.unpack_from('<7Q',payload_new,16)
    assert all(old_head[i] == new_head[i] for i in (0,1,3,5,6))
    vm_shift = new_head[4]-old_head[4]
    assert 0 <= vm_shift <= 65536 and vm_shift%4096 == 0
    segments = lambda blob:[struct.unpack_from('<4Q',blob,0x2a8+32*i) for i in range(count)]
    old_seg,new_seg = segments(payload_old),segments(payload_new)
    assert old_seg[:2] == new_seg[:2]
    assert new_seg[2][0] == old_seg[2][0] and new_seg[2][1] == old_seg[2][1]+vm_shift
    assert new_seg[2][2] == old_seg[2][2] and new_seg[2][3] == old_seg[2][3]+vm_shift
    assert all(b[0] == a[0]+vm_shift and b[1] == a[1] and
               b[2] == a[2]+vm_shift and b[3] == a[3]
               for a,b in zip(old_seg[3:9],new_seg[3:9]))
    assert new_seg[9][0] == old_seg[9][0]+vm_shift and new_seg[9][1] == old_seg[9][1]
    assert new_seg[9][2] == old_seg[9][2]+vm_shift and new_seg[9][3] >= old_seg[9][3]
    shifts = {b[2]-a[2] for a,b in zip(old_seg[10:],new_seg[10:])}
    assert len(shifts) == 1 and all(a[3] == b[3] for a,b in zip(old_seg[10:],new_seg[10:]))
    shift = shifts.pop()
    assert shift == vm_shift + new_seg[9][3]-old_seg[9][3]
    assert new_head[2]-old_head[2] == shift
    assert new_seg[10][0] == new_seg[9][0]+new_seg[9][1]
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
    import adt
    def tree(blob,head):
        raw = blob[head[2]:head[2]+head[3]]
        root,end = adt.parse(raw)
        assert end == len(raw)
        chosen = next(node for node in root.children if node.name == 'chosen')
        mmap = next(node for node in chosen.children if node.name == 'memory-map')
        return root,chosen,mmap
    old_tree,old_chosen,old_map = tree(payload_old,old_head)
    new_tree,new_chosen,new_map = tree(payload_new,new_head)
    names = {item['name'] for item in base['assets']}
    def scrub(node):
        props = []
        for name,flags,value in node.props:
            if name in names:
                pa,length = struct.unpack('<2Q',value)
                assert pa and length
                value = struct.pack('<2Q',0,length)
            elif name == 'LowPASRequest':
                assert len(value) >= 64 and value[:8] == b'LPASREQ1'
                mutable = bytearray(value)
                mutable[16:24] = bytes(8)
                mutable[48:56] = bytes(8)
                value = bytes(mutable)
            props.append((name,flags,value))
        return node.name,props,[scrub(child) for child in node.children]
    assert scrub(old_tree) == scrub(new_tree)
    def properties(node):
        return {name:(flags,value) for name,flags,value in node.props}
    old_properties,new_properties = properties(old_map),properties(new_map)
    assert len(old_properties) == len(old_map.props) and len(new_properties) == len(new_map.props)
    adt_sizes = {'NovatekFirmware':139264,'A615ZapMDT':16384,'A619GMUFirmware':32768,
                 'A630SQEFirmware':32304,'A615ZapCode':1984}
    new_pa_list = []
    assets = {item['name']:item for item in base['assets']}
    for old_entry,new_entry,name in zip(old_seg[10:],new_seg[10:],assets):
        item = assets[name]
        assert new_entry[0] == old_entry[0]+vm_shift
        old_pa = old_entry[0]-old_head[0]+old_head[5]
        new_pa = new_entry[0]-new_head[0]+new_head[5]
        assert old_pa == item['pa'] and new_pa == old_pa+vm_shift
        assert new_pa%16384 == 0 and old_head[5] <= new_pa < old_head[5]+old_head[6]
        assert new_pa+item['reserved'] <= old_head[5]+old_head[6]
        assert old_properties[name] == (0,struct.pack('<2Q',old_pa,adt_sizes[name]))
        assert new_properties[name] == (0,struct.pack('<2Q',new_pa,adt_sizes[name]))
        new_pa_list.append(new_pa)
        assert old_entry[1] == new_entry[1] == item['reserved']
        before = payload_old[old_entry[2]:old_entry[2]+old_entry[3]]
        after = payload_new[new_entry[2]:new_entry[2]+new_entry[3]]
        assert before == after and after[item['raw']:] == bytes(item['reserved']-item['raw'])
        assert hashlib.sha256(after[:item['raw']]).hexdigest() == item['source_sha256']
    assert all(right == left+assets[name]['reserved'] for left,right,name in
               zip(new_pa_list,new_pa_list[1:],list(assets)[:-1]))
    pas = properties(new_chosen)['LowPASRequest'][1]
    tail,total = struct.unpack_from('<Q',pas,16)[0],struct.unpack_from('<Q',pas,48)[0]
    assert tail == (new_head[2]+new_head[3]+16383)&~16383
    assert total == tail+0x200000 == len(payload_new)
    assert manifest['state'] == 'built' and manifest['make_exit'] == 0
    assert manifest['kernel']['sha256'] == new['kernel_sha256']
    assert manifest['kernel_banner'] == new['kernel_banner']
    assert manifest['build_identity']['id'] == new['build_identity']
    kernel = Path(manifest['kernel']['path'])
    assert sha(kernel) == new['kernel_sha256']
    data = kernel.read_bytes()
    assert b'sweet_sb_rate_probe' in data and b'SWEET SB DYLD PROBE' in data
    report = {'state':'independent-offline-SpringBoard-rate-image-review',
              'baseline_image_sha256':old['image_sha256'],
              'image_sha256':new['image_sha256'],'kernel_sha256':new['kernel_sha256'],
              'build_identity':new['build_identity'],
              'outer_geometry_shim_dtb_identical':True,
              'adt_unchanged_except_firmware_pa_and_PAS_tail':True,
              'firmware_content_padding_unchanged':True,
              'firmware_pa_shift_bytes':vm_shift,
              'kernel_segment_vm_relocation_bytes':vm_shift,
              'kernel_segment_file_growth_bytes':new_seg[9][3]-old_seg[9][3],
              'asset_payload_shift_bytes':shift,
              'new_policy_symbols_in_kernel':True,
              'booted':False,'device_writes':0,'physical_fps_qualified':False}
    with out.open('x') as stream:
        json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
