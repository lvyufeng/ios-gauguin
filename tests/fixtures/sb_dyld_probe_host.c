/* Complete production probe and kernel MAC dispatcher with typed OS seams.
 * This is a host model, never a process or policy on the physical phone.
 */
#include <errno.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"MODEL FAIL line=%d: %s\n",__LINE__,#x); exit(1); } } while (0)
typedef uint64_t user_addr_t;
struct proc { int pid; }; typedef struct proc *proc_t;
#define PROC_NULL ((proc_t)0)
struct credential { uid_t uid,ruid; }; typedef struct credential *kauth_cred_t;
struct mount { unsigned flags; }; typedef struct mount *mount_t;
struct vnode { int which; }; typedef struct vnode *vnode_t;
#define NULLVP ((vnode_t)0)
#define VREG 1
#define MNT_ROOTFS 0x4000
#define VNODE_LOOKUP_NOFOLLOW 1
#define VNODE_LOOKUP_NOCROSSMOUNT 2
#define KAUTH_VNODE_WRITE_DATA 2
struct vnode_attr { unsigned active,supported; uid_t va_uid;mode_t va_mode; };
#define VATTR_INIT(p) memset((p),0,sizeof(*(p)))
#define VATTR_WANTED(p,f) ((p)->active |= VNODE_ATTR_ ## f)
#define VATTR_IS_SUPPORTED(p,f) ((p)->supported & VNODE_ATTR_ ## f)
#define VNODE_ATTR_va_uid 1
#define VNODE_ATTR_va_mode 2
typedef int vfs_context_t;
static const char *scenario;
static bool is(const char *s) { return strcmp(scenario,s)==0; }
static struct proc process={57},other_process={58};
static struct credential credential;
static struct mount root_mount;
static struct vnode binary={1},different_binary={2};
static unsigned cred_refs,cred_puts,vnode_refs,vnode_puts,lookups,attrs,authorizations,copyins,copyouts;
static uint32_t sweet_dyld_probe;
static uint32_t sweet_sb_rate_probe;
static char diagnostic[1024];
static proc_t current_proc(void) { return &process; }
static int proc_pid(proc_t p) { return p->pid; }
static bool sb_case(void) { return strncmp(scenario,"sb-",3)==0; }
static void proc_name(int pid,char *name,size_t bytes)
{ CHECK(pid==57);snprintf(name,bytes,"%s",(sb_case()&&!is("sb-backboard-disabled"))||is("wrong-name") ? "SpringBoard" : "backboardd"); }
static kauth_cred_t kauth_cred_proc_ref(proc_t p)
{ CHECK(p==&process);if(is("missing-credential"))return NULL;cred_refs++;return &credential; }
static uid_t kauth_cred_getuid(kauth_cred_t c) { CHECK(c==&credential);return c->uid; }
static uid_t kauth_cred_getruid(kauth_cred_t c) { CHECK(c==&credential);return c->ruid; }
static void kauth_cred_unref(kauth_cred_t *c)
{ CHECK(*c==&credential);cred_puts++;*c=NULL; }
static vnode_t proc_getexecutablevnode(proc_t p)
{ CHECK(p==&process);if(is("missing-executable"))return NULLVP;vnode_refs++;return is("wrong-executable") ? &different_binary : &binary; }
static vfs_context_t vfs_context_kernel(void) { return 1; }
static vfs_context_t vfs_context_current(void) { return 2; }
static int vnode_lookup(const char *path,int flags,vnode_t *vp,vfs_context_t context)
{
    lookups++;CHECK(strcmp(path,sb_case() ? "/System/Library/CoreServices/SpringBoard.app/SpringBoard" : "/usr/libexec/backboardd")==0 && flags==3 && context==1 && *vp==NULLVP);
    if(is("lookup-failure")||is("sb-lookup-failure"))return ENOENT;
    vnode_refs++;*vp=&binary;return 0;
}
static int vnode_vtype(vnode_t vp) { CHECK(vp==&binary);return is("wrong-vnode-type")||is("sb-wrong-vnode-type") ? 2 : VREG; }
static mount_t vnode_mount(vnode_t vp) { CHECK(vp==&binary);return is("missing-mount") ? NULL : &root_mount; }
static unsigned vfs_flags(mount_t mp) { CHECK(mp==&root_mount);return mp->flags; }
static int vnode_getattr(vnode_t vp,struct vnode_attr *a,vfs_context_t context)
{
    attrs++;CHECK(vp==&binary && context==1 && a->active==3);
    if(is("getattr-failure"))return EIO;
    a->supported=is("missing-owner-attribute") ? 2 : is("missing-mode-attribute") ? 1 : 3;
    a->va_uid=is("nonroot-file-owner") ? 501 : 0;
    a->va_mode=0755 | (is("group-writable") ? S_IWGRP : 0) | ((is("world-writable")||is("sb-world-writable")) ? S_IWOTH : 0);
    return 0;
}
static int vnode_authorize(vnode_t vp,vnode_t parent,unsigned action,vfs_context_t context)
{ authorizations++;CHECK(vp==&binary && parent==NULLVP && action==2 && context==2);return is("ACL-writable")||is("sb-ACL-writable") ? 0 : is("ACL-query-failure") ? EIO : is("ACL-denied-EPERM") ? EPERM : EACCES; }
static void vnode_put(vnode_t vp) { CHECK(vp==&binary || vp==&different_binary);vnode_puts++; }
static int copyin(user_addr_t from,void *to,size_t n)
{ copyins++;CHECK(n==16);if(is("copyin-failure"))return EFAULT;memcpy(to,(void *)(uintptr_t)from,n);return 0; }
static int copyout(const void *from,user_addr_t to,size_t n)
{ copyouts++;CHECK(n==8);if(is("copyout-failure"))return EFAULT;memcpy((void *)(uintptr_t)to,from,n);return 0; }
static int model_printf(const char *fmt,...)
{ va_list ap;va_start(ap,fmt);int n=vsnprintf(diagnostic,sizeof(diagnostic),fmt,ap);va_end(ap);return n; }
#define printf model_printf
#include "production-probe.h"
#undef printf

#define MAC_MAX_POLICY_NAME 32
#define AUDIT_ARG(...) ((void)0)
struct mac_policy_ops { int (*mpo_policy_syscall)(proc_t,int,user_addr_t); };
struct mac_policy_conf { const char *mpc_name;struct mac_policy_ops *mpc_ops; };
static struct { unsigned staticmax,maxindex;struct { struct mac_policy_conf *mpc; } entries[3]; } mac_policy_list;
struct __mac_syscall_args { user_addr_t policy;int call;user_addr_t arg; };
static int copyinstr(user_addr_t from,char *to,size_t n,size_t *length)
{ if(is("policy-copyinstr-failure"))return EFAULT;size_t len=strlen((const char *)(uintptr_t)from)+1;CHECK(len<=n);memcpy(to,(void *)(uintptr_t)from,len);*length=len;return 0; }
static int mac_proc_check_mac_syscall(proc_t p,const char *target,int call)
{ (void)p;(void)target;(void)call;return is("MAC-dispatch-denial") ? EACCES : 0; }
static int mac_policy_list_conditional_busy(void) { return 0; }
static void mac_policy_list_unbusy(void) { CHECK(false); }
#include "production-dispatch.h"

int main(int argc,char **argv)
{
    CHECK(argc==2);scenario=argv[1];sweet_dyld_probe=!is("probe-disabled")&&!is("sb-backboard-disabled");sweet_sb_rate_probe=sb_case()&&!is("sb-disabled");credential=(struct credential){501,501};root_mount.flags=MNT_ROOTFS;
    if(is("root-compositor"))credential=(struct credential){0,0};
    if(is("wrong-uid"))credential=(struct credential){502,502};
    if(is("sb-wrong-uid"))credential=(struct credential){0,0};
    if(is("credential-mismatch"))credential=(struct credential){501,0};
    if(is("nonroot-mount")||is("sb-nonroot-mount"))root_mount.flags=0;
    struct mac_policy_ops none={NULL},probe={sweet_dyld_probe_syscall};
    struct mac_policy_conf old1={"SWEET AMFI",&none},old2={"Sandbox",&none},new_policy={"AMFI",&probe};
    mac_policy_list.entries[0].mpc=&old1;mac_policy_list.entries[1].mpc=&old2;mac_policy_list.entries[2].mpc=&new_policy;
    mac_policy_list.staticmax=is("old-policy-missing") ? 2 : 3;mac_policy_list.maxindex=mac_policy_list.staticmax-1;
    uint64_t flags=UINT64_C(0xaaaaaaaaaaaaaaaa);
    struct sweet_dyld_policy_args args={0,(user_addr_t)(uintptr_t)&flags};
    if(is("input-restricted"))args.input_flags=2;
    if(is("input-encrypted"))args.input_flags=4;
    if(is("input-both"))args.input_flags=6;
    if(is("unknown-input-bit0"))args.input_flags=1;
    if(is("unknown-input-bit3"))args.input_flags=8;
    if(is("null-output"))args.output_flags=0;
    if(is("unaligned-output"))args.output_flags++;
    struct __mac_syscall_args request={(user_addr_t)(uintptr_t)(is("wrong-policy") ? "Other" : "AMFI"),is("wrong-call") ? 91 : 90,(user_addr_t)(uintptr_t)&args};
    proc_t caller=is("null-process") ? PROC_NULL : is("not-current-process") ? &other_process : &process;
    int ignored=0;int result=__mac_syscall(caller,&request,&ignored);
    bool good=is("trusted")||is("root-compositor")||is("input-restricted")||is("input-encrypted")||is("input-both")||is("ACL-denied-EPERM")||is("sb-trusted");
    int wanted=good ? 0 : is("unknown-input-bit0")||is("unknown-input-bit3") ? EINVAL : is("copyin-failure")||is("copyout-failure")||is("null-output")||is("unaligned-output")||is("policy-copyinstr-failure") ? EFAULT : is("MAC-dispatch-denial") ? EACCES : ENOPOLICY;
    CHECK(result==wanted);CHECK(cred_refs==cred_puts && vnode_refs==vnode_puts);
    CHECK(flags==(good ? 2 : UINT64_C(0xaaaaaaaaaaaaaaaa)));
    uint64_t actual_delegate_flags=result==0 ? flags : 0;CHECK(actual_delegate_flags==(good ? 2 : 0));
    if(good)CHECK(copyins==1 && copyouts==1 && strstr(diagnostic,"output-mask=2 rc=0"));
    if(result==ENOPOLICY)CHECK(copyins==0 && copyouts==0);
    if(is("root-compositor"))CHECK(authorizations==0);
    if(is("sb-trusted"))CHECK(authorizations==1 && strstr(diagnostic,"SWEET SB DYLD PROBE"));
    CHECK((actual_delegate_flags & ~UINT64_C(2))==0);
    printf("MODEL PASS case=%s rc=%d delegate_flags=%llu references_balanced=1\n",scenario,result,(unsigned long long)actual_delegate_flags);
    return 0;
}
