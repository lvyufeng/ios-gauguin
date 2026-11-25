#!/usr/bin/env python3
"""Stage the exact in-render producer transport and pre-issue display binding."""

from difflib import unified_diff
from importlib import import_module
import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

callback = import_module('check-frame401-callback')
BASE = callback.BASE
ROOT = callback.ROOT
P400 = MAIN/'research/tmp/gauguin-frame400-staged-blank-worktree-20261123/research/tmp/frame-400'
CONTROL = P400/'native-kernel/build-manifest.json'
DEVELOPMENT = BASE/'producer-native-development-admission.json'
ELIGIBILITY = BASE/'pre-issue-eligibility.json'
GPU = Path('iokit/Kernel/arm/GauguinGPU.cpp')
FRAMEBUFFER = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')
KDEBUG = Path('bsd/kern/kdebug.c')
HEADERS = callback.NAMES | {
    'DisplayWriter401.h':'gauguin_display_writer401.h',
    'ProducerTransport401.h':'gauguin_producer_transport401.h',
}


def replace(text, before, after):
    require(text.count(before)==1,'0401 source anchor differs: '+before.splitlines()[0])
    return text.replace(before,after,1)


def gpu_transport(source):
    site = 'extern "C" uint32_t GauguinGPUSurfaceState(SweetSurface *s)'
    source = replace(source,site,'''extern "C" uint32_t sweet_ca401_declare_target(task_t, uint64_t, uint64_t, uint32_t);
extern "C" uint32_t sweet_ca401_writer_target(task_t, uint32_t);
extern "C" bool sweet_fb401_publish_writer(uint32_t, uint32_t, uint32_t, uint64_t);
extern "C" uint64_t sweet_fb401_seal_writer(uint32_t, uint32_t, uint32_t);
#include "../../../bsd/dev/gauguin_producer_transport401.h"

'''+site)
    method = 'IOReturn GauguinGPUUserClient::externalMethod(uint32_t selector,IOExternalMethodArguments *a,'
    head = source.index(method)
    entry = source.index('{',head) + 1
    source = source[:entry]+'''
    // Scope query only. It cannot drain the pending GPU or alter BO ownership.
    if (selector == GGR_DISPLAY_PRODUCER401) {
        if (!fCompositor || !fAsync || fTask != current_task()) return kIOReturnUnsupported;
        ggr_display_producer401 request{};
        if (!a || !a->structureInput || !a->structureOutput ||
            a->structureInputSize != sizeof(request) || a->structureOutputSize != sizeof(request) ||
            a->scalarInputCount || a->scalarOutputCount ||
            a->structureInputDescriptor || a->structureOutputDescriptor) return kIOReturnBadArgument;
        memcpy(&request, a->structureInput, sizeof(request));
        if (!request.object || !request.created_tick || !request.surface || request.cookie)
            return kIOReturnBadArgument;
        request.cookie = sweet_ca401_declare_target(fTask, request.object, request.created_tick, request.surface);
        memcpy(a->structureOutput, &request, sizeof(request));
        a->structureOutputSize = sizeof(request);
        return kIOReturnSuccess;
    }'''+source[entry:]
    source = replace(source,'r->nr_out_syncobjs||r->syncobj_stride||r->pad||r->fence_fd!=-1||',
        'r->nr_out_syncobjs||r->syncobj_stride||(r->pad&&(!fCompositor||!fAsync))||r->fence_fd!=-1||')
    site = '    auto bos=IONew(struct ggr_submit_bo,r->nr_bos);'
    source = replace(source,site,'''    const uint32_t producerCookie = r->pad;
    r->pad = 0;
    uint32_t producerSurface = producerCookie ? sweet_ca401_writer_target(fTask, producerCookie) : 0;
    uint32_t producerVersion = 0;
'''+site)
    site = '        const uint64_t displayTicket = fAsync ? sweet_fb352_waiting_ticket() : 0;'
    source = replace(source,site,'''        if (producerSurface) {
            unsigned surfaceWrites = 0;
            for (uint32_t i = 0; i < r->nr_bos; ++i)
                if (resolved[i]->surface && (bos[i].flags & 2u)) ++surfaceWrites;
            if (surfaceWrites != 1) producerSurface = 0;
        }
'''+site)
    site = '                flush_dcache64(b->surface->kernelAddress(),(unsigned)b->size,0);'
    source = replace(source,site,'''                if (writer && producerSurface == b->surface->id && !fPendingDisplayTicket) {
                    const uint32_t version = GauguinGPUSurfaceState(b->surface) & SCAN354_GPU_VERSION;
                    if (sweet_fb401_publish_writer(producerCookie, producerSurface, version, fPendingDisplayTicket))
                        producerVersion = version;
                }
'''+site)
    site = '        const uint32_t previousSurface = fAsync && !fPendingDisplayTicket ? sweet_fb391_previous_surface() : 0;'
    source = replace(source,site,'''        if (producerVersion) {
            // Close publication before the doorbell. A claimed ticket then
            // follows the existing issue, completion and cancellation path.
            fPendingDisplayTicket = sweet_fb401_seal_writer(producerCookie, producerSurface, producerVersion);
            if (fPendingDisplayTicket) fPendingDisplayVersion = producerVersion;
        }
'''+site)
    return source


def display_binding(source):
    site = 'extern "C" uint32_t GauguinGPUSurfaceState(SweetSurface *);'
    source = replace(source,site,site+'''
extern "C" uint32_t sweet_ca401_swap_cookie(uint32_t);
#include "../../../bsd/dev/gauguin_display_writer401.h"''')
    site = '    uint64_t watchPendingReadyLocked();'
    source = replace(source,site,site+'''
    bool bindBusyProducer401Locked(uint32_t cookie, uint32_t observed, uint32_t swapID,
        uint32_t mask, uint64_t &packedSurface);''')
    site = 'static AppleCLCD *gReadyDisplay;                             /* gReadyLock */'
    source = replace(source,site,site+'''
static display401_writer gBusyDisplayWriter401;               /* gReadyLock */

extern "C" bool
sweet_fb401_publish_writer(uint32_t cookie, uint32_t surface, uint32_t version, uint64_t existing)
{
    if (!cookie || !__atomic_load_n(&gReadyRetainsIssued, __ATOMIC_ACQUIRE)) return false;
    IOLock *lock = __atomic_load_n(&gReadyLock, __ATOMIC_ACQUIRE);
    if (!lock) return false;
    IOLockLock(lock);
    const bool published = gReadySource && sweet_frame351_window() &&
        display401_publish(&gBusyDisplayWriter401, cookie, surface, version, existing);
    IOLockUnlock(lock);
    return published;
}

extern "C" uint64_t
sweet_fb401_seal_writer(uint32_t cookie, uint32_t surface, uint32_t version)
{
    IOLock *lock = __atomic_load_n(&gReadyLock, __ATOMIC_ACQUIRE);
    if (!lock) return 0;
    IOLockLock(lock);
    const uint64_t ticket = display401_seal(&gBusyDisplayWriter401, cookie, surface, version);
    IOLockUnlock(lock);
    return ticket;
}
''')
    site = 'uint64_t\nAppleCLCD::watchPendingReadyLocked()'
    source = replace(source,site,'''bool
AppleCLCD::bindBusyProducer401Locked(uint32_t cookie, uint32_t observed, uint32_t swapID,
    uint32_t mask, uint64_t &packedSurface)
{
    if (!fReadyEvent || !waitingForReadyLocked() || !stage384EnabledLocked()) return false;
    auto *surface = fHeldPending.surfaces[0];
    const uint32_t version = observed & SCAN354_GPU_VERSION;
    const uint64_t ticket = pendingTicketLocked();
    IOLock *lock = __atomic_load_n(&gReadyLock, __ATOMIC_ACQUIRE);
    IOLockLock(lock);
    const bool exact = gReadySource && sweet_frame351_window() && GauguinGPUSurfaceState(surface) == observed &&
        display401_matches(&gBusyDisplayWriter401, cookie, surface->id, version) &&
        scan357_claim(gReadyWriters, ticket, version, version);
    if (exact) {
        const bool claimed = display401_claim(&gBusyDisplayWriter401, cookie, ticket, version);
        assert(claimed);
        (void)claimed;
        fHeldPending.surfaceVersion = version;
        packedSurface = (uint64_t)version << 32 | surface->id;
        fReadyGeneration = fHeldPending.generation;
        gReadyVersion = version;
        __atomic_store_n(&gReadyTicket, ticket, __ATOMIC_RELEASE);
        sweet_frame344_record(F344_SWAP, fHeldSubmitted, 0, swapID, mask, packedSurface);
        sweet_frame344_record(F357_BOUND, ticket >> 32, 2, ticket, version, cookie);
    }
    IOLockUnlock(lock);
    return exact;
}

'''+site)
    site = '        uint32_t observedSurfaceState = 0;\n        bool advancedPastPending = false;'
    source = replace(source,site,site+'\n        uint32_t producerCookie = 0;')
    site = '            surface = ((uint64_t)next.surfaceVersion << 32) | next.surfaces[0]->id;'
    source = replace(source,site,site+'''
            if (!fPowerOff && !advancedPastPending && (observedSurfaceState & SCAN354_GPU_STATUS) == 1 &&
                stage384EnabledLocked())
                producerCookie = sweet_ca401_swap_cookie(next.surfaces[0]->id);''')
    site = '        sweet_frame344_record(F344_SWAP,fHeldSubmitted,fPowerOff,swapID,get32(rec,0x104),surface);'
    source = replace(source,site,'''        const bool exactProducer = producerCookie &&
            bindBusyProducer401Locked(producerCookie, observedSurfaceState, swapID, get32(rec,0x104), surface);
        if (!exactProducer)
            sweet_frame344_record(F344_SWAP, fHeldSubmitted, fPowerOff, swapID, get32(rec,0x104), surface);''')
    site = '        watchPendingReadyLocked();\n    } else\n#endif\n    {\n        memcpy(fPending, rec, SWEET_FB_SWAP_REC_SIZE);'
    return replace(source,site,site.replace('watchPendingReadyLocked();','if (!exactProducer) watchPendingReadyLocked();'))


def core_binding(source):
    site = '#include "hakios-metal/texture.hpp"'
    source = replace(source,site,site+'''
#include "ProducerTransport401.h"

namespace hakios::metal {
extern thread_local uint32_t displayProducer401;
}

namespace {
class ScopedProducer401 {
public:
    explicit ScopedProducer401(uint32_t cookie) : previous_(hakios::metal::displayProducer401) {
        hakios::metal::displayProducer401 = cookie;
    }
    ~ScopedProducer401() { hakios::metal::displayProducer401 = previous_; }
    ScopedProducer401(const ScopedProducer401&) = delete;
    ScopedProducer401& operator=(const ScopedProducer401&) = delete;

private:
    const uint32_t previous_;
};
}
''')
    site = '    gauguin342::Trace trace342;'
    source = replace(source,site,site+'\n    std::atomic<uint32_t> displayProducer401{0};')
    site = 'void hakios_metal_cb_commit(hakios_metal_cb* cb, void (*callback)(hakios_metal_cb*, void*), void* context) {'
    source = replace(source,site,'''void hakios_metal_cb_bind_display_producer401(hakios_metal_cb* cb, uint64_t object,
    uint64_t createdTick, uint32_t surface)
{
    CbLease invocation(cb);
    if (!cb || !object || !createdTick || !surface || !cb->control || !cb->control->storage) return;
    ggr_display_producer401 request{object, createdTick, surface, 0};
    auto& transport = cb->control->storage->gpu->transport();
    if (transport.call(GGR_DISPLAY_PRODUCER401, &request, sizeof(request)) == 0 &&
        request.object == object && request.created_tick == createdTick && request.surface == surface) {
        cb->displayProducer401.store(request.cookie, std::memory_order_release);
    }
}

'''+site)
    site = '    gauguin342::SubmitScope submitScope339(cb->trace342);'
    return replace(source,site,site+'''
    ScopedProducer401 producer(cb->displayProducer401.exchange(0, std::memory_order_acq_rel));''')


def submit_binding(source):
    site = 'namespace hakios::metal {'
    source = replace(source,site,site+'\n\nthread_local uint32_t displayProducer401;')
    site = '    s.queueid = queue;'
    return replace(source,site,site+'\n    s.pad = displayProducer401;')


def frontend_binding(source):
    site = '#include "hakios-metal/hakios_metal.h"'
    source = replace(source,site,site+'''
extern void hakios_metal_cb_bind_display_producer401(hakios_metal_cb *, uint64_t, uint64_t, uint32_t);''')
    site = '@interface HakiosMetalCommandBuffer : _MTLCommandBuffer {'
    source = replace(source,site,site+'''
@private
    uint64_t _createdTick401;
    uint64_t _displayTarget401;
@protected''')
    site = '\t_createdAt = hm_now();'
    source = replace(source,site,site+'''
    if (gauguin_async338_scope(_createdAt)) _createdTick401 = mach_absolute_time();''')
    site = '- (id)renderCommandEncoderWithDescriptor:(MTLRenderPassDescriptor *)descriptor\n{'
    source = replace(source,site,'''- (void)hakiosCaptureDisplayTarget401:(HakiosMetalTexture *)texture
{
    if (!texture || !gauguin_async338_scope(_createdAt) ||
        [texture hakiosIsTurned] || [texture hakiosIsShadow]) return;
    IOSurfaceRef backing = [texture iosurface];
    const uint32_t surface = backing ? IOSurfaceGetID(backing) : 0;
    if (!surface) return;
    uint64_t expected = 0;
    if (!__atomic_compare_exchange_n(&_displayTarget401, &expected, surface, false,
            __ATOMIC_RELEASE, __ATOMIC_RELAXED) && expected != surface) {
        __atomic_store_n(&_displayTarget401, UINT64_MAX, __ATOMIC_RELEASE);
    }
}

'''+site)
    site = '\t\t[encoder hakiosTakeResolves:descriptor];   /* hm_read_render_pass judged them */\n\t\treturn encoder;'
    source = replace(source,site,site.replace('\t\treturn encoder;',
        '        if (encoder) [self hakiosCaptureDisplayTarget401:texture];\n\t\treturn encoder;'))
    site = ('\treturn [[[HakiosMetalParallelRenderCommandEncoder alloc] initWithHakiosCommandBuffer:self pass:&pass '
           'colorTexture:texture\n\t\t\t\t\t\t\t\t\t\t\tdescriptor:descriptor] autorelease];')
    source = replace(source,site,site.replace('\treturn [[[', '\tHakiosMetalParallelRenderCommandEncoder *encoder = [[[')
        +'\n    if (encoder) [self hakiosCaptureDisplayTarget401:texture];\n    return encoder;')
    site = '\t\tgauguin_c4_queue_trace(0, self, _createdAt, _committedAt, 0);'
    return replace(source,site,site+'''
        const uint64_t displayTarget = __atomic_load_n(&_displayTarget401, __ATOMIC_ACQUIRE);
        if (displayTarget && displayTarget <= UINT32_MAX)
            hakios_metal_cb_bind_display_producer401(_cb, (uintptr_t)self, _createdTick401, (uint32_t)displayTarget);''')


def stage():
    source = Path(load(CONTROL)['source'])
    overlay = BASE/'producer401-native.patch'
    diffs = []
    for path,change in ((GPU,gpu_transport),(FRAMEBUFFER,display_binding),(KDEBUG,callback.patch_kdebug)):
        before = (source/path).read_text()
        diffs.extend(unified_diff(before.splitlines(keepends=True),change(before).splitlines(keepends=True),
            'a/'+str(path),'b/'+str(path)))
    for file, mapped in HEADERS.items():
        diffs.extend(unified_diff([], (ROOT/file).read_text().splitlines(keepends=True),
            '/dev/null','b/bsd/dev/'+mapped))
    overlay.write_text(''.join(diffs))
    return overlay


def admit():
    receipt = load(DEVELOPMENT)
    require(receipt['admitted'] and receipt['planned_batch_bytes']>=306_000_000 and
        receipt['current_accounted_bytes']+receipt['planned_batch_bytes']<=receipt['limit_bytes'],
        '0401 native and signed userspace batch with the running trial reserve exceeds storage')
    evidence = load(ELIGIBILITY)
    require(evidence['single_native_display_writer_in_flush_phase']==5 and evidence['trial']=='0399' and
        all(sha(path)==digest for path,digest in evidence['input_pins'].items()),
        '0401 same-render, pre-issue cohort differs')


def native():
    admit()
    callback.inspect_native_sites()
    with TemporaryDirectory(prefix='401-host-',dir=BASE) as folder:
        for test in ('render_producer','display_writer'):
            fixture = WORK/'tests/fixtures'/f'frame401_{test}.c'
            binary = str(Path(folder)/test)
            subprocess.run(['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                '-fno-sanitize-recover=all','-I'+str(ROOT),str(fixture),'-o',binary],check=True,timeout=45)
            subprocess.run([binary],check=True,timeout=15)
    latest = import_module('check-frame400').baseline.P398/'native-kernel/build-manifest.json'
    patch = stage()
    out = BASE/'native-kernel'
    units = (('GauguinGPU',latest,'compile-GauguinGPU'),
        ('SweetFramebuffer',CONTROL,'compile-SweetFramebuffer'),
        ('kdebug',callback.CONTROL,'compile-kdebug'))
    import_module('build-frame347').link_scanout(CONTROL,out,parent_trial='0400',trial='0401',
        patches=(patch,),extra_units=units,recompile_scanout=False,
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    built = load(out/'build-manifest.json')
    require(built['inputs_unchanged'] and built['baseline_reproduced_except_uuid'] and
        {Path(p).stem for p in built['object_replacements'].values()}=={unit[0] for unit in units},
        '0401 linked objects differ from the reviewed render scope')
    return dict(kernel=built['kernel_sha256'],identity=built['identity'],device_commands=0,
        input_pins={str(p):sha(p) for p in (CONTROL,ELIGIBILITY,Path(__file__),DEVELOPMENT,
            *(ROOT/name for name in HEADERS))})


def qualify():
    admit()
    callback.inspect_native_sites()
    path = BASE/'native-kernel/build-manifest.json'
    built = load(path)
    baseline = Path(load(CONTROL)['source'])
    linked = Path(built['source'])
    overlay = BASE/'producer401-native.patch'
    require(built['inputs_unchanged'] and built['baseline_reproduced_except_uuid'] and
        {Path(p).stem for p in built['object_replacements'].values()}==
            {'GauguinGPU','SweetFramebuffer','kdebug'} and
        built['input_pins'][str(overlay)]==sha(overlay) and sha(built['kernel'])==built['kernel_sha256'],
        '0401 exact native build differs')
    for unit,transform in ((GPU,gpu_transport),(FRAMEBUFFER,display_binding),(KDEBUG,callback.patch_kdebug)):
        require((linked/unit).read_text()==transform((baseline/unit).read_text()),
            '0401 linked source differs: '+str(unit))
    for original,mapped in HEADERS.items():
        require((linked/'bsd/dev'/mapped).read_bytes()==(ROOT/original).read_bytes(),
            '0401 linked protocol layout differs: '+mapped)
    return dict(state='0401-exact-producer-build-verified',device_commands=0,pre_issue_exact_cases=5,
        patch_sha256=sha(overlay),input_pins={str(p):sha(p) for p in (
            path,overlay,CONTROL,ELIGIBILITY,Path(__file__),DEVELOPMENT,
            *(ROOT/name for name in HEADERS))})


if __name__=='__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=('stage','native','qualify'),default='stage',nargs='?')
    step = cli.parse_args().step
    print(stage() if step=='stage' else json.dumps(globals()[step](),indent=2))
