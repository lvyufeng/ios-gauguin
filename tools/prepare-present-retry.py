#!/usr/bin/env python3
"""Prepare bounded retry of a held frame whose GPU read is not ready."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

WORK = Path(__file__).resolve().parents[1]
MAIN = Path('/Users/baai/Project/ios-gauguin')
PARENT = MAIN / 'research/tmp/gauguin-key-perf565-worktree-20261116/research/tmp/key-perf565-331'
STATE = WORK / 'research/tmp/present-retry-332'
REL = Path('iokit/Kernel/arm/SweetFramebuffer.cpp')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def replace_once(source, old, new):
    assert source.count(old) == 1, old
    return source.replace(old, new)


def transform(source):
    source = replace_once(source, '    IOMobileFramebufferUserClient *owner;\n};',
        '    IOMobileFramebufferUserClient *owner;\n'
        '    uint64_t retryEpoch;\n    uint32_t retries;\n};')
    source = replace_once(source, '    void finishHeldFrame(struct sweet_fb_frame *frame);',
        '    uint64_t fHeldRetryEpoch, fHeldRequeued;\n'
        '    uint64_t fHeldRetrySuperseded, fHeldRetryCanceled, fHeldRetryExhausted;\n'
        '    void invalidateHeldRetryLocked(void); /* fLock held */\n'
        '    void finishHeldFrame(struct sweet_fb_frame *frame, bool retry = false);')
    source = replace_once(source, '\tvoid present(const uint8_t *rec, SweetSurface *const *held = NULL);',
        '\tbool present(const uint8_t *rec, SweetSurface *const *held = NULL);')
    source = replace_once(source, '    bzero(&fHeldPending, sizeof(fHeldPending));',
        '    bzero(&fHeldPending, sizeof(fHeldPending));\n'
        '    fHeldRetryEpoch = 1;\n'
        '    fHeldRequeued = fHeldRetrySuperseded = fHeldRetryCanceled = fHeldRetryExhausted = 0;')
    source = replace_once(source,
        '    if (fHoldPresent) IOLog("SWEET FB HOLD: enabled pending=1 active=1; original surfaces, prompt retirement\\n");',
        '    if (fHoldPresent) {\n'
        '        IOLog("SWEET FB HOLD: enabled pending=1 active=1; original surfaces, prompt retirement\\n");\n'
        '        IOLog("SWEET FB RETRY332: enabled max_retries=8; GPU read guards retained\\n");\n    }')
    source = replace_once(source, '        fb->present(rec, fb->fHoldPresent ? frame.surfaces : NULL);',
        '        bool ready = fb->present(rec, fb->fHoldPresent ? frame.surfaces : NULL);')
    source = replace_once(source, '        if (fb->fHoldPresent) fb->finishHeldFrame(&frame);',
        '        if (fb->fHoldPresent) fb->finishHeldFrame(&frame, !ready);')
    source = replace_once(source,
        '            fb->fHeldCanceled, fb->fHeldRejected, fb->fHeldPending.owner != NULL, fb->fHeldActive);',
        '            fb->fHeldCanceled, fb->fHeldRejected, fb->fHeldPending.owner != NULL, fb->fHeldActive);\n'
        '        IOLog("SWEET FB RETRY332: requeued=%llu newer=%llu canceled=%llu exhausted=%llu; max_retries=8\\n",\n'
        '            fb->fHeldRequeued, fb->fHeldRetrySuperseded, fb->fHeldRetryCanceled, fb->fHeldRetryExhausted);')
    source = replace_once(source, '    if (i != (unsigned int)-1) fClients->removeObject(i);',
        '    if (i != (unsigned int)-1) {\n'
        '        invalidateHeldRetryLocked();\n        fClients->removeObject(i);\n    }')
    old = '''void
AppleCLCD::finishHeldFrame(struct sweet_fb_frame *frame)
{
    bool consumed = frame->owner != NULL;
    sweet_fb_frame_release(frame);  /* after GPURead and the copy, before another frame */
    if (consumed) {
        IOLockLock(fLock);
        fHeldActive = false;
        fHeldRetired++;
        IOLockUnlock(fLock);
    }
}'''
    new = '''void
AppleCLCD::invalidateHeldRetryLocked(void)
{
    /* Zero permanently disables retry after epoch exhaustion. A closed owner
     * must not be revived if a later client reuses the same pointer value. */
    if (fHeldRetryEpoch == UINT64_MAX) fHeldRetryEpoch = 0;
    else if (fHeldRetryEpoch != 0) ++fHeldRetryEpoch;
}

void
AppleCLCD::finishHeldFrame(struct sweet_fb_frame *frame, bool retry)
{
    if (frame->owner == NULL) return;
    bool requeued = false;
    IOLockLock(fLock);
    if (retry) {
        if (!fHoldPresent || !fHeldActive || fPowerOff || fHeldRetryEpoch == 0 ||
            frame->retryEpoch != fHeldRetryEpoch ||
            fClients->getNextIndexOfObject(frame->owner, 0) == (unsigned int)-1) {
            ++fHeldRetryCanceled;
        } else if (fHeldPending.owner != NULL) {
            ++fHeldRetrySuperseded; /* a newer accepted swap wins */
        } else if (frame->retries >= 8) {
            ++fHeldRetryExhausted;
        } else {
            ++frame->retries;
            sweet_fb_frame_move(&fHeldPending, frame);
            fDirty = true;
            fHeldActive = false;
            ++fHeldRequeued;
            requeued = true;
        }
    }
    IOLockUnlock(fLock);
    if (requeued) return; /* retained surfaces moved; no reference was dropped */
    sweet_fb_frame_release(frame); /* after GPURead, outside framebuffer lock */
    IOLockLock(fLock);
    fHeldActive = false;
    ++fHeldRetired;
    IOLockUnlock(fLock);
}'''
    source = replace_once(source, old, new)
    source = replace_once(source, '        if (fPowerOff) {\n            cancelHeldFrameLocked',
        '        next.retryEpoch = fHeldRetryEpoch;\n'
        '        if (fPowerOff) {\n            cancelHeldFrameLocked')
    source = replace_once(source,
        'void\nAppleCLCD::present(const uint8_t *rec, SweetSurface *const *held)\n{\n    (void)held;',
        'bool\nAppleCLCD::present(const uint8_t *rec, SweetSurface *const *held)\n{\n'
        '    (void)held;\n    bool ready = true;')
    source = replace_once(source, 'if(!gpuRead.valid()){s->release();continue;}',
        'if(!gpuRead.valid()){ready=false;s->release();continue;}')
    source = replace_once(source,
        '    sweet_ui_trace_record(GUT_PRESENT_END,get32(rec,0x50),0,0,mask,0,0);\n#endif\n}',
        '    sweet_ui_trace_record(GUT_PRESENT_END,get32(rec,0x50),0,ready ? 0 : 1,mask,0,0);\n#endif\n'
        '    return ready;\n}')
    source = replace_once(source, '\t\t\t\tfFB->fPowerOff = off;\n',
        '\t\t\t\tfFB->fPowerOff = off;\n#if defined(GAUGUIN)\n'
        '                if (off) fFB->invalidateHeldRetryLocked();\n#endif\n')
    return source


def main():
    admission = json.loads((STATE / 'storage-whole-batch-admission.json').read_text())
    assert admission['admitted'] and admission['planned_batch_bytes'] == 800000000
    assert sha(PARENT / 'ready.json') == 'c6631696dc51c5362d715bf2c2dae4931923a8dc753d16f4154c90b72ebb5b1f'
    ready = json.loads((PARENT / 'ready.json').read_text())
    manifest_path = PARENT / 'local-link/build-manifest.json'
    assert sha(manifest_path) == ready['input_pins'][str(manifest_path)]
    manifest = json.loads(manifest_path.read_text())
    base = Path(manifest['source_union']['base'])
    overlay = Path(manifest['source_union']['overlay'])
    before_path = base / REL
    assert sha(before_path) == '645a49780f6aced1721216e7c041e76a62c2aa3c4cf4445dba50160af02cde4f'
    assert not (overlay / REL).exists()
    out = STATE / 'kernel-source'
    assert not out.exists()
    before = before_path.read_text()
    after = transform(before)
    support_headers = [base / 'iokit/Kernel/arm' / name for name in ('SweetPresentClock.h', 'SweetPresentStats.h')]
    inputs = [Path(__file__), PARENT / 'ready.json', manifest_path, before_path,
              STATE / 'storage-whole-batch-admission.json',
              *support_headers, *[p for p in overlay.rglob('*') if p.is_file()]]
    pins = {str(p.resolve()): sha(p) for p in inputs}
    shutil.copytree(overlay, out)
    for header in support_headers:
        shutil.copy2(header, out / header.relative_to(base))
    (out / REL).write_text(after)
    patch = WORK / 'xnu/patches/0245-gauguin-pending-present-retry.patch'
    assert not patch.exists()
    patch.write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                               fromfile='a/' + str(REL), tofile='b/' + str(REL))))
    series = WORK / 'xnu/patches/series'
    assert series.read_text().rstrip().endswith('0244-gauguin-native565-dcvs-profile.patch')
    series.write_text(series.read_text().rstrip() + '\n' + patch.name + '\n')
    assert all(sha(p) == h for p, h in pins.items())
    result = dict(state='prepared-PRESENT332-bounded-held-frame-retry', source=str(out),
        parent_manifest_sha256=sha(manifest_path), changed_files=[str(REL)],
        source_change_reversible=True, patch=str(patch), patch_sha256=sha(patch),
        maximum_additional_present_attempts_per_frame=8, additional_threads=0,
        additional_GPU_submissions=0, existing_GPU_read_guards_retained=True,
        newer_pending_preferred=True, owner_and_power_epoch_checked=True,
        input_pins=pins, device_commands=0, physical_FPS_qualified=False)
    with (STATE / 'source-preparation.json').open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'input_pins'}, indent=2))


if __name__ == '__main__':
    main()
