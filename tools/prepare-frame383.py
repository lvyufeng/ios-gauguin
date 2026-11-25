#!/usr/bin/env python3
"""Freeze the IOKit mapping fix on top of the restored 0382 flip trial."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

parent = import_module('prepare-frame382')
shared, save = parent.shared, parent.save
TRIAL = '0383'
BASE = WORK/'research/tmp/frame-383'
P382 = MAIN/'research/tmp/gauguin-private-scanout-worktree-20261122/research/tmp/frame-382'
REFERENCE = P382/'execution'
HEADER = 'e323ba2907e25653cf374df86ef7027c89784d15bf12ad80b163b755005936b2'
LOG_BYTES = 228_692_828
BATCH = 355_000_000
PATCH = WORK/'xnu/patches/0294-gauguin-map-private-scanout-with-iokit.patch'
DOC = WORK/'docs/gauguin-frame-383-iokit-mapping-20261123.md'
HOST = BASE/'host-verification.json'
RETIREMENT = MAIN/'research/tmp/0383-storage-retirement'
SUCCESS = '0383-hardware-page-flips-and-visible-frames-verified-root-restored'
FLAGS = (*[flag for flag in parent.FLAGS if not flag.startswith('allow_0382')],
         'allow_0383_one_60Hz_boot_and_bounded_VIG0_page_flips_with_private_IOKit_mappings')


def check_budget():
    receipt = load(BASE/'build-storage-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes']==BATCH and
            receipt['current_accounted_bytes']+BATCH<=receipt['limit_bytes'], 'whole 0383 batch was not admitted')


def baseline():
    expected = {
        'result.json':'95f0c47f6ddd32f37ba04e4dcb882dee69be18cd6329430f79cbe8e788733182',
        'independent-restore.json':'c669483515175b715812403e3a7fcf035fb7a0d861700838289055d3ac4d6b50',
        'kernel.log':'6fb704b6eefb66d9eda88ce999352cd7dcbf2ba3d0c465a7896347f992a19dab',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in expected.items()), '0382 evidence differs')
    result = load(REFERENCE/'result.json')
    original = load(REFERENCE/'restored-capture/result.json')
    log = (REFERENCE/'kernel.log').read_text()
    route = import_module('run-frame381-trial').dma_route(log)
    require(result['restored'] and result['independent_restore_verified'] and result['static_root_comparison_passed'] and
            route['address_translation_bypassed_for_both'] and '10371072, 0x100021): failed with 3' in log and
            'SWEET F382 I ' not in log and original['root_header_sha256']==HEADER and
            original['combined_log_bytes']==LOG_BYTES, '0382 failure or recovery evidence differs')
    return original


def current_baseline():
    original = baseline()
    current = load(BASE/'current-root-capture/result.json')
    require(not current['device_writes'] and len(current['files'])==31 and
            all(current[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')),
            'fresh TWRP baseline differs from verified 0382')
    return current


def capture():
    check_budget()
    baseline()
    profile = load(P382/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    current_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P382/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    shim = P382/'shim-native/Image'
    require(sha(shim)==load(P382/'shim-native/result.json')['binary_sha256'],'0382 shim differs')
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
                           frame_capture_mode=9,scripted_motion=True,private_scanout_shim=shim)
    donor = load(P382/'trial-plan.json')
    before = pack.parts(Path(donor['image']).read_bytes())
    after = pack.parts(Path(image['image']).read_bytes())
    require(before[1]==after[1] and before[3]==after[3] and image['command']==donor['boot_command'] and
            42_000_000<image['image_bytes']<44_000_000, '0383 boot wrapper, DTB or command differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P382/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P382/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame383-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def delta():
    current_baseline()
    return shared.stage.delta(BASE,P382,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = current_baseline()
    previous = load(P382/'trial-plan.json')
    native,image,edr = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame383-image.json',
                                                     'edr-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0383-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).stem for p in native['object_replacements'].values()}=={'gauguin_ui_trace_board','SweetFramebuffer'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'], 'unqualified 0383 native build')
    require(image['command']==previous['boot_command'] and sha(image['image'])==image['image_sha256'] and
            installed['trial']==TRIAL and installed['changed_ranges']==12 and
            installed['core_sha256']==previous['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==previous['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==previous['C4_sha256'] and
            installed['rows']['c4']['data_extents']==load(P382/'slot-delta/install-plan.json')['rows']['c4']['data_extents'] and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==previous['misc_before_sha256'],
            '0383 image, EDR or slots differ')
    sizes = {name:current['files'][name]['bytes'] for name in previous['log_capture']['sizes']}
    require(sum(sizes.values())==LOG_BYTES,'0383 log reserve differs')
    return dict(previous,state='prepared-frame383-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(P382/'trial-plan.json'),install_plan_sha256=sha(slots),
        image=image['image'],image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],
        kernel_identity=native['identity'],kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(previous['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,
            previous_verified_suffix_bytes=LOG_BYTES-previous['log_capture']['measured_baseline_bytes']),
        display_dma=dict(previous['display_dma'],private_iokit_WC_maps=True,readback_failure_discards_mappings=True,
            mapping_proof_sha256=sha(HOST),cache_mode='same physical IOKit mapping as inherited front'),
        optimization='Use IOKit for the two private framebuffer maps. The flip and write limits remain identical.')


def storage(plan):
    previous = load(P382/'storage-bound-382.json')
    parts = dict(previous['components'])
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0383 runtime exceeds reservation')
    return dict(previous,state='bounded0383-map-fix-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    previous = load(P382/'trial-plan.json')
    allowed = {'state','trial','root_header_sha256','parent_trial_plan_sha256','install_plan_sha256','image',
        'image_sha256','image_bytes','kernel_identity','kernel_banner','EDR_helper_sha256','log_capture',
        'optimization','display_dma'}
    require({k for k in plan.keys()|previous.keys() if plan.get(k)!=previous.get(k)}<=allowed and
            plan['frame_capture']==previous['frame_capture'] and
            plan['display_dma']['maximum_additional_volatile_stores']==2050,
            '0383 changed an effect outside the mapping fix')
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P382,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0383 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(host['patch_sha256']==sha(PATCH) and host['mapping_cases']==6 and not host['device_commands'] and
            rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'],
            '0383 recovery or mapping proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P382,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame383-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json')
    extra = [HOST,*[RETIREMENT/name for name in ('verified-retirement-manifest.json','build-admission.json')],
             P382/'shim-native/result.json',P382/'shim-native/Image',REFERENCE/'kernel.log',REFERENCE/'kernel.log.bin',
             parent.REFERENCE/'display-dma-preflight.json']
    # Full scanout measurements do not exist for the early-returned 0382
    # candidate. Pin the complete 0381 control and the raw 0382 failure.
    return shared.pins(base=BASE,prior=P382,doc=DOC,patch=PATCH,reference=parent.REFERENCE,trial=TRIAL,
                       extra=[*extra,REFERENCE/'result.json',REFERENCE/'independent-restore.json',
                              REFERENCE/'restored-capture/result.json'],
                       artifacts=[BASE/name for name in names])


def freeze():
    return shared.freeze(base=BASE,prior=P382,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
