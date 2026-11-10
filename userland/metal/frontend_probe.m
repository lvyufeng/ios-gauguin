/* SPDX-License-Identifier: MIT
 * Finite MTL-object/format/IOSurface diagnostic. No discovery or UI takeover.
 * Shader pipelines, CA variants and presentation are separate qualifications.
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#import <IOSurface/IOSurfaceRef.h>
#import <objc/message.h>
#import <objc/runtime.h>
#include <IOKit/IOKitLib.h>
#include <CommonCrypto/CommonDigest.h>
#include <dispatch/dispatch.h>
#include <errno.h>
#include <fcntl.h>
#include <mach/mach.h>
#include <stdatomic.h>
#include <stdio.h>
#include <spawn.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <time.h>
#include <unistd.h>
#include "GauguinMetalProfile.h"
#include "probe_boot.h"

#ifndef GAUGUIN_METAL_FRONTEND_BUILD
#error A pinned frontend build identity is required
#endif

enum { WIDTH = 64, HEIGHT = 64, WORDS = WIDTH * HEIGHT, STRIDE = WIDTH * 4 };
static const char *receipt_prefix = "GAUGUIN METAL226 ";
static unsigned submissions;
static _Atomic unsigned callbacks;
extern int memorystatus_control(uint32_t, int32_t, uint32_t, void *, size_t);
/* XNU libsyscall/wrappers/spawn/spawn_private.h, available since iOS9.
 * Keep the existing128MiB hard contract when replacing the diagnostic image. */
extern int posix_spawnattr_setjetsam_ext(posix_spawnattr_t *, short, int, int, int);
extern char **environ;
struct limits { int32_t active; uint32_t active_attr; int32_t inactive; uint32_t inactive_attr; };
_Static_assert(sizeof(struct limits) == 16, "GET8 wire layout");
struct priority_entry { int32_t pid; int32_t priority; uint64_t user_data; int32_t limit; uint32_t state; };
_Static_assert(sizeof(struct priority_entry) == 24, "GET1 single-pid wire layout");

__attribute__((noreturn)) static void fail(const char *phase, const char *why)
{
    fprintf(stderr, "%sFAIL phase=%s why=%.400s\n", receipt_prefix, phase, why ? why : "unknown");
    fflush(NULL);
    /* A failed DMA fence is still the kernel client's responsibility. */
    _Exit(1);
}
static void check(bool ok, const char *phase, const char *why) { if (!ok) fail(phase, why); }
static void receipt(const char *format, ...) __attribute__((format(printf,1,2)));
static void receipt(const char *format, ...)
{
    va_list args; va_start(args,format);fputs(receipt_prefix,stdout);vprintf(format,args);va_end(args);
}

static void legacy_gles_probe(void)
{
    /* Only the exact retained, qualified binary may supply the eight-fence
     * handoff expected by the existing compositor worker. No GPU is opened
     * here, and the old executable owns its original90s delay and cleanup. */
    int fd = open(GAUGUIN_LEGACY_PROBE_PATH, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    struct stat st;
    check(fd >= 0 && fstat(fd, &st) == 0 && gauguin_legacy_probe_metadata_ok(&st),
          "GLES-baseline", "retained probe metadata");
    unsigned char *data = malloc(GAUGUIN_LEGACY_PROBE_BYTES), digest[CC_SHA256_DIGEST_LENGTH];
    check(data != NULL, "GLES-baseline", "bounded hash allocation");
    size_t at = 0;
    while (at < GAUGUIN_LEGACY_PROBE_BYTES) {
        ssize_t n = read(fd, data + at, GAUGUIN_LEGACY_PROBE_BYTES - at);
        if (n < 0 && errno == EINTR) continue;
        check(n > 0, "GLES-baseline", "retained probe read");
        at += (size_t)n;
    }
    check(CC_SHA256(data, GAUGUIN_LEGACY_PROBE_BYTES, digest) != NULL &&
          !memcmp(digest, gauguin_legacy_probe_sha256, sizeof(digest)),
          "GLES-baseline", "retained probe identity");
    free(data); check(close(fd) == 0, "GLES-baseline", "probe fd close");
    /* A plain execv reached223 with active/inactive=-1 and nonfatal attributes
     * in the physical mode2 control. Explicit SETEXEC spawn attributes carry
     * both128MiB fatal limits into the replacement task, without creating a
     * second GPU owner. Preserve the current effective jetsam band. */
    struct priority_entry priority = {0}; struct limits before = {0};
    check(memorystatus_control(1, getpid(), 0, &priority, sizeof(priority)) == (int)sizeof(priority) &&
          priority.pid == getpid() && priority.priority >= 0,
          "GLES-baseline", "self priority query");
    check(memorystatus_control(8, getpid(), 0, &before, sizeof(before)) == 0,
          "GLES-baseline", "pre-SETEXEC limits query");
    posix_spawnattr_t attr;
    check(posix_spawnattr_init(&attr) == 0, "GLES-baseline", "spawn attributes");
    check(posix_spawnattr_setflags(&attr, POSIX_SPAWN_SETEXEC) == 0,
          "GLES-baseline", "SETEXEC attributes");
    /* spawn_internal.h: ACTIVE_FATAL0x04 | INACTIVE_FATAL0x08. Do not use
     * USE_EFFECTIVE_PRIORITY: XNU can return EALREADY before updating limits
     * for this already spawned process (memorystatus_update). */
    check(posix_spawnattr_setjetsam_ext(&attr, 0x0c, priority.priority, 128, 128) == 0,
          "GLES-baseline", "finite hard limits on replacement image");
    fprintf(stderr, "GAUGUIN METAL loader exact-mode2 SETEXEC qualified223 active=128 inactive=128 hard=1 priority=%d before_active=%d before_inactive=%d\n",
            priority.priority, before.active, before.inactive);
    fflush(NULL);
    char *const argv[] = {GAUGUIN_LEGACY_PROBE_PATH, "--metal223", NULL};
    int rc = posix_spawn(NULL, GAUGUIN_LEGACY_PROBE_PATH, NULL, &attr, argv, environ);
    (void)posix_spawnattr_destroy(&attr);
    /* Successful SETEXEC replaces this image and never returns here. */
    fail("GLES-baseline", rc ? "retained probe SETEXEC failed" : "SETEXEC unexpectedly returned");
}
static uint64_t now_ns(void)
{
    struct timespec t = {0};
    check(clock_gettime(CLOCK_MONOTONIC_RAW, &t) == 0 && t.tv_sec >= 0, "clock", "monotonic read");
    return (uint64_t)t.tv_sec * 1000000000 + (uint64_t)t.tv_nsec;
}
static void memory(const char *phase)
{
    struct limits m = {0};
    task_vm_info_data_t vm = {0}; mach_msg_type_number_t count = TASK_VM_INFO_REV1_COUNT;
    check(memorystatus_control(8, getpid(), 0, &m, sizeof(m)) == 0, phase, "GET8");
    check(task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&vm, &count) == KERN_SUCCESS &&
          count >= TASK_VM_INFO_REV1_COUNT, phase, "VM footprint");
    check(m.active == 128 && m.inactive == 128 && m.active_attr == 1 && m.inactive_attr == 1 &&
          vm.phys_footprint && vm.phys_footprint <= (128ULL << 20), phase, "128MiB hard-limit contract");
    receipt("memory phase=%s active=128 inactive=128 hard=1 footprint=%llu\n",
           phase, (unsigned long long)vm.phys_footprint);
}
static void trusted_file(NSString *path)
{
    struct stat st;
    check(lstat([path fileSystemRepresentation], &st) == 0 && S_ISREG(st.st_mode) &&
          st.st_uid == 0 && !(st.st_mode & (S_IWGRP | S_IWOTH)), "bundle", "root-owned regular binary required");
}
static void finish(id<MTLCommandBuffer> cb, const char *phase)
{
    check(cb != nil, phase, "command buffer missing");
    dispatch_semaphore_t done = dispatch_semaphore_create(0);
    check(done != NULL, phase, "completion semaphore");
    [cb addCompletedHandler:^(id<MTLCommandBuffer> completed) {
        check([completed status] == MTLCommandBufferStatusCompleted && [completed error] == nil,
              phase, "completion handler status");
        atomic_fetch_add(&callbacks, 1);
        dispatch_semaphore_signal(done);
    }];
    [cb commit];
    [cb waitUntilCompleted];
    check(dispatch_semaphore_wait(done, dispatch_time(DISPATCH_TIME_NOW, 5LL * NSEC_PER_SEC)) == 0,
          phase, "completion callback timeout");
    dispatch_release(done);
    check([cb status] == MTLCommandBufferStatusCompleted && [cb error] == nil, phase, "command buffer failed");
    ++submissions;
    check(atomic_load(&callbacks) == submissions, phase, "one completion callback per command buffer");
}
static id<MTLTexture> texture(id<MTLDevice> device, MTLPixelFormat format)
{
    MTLTextureDescriptor *d = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:format width:WIDTH height:HEIGHT mipmapped:NO];
    d.storageMode = MTLStorageModeShared; d.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    id<MTLTexture> t = [device newTextureWithDescriptor:d];
    check(t != nil, "texture", "allocation refused");
    return t;
}
static uint64_t verify_words(const uint32_t *got, const uint32_t *want, const char *phase)
{
    uint64_t hash = 14695981039346656037ULL;
    for (unsigned i = 0; i < WORDS; i++) {
        if (got[i] != want[i]) {
            char reason[128]; snprintf(reason, sizeof(reason), "pixel=%u actual=%08x expected=%08x", i, got[i], want[i]);
            fail(phase, reason);
        }
        for (unsigned j = 0; j < 4; j++) hash = (hash ^ (uint8_t)(got[i] >> (8 * j))) * 1099511628211ULL;
    }
    receipt("pixels phase=%s words=4096 hash=%016llx PASS\n", phase, (unsigned long long)hash);
    return hash;
}
static void verify_texture(id<MTLTexture> target, const uint32_t *want, const char *phase)
{
    uint32_t got[WORDS]; memset(got, 0xa5, sizeof(got));
    [target getBytes:got bytesPerRow:STRIDE fromRegion:MTLRegionMake2D(0, 0, WIDTH, HEIGHT) mipmapLevel:0];
    verify_words(got, want, phase);
}
static void clear(id<MTLCommandQueue> queue, id<MTLTexture> target, MTLClearColor color, const char *phase)
{
    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = target;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = color;
    id<MTLCommandBuffer> cb = [queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [cb renderCommandEncoderWithDescriptor:pass];
    check(encoder != nil, phase, "render encoder missing");
    [encoder endEncoding];
    finish(cb, phase);
}
static void formats(id<MTLDevice> device, id<MTLCommandQueue> queue)
{
    static const MTLPixelFormat formats[] = {MTLPixelFormatRGBA8Unorm, MTLPixelFormatBGRA8Unorm,
        MTLPixelFormatRGBA8Unorm_sRGB, MTLPixelFormatBGRA8Unorm_sRGB};
    for (unsigned f = 0; f < 4; f++) @autoreleasepool {
        id<MTLTexture> target = texture(device, formats[f]);
        for (unsigned p = 0; p < 2; p++) @autoreleasepool {
            uint32_t words[WORDS]; memset(words, 0xa5, sizeof(words));
            [target replaceRegion:MTLRegionMake2D(0, 0, WIDTH, HEIGHT) mipmapLevel:0 withBytes:words bytesPerRow:STRIDE];
            MTLClearColor color = p ? MTLClearColorMake(.5, .5, .5, 1) : MTLClearColorMake(1, 0, 0, 1);
            uint32_t expected = p ? (f >= 2 ? 0xffbcbcbc : 0xff808080) : (f & 1 ? 0xffff0000 : 0xff0000ff);
            for (unsigned i = 0; i < WORDS; i++) words[i] = expected;
            char phase[64]; snprintf(phase, sizeof(phase), "format-%lu-%s", (unsigned long)formats[f], p ? "half-linear" : "red");
            clear(queue, target, color, phase); verify_texture(target, words, phase);
        }
        [target release];
    }
}
static void slots(id<MTLDevice> device, id<MTLCommandQueue> queue, uint32_t seed)
{
    for (unsigned i = 0; i < 80; i++) @autoreleasepool {
        id<MTLCommandBuffer> abandoned = [queue commandBuffer];
        check(abandoned != nil && abandoned.status == MTLCommandBufferStatusNotEnqueued,
              "abandoned-slots", "uncommitted command buffer creation");
    }
    receipt("abandoned-slots count=80 PASS\n");
    id<MTLTexture> target = texture(device, MTLPixelFormatRGBA8Unorm);
    for (unsigned i = 0; i < 72; i++) @autoreleasepool {
        uint32_t bits = (seed + i) & 7, words[WORDS];
        uint32_t expected = 0xff000000 | ((bits & 1) ? 255 : 0) | ((bits & 2) ? 0xff00 : 0) | ((bits & 4) ? 0xff0000 : 0);
        for (unsigned x = 0; x < WORDS; x++) words[x] = expected;
        char phase[64]; snprintf(phase, sizeof(phase), "reuse-%02u", i);
        clear(queue, target, MTLClearColorMake(!!(bits & 1), !!(bits & 2), !!(bits & 4), 1), phase);
        verify_texture(target, words, phase);
    }
    [target release];
}
static void surfaces(id<MTLDevice> device, id<MTLCommandQueue> queue, uint32_t seed)
{
    NSDictionary *properties = @{(id)kIOSurfaceWidth:@(WIDTH), (id)kIOSurfaceHeight:@(HEIGHT),
        (id)kIOSurfaceBytesPerElement:@4, (id)kIOSurfaceBytesPerRow:@(STRIDE),
        (id)kIOSurfaceAllocSize:@(STRIDE * HEIGHT), (id)kIOSurfacePixelFormat:@(0x42475241)};
    IOSurfaceRef surface = IOSurfaceCreate((CFDictionaryRef)properties);
    check(surface != NULL && IOSurfaceGetID(surface) != 0 && IOSurfaceGetBytesPerRow(surface) == STRIDE,
          "surface", "caller-backed64x64 BGRA surface");
    check(IOSurfaceLock(surface, 0, NULL) == KERN_SUCCESS, "surface", "write lock");
    check(IOSurfaceGetBaseAddress(surface) != NULL, "surface", "base address");
    memset(IOSurfaceGetBaseAddress(surface), 0xa5, STRIDE * HEIGHT);
    check(IOSurfaceUnlock(surface, 0, NULL) == KERN_SUCCESS, "surface", "write unlock");
    MTLTextureDescriptor *d = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm width:WIDTH height:HEIGHT mipmapped:NO];
    d.storageMode = MTLStorageModeShared; d.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    id<MTLTexture> imported = [device newTextureWithDescriptor:d iosurface:surface plane:0];
    check(imported != nil, "surface", "Metal import");
    clear(queue, imported, MTLClearColorMake(1, 0, 0, 1), "surface-GPU-to-CPU");
    uint32_t want[WORDS]; for (unsigned i = 0; i < WORDS; i++) want[i] = 0xffff0000;
    check(IOSurfaceLock(surface, kIOSurfaceLockReadOnly, NULL) == KERN_SUCCESS, "surface-read", "read lock");
    verify_words(IOSurfaceGetBaseAddress(surface), want, "surface-GPU-to-CPU");
    check(IOSurfaceUnlock(surface, kIOSurfaceLockReadOnly, NULL) == KERN_SUCCESS, "surface-read", "read unlock");
    id<MTLTexture> target = texture(device, MTLPixelFormatBGRA8Unorm);
    for (unsigned p = 0; p < 2; p++) @autoreleasepool {
        for (unsigned i = 0; i < WORDS; i++) want[i] = 0xff000000 | ((seed ^ (i * 0x9e3779b1u) ^ (p * 0x00ffffffu)) & 0x00ffffffu);
        check(IOSurfaceLock(surface, 0, NULL) == KERN_SUCCESS, "surface-update", "CPU write lock");
        memcpy(IOSurfaceGetBaseAddress(surface), want, sizeof(want));
        check(IOSurfaceUnlock(surface, 0, NULL) == KERN_SUCCESS, "surface-update", "CPU write unlock");
        id<MTLCommandBuffer> cb = [queue commandBuffer];
        id<MTLBlitCommandEncoder> encoder = [cb blitCommandEncoder];
        check(encoder != nil, "surface-copy", "blit encoder");
        [encoder copyFromTexture:imported sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0,0,0)
                     sourceSize:MTLSizeMake(WIDTH,HEIGHT,1) toTexture:target destinationSlice:0
               destinationLevel:0 destinationOrigin:MTLOriginMake(0,0,0)];
        [encoder endEncoding];
        const char *phase = p ? "surface-CPU-to-GPU-B" : "surface-CPU-to-GPU-A";
        finish(cb, phase); verify_texture(target, want, phase);
    }
    receipt("surface id=%u width=64 height=64 stride=256 format=BGRA cases=3 PASS\n", IOSurfaceGetID(surface));
    [target release]; [imported release]; CFRelease(surface);
}
#if defined(GAUGUIN_METAL_SHADER_BYTES) && defined(GAUGUIN_METAL_SHADER_SHA256)
#define GAUGUIN_HAS_SHADER_PROBE 1
#include "pipeline_tests.h"
#else
#define GAUGUIN_HAS_SHADER_PROBE 0
#endif
#ifdef GAUGUIN_CA_RENDERER_PROBE
#define GAUGUIN_HAS_CA_PROBE 1
#include "ca_renderer_tests.h"
#else
#define GAUGUIN_HAS_CA_PROBE 0
#endif
static void run(bool pipelines, bool ca)
{
    uint32_t seed = (uint32_t)now_ns() ^ ((uint32_t)getpid() * 0x9e3779b9u);
    @autoreleasepool {
    NSString *path = @"/usr/local/lib/gauguin/GauguinMetal.bundle";
    trusted_file([path stringByAppendingPathComponent:@"GauguinMetal"]);
    trusted_file([path stringByAppendingPathComponent:@"Info.plist"]);
    NSBundle *bundle = [[NSBundle alloc] initWithPath:path]; NSError *error = nil;
    check(bundle && [bundle loadAndReturnError:&error], "bundle", [[error description] UTF8String]);
    Class cls = [bundle principalClass], base = objc_getClass("_MTLDevice");
    check(cls && base && class_getSuperclass(cls) == base && !strcmp(class_getName(cls), "HakiosMetalDevice"),
          "bundle", "exact principal and superclass");
    io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("IOAcceleratorES"));
    check(service != IO_OBJECT_NULL, "device", "accelerator registry service");
    id<MTLDevice> device = ((id (*)(id, SEL, io_service_t))objc_msgSend)([cls alloc], sel_registerName("initWithAcceleratorPort:"), service);
    IOObjectRelease(service);
    check(device != nil, "device", "profile/ABI/kernel admission refused");
    ((void (*)(id, SEL))objc_msgSend)(device, sel_registerName("initLimits"));
    check(device.maxBufferLength == GAUGUIN_METAL_MAX_BUFFER_BYTES, "limits", "actual kernel64MiB maxBO");
    check([device newBufferWithLength:GAUGUIN_METAL_MAX_BUFFER_BYTES + 1 options:MTLResourceStorageModeShared] == nil,
          "limits", "oversized allocation must be refused before IO");
    id<MTLCommandQueue> queue = [device newCommandQueueWithMaxCommandBufferCount:4];
    check(queue != nil, "queue", "queue creation");
    receipt("device=%s seed=%u maxBO=67108864 queueSlots=4\n", [[device name] UTF8String], seed);
    memory("opened");
    if (ca) {
#if GAUGUIN_HAS_CA_PROBE
        ca_render_scenes(device, queue);
#endif
    } else {
        formats(device, queue); slots(device, queue, seed); surfaces(device, queue, seed);
#if GAUGUIN_HAS_SHADER_PROBE
        if (pipelines) shader_pipelines(device,queue,seed);
#endif
    }
    unsigned expected = ca ? 10 : (pipelines ? 93 : 83);
    check(submissions == expected && atomic_load(&callbacks) == expected, "final", "all GPU jobs and callbacks required");
    [queue release]; [device release]; [bundle release];
    }
    memory("after-resource-release");
    io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("HakiosGPU"));
    check(service != IO_OBJECT_NULL, "owner-release", "GPU service");
    io_connect_t connection = IO_OBJECT_NULL;
    kern_return_t opened = IOServiceOpen(service, mach_task_self(), 0, &connection);
    IOObjectRelease(service);
    check(opened == KERN_SUCCESS && connection != IO_OBJECT_NULL, "owner-release", "sole GPU owner was not released");
    check(IOServiceClose(connection) == KERN_SUCCESS, "owner-release", "reacquired client close");
    receipt("ownership reacquired=1 closed=1 PASS\n");
    if (ca)
        receipt("RESULT PASS build=%s seed=%u scenes=5 pixels=20480 explicit_jobs=10 exact_CA=1 discovery=0 UI=0\n", GAUGUIN_METAL_FRONTEND_BUILD, seed);
    else if (pipelines)
        receipt("RESULT PASS build=%s seed=%u jobs=93 pixel_checks=372736 compute_words=512 half_pixels=4096 abandoned=80 teardown-requested=1 discovery=0 shader-pipelines=1 UI=0\n",GAUGUIN_METAL_FRONTEND_BUILD,seed);
    else
        receipt("RESULT PASS build=%s seed=%u jobs=83 words=339968 abandoned=80 teardown-requested=1 discovery=0 shader-pipelines=0 UI=0\n", GAUGUIN_METAL_FRONTEND_BUILD, seed);
}
int main(int argc, char **argv)
{
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc != 2 || (strcmp(argv[1], "--metal226") && strcmp(argv[1], "--metal227") && strcmp(argv[1], "--metal230")) || getuid() || geteuid() ||
        strcmp(getprogname(), GAUGUIN_METAL_PROBE_NAME)) return 2;
    bool pipelines = strcmp(argv[1], "--metal227") == 0;
    bool ca = strcmp(argv[1], "--metal230") == 0;
    if (pipelines) receipt_prefix = "GAUGUIN METAL227 ";
    if (ca) receipt_prefix = "GAUGUIN METAL230 ";
    char args[1024] = {0}; size_t n = sizeof(args) - 1;
    check(sysctlbyname("kern.bootargs", args, &n, NULL, 0) == 0 && n < sizeof(args), "scope", "boot profile");
    enum gauguin_probe_route route = gauguin_probe_boot_route(args);
    if (route == GAUGUIN_PROBE_GLES) legacy_gles_probe();
    check(route == GAUGUIN_PROBE_METAL, "scope", "exact mode1+gmt1 or mode2 without gmt required");
    check(!pipelines || GAUGUIN_HAS_SHADER_PROBE, "scope", "shader probe is not compiled in");
    check(!ca || GAUGUIN_HAS_CA_PROBE, "scope", "CA renderer probe is not compiled in");
    check(setenv("GAUGUIN_METAL_MODE", "offscreen226", 1) == 0, "scope", "probe mode");
    alarm(210);
    receipt("begin build=%s delay=90 scope=%s\n", GAUGUIN_METAL_FRONTEND_BUILD,ca ? "root-offscreen-real-CARenderer-not-desktop" : (pipelines ? "root-offscreen-shader-pipelines-not-CA" : "root-offscreen-objects-not-CA"));
    memory("before-delay");
    uint64_t start = now_ns(); struct timespec rest = {90, 0};
    while (nanosleep(&rest, &rest)) check(errno == EINTR, "delay", "nanosleep");
    check(now_ns() - start >= 90ULL * 1000000000, "delay", "monotonic90s");
    @try { @autoreleasepool { run(pipelines, ca); } }
    @catch (NSException *exception) { fail("exception", [[exception description] UTF8String]); }
    check(now_ns() - start < 210ULL * 1000000000, "deadline", "finite diagnostic");
    alarm(0);
    return 0;
}
