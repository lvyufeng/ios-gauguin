#!/usr/bin/env python3
"""Make a bounded trace command from the qualified desktop profile; no device IO."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,struct,sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mkpayload import encode_cmdline,BOOT_LINE_LENGTH

SOURCE='24577f7277a76e15d84d157ce45a8f1077c22db3bf19b678a6813544782b4f6f'
BASE_IMAGE='18d3196f5827e7105c7b598c2951596f25f56449330223cbc9530ff3d4f1f72f'
BASE_KERNEL='dc220b5b24c38f0bd641c2a41693ba664447d18a0735e8c342df6b2fbfd8cae8'
OLD='sweettrial=gwrt-0175-a1'
def need(ok,message):
    if not ok:raise ValueError(message)
def sha(p):
    with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def trace_command(command,gesture):
    need(type(gesture)is int and 1<=gesture<=16,'gesture must be an integer from1 through16')
    encode_cmdline(command)
    words=command.split();need(' '.join(words)==command,'canonical command spacing required')
    keys=[w.split('=',1)[0]for w in words];need(len(set(keys))==len(keys),'duplicate boot key')
    need(words.count(OLD)==1 and 'sweettrace'not in keys,'expected unused trial tag, no existing trace key')
    for token in ['sweet_dyld_probe=1','sweeteagl=2','gmt=2','sweetfb_hz=60']:
        need(words.count(token)==1,'exact desktop selectors required')
    index=words.index(OLD);out=words.copy();out[index]='sweettrace='+str(gesture)
    result=' '.join(out);encoded=encode_cmdline(result)
    need(len(encoded)<BOOT_LINE_LENGTH,'trace command exceeds payload ABI')
    need(out[:index]+out[index+1:]==words[:index]+words[index+1:],'non-metadata boot arguments changed')
    return result
def prepare(base_path,source_path,native_path,gesture,out):
    repo=Path(__file__).resolve().parents[1]
    base=json.loads(base_path.read_text());source=json.loads(source_path.read_text());native=json.loads(native_path.read_text())
    need(base['state']=='offline250-complete-desktop-image-not-installed-or-phone-qualified'and
         base['image_sha256']==BASE_IMAGE and base['kernel_sha256']==BASE_KERNEL,'qualified250 base identity')
    need(sha(base['image'])==BASE_IMAGE,'base image bytes changed')
    need(base['command_bytes']==607 and base['command_field_bytes']==608 and base['command_roundtrip_complete'],'qualified607-byte command')
    need(len(base['command'].encode())==607,'base command length')
    spec=importlib.util.spec_from_file_location('trace_profile_manifest',repo/'tools/xnu-build-manifest.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    actual=m.snapshot(Path(source['source']))
    need(actual==source['snapshot'] and actual['sha256']==SOURCE and actual['files']==5335,'qualified208 source changed')
    need(source['active_patches']==208,'kernel patch count')
    # This exact tree has no direct consumer of the former label. Do not drop
    # a key from a future kernel merely because this revision did not use it.
    for name,kind,pin in actual['entries']:
        if kind!='symlink':need(b'sweettrial'not in (Path(source['source'])/name).read_bytes(),'trial tag has a source consumer: '+name)
    need(native['state']=='passed-native-ARM64-selected-TUs'and native['inputs_unchanged'] and
         native['reference_files_unchanged']and native['candidate_export_overrides_unchanged'],'native qualification')
    expected={'bsd/dev/gauguin_ui_trace.c','bsd/dev/gauguin_ui_trace_board.c','bsd/dev/gauguin_nvt/runtime/nvt_runtime.c',
              'bsd/dev/sweet_ufs.c','bsd/dev/gauguin_gmu_board.c','bsd/kern/bsd_init.c',
              'iokit/Kernel/arm/GauguinGPU.cpp','iokit/Kernel/arm/hid/SweetHID.cpp','iokit/Kernel/arm/SweetFramebuffer.cpp'}
    need({r['file']for r in native['results']}==expected,'native TU coverage')
    for name,pin in native['input_pins'].items():need(sha(name)==pin,'native input changed: '+name)
    for row in native['results']:
        p=Path(row['object']);need(row['exit']==0 and row['full_candidate_includes']and sha(p)==row['object_sha256'],'native object')
        h=struct.unpack_from('<8I',p.read_bytes());need(h[:2]==(0xfeedfacf,0x100000c)and h[3]==1,'ARM64 object')
    command=trace_command(base['command'],gesture)
    result={'state':'reviewed-trace-command-not-kernel-or-image','command':command,'command_bytes':len(command.encode()),
        'command_field_bytes':608,'gesture':gesture,'removed_unconsumed_metadata':OLD,'source_sha256':SOURCE,
        'all_other_token_bytes_and_order_preserved':True,'base_image_sha256':BASE_IMAGE,
        'requires_full_kernel_build_and_image_qualification':True,'requires_0240_and_exact_paired239_trial_first':True,
        'requires_0250_desktop_correctness_first':True,'device_commands':0,'hardware_qualified':False,
        'input_pins':{str(p.resolve()):sha(p)for p in [base_path,source_path,native_path,Path(__file__),repo/'tools/mkpayload.py']}}
    need(out.resolve().is_relative_to(repo/'research/tmp')and not out.exists(),'fresh private output required')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x')as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['state','command_bytes','gesture','hardware_qualified']}))
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['base','source-proof','native-proof','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--gesture',type=int,default=2);a=p.parse_args()
    prepare(a.base,a.source_proof,a.native_proof,a.gesture,a.out)
if __name__=='__main__':main()
