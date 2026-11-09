/* Run the isolated compositor GPU probe after the kernel permits handoff. */
#include <IOKit/IOKitLib.h>
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <time.h>
#include <unistd.h>

static bool
pilot_enabled(void)
{
    const char *name = getprogname(), *mode = getenv("GAUGUIN_EAGL_MODE");
    if (getuid() != 501 || geteuid() != 501 || !name || strcmp(name, "backboardd") ||
        !mode || strcmp(mode, "admission")) {
        return false;
    }
    char args[1024] = {0};
    size_t length = sizeof(args) - 1;
    if (sysctlbyname("kern.bootargs", args, &length, NULL, 0) != 0 || length >= sizeof(args)) {
        return false;
    }
    bool matched = false;
    char *state;
    for (char *arg = strtok_r(args, " \t", &state); arg; arg = strtok_r(NULL, " \t", &state)) {
        if (strncmp(arg, "sweeteagl=", sizeof("sweeteagl=") - 1) == 0) {
            if (matched || strcmp(arg, "sweeteagl=2") != 0) {
                return false;
            }
            matched = true;
        }
    }
    return matched;
}

static bool
wait_for_gpu(void)
{
    struct timespec start, now;
    if (clock_gettime(CLOCK_MONOTONIC_RAW, &start) != 0) {
        return false;
    }
    do {
        io_service_t service = IOServiceGetMatchingService(kIOMainPortDefault, IOServiceMatching("HakiosGPU"));
        if (service != IO_OBJECT_NULL) {
            io_connect_t connection = IO_OBJECT_NULL;
            kern_return_t result = IOServiceOpen(service, mach_task_self(), 0, &connection);
            IOObjectRelease(service);
            if (result == KERN_SUCCESS) {
                return connection != IO_OBJECT_NULL && IOServiceClose(connection) == KERN_SUCCESS;
            }
        }
        const struct timespec delay = {1, 0};
        nanosleep(&delay, NULL);
    } while (clock_gettime(CLOCK_MONOTONIC_RAW, &now) == 0 &&
             now.tv_sec >= start.tv_sec && now.tv_sec - start.tv_sec < 240);
    return false;
}

static void *
open_root_library(const char *path, int flags)
{
    struct stat info;
    if (lstat(path, &info) != 0 || !S_ISREG(info.st_mode) || info.st_uid != 0 ||
        (info.st_mode & (S_IWGRP | S_IWOTH)) != 0 || access(path, W_OK) == 0 ||
        (errno != EACCES && errno != EPERM && errno != EROFS)) {
        fprintf(stderr, "GAUGUIN GPU PILOT library path rejected %s\n", path);
        return NULL;
    }
    void *library = dlopen(path, flags);
    if (library == NULL) {
        const char *error = dlerror();
        fprintf(stderr, "GAUGUIN GPU PILOT dlopen failed %.160s\n", error ? error : "unknown");
    }
    return library;
}

static void *
run_pilot(void *unused)
{
    (void)unused;
    static const char worker[] = "/usr/local/lib/gauguin/libGauguinCompositorProbe.dylib";
    fprintf(stderr, "GAUGUIN GPU PILOT begin pid=%d\n", getpid());
    if (!wait_for_gpu()) {
        fprintf(stderr, "GAUGUIN GPU PILOT failed waiting for clean GPU handoff\n");
        return NULL;
    }
    void *library = open_root_library(worker, RTLD_NOW | RTLD_LOCAL | RTLD_FIRST);
    if (library == NULL) {
        return NULL;
    }
    int (*run)(void) = (int (*)(void))dlsym(library, "gauguin_compositor_gles_run");
    int result = run ? run() : -1;
    if (dlclose(library) != 0) {
        result = -1;
    }
    fprintf(stderr, "GAUGUIN GPU PILOT finish pid=%d rc=%d\n", getpid(), result);
    fflush(stderr);
#if defined(GAUGUIN_EAGL_BRIDGE_LOADER)
    if (result == 0) {
        /* Objective-C class methods retain these code addresses for the entire
         * compositor lifetime, including already-created contexts. */
        static void *bridge_image;
        bridge_image = open_root_library("/usr/local/lib/gauguin/libGauguinEAGL.dylib",
                                         RTLD_NOW | RTLD_LOCAL | RTLD_FIRST | RTLD_NODELETE);
        int (*installed)(void) = bridge_image
            ? (int (*)(void))dlsym(bridge_image, "gauguin_eagl_bridge_installed") : NULL;
        fprintf(stderr, "GAUGUIN EAGL BRIDGE finish installed=%d pid=%d\n",
                installed ? installed() : 0, getpid());
        fflush(stderr);
    }
#endif
    return NULL;
}

__attribute__((visibility("hidden"))) void
gauguin_eagl_start_pilot(void)
{
    if (!pilot_enabled()) {
        return;
    }
    pthread_attr_t attr;
    int result = pthread_attr_init(&attr);
    if (result == 0) {
        result = pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED);
        if (result == 0) {
            pthread_t thread;
            result = pthread_create(&thread, &attr, run_pilot, NULL);
        }
        pthread_attr_destroy(&attr);
    }
    if (result != 0) {
        fprintf(stderr, "GAUGUIN GPU PILOT worker creation failed rc=%d\n", result);
    }
}
