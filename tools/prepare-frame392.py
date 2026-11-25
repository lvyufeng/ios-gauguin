#!/usr/bin/env python3
"""Freeze a one-shot 60 Hz trial with the single 650 MHz Android operating-point change."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

check = import_module('check-frame392')
previous = import_module('prepare-frame391')
BASE, P391, PROFILE = check.BASE, check.P391, check.PROFILE
P388, BATCH, RESERVE, shared, save = (previous.P388,previous.BATCH,previous.RESERVE,previous.shared,previous.save)
KERNEL = BASE/'native-kernel/build-manifest.json'
IMAGE = BASE/'frame392-image.json'
OFFLINE = BASE/'offline.json'
LAST = P391/'execution'
DOC = WORK/'docs/gauguin-frame-392-native-stock-20261123.md'
TRIAL = '0392'
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0391')],
         'allow_0392_one_bounded_60Hz_temporary_boot_with_stock_650MHz_GPU_vote')
SUCCESS = '0392-Android-stock-GPU-point-measured-root-restored'


def admitted():
    receipt = load(BASE/'live-batch-admission.json')
    planned = receipt['planned_batch_bytes']
    require(receipt['admitted'] and planned in (BATCH,BATCH+RESERVE) and
        receipt['current_accounted_bytes']+planned<=receipt['limit_bytes'],'0392 full batch exceeds storage')


def baseline(*, fresh=True):
    end,proof,restored = (load(LAST/path) for path in
        ('result.json','independent-restore.json','restored-capture/result.json'))
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed'] and
        proof['install_plan_sha256']==load(P391/'trial-plan.json')['install_plan_sha256'] and
        proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
        proof['root_header_sha256']==restored['root_header_sha256'] and not end.get('stable_60_fps_observed',False),
        '0391 must have restored the original root and left 60 fps unfinished')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(
        current[key]==restored[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
        'current recovery root differs from 0391 readback')
    return current


def command_profile(command):
    require(command.split().count('gpf=4')==1 and 'gpf=5' not in command.split(),'ambiguous GPU profile change')
    return command.replace('gpf=4','gpf=5')


def package():
    admitted()
    pack = import_module('package-frame344')
    native,host = load(KERNEL),load(OFFLINE)
    require(native['state']=='0392-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
        native['input_pins'][str(check.PATCH)]==host['patch_sha256']==sha(check.PATCH) and
        {Path(name).stem for name in native['object_replacements'].values()}==
            {'gauguin_gmu_board','gauguin_gmu_firmware'} and
        not host['device_commands'] and native['inputs_unchanged'],'0392 kernel inputs differ')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),native,base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=previous.previous.prior388.SHIM,
        command_profile=command_profile)
    reference = load(P391/'trial-plan.json')
    orig,new = (pack.parts(Path(path).read_bytes()) for path in (reference['image'],image['image']))
    require(orig[0][:16]==new[0][:16] and orig[0][20:]==new[0][20:] and orig[1]==new[1] and orig[3]==new[3] and
        command_profile(reference['boot_command'])==image['command'] and 42_000_000<image['image_bytes']<44_000_000,
        '0392 wrapper, DTB or replacement boot argument differs')
    image['kernel_manifest'] = str(KERNEL)
    save(BASE/'edr-native/result.json',pack.edr(image,base=BASE,trial=TRIAL,
        signed_reference=P391/'edr-native/result.json',profile=('gpf=4','gpf=5')))
    for kind in ('core','c4'):
        target = BASE/(kind+'-native/result.json')
        target.parent.mkdir()
        shutil.copyfile(P391/(kind+'-native/result.json'),target)
    save(IMAGE,image)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def capture():
    admitted()
    return capture_from(BASE,P391,TRIAL,baseline)


def capture_from(base,parent,trial,preflight):
    last = preflight(fresh=False)
    profile = load(parent/'capture-profile.json')
    profile.update(out=str((base/'current-root-capture').relative_to(MAIN)),
        expected_header_sha256=last['root_header_sha256'],max_combined_log_bytes=last['combined_log_bytes'])
    import_module('capture-core342-root').capture(profile,save_files=False)
    preflight()
    parent_result = parent/'execution/restored-capture/result.json'
    proc = subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
        '--baseline',str(parent_result),'--out',str(base/'slot-capture'),
        '--reuse-data-from',str(parent/'slot-capture')],capture_output=True,text=True,timeout=300)
    require(proc.returncode==0,trial+' live slot read failed: '+proc.stderr[-1800:])
    result = import_module('capture-core342-metadata').capture(base/'metadata-snapshot',last['root_header_sha256'],
        trial=trial,maximum_compressed_bytes=28_000_000)
    return {key:result[key] for key in ('compressed_bytes','device_writes','device_boots')}


def delta():
    live = baseline()
    return shared.stage.delta(BASE,P391,trial=TRIAL,header=live['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=7_975_712)


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(result['checks']),failure_points=result['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    native,image,edr,host = (load(path) for path in (KERNEL,IMAGE,BASE/'edr-native/result.json',OFFLINE))
    parent_path = P391/'trial-plan.json'
    parent = load(parent_path)
    install_path = BASE/'slot-delta/install-plan.json'
    install = load(install_path)
    header, size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(host['state']=='0392-stock-650-guarded-OOB-offline-verified' and host['profile']==PROFILE and
        sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
        sha(image['image'])==image['image_sha256'] and image['command']==command_profile(parent['boot_command']) and
        image['build_identity']==native['identity']==edr['kernel_identity'] and edr['retargeted_optin']==['gpf=4','gpf=5'] and
        sha(edr['binary'])==edr['binary_sha256']==install['admission_sha256'] and
        install['core_sha256']==parent['owned_core_sha256'] and install['trial']==TRIAL and
        install['root_header_sha256']==header and install['changed_ranges']==12 and
        sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
        parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
        parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
        parent['sustained_motion']['normal_reports']==162,'0392 physical and restoration scope differs')
    return dict(parent,state='prepared-frame392-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],boot_command=image['command'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={key:live['files'][key]['bytes'] for key in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        GPU_native_profile=PROFILE,optimization='Request the same handset stock Android 650 MHz/BW10 operating point.',
        performance_comparison='Compare 0391/0392 exact native writers, issue/EOP/cache, vblank and CRC in the same script.')


def criteria(plan):
    admitted()
    parent = load(P391/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','boot_command','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'GPU_native_profile','optimization','performance_comparison'}
    require({k for k in parent.keys() | plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0392 effect scope differs')
    old,new = (load(root/'slot-delta/install-plan.json') for root in (P391,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
        =={'admission'},'0392 userspace scope differs beyond signed profile admission')
    model = load(BASE/'restore-model/result.json')
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and len(model['checks'])==49 and
        model['all_restore_partial_write_points']==17,'0392 rollback model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P391,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P391/'storage-bound-391.json')
    require(old['worst_case_bytes']<=RESERVE,'0392 runtime exceeds reserve')
    return dict(old,state='bounded0392-Android-GPU-point-runtime',fresh_log_bytes=
        plan['log_capture']['measured_baseline_bytes'],log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/path for path in scripts),DOC,check.PATCH,check.FIXTURE,check.TEST,check.DONOR,OFFLINE,KERNEL,IMAGE,
        BASE/'current-root-capture/result.json',BASE/'live-batch-admission.json',BASE/'verified-retirement-manifest.json',
        MAIN/'tools/storage-budget.py',P388/'restored-DPU-comparison.json',P391/'ready.json',P391/'trial-plan.json',
        P391/'capture-profile.json',P391/'storage-bound-391.json',
        *(LAST/path for path in ('result.json','independent-restore.json','restored-capture/result.json',
            'scanout-comparison-0388-0391.json','kernel.log','kernel.log.bin','page-flip-latches.json')),
        *(previous.REFERENCE/name for name in previous.previous.prior.audit.PINS),
        previous.previous.prior388.MOTION_ANALYZER,Path(load(P391/'trial-plan.json')['observer_helper'])]
    result = scoped_pins(BASE,files,KERNEL,IMAGE)
    for name,digest in load(OFFLINE)['policy']['input_pins'].items():
        require(sha(name)==digest,'Android policy source changed: '+name)
        result[name] = digest
    return result


def scoped_pins(base, files, kernel, image):
    for directory in ('slot-delta','slot-capture','metadata-snapshot','restore-model','edr-native','c4-native','core-native'):
        files.extend(path for path in (base/directory).rglob('*') if path.is_file())
    result = {str(path):sha(path) for path in files}
    for receipt in (kernel,image,base/'edr-native/result.json',base/'core-native/result.json',
                    base/'c4-native/result.json',base/'restore-model/result.json'):
        data = load(receipt)
        for name,digest in data.get('input_pins',{}).items():
            require(sha(name)==digest and result.setdefault(name,digest)==digest,'0392 pinned input differs: '+name)
        for key in ('kernel','image','binary'):
            if key in data:
                result[data[key]] = sha(data[key])
    return result


def freeze():
    return shared.freeze(base=BASE,prior=P391,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {action.__name__:action for action in (package,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
