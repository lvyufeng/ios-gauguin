/* Complete production diagnostics under typed OS boundaries; no device calls. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"MODEL FAIL %d %s\n",__LINE__,#x); exit(1); } } while (0)
#define NCARGS 262144
#define PAGE_SIZE 16384
#define MAXPATHLEN 1024
#ifndef __unused
#define __unused __attribute__((unused))
#endif
struct proc { int pid; }; typedef struct proc *proc_t;
struct image_params { char *ip_strings,*ip_startargv,*ip_endargv,*ip_endenvv,*ip_strendp; int ip_argc,ip_envc; };
static struct proc process={57};
static const char *scenario;
static bool is(const char *s) { return strcmp(scenario,s)==0; }
static unsigned sweet_exec_loader_probe=1,sweet_dyld_probe=1,calls,name_gets,name_puts,path_gets;
static char diagnostic[1024];
static int proc_pid(proc_t p) { CHECK(p==&process);return p->pid; }
static proc_t current_proc(void) { return is("file-nullproc") ? NULL : &process; }
static void proc_name(int pid,char *s,size_t n)
{ CHECK(pid==57);snprintf(s,n,"%s",is("file-wrongproc") ? "SpringBoard" : is("file-xpcproxy") ? "xpcproxy" : "backboardd"); }
static int model_printf(const char *format,...)
{ calls++;va_list ap;va_start(ap,format);int n=vsnprintf(diagnostic,sizeof(diagnostic),format,ap);va_end(ap);return n; }
#define printf model_printf
#include "production-exec.h"
struct vnode { int kind; }; typedef struct vnode *vnode_t;
#define NULLVP ((vnode_t)0)
#define VREG 1
typedef void *kauth_cred_t;
struct label;
struct fileops { int fo_type; };
struct fileglob { struct fileops *fg_ops; void *data; };
#define DTYPE_VNODE 1
#define FILEGLOB_DTYPE(fg) ((fg)->fg_ops->fo_type)
static struct vnode node={VREG};
static int vnode_vtype(vnode_t v) { CHECK(v==&node);return v->kind; }
static const char *vnode_getname(vnode_t v)
{ CHECK(v==&node);if(is("file-nullleaf"))return NULL;name_gets++;return is("file-wrongleaf") ? "other.dylib" : "libGauguinEAGLAdmission.dylib"; }
static void vnode_putname(const char *name) { CHECK(name!=NULL);name_puts++; }
static int vn_getpath(vnode_t v,char *p,int *n)
{
    CHECK(v==&node && *n==MAXPATHLEN);path_gets++;
    if(is("file-patherror"))return 5;
    if(is("file-emptylen")){*n=0;return 0;}
    if(is("file-oversizelen")){*n=MAXPATHLEN+1;return 0;}
    if(is("file-unterminated")){memset(p,'X',MAXPATHLEN);*n=MAXPATHLEN;return 0;}
    const char *s=is("file-pathalias") ? "/tmp/libGauguinEAGLAdmission.dylib" : "/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib";
    *n=(int)strlen(s)+1;memcpy(p,s,(size_t)*n);return 0;
}
static void *fg_get_data(struct fileglob *fg) { CHECK(fg!=NULL);return fg->data; }
#include "production-file.h"
#undef printf

static char *put(char *p,const char *s) { size_t n=strlen(s)+1;memcpy(p,s,n);return p+n; }
static void exec_case(void)
{
    size_t capacity=NCARGS+PAGE_SIZE;char *buf=calloc(1,capacity);CHECK(buf);
    struct image_params image={0};image.ip_strings=buf;
    bool proxy=is("exec-proxy")||is("exec-proxy-other-job");
    const char *path=proxy ? "executable_path=/usr/libexec/xpcproxy" : is("exec-otherimage") ? "executable_path=/usr/libexec/other" : is("exec-relativeimage") ? "executable_path=backboardd" : "executable_path=/usr/libexec/backboardd";
    char *p=put(buf,path);image.ip_startargv=p;p=put(p,proxy ? "xpcproxy" : "backboardd");image.ip_argc=1;
    if(proxy){p=put(p,is("exec-proxy-other-job") ? "com.apple.other" : "com.apple.backboardd");image.ip_argc++;}
    image.ip_endargv=p;unsigned inserted=1,expected=1,mode=1,admission=1;
    if(is("exec-no-env")){inserted=expected=mode=admission=0;}
    else {
        if(is("exec-missing-insert")){inserted=expected=0;}
        else if(is("exec-wrong-insert")){p=put(p,"DYLD_INSERT_LIBRARIES=/other.dylib");image.ip_envc++;expected=0;}
        else if(is("exec-false-key")){p=put(p,"DYLD_INSERT_LIBRARIES_EXTRA=private");image.ip_envc++;inserted=expected=0;}
        else {p=put(p,"DYLD_INSERT_LIBRARIES=/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib");image.ip_envc++;}
        if(is("exec-duplicate-insert")){p=put(p,"DYLD_INSERT_LIBRARIES=/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib");image.ip_envc++;inserted=expected=2;}
        p=put(p,is("exec-wrong-mode") ? "GAUGUIN_EAGL_MODE=render" : "GAUGUIN_EAGL_MODE=admission");image.ip_envc++;if(is("exec-wrong-mode"))admission=0;
        if(is("exec-empty-env")){p=put(p,"");image.ip_envc++;}
    }
    image.ip_endenvv=image.ip_strendp=p;bool event=true;proc_t proc=&process;
    if(is("exec-disabled")){sweet_exec_loader_probe=0;event=false;}
    if(is("exec-otherimage")||is("exec-relativeimage"))event=false;
    if(is("exec-nullproc")){proc=NULL;event=false;}
    if(is("exec-nullbase")){image.ip_strings=NULL;event=false;}
    if(is("exec-reversed")){image.ip_endargv=image.ip_startargv-1;event=false;}
    if(is("exec-envaftertail")){image.ip_strendp=image.ip_endenvv-1;event=false;}
    if(is("exec-tailpastcap")){image.ip_strendp=buf+capacity+1;event=false;}
    if(is("exec-negative-argc")){image.ip_argc=-1;event=false;}
    if(is("exec-negative-envc")){image.ip_envc=-1;event=false;}
    if(is("exec-argv-overcount")){image.ip_argc=(int)(image.ip_endargv-image.ip_startargv)+1;event=false;}
    if(is("exec-env-overcount")){image.ip_envc=(int)(image.ip_endenvv-image.ip_endargv)+1;event=false;}
    if(is("exec-path-nonul")){memset(buf,'X',(size_t)(image.ip_startargv-buf));event=false;}
    if(is("exec-argv-nonul")){image.ip_endargv[-1]='X';event=false;}
    if(is("exec-env-nonul")){image.ip_endenvv[-1]='X';event=false;}
    if(is("exec-address-overflow")){image.ip_strings=(char *)(UINTPTR_MAX-3);event=false;}
    if(is("exec-null-image"))event=false;
    struct image_params saved=image;char *before=malloc(capacity);CHECK(before);memcpy(before,buf,capacity);
    sweet_dyld_exec_trace(is("exec-null-image") ? NULL : &image,proc);
    CHECK(memcmp(&saved,&image,sizeof(image))==0 && memcmp(before,buf,capacity)==0 && calls==(unsigned)event);
    if(event){char want[1024];snprintf(want,sizeof(want),"SWEET DYLD EXEC: pid=57 image=%u argc=%d envc=%d job=%u insert=%u expected=%u mode=%u admission=%u\n",proxy ? 2u:1u,image.ip_argc,image.ip_envc,is("exec-proxy") ? 1u:0u,inserted,expected,mode,admission);CHECK(strcmp(diagnostic,want)==0);}
    free(before);free(buf);
}
static void file_case(void)
{
    bool mmap=strstr(scenario,"mmap")!=NULL || is("file-nullfg")||is("file-nullops")||is("file-pipe")||is("file-null-data");
    bool event=is("file-open")||is("file-xpcproxy")||is("file-mmap-read")||is("file-mmap-exec")||is("file-mmap-write")||is("file-mmap-null-maxprot");
    if(is("file-disabled"))sweet_dyld_probe=0;
    if(is("file-directory"))node.kind=2;
    struct fileops ops={is("file-pipe") ? 2:DTYPE_VNODE};struct fileglob fg={is("file-nullops") ? NULL:&ops,is("file-null-data") ? NULL:&node};
    int maximum=7,prot=is("file-mmap-exec") ? 5:is("file-mmap-write") ? 3:1;
    int rc=mmap ? sweet_dyld_probe_mmap(NULL,is("file-nullfg") ? NULL:&fg,NULL,prot,2,UINT64_C(0x100000000),is("file-mmap-null-maxprot") ? NULL:&maximum) : sweet_dyld_probe_open(NULL,is("file-nullvp") ? NULL:&node,NULL,1);
    CHECK(rc==0 && maximum==7 && calls==(unsigned)event && name_gets==name_puts);
    if(event){char want[1024];snprintf(want,sizeof(want),"SWEET DYLD FILE: pid=57 op=%u prot=%d flags=%d offset=%llu expected-path=1\n",mmap ? 2u:1u,mmap ? prot:1,mmap ? 2:0,mmap ? UINT64_C(0x100000000):UINT64_C(0));CHECK(strcmp(diagnostic,want)==0 && path_gets==1);}
}
int main(int argc,char **argv)
{
    CHECK(argc==2);scenario=argv[1];
    if(strncmp(scenario,"exec-",5)==0)exec_case();else file_case();
    CHECK(name_gets==name_puts);printf("MODEL PASS case=%s read_only=1 references_balanced=1\n",scenario);return 0;
}
