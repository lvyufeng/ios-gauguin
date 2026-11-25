#!/usr/bin/env python3
"""Verify the bounded Android KGSL bandwidth step against the phone's live DT."""

import argparse
from contextlib import redirect_stdout
from importlib import import_module
from io import StringIO
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-409'
P408 = MAIN/'research/tmp/gauguin-frame408-dpu-dispatch-budget-worktree-20261124/research/tmp/frame-408'
P405 = MAIN/'research/tmp/gauguin-frame405-eop-deadline-worktree-20261124/research/tmp/frame-405'
P392 = MAIN/'research/tmp/gauguin-frame392-native-stock-worktree-20261123/research/tmp/frame-392'
PARENT = P408/'native-kernel-1401/build-manifest.json'
ADMISSION = P408/'offline-0409-batch-admission.json'
PATCH = WORK/'graphics/gauguin-display/0409-stock-gpu-bandwidth-step.patch'
FIXTURE = WORK/'tests/fixtures/gmu-firmware/firmware_host.c'
TEST = WORK/'tests/test_gmu_firmware.py'
KERNEL = BASE/'native-kernel/build-manifest.json'
HOST = BASE/'offline.json'
STOCK = MAIN/'research/tmp/dsh-0139/policy-audit.json'
CAPTURE = STOCK.with_name('policy-capture.json')
COMPILER = Path('/Library/Developer/CommandLineTools/usr/bin')
PROFILE = dict(perf_index=5,frequency_hz=650_000_000,bw_index=11,
               bandwidth_bytes_per_second=7_216_000_000,bw_word=0x0000b00b)


def checked(argv, **kwargs):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=180, **kwargs)
    require(result.returncode==0, result.stderr[-2200:]+result.stdout[-1500:])
    return result.stdout


def check_admission():
    row = load(ADMISSION)
    require(row['admitted'] and row['planned_batch_bytes']==310_000_000 and
            row['current_accounted_bytes']+row['planned_batch_bytes']<=row['limit_bytes'],
            '0409 offline batch exceeds the concurrent runtime reserve')


def stock():
    receipt = load(STOCK)
    pins = {str(MAIN/path):digest for path,digest in receipt['input_pins'].items()}
    require(all(sha(path)==digest for path,digest in pins.items()),
            'captured Android policy inputs differ')
    capture = load(CAPTURE)
    files = {row['path']:MAIN/row['output'] for row in capture['records']}
    fdt = files['/sys/firmware/fdt']
    require(str(fdt) in pins,'unbound Android DT')
    def values(node, prop):
        return list(map(int,checked(['fdtget','-t','u',str(fdt),node,prop]).split()))
    bin_path = receipt['matching_live_dt_bin']
    gpu = bin_path.rsplit('/',2)[0]
    level = bin_path+'/qcom,gpu-pwrlevel@1'
    properties = ('reg','qcom,gpu-freq','qcom,bus-freq','qcom,bus-min','qcom,bus-max')
    require(values(bin_path,'qcom,speed-bin')==[169] and
            receipt['off_inclusive_ascending_hz_arc_vlvl'][5]==[650_000_000,320] and
            [values(level,key) for key in properties]==[[1],[650_000_000],[10],[8],[12]],
            'active bin or stock 650 MHz bus limits differ')
    vectors = values(gpu,'qcom,msm-bus,vectors-KBps')
    require(values(gpu,'qcom,msm-bus,num-cases')==[13] and values(gpu,'qcom,msm-bus,num-paths')==[1] and
            len(vectors)==52 and all(vectors[i:i+3]==[26,512,0] for i in range(0,52,4)) and
            vectors[43:52:4]==[6220000,7216000,8371200],
            'stock GPU to DDR vectors differ')
    return dict(active_bin=169,stock_range=[8,12],default_bw_index=10,native_vectors_kbps=vectors[3::4],
                input_pins={str(STOCK):sha(STOCK),**pins})


def guard_cases(tree, root, *, gate='bw11'):
    board = (tree/'bsd/dev/gauguin_gmu_board.c').read_text()
    start = board.index('static bool gfw_frame409_bw11(')
    finish = board.index('static enum gmb_result gfw_once(',start)
    require(board.count(f'const bool {gate}=dcvs&&gfw_frame409_bw11(profile,sqe);')==1,
            'missing DCVS scope guard')
    body = board[start:finish]
    test = root/'scope.c'
    test.write_text('''#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
static const char *const names[] = {"swp","sweetfb_stats","sweetfb_hz",
    "sweetnvt","sweetgpuservice","sweetgpuservicesecs"};
static const int defaults[] = {4,9,60,0,1,600};
static int missing = -1, mismatched = -1;
static unsigned reads;
static bool PE_parse_boot_argn(const char *key, void *result, size_t size)
{
    assert(size == sizeof(int));
    for (unsigned i=0; i<sizeof(names)/sizeof(names[0]); ++i) {
        if (strcmp(names[i],key)) continue;
        ++reads;
        if ((int)i == missing) return false;
        *(int *)result = defaults[i] + ((int)i == mismatched);
        return true;
    }
    assert(false);
    return false;
}
'''+body+'''
int main(void)
{
    assert(gfw_frame409_bw11(5,true) && reads==6);
    reads=0;
    assert(!gfw_frame409_bw11(5,false));
    for (int profile=0; profile<8; ++profile)
        if (profile!=5) assert(!gfw_frame409_bw11(profile,true));
    assert(!reads);
    for (int i=0; i<6; ++i) {
        missing=i;
        assert(!gfw_frame409_bw11(5,true));
        missing=-1;
        mismatched=i;
        assert(!gfw_frame409_bw11(5,true));
        mismatched=-1;
    }
    return 0;
}
''')
    binary = root/'scope'
    checked(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
             str(test),'-o',str(binary)])
    checked([str(binary)])
    return 21


def host():
    check_admission()
    stock_policy = stock()
    with TemporaryDirectory(prefix='0409-host-',dir=BASE) as temporary:
        root = Path(temporary)
        tree = root/'source'
        shutil.copytree(load(PARENT)['source'],tree)
        checked(['patch','-p1','-F','0','-i',str(PATCH)],cwd=tree)
        scope_checks = guard_cases(tree,root)
        output = checked([sys.executable,str(TEST)],env=dict(os.environ,XNU_SOURCE=str(tree)))
    require(all('exact6 stores TCM'+wire in output for wire in (
        '30000001/00005005','30000004/00009009','30000005/0000a00a','30000005/0000b00b')),
        'host did not prove all native votes')
    return dict(state='0409-stock-BW11-guarded-OOB-offline-verified',profile=PROFILE,
                scope_checks=scope_checks,policy=stock_policy,results=output.splitlines(),device_commands=0,
                patch_sha256=sha(PATCH),input_pins={str(p):sha(p) for p in (ADMISSION,PARENT,PATCH,FIXTURE,TEST)})


def native():
    check_admission()
    proof = load(HOST)
    require(not proof['device_commands'] and proof['profile']==PROFILE and proof['scope_checks']==21 and
            all(sha(path)==digest for path,digest in proof['input_pins'].items()),
            '0409 host inputs differ')
    units = (('gauguin_gmu_board',P405),('gauguin_gmu_firmware',P392))
    with redirect_stdout(StringIO()):
        import_module('build-frame347').link_scanout(PARENT,KERNEL.parent,parent_trial='0408',trial='0409',
            patches=(PATCH,),extra_units=tuple((name,parent/'native-kernel/build-manifest.json','compile-'+name)
                for name,parent in units),recompile_scanout=False,compiler_bin=COMPILER)
    result = load(KERNEL)
    for before,after in result['object_replacements'].items():
        old_refs,new_refs = (set(checked(['nm','-uj',path]).splitlines()) for path in (before,after))
        added = {'_gmf_bootstrap_dcvs650_bw11_once'} if Path(after).stem=='gauguin_gmu_board' else set()
        require(new_refs-old_refs==added and not old_refs-new_refs,'unexpected GMU import change')
    return {key:result[key] for key in ('state','identity','kernel_sha256','kernel_bytes','object_replacements',
                                       'baseline_reproduced_except_uuid','inputs_unchanged')}


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('stage',choices=('stock','host','native'))
    print(json.dumps(globals()[cli.parse_args().stage](),indent=2))
