#ifndef GAUGUIN_EDR_DEFAULT_CORE_H
#define GAUGUIN_EDR_DEFAULT_CORE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>

/* Valid only after the fixed20H392 libdispatch code/UUID contract is checked.
 * A generation state is already initialized; it need not have become -1 yet. */
static inline bool geq_once_complete(uintptr_t state)
{
    return state == UINTPTR_MAX || (state & 3) == 2;
}
static inline bool geq_once_available(uintptr_t state)
{
    return state == 0 || geq_once_complete(state);
}

/* Q337 requires the fixed kernel, mapping opt-in and native565 profile. */
static inline bool geq_scope(const char *program, unsigned uid, unsigned euid,
                            const char *os, const char *kernel, const char *args,
                            const char *mode)
{
    if (!program || strcmp(program, "backboardd") || uid != 501 || euid != 501 ||
        !os || strcmp(os, "20H392") || !kernel ||
        !strstr(kernel, "xnu-local337-d846caeab5924ac49b8ac8802e070e95") || !args ||
        !mode || strcmp(mode, "edr-default318"))
        return false;
    unsigned metal = 0, sampler = 0, mapping = 0, profile = 0;
    bool valid = true;
    for (const char *p = args; *p;) {
        while (*p == ' ' || *p == '\t' || *p == '\n') ++p;
        const char *start = p;
        while (*p && *p != ' ' && *p != '\t' && *p != '\n') ++p;
        size_t length = (size_t)(p - start);
        if (length >= 4 && !memcmp(start, "gmt=", 4)) {
            ++metal;
            valid = valid && length == 5 && !memcmp(start, "gmt=2", 5);
        }
        if (length >= 4 && !memcmp(start, "gsp=", 4)) {
            ++sampler;
            valid = valid && length == 7 && !memcmp(start, "gsp=328", 7);
        }
        if (length >= 4 && !memcmp(start, "gpf=", 4)) {
            ++profile;
            valid = valid && length == 5 && !memcmp(start, "gpf=4", 5);
        }
        if (length >= 12 && !memcmp(start, "sweetgpumap=", 12)) {
            ++mapping;
            valid = valid && length == 13 && !memcmp(start, "sweetgpumap=1", 13);
        }
    }
    return metal == 1 && sampler == 1 && mapping == 1 && profile == 1 && valid;
}

enum geq_result {
    GEQ_INSTALLED = 1,
    GEQ_INVALID = -1,
    GEQ_ORIGINAL_MISMATCH = -2,
    GEQ_PROTECT_FAILED = -3,
    GEQ_RACE = -4,
    GEQ_RESTORE_FAILED_WITHOUT_WRITE = -5,
    GEQ_ROLLED_BACK = -6,
    GEQ_ROLLBACK_INCOMPLETE = -7
};

struct geq_memory_ops {
    void *context;
    int (*writable_copy)(void *);
    int (*restore_protection)(void *);
};

/* Only an aligned, verified optional function pointer is changed. Failure to
 * restore protection rolls back our own NULL value without overwriting a race. */
static inline enum geq_result geq_clear_optional(uintptr_t *slot, uintptr_t original,
                                               const struct geq_memory_ops *ops)
{
    if (!slot || ((uintptr_t)slot & (sizeof(uintptr_t) - 1)) || !original || !ops ||
        !ops->writable_copy || !ops->restore_protection)
        return GEQ_INVALID;
    if (__atomic_load_n(slot, __ATOMIC_ACQUIRE) != original)
        return GEQ_ORIGINAL_MISMATCH;
    if (ops->writable_copy(ops->context)) return GEQ_PROTECT_FAILED;
    uintptr_t expected = original;
    if (!__atomic_compare_exchange_n(slot, &expected, 0, false,
                                    __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE))
        return ops->restore_protection(ops->context) ?
            GEQ_RESTORE_FAILED_WITHOUT_WRITE : GEQ_RACE;
    if (!ops->restore_protection(ops->context)) return GEQ_INSTALLED;
    expected = 0;
    bool rolled_back = __atomic_compare_exchange_n(slot, &expected, original, false,
                                                   __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE);
    int restored = ops->restore_protection(ops->context);
    return rolled_back && !restored ? GEQ_ROLLED_BACK : GEQ_ROLLBACK_INCOMPLETE;
}
#endif
