#!/usr/bin/env python3
"""Prepare a single physical-touch preview with the 0384 display path."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

pacing = import_module('prepare-frame384')
shared, save = pacing.shared, pacing.save
P384 = MAIN/'research/tmp/gauguin-early-stage-worktree-20261123/research/tmp/frame-384'
P386 = MAIN/'research/tmp/gauguin-frame386-ca-swipe-arm-worktree-20261123/research/tmp/frame-386'
M343 = MAIN/'research/tmp/gauguin-manual-touch-worktree-20261119/research/tmp/manual-touch-343/edr-native'
BASE = WORK/'research/tmp/frame-387'
TRIAL = '0387'
HEADER = '4a01f180651a018098a30c373736fb01c99b5ec773762ccf42a0d0f2e49a3869'
LOG_BYTES = 244_698_090
RESERVE = 100_000_000
SUCCESS = '0387-manual-preview-finished-root-restored'
DOC = WORK/'docs/gauguin-frame-387-manual-touch-20261123.md'
PATCH = WORK/'xnu/patches/0298-gauguin-guard-physical-touch-preview.patch'
SHIM = pacing.parent.P382/'shim-native/Image'
IMAGE = BASE/'frame387-image.json'
FLAGS = ('approved','one_shot','allow_install','allow_restore','allow_rollback',
         'allow_misc_marker','allow_temporary_boot','allow_recovery_fallback',
         'allow_original_tail_reclaim','allow_completed_journal_header','allow_primary_free_count_update',
         'allow_physical_NVT_input','allow_bounded_0384_display_preview')
ARGUMENTS = {'sweetnvt':('0','1'), 'swp':('4','0'), 'gsp':('328','0'), 'sbp':('1','0'),
             'touch_lat':('1','0'), 'sweettzsample':('1','0'), 'sweettrace':('2','0')}


def command(parent):
    words = parent.split()
    keys = [word.partition('=')[0] for word in words]
    require(len(keys) == len(set(keys)) and all(f'{key}={old}' in words for key,(old,_) in ARGUMENTS.items()),
            '0384 preview argument donor differs')
    replace = {f'{key}={old}':f'{key}={new}' for key,(old,new) in ARGUMENTS.items()}
    return ' '.join(replace.get(word,word) for word in words)


def admitted():
    proof = load(BASE/'batch-admission.json')
    require(proof['admitted'] and proof['planned_batch_bytes'] == 218_000_000 and
            proof['current_accounted_bytes']+proof['planned_batch_bytes'] <= proof['limit_bytes'],
            'full manual preview batch was not admitted')


def baseline():
    restored = P386/'execution'
    proof = restored/'independent-restore.json'
    require(sha(proof) == '166f4dbcf318209eb8b5a19d58ac550a0668ad029c142c18bd4ea5eb6035190b'
            and load(proof)['root_header_sha256'] == HEADER and load(proof)['misc_original_4096_bytes_match'],
            '0386 independent restore differs')
    original = load(restored/'restored-capture/result.json')
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files']) == 31 and
            current['combined_log_bytes'] == LOG_BYTES and
            all(current[key] == original[key] for key in ('root_header_sha256','combined_log_bytes','files','directories')),
            'manual preview TWRP state differs from 0386')
    return current


def helper(image):
    pack = import_module('package-frame344')
    donor = load(M343/'result.json')
    reference = load(P384/'edr-native/result.json')
    binary = Path(donor['binary'])
    wanted = image['build_identity']
    require(sha(binary) == donor['binary_sha256'] and donor['scope_checks'] == 2146
            and donor['binary_bytes'] == reference['binary_bytes'] == 53520, 'manual EDR donor differs')
    source_paths = sorted((P384/'edr-native/sources').iterdir())
    for path in source_paths:
        projected = path.read_bytes().replace(reference['kernel_identity'].encode(),donor['kernel_identity'].encode())
        if path.name == 'EDRDefaultCore.h':
            projected = projected.replace(b'length == 7 && !memcmp(start, "gsp=328", 7)',
                                          b'length == 5 && !memcmp(start, "gsp=0", 5)')
        require(projected == (M343/'sources'/path.name).read_bytes(), 'manual and 0384 EDR policies differ')
    out = BASE/'edr-native'
    out.mkdir()
    target = out/binary.name
    subprocess.run(['codesign','--verify','--strict',str(binary)],check=True,capture_output=True,timeout=60)
    patched, signature = pack.retarget_edr_identity(binary.read_bytes(),donor['kernel_identity'].encode(),wanted.encode())
    target.write_bytes(patched)
    subprocess.run(['codesign','--force','--sign','-',str(target)],check=True,capture_output=True,timeout=60)
    subprocess.run(['codesign','--verify','--strict',str(target)],check=True,capture_output=True,timeout=60)
    require(target.stat().st_size == 53520 and patched[:signature] == target.read_bytes()[:signature],
            'signed helper differs outside the identity and signature')
    pins = (binary,M343/'result.json',P384/'edr-native/result.json',*source_paths,
            *(M343/'sources'/path.name for path in source_paths))
    return dict(state='0387-manual-EDR-signed-offline',binary=str(target),binary_sha256=sha(target),
        binary_bytes=target.stat().st_size,kernel_identity=wanted,identity_only_retarget=True,
        scope_checks=donor['scope_checks'],input_pins={str(path):sha(path) for path in pins},device_commands=0)


def package():
    admitted()
    pack = import_module('package-frame344')
    manifest = BASE/'native-kernel/build-manifest.json'
    require(sha(SHIM) == load(SHIM.parent/'result.json')['binary_sha256'], 'private scanout shim differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(manifest),base=BASE,trial=TRIAL,
        frame_capture_mode=9,scripted_motion=True,private_scanout_shim=SHIM,command_profile=command)
    old = load(P384/'trial-plan.json')
    a,b = (pack.parts(Path(path).read_bytes()) for path in (old['image'],image['image']))
    require(a[1] == b[1] and a[3] == b[3] and image['command'] == command(old['boot_command']) and
            image['image_bytes'] == old['image_bytes'], 'manual image changed the shim, DTB or container')
    image['kernel_manifest'] = str(manifest)
    save(IMAGE,image)
    save(BASE/'edr-native/result.json',helper(image))
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P384/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    return {key:image[key] for key in ('image_sha256','image_bytes')}


def delta():
    baseline()
    return shared.stage.delta(BASE,P384,trial=TRIAL,header=HEADER,baseline=P386/'execution/restored-capture/result.json')


def model():
    proof = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(proof['checks']),partial_points=proof['all_restore_partial_write_points'])


def expected_plan():
    before = baseline()
    parent = load(P384/'trial-plan.json')
    core,image,edr = map(load,(BASE/'native-kernel/build-manifest.json',IMAGE,BASE/'edr-native/result.json'))
    delta_path = BASE/'slot-delta/install-plan.json'
    install = load(delta_path)
    require(core['state'] == '0387-native-ARM64-linked' and core['baseline_reproduced_except_uuid']
            and core['input_pins'][str(PATCH)] == sha(PATCH) and core['inputs_unchanged']
            and {Path(path).stem for path in core['object_replacements']} == {'SweetFramebuffer','gauguin_ui_trace_board'}
            and core['identity'] == image['build_identity'] == edr['kernel_identity']
            and sha(core['kernel']) == core['kernel_sha256'] == image['kernel_sha256']
            and sha(image['image']) == image['image_sha256'] and image['command'] == command(parent['boot_command'])
            and edr['binary_sha256'] == sha(edr['binary']) == install['admission_sha256']
            and install['core_sha256'] == parent['owned_core_sha256'] and install['changed_ranges'] == 12
            and install['trial'] == TRIAL and install['root_header_sha256'] == HEADER
            and sha(BASE/'metadata-snapshot/misc-original.bin') == parent['misc_before_sha256'],
            'manual image, Core or reversible range differs')
    sizes = {path:before['files'][path]['bytes'] for path in parent['log_capture']['sizes']}
    require(sum(sizes.values()) == LOG_BYTES, 'manual log baseline differs')
    return dict(parent,state='prepared-frame387-manual-touch',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(P384/'trial-plan.json'),install_plan_sha256=sha(delta_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        boot_command=image['command'],kernel_identity=core['identity'],kernel_banner=core['kernel_banner'],
        EDR_helper_sha256=edr['binary_sha256'],storage_reserve_bytes=RESERVE,
        scripted_strokes=0,scripted_reports=0,wake_button_pairs_max=0,sustained_motion=None,
        main_thread_sampling=None, process_sampling=None,
        log_capture=dict(parent['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX),
        frame_capture=dict(parent['frame_capture'],starts_at='first valid physical contact with display on',
            publish_new_content_fps=False),
        user_input='physical-Novatek-touch-only',
        optimization='0384 DPU cadence and two-slot early staging under the existing guarded display window.',
        performance_comparison='Physical user interaction. No scripted score.')


def criteria(plan):
    admitted()
    restore = load(BASE/'restore-model/result.json')
    require(restore['all_model_IO_writes_memory_only'] and restore['install_ranges'] == 12
            and len(restore['checks']) == 49 and restore['all_restore_partial_write_points'] == 17
            and restore['input_pins'][str(BASE/'slot-delta/install-plan.json')] == plan['install_plan_sha256'],
            'manual restore model differs')
    require(load(BASE/'manual-host-proof.json')['test_passed'], 'manual trigger was not checked offline')
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P384,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256'] != old['rows'][name]['new_file_sha256']}
            == {'admission'}, 'manual root changed beyond the approved helper and six existing slots')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P384,HEADER,plan)


def storage(plan):
    original = load(P386/'storage-bound-386.json')
    names = ('kernel_ring_raw_and_decoded','observer_stdout_stderr','one_restore_preimage_and_target_set',
             'eight_executor_receipts','progress_and_restore_recipe','three_hash_manifests',
             'verified_log_suffixes','overhead_and_executor_output')
    components = {key:original['components'][key] for key in names}
    require(sum(components.values()) <= RESERVE, 'manual runtime reservation insufficient')
    return dict(state='bounded0387-physical-preview-runtime',components=components,worst_case_bytes=sum(components.values()))


def pins():
    helpers = [WORK/name for name in subprocess.check_output(
        ['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()]
    plan = expected_plan()
    files = [*helpers,DOC,PATCH,WORK/'xnu/patches/series',MAIN/'tools/storage-budget.py',
             SHIM,Path(plan['observer_helper']),Path(plan['image']),BASE/'batch-admission.json',
             BASE/'current-root-capture/result.json',BASE/'manual-host-proof.json',
             P386/'execution/independent-restore.json',P386/'execution/restored-capture/result.json',
             P384/'trial-plan.json',P386/'capture-profile.json']
    for folder in ('slot-delta','slot-capture','metadata-snapshot','restore-model'):
        files.extend(p for p in (BASE/folder).rglob('*') if p.is_file())
    extra = {}
    for name in ('native-kernel/build-manifest.json',IMAGE.name,'edr-native/result.json',
                 'core-native/result.json','c4-native/result.json','restore-model/result.json'):
        receipt = BASE/name
        files.append(receipt)
        data = load(receipt)
        extra.update(data.get('input_pins',{}))
        files.extend(Path(data[key]) for key in ('kernel','binary','image') if key in data)
    checked = {str(path):sha(path) for path in files}
    for name,digest in extra.items():
        require(sha(name) == digest and checked.setdefault(name,digest) == digest, 'manual input changed: '+name)
    return checked


def freeze():
    return shared.freeze(base=BASE,prior=P386,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__ == '__main__':
    actions = {fn.__name__:fn for fn in (package,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=actions)
    print(json.dumps(actions[parser.parse_args().step](),indent=2))
