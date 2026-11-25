#!/usr/bin/env python3
"""Verify the bounded pending display slot and reproduce its archive opportunity."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from importlib import import_module
from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from frame366_scope import MAIN, WORK, load, require, sha
from frame390_build import CA, DPU

BASE = WORK/'research/tmp/frame-391'
PATCH = WORK/'graphics/gauguin-display/0391-retain-previous-pending-swap.patch'
FIXTURE = WORK/'tests/fixtures/frame391_pending.cpp'
GPU = MAIN/'research/tmp/gauguin-issued-probe-worktree-20261121/research/tmp/frame-366/native-kernel'
UNITS = {
    'iokit/Kernel/arm/SweetFramebuffer.cpp':DPU,
    'iokit/Kernel/arm/GauguinGPU.cpp':GPU,
}


def function(source, name):
    target = source.index('\n'+name+'(')
    return source[source.rindex('\n',0,target)+1:source.index('\n}',target)+2]


def compile_unit(source, output, path, donor):
    unit = Path(path).stem
    manifest = load(donor/'build-manifest.json')
    step = next(item for item in manifest['steps'] if item['name']=='compile-'+unit and item['exit']==0)
    argv = list(step['argv'])
    index = next(i for i,arg in enumerate(argv) if arg.endswith('/'+Path(path).name))
    argv[index] = str(source/path)
    obj = output/(unit+'.o')
    old = argv[argv.index('-o')+1]
    argv[argv.index('-o')+1] = str(obj)
    argv[argv.index('-MF')+1] = str(obj.with_suffix('.d'))
    proc = subprocess.run(argv,cwd=step['cwd'],capture_output=True,text=True,timeout=90)
    require(proc.returncode==0,'ARM64 '+unit+' compile failed: '+proc.stderr[-2400:])
    actual, reference = (set(subprocess.check_output(['nm','-uj',str(p)]).splitlines()) for p in (obj,old))
    imported = {b'_sweet_fb391_previous_surface', b'_sweet_fb391_claim_previous'} if unit=='GauguinGPU' else set()
    require(actual-reference==imported and not reference-actual,'0391 ARM64 imports differ: '+unit)
    return unit,sha(obj)


def check():
    with TemporaryDirectory(prefix='0391-host-',dir=BASE) as temporary:
        root = Path(temporary)
        source = root/'source'
        shutil.copytree(DPU/'source',source)
        p = subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)],cwd=source,capture_output=True,text=True,timeout=30)
        require(p.returncode==0,'0391 source patch failed: '+p.stdout[-1700:])
        cpp = (source/next(iter(UNITS))).read_text()
        (root/'Frame391Methods.inc').write_text('\n\n'.join(function(cpp,name) for name in (
            'sweet_fb391_previous_surface','sweet_fb391_claim_previous','AppleCLCD::pendingTicketLocked',
            'AppleCLCD::boundFrameLocked','AppleCLCD::replacePendingLocked','AppleCLCD::collectIssuedLocked',
            'AppleCLCD::cancelHeldFramesLocked'))+'\n')
        binary = root/'fixture'
        p = subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-I'+str(root),'-I'+str(source/'bsd/dev'),str(FIXTURE),'-o',str(binary)],
            text=True,capture_output=True,timeout=60)
        require(p.returncode==0,'0391 host fixture failed to compile: '+p.stderr[-2400:])
        subprocess.run([str(binary)],check=True,timeout=25)
        with ThreadPoolExecutor(max_workers=2) as pool:
            objects = dict(pool.map(lambda item:compile_unit(source,root,*item),UNITS.items()))
    return dict(state='0391-previous-pending-swap-offline-verified',read_guard_and_generation_scenarios=4,
                ASan_UBSan=True,device_commands=0,objects=objects,patch_sha256=sha(PATCH),replay=replay())


def replay():
    sys.path.append(str(CA/'tools'))
    feasible = import_module('audit-frame-supply').feasible
    audit = import_module('audit-frame388-restored')
    scope = import_module('prepare-frame390')
    trace = audit.trace
    results = {}
    for name,archive in (('0388',scope.P388),('0389',scope.P389)):
        root = archive/'execution'
        terminal = load(root/'result.json')
        proof = load(root/'independent-restore.json')
        require(terminal['independent_restore_verified'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'],'queue replay requires independent restore')
        raw = (root/'kernel.log').read_text()
        rows,_,_,_ = audit.stage.staging.parse(raw)
        scans,metrics = audit.score_archive(root,load(archive/'trial-plan.json')['kernel_banner'])
        latches = audit.stage.staging.verified_latches(rows,audit.flip.latch_receipts(raw,rows)['accepted_by_scan'])
        starts = [row for row in rows[trace.SWAP] if not row.flags and row.c]
        ready = {row.id:row.tick for row in rows[trace.READY]}
        issued = {row.id:row.tick for row in rows[trace.ISSUE]}
        writers = trace.indexed(rows[trace.WRITER],lambda row:(row.a,row.c),'surface version writer')
        result = Counter()
        for window in metrics['moving_GPU']['ordinary']['windows']:
            lane = [r for r in scans if r['workload']=='ordinary' and r['phase']=='active' and
                r['stroke']==window['stroke'] and window['first_scan']<=r['frame']<=window['last_scan']]
            preceding = max((scan for scan in latches if scan<lane[0]['frame']),default=0)
            front = latches[preceding]['generation'] if preceding else 0
            slots = [SimpleNamespace(end=row['vblank_ticks'][1]) for row in lane]
            bound, alternatives = [], []
            for i,row in enumerate(starts):
                g,tick = row.id,row.tick
                if g<=front or tick>slots[-1].end:
                    continue
                version,surface = divmod(row.c,1<<32)
                found = writers.get((surface,version))
                if not found or found.id not in ready:
                    continue
                release = ready[found.id]
                if release>slots[-1].end:
                    continue
                if found.b>>32==g:
                    bound.append((g,release))
                elif not found.b and i+1<len(starts):
                    next_swap = starts[i+1]
                    limit = starts[i+2].tick if i+2<len(starts) else slots[-1].end
                    if next_swap.tick<issued[found.id]<limit and surface!=(next_swap.c&0xffffffff):
                        alternatives.append((g,release))
            result.update(slots=len(slots),observed=sum(row['crc']=='changed' for row in lane),
                latest_only=feasible(slots,bound,front),with_previous=feasible(slots,bound+alternatives,front),
                recovered_writer_identities=len(alternatives))
        results[name] = dict(result)
    return dict(warm_motion=results,scope='Optimistic zero-copy replay with fixed observed producer times and one retained older surface.')


def native():
    proof = load(BASE/'live-batch-admission.json')
    require(proof['admitted'] and proof['planned_batch_bytes']==315_000_000,'full 0391 batch not admitted')
    receipt = load(BASE/'offline.json')
    require(receipt['patch_sha256']==sha(PATCH) and not receipt['device_commands'],'0391 host source differs')
    import_module('build-frame347').link_scanout(DPU/'build-manifest.json',BASE/'native-kernel',
        parent_trial='0388',trial='0391',patches=(PATCH,),
        extra_units=tuple((Path(path).stem,root/'build-manifest.json','compile-'+Path(path).stem)
                          for path,root in UNITS.items()),
        recompile_scanout=False,compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    return load(BASE/'native-kernel/build-manifest.json')['kernel_sha256']


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('host','native','replay'))
    step = parser.parse_args().action
    result = {'host':check,'native':native,'replay':replay}[step]()
    print(json.dumps(result,indent=2))
