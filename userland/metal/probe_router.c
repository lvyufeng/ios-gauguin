/* Hash-checked SETEXEC routing, preserving the existing diagnostic/legacy image. MIT. */
#include "router_policy.h"
#include "GauguinProbeRouterTargets.h"
#include <CommonCrypto/CommonDigest.h>
#include <errno.h>
#include <fcntl.h>
#include <spawn.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sysctl.h>
#include <unistd.h>

extern int memorystatus_control(uint32_t,int32_t,uint32_t,void *,size_t);
extern int posix_spawnattr_setjetsam_ext(posix_spawnattr_t *,short,int,int,int);
extern char **environ;
struct router_limits {int32_t active;uint32_t active_attr;int32_t inactive;uint32_t inactive_attr;};
struct router_priority {int32_t pid,priority;uint64_t user_data;int32_t limit;uint32_t state;};
_Static_assert(sizeof(struct router_limits)==16,"GET8 layout");
_Static_assert(sizeof(struct router_priority)==24,"GET1 layout");

static int failure(const char *phase,int code)
{
    fprintf(stderr,"GAUGUIN ROUTER247 FAIL phase=%s code=%d\n",phase,code);
    return 1;
}
static bool target_verified(const struct gauguin_router_target *target)
{
    int fd=open(target->path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);struct stat before={0},after={0};
    if(fd<0)return false;
    bool valid=fstat(fd,&before)==0&&gauguin_router_metadata(&before,target->bytes);
    unsigned char *data=valid?malloc((size_t)target->bytes):NULL;
    valid=valid&&data;size_t at=0;unsigned interruptions=0;
    while(valid&&at<target->bytes) {
        ssize_t n=read(fd,data+at,(size_t)target->bytes-at);
        if(n<0&&errno==EINTR&&++interruptions<=100)continue;
        if(n<=0){valid=false;break;}
        at+=(size_t)n;
    }
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    if(valid)valid=CC_SHA256(data,(CC_LONG)target->bytes,digest)!=NULL&&
                   !memcmp(digest,target->sha256,sizeof(digest));
    if(valid)valid=fstat(fd,&after)==0&&gauguin_router_metadata(&after,target->bytes)&&
                   before.st_dev==after.st_dev&&before.st_ino==after.st_ino&&
                   before.st_mtime==after.st_mtime&&before.st_ctime==after.st_ctime;
    free(data);if(close(fd))valid=false;return valid;
}
int main(int argc,char **argv)
{
    if(argc!=2||strcmp(argv[1],"--route247"))return failure("arguments",2);
    char args[1024]={0},version[64]={0};size_t n=sizeof(args)-1,v=sizeof(version)-1;
    if(sysctlbyname("kern.bootargs",args,&n,NULL,0)||n>=sizeof(args)||
       sysctlbyname("kern.osversion",version,&v,NULL,0)||v>=sizeof(version)||
       !gauguin_router_identity(getuid(),geteuid(),getprogname(),version))return failure("identity",2);
    enum gauguin_router_route route=gauguin_router_select(args);
    if(route==GRR_REJECT)return failure("profile",2);
    const struct gauguin_router_target *target=route==GRR_BOOTSTRAP?&gauguin_router_bootstrap:&gauguin_router_retained;
    if(!target_verified(target))return failure("target",errno);
    struct router_priority priority={0};struct router_limits limits={0};
    if(memorystatus_control(1,getpid(),0,&priority,sizeof(priority))!=(int)sizeof(priority)||
       priority.pid!=getpid()||priority.priority<0||
       memorystatus_control(8,getpid(),0,&limits,sizeof(limits))||
       limits.active!=128||limits.inactive!=128||limits.active_attr!=1||limits.inactive_attr!=1)
        return failure("memory",1);
    posix_spawnattr_t attr;int rc=posix_spawnattr_init(&attr);
    if(rc)return failure("spawn-init",rc);
    rc=posix_spawnattr_setflags(&attr,POSIX_SPAWN_SETEXEC);
    if(!rc)rc=posix_spawnattr_setjetsam_ext(&attr,0x0c,priority.priority,128,128);
    if(rc){posix_spawnattr_destroy(&attr);return failure("spawn-attributes",rc);}
    char *const next[]={(char *)target->path,(char *)target->argument,NULL};
    fprintf(stderr,"GAUGUIN ROUTER247 selected=%s target=%s hard_mb=128 priority=%d build=%s\n",
            route==GRR_BOOTSTRAP?"bootstrap":"retained",target->path,priority.priority,GAUGUIN_ROUTER_BUILD);
    fflush(NULL);
    /* The successful call replaces this image: no second PID or GPU owner. */
    rc=posix_spawn(NULL,target->path,NULL,&attr,next,environ);
    posix_spawnattr_destroy(&attr);
    return failure(rc?"SETEXEC":"SETEXEC-returned",rc);
}
