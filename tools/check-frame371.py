#!/usr/bin/env python3
"""Check the compiled transport observer and offline attribution boundaries."""

from importlib import import_module
import subprocess

from frame371_transport import classify, deadline_transport, decode

scope = import_module('prepare-frame371')

SHIM = r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define TASK_NULL NULL
#define MACH_MSG_SUCCESS 0
typedef int mach_msg_return_t;
typedef struct { uint32_t val[8]; } audit_token_t;
typedef struct { audit_token_t msgh_audit; } mach_msg_max_trailer_t;
typedef struct { uint32_t msgh_id; } message_header;
typedef struct { message_header header; mach_msg_max_trailer_t trailer; } *ipc_kmsg_t;
typedef struct { bool active; struct task *is_task; } *ipc_space_t;
typedef struct task { const audit_token_t token; ipc_space_t itk_space; } *task_t;
typedef struct { ipc_space_t receiver; } *ipc_port_t;
static task_t current;
static uint64_t now, tid;
static uint64_t mach_absolute_time(void) { return now; }
static uint64_t current_thread(void) { return tid; }
static uint64_t thread_tid(uint64_t thread) { return thread; }
static task_t current_task(void) { return current; }
static uint32_t task_pid(task_t task) { return task->token.val[5]; }
static const audit_token_t *task_get_audit_token(task_t task) { return &task->token; }
static ipc_space_t ip_get_receiver(ipc_port_t port) { return port->receiver; }
static bool is_active(ipc_space_t space) { return space->active; }
static message_header *ikm_header(ipc_kmsg_t msg) { return &msg->header; }
static mach_msg_max_trailer_t *ipc_kmsg_get_trailer(ipc_kmsg_t msg, bool copied)
{ assert(!copied); return &msg->trailer; }
void sweet_log_append(const char *line, int length) { fwrite(line, 1, length, stdout); }
'''

EXERCISE = r'''
int main(void)
{
    struct task source = {.token.val={0,0,0,0,0,11,0,1}};
    struct task target = {.token.val={0,0,0,0,0,12,0,2}};
    struct task other = {.token.val={0,0,0,0,0,12,0,3}};
    __typeof__(*target.itk_space) space = {true, &target};
    target.itk_space = &space;
    other.itk_space = &space;
    __typeof__(* (ipc_port_t)0) port = {&space};
    __typeof__(* (ipc_kmsg_t)0) message = {{321},{source.token}};
    struct f371_delivery row;
    assert(!f371_live());
    sweet_frame371_arm(f371_identity(&source.token), f371_identity(&target.token), 1000);

    now = 200; current = &source; tid = 41;
    space.is_task = &other;
    f371_send(&message, &port, 190);
    assert(f371_sent == 0);
    space.is_task = &target;
    f371_send(&message, &port, 190);
    f371_post(&message);
    now = 215; current = &other; tid = 52;
    assert(!f371_take(&message, &space, &row));
    current = &target;
    assert(f371_take(&message, &space, &row));
    assert(row.serial == 1 && row.message_id == 321 && row.send == 190 && row.post == 200);
    assert(row.source_thread == 41 && row.receiver_thread == 52);
    assert(!f371_take(&message, &space, &row));
    now = 220; f371_complete(&row, MACH_MSG_SUCCESS);

    now = 310; current = &source; tid = 41;
    f371_send(&message, &port, 305);
    f371_post(&message);
    f371_forget(&message); /* reuse the same address without an inherited tag */
    current = &target; tid = 52;
    assert(!f371_take(&message, &space, &row));

    now = 400; current = &source; tid = 42;
    f371_send(&message, &port, 390);
    f371_post(&message);
    current = &target; tid = 53;
    assert(f371_take(&message, &space, &row));
    f371_complete(&row, 1);

    now = 510; current = &source; tid = 41;
    f371_send(&message, &port, 505);
    f371_post(&message);
    current = &target; tid = 52;
    struct f371_slot *slot = f371_slot_for(&message);
    assert(f371_try_slot(slot));
    assert(!f371_take(&message, &space, &row));
    f371_release_slot(slot);
    assert(f371_take(&message, &space, &row));
    now = 535; f371_complete(&row, MACH_MSG_SUCCESS);
    assert(f371_copied == 2 && f371_missed == 3 && f371_failed == 1 && f371_busy == 1);

    assert(f371_enter(900));
    sweet_frame371_drain();
    f371_leave();
    sweet_frame371_drain();
    sweet_frame371_drain();
    assert(!f371_live() && !f371_enter(999) && !f371_enter(1000));
    return 0;
}
'''


def main():
    scope.check_budget()
    out = scope.HOST.parent
    out.mkdir()
    source = scope.BASE/'native-kernel/source/osfmk/ipc/ipc_kmsg.c'
    native = source.read_text()
    code = native[native.index('enum { F371_SLOTS'):native.index('#endif /* GAUGUIN */')]
    projection = out/'observer-projection.c'
    projection.write_text(SHIM+code+EXERCISE)
    binary = out/'observer-projection'
    subprocess.run(['xcrun','clang','-std=c11','-O1','-g','-fsanitize=address,undefined',
        '-fno-sanitize-recover=all',str(projection),'-o',str(binary)],check=True,timeout=60)
    raw = 'SWEET F344 H: count=1 reason=1 lost=0 start=100 end=1000 numer=1 denom=1\n'
    raw += subprocess.check_output([str(binary)],text=True,timeout=30)
    out_log = out/'modeled-transport.log'
    out_log.write_text(raw)
    saved = decode(raw,1,1)
    scope.require(saved['paired_exact_receipts']==2 and not saved['full_scope_observed'],'modeled loss disappeared')
    pair = saved['pairs'][0]
    expected = ['before_send','send_before_post','post_before_copyout','copyout_before_SwapBegin']
    scope.require([classify(pair,t) for t in (189,190,200,220)]==expected,'cutoff equality differs')
    miss = dict(stroke=3,scan=4,deadline_ns=210,returned_main_callback={'returned_us':0},
        next_swap={'generation':7},CA_observer=None,next_swap_within_stroke_tail=True)
    swap = dict(generation=7,begin_tick=240,begin_thread=52)
    match, = deadline_transport({'details':[miss]},[swap],saved,[],[],lambda t:t)
    scope.require(match['same_thread_deadline_stage']=='post_before_copyout','same-thread cutoff differs')
    swap['begin_thread'] = 53
    unjoined, = deadline_transport({'details':[miss]},[swap],saved,[],[],lambda t:t)
    scope.require(unjoined['same_thread_deadline_stage']=='different_receiver_thread_only','wrong thread was joined')
    for malformed in (raw.replace('F: count=2','F: count=3'),
                      raw.replace('E 4 141','E 1 141'),
                      raw.replace('be c8 dc','be dd dc')):
        try:
            decode(malformed,1,1)
        except ValueError:
            continue
        scope.require(False,'damaged transport capture was accepted')
    archived = scope.load(scope.REFERENCE/'scoped-swap-timing-0370.json')
    warm = [row for row in archived['frontend_cutoffs']['details'] if row['stroke']>=3]
    count = len(warm)
    returned = sum(row['returned_main_callback'] is not None for row in warm)
    scope.require((count,returned)==(26,24),'0370 reproduced warm cutoff population differs')
    scope.save(scope.HOST,dict(state='0371-producer-transport-cross-compiled-and-modeled',
        patch_sha256=scope.sha(scope.PATCH),projection_passed=True,device_writes=0,device_boots=0,
        warm_0370_cutoffs=count,warm_0370_returned_touch=returned,
        input_pins={str(path):scope.sha(path) for path in (source,projection,binary,out_log)}))


if __name__=='__main__':
    main()
