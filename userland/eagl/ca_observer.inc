/* The one-slot observer is specific to the inventoried 20H392 QuartzCore.
 * It never replaces native GL dispatch, and always forwards exactly once.
 * Callers must obey EAGL's existing one-thread-at-a-time context contract. */
#include <mach/vm_map.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>

#define GAUGUIN_CA_IMAGE UINT64_C(0x188284000)
#define GAUGUIN_CA_VTABLE UINT64_C(0x1d5b2f6e8)
#define GAUGUIN_CA_UNIFORM UINT64_C(0x1884b21ac)
#define GAUGUIN_CA_TABLE_OFFSET 0x7f8u
#define GAUGUIN_CA_UNKNOWN 90u

_Static_assert(sizeof(vm_address_t) == 8 && sizeof(vm_size_t) == 8 &&
               sizeof(unsigned) == 4 && sizeof(size_t) == 8 && sizeof(float) == 4, "20H392 arm64 ABI");

typedef void (*gauguin_ca_uniform_fn)(void *, unsigned, size_t, size_t, const float *);
struct gauguin_ca_site {
    uintptr_t *slot, vptr;
    gauguin_ca_uniform_fn original;
};
static uintptr_t gauguin_ca_vptr;
static gauguin_ca_uniform_fn gauguin_ca_original;
static pthread_mutex_t gauguin_ca_install_lock = PTHREAD_MUTEX_INITIALIZER;
static int gauguin_ca_ready;

static bool
gauguin_ca_read(uintptr_t address, void *out, size_t size)
{
    vm_size_t copied = 0;
    return address && size && address <= UINTPTR_MAX - size &&
        vm_read_overwrite(mach_task_self(), address, size,
                               (vm_address_t)out, &copied) == KERN_SUCCESS && copied == size;
}

/* Also checks the unslid image base and instruction prefix. A UUID alone does
 * not authorize a mismatched address, vtable entry, or function ABI. */
static bool
gauguin_ca_identify(uintptr_t image, intptr_t slide, struct gauguin_ca_site *site)
{
    static const uint8_t uuid[16] = {
        0x9e,0x40,0xb2,0xeb,0x26,0x0c,0x3a,0xf1,0xae,0x45,0xa1,0xa5,0x51,0xa8,0xc1,0xb9
    };
    static const uint8_t code[64] = {
        0xf8,0x5f,0xbc,0xa9,0xf6,0x57,0x01,0xa9,0xf4,0x4f,0x02,0xa9,0xfd,0x7b,0x03,0xa9,
        0xfd,0xc3,0x00,0x91,0xf3,0x03,0x04,0xaa,0xf4,0x03,0x03,0xaa,0xf6,0x03,0x02,0xaa,
        0xf7,0x03,0x01,0xaa,0xf5,0x03,0x00,0xaa,0x31,0x00,0x00,0x94,0xff,0x1a,0x00,0x71,
        0x68,0x02,0x00,0x54,0xa8,0x8a,0x43,0xf9,0x28,0x02,0x00,0xb4,0x08,0x49,0x37,0x8b
    };
    struct mach_header_64 header;
    if (slide < 0 || (uint64_t)slide > UINTPTR_MAX - GAUGUIN_CA_VTABLE - 0x398 ||
        image != GAUGUIN_CA_IMAGE + (uintptr_t)slide ||
        !gauguin_ca_read(image, &header, sizeof(header)) || header.magic != MH_MAGIC_64 ||
        header.cputype != CPU_TYPE_ARM64 || !header.ncmds || header.ncmds > 256 ||
        header.sizeofcmds > 1024 * 1024) return false;
    uintptr_t at = image + sizeof(header), end = at + header.sizeofcmds;
    unsigned matches = 0;
    for (unsigned i = 0; i < header.ncmds; i++) {
        struct load_command command;
        if (at > end || end - at < sizeof(command) ||
            !gauguin_ca_read(at, &command, sizeof(command)) || command.cmdsize < sizeof(command) ||
            command.cmdsize > end - at) return false;
        if (command.cmd == LC_UUID) {
            struct uuid_command identity;
            if (command.cmdsize != sizeof(identity) ||
                !gauguin_ca_read(at, &identity, sizeof(identity)) ||
                memcmp(identity.uuid, uuid, sizeof(uuid))) return false;
            matches++;
        }
        at += command.cmdsize;
    }
    if (at != end || matches != 1) return false;
    uintptr_t slot = GAUGUIN_CA_VTABLE + (uintptr_t)slide + 0x10 + 0x388;
    uintptr_t target, expected = GAUGUIN_CA_UNIFORM + (uintptr_t)slide;
    uint8_t actual[sizeof(code)];
    if (!gauguin_ca_read(slot, &target, sizeof(target)) || target != expected ||
        !gauguin_ca_read(target, actual, sizeof(actual)) || memcmp(actual, code, sizeof(code))) return false;
    *site = (struct gauguin_ca_site){ (uintptr_t *)slot,
        GAUGUIN_CA_VTABLE + (uintptr_t)slide + 0x10, (gauguin_ca_uniform_fn)target };
    return true;
}

static bool
gauguin_ca_locate(struct gauguin_ca_site *site)
{
    for (uint32_t i = 0; i < _dyld_image_count(); i++) {
        const char *name = _dyld_get_image_name(i);
        if (name && !strcmp(name, "/System/Library/Frameworks/QuartzCore.framework/QuartzCore")) {
            return gauguin_ca_identify((uintptr_t)_dyld_get_image_header(i),
                                       _dyld_get_image_vmaddr_slide(i), site);
        }
    }
    return false;
}

/* Reading a whole bounded context snapshot avoids dereferencing a retained CA
 * pointer after its destruction. Require the exact live vptr AND our table.
 * A native context cannot publish values into any of the owned contexts. */
static bool
gauguin_ca_snapshot(uintptr_t context, uintptr_t *table, unsigned *function)
{
    uint8_t bytes[GAUGUIN_CA_TABLE_OFFSET + sizeof(uintptr_t)];
    uintptr_t vptr, object;
    uint32_t type;
    if (!gauguin_ca_read(context, bytes, sizeof(bytes))) return false;
    memcpy(&vptr, bytes, sizeof(vptr));
    memcpy(&object, bytes + 0x10, sizeof(object));
    memcpy(table, bytes + GAUGUIN_CA_TABLE_OFFSET, sizeof(*table));
    if (vptr != __atomic_load_n(&gauguin_ca_vptr, __ATOMIC_ACQUIRE) || !object || object > UINTPTR_MAX - 0x10 ||
        !gauguin_ca_read(object + 0x10, &type, sizeof(type))) return false;
    *function = type & 0xffu;
    return true;
}

static void
gauguin_ca_observe(void *context, unsigned index, size_t components, size_t count,
                   const float *values)
{
    uintptr_t table;
    unsigned function;
    pthread_mutex_lock(&gauguin_context_lock);
    if (gauguin_ca_snapshot((uintptr_t)context, &table, &function)) {
        for (unsigned i = 0; i < sizeof(contexts) / sizeof(contexts[0]); i++) {
            struct eagl *e = contexts[i];
            if (e == NULL || table != (uintptr_t)e->table || e->table[0] != e) continue;
            if (e->ca.context != (uintptr_t)context) {
                memset(&e->ca, 0, sizeof(e->ca));
                e->ca.context = (uintptr_t)context;
            }
            if (function < 90 && index == 0) {
                /* Invalidate on malformed updates; never reuse old uniforms. */
                e->ca.given[function] = 0;
                if (components >= 1 && components <= 4 && count && count <= 20 / components) {
                    float copy[20];
                    size_t numbers = components * count;
                    if (gauguin_ca_read((uintptr_t)values, copy, numbers * sizeof(float))) {
                        if (!e->ca.said[function] || (function_numbers && e->ca.said[function] < 12 &&
                            memcmp(e->ca.values[function], copy, numbers * sizeof(float)))) {
                            char text[256] = "";
                            size_t used = 0;
                            for (size_t n = 0; n < numbers && used < sizeof(text) - 16; n++) {
                                used += (size_t)snprintf(text + used, sizeof(text) - used, " %.3g", (double)copy[n]);
                            }
                            e->ca.said[function]++;
                            say("hakios-gl: CoreAnimation gives its function %u numbers: %zu of %zu:%s owned=1\n",
                                function, count, components, text);
                        }
                        memcpy(e->ca.values[function], copy, numbers * sizeof(float));
                        e->ca.given[function] = (uint8_t)numbers;
                    }
                }
            }
            break;
        }
    }
    pthread_mutex_unlock(&gauguin_context_lock);
}

static void
gauguin_ca_uniform(void *context, unsigned index, size_t components, size_t count, const float *values)
{
    gauguin_ca_uniform_fn original = __atomic_load_n(&gauguin_ca_original, __ATOMIC_ACQUIRE);
    gauguin_ca_observe(context, index, components, count, values);
    original(context, index, components, count, values);
}

/* Consumers read a draw snapshot, never the concurrently observed state.
 * Only the active function and variableDownsample (38) are used by a draw. */
static unsigned
gauguin_ca_function(struct eagl *e)
{
    uintptr_t table;
    unsigned function = GAUGUIN_CA_UNKNOWN;
    pthread_mutex_lock(&gauguin_context_lock);
    if (!e->ca.context || !gauguin_ca_snapshot(e->ca.context, &table, &function) ||
        table != (uintptr_t)e->table || e->table[0] != e || function >= 90) {
        memset(&e->ca, 0, sizeof(e->ca));
        memset(e->ca_draw.given, 0, sizeof(e->ca_draw.given));
        function = GAUGUIN_CA_UNKNOWN;
    } else {
        memcpy(e->ca_draw.values[function], e->ca.values[function], sizeof(e->ca.values[function]));
        e->ca_draw.given[function] = e->ca.given[function];
        memcpy(e->ca_draw.values[38], e->ca.values[38], sizeof(e->ca.values[38]));
        e->ca_draw.given[38] = e->ca.given[38];
    }
    pthread_mutex_unlock(&gauguin_context_lock);
    return function;
}

#ifndef GAUGUIN_CA_LOCATE
#define GAUGUIN_CA_LOCATE gauguin_ca_locate
#endif
#ifndef GAUGUIN_CA_PROTECT
#define GAUGUIN_CA_PROTECT vm_protect
#endif
static int
gauguin_ca_install(void)
{
    pthread_mutex_lock(&gauguin_ca_install_lock);
    if (__atomic_load_n(&gauguin_ca_ready, __ATOMIC_ACQUIRE)) {
        pthread_mutex_unlock(&gauguin_ca_install_lock);
        return 1;
    }
    struct gauguin_ca_site site;
    vm_address_t region;
    vm_size_t extent;
    vm_region_basic_info_data_64_t info;
    mach_msg_type_number_t count = VM_REGION_BASIC_INFO_COUNT_64;
    mach_port_t object = MACH_PORT_NULL;
    int installed = 0;
    if (!GAUGUIN_CA_LOCATE(&site)) goto done;
    region = (vm_address_t)site.slot;
    if (vm_region_64(mach_task_self(), &region, &extent, VM_REGION_BASIC_INFO_64,
                       (vm_region_info_t)&info, &count, &object) != KERN_SUCCESS) goto done;
    if (object != MACH_PORT_NULL) mach_port_deallocate(mach_task_self(), object);
    if ((info.protection & VM_PROT_READ) == 0 || (info.protection & (VM_PROT_WRITE | VM_PROT_EXECUTE)) ||
        region > (uintptr_t)site.slot || (uintptr_t)site.slot - region > extent ||
        extent - ((uintptr_t)site.slot - region) < sizeof(uintptr_t)) goto done;
    vm_address_t page = (uintptr_t)site.slot & ~((uintptr_t)vm_page_size - 1);
    uintptr_t expected = (uintptr_t)site.original;
    if (GAUGUIN_CA_PROTECT(mach_task_self(), page, vm_page_size, FALSE,
                           VM_PROT_READ | VM_PROT_WRITE | VM_PROT_COPY) != KERN_SUCCESS) goto done;
    __atomic_store_n(&gauguin_ca_vptr, site.vptr, __ATOMIC_RELEASE);
    __atomic_store_n(&gauguin_ca_original, site.original, __ATOMIC_RELEASE);
    bool swapped = __atomic_compare_exchange_n(site.slot, &expected, (uintptr_t)gauguin_ca_uniform,
                                               false, __ATOMIC_RELEASE, __ATOMIC_ACQUIRE);
    if (GAUGUIN_CA_PROTECT(mach_task_self(), page, vm_page_size, FALSE, info.protection) != KERN_SUCCESS) {
        if (swapped) {
            expected = (uintptr_t)gauguin_ca_uniform;
            (void)__atomic_compare_exchange_n(site.slot, &expected, (uintptr_t)site.original,
                                              false, __ATOMIC_RELEASE, __ATOMIC_ACQUIRE);
        }
        kern_return_t restored = GAUGUIN_CA_PROTECT(mach_task_self(), page, vm_page_size, FALSE, info.protection);
        say("GAUGUIN CA protection restore failed; hook rolled back restore=%d\n", restored);
        goto done;
    }
    if (swapped) {
        __atomic_store_n(&gauguin_ca_ready, 1, __ATOMIC_RELEASE);
        say("GAUGUIN CA uniform observer installed build=20H392 offset=388\n");
        installed = 1;
    }
done:
    if (!installed) say("GAUGUIN CA uniform observer rejected; native EAGL retained\n");
    pthread_mutex_unlock(&gauguin_ca_install_lock);
    return installed;
}
