#!/usr/bin/env python3
"""Freeze the 0389 Core comparison over the restored 0388 root."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, WORK, load, require, sha

prior = import_module('prepare-frame388')
audit = import_module('audit-frame388-restored')
core_check = import_module('check-frame389-core')
shared, save = prior.shared, prior.save
TRIAL = '0389'
BASE = core_check.BASE
P388 = MAIN/'research/tmp/gauguin-frame388-android-display-worktree-20261123/research/tmp/frame-388'
REFERENCE = P388/'execution'
HEADER = '2a4526ef2541d67680dd4dc564dac3f6255e398ad6218ba4e3a8368845c1f61f'
LOG_BYTES = 248_828_732
BATCH, RESERVE = 300_000_000, prior.RESERVE
DOC = WORK/'docs/gauguin-frame-389-hardware-trial-20261123.md'
FLAGS = (*[flag for flag in prior.FLAGS if not flag.startswith('allow_0388')],
         'allow_0389_one_60Hz_temporary_boot_with_exact_0388_image_and_packet_recording_Core')
SUCCESS = '0389-DPU-and-packet-recording-measured-root-restored'
CORE = BASE/'core-native/result.json'
HOST = BASE/'host/result.json'


def admitted():
    budget = load(BASE/'live-batch-admission.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] == BATCH and
            budget['current_accounted_bytes']+BATCH <= budget['limit_bytes'],
            'combined 0389 preparation and runtime batch exceeds storage')


def baseline(*, fresh=True):
    require(all(sha(REFERENCE/name)==audit.PINS[name] for name in
                ('result.json','independent-restore.json','restored-capture/result.json')),
            '0388 restore evidence changed')
    terminal, proof, original = (load(REFERENCE/name) for name in
        ('result.json','independent-restore.json','restored-capture/result.json'))
    require(terminal['restored'] and terminal['independent_restore_verified'] and
            terminal['static_root_comparison_passed'] and proof['journal_empty'] and
            proof['misc_original_4096_bytes_match'] and proof['all_original_slot_bits_allocated'] and
            proof['root_header_sha256']==original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES,'0388 recovery is incomplete')
    if not fresh:
        return original
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and
            all(current[key]==original[key] for key in ('files','directories','root_header_sha256','combined_log_bytes')),
            'the current read-only root differs from the independent 0388 recovery')
    return current


def capture():
    admitted()
    baseline(fresh=False)
    profile = load(P388/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    if not (BASE/'current-root-capture/result.json').exists():
        import_module('capture-core342-root').capture(profile,save_files=False)
    baseline()
    if not (BASE/'slot-capture/result.json').exists():
        proc = subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),
            '--baseline',str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
            '--reuse-data-from',str(P388/'slot-capture')],capture_output=True,text=True,timeout=300)
        require(proc.returncode==0,'read-only slot capture failed: '+proc.stderr[-1500:])
    metadata = BASE/'metadata-snapshot'
    receipt = (load(metadata/'result.json') if (metadata/'result.json').exists() else
        import_module('capture-core342-metadata').capture(metadata,HEADER,trial=TRIAL,maximum_compressed_bytes=28_000_000))
    return {key:receipt[key] for key in ('compressed_bytes','device_writes','device_boots')}


def delta():
    baseline()
    core = load(CORE)
    for kind in ('edr','c4'):
        receipt = BASE/(kind+'-native/result.json')
        receipt.parent.mkdir(exist_ok=True)
        exact = load(P388/(kind+'-native/result.json'))
        if not receipt.exists():
            save(receipt,exact)
        require(load(receipt)==exact,'prior userspace receipt differs: '+kind)
    return shared.stage.delta(BASE,P388,trial=TRIAL,header=HEADER,
        baseline=REFERENCE/'restored-capture/result.json',core_logical=core['bytes'])


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return dict(checks=len(result['checks']),partial_points=result['all_restore_partial_write_points'])


def expected_plan():
    current = baseline()
    reference_file = P388/'trial-plan.json'
    reference = load(reference_file)
    core, host = load(CORE), load(HOST)
    delta_file = BASE/'slot-delta/install-plan.json'
    install = load(delta_file)
    require(core['state']=='0389-exact-ARM64-Core-signed' and core['signature_verified'] and core['bytes']==7_975_728 and
            core['reconstructed_reference_sha256']==reference['owned_core_sha256']==core_check.REFERENCE_SHA and
            core['binary_sha256']==sha(core['binary'])==install['core_sha256'] and
            core['bytes']==install['rows']['core']['new_logical'] and
            host['state']=='0389-packet-recording-verified-offline' and host['host_time_improvement'] and
            host['ownership_checks']==23 and core['source_sha256']==host['source_sha256'] and
            not host['device_commands'] and not core['device_commands'],'0389 offline signed candidate differs')
    require(sha(reference['image'])==reference['image_sha256'] and
            load(BASE/'edr-native/result.json')==load(P388/'edr-native/result.json') and
            install['admission_sha256']==reference['EDR_helper_sha256'] and install['changed_ranges']==12 and
            install['trial']==TRIAL and install['root_header_sha256']==HEADER and
            sha(BASE/'metadata-snapshot/misc-original.bin')==reference['misc_before_sha256'] and
            (reference['scripted_strokes'],reference['scripted_reports'],reference['sustained_motion']['normal_reports'])
            ==(13,442,162) and reference['frame_capture']['target_refresh_hz']==60 and
            reference['frame_capture']['modesets']==0 and reference['frame_capture']['crc_required_preimage']==0x01000000 and
            reference['frame_capture']['crc_cleanup_readback_equals_recorded_preimage'],
            '0388 boot, scripted input or frozen CRC limits differ')
    sizes = {key:current['files'][key]['bytes'] for key in reference['log_capture']['sizes']}
    return dict(reference,state='prepared-frame389-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(reference_file),install_plan_sha256=sha(delta_file),
        owned_core_sha256=core['binary_sha256'],owned_core_logical_bytes=core['bytes'],
        matched_Core_control=dict(reference['matched_Core_control'],installed_this_trial=False),
        log_capture=dict(reference['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,previous_verified_suffix_bytes=
            LOG_BYTES-reference['log_capture']['measured_baseline_bytes']),
        packet_recording=dict(host_proof_sha256=sha(HOST),command_packet_bytes_identical=True,
            replacement_core_receipt_sha256=sha(CORE)),
        optimization='Skip duplicate CPU work on unchanged render register packets.',
        performance_comparison='Compare 0388 and 0389 scan ordinals, exact moving submissions and first response.')


def criteria(plan):
    admitted()
    previous = load(P388/'trial-plan.json')
    adjustable = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256',
        'owned_core_sha256','owned_core_logical_bytes','matched_Core_control','log_capture',
        'packet_recording','optimization','performance_comparison'}
    require({key for key in previous.keys() | plan.keys() if previous.get(key)!=plan.get(key)} <= adjustable,
            '0389 effects differ outside the Core-only comparison')
    old, new = (load(root/'slot-delta/install-plan.json') for root in (P388,BASE))
    require({name for name,row in new['rows'].items() if row['new_file_sha256']!=old['rows'][name]['new_file_sha256']}
            == {'core'}, '0389 userspace differs outside the Core')
    rollback = load(BASE/'restore-model/result.json')
    require(rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            len(rollback['checks'])==49 and rollback['all_restore_partial_write_points']==17 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'],
            '0389 rollback proof is incomplete')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P388,HEADER,plan)


def storage(plan):
    bound = load(P388/'storage-bound-388.json')
    require(bound['worst_case_bytes']==sum(bound['components'].values())<=RESERVE and
            plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,'0389 result files exceed the runtime reserve')
    return dict(bound,state='bounded0389-Core-comparison-runtime',fresh_log_bytes=LOG_BYTES,
                log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def pins():
    scripts = subprocess.check_output(['git','ls-files','tools/*.py','tools/*.sh'],cwd=WORK,text=True).splitlines()
    files = [*(WORK/name for name in scripts),DOC,core_check.PATCH,core_check.FIXTURE,CORE,HOST,
        MAIN/'tools/storage-budget.py',BASE/'core-build-admission.json',BASE/'live-batch-admission.json',
        BASE/'current-root-capture/result.json',P388/'ready.json',P388/'trial-plan.json',P388/'capture-profile.json',
        P388/'storage-bound-388.json',P388/'restored-DPU-comparison.json',P388/'0388-supply-audit.json',
        *(REFERENCE/name for name in (*audit.PINS, 'kernel-IO-analysis.json', 'kernel-IO-identity-analysis.json')),
        prior.MOTION_ANALYZER,
        *(Path(load(P388/'trial-plan.json')[key]) for key in ('image','observer_helper'))]
    retirement = BASE/'live-retirement/verified-retirement-manifest.json'
    if retirement.is_file():
        files.append(retirement)
    for name in ('slot-delta','slot-capture','metadata-snapshot','restore-model','edr-native','c4-native'):
        files.extend(path for path in (BASE/name).rglob('*') if path.is_file())
    result = {str(path):sha(path) for path in files}
    for path in (CORE,HOST,BASE/'edr-native/result.json',BASE/'c4-native/result.json'):
        receipt = load(path)
        for name,digest in receipt.get('input_pins',{}).items():
            require(sha(name)==digest and result.setdefault(name,digest)==digest,'0389 pinned input differs: '+name)
        if 'binary' in receipt:
            result[receipt['binary']] = sha(receipt['binary'])
    return result


def freeze():
    return shared.freeze(base=BASE,prior=P388,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {action.__name__:action for action in (capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
