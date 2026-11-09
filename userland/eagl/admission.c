/* Read-only EAGL admission diagnostics. No GPU client or renderer changes.
 * MIT; see LICENSE.upstream for the HakiOS sources used by the separate bridge.
 */
#include <IOKit/IOKitLib.h>
#include <mach/mach.h>
#include <objc/runtime.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysctl.h>
#include <unistd.h>

extern int memorystatus_control(uint32_t, int32_t, uint32_t, void *, size_t);
struct memlimit {
    int32_t active;
    uint32_t active_attr;
    int32_t inactive;
    uint32_t inactive_attr;
};
_Static_assert(sizeof(struct memlimit) == 16, "XNU GET8 wire layout");

/* This same function gates the compiled bridge. It deliberately never admits
 * method replacement: compositor access and startup ordering are later stages.
 * There is no environment value or boot argument which enables rendering here.
 */
int
gauguin_eagl_admit(void)
{
    static const struct { const char *name, *type; } expected[] = {
        { "initWithAPI:properties:", "@32@0:8Q16@24" },
        { "API", "Q16@0:8" },
        { "sharegroup", "@16@0:8" },
        { "setParameter:to:", "Q28@0:8I16^i20" },
        { "getMacroContextPrivate", "^{EAGLMacroContext=}16@0:8" },
        { "texImageIOSurface:target:internalFormat:width:height:format:type:plane:invert:",
          "B72@0:8^{__IOSurface=}16Q24Q32I40I44Q48Q56I64B68" },
        { "attachImage:toCoreSurface:invertedRender:", "B36@0:8Q16^{__IOSurface=}24B32" },
        { "dealloc", "v16@0:8" },
    };
    const char *program = getprogname(), *mode = getenv("GAUGUIN_EAGL_MODE");
    if (!program || strcmp(program, "backboardd") || getuid() != 501 || geteuid() != 501)
        return 0;
    fprintf(stderr, "GAUGUIN EAGL186 begin pid=%d uid=%u euid=%u mode=%s\n",
        getpid(), getuid(), geteuid(), mode ? mode : "admission");
    char version[64] = {0}; size_t bytes = sizeof(version) - 1;
    int version_rc = sysctlbyname("kern.osversion", version, &bytes, NULL, 0);
    fprintf(stderr, "GAUGUIN EAGL186 osversion rc=%d value=%s\n", version_rc, version);
    Class cls = objc_getClass("EAGLContext");
    unsigned matched = 0;
    for (unsigned i = 0; i < sizeof(expected) / sizeof(expected[0]); i++) {
        Method method = cls ? class_getInstanceMethod(cls, sel_registerName(expected[i].name)) : NULL;
        const char *type = method ? method_getTypeEncoding(method) : NULL;
        int same = type && strcmp(type, expected[i].type) == 0;
        matched += same;
        fprintf(stderr, "GAUGUIN EAGL186 method=%s encoding=%s match=%d\n",
            expected[i].name, type ? type : "<absent>", same);
    }
    struct memlimit limits = {0}; errno = 0;
    int limit_rc = memorystatus_control(8, getpid(), 0, &limits, sizeof(limits));
    int limit_errno = limit_rc ? errno : 0;
    task_vm_info_data_t vm = {0}; mach_msg_type_number_t count = TASK_VM_INFO_REV1_COUNT;
    kern_return_t vm_rc = task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&vm, &count);
    int vm_valid = vm_rc == KERN_SUCCESS && count >= TASK_VM_INFO_REV1_COUNT;
    fprintf(stderr, "GAUGUIN EAGL186 memory get8_rc=%d errno=%d active_mb=%d active_attr=%u inactive_mb=%d inactive_attr=%u vm_rc=%d vm_valid=%d footprint_bytes=%llu\n",
        limit_rc, limit_errno, limits.active, limits.active_attr, limits.inactive, limits.inactive_attr,
        vm_rc, vm_valid, (unsigned long long)(vm_valid ? vm.phys_footprint : 0));
    io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("HakiosGPU"));
    fprintf(stderr, "GAUGUIN EAGL186 finish methods=%u/8 gpu_service_present=%d hooks=0 gpu_opens=0 rendering=disabled\n",
        matched, service != IO_OBJECT_NULL);
    if (service) IOObjectRelease(service);
    fflush(stderr);
    return 0;
}

#if defined(GAUGUIN_EAGL_ADMISSION_ONLY)
#if defined(GAUGUIN_EAGL_PILOT)
void gauguin_eagl_start_pilot(void);
#endif

__attribute__((constructor)) static void admission_install(void)
{
    (void)gauguin_eagl_admit();
#if defined(GAUGUIN_EAGL_PILOT)
    gauguin_eagl_start_pilot();
#endif
}
#endif
