/* Experimental backboardd admission with actual 20H392 ABI checks. MIT. */
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include "GauguinMetalProfile.h"
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <unistd.h>
#include <dlfcn.h>
#include <mach-o/loader.h>
#include <time.h>
#include <hakios-metal/hakios_metal.h>
#include "GauguinMetalBootstrapWait.h"

static bool desktop_cache_prepare(void);

bool gauguin_metal_profile_admit(void)
{
    char args[1024] = {0}, version[64] = {0};
    size_t n = sizeof(args) - 1, v = sizeof(version) - 1;
    if (sysctlbyname("kern.bootargs", args, &n, NULL, 0) || n >= sizeof(args) ||
        !gauguin_desktop_boot(args) ||
        sysctlbyname("kern.osversion", version, &v, NULL, 0) || v >= sizeof(version) ||
        !gauguin_desktop_identity(getuid(), geteuid(), getprogname(), version)) return false;

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
            fprintf(stderr, "GAUGUIN METAL244 ABI rejected %s %s encoding=%s\n",
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
            fprintf(stderr, "GAUGUIN METAL244 ABI rejected %s.%s type=%s\n",
                    ivars[i].cls, ivars[i].name, type ? type : "<absent>");
            return false;
        }
    }
    if (!objc_getProtocol("MTLDeviceSPI") || !desktop_cache_prepare()) return false;
    fprintf(stderr, "GAUGUIN METAL244 admitted backboardd OS=20H392 methods=12 ivars=2 "
                    "experimental-profile=1 upload=snapshot-only\n");
    return true;
}

static bool desktop_cache_prepare(void)
{
    unsetenv("HAKIOS_METAL_CACHE");
    unsetenv("HAKIOS_METAL_CACHE_SEED");
    const char *path = "/private/var/mobile/Library/Caches/gauguin-metal244";
    struct stat info;
    int rc = mkdir(path, 0700);
    if ((rc != 0 && errno != EEXIST) || lstat(path, &info) ||
        !S_ISDIR(info.st_mode) || info.st_uid != 501 ||
        (info.st_mode & 0777) != 0700 || access(path, W_OK | X_OK)) {
        fprintf(stderr, "GAUGUIN METAL244 refused compositor cache path=%s errno=%d\n", path, errno);
        return false;
    }
    if (setenv("HAKIOS_METAL_CACHE", path, 1) || setenv("HAKIOS_METAL_LISTING", "0", 1)) return false;
    return true;
}

void gauguin_metal_profile_cache(void)
{
    /* Admission already required this cache. Recheck rather than inherit a
     * root-probe cache or seed; a later failure must remain visible in logs. */
    if (!desktop_cache_prepare()) fprintf(stderr, "GAUGUIN METAL244 cache lost after admission\n");
}

bool gauguin_metal_desktop_upload(const void *return_pc, const void *bytes,
                                 size_t length, uint64_t options)
{
    if (!gauguin_desktop_upload_bounds((uintptr_t)bytes, length, options)) return false;
    Dl_info info = {0};
    if (!dladdr(return_pc, &info) || !info.dli_fbase || !info.dli_fname ||
        (uintptr_t)return_pc < (uintptr_t)info.dli_fbase) return false;
    const struct mach_header_64 *header = info.dli_fbase;
    if (header->magic != MH_MAGIC_64 || header->ncmds > 4096 || header->sizeofcmds > (1U << 20)) return false;
    const unsigned char *at = (const unsigned char *)(header + 1);
    const unsigned char *end = at + header->sizeofcmds;
    const unsigned char *uuid = NULL;
    for (uint32_t i = 0; i < header->ncmds; i++) {
        if ((size_t)(end - at) < sizeof(struct load_command)) return false;
        const struct load_command *cmd = (const struct load_command *)at;
        if (cmd->cmdsize < sizeof(*cmd) || cmd->cmdsize > (size_t)(end - at)) return false;
        if (cmd->cmd == LC_UUID) {
            if (uuid || cmd->cmdsize != sizeof(struct uuid_command)) return false;
            uuid = ((const struct uuid_command *)cmd)->uuid;
        }
        at += cmd->cmdsize;
    }
    return at == end && gauguin_desktop_upload_site(info.dli_fname, uuid,
             (uintptr_t)return_pc - (uintptr_t)info.dli_fbase);
}

static bool desktop_wait_clock(void *cookie,uint64_t *out)
{
    (void)cookie;struct timespec t={0};
    if(clock_gettime(CLOCK_MONOTONIC_RAW,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000||
       (uint64_t)t.tv_sec>(UINT64_MAX-(uint64_t)t.tv_nsec)/1000000000)return false;
    *out=(uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;return true;
}
static bool desktop_wait_sleep(void *cookie,uint64_t ns)
{
    (void)cookie;struct timespec pause={(time_t)(ns/1000000000),(long)(ns%1000000000)};
    for(unsigned n=0;n<100;n++) {
        if(!nanosleep(&pause,&pause))return true;
        if(errno!=EINTR)return false;
    }
    return false;
}
static void *desktop_wait_open(void *cookie){(void)cookie;return hakios_metal_open();}
static void desktop_wait_close(void *cookie,void *device){(void)cookie;hakios_metal_close(device);}
void *gauguin_metal_desktop_open(void)
{
    struct gauguin_metal_wait_ops ops={NULL,desktop_wait_clock,desktop_wait_sleep,desktop_wait_open,desktop_wait_close};
    struct gauguin_metal_wait_result result;
    void *device=gauguin_metal_wait_open(&ops,&result);
    fprintf(stderr,"GAUGUIN METAL246 first-open reason=%u attempts=%u elapsed_ns=%llu device=%u\n",
            (unsigned)result.reason,result.attempts,(unsigned long long)result.elapsed_ns,device!=NULL);
    return device;
}
