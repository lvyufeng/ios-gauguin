#!/usr/bin/env python3
"""Freeze a 60 Hz read-only CA timeline trial with the 0388 render path."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha
from frame390_build import BASE, CA, DPU, HEADER as OBSERVER_HEADER, native
from frame390_timeline import MAX_CONSOLE_BYTES

prior = import_module('prepare-frame389')
prior388 = import_module('prepare-frame388')
P388 = prior.P388
P389 = MAIN/'research/tmp/gauguin-frame389-core-deadline-worktree-20261123/research/tmp/frame-389'
REFERENCE = P388/'execution'
LAST = P389/'execution'
TRIAL = '0390'
HEADER = 'd4b46baafc8526f26866a46b3d5b3b4083238f8addf907f900a32a1ee0a3848c'
LOG_BYTES = 252_859_495
DOC = WORK/'docs/gauguin-frame-390-ca-timeline-20261123.md'
BATCH, RESERVE, shared, save = 315_000_000, prior.RESERVE, prior.shared, prior.save
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0389')],
         'allow_0390_single_60Hz_temporary_boot_with_compact_CA_timeline')
SUCCESS = '0390-DPU-and-CA-timeline-observed-root-restored'
KERNEL = BASE/'native-kernel/build-manifest.json'
IMAGE = BASE/'frame390-image.json'
OFFLINE = BASE/'offline-timeline.json'
NATIVE_PROOF = BASE/'native-proof.json'
TERMINAL_PINS = {
    'result.json': 'e5d68f777cc18271ccad72bff5cbec0d73be642ba43d95db21cb4e6fa12607bd',
    'independent-restore.json': 'b6ded0f326b7a82d4b599a01c1b81d431cd10561c2bdbfab1d458b93113f9bc7',
    'scanout-comparison-0388-0389.json': '21c95e3b7c77b51322561d3d8db8a9cf56fd09a8fc23e8a7b21ddd1c77fbff92',
}


def admitted():
    budget = load(BASE/'live-batch-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes']==BATCH and
            budget['current_accounted_bytes']+BATCH<=budget['limit_bytes'], 'full 0390 batch exceeds storage')


def baseline(*, fresh=True):
    require(all(sha(LAST/name)==digest for name,digest in TERMINAL_PINS.items()),'0389 readback archive differs')
    result,proof,old = (load(LAST/name) for name in ('result.json','independent-restore.json','restored-capture/result.json'))
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
        proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and
        proof['misc_original_4096_bytes_match'] and old['root_header_sha256']==proof['root_header_sha256']==HEADER and
        old['combined_log_bytes']==LOG_BYTES,'0389 independent recovery is incomplete')
    if not fresh:
        return old
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(
        current[k]==old[k] for k in ('root_header_sha256','combined_log_bytes','files','directories')),
        'current recovery root differs from the restored 0389 baseline')
    return current


def capture():
    admitted()
    baseline(fresh=False)
    profile = load(P389/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    baseline()
    program = subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
        '--baseline',str(LAST/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P389/'slot-capture')],capture_output=True,text=True,timeout=300)
    require(program.returncode==0,'0390 slot readback failed: '+program.stderr[-1800:])
    observed = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,
        trial=TRIAL,maximum_compressed_bytes=28_000_000)
    return {key:observed[key] for key in ('compressed_bytes','device_writes','device_boots')}


def package():
    admitted()
    pack = import_module('package-frame344')
    manifest,proof,host = map(load,(KERNEL,NATIVE_PROOF,OFFLINE))
    require(manifest['kernel_sha256']==proof['kernel_sha256']==sha(manifest['kernel']) and
        host['staged_patch_sha256']==sha(BASE/'390-ca-timeline.patch') and
        host['state']=='0390-compact-CA-timeline-offline-verified','0390 linked kernel or CA fixture differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'), manifest,
        base=BASE,trial=TRIAL,frame_capture_mode=9,scripted_motion=True,private_scanout_shim=prior388.SHIM)
    reference = load(P388/'trial-plan.json')
    old,new = (pack.parts(Path(path).read_bytes()) for path in (reference['image'],image['image']))
    require(old[0][:16]==new[0][:16] and old[0][20:]==new[0][20:] and
        old[1]==new[1] and old[3]==new[3] and image['command']==reference['boot_command'] and
        42_000_000<image['image_bytes']<44_000_000,'0390 boot wrapper, DTB or command changed')
    image['kernel_manifest'] = str(KERNEL)
    save(BASE/'edr-native/result.json', pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P388/'edr-native/result.json'))
    for kind in ('core','c4'):
        target = BASE/(kind+'-native/result.json')
        target.parent.mkdir()
        shutil.copyfile(P388/(kind+'-native/result.json'),target)
    save(IMAGE,image)
    return {key:image[key] for key in ('image_sha256','image_bytes','build_identity')}


def delta():
    baseline()
    return shared.stage.delta(BASE,P388,trial=TRIAL,header=HEADER,
           baseline=LAST/'restored-capture/result.json',core_logical=7_975_712)


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),failure_points=proof['all_restore_partial_write_points'])


def expected_plan():
    current = baseline()
    parent_file = P388/'trial-plan.json'
    parent = load(parent_file)
    manifest, image, edr, host = (load(path) for path in
        (KERNEL,IMAGE,BASE/'edr-native/result.json',OFFLINE))
    install_path = BASE/'slot-delta/install-plan.json'
    install = load(install_path)
    require(manifest['state']=='0390-native-ARM64-linked' and manifest['inputs_unchanged'] and
        manifest['baseline_reproduced_except_uuid'] and
        sha(manifest['kernel'])==manifest['kernel_sha256']==image['kernel_sha256'] and
        sha(image['image'])==image['image_sha256'] and image['command']==parent['boot_command'] and
        manifest['identity']==image['build_identity']==edr['kernel_identity'] and edr['identity_only_retarget'] and
        sha(edr['binary'])==edr['binary_sha256']==install['admission_sha256'] and
        install['core_sha256']==parent['owned_core_sha256'] and install['trial']==TRIAL and
        install['changed_ranges']==12 and install['root_header_sha256']==HEADER and
        sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'],
        '0390 kernel, DPU profile, or reversible install differs')
    require(host['fixture_swipes']==13 and host['archive']['matching_retained_apply_chains']==152 and
        host['staged_patch_sha256']==sha(BASE/'390-ca-timeline.patch') and not host['device_commands'],
        'compact CA timeline offline or identity gate failed')
    with (LAST/'kernel.log.bin').open('rb') as source:
        magic, version, capacity, used, _ = struct.unpack('<8sIIQQ',source.read(32))
    require((magic,version,capacity)==(b'SWEETLOG',1,4_194_304) and used+MAX_CONSOLE_BYTES<capacity and
        parent['scripted_strokes']==13 and parent['sustained_motion']['normal_reports']==162 and
        parent['frame_capture']['target_refresh_hz']==60 and parent['frame_capture']['modesets']==0 and
        parent['frame_capture']['crc_required_preimage']==0x01000000,
        '0390 console room, scripted input, or 60 Hz CRC limits differ')
    sizes = {key:current['files'][key]['bytes'] for key in parent['log_capture']['sizes']}
    return dict(parent,state='prepared-frame390-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(parent_file),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=manifest['identity'],kernel_banner=manifest['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(parent['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=used,
            reserved_frame_console_bytes=capacity-used,previous_verified_suffix_bytes=LOG_BYTES-prior.LOG_BYTES),
        ca_membership=dict(snapshots_per_gesture=48,transactions_retained_per_gesture=3072,
            added_console_max_bytes=MAX_CONSOLE_BYTES,offline_sha256=sha(OFFLINE),updates_CA_timing=False),
        optimization='Retain exact CA membership and commit receipts per gesture.',
        performance_comparison='Compare 0388/0390 vblank and CRC under the same script and Core.')


def criteria(plan):
    admitted()
    previous = load(P388/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'ca_membership','optimization','performance_comparison'}
    require({k for k in previous.keys() | plan.keys() if plan.get(k)!=previous.get(k)}<=allowed,
        '0390 changed a device effect outside the CA timeline')
    a,b = (load(folder/'slot-delta/install-plan.json') for folder in (P388,BASE))
    require({name for name,row in b['rows'].items() if row['new_file_sha256']!=a['rows'][name]['new_file_sha256']}
        =={'admission'},'0390 user files differ beyond the kernel identity binding')
    model = load(BASE/'restore-model/result.json')
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and len(model['checks'])==49 and
        model['all_restore_partial_write_points']==17,'0390 bounded rollback model incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P388,HEADER,plan)


def storage(plan):
    inherited = load(P388/'storage-bound-388.json')
    components = dict(inherited['components'],compact_CA_receipts_and_post_restore_analysis=2_000_000)
    worst = sum(components.values())
    require(worst<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,'0390 reserve exceeded')
    return dict(inherited,state='bounded0390-CA-timeline-runtime',fresh_log_bytes=LOG_BYTES,
        log_cap_bytes=LOG_BYTES+LOG_SUFFIX,components=components,worst_case_bytes=worst)


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/name for name in scripts),DOC,OBSERVER_HEADER,KERNEL,IMAGE,OFFLINE,NATIVE_PROOF,
        BASE/'390-ca-timeline.patch',BASE/'live-batch-admission.json',BASE/'current-root-capture/result.json',
        BASE/'live-retirement/verified-retirement-manifest.json',
        MAIN/'tools/storage-budget.py',P388/'ready.json',P388/'trial-plan.json',P388/'capture-profile.json',
        P388/'storage-bound-388.json',P388/'restored-DPU-comparison.json',P389/'trial-plan.json',
        LAST/'restored-capture/result.json',*(LAST/name for name in TERMINAL_PINS),
        *(REFERENCE/name for name in prior.audit.PINS),prior388.MOTION_ANALYZER,
        Path(load(P388/'trial-plan.json')['observer_helper'])]
    for name in ('slot-delta','slot-capture','metadata-snapshot','restore-model','edr-native','c4-native','core-native'):
        files.extend(path for path in (BASE/name).rglob('*') if path.is_file())
    files.extend(CA/'tools'/path for path in ('check-frame390-display-port.py','check-frame390-membership.py',
        'frame390_membership.py','frame385_transactions.py','run-frame385-trial.py'))
    result = {str(path):sha(path) for path in files}
    for receipt in (OFFLINE,KERNEL,IMAGE,BASE/'edr-native/result.json',BASE/'core-native/result.json',
                    BASE/'c4-native/result.json',BASE/'restore-model/result.json'):
        data = load(receipt)
        for name,digest in (data.get('input_pins',{}) | data.get('archive',{}).get('source_pins',{})).items():
            require(sha(name)==digest and result.setdefault(name,digest)==digest,'0390 pinned input differs: '+name)
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
    actions = {action.__name__:action for action in (capture,package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(json.dumps(actions[parser.parse_args().step](),indent=2))
