#!/usr/bin/env python3
"""Freeze one 0391 temporary boot with a bounded previous pending swap."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

check = import_module('check-frame391')
previous = import_module('prepare-frame390')
P388, REFERENCE = previous.P388,previous.REFERENCE
P390 = MAIN/'research/tmp/gauguin-frame390-ca-timeline-worktree-20261123/research/tmp/frame-390'
LAST = P390/'execution'
TRIAL = '0391'
BASE = check.BASE
DOC = WORK/'docs/gauguin-frame-391-pending-swap-20261123.md'
BATCH,RESERVE,shared,save = previous.BATCH,previous.RESERVE,previous.shared,previous.save
KERNEL = BASE/'native-kernel/build-manifest.json'
IMAGE = BASE/'frame391-image.json'
OFFLINE = BASE/'offline.json'
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0390')],
         'allow_0391_one_60Hz_temporary_boot_with_previous_pending_surface')
SUCCESS = '0391-DPU-and-previous-pending-swap-measured-root-restored'


def admitted():
    receipt = load(BASE/'live-batch-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes']==BATCH and
        receipt['current_accounted_bytes']+BATCH<=receipt['limit_bytes'],'0391 full batch exceeds storage')


def baseline(*, fresh=True):
    end,proof,parent = (load(LAST/path) for path in
        ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed'] and
        proof['install_plan_sha256']==load(P390/'trial-plan.json')['install_plan_sha256'] and
        proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
        proof['root_header_sha256']==parent['root_header_sha256'] and not end.get('stable_60_fps_observed',False),
        '0390 result requires a verified restored root and unfinished 60 fps target')
    if not fresh:
        return parent
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(
        current[key]==parent[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
        'current recovery root differs from 0390 readback')
    return current


def package():
    admitted()
    pack = import_module('package-frame344')
    native,host = load(KERNEL),load(OFFLINE)
    require(native['state']=='0391-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
        native['input_pins'][str(check.PATCH)]==host['patch_sha256']==sha(check.PATCH) and
        {Path(name).stem for name in native['object_replacements']}=={'GauguinGPU','SweetFramebuffer'} and
        not host['device_commands'] and native['inputs_unchanged'],'0391 candidate inputs differ')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=previous.prior388.SHIM)
    parent = load(P388/'trial-plan.json')
    a,b = (pack.parts(Path(path).read_bytes()) for path in (parent['image'],image['image']))
    require(a[0][:16]==b[0][:16] and a[0][20:]==b[0][20:] and a[1]==b[1] and a[3]==b[3] and
        parent['boot_command']==image['command'] and 42_000_000<image['image_bytes']<44_000_000,
        '0391 wrapper, DTB or boot command changed')
    image['kernel_manifest'] = str(KERNEL)
    save(BASE/'edr-native/result.json', pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P388/'edr-native/result.json'))
    for kind in ('core','c4'):
        target = BASE/(kind+'-native/result.json')
        target.parent.mkdir()
        shutil.copyfile(P388/(kind+'-native/result.json'),target)
    save(IMAGE,image)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    admitted()
    last = baseline(fresh=False)
    profile = load(P390/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),
        expected_header_sha256=last['root_header_sha256'],max_combined_log_bytes=last['combined_log_bytes'])
    import_module('capture-core342-root').capture(profile,save_files=False)
    baseline()
    proc = subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
        '--baseline',str(LAST/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P390/'slot-capture')],capture_output=True,text=True,timeout=300)
    require(proc.returncode==0,'0391 live slot read failed: '+proc.stderr[-1800:])
    result = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',last['root_header_sha256'],
        trial=TRIAL,maximum_compressed_bytes=28_000_000)
    return {key:result[key] for key in ('compressed_bytes','device_writes','device_boots')}


def delta():
    live = baseline()
    return shared.stage.delta(BASE,P388,trial=TRIAL,header=live['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=7_975_712)


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    native,image,edr,host = (load(path) for path in (KERNEL,IMAGE,BASE/'edr-native/result.json',OFFLINE))
    parent_path = P388/'trial-plan.json'
    parent = load(parent_path)
    delta_path = BASE/'slot-delta/install-plan.json'
    install = load(delta_path)
    header, size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(host['state']=='0391-previous-pending-swap-offline-verified' and host['read_guard_and_generation_scenarios']==4
        and sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256']
        and sha(image['image'])==image['image_sha256'] and image['command']==parent['boot_command']
        and image['build_identity']==native['identity']==edr['kernel_identity'] and edr['identity_only_retarget']
        and sha(edr['binary'])==edr['binary_sha256']==install['admission_sha256']
        and install['core_sha256']==parent['owned_core_sha256'] and install['trial']==TRIAL
        and install['root_header_sha256']==header and install['changed_ranges']==12
        and sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256']
        and parent['frame_capture']['target_refresh_hz']==60 and parent['frame_capture']['modesets']==0
        and parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13
        and parent['sustained_motion']['normal_reports']==162,'0391 frozen kernel, recovery, or display scope differs')
    return dict(parent,state='prepared-frame391-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(delta_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={key:live['files'][key]['bytes'] for key in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-previous.LOG_BYTES),
        pending_swap=dict(previous_unissued_limit=1,distinct_surface=True,offline_sha256=sha(OFFLINE)),
        optimization='Retain one prior per-surface pending update until exact producer binding or replacement.',
        performance_comparison='Compare 0388/0391 exact native writers, vblank and CRC in the same script.')


def criteria(plan):
    admitted()
    parent = load(P388/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'pending_swap','optimization','performance_comparison'}
    require({k for k in parent.keys() | plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0391 effect scope differs')
    old,new = (load(root/'slot-delta/install-plan.json') for root in (P388,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
        =={'admission'},'0391 userspace scope differs beyond signed identity')
    model = load(BASE/'restore-model/result.json')
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and len(model['checks'])==49 and
        model['all_restore_partial_write_points']==17,'0391 rollback model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P388,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P388/'storage-bound-388.json')
    require(old['worst_case_bytes']<=RESERVE,'0391 runtime exceeds reserve')
    return dict(old,state='bounded0391-previous-pending-display-runtime',fresh_log_bytes=
        plan['log_capture']['measured_baseline_bytes'],log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/path for path in scripts),DOC,check.PATCH,check.FIXTURE,OFFLINE,KERNEL,IMAGE,
        BASE/'current-root-capture/result.json',BASE/'live-batch-admission.json',BASE/'verified-retirement-manifest.json',
        MAIN/'tools/storage-budget.py',P388/'ready.json',P388/'trial-plan.json',P388/'capture-profile.json',
        P388/'storage-bound-388.json',P388/'restored-DPU-comparison.json',P390/'trial-plan.json',
        *(LAST/path for path in ('result.json','independent-restore.json','restored-capture/result.json')),
        *(REFERENCE/name for name in previous.prior.audit.PINS),previous.prior388.MOTION_ANALYZER,
        Path(load(P388/'trial-plan.json')['observer_helper'])]
    for name in ('slot-delta','slot-capture','metadata-snapshot','restore-model','edr-native','c4-native','core-native'):
        files.extend(path for path in (BASE/name).rglob('*') if path.is_file())
    result = {str(path):sha(path) for path in files}
    for receipt in (KERNEL,IMAGE,BASE/'edr-native/result.json',BASE/'core-native/result.json',
                    BASE/'c4-native/result.json',BASE/'restore-model/result.json'):
        data = load(receipt)
        for name,digest in data.get('input_pins',{}).items():
            require(sha(name)==digest and result.setdefault(name,digest)==digest,'0391 pinned input differs: '+name)
        for key in ('kernel','image','binary'):
            if key in data:
                result[data[key]] = sha(data[key])
    return result


def freeze():
    return shared.freeze(base=BASE,prior=P388,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {action.__name__:action for action in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
