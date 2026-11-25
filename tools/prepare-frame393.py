#!/usr/bin/env python3
"""Freeze an exact per-member CA timeline over the restored 0395 control."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha
from frame393_build import BASE, HEADER, PREP392 as KERNEL_CONTROL, PREVIOUS
from frame393_timeline import MAX_CONSOLE_BYTES, MAX_RECEIPTS

previous = import_module('prepare-frame392')
P391, P388, BATCH, RESERVE, shared, save = (previous.P391,previous.P388,previous.BATCH,
    previous.RESERVE,previous.shared,previous.save)
KERNEL = BASE/'native-kernel/build-manifest.json'
IMAGE = BASE/'frame393-image.json'
OFFLINE = BASE/'offline.json'
P395 = (MAIN/'research/tmp/gauguin-frame395-native-scope-worktree-20261123'
        /'research/tmp/frame-395')
LAST = P395/'execution'
TRIAL = '0393'
DOC = WORK/'docs/gauguin-frame-393-ca-members-20261123.md'
FLAGS = (*[flag for flag in previous.FLAGS if not flag.startswith('allow_0392')],
         'allow_0393_one_bounded_60Hz_temporary_boot_with_per_context_CA_receipts')
SUCCESS = '0393-per-context-CA-physical-timeline-measured-root-restored'


def admitted():
    receipt = load(BASE/'live-batch-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes']==BATCH and
        receipt['current_accounted_bytes']+BATCH<=receipt['limit_bytes'],'0393 full batch exceeds storage')


def baseline(*, fresh=True):
    end,proof,restored = (load(LAST/path) for path in
        ('result.json','independent-restore.json','restored-capture/result.json'))
    replay = load(LAST/'score-replay-0395.json')
    require(end['restored'] and end['independent_restore_verified'] and end['static_root_comparison_passed'] and
        proof['install_plan_sha256']==load(P395/'trial-plan.json')['install_plan_sha256'] and
        proof['journal_empty'] and proof['all_original_slot_bits_allocated'] and proof['misc_original_4096_bytes_match'] and
        proof['root_header_sha256']==restored['root_header_sha256'] and
        replay['state']=='0395-physical-score-replayed-after-independent-restore' and not replay['device_commands'] and
        replay['compiled_EDR_activation'] and replay['DPU_independent_physical_FPS_qualified'] and
        not replay['stable_60_fps_observed'] and all(sha(path)==digest for path,digest in replay['input_pins'].items()),
        '0395 restore must be independently verified and stable 60 fps unfinished')
    if not fresh:
        return restored
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and all(current[key]==restored[key]
        for key in ('root_header_sha256','combined_log_bytes','files','directories')),'current TWRP root differs from 0395')
    return current


def verify_helper():
    pack = import_module('package-frame344')
    machine = import_module('check-frame395-edr')
    image = load(IMAGE)
    native,host = load(KERNEL),load(OFFLINE)
    patch = BASE/'393-ca-members.patch'
    require(native['state']=='0393-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
        native['input_pins'][str(patch)]==host['stage_patch_sha256']==sha(patch) and
        not host['device_commands'] and native['inputs_unchanged'],'0393 native kernel inputs differ')
    reference = load(KERNEL_CONTROL/'trial-plan.json')
    orig,new = (pack.parts(Path(path).read_bytes()) for path in (reference['image'],image['image']))
    require(orig[0][:16]==new[0][:16] and orig[0][20:]==new[0][20:] and orig[1]==new[1] and orig[3]==new[3] and
        reference['boot_command']==image['command'] and sha(image['image'])==image['image_sha256'],
        '0393 wrapper, DTB or exact stock boot arguments differ')
    control_path = P395/'edr-native/result.json'
    control = load(control_path)
    admission = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P391/'edr-native/result.json',profile=('gpf=4','gpf=5'))
    old,new = (Path(item['binary']) for item in (control,admission))
    w = machine.native_words(new)
    require(w[0x4be0]==0x528006a4 and w==machine.native_words(old) and sha(old)==control['binary_sha256'],
            '0393 EDR machine code differs from compiled stock scope')
    admission['input_pins'].update({str(control_path):sha(control_path),str(old):sha(old)})
    admission['matching_0395_machine_code'] = True
    save(BASE/'edr-native/result.json',admission)
    return dict(binary_sha256=admission['binary_sha256'],native_scope_matches_0395=True)


def capture():
    admitted()
    return previous.capture_from(BASE,P395,TRIAL,baseline)


def delta():
    return shared.stage.delta(BASE,P395,trial=TRIAL,header=baseline()['root_header_sha256'],
        baseline=LAST/'restored-capture/result.json',core_logical=7_975_712)


def model():
    r = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(r['checks']),failure_points=r['all_restore_partial_write_points'])


def expected_plan():
    live = baseline()
    native,image,edr,host = (load(path) for path in (KERNEL,IMAGE,BASE/'edr-native/result.json',OFFLINE))
    parent_path = P395/'trial-plan.json'
    parent = load(parent_path)
    install_path = BASE/'slot-delta/install-plan.json'
    install = load(install_path)
    header,size = (live[key] for key in ('root_header_sha256','combined_log_bytes'))
    require(host['exact_members']==2 and host['ASan_UBSan'] and sha(image['image'])==image['image_sha256'] and
        sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and edr['matching_0395_machine_code'] and
        image['command']==parent['boot_command'] and image['build_identity']==native['identity']==edr['kernel_identity'] and
        sha(edr['binary'])==edr['binary_sha256']==install['admission_sha256'] and
        install['core_sha256']==parent['owned_core_sha256'] and install['trial']==TRIAL and
        install['root_header_sha256']==header and install['changed_ranges']==12 and
        sha(BASE/'metadata-snapshot/misc-original.bin')==parent['misc_before_sha256'] and
        parent['frame_capture']['target_refresh_hz']==60 and not parent['frame_capture']['modesets'] and
        parent['frame_capture']['crc_required_preimage']==0x01000000 and parent['scripted_strokes']==13 and
        parent['sustained_motion']['normal_reports']==162,'0393 timing, userspace or recovery scope differs')
    return dict(parent,state='prepared-frame393-one-shot',trial=TRIAL,root_header_sha256=header,
        parent_trial_plan_sha256=sha(parent_path),install_plan_sha256=sha(install_path),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(parent['log_capture'],measured_baseline_bytes=size,max_combined_log_bytes=size+LOG_SUFFIX,
            sizes={key:live['files'][key]['bytes'] for key in parent['log_capture']['sizes']},
            previous_verified_suffix_bytes=size-parent['log_capture']['measured_baseline_bytes']),
        signed_native_EDR_scope_sha256=sha(BASE/'source-compiled-scope.json'),
        CA_member_timeline=dict(strokes=13,per_stroke_exact_receipts=MAX_RECEIPTS,console_limit_bytes=MAX_CONSOLE_BYTES,
                                original_debug_gate_preserved=True,offline_sha256=sha(OFFLINE)),
        optimization='Measure each exact source context in the visible update without changing timing.',
        performance_comparison='Compare 0395 and 0393 against the same vblank/CRC and separate onset and motion.')


def criteria(plan):
    admitted()
    parent = load(P395/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'CA_member_timeline','signed_native_EDR_scope_sha256','optimization','performance_comparison'}
    require({k for k in parent.keys() | plan.keys() if plan.get(k)!=parent.get(k)}<=allowed,'0393 behavior scope differs')
    old,new = (load(root/'slot-delta/install-plan.json') for root in (P395,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
        =={'admission'},'0393 userspace scope differs beyond image admission')
    model = load(BASE/'restore-model/result.json')
    require(model['all_model_IO_writes_memory_only'] and model['install_ranges']==12 and len(model['checks'])==49 and
        model['all_restore_partial_write_points']==17,'0393 rollback model differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P395,plan['root_header_sha256'],plan)


def storage(plan):
    old = load(P395/'storage-bound-395.json')
    require(old['worst_case_bytes']<=RESERVE,'0393 runtime exceeds reserve')
    return dict(old,state='bounded0393-CA-member-runtime',fresh_log_bytes=plan['log_capture']['measured_baseline_bytes'],
                log_cap_bytes=plan['log_capture']['max_combined_log_bytes'])


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/path for path in scripts),DOC,HEADER,PREVIOUS,OFFLINE,KERNEL,IMAGE,
        MAIN/'tools/storage-budget.py',BASE/'package-admission.json',BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',BASE/'verified-retirement-manifest.json',BASE/'source-compiled-scope.json',
        P388/'restored-DPU-comparison.json',P395/'ready.json',P395/'trial-plan.json',P395/'capture-profile.json',
        P395/'storage-bound-395.json',*(LAST/path for path in ('result.json','independent-restore.json',
            'restored-capture/result.json','score-replay-0395.json','edr-activation.json',
            'scanout-comparison-0391-0395.json','kernel.log','kernel.log.bin','page-flip-latches.json')),
        *(previous.previous.REFERENCE/name for name in previous.previous.previous.prior.audit.PINS),
        previous.previous.previous.prior388.MOTION_ANALYZER,Path(load(P395/'trial-plan.json')['observer_helper'])]
    return previous.scoped_pins(BASE,files,KERNEL,IMAGE)


def freeze():
    return shared.freeze(base=BASE,prior=P395,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    actions = {action.__name__:action for action in (verify_helper,capture,delta,model,freeze,review)}
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=actions)
    print(json.dumps(actions[cli.parse_args().step](),indent=2))
