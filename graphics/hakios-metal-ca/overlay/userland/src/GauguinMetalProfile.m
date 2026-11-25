/* Offscreen root probe admission. No publication, interposition or UI hooks.
 * Private layouts are checked by name against actual 20H392 metadata. MIT. */
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include "GauguinMetalProfile.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <unistd.h>

bool gauguin_metal_profile_admit(void)
{
    const char *name = getprogname(), *mode = getenv("GAUGUIN_METAL_MODE");
    if (getuid() || geteuid() || !name || strcmp(name, GAUGUIN_METAL_PROBE_NAME) ||
        !mode || strcmp(mode, "offscreen226")) return false;
    char args[1024] = {0}, version[64] = {0};
    size_t n = sizeof(args) - 1, v = sizeof(version) - 1;
    if (sysctlbyname("kern.bootargs", args, &n, NULL, 0) || n >= sizeof(args) ||
        !gauguin_metal_boot_profile(args) ||
        sysctlbyname("kern.osversion", version, &v, NULL, 0) || v >= sizeof(version) ||
        strcmp(version, "20H392")) return false;

    static const struct { const char *cls, *selector, *encoding; } methods[] = {
        {"_MTLDevice", "init", "@16@0:8"},
        {"_MTLDevice", "initLimits", "v16@0:8"},
        {"_MTLDevice", "targetDeviceInfo", "r^{MTLTargetDeviceArch=QI*}16@0:8"},
        {"_MTLCommandQueue", "initWithDevice:descriptor:", "@32@0:8@16@24"},
        {"_MTLCommandBuffer", "initWithQueue:retainedReferences:synchronousDebugMode:", "@32@0:8@16B24B28"},
        {"_MTLCommandBuffer", "commitWithDeadline:", "v24@0:8Q16"},
        {"_MTLCommandEncoder", "initWithCommandBuffer:", "@24@0:8@16"},
        {"_MTLCommandEncoder", "setThreadgroupPackingDisabled:", "v20@0:8B16"},
        {"_MTLRenderPipelineState", "initWithDevice:pipelineStateDescriptor:", "@32@0:8@16@24"},
        {"_MTLComputePipelineState", "initWithDevice:pipelineStateDescriptor:", "@32@0:8@16@24"},
        {"_MTLSamplerState", "initWithDevice:samplerDescriptor:", "@32@0:8@16@24"},
        {"_MTLFunction", "bitcodeData", "@16@0:8"},
    };
    for (size_t i = 0; i < sizeof(methods) / sizeof(methods[0]); i++) {
        Class cls = objc_getClass(methods[i].cls);
        Method method = cls ? class_getInstanceMethod(cls, sel_registerName(methods[i].selector)) : NULL;
        const char *type = method ? method_getTypeEncoding(method) : NULL;
        if (!type || strcmp(type, methods[i].encoding)) {
            fprintf(stderr, "GAUGUIN METAL226 ABI rejected %s %s encoding=%s\n",
                    methods[i].cls, methods[i].selector, type ? type : "<absent>");
            return false;
        }
    }
    static const struct { const char *cls, *name, *type; size_t bytes; } ivars[] = {
        {"_MTLCommandQueue", "_commandBufferSemaphore", "@\"NSObject<OS_dispatch_semaphore>\"", sizeof(void *)},
        {"_MTLCommandBuffer", "_needsCommandBufferSemaphoreSignal", "B", sizeof(BOOL)},
    };
    for (size_t i = 0; i < sizeof(ivars) / sizeof(ivars[0]); i++) {
        Class cls = objc_getClass(ivars[i].cls);
        Ivar ivar = cls ? class_getInstanceVariable(cls, ivars[i].name) : NULL;
        const char *type = ivar ? ivar_getTypeEncoding(ivar) : NULL;
        ptrdiff_t offset = ivar ? ivar_getOffset(ivar) : -1;
        if (!type || strcmp(type, ivars[i].type) || offset < (ptrdiff_t)sizeof(id) ||
            class_getInstanceSize(cls) < ivars[i].bytes ||
            (size_t)offset > class_getInstanceSize(cls) - ivars[i].bytes) {
            fprintf(stderr, "GAUGUIN METAL226 ABI rejected %s.%s type=%s\n",
                    ivars[i].cls, ivars[i].name, type ? type : "<absent>");
            return false;
        }
    }
    if (!objc_getProtocol("MTLDeviceSPI")) return false;
    fprintf(stderr, "GAUGUIN METAL226 admitted OS=20H392 methods=12 ivars=2 root-only no-discovery\n");
    return true;
}

void gauguin_metal_profile_cache(void)
{
    /* Never inherit a writable cache or seed path from an unrelated renderer.
     * The diagnostic uses one root-owned directory and no baked shader seed. */
    unsetenv("HAKIOS_METAL_CACHE");
    unsetenv("HAKIOS_METAL_CACHE_SEED");
    const char *path = "/private/var/tmp/gauguin-metal226-cache";
    struct stat info;
    int rc = mkdir(path, 0700);
    if ((rc == 0 || errno == EEXIST) && lstat(path, &info) == 0 &&
        S_ISDIR(info.st_mode) && info.st_uid == 0 && (info.st_mode & 0777) == 0700 &&
        access(path, W_OK | X_OK) == 0) {
        setenv("HAKIOS_METAL_CACHE", path, 1);
    }
    setenv("HAKIOS_METAL_LISTING", "0", 1);
}
