#!/usr/bin/env python3
"""Prepare a reversible MAP324 descriptor-only fast path on the pinned 0316 source union."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
STATE = WORK/'research/tmp/map-query-324'
PARENT = MAIN/'research/tmp/gauguin-receiver-sample-worktree-20261115/research/tmp/receiver-sample-316/local-link/build-manifest.json'
CHANGED = ('bsd/dev/gauguin_gpu_runtime.h', 'bsd/dev/gauguin_gmu_board.c', 'iokit/Kernel/arm/GauguinGPU.cpp')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def instrument(name, raw):
    original, edits = raw, []

    def edit(before, after):
        nonlocal raw
        assert raw.count(before) == 1, (name, before)
        raw = raw.replace(before, after)
        edits.append((before, after))

    if name.endswith('gauguin_gpu_runtime.h'):
        anchor = 'bool sweet_gpu_runtime_ready(void);\n'
        edit(anchor, anchor + '/* CPU metadata only, under the existing GPU lock; never a completion proof. */\n'
             'bool sweet_gpu_runtime_pending_metadata(uint32_t native_fence);\n')
    elif name.endswith('gauguin_gmu_board.c'):
        anchor = 'bool sweet_gpu_runtime_ready(void)\n'
        edit(anchor, '''/* A descriptor for an unrelated ordinary BO does not access the GPU or
 * its page tables. Admit only the exact live pending software state; any
 * ambiguity falls back to the original wait/health path in the user client. */
bool sweet_gpu_runtime_pending_metadata(uint32_t native_fence)
{
    if(!ggrb_started||!ggrb_service||!ggrb_root||ggrb_live_sample.reason||
       ggrb_context.state!=GGR_BUSY||ggrb_context.last_error!=GGR_OK||
       !native_fence||ggrb_context.completed==UINT32_MAX||
       ggrb_context.submitted!=ggrb_context.completed+1||
       native_fence!=ggrb_context.submitted||ggrb_context.pending_wptr>=8192||
       !ggrb_context.pending_deadline_ns||!ggrb_context.ops.nanoseconds)return false;
    uint64_t now=ggrb_context.ops.nanoseconds(ggrb_context.ops.cookie);
    return now&&now<ggrb_context.pending_deadline_ns&&now<ggrb_end;
}
''' + anchor)
    else:
        edit('static IOLock *gLock;\n', '''static IOLock *gLock;
static bool gMapUnrelated;
/* Protected by gLock; counts only the same completed profiling prefix. */
static struct {uint64_t calls,fast,waited,failures;bool overflow;} gMapStats;
''')
        anchor = '    gMetalBootstrapMode=sweet_metal_desktop_enabled();\n'
        edit(anchor, anchor + '    int mapRequested=0;PE_parse_boot_argn("sweetgpumap",&mapRequested,sizeof(mapRequested));\n'
             '    gMapUnrelated=mapRequested==1;\n')
        anchor = '    s->release();gPublished=started;\n'
        edit(anchor, anchor + '    IOLog("SWEET GPU MAP324: enabled=%u service=%u ordinary-unsubmitted-owner-only\\n",gMapUnrelated?1u:0u,started?1u:0u);\n')
        start = raw.index('IOReturn GauguinGPUUserClient::clientMemoryForType(')
        end = raw.index('\nIOReturn GauguinGPUUserClient::surface(', start)
        before = raw[start:end]
        after = before.replace('    if(b&&fPendingCount&&finishPending(true,true)!=kIOReturnSuccess)b=nullptr;\n', '''    const bool fast=gMapUnrelated&&fCompositor&&fAsync&&b&&b->memory&&
        !b->surface&&!b->pending&&!b->closePending&&
        OSDynamicCast(IOBufferMemoryDescriptor,b->memory)!=nullptr&&
        fPendingCount&&fPendingCount<=GGR_MAX_BUFFERS&&fPendingQueue&&fPendingNativeFence&&fPendingQueueFence&&
        fPendingQueue->issued==fPendingQueueFence&&fPendingQueue->completed!=UINT32_MAX&&
        fPendingQueueFence==fPendingQueue->completed+1&&
        sweet_gpu_runtime_pending_metadata(fPendingNativeFence);
    bool waited=false;
    if(b&&fPendingCount&&!fast){
        waited=true;
        if(finishPending(true,true)!=kIOReturnSuccess)b=nullptr;
    }
''')
        assert after != before
        after = after.replace('&&sweet_gpu_runtime_ready()) {', '&&(fast||sweet_gpu_runtime_ready())) {')
        anchor = '    gapi_end(profile,r);IOLockUnlock(gLock);IOLockUnlock(gRequests);return r;'
        assert after.count(anchor) == 1
        after = after.replace(anchor, '''    if(profile&&!gapi_frozen){
        if(gMapStats.calls==UINT64_MAX)gMapStats.overflow=true;
        else {++gMapStats.calls;gMapStats.fast+=fast&&r==kIOReturnSuccess;
              gMapStats.waited+=waited;gMapStats.failures+=r!=kIOReturnSuccess;}
    }
''' + anchor)
        edit(before, after)
        anchor = '''}

/* Only a serialized request can wait. Display may poll/complete the escrow'''
        edit(anchor, '''    snprintf(line,sizeof(line),"SWEET GPU MAP324: calls=%llu fast=%llu waited=%llu failures=%llu valid=%u; descriptor-only",
        (unsigned long long)gMapStats.calls,(unsigned long long)gMapStats.fast,
        (unsigned long long)gMapStats.waited,(unsigned long long)gMapStats.failures,
        !gMapStats.overflow&&gapi_valid?1u:0u);record(line);
}

/* Only a serialized request can wait. Display may poll/complete the escrow''')
    undone = raw
    for before, after in reversed(edits):
        assert undone.count(after) == 1
        undone = undone.replace(after, before)
    assert undone == original
    return raw


def main():
    parent = json.loads(PARENT.read_text())
    assert parent['state'] == 'linked-from-verified-0301-objects' and parent['inputs_unchanged']
    source = Path(parent['source_union']['base'])
    out = STATE/'kernel-source'
    assert not out.exists()
    budget = json.loads((STATE/'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes'] == 700000000
    patch = ''
    pins = {}
    for name in CHANGED:
        old = source/name
        assert sha(old) == parent['input_pins'][str(old)]['sha256']
        raw = old.read_text()
        modified = instrument(name, raw)
        p = out/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(modified)
        patch += ''.join(difflib.unified_diff(raw.splitlines(True), modified.splitlines(True), fromfile='a/'+name, tofile='b/'+name))
        pins[str(old)] = sha(old)
    # Preserve the 0316 sampler and the current private quoted-header context.
    overlay = Path(parent['source_union']['overlay'])
    for p in overlay.rglob('*'):
        if p.is_file():
            dest = out/p.relative_to(overlay)
            assert not dest.exists()
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dest)
            pins[str(p)] = sha(p)
    support = [p.relative_to(source) for p in (source/'bsd/dev').glob('gauguin_*.h')]
    support += [Path(p) for p in ('iokit/Kernel/arm/SweetSurface.h','iokit/Kernel/arm/SweetMetalBootstrap.h','bsd/kern/sweet_eagl_diagnostics.h')]
    for name in support:
        p = source/name
        if (out/name).exists():continue
        assert sha(p) == parent['input_pins'][str(p)]['sha256']
        (out/name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, out/name)
        pins[str(p)] = sha(p)
    patch_path = WORK/'xnu/patches/0238-gauguin-unrelated-map-descriptor.patch'
    assert not patch_path.exists()
    patch_path.write_text(patch)
    result = dict(state='prepared-MAP324-source-only', parent_manifest_sha256=sha(PARENT),
        changed_files=list(CHANGED), source=str(out), patch=str(patch_path), patch_sha256=sha(patch_path),
        source_change_reversible=True, input_pins=pins, new_GPU_commands=0, new_threads=0, device_commands=0)
    (STATE/'source-preparation.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))


if __name__ == '__main__':main()
