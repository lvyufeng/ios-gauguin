#!/usr/bin/env python3
"""Verify the exact producer seal after the native call and before its recorded issue."""

from difflib import unified_diff
from importlib import import_module
import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

producer = import_module('stage-frame401-producer')
BASE = WORK/'research/tmp/frame-404'
P403 = MAIN/'research/tmp/gauguin-frame403-compact-cpu-proof-worktree-20261124/research/tmp/frame-403'
CONTROL = P403/'native-kernel/build-manifest.json'
ADMISSION = BASE/'combine-development-admission.json'
ALIAS = producer.ROOT/'DisplayPrevious404.h'
FIXTURE = WORK/'tests/fixtures/frame404_previous_writer.c'
PATCH = BASE/'404-in-render-producer.patch'


def gpu_unit(unit):
    unit = producer.gpu_transport(unit)
    begin = unit.index('        if (producerVersion) {\n')
    end = unit.index('        const uint32_t previousSurface',begin)
    unit = unit[:begin]+unit[end:]
    site = '        if(ok&&(!fence||fence<=fNativeFence))'
    seal = '''        if (producerVersion) {
            // The pending BO escrow still belongs to this submission.
            // Seal before reporting the issue or cancelling a failed issue.
            const uint64_t exact = sweet_fb401_seal_writer(producerCookie, producerSurface, producerVersion);
            if (exact) {
                assert(!fPendingDisplayTicket);
                fPendingDisplayTicket = exact;
                fPendingDisplayVersion = producerVersion;
            }
        }
'''
    unit = producer.replace(unit,site,seal+site)
    require(unit.index('bool ok=fAsync?sweet_gpu_runtime_issue(') <
            unit.index('const uint64_t exact = sweet_fb401_seal_writer(') <
            unit.index('if(ok&&(!fence||fence<=fNativeFence))') <
            unit.index('sweet_frame344_record(F344_ISSUE'), '0404 issue and binding order differs')
    return unit


def framebuffer_unit(unit):
    unit = producer.display_binding(unit)
    include = '#include "../../../bsd/dev/gauguin_display_writer401.h"'
    unit = producer.replace(unit,include,include+'\n#include "../../../bsd/dev/gauguin_display_previous404.h"')
    begin = '    const bool claimed = gReadySource && sweet_frame351_window() && (uint32_t)ticket == surface &&'
    unit = producer.replace(unit,begin,'''    const bool claimed = gReadySource && sweet_frame351_window() && (uint32_t)ticket == surface &&
        display404_previous_allowed(&gBusyDisplayWriter401, surface, version) &&''')
    line = '    if (claimed) sweet_frame344_record(F357_BOUND, ticket >> 32, 1, ticket, version, 0);'
    return producer.replace(unit,line,'''    if (claimed) {
        display404_previous_claimed(&gBusyDisplayWriter401, surface, version);
        sweet_frame344_record(F357_BOUND, ticket >> 32, 1, ticket, version, 0);
    }''')


def recorded_cohort():
    phase = load(producer.ELIGIBILITY)
    require(phase['single_native_display_writer_in_flush_phase']==5 and
        all(sha(p)==v for p,v in phase['input_pins'].items()), '0404 pre-issue archive differs')
    diagnostic = next(Path(p) for p in phase['input_pins'] if p.endswith('/0399-busy-writer-supply-ceiling.json'))
    # The historical phase bands come from the exact recording-thread, target
    # and native-fence joins already pinned by the 0401 producer verifier.
    raw = diagnostic.parent/'execution/kernel.log'
    trace = import_module('frame344_log')
    rows,_,n,d = import_module('frame384_stage').parse(raw.read_text())
    issued = {row.id:row.tick*n//d for row in rows[trace.ISSUE]}
    cohort = [row for row in phase['rows'] if row['IOSurface_write_count']==1 and
              row['flush_entry_ns']<=row['swap_ns']<issued[row['fence']]]
    require(len(cohort)==9,'0404 single producer cohort differs')
    return [r['generation'] for r in cohort]


def host():
    admission = load(ADMISSION)
    require(admission['admitted'] and admission['planned_batch_bytes']>=72_000_000 and
        admission['current_accounted_bytes']+admission['planned_batch_bytes']<=admission['limit_bytes'],
        '0404 native allocation exceeds the admitted development batch')
    cohort = recorded_cohort()
    source = Path(load(CONTROL)['source'])
    original = Path(load(producer.CONTROL)['source'])
    files = [(producer.GPU,gpu_unit),(producer.FRAMEBUFFER,framebuffer_unit),
        (producer.KDEBUG,producer.callback.patch_kdebug)]
    blocks = []
    for path,transform in files:
        before = (source/path).read_text()
        require(before==(original/path).read_text(),'0404 participant differs from the verified 0401 source')
        blocks.extend(unified_diff(before.splitlines(keepends=True),transform(before).splitlines(keepends=True),
            'a/'+str(path),'b/'+str(path)))
    headers = producer.HEADERS | {ALIAS.name:'gauguin_display_previous404.h'}
    for name,path in headers.items():
        blocks.extend(unified_diff([], (producer.ROOT/name).read_text().splitlines(keepends=True),
            '/dev/null','b/bsd/dev/'+path))
    PATCH.write_text(''.join(blocks))
    with TemporaryDirectory(prefix='404-writer-',dir=BASE) as temporary:
        binary = str(Path(temporary)/'test')
        subprocess.run(['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(producer.ROOT),
            str(FIXTURE),'-o',binary],check=True,timeout=45)
        subprocess.run([binary],check=True,timeout=15)
    return dict(state='0404-post-call-exact-writer-host-verified',ASan_UBSan=True,eligible_generations=cohort,
        patch_sha256=sha(PATCH),device_commands=0,input_pins={str(p):sha(p) for p in (CONTROL,
            producer.CONTROL,producer.ELIGIBILITY,ADMISSION,ALIAS,FIXTURE,PATCH)})


def native():
    require(load(BASE/'offline.json')==host(),'0404 ownership model differs')
    latest = import_module('check-frame400').baseline.P398/'native-kernel/build-manifest.json'
    out = BASE/'native-kernel'
    import_module('build-frame347').link_scanout(CONTROL,out,parent_trial='0403',trial='0404',
        patches=(PATCH,),extra_units=(('GauguinGPU',latest,'compile-GauguinGPU'),
            ('SweetFramebuffer',producer.CONTROL,'compile-SweetFramebuffer'),
            ('kdebug',producer.callback.CONTROL,'compile-kdebug')),
        recompile_scanout=False,compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    built = load(out/'build-manifest.json')
    require(built['inputs_unchanged'] and built['baseline_reproduced_except_uuid'] and
        {Path(p).stem for p in built['object_replacements'].values()}=={'GauguinGPU','SweetFramebuffer','kdebug'},
        '0404 changed native units outside producer ownership')
    return dict(kernel_sha256=built['kernel_sha256'],identity=built['identity'],device_commands=0)


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=('host','native'))
    print(json.dumps(globals()[cli.parse_args().step](),indent=2))
