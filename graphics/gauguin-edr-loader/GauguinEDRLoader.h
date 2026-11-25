#ifndef GAUGUIN_EDR_LOADER_H
#define GAUGUIN_EDR_LOADER_H
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* Supplied by the unchanged C4 frontend: mach_absolute_time in seconds. */
static double hm_now(void);
static unsigned gauguin_edr_loader_attempted;

/* Called AFTER the original GPU completion handler and its release. There is
 * one attempt per process, including refusals; no work is retried on a frame.
 * The helper independently verifies the exact OS/kernel/images before writing. */
static inline void gauguin_edr_load_after_completion(void)
{
    if (__atomic_exchange_n(&gauguin_edr_loader_attempted, 1, __ATOMIC_ACQ_REL)) return;
    const char *name = getprogname(), *mode = getenv("GAUGUIN_EAGL_MODE");
    int identity = name && !strcmp(name, "backboardd") && getuid() == 501 && geteuid() == 501;
    int enabled = mode && !strcmp(mode, "edr-default318");
    fprintf(stderr, "GAUGUIN EDR318 LOADER: entry us=%.0f identity=%u mode=%u\n",
            hm_now() * 1e6, identity, enabled);
    if (!identity || !enabled) {
        fprintf(stderr, "GAUGUIN EDR318 LOADER: refused=scope\n");
        return;
    }
    (void)dlerror();
    void *handle = dlopen("/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib", RTLD_NOW | RTLD_LOCAL);
    const char *error = handle ? NULL : dlerror();
    fprintf(stderr, "GAUGUIN EDR318 LOADER: result=%s us=%.0f\n",
            handle ? "opened" : "failed", hm_now() * 1e6);
    if (error) fprintf(stderr, "GAUGUIN EDR318 LOADER: error=%.400s\n", error);
    fflush(stderr);
    /* Retain the successful handle for the lifetime of backboardd. */
}
#endif
