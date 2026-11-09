/* Build the production exec extraction and insertion with typed OS seams. */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "%d: %s\n", __LINE__, #x); exit(1); } } while (0)
#define NCARGS 262144
#define PAGE_SIZE 16384
#define ARM64_BOARD_CONFIG_SWEET 1
#define IMGPF_INTERPRET 1
#define IMGPF_IS_64BIT_ADDR 2
#define IMGPF_WAS_64BIT_ADDR 4
#define IMGPF_EXEC 0x100
#define IMGPF_SPAWN 0x10
#define UIO_SYSSPACE 0
#define UIO_SEG_IS_USER_SPACE(seg) ((seg) != UIO_SYSSPACE)
#define CAST_DOWN(type, value) ((type)(uintptr_t)(value))
#define IS_WHITESPACE(ch) ((ch) == ' ' || (ch) == '\t')
#define TRUE true
typedef bool boolean_t;

struct proc { int pid; uint64_t uniqueid; int pidversion; bool shadow; int original_parent; };
typedef struct proc *proc_t;
static struct proc process = {57, 1234, 19, false, 1};
static struct proc other_process = {58, 3456, 20, false, 1};
static struct proc shadow_process = {57, 1234, 19, true, 1};
static struct proc launchd = {1, 1, 1, false, 0};
struct thread { proc_t proc; };
typedef struct thread *thread_t;
#define THREAD_NULL NULL
static struct thread exec_thread = {&process};
static thread_t image_thread = &exec_thread;
static proc_t get_bsdthreadtask_info(thread_t thread) { return thread->proc; }
struct credential { uid_t uid, ruid; };
typedef struct credential *kauth_cred_t;
#define IS_VALID_CRED(cred) ((cred) != NULL)
struct context { proc_t proc; kauth_cred_t cred; };
typedef struct context *vfs_context_t;
static struct credential credentials = {501, 501};
static struct context exec_context = {&process, &credentials}, kernel_context;
static proc_t running_proc = &process;
static proc_t current_proc(void) { return running_proc; }
static int proc_pid(proc_t p) { return p->pid; }
static uint64_t proc_uniqueid(proc_t p) { return p->uniqueid; }
static int proc_pidversion(proc_t p) { return p->pidversion; }
static bool proc_is_shadow(proc_t p) { return p->shadow; }
static bool proc_isinitproc(proc_t p) { return p == &launchd; }
static int proc_original_ppid(proc_t p) { return p->original_parent; }
static proc_t vfs_context_proc(vfs_context_t ctx) { return ctx->proc; }
static kauth_cred_t vfs_context_ucred(vfs_context_t ctx) { return ctx->cred; }
static vfs_context_t vfs_context_kernel(void) { return &kernel_context; }
static uid_t kauth_cred_getuid(kauth_cred_t cred) { return cred->uid; }
static uid_t kauth_cred_getruid(kauth_cred_t cred) { return cred->ruid; }

#define VREG 1
#define NULLVP NULL
#define MNT_ROOTFS 1
#define VNODE_LOOKUP_NOFOLLOW 1
#define VNODE_LOOKUP_NOCROSSMOUNT 2
#define KAUTH_VNODE_WRITE_DATA 1
struct mount { unsigned flags; };
typedef struct mount *mount_t;
static struct mount root_mount = {MNT_ROOTFS}, other_mount;
struct vnode { mount_t mount; int type, refs, auth; uid_t uid; mode_t mode; };
typedef struct vnode *vnode_t;
static struct vnode target = {&root_mount, VREG, 1, EACCES, 0, 0755};
static struct vnode library = {&root_mount, VREG, 0, EPERM, 0, 0644};
static struct vnode proxy = {&root_mount, VREG, 1, EACCES, 0, 0755};
struct vnode_attr { uid_t va_uid; mode_t va_mode; bool supported; };
#define VATTR_INIT(a) (*(a) = (struct vnode_attr){0})
#define VATTR_WANTED(a, field) ((void)(a)->field)
#define VATTR_IS_SUPPORTED(a, field) ((void)(a)->field, (a)->supported)
static bool missing_target, missing_library, attributes_unsupported, attributes_error;
static unsigned lookups, writes, authorizations;
static int vnode_vtype(vnode_t node) { return node->type; }
static mount_t vnode_mount(vnode_t node) { return node->mount; }
static unsigned vfs_flags(mount_t mount) { return mount->flags; }

static int vnode_lookup(const char *path, int flags, vnode_t *out, vfs_context_t ctx)
{
    CHECK(ctx == &kernel_context);
    CHECK(flags == (VNODE_LOOKUP_NOFOLLOW | VNODE_LOOKUP_NOCROSSMOUNT));
    lookups++;
    if (strcmp(path, "/usr/libexec/backboardd") == 0) {
        if (missing_target) return ENOENT;
        *out = &target;
    } else if (strcmp(path, "/usr/libexec/xpcproxy") == 0) {
        *out = &proxy;
    } else {
        CHECK(strcmp(path, "/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib") == 0);
        if (missing_library) return ENOENT;
        *out = &library;
    }
    (*out)->refs++;
    return 0;
}

static int vnode_getattr(vnode_t node, struct vnode_attr *a, vfs_context_t ctx)
{
    CHECK(node->refs > 0 && ctx == &kernel_context);
    if (attributes_error) return EIO;
    *a = (struct vnode_attr){node->uid, node->mode, !attributes_unsupported};
    return 0;
}

static int vnode_authorize(vnode_t node, vnode_t parent, int action, vfs_context_t ctx)
{
    CHECK(node->refs > 0 && parent == NULL && ctx == &exec_context);
    CHECK(action == KAUTH_VNODE_WRITE_DATA && ctx->cred->uid == 501);
    authorizations++;
    return node->auth;
}

static void vnode_put(vnode_t node) { CHECK(node->refs > 0); node->refs--; }

struct image_params {
    char *ip_strings, *ip_strendp, *ip_startargv, *ip_endargv, *ip_endenvv;
    int ip_strspace, ip_argspace, ip_argc, ip_envc, ip_flags, ip_seg;
    char *ip_interp_buffer;
    int ip_interp_sugid_fd;
    user_addr_t ip_user_argv, ip_user_envv, ip_user_fname;
    vnode_t ip_vp, ip_scriptvp;
    vfs_context_t ip_vfs_context;
    thread_t ip_new_thread;
};

static int copyinptr(user_addr_t address, user_addr_t *out, int pointer_size)
{
    CHECK(pointer_size == sizeof(*out));
    memcpy(out, (void *)address, sizeof(*out));
    return 0;
}

static int copyinstr(user_addr_t address, char *out, size_t size, size_t *copied)
{
    const char *in = (const char *)address;
    size_t n = strlen(in) + 1;
    *copied = n < size ? n : size;
    memcpy(out, in, *copied);
    return n <= size ? 0 : ENAMETOOLONG;
}

static bool copy_failure;
static int copystr(const char *in, char *out, size_t size, size_t *copied)
{
    CHECK(strncmp(in, "DYLD_INSERT_LIBRARIES=", 22) == 0);
    writes++;
    if (copy_failure) {
        CHECK(size >= 4);
        memcpy(out, in, 4);
        *copied = 4;
        return EFAULT;
    }
    return copyinstr((user_addr_t)in, out, size, copied);
}

static unsigned sweet_exec_loader_probe = 1, sweet_eagl_inject_requested;
#include "production-add.h"
#include "production-env.h"
#include "production-inject.h"
#include "production-extract.h"

#define MEMORYSTATUS_ENTITLEMENT "com.apple.private.memorystatus"
#define MEMORYSTATUS_CMD_GET_MEMLIMIT_PROPERTIES 8
struct memorystatus_control_args {
    unsigned command;
    int pid;
    unsigned flags;
    user_addr_t buffer;
    size_t buffersize;
};
typedef struct {
    int32_t memlimit_active;
    uint32_t memlimit_active_attr;
    int32_t memlimit_inactive;
    uint32_t memlimit_inactive_attr;
} memorystatus_memlimit_properties_t;
static unsigned subject_queries, memory_snapshots;
static bool has_entitlement;

static bool sweet_dyld_probe_subject(proc_t p, uid_t *effective, uid_t *real)
{
    subject_queries++;
    *effective = credentials.uid;
    *real = credentials.ruid;
    return p == &process && *effective == *real;
}

static void memorystatus_get_memlimit_properties_internal(proc_t p, memorystatus_memlimit_properties_t *limits)
{
    CHECK(p == &process);
    memory_snapshots++;
    *limits = (memorystatus_memlimit_properties_t){64, 1, -1, 0};
}

static kauth_cred_t kauth_cred_get(void) { return &credentials; }
static bool kauth_cred_issuser(kauth_cred_t cred) { return cred->uid == 0; }
static bool IOCurrentTaskHasEntitlement(const char *entitlement)
{
    CHECK(strcmp(entitlement, MEMORYSTATUS_ENTITLEMENT) == 0);
    return has_entitlement;
}

#include "production-diagnostic-caller.h"
#include "production-memory.h"
#include "production-pilot.h"

static int memory_auth(proc_t p, struct memorystatus_control_args *args, bool skip_auth_check)
{
    int error = 0;
#include "production-auth.h"
out:
    return error;
}

static void memory_case(const char *scenario)
{
    bool exact = strcmp(scenario, "memory-self") == 0;
    bool log_checked = exact;
    bool authorized = false;
    uint32_t sentinel = 0xa1a2a3a4;
    struct memorystatus_control_args args = {8, 57, 0, (user_addr_t)&sentinel, 16};
    proc_t p = &process;
    sweet_eagl_inject_requested = 1;
    if (strcmp(scenario, "memory-disabled") == 0) sweet_eagl_inject_requested = 0;
    else if (strcmp(scenario, "memory-other-proc") == 0) {
        p = &other_process;
        args.pid = 58;
        log_checked = true;
    } else if (strcmp(scenario, "memory-other-uid") == 0) {
        credentials.uid = credentials.ruid = 502;
        log_checked = true;
    } else if (strcmp(scenario, "memory-root") == 0) {
        credentials.uid = credentials.ruid = 0;
        authorized = true;
    } else if (strcmp(scenario, "memory-entitled") == 0) {
        has_entitlement = true;
        authorized = true;
    } else if (strcmp(scenario, "memory-other-pid") == 0) args.pid = 58;
    else if (strcmp(scenario, "memory-wrong-size") == 0) args.buffersize = 32;
    else if (strcmp(scenario, "memory-wrong-command") == 0) args.command = 7;
    else if (strcmp(scenario, "memory-flags") == 0) args.flags = 1;
    else if (strcmp(scenario, "memory-no-buffer") == 0) args.buffer = USER_ADDR_NULL;
    else CHECK(exact);
    int error = memory_auth(p, &args, false);
    CHECK(error == (authorized ? 0 : EPERM));
    CHECK(subject_queries == (unsigned)log_checked && memory_snapshots == (unsigned)exact);
    CHECK(sentinel == 0xa1a2a3a4);
    printf("MEMORY PASS error=%d snapshots=%u\n", error, memory_snapshots);
}

static void pilot_case(const char *scenario)
{
#define PILOT(name) (strcmp(scenario, name) == 0)
    static char args[] = "xpcproxy\0com.apple.backboardd";
    static char other_args[] = "com.apple.backboardd\0other";
    const char *path = "executable_path=/usr/libexec/xpcproxy";
    char *buffer = calloc(1, NCARGS + PAGE_SIZE);
    CHECK(buffer);
    running_proc = &launchd;
    sweet_eagl_inject_requested = PILOT("pilot-mode-off") ? 1 : 2;
    const char *arguments = PILOT("pilot-argv0-only") ? other_args : args;
    size_t length = PILOT("pilot-argv0-only") ? sizeof(other_args) : sizeof(args);
    size_t path_bytes = strlen(path) + 1;
    memcpy(buffer, path, path_bytes);
    memcpy(buffer + path_bytes, arguments, length);
    char *end = buffer + path_bytes + length;
    struct image_params image = {
        .ip_strings = buffer, .ip_startargv = buffer + path_bytes, .ip_endargv = end,
        .ip_endenvv = end, .ip_strendp = end, .ip_argc = 2, .ip_new_thread = &exec_thread,
        .ip_vp = &proxy, .ip_vfs_context = &exec_context, .ip_flags = IMGPF_SPAWN,
    };
    if (PILOT("pilot-wrong-parent")) running_proc = &other_process;
    if (PILOT("pilot-reparented")) process.original_parent = 2;
    if (PILOT("pilot-exec-not-spawn")) image.ip_flags = IMGPF_EXEC;
    if (PILOT("pilot-other-vnode")) image.ip_vp = &target;
    if (PILOT("pilot-writable-proxy")) proxy.mode |= S_IWOTH;
    if (PILOT("pilot-thread-mismatch")) exec_thread.proc = &other_process;
    if (sweet_dyld_exec_trace(&image, &process) && sweet_eagl_gpu_pilot_enabled()) {
        sweet_eagl_gpu_record_proxy(&image, &process);
    }
    CHECK(proxy.refs == 1 && target.refs == 1);
    bool recorded = PILOT("pilot-good") || PILOT("pilot-pid-reused") || PILOT("pilot-wrong-uid") || PILOT("pilot-foreign-task");
    CHECK(sweet_eagl_launch_uniqueid == (recorded ? 1234u : 0u));
    running_proc = PILOT("pilot-foreign-task") ? &other_process : &process;
    if (PILOT("pilot-pid-reused")) process.uniqueid++;
    if (PILOT("pilot-wrong-uid")) credentials.uid = credentials.ruid = 502;
    CHECK(sweet_eagl_gpu_pilot_caller(&process) == PILOT("pilot-good"));
    CHECK(!sweet_eagl_gpu_pilot_caller(NULL));
    printf("PILOT PASS recorded=%d allowed=%d\n", recorded, PILOT("pilot-good"));
    free(buffer);
#undef PILOT
}

static struct image_params run_extract(char *buf, user_addr_t *args, user_addr_t *env,
    const char *path, int flags, vnode_t actual, vnode_t script, vfs_context_t context)
{
    size_t length = strlen(path) + 1;
    memcpy(buf, path, length);
    struct image_params image = {
        .ip_strings = buf, .ip_strendp = buf + length, .ip_strspace = NCARGS + PAGE_SIZE - (int)length,
        .ip_argspace = NCARGS, .ip_flags = flags, .ip_seg = 1, .ip_user_argv = (user_addr_t)args,
        .ip_user_envv = (user_addr_t)env, .ip_vp = actual, .ip_scriptvp = script,
        .ip_vfs_context = context, .ip_new_thread = image_thread,
    };
    CHECK(exec_extract_strings(&image) == 0);
    CHECK(image.ip_endenvv == image.ip_strendp && image.ip_strspace % 8 == 0);
    return image;
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    const char *scenario = argv[1];
    if (strncmp(scenario, "pilot-", 6) == 0) {
        pilot_case(scenario);
        return 0;
    }
    if (strncmp(scenario, "memory-", 7) == 0) {
        memory_case(scenario);
        return 0;
    }
#define CASE(name) (strcmp(scenario, name) == 0)
    static const char mode[] = "GAUGUIN_EAGL_MODE=admission";
    const char *path = "executable_path=/usr/libexec/backboardd";
    static char argument[NCARGS];
    strcpy(argument, "backboardd");
    user_addr_t args[] = {(user_addr_t)argument, 0};
    user_addr_t env[] = {(user_addr_t)"LOG=keep", (user_addr_t)mode, 0, 0, 0};
    char *before = calloc(1, NCARGS + PAGE_SIZE), *after = calloc(1, NCARGS + PAGE_SIZE);
    CHECK(before && after);
    bool append = false, event = true;
    unsigned expected = SEI_SUBJECT, reason = 0, expected_lookups = 0;
    unsigned requested = 1;
    int flags = IMGPF_IS_64BIT_ADDR | IMGPF_WAS_64BIT_ADDR;
    vnode_t actual = &target, script = NULL;
    vfs_context_t context = &exec_context;

    if (CASE("mobile") || CASE("root") || CASE("exact-fit") || CASE("one-short") || CASE("partial-copy")) {
        append = !CASE("one-short") && !CASE("partial-copy");
        expected = append ? SEI_APPENDED : CASE("one-short") ? SEI_SPACE : SEI_COPY;
        expected_lookups = 2;
        if (CASE("root")) credentials.uid = credentials.ruid = 0;
        if (CASE("partial-copy")) copy_failure = true;
        if (CASE("exact-fit") || CASE("one-short")) {
            /* One argv, three env entries after insertion and two terminators.
             * One extra byte in the input crosses the aligned NCARGS limit. */
            size_t env_bytes = sizeof("LOG=keep") + sizeof(mode);
            size_t fixed = env_bytes + 6 * 8 + sizeof(sweet_eagl_insert);
            size_t length = NCARGS - fixed;
            CHECK((length + env_bytes + sizeof(sweet_eagl_insert)) % 8 == 0);
            if (CASE("one-short")) length++;
            memset(argument, 'a', length - 1);
            argument[length - 1] = 0;
        }
    } else if (CASE("disabled") || CASE("bad-flag") || CASE("trace-off") ||
        CASE("other-path") || CASE("null-context")) {
        event = false;
        if (CASE("disabled")) requested = 0;
        if (CASE("bad-flag")) requested = 3;
        if (CASE("trace-off")) sweet_exec_loader_probe = 0;
        if (CASE("other-path")) path = "executable_path=/usr/libexec/other";
        if (CASE("null-context")) context = NULL;
    } else if (CASE("mode-absent") || CASE("mode-duplicate") || CASE("mode-other")) {
        expected = SEI_MODE;
        if (CASE("mode-absent")) env[1] = 0;
        if (CASE("mode-duplicate")) env[2] = (user_addr_t)mode;
        if (CASE("mode-other")) env[1] = (user_addr_t)"GAUGUIN_EAGL_MODE=render";
    } else if (CASE("already") || CASE("conflicting") || CASE("duplicate")) {
        expected = CASE("already") ? SEI_ALREADY : SEI_CONFLICT;
        expected_lookups = CASE("already") ? 2 : 0;
        env[2] = CASE("conflicting") ? (user_addr_t)"DYLD_INSERT_LIBRARIES=/other" : (user_addr_t)sweet_eagl_insert;
        if (CASE("duplicate")) env[3] = (user_addr_t)sweet_eagl_insert;
    } else if (CASE("other-proc") || CASE("null-thread") || CASE("script") || CASE("addr32") || CASE("missing-vnode")) {
        reason = CASE("other-proc") || CASE("null-thread") ? 1 : 8;
        if (CASE("other-proc")) exec_context.proc = &other_process;
        if (CASE("null-thread")) image_thread = NULL;
        if (CASE("script")) script = &library;
        if (CASE("addr32")) flags &= ~IMGPF_IS_64BIT_ADDR;
        if (CASE("missing-vnode")) actual = NULL;
    } else if (strncmp(scenario, "shadow", 6) == 0) {
        exec_context.proc = exec_thread.proc = &shadow_process;
        flags |= IMGPF_EXEC;
        append = CASE("shadow");
        if (append) {
            expected = SEI_APPENDED;
            expected_lookups = 2;
        } else {
            reason = 9;
            if (CASE("shadow-no-exec")) flags &= ~IMGPF_EXEC;
            else if (CASE("shadow-not-marked")) shadow_process.shadow = false;
            else if (CASE("shadow-wrong-pid")) shadow_process.pid = 58;
            else if (CASE("shadow-wrong-id")) shadow_process.uniqueid++;
            else if (CASE("shadow-wrong-version")) shadow_process.pidversion++;
            else CHECK(false);
        }
    } else if (CASE("no-cred") || CASE("setuid") || CASE("other-uid")) {
        reason = CASE("no-cred") ? 2 : 3;
        if (CASE("no-cred")) exec_context.cred = NULL;
        if (CASE("setuid")) credentials.ruid = 0;
        if (CASE("other-uid")) credentials.uid = credentials.ruid = 502;
    } else if (CASE("no-target") || CASE("wrong-target") || CASE("target-mount") ||
        CASE("no-attributes") || CASE("getattr-error") || CASE("target-acl")) {
        expected_lookups = 1;
        reason = CASE("no-target") ? 4 : 5;
        if (CASE("no-target")) missing_target = true;
        if (CASE("wrong-target")) actual = &library;
        if (CASE("target-mount")) target.mount = &other_mount;
        if (CASE("no-attributes")) attributes_unsupported = true;
        if (CASE("getattr-error")) attributes_error = true;
        if (CASE("target-acl")) target.auth = 0;
    } else {
        CHECK(CASE("no-library") || CASE("library-mode") || CASE("library-owner") ||
            CASE("library-type") || CASE("library-acl-error"));
        expected_lookups = 2;
        reason = CASE("no-library") ? 6 : 7;
        if (CASE("no-library")) missing_library = true;
        if (CASE("library-mode")) library.mode |= S_IWGRP;
        if (CASE("library-owner")) library.uid = 501;
        if (CASE("library-type")) library.type = 2;
        if (CASE("library-acl-error")) library.auth = EIO;
    }

    struct image_params old = run_extract(before, args, env, path, flags, actual, script, context);
    sweet_eagl_inject_requested = requested;
    struct image_params new = run_extract(after, args, env, path, flags, actual, script, context);
    CHECK(target.refs == 1 && library.refs == 0 && lookups == expected_lookups);
    CHECK(writes == (unsigned)(append || copy_failure));
    if (CASE("mobile")) CHECK(authorizations == 2);
    if (CASE("root")) CHECK(authorizations == 0);
    CHECK(new.ip_argc == old.ip_argc && new.ip_envc == old.ip_envc + append);
    CHECK(new.ip_endargv - after == old.ip_endargv - before);
    if (append) {
        const char *end = old.ip_endargv;
        for (int i = 0; i < old.ip_envc; i++) end += strlen(end) + 1;
        CHECK(memcmp(before, after, (size_t)(end - before)) == 0);
        CHECK(strcmp(after + (end - before), sweet_eagl_insert) == 0);
        size_t delta = (size_t)((new.ip_strendp - after) - (old.ip_strendp - before));
        CHECK(old.ip_argspace - new.ip_argspace == (int)delta + 8);
        CHECK(old.ip_strspace - new.ip_strspace == (int)delta);
        if (CASE("exact-fit")) CHECK(new.ip_argspace == 0);
        sweet_dyld_exec_trace(&new, &process);
    } else {
        CHECK(old.ip_strspace == new.ip_strspace && old.ip_argspace == new.ip_argspace);
        CHECK(old.ip_endenvv - before == new.ip_endenvv - after);
        CHECK(memcmp(before, after, (size_t)(old.ip_endenvv - before)) == 0);
    }
    if (CASE("one-short")) CHECK(old.ip_argspace > 0);
    printf("MODEL PASS outcome=%u reason=%u event=%u\n", expected, reason, event);
    free(before);
    free(after);
    return 0;
}
