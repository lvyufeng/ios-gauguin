/* Exercise production policy/transaction code and the real Darwin VM adapters. */
#include "../../graphics/gauguin-io-path/edr/EDRDefault.c"
#include <fcntl.h>
#include <dlfcn.h>
#include <sys/mman.h>

static unsigned checks;
static void need(bool yes, const char *what)
{
    ++checks;
    if (!yes) { fprintf(stderr, "FAIL %s\n", what); exit(2); }
}
struct fault {
    uintptr_t slot;
    unsigned writable, restores;
    int protect_error;
    unsigned restore_errors;
    bool race_before, race_after;
};
static int fake_writable(void *context)
{
    struct fault *f = context;
    ++f->writable;
    if (f->race_before) f->slot = 456;
    return f->protect_error;
}
static int fake_restore(void *context)
{
    struct fault *f = context;
    ++f->restores;
    if (f->race_after && f->restores == 1) f->slot = 789;
    return f->restores <= f->restore_errors ? -1 : 0;
}
static enum geq_result transaction(struct fault *f)
{
    struct geq_memory_ops ops = { f, fake_writable, fake_restore };
    return geq_clear_optional(&f->slot, 123, &ops);
}
static bool host_scope(const char *program, unsigned uid, unsigned euid,
                       const char *os, const char *kernel, const char *args)
{
    return geq_scope(program, uid, euid, os, kernel, args, "edr-default318");
}
int main(void)
{
    const char *kernel = "Darwin: xnu-local342-272d6c88821c91d83d2f06497992d353";
    need(host_scope("backboardd", 501, 501, "20H392", kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4"), "exact scope");
    need(host_scope("backboardd", 501, 501, "20H392", kernel, "a=1\tgmt=2\ngsp=328 other=2 sweetgpumap=1 gpf=4"), "whole token");
    const char *bad_mapping[] = {
        "gmt=2 gsp=328 gpf=4", "gmt=2 gsp=328 sweetgpumap=0 gpf=4", "gmt=2 gsp=328 sweetgpumap=2 gpf=4",
        "gmt=2 gsp=328 sweetgpumap=01 gpf=4", "gmt=2 gsp=328 sweetgpumap=1x gpf=4",
        "gmt=2 gsp=328 sweetgpumap=1 sweetgpumap=1 gpf=4", "gmt=2 gsp=328 other=sweetgpumap=1 gpf=4"
    };
    for (unsigned i=0;i<sizeof(bad_mapping)/sizeof(bad_mapping[0]);i++)
        need(!host_scope("backboardd",501,501,"20H392",kernel,bad_mapping[i]),"mapping opt-in required exactly once");
    need(!host_scope("backboardd",501,501,"20H392","Darwin: xnu-local316-7b216154ad1241fbab89f0d6385f0344",
                    "gmt=2 gsp=328 sweetgpumap=1 gpf=4"),"old kernel scope refused");
    const char *bad_profile[] = {
        "gmt=2 gsp=328 sweetgpumap=1", "gmt=2 gsp=328 sweetgpumap=1 gpf=0",
        "gmt=2 gsp=328 sweetgpumap=1 gpf=1", "gmt=2 gsp=328 sweetgpumap=1 gpf=2",
        "gmt=2 gsp=328 sweetgpumap=1 gpf=3",
        "gmt=2 gsp=328 sweetgpumap=1 gpf=04", "gmt=2 gsp=328 sweetgpumap=1 gpf=4x",
        "gmt=2 gsp=328 sweetgpumap=1 gpf=4 gpf=4", "gmt=2 gsp=328 sweetgpumap=1 other=gpf=4"
    };
    for(unsigned i=0;i<sizeof(bad_profile)/sizeof(bad_profile[0]);i++)
        need(!host_scope("backboardd",501,501,"20H392",kernel,bad_profile[i]),"native565 opt-in required exactly once");
    need(!host_scope("backboardd",501,501,"20H392","Darwin: xnu-local324-651abf89bb854a769f184c0c671b540a",
                    "gmt=2 gsp=328 sweetgpumap=1 gpf=4"),"previous mapping kernel refused");
    need(!host_scope("backboardd",501,501,"20H392",kernel,"gmt=2 gsp=316 sweetgpumap=1 gpf=4"),"old sampler profile refused");
    need(!host_scope("backboardd",501,501,"20H392","xnu-local328-c6fa9e0be2574bfca23a4a6951e0bbe6","gmt=2 gsp=328 sweetgpumap=1 gpf=4"),"328 kernel refused");
    need(!host_scope("backboardd",501,501,"20H392","xnu-local331-01cb28877a5544d19a5f9e8a9abc556a","gmt=2 gsp=328 sweetgpumap=1 gpf=4"),"331 kernel refused");
    const char *bad_modes[] = { "admission", "edr-default316", "", NULL };
    for (unsigned i = 0; i < sizeof(bad_modes)/sizeof(bad_modes[0]); ++i)
        need(!geq_scope("backboardd", 501, 501, "20H392", kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4", bad_modes[i]), "dedicated mode required");
    need(!host_scope("backboardd",501,501,"20H392","xnu-local337-d846caeab5924ac49b8ac8802e070e95","gmt=2 gsp=328 sweetgpumap=1 gpf=4"),"337 kernel refused");
    const char *bad[] = { " sweetgpumap=1 gpf=4", "gmt=2 sweetgpumap=1 gpf=4", "gsp=328 sweetgpumap=1 gpf=4", "gmt=2x gsp=328 sweetgpumap=1 gpf=4",
        "gmt=2 gsp=328 gmt=2 sweetgpumap=1 gpf=4", "gmt=2 gsp=328 gsp=328 sweetgpumap=1 gpf=4", "gmt=2 gsp=315 sweetgpumap=1 gpf=4",
        "gmt=1 gsp=328 sweetgpumap=1 gpf=4", "other=gmt=2 gsp=328 sweetgpumap=1 gpf=4", "gmt= 2 gsp=328 sweetgpumap=1 gpf=4", NULL };
    for (unsigned i = 0; i < sizeof(bad)/sizeof(bad[0]); ++i)
        need(!host_scope("backboardd", 501, 501, "20H392", kernel, bad[i]), "bad opt-in");
    const char *programs[] = { "SpringBoard", "backboardd-helper", "", NULL };
    for (unsigned i = 0; i < sizeof(programs)/sizeof(programs[0]); ++i)
        need(!host_scope(programs[i], 501, 501, "20H392", kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4"), "other process");
    for (unsigned id = 0; id < 1024; ++id) {
        need(host_scope("backboardd", id, 501, "20H392", kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4") == (id == 501), "real uid");
        need(host_scope("backboardd", 501, id, "20H392", kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4") == (id == 501), "effective uid");
    }
    need(!host_scope("backboardd", 501, 501, "20H393", kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4"), "other OS");
    need(!host_scope("backboardd", 501, 501, NULL, kernel, "gmt=2 gsp=328 sweetgpumap=1 gpf=4"), "missing OS");
    need(!host_scope("backboardd", 501, 501, "20H392", "other kernel", "gmt=2 gsp=328 sweetgpumap=1 gpf=4"), "other kernel");
    need(!host_scope("backboardd", 501, 501, "20H392", NULL, "gmt=2 gsp=328 sweetgpumap=1 gpf=4"), "missing kernel");

    struct fault f = { .slot = 123 };
    struct geq_memory_ops ops = { &f, fake_writable, fake_restore };
    need(geq_clear_optional(NULL, 123, &ops) == GEQ_INVALID, "null slot");
    need(geq_clear_optional((void *)1, 123, &ops) == GEQ_INVALID, "unaligned slot");
    need(geq_clear_optional(&f.slot, 0, &ops) == GEQ_INVALID, "zero original");
    need(geq_clear_optional(&f.slot, 123, NULL) == GEQ_INVALID, "no operations");
    struct geq_memory_ops empty = {0};
    need(geq_clear_optional(&f.slot, 123, &empty) == GEQ_INVALID, "missing operations");
    need(!f.writable && !f.restores && f.slot == 123, "invalid no operations");
    f = (struct fault){ .slot = 456 };
    need(transaction(&f) == GEQ_ORIGINAL_MISMATCH && !f.writable && f.slot == 456, "other pointer preserved");
    f = (struct fault){ .slot = 123, .protect_error = -1 };
    need(transaction(&f) == GEQ_PROTECT_FAILED && f.slot == 123 && !f.restores, "failed protect no write");
    f = (struct fault){ .slot = 123 };
    need(transaction(&f) == GEQ_INSTALLED && !f.slot && f.writable == 1 && f.restores == 1, "clear once");
    f = (struct fault){ .slot = 123, .race_before = true };
    need(transaction(&f) == GEQ_RACE && f.slot == 456 && f.restores == 1, "pre-CAS race preserved");
    f = (struct fault){ .slot = 123, .race_before = true, .restore_errors = 1 };
    need(transaction(&f) == GEQ_RESTORE_FAILED_WITHOUT_WRITE && f.slot == 456, "race plus protect failure");
    f = (struct fault){ .slot = 123, .restore_errors = 1 };
    need(transaction(&f) == GEQ_ROLLED_BACK && f.slot == 123 && f.restores == 2, "rollback original");
    f = (struct fault){ .slot = 123, .restore_errors = 2 };
    need(transaction(&f) == GEQ_ROLLBACK_INCOMPLETE && f.slot == 123, "protection rollback reported");
    f = (struct fault){ .slot = 123, .restore_errors = 1, .race_after = true };
    need(transaction(&f) == GEQ_ROLLBACK_INCOMPLETE && f.slot == 789, "rollback does not clobber another writer");

    size_t unit = vm_page_size;
    unsigned char *mapping = mmap(NULL, unit*3, PROT_NONE, MAP_ANON | MAP_PRIVATE, -1, 0);
    need(mapping != MAP_FAILED, "guarded mapping");
    unsigned char *data = mapping + unit;
    need(!mprotect(data, unit, PROT_READ | PROT_WRITE), "initialize own page");
    memset(data, 0x5a, unit);
    uintptr_t *slot = (void *)(data + 128);
    uintptr_t original = (uintptr_t)&main;
    *slot = original;
    unsigned char *expected = malloc(unit);
    need(expected != NULL, "comparison storage");
    memcpy(expected, data, unit);
    memset(expected + 128, 0, sizeof(*slot));
    need(!mprotect(data, unit, PROT_READ), "read-only initial page");
    struct geq_page page = {0};
    need(geq_region((uintptr_t)slot, sizeof(*slot), VM_PROT_READ, &page), "real LP64 region");
    need(page.protection == VM_PROT_READ && page.address == (uintptr_t)data && page.size == unit, "exact page/protection");
    need(!geq_region((uintptr_t)mapping, 1, VM_PROT_READ, NULL), "guard page denied");
    need(!geq_region(UINTPTR_MAX-3, 8, VM_PROT_READ, NULL), "overflow denied");
    need(!geq_region((uintptr_t)data, unit+1, VM_PROT_READ, NULL), "cross-region denied");
    struct geq_memory_ops real = { &page, geq_writable_copy, geq_restore };
    need(geq_clear_optional(slot, original, &real) == GEQ_INSTALLED, "real writable-copy and restore");
    need(!memcmp(data, expected, unit), "only eight bytes changed");
    struct geq_page after = {0};
    need(geq_region((uintptr_t)slot, sizeof(*slot), VM_PROT_READ, &after) &&
         after.protection == VM_PROT_READ, "original protection restored");
    unsigned char digest[32];
    CC_SHA256((const void *)(uintptr_t)&geq_scope, 4, digest);
    need(geq_digest((uintptr_t)&geq_scope, 4, digest, NULL), "real executable digest");
    digest[0] ^= 1;
    need(!geq_digest((uintptr_t)&geq_scope, 4, digest, NULL), "code mismatch rejected");
    need(!geq_digest((uintptr_t)data, 4, digest, NULL), "data not accepted as code");
    void *shared = dlsym(RTLD_DEFAULT, "mach_absolute_time");
    need(shared != NULL, "shared-cache symbol");
    struct geq_leaf leaf;
    need(geq_leaf((uintptr_t)shared, 64, VM_PROT_READ | VM_PROT_EXECUTE, &leaf), "shared executable leaf");
    need(leaf.depth > 0 && leaf.depth <= 8 && leaf.count == 12 && !leaf.info.is_submap, "bounded short leaf");
    vm_address_t outer = (vm_address_t)shared; vm_size_t outer_size = 0;
    vm_region_basic_info_data_64_t basic = {0};
    mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64; mach_port_t object = 0;
    need(vm_region_64(mach_task_self(), &outer, &outer_size, VM_REGION_BASIC_INFO_64,
        (vm_region_info_t)&basic, &count, &object) == KERN_SUCCESS, "legacy map observation");
    if (object) mach_port_deallocate(mach_task_self(), object);
    need(basic.reserved && basic.protection == VM_PROT_READ, "reproduces318outermap");
    CC_SHA256(shared, 64, digest);
    need(geq_digest((uintptr_t)shared, 64, digest, NULL), "production shared code digest now passes");
    digest[0] ^= 1;
    need(!geq_digest((uintptr_t)shared, 64, digest, NULL), "shared code mismatch refused");
    need(!geq_region((uintptr_t)shared, 8, VM_PROT_READ, &page), "executable page never writable");
    free(expected);
    need(!munmap(mapping, unit*3), "mapping released");

    /* Shared read-only backing is the important isolation case: a writable
     * private copy must leave both another mapping and the backing file intact. */
    unsigned char *backing = malloc(unit);
    need(backing != NULL, "backing buffer");
    memset(backing, 0x6b, unit);
    memcpy(backing + 128, &original, sizeof(original));
    char path[] = "/tmp/gauguin-edr-cow-XXXXXX";
    int fd = mkstemp(path);
    need(fd >= 0 && write(fd, backing, unit) == (ssize_t)unit, "own temporary backing");
    int read_fd = open(path, O_RDONLY);
    need(read_fd >= 0 && !close(fd), "read-only descriptor");
    unsigned char *first = mmap(NULL, unit, PROT_READ, MAP_SHARED, read_fd, 0);
    unsigned char *second = mmap(NULL, unit, PROT_READ, MAP_SHARED, read_fd, 0);
    need(first != MAP_FAILED && second != MAP_FAILED && !unlink(path), "two shared mappings");
    slot = (void *)(first + 128);
    need(geq_region((uintptr_t)slot, sizeof(*slot), VM_PROT_READ, &page), "shared mapping metadata");
    real.context = &page;
    need(geq_clear_optional(slot, original, &real) == GEQ_INSTALLED, "shared source becomes private copy");
    need(!memcmp(second, backing, unit), "other mapping unchanged");
    uintptr_t on_disk = 0;
    need(pread(read_fd, &on_disk, sizeof(on_disk), 128) == sizeof(on_disk) &&
         on_disk == original, "backing file unchanged");
    memset(backing + 128, 0, sizeof(original));
    need(!memcmp(first, backing, unit), "private mapping only eight bytes changed");
    need(geq_region((uintptr_t)slot, sizeof(*slot), VM_PROT_READ, &after) &&
         after.protection == VM_PROT_READ, "shared-copy protection restored");
    need(!munmap(first, unit) && !munmap(second, unit) && !close(read_fd), "shared mappings released");
    free(backing);
    printf("{\"state\":\"EDR320-policy-transaction-and-Darwin-VM-checks-passed\",\"checks\":%u,\"device_commands\":0,\"iOS_runtime_qualified\":false}\n", checks);
    return 0;
}
