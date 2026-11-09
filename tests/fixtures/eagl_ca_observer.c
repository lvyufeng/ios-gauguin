#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <pthread.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <string.h>
#include "ca_effects.h"

struct eagl { void *table[1]; struct gauguin_ca_effects ca, ca_draw; };
static struct eagl *contexts[8];
static pthread_mutex_t gauguin_context_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER;
static int function_numbers;
static _Atomic unsigned assertions, calls;
static void check(bool yes, int line) {
    atomic_fetch_add(&assertions, 1);
    if (!yes) { fprintf(stderr, "CA observer assertion line %d\n", line); exit(1); }
}
#define CHECK(yes) check(!!(yes), __LINE__)
static void say(const char *format, ...) { (void)format; }
struct gauguin_ca_site;
static bool locate_test(struct gauguin_ca_site *site);
static kern_return_t protect_test(vm_map_t, mach_vm_address_t, mach_vm_size_t, boolean_t, vm_prot_t);
#define GAUGUIN_CA_LOCATE locate_test
#define GAUGUIN_CA_PROTECT protect_test
#include "ca_observer.inc"

static struct gauguin_ca_site test_site;
static bool fail_locate, race_slot;
static unsigned protect_calls, fail_protect;
static bool locate_test(struct gauguin_ca_site *site) {
    if (fail_locate) return false;
    *site = test_site; return true;
}
static kern_return_t protect_test(vm_map_t task, mach_vm_address_t at, mach_vm_size_t size,
                                  boolean_t maximum, vm_prot_t protection) {
    protect_calls++;
    if (protect_calls == fail_protect) return KERN_PROTECTION_FAILURE;
    kern_return_t result = mach_vm_protect(task, at, size, maximum, protection);
    if (race_slot && result == KERN_SUCCESS && (protection & VM_PROT_WRITE)) {
        *test_site.slot = 1;
    }
    return result;
}
static mach_vm_address_t allocate(size_t size) {
    mach_vm_address_t address = 0;
    CHECK(mach_vm_allocate(mach_task_self(), &address, size, VM_FLAGS_ANYWHERE) == KERN_SUCCESS);
    return address;
}
static vm_prot_t protection_at(uintptr_t address) {
    mach_vm_address_t base = address; mach_vm_size_t size;
    vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64;
    mach_port_t object = MACH_PORT_NULL;
    CHECK(mach_vm_region(mach_task_self(), &base, &size, VM_REGION_BASIC_INFO_64,
                          (vm_region_info_t)&info, &count, &object) == KERN_SUCCESS);
    if (object) mach_port_deallocate(mach_task_self(), object);
    return info.protection;
}
static void reset_slot(void) {
    CHECK(mach_vm_protect(mach_task_self(), (uintptr_t)test_site.slot, vm_page_size, FALSE,
                          VM_PROT_READ | VM_PROT_WRITE) == KERN_SUCCESS);
    *test_site.slot = (uintptr_t)test_site.original;
    CHECK(mach_vm_protect(mach_task_self(), (uintptr_t)test_site.slot, vm_page_size, FALSE,
                          VM_PROT_READ) == KERN_SUCCESS);
    fail_locate = race_slot = false; protect_calls = fail_protect = 0;
}
static _Thread_local struct {
    void *context; unsigned index; size_t components, count; const float *values;
    struct eagl *e; unsigned function, expected;
} forwarded;
static void original(void *context, unsigned index, size_t components, size_t count, const float *values) {
    CHECK(context == forwarded.context && index == forwarded.index && components == forwarded.components &&
          count == forwarded.count && values == forwarded.values);
    if (forwarded.e) CHECK(forwarded.e->ca.given[forwarded.function] == forwarded.expected);
    atomic_fetch_add(&calls, 1);
}
static void invoke(void *context, unsigned index, size_t components, size_t count, const float *values,
                   struct eagl *e, unsigned function, unsigned expected) {
    forwarded.context = context; forwarded.index = index; forwarded.components = components;
    forwarded.count = count; forwarded.values = values; forwarded.e = e;
    forwarded.function = function; forwarded.expected = expected;
    gauguin_ca_uniform_fn entry = (gauguin_ca_uniform_fn)*test_site.slot;
    entry(context, index, components, count, values);
}
struct fake_context { uint8_t bytes[0x800]; uint32_t function[8]; struct eagl e; };
static void set_function(struct fake_context *ca, unsigned function) { ca->function[4] = function; }
static void initialize(struct fake_context *ca) {
    memset(ca, 0, sizeof(*ca));
    uintptr_t vptr = test_site.vptr, pointer = (uintptr_t)ca->function, table = (uintptr_t)ca->e.table;
    memcpy(ca->bytes, &vptr, sizeof(vptr));
    memcpy(ca->bytes + 0x10, &pointer, sizeof(pointer));
    memcpy(ca->bytes + 0x7f8, &table, sizeof(table));
    ca->e.table[0] = &ca->e;
}
static void *thread_main(void *arg) {
    struct fake_context *ca = arg;
    for (unsigned i = 0; i < 400; i++) {
        float values[20];
        for (unsigned j = 0; j < 20; j++) values[j] = (float)((uintptr_t)ca & 0xffff) + j + i;
        set_function(ca, i % 2 ? 20 : 45);
        invoke(ca->bytes, 0, 4, 5, values, &ca->e, ca->function[4], 20);
        CHECK(gauguin_ca_function(&ca->e) == ca->function[4]);
        CHECK(!memcmp(ca->e.ca_draw.values[ca->function[4]], values, sizeof(values)));
    }
    return NULL;
}
static void identity_tests(void) {
    /* Sparse anonymous VM, not a byte-array reimplementation of the parser. */
    size_t size = (size_t)(GAUGUIN_CA_VTABLE - GAUGUIN_CA_IMAGE + 0x8000);
    uintptr_t image = allocate(size);
    CHECK(image > GAUGUIN_CA_IMAGE);
    intptr_t slide = (intptr_t)(image - GAUGUIN_CA_IMAGE);
    struct mach_header_64 *header = (void *)image;
    *header = (struct mach_header_64){ .magic = MH_MAGIC_64, .cputype = CPU_TYPE_ARM64,
                                      .ncmds = 1, .sizeofcmds = sizeof(struct uuid_command) };
    struct uuid_command *uuid = (void *)(header + 1);
    *uuid = (struct uuid_command){ .cmd = LC_UUID, .cmdsize = sizeof(*uuid),
        .uuid = {0x9e,0x40,0xb2,0xeb,0x26,0x0c,0x3a,0xf1,0xae,0x45,0xa1,0xa5,0x51,0xa8,0xc1,0xb9} };
    uintptr_t *slot = (void *)(GAUGUIN_CA_VTABLE + slide + 0x398);
    uintptr_t target = GAUGUIN_CA_UNIFORM + slide;
    *slot = target;
    static const uint8_t code[] = {
        0xf8,0x5f,0xbc,0xa9,0xf6,0x57,0x01,0xa9,0xf4,0x4f,0x02,0xa9,0xfd,0x7b,0x03,0xa9,
        0xfd,0xc3,0x00,0x91,0xf3,0x03,0x04,0xaa,0xf4,0x03,0x03,0xaa,0xf6,0x03,0x02,0xaa,
        0xf7,0x03,0x01,0xaa,0xf5,0x03,0x00,0xaa,0x31,0x00,0x00,0x94,0xff,0x1a,0x00,0x71,
        0x68,0x02,0x00,0x54,0xa8,0x8a,0x43,0xf9,0x28,0x02,0x00,0xb4,0x08,0x49,0x37,0x8b
    };
    memcpy((void *)target, code, sizeof(code));
    struct gauguin_ca_site site;
    CHECK(gauguin_ca_identify(image, slide, &site));
    CHECK(site.slot == slot && site.vptr == GAUGUIN_CA_VTABLE + slide + 0x10 && (uintptr_t)site.original == target);
    uuid->uuid[0] ^= 1; CHECK(!gauguin_ca_identify(image, slide, &site)); uuid->uuid[0] ^= 1;
    uuid->cmdsize--; CHECK(!gauguin_ca_identify(image, slide, &site)); uuid->cmdsize++;
    header->ncmds = 257; CHECK(!gauguin_ca_identify(image, slide, &site)); header->ncmds = 1;
    header->sizeofcmds++; CHECK(!gauguin_ca_identify(image, slide, &site)); header->sizeofcmds--;
    *slot = 1; CHECK(!gauguin_ca_identify(image, slide, &site)); *slot = target;
    *(uint8_t *)target ^= 1; CHECK(!gauguin_ca_identify(image, slide, &site)); *(uint8_t *)target ^= 1;
    CHECK(!gauguin_ca_identify(image, -1, &site));
    CHECK(!gauguin_ca_identify(image + 1, slide, &site));
    CHECK(mach_vm_deallocate(mach_task_self(), image, size) == KERN_SUCCESS);
    CHECK(!gauguin_ca_identify(image, slide, &site));
    CHECK(!gauguin_ca_locate(&site)); /* Host QuartzCore is not the approved iOS build. */
}
int main(void) {
    identity_tests();
    test_site = (struct gauguin_ca_site){ (void *)allocate(vm_page_size), 0x12340, original };
    reset_slot(); fail_locate = true;
    CHECK(!gauguin_ca_install() && *test_site.slot == (uintptr_t)original && protect_calls == 0);
    reset_slot(); fail_protect = 1;
    CHECK(!gauguin_ca_install() && *test_site.slot == (uintptr_t)original);
    CHECK(protection_at((uintptr_t)test_site.slot) == VM_PROT_READ);
    reset_slot(); fail_protect = 2;
    CHECK(!gauguin_ca_install() && *test_site.slot == (uintptr_t)original && protect_calls == 3);
    CHECK(protection_at((uintptr_t)test_site.slot) == VM_PROT_READ);
    reset_slot(); race_slot = true;
    CHECK(!gauguin_ca_install() && *test_site.slot == 1);
    CHECK(protection_at((uintptr_t)test_site.slot) == VM_PROT_READ);
    reset_slot();
    CHECK(gauguin_ca_install() && *test_site.slot == (uintptr_t)gauguin_ca_uniform);
    CHECK(protection_at((uintptr_t)test_site.slot) == VM_PROT_READ);
    unsigned protects = protect_calls;
    CHECK(gauguin_ca_install() && protect_calls == protects);
    struct fake_context ca[4];
    for (unsigned i = 0; i < 4; i++) { initialize(&ca[i]); contexts[i] = &ca[i].e; }
    float values[20]; for (unsigned i = 0; i < 20; i++) values[i] = i / 10.f;
    set_function(&ca[0], 45);
    invoke(ca[0].bytes, 0, 4, 5, values, &ca[0].e, 45, 20);
    CHECK(gauguin_ca_function(&ca[0].e) == 45 && ca[0].e.ca_draw.given[45] == 20);
    CHECK(!memcmp(values, ca[0].e.ca_draw.values[45], sizeof(values)));
    CHECK(!ca[1].e.ca.given[45]);
    /* Rejected values cannot leave a previously valid matrix marked present. */
    invoke(ca[0].bytes, 0, 4, SIZE_MAX, values, &ca[0].e, 45, 0);
    invoke(ca[0].bytes, 0, 0, 5, values, &ca[0].e, 45, 0);
    invoke(ca[0].bytes, 0, 5, 4, values, &ca[0].e, 45, 0);
    invoke(ca[0].bytes, 0, 4, 0, values, &ca[0].e, 45, 0);
    invoke(ca[0].bytes, 0, 4, 5, NULL, &ca[0].e, 45, 0);
    invoke(ca[0].bytes, 0, 4, 5, (void *)1, &ca[0].e, 45, 0);
    invoke(ca[0].bytes, 1, 4, 5, values, &ca[0].e, 45, 0);
    invoke((void *)1, 0, 4, 5, values, NULL, 0, 0);
    set_function(&ca[0], 255); invoke(ca[0].bytes, 0, 4, 5, values, NULL, 0, 0);
    CHECK(gauguin_ca_function(&ca[0].e) == 90);
    set_function(&ca[0], 45);
    ca[0].bytes[0] ^= 1; invoke(ca[0].bytes, 0, 4, 5, values, NULL, 0, 0);
    CHECK(!ca[0].e.ca.given[45]); ca[0].bytes[0] ^= 1;
    ca[0].e.table[0] = NULL; invoke(ca[0].bytes, 0, 4, 5, values, NULL, 0, 0);
    CHECK(!ca[0].e.ca.given[45]); ca[0].e.table[0] = &ca[0].e;
    struct fake_context native; initialize(&native); set_function(&native, 45);
    invoke(native.bytes, 0, 4, 5, values, NULL, 0, 0);
    CHECK(!native.e.ca.given[45]);
    unsigned before = atomic_load(&calls);
    pthread_t threads[4];
    for (unsigned i = 0; i < 4; i++) CHECK(!pthread_create(&threads[i], NULL, thread_main, &ca[i]));
    for (unsigned i = 0; i < 4; i++) CHECK(!pthread_join(threads[i], NULL));
    CHECK(atomic_load(&calls) == before + 1600);
    /* A destroyed/unmapped CA context yields unknown, never a direct load. */
    ca[0].e.ca.context = 1;
    CHECK(gauguin_ca_function(&ca[0].e) == 90 && !ca[0].e.ca_draw.given[45]);
    CHECK(mach_vm_deallocate(mach_task_self(), (uintptr_t)test_site.slot, vm_page_size) == KERN_SUCCESS);
    printf("PASS %u CA identity, forwarding, COW rollback, context and lifetime assertions; calls=%u\n",
           atomic_load(&assertions), atomic_load(&calls));
    return 0;
}
