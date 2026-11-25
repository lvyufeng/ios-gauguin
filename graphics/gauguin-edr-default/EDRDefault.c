/* Opt-in, process-private use of QuartzCore's existing optional-EDR fallback.
 * No Apple code bytes are included or modified. See the actual-OS contract. */
#include "EDRDefaultCore.h"
#include "EDRDefaultContract.h"
#include <CommonCrypto/CommonDigest.h>
#include <dispatch/dispatch.h>
#include <mach/mach.h>
#include <mach/vm_map.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sysctl.h>
#include <unistd.h>

_Static_assert(sizeof(vm_address_t) == 8 && sizeof(vm_size_t) == 8 &&
               sizeof(uintptr_t) == 8 && sizeof(dispatch_once_t) == 8,
               "requires the observed LP64 VM and once ABI");

struct geq_image {
    const struct mach_header_64 *header;
    uintptr_t slide;
};
struct geq_page {
    vm_address_t address;
    vm_size_t size;
    vm_prot_t protection;
};
enum { GEQ_MAX_SUBMAP_DEPTH = 8 };
struct geq_leaf {
    vm_address_t begin;
    vm_size_t length;
    natural_t depth;
    mach_msg_type_number_t count;
    kern_return_t status;
    vm_region_submap_short_info_data_64_t info;
};
_Static_assert(VM_REGION_SUBMAP_SHORT_INFO_COUNT_64 == 12,
               "requires the observed short region ABI");

static bool geq_leaf(uintptr_t address, size_t size, vm_prot_t required,
                     struct geq_leaf *leaf)
{
    *leaf = (struct geq_leaf){ .begin = address, .depth = GEQ_MAX_SUBMAP_DEPTH,
        .count = VM_REGION_SUBMAP_SHORT_INFO_COUNT_64, .status = KERN_INVALID_ARGUMENT };
    if (!address || !size || size > UINTPTR_MAX - address) return false;
    /* BASIC reports the outer read-only shared-cache submap. Request its leaf
     * in one bounded RPC; SHORT avoids scanning resident-page statistics. */
    leaf->status = vm_region_recurse_64(mach_task_self(), &leaf->begin,
        &leaf->length, &leaf->depth, (vm_region_recurse_info_t)&leaf->info, &leaf->count);
    return leaf->status == KERN_SUCCESS &&
        leaf->count == VM_REGION_SUBMAP_SHORT_INFO_COUNT_64 &&
        leaf->depth <= GEQ_MAX_SUBMAP_DEPTH && !leaf->info.is_submap &&
        leaf->begin <= address && leaf->length <= UINTPTR_MAX - leaf->begin &&
        address + size <= leaf->begin + leaf->length &&
        (leaf->info.protection & required) == required;
}

static bool geq_region(uintptr_t address, size_t size, vm_prot_t required,
                       struct geq_page *page)
{
    struct geq_leaf leaf;
    if (!geq_leaf(address, size, required, &leaf)) return false;
    if (page) {
        vm_size_t unit = vm_page_size;
        if (unit < 4096 || unit > 65536 || (unit & (unit - 1)) ||
            (leaf.info.protection & VM_PROT_EXECUTE)) return false;
        uintptr_t start = address & ~(uintptr_t)(unit - 1);
        if (start < leaf.begin || start > UINTPTR_MAX - unit ||
            start + unit > leaf.begin + leaf.length || address + size > start + unit)
            return false;
        page->address = start;
        page->size = unit;
        page->protection = leaf.info.protection;
    }
    return true;
}

static bool geq_image(const char *path, const unsigned char uuid[16],
                      struct geq_image *result)
{
    unsigned matches = 0;
    uint32_t count = _dyld_image_count();
    if (count > 4096) return false;
    for (uint32_t i = 0; i < count; ++i) {
        const char *name = _dyld_get_image_name(i);
        if (!name || strcmp(name, path)) continue;
        if (++matches != 1) return false;
        const struct mach_header_64 *h = (const void *)_dyld_get_image_header(i);
        intptr_t slide = _dyld_get_image_vmaddr_slide(i);
        if (slide < 0 || (uint64_t)slide > UINT64_C(0x100000000) ||
            !geq_region((uintptr_t)h, sizeof(*h), VM_PROT_READ, NULL) ||
            h->magic != MH_MAGIC_64 || h->cputype != CPU_TYPE_ARM64 ||
            h->filetype != MH_DYLIB || h->ncmds > 512 || h->sizeofcmds > 65536 ||
            !geq_region((uintptr_t)h, sizeof(*h) + h->sizeofcmds, VM_PROT_READ, NULL))
            return false;
        size_t at = 0;
        unsigned uuids = 0;
        const unsigned char *commands = (const void *)(h + 1);
        for (uint32_t j = 0; j < h->ncmds; ++j) {
            if (at > h->sizeofcmds || h->sizeofcmds - at < sizeof(struct load_command))
                return false;
            const struct load_command *cmd = (const void *)(commands + at);
            if (cmd->cmdsize < sizeof(*cmd) || cmd->cmdsize > h->sizeofcmds - at)
                return false;
            if (cmd->cmd == LC_UUID) {
                if (cmd->cmdsize != sizeof(struct uuid_command) || ++uuids != 1 ||
                    memcmp(((const struct uuid_command *)cmd)->uuid, uuid, 16))
                    return false;
            }
            at += cmd->cmdsize;
        }
        if (at != h->sizeofcmds || uuids != 1) return false;
        result->header = h;
        result->slide = (uintptr_t)slide;
    }
    return matches == 1;
}

static bool geq_digest(uintptr_t address, size_t length, const unsigned char digest[32],
                       const char *label)
{
    unsigned char actual[CC_SHA256_DIGEST_LENGTH] = {0};
    struct geq_leaf leaf;
    bool mapped = geq_leaf(address, length, VM_PROT_READ | VM_PROT_EXECUTE, &leaf);
    bool hashed = mapped && length <= UINT32_MAX &&
        CC_SHA256((const void *)address, (CC_LONG)length, actual);
    bool match = hashed && !memcmp(actual, digest, sizeof(actual));
    if (label) {
        static const char hex[] = "0123456789abcdef";
        char text[65];
        for (size_t i = 0; i < sizeof(actual); ++i) {
            text[i*2] = hex[actual[i] >> 4]; text[i*2+1] = hex[actual[i] & 15];
        }
        text[64] = 0;
        fprintf(stderr, "GAUGUIN EDR320: code-check name=%s region=%u kr=%d count=%u depth=%u protection=%d hashed=%u hash=%u sha256=%s\n",
                label, mapped, leaf.status, leaf.count, leaf.depth, leaf.info.protection,
                hashed, match, text);
        /* Only these two fixed code spans can be requested by the constructor.
         * Preserve bounded mismatch evidence without reading a rejected map. */
        if (hashed && !match && length <= GEQ_CALLBACK_BYTES) {
            char bytes[GEQ_CALLBACK_BYTES*2+1];
            const unsigned char *code = (const void *)address;
            for (size_t i = 0; i < length; ++i) {
                bytes[i*2] = hex[code[i] >> 4]; bytes[i*2+1] = hex[code[i] & 15];
            }
            bytes[length*2] = 0;
            fprintf(stderr, "GAUGUIN EDR320: code-mismatch name=%s bytes=%zu hex=%s\n", label, length, bytes);
        }
        fflush(stderr);
    }
    return match;
}

static int geq_writable_copy(void *context)
{
    struct geq_page *page = context;
    return vm_protect(mach_task_self(), page->address, page->size, false,
                     page->protection | VM_PROT_WRITE | VM_PROT_COPY);
}
static int geq_restore(void *context)
{
    struct geq_page *page = context;
    return vm_protect(mach_task_self(), page->address, page->size, false,
                     page->protection);
}
static bool geq_sysctl(const char *name, char *value, size_t capacity)
{
    size_t size = capacity - 1;
    return sysctlbyname(name, value, &size, NULL, 0) == 0 && size < capacity &&
           memchr(value, 0, capacity) != NULL;
}

static bool geq_initialize_once(dispatch_once_t *once, dispatch_block_t block)
{
    uintptr_t before = (uintptr_t)__atomic_load_n(once, __ATOMIC_ACQUIRE);
    bool available = geq_once_available(before);
    fprintf(stderr, "GAUGUIN EDR320: once before=0x%016llx eligible=%u\n",
            (unsigned long long)before, available);
    fflush(stderr);
    if (!available) return false;
    /* Use the system API for acquire/completion ordering. Never overwrite its
     * predicate, invoke the block directly, or wait on an observed busy owner. */
    dispatch_once(once, block);
    uintptr_t after = (uintptr_t)__atomic_load_n(once, __ATOMIC_ACQUIRE);
    bool complete = geq_once_complete(after);
    fprintf(stderr, "GAUGUIN EDR320: once after=0x%016llx complete=%u\n",
            (unsigned long long)after, complete);
    fflush(stderr);
    return complete;
}

__attribute__((constructor)) static void geq_install(void)
{
    char os[64] = {0}, kernel[512] = {0}, args[1024] = {0};
    const char *mode = getenv("GAUGUIN_EAGL_MODE");
    if (!mode || strcmp(mode, "edr-default318")) return;
    bool os_ok = geq_sysctl("kern.osversion", os, sizeof(os));
    bool kernel_ok = geq_sysctl("kern.version", kernel, sizeof(kernel));
    bool args_ok = geq_sysctl("kern.bootargs", args, sizeof(args));
    bool scope_ok = os_ok && kernel_ok && args_ok &&
        geq_scope(getprogname(), getuid(), geteuid(), os, kernel, args, mode);
    fprintf(stderr, "GAUGUIN EDR320: entry os_read=%u kernel_read=%u args_read=%u scope=%u\n",
            os_ok, kernel_ok, args_ok, scope_ok);
    fflush(stderr);
    if (!scope_ok) return;
    const char *reason = "quartzcore-image";
    struct geq_image qc = {0}, edr = {0};
    struct geq_page page = {0};
    if (!geq_image(GEQ_QC_PATH, geq_qc_uuid, &qc) ||
        (uintptr_t)qc.header != GEQ_QC_BASE + qc.slide) goto refused;
    reason = "original-code";
    bool initializer_ok = geq_digest(GEQ_INITIALIZER + qc.slide, GEQ_INITIALIZER_BYTES,
                                     geq_initializer_sha, "initializer");
    bool callback_ok = geq_digest(GEQ_CALLBACK + qc.slide, GEQ_CALLBACK_BYTES,
                                  geq_callback_sha, "callback");
    if (!initializer_ok || !callback_ok) goto refused;
    uintptr_t *slot = (void *)(GEQ_SLOT + qc.slide);
    dispatch_once_t *once = (void *)(GEQ_ONCE + qc.slide);
    struct { uintptr_t isa; uint32_t flags, reserved; uintptr_t invoke, descriptor; }
        *block = (void *)(GEQ_BLOCK + qc.slide);
    reason = "once-mapping";
    if (!geq_region((uintptr_t)once, sizeof(*once), VM_PROT_READ | VM_PROT_WRITE, NULL)) goto refused;
    reason = "block-mapping";
    if (!geq_region((uintptr_t)block, sizeof(*block), VM_PROT_READ, NULL)) goto refused;
    reason = "block-contract";
    if (!(block->flags & (1U << 28)) || block->invoke != GEQ_INITIALIZER + qc.slide) goto refused;
    reason = "initial-slot-mapping";
    if (!geq_region((uintptr_t)slot, sizeof(*slot), VM_PROT_READ, &page)) goto refused;
    reason = "once-abi-image";
    struct geq_image dispatch = {0};
    if (!geq_image(GEQ_DISPATCH_PATH, geq_dispatch_uuid, &dispatch) ||
        dispatch.slide != qc.slide) goto refused;
    reason = "once-abi-code";
    unsigned checked = 0;
    for (size_t i = 0; i < sizeof(geq_once_functions)/sizeof(geq_once_functions[0]); ++i) {
        const struct geq_function_contract *f = &geq_once_functions[i];
        if (!geq_digest(f->address + dispatch.slide, f->bytes, f->digest, NULL)) break;
        ++checked;
    }
    fprintf(stderr, "GAUGUIN EDR320: once-abi checks=%u passed=%u\n", checked, checked == 6);
    fflush(stderr);
    if (checked != 6) goto refused;
    reason = "initializer-state";
    if (!geq_initialize_once(once, (dispatch_block_t)block)) goto refused;
    reason = "provider-image";
    if (!geq_image(GEQ_EDR_PATH, geq_edr_uuid, &edr) || edr.slide != qc.slide)
        goto refused;
    uintptr_t original = GEQ_PROVIDER + edr.slide;
    reason = "provider-pointer";
    if (!geq_region(original, 4, VM_PROT_READ | VM_PROT_EXECUTE, NULL) ||
        __atomic_load_n(slot, __ATOMIC_ACQUIRE) != original) goto refused;
    /* Initialization may have materialized a private writable data page. */
    reason = "slot-mapping";
    if (!geq_region((uintptr_t)slot, sizeof(*slot), VM_PROT_READ, &page)) goto refused;
    struct geq_memory_ops ops = { &page, geq_writable_copy, geq_restore };
    enum geq_result result = geq_clear_optional(slot, original, &ops);
    fprintf(stderr, "GAUGUIN EDR320: optional-query result=%d slot_null=%u bytes=8 code_writes=0\n",
            result, __atomic_load_n(slot, __ATOMIC_ACQUIRE) == 0);
    fflush(stderr);
    return;
refused:
    fprintf(stderr, "GAUGUIN EDR320: refused reason=%s\n", reason);
    fflush(stderr);
}
