#!/usr/bin/env python3
"""Package and freeze the stage behind the 0381 display DMA qualification."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import shutil
import subprocess
import sys

from frame366_scope import LOG_SUFFIX, MAIN, RESERVE, WORK, load, require, sha

preflight = import_module('prepare-frame381')
shared = preflight.shared
save = shared.stage.save
TRIAL = '0382'
P381 = MAIN/'research/tmp/gauguin-page-flip-worktree-20261122/research/tmp/frame-381'
BASE = WORK/'research/tmp/frame-382'
REFERENCE = P381/'execution'
HEADER = 'faebf4608abde011fd485b1e9376e231a7a155c1c116932e7d4789b36b1d3762'
LOG_BYTES = 228_476_457
BATCH = 370_000_000
PATCH = WORK/'xnu/patches/0293-gauguin-stage-scanout-behind-confirmed-latch.patch'
DOC = WORK/'docs/gauguin-frame-382-page-flip-20261123.md'
HOST = BASE/'host-verification.json'
RETIREMENT = MAIN/'research/tmp/0381-flip-retirement'
FLAGS = (*[flag for flag in preflight.FLAGS if not flag.startswith('allow_0381')],
         'allow_0382_one_60Hz_boot_and_bounded_VIG0_page_flips')
SUCCESS = '0382-hardware-page-flips-and-visible-frames-verified-root-restored'


def check_budget():
    receipt = load(BASE/'build-storage-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes']==BATCH and
            receipt['current_accounted_bytes']+BATCH<=receipt['limit_bytes'], 'whole flip batch not admitted')


def baseline():
    expected = {
        'result.json':'2581c808a26c102f0a7fb76ac65d57f0d261f175b648fdfbe3aaa6803a654029',
        'independent-restore.json':'e161cdd3ec2fa86611b62adf23b655a9fe6244cc8fab4652d24eb507fda5c95a',
        'display-dma-preflight.json':'32751e3bf768753f7f9094c5beccd561cf8e7ea4fe270d8cb790dd555abb9eb4',
    }
    require(all(sha(REFERENCE/name)==digest for name,digest in expected.items()), '0381 evidence differs')
    terminal = load(REFERENCE/'result.json')
    original = load(REFERENCE/'restored-capture/result.json')
    require(terminal['restored'] and terminal['independent_restore_verified'] and terminal['static_root_comparison_passed'] and
            terminal['display_DMA_qualification']['address_translation_bypassed_for_both'] and
            original['root_header_sha256']==HEADER and original['combined_log_bytes']==LOG_BYTES, 'unqualified 0381 baseline')
    return original


def current_baseline():
    original = baseline()
    fresh = load(BASE/'current-root-capture/result.json')
    require(not fresh['device_writes'] and len(fresh['files'])==31 and
            all(fresh[k]==original[k] for k in ('files','directories','root_header_sha256','combined_log_bytes')),
            'fresh TWRP baseline differs from verified 0381')
    return fresh


def capture():
    check_budget()
    baseline()
    profile = load(P381/'capture-profile.json')
    profile.update(out=str((BASE/'current-root-capture').relative_to(MAIN)),expected_header_sha256=HEADER,
                   max_combined_log_bytes=LOG_BYTES)
    import_module('capture-core342-root').capture(profile,save_files=False)
    current_baseline()
    subprocess.run([sys.executable,str(WORK/'tools/capture-sb-cadence-slot.py'),'--baseline',
        str(REFERENCE/'restored-capture/result.json'),'--out',str(BASE/'slot-capture'),
        '--reuse-data-from',str(P381/'slot-capture')],check=True,capture_output=True,timeout=300)
    meta = import_module('capture-core342-metadata').capture(BASE/'metadata-snapshot',HEADER,trial=TRIAL,
                                                           maximum_compressed_bytes=28_000_000)
    return {k:meta[k] for k in ('compressed_bytes','device_writes','device_boots')}


def shim_image(out=None, *, state='0382-arm64-shim-linked'):
    out = BASE/'shim-native' if out is None else out
    out.mkdir()
    llvm = Path('/opt/homebrew/opt/llvm/bin')
    lld = Path('/opt/homebrew/bin/ld.lld')
    flags = ('--target=aarch64-none-elf','-O2','-ffreestanding','-fno-pic','-fno-jump-tables','-mgeneral-regs-only',
             '-mstrict-align','-fno-stack-protector','-Wall','-Wextra')
    sources = tuple(WORK/'shim'/name for name in
                    ('start.S','shim.c','console.c','mmu.c','fdt.c','loader.c','pas_reservation.c','ufs.c'))

    def invoke(name, argv):
        result = subprocess.run(argv,cwd=WORK,capture_output=True,timeout=90)
        (out/(name+'.log')).write_bytes(result.stdout+result.stderr)
        require(result.returncode==0, name+' failed')
        return result.stdout.decode()

    objects = []
    for source in sources:
        obj = out/(source.stem+'.o')
        invoke(source.stem,[llvm/'clang',*flags,'-c',source,'-o',obj])
        if source.name!='start.S':
            require('R_AARCH64_ABS64' not in invoke(source.stem+'-relocations',[llvm/'llvm-readelf','-r',obj]),
                    'shim C holds an absolute relocation')
        objects.append(obj)
    elf, image = (out/name for name in ('shim.elf','Image'))
    link = WORK/'shim/shim.ld'
    invoke('link',[lld,'--build-id=none','-T',link,'-N',*objects,'-o',elf])
    require('There are no relocations' in invoke('elf-relocations',[llvm/'llvm-readelf','-r',elf]) and
            not invoke('undefined',[llvm/'llvm-nm','-u',elf]).strip(), 'unresolved relocated shim')
    symbols = {row.split()[-1]:int(row.split()[0],16) for row in
               invoke('symbols',[llvm/'llvm-nm',elf]).splitlines() if len(row.split())==3}
    invoke('binary',[llvm/'llvm-objcopy','-O','binary',elf,image])
    require(symbols['_head']==0 and image.stat().st_size<symbols['_end']<0x100000,
            'invalid shim head, payload or stack geometry')
    with image.open('r+b') as stream:
        stream.truncate(symbols['_end'])
    pins = (*sources,*sorted((WORK/'shim').glob('*.h')),link,elf,lld,
            *(llvm/name for name in ('clang','llvm-nm','llvm-objcopy','llvm-readelf')))
    save(out/'result.json',dict(state=state,binary=str(image),binary_sha256=sha(image),
        bytes=image.stat().st_size,input_pins={str(p):sha(p) for p in pins},device_commands=0))
    return image


def package():
    check_budget()
    pack = import_module('package-frame344')
    native = BASE/'native-kernel/build-manifest.json'
    shim = shim_image()
    image = pack.boot_image(load(pack.P343/'runtime343-image.json'),load(native),base=BASE,trial=TRIAL,
                           frame_capture_mode=9,scripted_motion=True,private_scanout_shim=shim)
    donor = load(P381/'trial-plan.json')
    before = pack.parts(Path(donor['image']).read_bytes())
    after = pack.parts(Path(image['image']).read_bytes())
    require(before[3]==after[3] and after[1]==shim.read_bytes() and
            image['command']==donor['boot_command'] and 42_000_000<image['image_bytes']<44_000_000,
            '0382 boot arguments, DTB or wrapper differ')
    image['kernel_manifest'] = str(native)
    edr = pack.edr(image,base=BASE,trial=TRIAL,signed_reference=P381/'edr-native/result.json')
    for name in ('core','c4'):
        (BASE/(name+'-native')).mkdir()
        shutil.copyfile(P381/(name+'-native')/'result.json',BASE/(name+'-native')/'result.json')
    save(BASE/'edr-native/result.json',edr)
    save(BASE/'frame382-image.json',image)
    return {k:image[k] for k in ('image','image_sha256','image_bytes')}


def delta():
    current_baseline()
    return shared.stage.delta(BASE,P381,trial=TRIAL,header=HEADER,baseline=REFERENCE/'restored-capture/result.json')


def model():
    result = import_module('check-core342-rollback').check(BASE,BASE/'restore-model',trial=TRIAL)
    return {k:v for k,v in result.items() if k not in ('input_pins','checks')} | {'checks':len(result['checks'])}


def expected_plan():
    current = current_baseline()
    previous = load(P381/'trial-plan.json')
    native,image,edr,shim = (load(BASE/name) for name in ('native-kernel/build-manifest.json','frame382-image.json',
                                       'edr-native/result.json','shim-native/result.json'))
    slots = BASE/'slot-delta/install-plan.json'
    installed = load(slots)
    require(native['state']=='0382-native-ARM64-linked' and native['baseline_reproduced_except_uuid'] and
            native['inputs_unchanged'] and native['input_pins'][str(PATCH)]==sha(PATCH) and
            {Path(p).stem for p in native['object_replacements'].values()}=={'gauguin_ui_trace_board','SweetFramebuffer'} and
            sha(native['kernel'])==native['kernel_sha256']==image['kernel_sha256'] and
            native['identity']==image['build_identity']==edr['kernel_identity'] and
            image['input_pins'][shim['binary']]==shim['binary_sha256']==sha(shim['binary']), '0382 exact build differs')
    require(image['command']==previous['boot_command'] and sha(image['image'])==image['image_sha256'] and
            installed['trial']==TRIAL and installed['changed_ranges']==12 and
            installed['core_sha256']==previous['owned_core_sha256'] and
            installed['rows']['eagl']['new_file_sha256']==previous['SB_sha256'] and
            installed['rows']['c4']['new_file_sha256']==previous['C4_sha256'] and
            installed['rows']['c4']['data_extents']==load(P381/'slot-delta/install-plan.json')['rows']['c4']['data_extents'] and
            installed['admission_sha256']==edr['binary_sha256']==sha(edr['binary']) and edr['identity_only_retarget'] and
            sha(BASE/'metadata-snapshot/misc-original.bin')==previous['misc_before_sha256'],
            '0382 image, EDR or slots differ')
    sizes = {name:current['files'][name]['bytes'] for name in previous['log_capture']['sizes']}
    frame = previous['frame_capture']
    reference_bytes = (REFERENCE/'kernel.log').stat().st_size
    require(sum(sizes.values())==LOG_BYTES and reference_bytes+110_000<4_194_304 and
            frame['target_refresh_hz']==60 and frame['modesets']==0 and frame['crc_preimage_reads']==2 and
            frame['crc_required_preimage']==0x01000000 and frame['maximum_volatile_crc_register_writes']==4 and
            frame['crc_cleanup_readback_equals_recorded_preimage'] and previous['scripted_strokes']==13 and
            previous['sustained_motion']['normal_reports']==162, '0382 CRC, input or console scope differs')
    return dict(previous,state='prepared-frame382-one-shot',trial=TRIAL,root_header_sha256=HEADER,
        parent_trial_plan_sha256=sha(P381/'trial-plan.json'),install_plan_sha256=sha(slots),image=image['image'],
        image_sha256=image['image_sha256'],image_bytes=image['image_bytes'],kernel_identity=native['identity'],
        kernel_banner=native['kernel_banner'],EDR_helper_sha256=edr['binary_sha256'],
        log_capture=dict(previous['log_capture'],sizes=sizes,measured_baseline_bytes=LOG_BYTES,
            max_combined_log_bytes=LOG_BYTES+LOG_SUFFIX,reference_kernel_log_bytes=reference_bytes,
            reserved_frame_console_bytes=4_194_304-reference_bytes,
            previous_verified_suffix_bytes=LOG_BYTES-previous['log_capture']['measured_baseline_bytes']),
        frame_capture=dict(frame,maximum_total_display_register_writes=2054),
        display_dma=dict(probe=previous['display_dma'],proof_sha256=sha(REFERENCE/'display-dma-preflight.json'),
            prospective_buffer_mapping_bytes=20_742_144,prospective_buffer_access_bytes=10_368_000*1025+12,
            flips=1024,restore_display_front_flips=1,
            volatile_store_addresses=['0x0ae05014','0x0ae02018'],maximum_additional_volatile_stores=2050,
            page_flip_position_polls_max=40960,page_flip_mmio_reads_upper_bound=5_242_912,
            timeout_ns=45_000_000,guard_lines_at_least=192,host_verification_sha256=sha(HOST)),
        optimization='Stage a full guarded frame in a private inactive buffer and wait for a confirmed hardware latch.',
        performance_comparison='0380 and 0381 control by gesture and physical scan ordinal. Retest stroke 4 and slow drag.')


def storage(plan):
    previous = load(P381/'storage-bound-381.json')
    parts = dict(previous['components'])
    require(sum(parts.values())<=RESERVE and plan['log_capture']['measured_baseline_bytes']==LOG_BYTES,
            '0382 runtime exceeds reservation')
    return dict(previous,state='bounded0382-flip-runtime-batch',components=parts,worst_case_bytes=sum(parts.values()),
                fresh_log_bytes=LOG_BYTES,log_cap_bytes=LOG_BYTES+LOG_SUFFIX)


def criteria(plan):
    check_budget()
    old,new = (load(path/'slot-delta/install-plan.json') for path in (P381,BASE))
    require({n for n in new['rows'] if new['rows'][n]['new_file_sha256']!=
             old['rows'][n]['new_file_sha256']}=={'admission'}, '0382 userspace changed beyond EDR identity')
    rollback = load(BASE/'restore-model/result.json')
    host = load(HOST)
    require(host['patch_sha256']==sha(PATCH) and host['lifetime']['missing_store_barrier_prevents_reuse'] and
            host['lifetime']['timeout_pins_both'] and host['fixture_cases']>=5 and not host['device_commands'] and
            rollback['all_model_IO_writes_memory_only'] and rollback['install_ranges']==12 and
            rollback['all_restore_partial_write_points']==17 and len(rollback['checks'])==49 and
            rollback['input_pins'][str(BASE/'slot-delta/install-plan.json')]==plan['install_plan_sha256'],
            '0382 host lifetime, scoring or restore proof differs')
    import_module('review-frame344-trial').check_effect_bounds(BASE,P381,HEADER,plan)


def pins():
    names = ('native-kernel/build-manifest.json','frame382-image.json','edr-native/result.json',
             'core-native/result.json','c4-native/result.json','restore-model/result.json','shim-native/result.json')
    extra = [HOST,*[RETIREMENT/name for name in ('verified-retirement-manifest.json','build-admission.json')],
             REFERENCE/'display-dma-preflight.json',REFERENCE/'scanout-comparison-0380-0381-control.json',
             WORK/'research/tmp/frame-381-backing-host/result.json']
    return shared.pins(base=BASE,prior=P381,doc=DOC,patch=PATCH,reference=REFERENCE,trial=TRIAL,
                       extra=extra,artifacts=[BASE/name for name in names])


def freeze():
    return shared.freeze(base=BASE,prior=P381,expected=expected_plan,validate=criteria,storage_bound=storage,
                         pin_inputs=pins,reserve=RESERVE)


def review():
    return shared.review(base=BASE,doc=DOC,expected=expected_plan,validate=criteria,storage_bound=storage,
                         preparer=Path(__file__),reserve=RESERVE)


if __name__=='__main__':
    steps = {fn.__name__:fn for fn in (package,capture,delta,model,freeze,review)}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step',choices=steps)
    print(json.dumps(steps[parser.parse_args().step](),indent=2))
