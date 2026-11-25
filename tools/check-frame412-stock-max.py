#!/usr/bin/env python3
"""Validate the same phone's highest stock Android 60 Hz GPU operating point."""

import argparse
from contextlib import redirect_stdout
from difflib import unified_diff
from importlib import import_module
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

prior = import_module('check-frame409-bandwidth')
phase = import_module('check-frame410-phase')
BASE = WORK/'research/tmp/frame-412'
P411 = MAIN/'research/tmp/gauguin-frame411-linear-view-worktree-20261124/research/tmp/frame-411'
ADMISSION = P411/'offline-0412-batch-admission.json'
REFERENCE = phase.source_manifest('0409')
KERNEL = BASE/'native-kernel-stock-scope/build-manifest.json'
HOST = BASE/'stock-scope-offline.json'
PATCH = BASE/'412-stock-800MHz-existing-scope.patch'
BOARD = Path('bsd/dev/gauguin_gmu_board.c')
FIRMWARE = Path('bsd/dev/gauguin_gmu_firmware.c')
DECLARATIONS = FIRMWARE.with_suffix('.h')
FIXTURE = WORK/'tests/fixtures/gmu-firmware/firmware_host.c'
TEST = WORK/'tests/test_gmu_firmware.py'
PROFILE = dict(perf_index=6,frequency_hz=800_000_000,bw_index=12,
               bandwidth_bytes_per_second=8_371_200_000,bw_word=0x0000c00c,
               arc_virtual_level=384,gx_index=6,mx_index=7)


def replace(source,before,after):
    require(source.count(before)==1,'unexpected stock GPU substitution: '+before.splitlines()[0])
    return source.replace(before,after,1)


def admitted():
    result = load(ADMISSION)
    require(result['admitted'] and result['planned_batch_bytes']==310_000_000 and
            result['current_accounted_bytes']+result['planned_batch_bytes']<=result['limit_bytes'],
            '0412 build and 0411 runtime exceed the complete offline batch')


def stock():
    parent = prior.stock()
    policy,capture = load(prior.STOCK),load(prior.CAPTURE)
    fdt, = (MAIN/row['output'] for row in capture['records'] if row['path']=='/sys/firmware/fdt')
    row = policy['matching_live_dt_bin']+'/qcom,gpu-pwrlevel@0'
    values = [int(prior.checked(['fdtget','-t','u',str(fdt),row,prop]).strip()) for prop in
        ('reg','qcom,gpu-freq','qcom,bus-freq','qcom,bus-min','qcom,bus-max')]
    require(policy['active_frequencies_hz'][0]==800_000_000 and
            policy['off_inclusive_ascending_hz_arc_vlvl'][6]==[800_000_000,384] and
            values==[0,800_000_000,12,10,12] and parent['native_vectors_kbps'][12]==8_371_200,
            'same handset stock clock, ARC or GPU-DDR vote differs')
    return dict(bin=169,linux_row=0,bus_range=[10,12],kernel_profile=PROFILE,input_pins=parent['input_pins'])


def board(source):
    source = replace(source,'''    const bool bw11=dcvs&&gfw_frame409_bw11(profile,sqe);
    if(bw11){
        gfw_work.result=gmf_bootstrap_dcvs650_bw11_once(&gfw_context,&ops,plan,bw,&gfw_work.firmware);''',
        '''    // Only this kernel's bounded 0409 scripted scope selects the stock top row.
    const bool stock800=dcvs&&gfw_frame409_bw11(profile,sqe);
    if(stock800){
        gfw_work.result=gmf_bootstrap_dcvs800_once(&gfw_context,&ops,plan,bw,&gfw_work.firmware);''')
    return replace(source,'''        if(bw11)gmb_record("SWEET GMU DCVS: request perf_index=5 hz=650000000 bw_index=11 Bps=7216000000 option=00000000 perf=30000005 bw=0000b00b; requested, not measured");''',
        '''        if(stock800)gmb_record("SWEET GMU DCVS: request perf_index=6 hz=800000000 bw_index=12 Bps=8371200000 option=00000000 perf=30000006 bw=0000c00c; requested, not measured");''')


def patch(tree):
    definitions = '''enum gmf_result gmf_bootstrap_dcvs800_once(struct gmf_context *c,const struct gmf_ops *ops,
    const struct gmf_plan *plan,const struct gmf_bw_plan *bw,struct gmf_receipt *out)
{
    if(!bw)return GMF_ARGUMENT;
    return bootstrap(c,ops,plan,out,true,bw,6,12);
}
'''
    declares = '''enum gmf_result gmf_bootstrap_dcvs800_once(struct gmf_context *,const struct gmf_ops *,
    const struct gmf_plan *,const struct gmf_bw_plan *,struct gmf_receipt *);
'''
    edited = {BOARD:board((tree/BOARD).read_text()),FIRMWARE:(tree/FIRMWARE).read_text()+definitions,
              DECLARATIONS:replace((tree/DECLARATIONS).read_text(), '#endif\n',declares+'#endif\n')}
    lines = []
    for name, content in edited.items():
        lines.extend(unified_diff((tree/name).read_text().splitlines(keepends=True),content.splitlines(keepends=True),
             'a/'+str(name),'b/'+str(name)))
    PATCH.write_text(''.join(lines))


def host():
    admitted()
    policy = stock()
    reference = load(REFERENCE)
    original = Path(reference['source'])
    patch(original)
    with TemporaryDirectory(prefix='0412-host-',dir=BASE) as tmp:
        workspace = Path(tmp)
        tree = workspace/'source'
        shutil.copytree(original,tree)
        prior.checked(['patch','-p1','-F','0','-i',str(PATCH)],cwd=tree)
        checks = prior.guard_cases(tree,workspace,gate='stock800')
        output = prior.checked([sys.executable,str(TEST)],env=dict(os.environ,XNU_SOURCE=str(tree)))
    votes = ('30000001/00005005','30000004/00009009','30000005/0000a00a','30000005/0000b00b','30000006/0000c00c')
    require(all('exact6 stores TCM'+vote in output for vote in votes),'one exact operating point oracle did not run')
    return dict(state='0412-stock-PERF6-BW12-offline-verified',profile=PROFILE,scope_checks=checks,policy=policy,
        results=output.splitlines(),device_commands=0,patch_sha256=sha(PATCH),
        input_pins={str(p):sha(p) for p in (ADMISSION,REFERENCE,PATCH,FIXTURE,TEST)})


def native():
    admitted()
    proof = load(HOST)
    require(proof['profile']==PROFILE and proof['scope_checks']==21 and not proof['device_commands'] and
            all(sha(path)==digest for path,digest in proof['input_pins'].items()),'0412 host proof differs')
    names = ('gauguin_gmu_board','gauguin_gmu_firmware')
    with redirect_stdout(StringIO()):
        import_module('build-frame347').link_scanout(REFERENCE,KERNEL.parent,parent_trial='0409',trial='0412',
          patches=(PATCH,),extra_units=tuple((name,REFERENCE,'compile-'+name) for name in names),
          recompile_scanout=False,compiler_bin=prior.COMPILER)
    result = load(KERNEL)
    require({Path(name).stem for name in result['object_replacements'].values()}==set(names),
            'unexpected 0412 native object replacements')
    for before,after in result['object_replacements'].items():
        old_refs,new_refs = (set(prior.checked([str(prior.COMPILER/'nm'),'-uj',path]).splitlines()) for path in (before,after))
        is_board = Path(after).stem=='gauguin_gmu_board'
        added = {'_gmf_bootstrap_dcvs800_once'} if is_board else set()
        removed = {'_gmf_bootstrap_dcvs650_bw11_once'} if is_board else set()
        require(new_refs-old_refs==added and old_refs-new_refs==removed,
                '0412 changes GMU imports outside the stock request')
    return {key:result[key] for key in ('state','identity','kernel_sha256','kernel_bytes',
                                      'object_replacements','baseline_reproduced_except_uuid','inputs_unchanged')}


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stage',choices=('stock','host','native'))
    print(json.dumps(globals()[cli.parse_args().stage](),indent=2))
