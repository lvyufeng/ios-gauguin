"""Reversible queue metadata additions to the exact C4Q321 frontend."""
def instrument(raw):
    original=raw;edits=[]
    def replace(a,b):
        nonlocal raw
        assert raw.count(a)==1,a
        raw=raw.replace(a,b);edits.append((a,b))
    replace('#include "GauguinC4QueueTrace.h"',
            '#include "GauguinC4QueueTrace.h"\n#include "GauguinQueue337.h"')
    a='\tdispatch_queue_t _deferred;              /* every commit enters this FIFO, including ordinary commits */'
    replace(a,a+'\n\tuint64_t _traceQueue, _traceAdmitted, _traceRetired;')
    a='- (void)hakiosAdmit:(dispatch_block_t)commit; /* caller holds the queue\'s admission lock */'
    methods='''
- (uint64_t)hakiosTraceQueue;
- (uint64_t)hakiosTraceAdmit;
- (uint64_t)hakiosTraceRetired;
- (uint64_t)hakiosTraceRetire;'''
    replace(a,a+methods)
    a='\thakios_metal_queue_set_deferred(_queue, 1);'
    replace(a,a+'\n\tstatic uint64_t traceIdentifier;\n\t_traceQueue = __atomic_add_fetch(&traceIdentifier, 1, __ATOMIC_RELAXED);')
    a='/* Called under @synchronized(queue): one lock defines admission order for held and ordinary buffers alike. */'
    replace(a,'''- (uint64_t)hakiosTraceQueue { return _traceQueue; }
- (uint64_t)hakiosTraceAdmit { return ++_traceAdmitted; } /* caller holds admission lock */
- (uint64_t)hakiosTraceRetired { return __atomic_load_n(&_traceRetired, __ATOMIC_ACQUIRE); }
- (uint64_t)hakiosTraceRetire { return __atomic_add_fetch(&_traceRetired, 1, __ATOMIC_RELEASE); }

'''+a)
    a='\t\t[_queue hakiosAdmit:^{\n'
    replace(a,'''\t\tHakiosMetalCommandQueue *traceQueue = _queue;
\t\tconst uint64_t traceID = [traceQueue hakiosTraceQueue];
\t\tconst uint64_t traceTicket = [traceQueue hakiosTraceAdmit];
\t\tconst uintptr_t traceObject = (uintptr_t)self;
\t\tconst double traceMade = _createdAt;
\t\tgauguin_queue337(0, traceObject, traceMade, traceID, traceTicket, [traceQueue hakiosTraceRetired], hm_now());
'''+a)
    a='\t\t\tgauguin_c4_queue_trace(1, self, _createdAt, hm_now(), 0);'
    replace(a,a+'\n\t\t\tgauguin_queue337(1, traceObject, traceMade, traceID, traceTicket, [traceQueue hakiosTraceRetired], hm_now());')
    a='\t\t\tif (state >= HAKIOS_METAL_SCHEDULED) [self hakiosMarkScheduled];\n\t\t\t[self release];'
    replace(a,a+'\n\t\t\tgauguin_queue337(2, traceObject, traceMade, traceID, traceTicket, [traceQueue hakiosTraceRetire], hm_now());')
    undone=raw
    for a,b in reversed(edits):
        assert undone.count(b)==1
        undone=undone.replace(b,a)
    assert undone==original
    return raw,len(edits)
