"""Exact reversible additions to the pinned SURF334 C API and Q337 frontend."""
HEADER='include/hakios-metal/hakios_metal.h'
SOURCE='src/c_api.cpp'


def core(raw,name):
    edits=[]
    def replace(old,new):
        nonlocal raw
        assert raw.count(old)==1,(name,old)
        raw=raw.replace(old,new);edits.append((old,new))
    if name==HEADER:
        at='enum hakios_metal_status hakios_metal_cb_status(hakios_metal_cb *cb);'
        replace(at,at+'''
/* Observe existing deferred jobs. Set identity before encoding (ticket=0),
 * then assign the immutable admission ticket before posting commit. */
void hakios_metal_cb_trace338(hakios_metal_cb *cb, uintptr_t object,
                             uint64_t made_us, uint64_t queue, uint64_t ticket);
/* Same recorder FIFO, after already-posted commit/recording. Exactly one call
 * on normal return. Notification enqueue failure uses a synchronous drain;
 * it does not fail the recording or duplicate commit. Callback must not throw.
 * cb/context remain caller-owned until invocation; the job owns a C-handle
 * lease independently. The internal callback must return without waiting for
 * CB completion; frontend handlers are dispatched separately. This adds no
 * GPU submission or worker thread. */
void hakios_metal_cb_notify_recorded338(hakios_metal_cb *cb,
    void (*callback)(hakios_metal_cb *, void *), void *context);
''')
    elif name==SOURCE:
        replace('#include <atomic>','#include <atomic>\n#include "Recording338.hpp"')
        at='std::atomic<int>* pendingOf(hakios_metal_cb* cb);'
        replace(at,at+'''
void observedJob338(hakios_metal_cb*,unsigned,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,bool) noexcept;
''')
        replace('        std::function<void()> f;','''        std::function<void()> f;
        unsigned kind=0;
        uint64_t sequence=0, enqueued=0, busyPrefix=0;''')
        replace('        std::deque<Job> jobs;','''        std::deque<Job> jobs;
        uint64_t sequence=0;
        gauguin338::WorkMeter meter;''')
        replace('    void post(hakios_metal_cb* cb, std::function<void()> f) {',
                '    void post(hakios_metal_cb* cb, std::function<void()> f, unsigned kind=0, bool marksRecording=true) {')
        replace('        Job job{CbLease(cb), cb, pendingOf(cb), std::move(f)};',
                '        Job job{CbLease(cb), cb, pendingOf(cb), std::move(f)};\n        job.kind=kind;')
        replace('            state->jobs.push_back(std::move(job));','''            state->jobs.push_back(std::move(job));
            auto& admitted=state->jobs.back();
            admitted.sequence=++state->sequence;
            admitted.enqueued=gauguin338::nowNs();
            admitted.busyPrefix=state->meter.snapshot(admitted.enqueued);''')
        replace('''        } catch (...) {
            recordingFailed(cb);
            throw; // existing C++ allocation-failure contract
''','''        } catch (...) {
            if (marksRecording) recordingFailed(cb);
            throw; // existing C++ allocation-failure contract
''')
        replace('''            state->busy = true;
            g.unlock();
            try { job.f(); } catch (...) { recordingFailed(job.cb); }
            g.lock();
            job.pending->fetch_sub(1);''','''            state->busy = true;
            const uint64_t busyWait=state->meter.completed-job.busyPrefix;
            const uint64_t began=gauguin338::nowNs();
            state->meter.begin(began);
            g.unlock();
            bool failed=false;
            try { job.f(); } catch (...) { recordingFailed(job.cb);failed=true; }
            const uint64_t ended=gauguin338::nowNs();
            state->meter.finish(ended);
            observedJob338(job.cb,job.kind,job.sequence,job.enqueued,began,ended,busyWait,failed);
            g.lock();
            state->meter.retire(ended);
            job.pending->fetch_sub(1);''')
        replace('    std::atomic<int> pending{0};          // jobs posted for this buffer and not yet done',
                '    std::atomic<int> pending{0};          // jobs posted for this buffer and not yet done\n    gauguin338::Trace trace338;')
        at='void syncOne(hakios_metal_cb* cb) { if (cb->deferrer != nullptr) cb->deferrer->drain(&cb->pending); }'
        replace(at,at+'''
void observedJob338(hakios_metal_cb* cb,unsigned kind,uint64_t sequence,uint64_t enqueued,
                    uint64_t began,uint64_t ended,uint64_t busyWait,bool failed) noexcept {
    gauguin338::observe(cb->trace338,kind,sequence,enqueued,began,ended,busyWait,
                        unsigned(cb->cb->status()),failed);
}
''')
        at='if (deferring(cb)) return cb->deferrer->post(cb, [cb, callback, context] { hakios_metal_cb_commit(cb, callback, context); });'
        replace(at,at[:-2]+', 1);')
        at='enum hakios_metal_status hakios_metal_cb_status(hakios_metal_cb* cb) {'
        replace(at,'''void hakios_metal_cb_trace338(hakios_metal_cb* cb, uintptr_t object,
                             uint64_t made_us, uint64_t queue, uint64_t ticket) {
    if (cb) cb->trace338.identify(object,made_us,queue,ticket);
}

void hakios_metal_cb_notify_recorded338(hakios_metal_cb* cb,
    void (*callback)(hakios_metal_cb*,void*),void* context) {
    CbLease invocation(cb);
    if (!callback) return;
    if (deferring(cb)) {
        bool accepted=false;
        try {
            // Only queue admission is inside catch. A callback exception must
            // never be mistaken for failed admission and invoked twice.
            cb->deferrer->post(cb,[cb,callback,context] { callback(cb,context); },2,false);
            accepted=true;
        } catch (...) { /* notification ownership has not transferred */ }
        if (accepted) return;
        syncOne(cb); // rare allocation/closed-recorder fallback, no re-commit
    }
    callback(cb,context);
}

'''+at)
    else:
        raise ValueError(name)
    return raw,edits


def frontend(raw):
    edits=[]
    def replace(old,new):
        nonlocal raw
        assert raw.count(old)==1,old
        raw=raw.replace(old,new);edits.append((old,new))
    replace('#include "GauguinQueue337.h"','#include "GauguinQueue337.h"\n#include "GauguinAsync338.h"')
    at='\t_createdAt = hm_now();'
    replace(at,at+'''
    if (_cb && gauguin_async338_scope(_createdAt))
        hakios_metal_cb_trace338(_cb,(uintptr_t)self,gauguin_async338_us(_createdAt),[queue hakiosTraceQueue],0);''')
    at='static void\nhm_completed(hakios_metal_cb *cb, void *context)'
    replace(at,'''static void
hm_recorded338(hakios_metal_cb *cb, void *context)
{
    HakiosMetalCommandBuffer *self=(HakiosMetalCommandBuffer *)context;
    @try {
        @autoreleasepool {
            /* Recorder worker skips syncOne; failed notification admission has
             * already drained on the caller. Neither case posts a new commit. */
            enum hakios_metal_status state=hakios_metal_cb_status(cb);
            gauguin_async338_notice(self,[self hakiosCreatedAt],hm_now(),(unsigned)state);
            if (state>=HAKIOS_METAL_SCHEDULED) [self hakiosMarkScheduled];
        }
    } @finally {
        [self release]; /* independent scheduling-notification lease */
    }
}

'''+at)
    at='\t\tconst uint64_t traceTicket = [traceQueue hakiosTraceAdmit];'
    replace(at,at+'''
        if (gauguin_async338_scope(_createdAt))
            hakios_metal_cb_trace338(_cb,(uintptr_t)self,gauguin_async338_us(_createdAt),traceID,traceTicket);''')
    at='''\t\t\t/* In deferred mode commit posts to the core worker. Status drains that work before
\t\t\t * we announce scheduling; an error awaiting its FIFO callback is terminal later. */
\t\t\tenum hakios_metal_status state = hakios_metal_cb_status(_cb);
\t\t\tgauguin_c4_queue_trace(4, self, _createdAt, hm_now(), (unsigned)state);
\t\t\thm_fps_commit(hm_now() - began);
\t\t\tif (state >= HAKIOS_METAL_SCHEDULED) [self hakiosMarkScheduled];'''
    replace(at,'''            /* The serial frontend need only preserve admission order. A same-
             * recorder notification observes actual commit execution later.
             * Its separate lease also covers completion-before-notification. */
            [self retain];
            hakios_metal_cb_notify_recorded338(_cb,hm_recorded338,self);
            gauguin_c4_queue_trace(4,self,_createdAt,hm_now(),0);
            hm_fps_commit(hm_now()-began);''')
    return raw,edits


def check_reverse(original,changed,edits):
    for old,new in reversed(edits):
        assert changed.count(new)==1
        changed=changed.replace(new,old)
    assert changed==original
