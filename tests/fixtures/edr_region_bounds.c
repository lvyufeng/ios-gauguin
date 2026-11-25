/* Feed malformed replies through the production leaf validator. No device IO. */
#include <mach/mach.h>
#include <mach/vm_map.h>
#include <assert.h>
static kern_return_t fake_region(vm_map_read_t, vm_address_t *, vm_size_t *,
    natural_t *, vm_region_recurse_info_t, mach_msg_type_number_t *);
#define vm_region_recurse_64 fake_region
#include "../../graphics/gauguin-edr-default/EDRDefault.c"
#undef vm_region_recurse_64

static struct geq_leaf reply;
static unsigned calls, checks;
static kern_return_t fake_region(vm_map_read_t task, vm_address_t *address,
    vm_size_t *size, natural_t *depth, vm_region_recurse_info_t info,
    mach_msg_type_number_t *count)
{
    assert(task == mach_task_self() && *depth == 8 && *count == 12);
    ++calls;
    *address = reply.begin; *size = reply.length; *depth = reply.depth;
    memcpy(info, &reply.info, sizeof(reply.info)); *count = reply.count;
    return reply.status;
}
static void reset(void)
{
    reply = (struct geq_leaf){ .begin = 0x1000, .length = 0x4000, .depth = 1,
        .count = 12, .status = KERN_SUCCESS,
        .info = { .protection = VM_PROT_READ | VM_PROT_EXECUTE } };
}
static void expect(bool wanted)
{
    struct geq_leaf leaf;
    unsigned before = calls;
    assert(geq_leaf(0x2000, 64, VM_PROT_READ | VM_PROT_EXECUTE, &leaf) == wanted);
    assert(calls == before + 1); ++checks;
}
int main(void)
{
    reset(); expect(true);
    reply.depth = 8; expect(true);
    reply.depth = 9; expect(false);
    reset(); reply.info.is_submap = 1; expect(false);
    reset(); reply.status = KERN_INVALID_ADDRESS; expect(false);
    reset(); reply.count = 11; expect(false);
    reply.count = 13; expect(false);
    reset(); reply.begin = 0x2001; expect(false);
    reset(); reply.length = 0; expect(false);
    reply.length = 0x103f; expect(false);
    reply.length = 0x1040; expect(true);
    reply.length = UINTPTR_MAX; expect(false);
    reset(); reply.info.protection = VM_PROT_READ; expect(false);
    reply.info.protection = VM_PROT_EXECUTE; expect(false);
    reply.info.protection = VM_PROT_NONE; expect(false);
    struct geq_leaf leaf;
    unsigned before = calls;
    assert(!geq_leaf(0, 64, VM_PROT_READ, &leaf));
    assert(!geq_leaf(0x2000, 0, VM_PROT_READ, &leaf));
    assert(!geq_leaf(UINTPTR_MAX-3, 8, VM_PROT_READ, &leaf));
    assert(calls == before); checks += 3;
    reset(); reply.info.is_submap = 1;
    unsigned char digest[32] = {0};
    assert(!geq_digest(0x2000, 64, digest, "initializer")); ++checks;
    struct geq_page page;
    reset(); assert(!geq_region(0x2000, 8, VM_PROT_READ, &page)); ++checks;
    printf("{\"state\":\"passed-production-recursive-region-boundaries\",\"checks\":%u,\"rpc_calls\":%u,\"max_input_depth\":8,\"short_info_count\":12,\"device_commands\":0}\n", checks, calls);
}
