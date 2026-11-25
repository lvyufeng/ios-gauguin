#!/usr/bin/env python3
"""Verify early flip dispatch on the exact independently measured 0394 control."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN,WORK,load,require,sha

baseline = import_module('prepare-frame399')
BASE = WORK/'research/tmp/frame-400'
CONTROL = baseline.P398/'native-kernel/build-manifest.json'
PATCH = WORK/'graphics/gauguin-display/0400-dispatch-staged-flip-in-blank.patch'
FIXTURE = WORK/'tests/fixtures/frame400_stage_completion.cpp'
FRAMEBUFFER = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
ARCHIVE = baseline.P394/'0394-cutoff-audit.json'
OFFLINE_ADMISSION = (MAIN/'research/tmp/gauguin-frame399-cpu-frequency-observation-worktree-20261123'
                     /'research/tmp/frame-399/next-offline-development-assessment.json')


def host():
    source = Path(load(CONTROL)['source'])/FRAMEBUFFER
    with TemporaryDirectory(prefix='0400-stage-',dir=BASE) as temporary:
        folder = Path(temporary)
        candidate = folder/FRAMEBUFFER
        candidate.parent.mkdir(parents=True)
        candidate.write_bytes(source.read_bytes())
        subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)],cwd=folder,check=True,capture_output=True,timeout=20)
        function = import_module('check-frame391').function
        unit = candidate.read_text()
        methods = [function(unit,'AppleCLCD::'+name) for name in ('stage384Fired','flip382AdvanceLocked')]
        (folder/'Stage400Methods.inc').write_text('\n\n'.join(methods)+'\n')
        executable = folder/'test'
        args = ['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-fno-sanitize-recover=all','-I'+str(folder),str(FIXTURE),'-o',str(executable)]
        check = subprocess.run(args,capture_output=True,text=True,timeout=45)
        require(check.returncode==0,'0400 exact staging methods did not compile: '+check.stderr[-2000:])
        subprocess.run([str(executable)],check=True,timeout=20)
    evidence = load(ARCHIVE)
    control = load(baseline.P394/'execution/result.json')
    require(control['independent_restore_verified'] and control['DPU_independent_physical_FPS_qualified'] and
            not control['stable_60_fps_observed'] and
            all(sha(path)==digest for path,digest in evidence['input_pins'].items()) and
            evidence['trial']=='0394' and evidence['total_repeats']==15 and
            evidence['same_blank_stage_publication_opportunities']==[14420,14553,14697,15554],
            '0394 physical deadline evidence differs')
    margins = [row['next_latch']['publication_to_early_cutoff_ns'] for row in evidence['details']
               if row['scan'] in evidence['same_blank_stage_publication_opportunities']]
    return dict(state='0400-staged-blank-dispatch-host-verified',ASan_UBSan=True,exact_state_cases=6,
                publication_to_early_cutoff_ns=margins,device_commands=0,patch_sha256=sha(PATCH),
                input_pins=evidence['input_pins']|{str(path):sha(path) for path in (source,CONTROL,PATCH,FIXTURE,ARCHIVE)})


def native():
    admission = load(OFFLINE_ADMISSION)
    require(admission['admitted'] and admission['planned_batch_bytes']==387_000_000 and
            admission['current_accounted_bytes']+admission['planned_batch_bytes']<=admission['limit_bytes'] and
            load(BASE/'offline.json')==host(),'0400 verified source or complete active-batch budget differs')
    out = BASE/'native-kernel'
    donor = baseline.check.placement.P391/'native-kernel/build-manifest.json'
    import_module('build-frame347').link_scanout(CONTROL,out,parent_trial='0398',trial='0400',patches=(PATCH,),
        extra_units=(('SweetFramebuffer',donor,'compile-SweetFramebuffer'),),recompile_scanout=False,
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    result = load(out/'build-manifest.json')
    require(result['inputs_unchanged'] and result['baseline_reproduced_except_uuid'] and
            {Path(p).stem for p in result['object_replacements'].values()}=={'SweetFramebuffer'},
            '0400 rebuilt components outside the exact framebuffer')
    original,candidate = next(iter(result['object_replacements'].items()))
    def imports(path):
        return set(subprocess.check_output(['xcrun','nm','-uj',path],timeout=30).splitlines())
    require(imports(original)==imports(candidate),'0400 new kernel dependencies')
    return dict(kernel_sha256=result['kernel_sha256'],identity=result['identity'],device_commands=0)


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=('host','native'))
    print(json.dumps(globals()[cli.parse_args().step](),indent=2))
