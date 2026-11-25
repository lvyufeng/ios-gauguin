#!/usr/bin/env python3
"""Bind the fixed 0392 GPU vote to the captured stock Android operating point."""

import argparse
from importlib import import_module
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-392'
P391 = MAIN/'research/tmp/gauguin-frame391-pending-swap-worktree-20261123/research/tmp/frame-391'
NATIVE = P391/'native-kernel/build-manifest.json'
DONOR = (MAIN/'research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331'
         /'kernel-native-v1/result.json')
PATCH = WORK/'graphics/gauguin-display/0392-android-stock-gpu-operating-point.patch'
FIXTURE = WORK/'tests/fixtures/gmu-firmware/firmware_host.c'
TEST = WORK/'tests/test_gmu_firmware.py'
CAPTURE = MAIN/'research/tmp/dsh-0139/policy-capture.json'
STOCK = CAPTURE.with_name('policy-audit.json')
PROFILE = dict(argument='gpf=5',frequency_hz=650_000_000,perf_index=5,bw_index=10,
               bandwidth_bytes_per_second=6_220_000_000,ARC_virtual_level=320,GX_index=5,MX_index=6)
COMPILER = Path('/Library/Developer/CommandLineTools/usr/bin')


def checked(argv, **kwargs):
    result = subprocess.run(argv,capture_output=True,text=True,timeout=180,**kwargs)
    require(result.returncode==0,result.stderr[-2500:]+result.stdout[-1000:])
    return result.stdout


def stock_policy():
    original = load(STOCK)
    require(all(sha(MAIN/path)==digest for path,digest in original['input_pins'].items()),
            'stock policy inputs differ')
    capture = load(CAPTURE)
    data = {row['path']:MAIN/row['output'] for row in capture['records']}
    fdt = data['/sys/firmware/fdt']
    gpu = '/sys/class/kgsl/kgsl-3d0/'
    freqs = [int(n) for n in data[gpu+'gpu_available_frequencies'].read_text().split()]
    require(freqs==original['active_frequencies_hz'] and freqs[:3]==[800_000_000,650_000_000,565_000_000] and
            original['off_inclusive_ascending_hz_arc_vlvl'][5]==[650_000_000,320],
            'retained Android power table differs')
    bin_path = original['matching_live_dt_bin']
    require(original['matching_bin_property']==169 and bin_path.endswith('/qcom,gpu-pwrlevels-2'),
            'retained Android active bin differs')
    level = bin_path+'/qcom,gpu-pwrlevel@1'
    properties = ('reg','qcom,gpu-freq','qcom,bus-freq','qcom,bus-min','qcom,bus-max')
    rows = [int(checked(['fdtget','-t','u',str(fdt),level,key])) for key in properties]
    require(rows==[1,650_000_000,10,8,12],'retained board policy has a different 650 MHz bandwidth row')
    return dict(linux_powerlevel=rows[0],bw_range=rows[-2:],max_stock_frequency_hz=freqs[0],
                active_dt_bin=169,input_pins={str(STOCK):sha(STOCK),
                   **{str(MAIN/path):digest for path,digest in original['input_pins'].items()}})


def host():
    original = load(NATIVE)
    policy = stock_policy()
    with TemporaryDirectory(prefix='0392-host-',dir=BASE) as temporary:
        source = Path(temporary)/'source'
        shutil.copytree(original['source'],source)
        checked(['patch','-p1','-F','0','-i',str(PATCH)],cwd=source)
        output = checked([sys.executable,str(TEST)],env=dict(os.environ,XNU_SOURCE=str(source)))
    require(all('exact6 stores TCM'+wire in output for wire in (
        '30000001/00005005','30000004/00009009','30000005/0000a00a')),
        'host did not prove all three exact native votes')
    require('0x01400605,650000' in FIXTURE.read_text(),'650 MHz table oracle missing')
    return dict(state='0392-stock-650-guarded-OOB-offline-verified',profile=PROFILE,policy=policy,
                results=output.splitlines(),patch_sha256=sha(PATCH),fixture_sha256=sha(FIXTURE),device_commands=0)


def native():
    import_module('prepare-frame392').admitted()
    old,donor,offline = (load(path) for path in (NATIVE,DONOR,BASE/'offline.json'))
    require(offline['patch_sha256']==sha(PATCH) and offline['fixture_sha256']==sha(FIXTURE) and
            not offline['device_commands'] and donor['inputs_unchanged'],'0392 host inputs differ')
    # The archived recipe predates the steps manifest format. Match its
    # preimages and object bytes to the reproduced 0391 filelist before adapting it.
    recipe = BASE/'native-recipe.json'
    steps = []
    for item in donor['results']:
        name = Path(item['file']).stem
        object_path = item['object']
        require(sha(object_path)==item['object_sha256']==old['input_pins'][object_path],
                'GMU object is absent from the 0391 baseline')
        steps.append(dict(name='compile-'+name,argv=item['arguments'],cwd=item['cwd'],exit=item['exit']))
    require({step['name'] for step in steps}=={'compile-gauguin_gmu_board','compile-gauguin_gmu_firmware'},
            'unexpected kernel build recipe')
    with recipe.open('x') as stream:
        json.dump(dict(source_receipt=str(DONOR),source_sha256=sha(DONOR),steps=steps),stream,indent=2)
        stream.write('\n')
    output = BASE/'native-kernel'
    import_module('build-frame347').link_scanout(NATIVE,output,parent_trial='0391',trial='0392',
        patches=(PATCH,),extra_units=tuple((step['name'].removeprefix('compile-'),recipe,step['name']) for step in steps),
        recompile_scanout=False,compiler_bin=COMPILER)
    result = load(output/'build-manifest.json')
    for before, after in result['object_replacements'].items():
        old_refs,new_refs = (set(checked(['nm','-uj',str(path)]).splitlines()) for path in (before,after))
        added = {'_gmf_bootstrap_dcvs650_once'} if Path(after).stem=='gauguin_gmu_board' else set()
        require(new_refs-old_refs==added and not old_refs-new_refs,'unexpected GMU import change')
    return dict(kernel_sha256=result['kernel_sha256'],identity=result['identity'])


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('stock_policy','host','native'))
    args = parser.parse_args()
    print(json.dumps(globals()[args.stage](),indent=2))
