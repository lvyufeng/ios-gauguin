/* The accepted standalone GLES workload with compositor scope and cleanup. */
#define GL_GLEXT_PROTOTYPES 1
#include <GLES3/gl3.h>
#include <GL/osmesa.h>
#include <IOKit/IOKitLib.h>
#include <IOSurface/IOSurfaceRef.h>
#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <errno.h>
#include <stdbool.h>
#include <mach/mach.h>
enum { WIDTH = 32, HEIGHT = 32, PIXELS = WIDTH * HEIGHT };
struct param {
    uint32_t pipe, param;
    uint64_t value;
    uint32_t len, pad;
};
_Static_assert(sizeof(struct param) == 24, "msm GET_PARAM wire layout");
static int fail(const char *where)
{
    fprintf(stderr, "GAUGUIN COMP GPU FAIL: %s\n", where);
    fflush(stderr);
    return 1;
}
static int memory_checkpoint(const char *phase)
{
    task_vm_info_data_t vm = {0};
    mach_msg_type_number_t count = TASK_VM_INFO_REV1_COUNT;
    if (task_info(mach_task_self(), TASK_VM_INFO, (task_info_t)&vm, &count) != KERN_SUCCESS ||
        count < TASK_VM_INFO_REV1_COUNT || !vm.phys_footprint) {
        return fail("read compositor physical footprint");
    }
    printf("GAUGUIN COMP GPU memory phase=%s footprint_bytes=%llu\n", phase,
           (unsigned long long)vm.phys_footprint);
    fflush(stdout);
    return 0;
}
static bool number(CFMutableDictionaryRef props, CFStringRef key, int32_t value)
{
    CFNumberRef n = CFNumberCreate(NULL, kCFNumberSInt32Type, &value);
    if (n == NULL) {
        return false;
    }
    CFDictionarySetValue(props, key, n);
    CFRelease(n);
    return true;
}
static int query_identity(void)
{
    io_service_t service =
        IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("HakiosGPU"));
    if (!service) {
        return fail("no real HakiosGPU service");
    }
    io_connect_t c = 0;
    kern_return_t rc = IOServiceOpen(service, mach_task_self(), 0, &c);
    IOObjectRelease(service);
    if (rc) {
        return fail("GPU user client open");
    }
    const uint32_t ids[] = {1, 2, 3, 6};
    uint64_t values[4] = {0};
    for (unsigned i = 0; i < 4; i++) {
        struct param p = {0x10, ids[i], 0, 0, 0};
        size_t size = sizeof(p);
        rc = IOConnectCallStructMethod(c, 0x40, &p, sizeof(p), &p, &size);
        if (rc || size != sizeof(p)) {
            IOServiceClose(c);
            return fail(ids[i] == 6
                            ? "kernel must implement actual GMEM-base parameter6 before GLES"
                            : "hardware query");
        }
        values[i] = p.value;
    }
    rc = IOServiceClose(c);
    if (rc || values[0] != 619 || values[1] != 512 * 1024 || values[2] != 0x06010900 ||
        values[3] != 0x100000) {
        return fail("actual A619 identity/configured GMEM differs");
    }
    printf("GAUGUIN COMP GPU identity gpu=%llu chip=%llx gmem=%llu base=%llx\n",
           (unsigned long long)values[0], (unsigned long long)values[2],
           (unsigned long long)values[1], (unsigned long long)values[3]);
    fflush(stdout);
    return 0;
}
static GLuint shader(GLenum type, const char *source)
{
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &source, NULL);
    glCompileShader(s);
    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    if (!ok) {
        char log[2048];
        GLsizei n = 0;
        glGetShaderInfoLog(s, sizeof(log), &n, log);
        fprintf(stderr, "GLSL compile: %.*s\n", (int)n, log);
        glDeleteShader(s);
        return 0;
    }
    return s;
}
static GLuint program(const char *fs)
{
    const char *vs = "#version 300 es\nout vec2 uv;\nvoid main(){vec2 "
                     "p=vec2((gl_VertexID==1)?3.0:-1.0,(gl_VertexID==2)?3.0:-1.0);uv=(p+1.0)*0.5;"
                     "gl_Position=vec4(p,0.0,1.0);}\n";
    GLuint v = shader(GL_VERTEX_SHADER, vs), f = shader(GL_FRAGMENT_SHADER, fs);
    if (!v || !f) {
        if (v) {
            glDeleteShader(v);
        }
        if (f) {
            glDeleteShader(f);
        }
        return 0;
    }
    GLuint p = glCreateProgram();
    glAttachShader(p, v);
    glAttachShader(p, f);
    glLinkProgram(p);
    glDeleteShader(v);
    glDeleteShader(f);
    GLint ok = 0;
    glGetProgramiv(p, GL_LINK_STATUS, &ok);
    if (!ok) {
        char log[2048];
        GLsizei n = 0;
        glGetProgramInfoLog(p, sizeof(log), &n, log);
        fprintf(stderr, "GLSL link: %.*s\n", (int)n, log);
        glDeleteProgram(p);
        return 0;
    }
    return p;
}
static uint32_t expected(uint32_t seed, unsigned x, unsigned y)
{
    unsigned cell = ((x / 4) + (y / 4) + (seed & 1)) & 1;
    unsigned bits = ((seed >> 1) & 7) ^ (cell ? 7 : 0);
    return 0xff000000u | ((bits & 1) ? 0x000000ffu : 0) | ((bits & 2) ? 0x0000ff00u : 0) |
           ((bits & 4) ? 0x00ff0000u : 0);
}
__attribute__((visibility("default"))) int gauguin_compositor_gles_run(void)
{
    if (getuid() != 501 || geteuid() != 501 || !getprogname() ||
        strcmp(getprogname(), "backboardd")) {
        return fail("unexpected compositor identity");
    }
    if (memory_checkpoint("before-context") || query_identity()) {
        return 1;
    }
    int status = 1;
    OSMesaContext context = NULL;
    bool current = false, surface_locked = false;
    IOSurfaceRef surface = NULL;
    IOSurfaceLockOptions lock_options = 0;
    GLuint draw = 0, sample = 0, texture = 0, shared = 0, framebuffer = 0, vao = 0;
    const int attribs[] = {OSMESA_FORMAT,
                           OSMESA_BGRA,
                           OSMESA_DEPTH_BITS,
                           0,
                           OSMESA_STENCIL_BITS,
                           0,
                           OSMESA_PROFILE,
                           OSMESA_ES_PROFILE,
                           OSMESA_CONTEXT_MAJOR_VERSION,
                           3,
                           OSMESA_CONTEXT_MINOR_VERSION,
                           0,
                           0};
    context = OSMesaCreateContextAttribs(attribs, NULL);
    uint32_t memory[PIXELS];
    memset(memory, 0x5a, sizeof(memory));
    if (!context) {
        fail("real ES3 context creation");
        goto cleanup;
    }
    if (memory_checkpoint("context-created")) {
        goto cleanup;
    }
    if (!OSMesaMakeCurrent(context, memory, GL_UNSIGNED_BYTE, WIDTH, HEIGHT)) {
        fail("real ES3 context current");
        goto cleanup;
    }
    current = true;
    if (memory_checkpoint("context-current")) {
        goto cleanup;
    }
    const char *renderer = (const char *)glGetString(GL_RENDERER),
               *version = (const char *)glGetString(GL_VERSION);
    printf("GAUGUIN COMP GPU renderer=%s version=%s\n", renderer ? renderer : "null",
           version ? version : "null");
    fflush(stdout);
    if (!renderer || !version ||
        (!strstr(renderer, "FD619") && !strstr(renderer, "Adreno (TM) 619")) ||
        strstr(renderer, "softpipe") || strstr(renderer, "llvmpipe") ||
        !strstr(version, "OpenGL ES 3")) {
        fail("hardware renderer identity");
        goto cleanup;
    }
    draw = program(
        "#version 300 es\nprecision highp float;\nuniform vec4 tint;uniform int phase;out vec4 "
        "color;void main(){ivec2 p=ivec2(gl_FragCoord.xy);bool "
        "odd=((p.x/4+p.y/4+phase)&1)!=0;color=vec4(odd?vec3(1.0)-tint.rgb:tint.rgb,1.0);}\n");
    sample = program("#version 300 es\nprecision highp float;in vec2 uv;uniform sampler2D src;out "
                     "vec4 color;void main(){color=texture(src,uv);}\n");
    if (!draw || !sample) {
        fail("runtime GLSL programs");
        goto cleanup;
    }
    if (memory_checkpoint("programs-linked")) {
        goto cleanup;
    }
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &t) != 0) {
        fail("read shader seed clock");
        goto cleanup;
    }
    uint32_t seed = (uint32_t)t.tv_nsec ^ ((uint32_t)getpid() * 0x9e3779b9u);
    glGenVertexArrays(1, &vao);
    glBindVertexArray(vao);
    glGenTextures(1, &texture);
    glBindTexture(GL_TEXTURE_2D, texture);
    glTexStorage2D(GL_TEXTURE_2D, 1, GL_RGBA8, WIDTH, HEIGHT);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glGenFramebuffers(1, &framebuffer);
    glBindFramebuffer(GL_FRAMEBUFFER, framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0);
    if (glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
        fail("normal framebuffer");
        goto cleanup;
    }
    glViewport(0, 0, WIDTH, HEIGHT);
    glUseProgram(draw);
    unsigned bits = (seed >> 1) & 7;
    glUniform4f(glGetUniformLocation(draw, "tint"), (bits & 1) ? 1 : 0, (bits & 2) ? 1 : 0,
                (bits & 4) ? 1 : 0, 1);
    glUniform1i(glGetUniformLocation(draw, "phase"), seed & 1);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glFinish();
    uint32_t result[PIXELS];
    glReadPixels(0, 0, WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, result);
    if (glGetError() != GL_NO_ERROR) {
        fail("normal shader draw/readback GL error");
        goto cleanup;
    }
    uint32_t hash = 2166136261u;
    for (unsigned i = 0; i < PIXELS; i++) {
        if (result[i] != expected(seed, i % WIDTH, i / WIDTH)) {
            fprintf(stderr, "normal mismatch pixel=%u actual=%08x expected=%08x\n", i, result[i],
                    expected(seed, i % WIDTH, i / WIDTH));
            goto cleanup;
        }
        hash = (hash ^ result[i]) * 16777619u;
    }
    printf("GAUGUIN COMP GPU normal seed=%u pixels=%u hash=%08x\n", seed, PIXELS, hash);
    fflush(stdout);
    if (memory_checkpoint("normal-readback")) {
        goto cleanup;
    }
    CFMutableDictionaryRef props = CFDictionaryCreateMutable(
        NULL, 0, &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    if (!props) {
        fail("IOSurface properties allocation");
        goto cleanup;
    }
    bool properties_ok =
        number(props, kIOSurfaceWidth, WIDTH) && number(props, kIOSurfaceHeight, HEIGHT) &&
        number(props, kIOSurfaceBytesPerRow, 4 * WIDTH) &&
        number(props, kIOSurfaceBytesPerElement, 4) &&
        number(props, kIOSurfacePixelFormat, 0x42475241) &&
        number(props, CFSTR("IOSurfaceOffset"), 64) && number(props, kIOSurfaceAllocSize, 16384);
    if (properties_ok) {
        surface = IOSurfaceCreate(props);
    }
    CFRelease(props);
    if (!surface) {
        fail("IOSurface create");
        goto cleanup;
    }
    if (IOSurfaceLock(surface, 0, NULL)) {
        fail("surface init lock");
        goto cleanup;
    }
    surface_locked = true;
    void *base = IOSurfaceGetBaseAddress(surface);
    if (!base) {
        fail("surface base");
        goto cleanup;
    }
    memset(base, 0xa5, PIXELS * 4);
    if (IOSurfaceUnlock(surface, 0, NULL)) {
        fail("surface init unlock");
        goto cleanup;
    }
    surface_locked = false;
    typedef void (*ImportImage)(GLenum, void *);
    ImportImage import = (ImportImage)OSMesaGetProcAddress("glEGLImageTargetTexture2DOES");
    if (!import) {
        fail("IOSurface import entry");
        goto cleanup;
    }
    glGenTextures(1, &shared);
    glBindTexture(GL_TEXTURE_2D, shared);
    import(GL_TEXTURE_2D, (void *)(uintptr_t)IOSurfaceGetID(surface));
    glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, shared, 0);
    if (glGetError() != GL_NO_ERROR ||
        glCheckFramebufferStatus(GL_FRAMEBUFFER) != GL_FRAMEBUFFER_COMPLETE) {
        fail("IOSurface framebuffer/import");
        goto cleanup;
    }
    glActiveTexture(GL_TEXTURE0);
    glBindTexture(GL_TEXTURE_2D, texture);
    glUseProgram(sample);
    glUniform1i(glGetUniformLocation(sample, "src"), 0);
    glDrawArrays(GL_TRIANGLES, 0, 3);
    glFinish();
    if (glGetError() != GL_NO_ERROR) {
        fail("IOSurface sampled draw/fence");
        goto cleanup;
    }
    lock_options = kIOSurfaceLockReadOnly;
    if (IOSurfaceLock(surface, lock_options, NULL)) {
        fail("surface result lock");
        goto cleanup;
    }
    surface_locked = true;
    volatile uint32_t *pixels = (volatile uint32_t *)IOSurfaceGetBaseAddress(surface);
    if (!pixels) {
        fail("surface result base");
        goto cleanup;
    }
    hash = 2166136261u;
    for (unsigned i = 0; i < PIXELS; i++) {
        uint32_t rgba = expected(seed, i % WIDTH, i / WIDTH);
        uint32_t bgra = (rgba & 0xff00ff00u) | ((rgba & 0xffu) << 16) | ((rgba >> 16) & 0xffu);
        uint32_t have = pixels[i];
        if (have != bgra) {
            fprintf(stderr, "surface mismatch pixel=%u actual=%08x expected=%08x\n", i, have, bgra);
            goto cleanup;
        }
        hash = (hash ^ have) * 16777619u;
    }
    if (IOSurfaceUnlock(surface, lock_options, NULL)) {
        fail("surface result unlock");
        goto cleanup;
    }
    surface_locked = false;
    printf("GAUGUIN COMP GPU surface seed=%u pixels=%u hash=%08x\n", seed, PIXELS, hash);
    fflush(stdout);
    if (memory_checkpoint("surface-readback")) {
        goto cleanup;
    }
    status = 0;
cleanup:
    if (surface_locked) {
        IOSurfaceUnlock(surface, lock_options, NULL);
    }
    if (current) {
        glBindFramebuffer(GL_FRAMEBUFFER, 0);
        glDeleteFramebuffers(1, &framebuffer);
        glDeleteTextures(1, &shared);
        glDeleteTextures(1, &texture);
        glDeleteVertexArrays(1, &vao);
        if (sample) {
            glDeleteProgram(sample);
        }
        if (draw) {
            glDeleteProgram(draw);
        }
        OSMesaMakeCurrent(NULL, NULL, GL_UNSIGNED_BYTE, 0, 0);
    }
    if (context) {
        OSMesaDestroyContext(context);
    }
    if (surface) {
        CFRelease(surface);
    }
    if (status == 0) {
        puts("GAUGUIN COMP GPU PASS real-GLSL-draw-texture-IOSurface");
        fflush(stdout);
    }
    return status;
}
