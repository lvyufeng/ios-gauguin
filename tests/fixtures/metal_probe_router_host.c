/* Real router, hash/file IO and spawn attributes; modeled credentials/SETEXEC. MIT. */
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <setjmp.h>
#include <spawn.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
#include "GauguinProbeRouterTargets.h"
extern int gauguin_router_main(int,char **);
extern char **environ;
static const char *scenario;
static unsigned stats,memcalls,spawns,jetsamcalls;
static const posix_spawnattr_t *jetsam_attr;
static jmp_buf replacement;
#define CASE(x) (!strcmp(scenario,x))
uid_t router_getuid(void){return CASE("uid")?501:0;}
uid_t router_geteuid(void){return CASE("euid")?501:0;}
const char *router_getprogname(void){return CASE("program")?"other":"gauguin-gpu-probe-router";}
int router_sysctl(const char *key,void *out,size_t *n,void *newp,size_t newn)
{
    assert(!newp&&!newn);const char *s="20H392";
    if(!strcmp(key,"kern.osversion")){if(CASE("version"))s="20H391";}
    else {
        assert(!strcmp(key,"kern.bootargs"));s="sweeteagl=1 gmt=1 sweet_dyld_probe=1";
        if(CASE("desktop"))s="sweeteagl=2 gmt=2 sweet_dyld_probe=1";
        if(CASE("legacy"))s="sweeteagl=2 sweet_dyld_probe=1";
        if(CASE("mode-prefix"))s="xsweeteagl=2 gmt=2 sweet_dyld_probe=1";
        if(CASE("mode-duplicate"))s="sweeteagl=2 gmt=2 gmt=2 sweet_dyld_probe=1";
        if(CASE("mode-conflict"))s="sweeteagl=2 gmt=1 sweet_dyld_probe=1";
        if(CASE("mode-one-two"))s="sweeteagl=1 gmt=2 sweet_dyld_probe=1";
        if(CASE("mode-empty"))s="";
    }
    assert(*n>=strlen(s)+1);memcpy(out,s,strlen(s)+1);*n=strlen(s)+1;return 0;
}
int router_fstat(int fd,struct stat *st)
{
    int rc=fstat(fd,st);if(rc)return rc;stats++;st->st_uid=st->st_gid=0;
    if(CASE("target-owner"))st->st_uid=501;
    if(CASE("target-group"))st->st_gid=501;
    if(CASE("target-mode"))st->st_mode|=S_IWGRP;
    if(CASE("target-link"))st->st_nlink=2;
    if(CASE("target-size"))st->st_size--;
    if(CASE("target-changed")&&stats==2)st->st_ino++;
    return 0;
}
int router_mem(uint32_t command,int32_t pid,uint32_t flags,void *buffer,size_t n)
{
    assert(pid==getpid()&&!flags);memcalls++;
    if(command==1) {
        struct {int32_t pid,priority;uint64_t user;int32_t limit;uint32_t state;} v={getpid(),17,0,128,0};
        assert(n==sizeof(v));if(CASE("priority"))v.priority=-1;if(CASE("priority-pid"))v.pid++;
        memcpy(buffer,&v,n);return (int)n;
    }
    assert(command==8);struct {int32_t active;uint32_t a;int32_t inactive;uint32_t i;} v={128,1,128,1};
    assert(n==sizeof(v));if(CASE("memory-active"))v.active=6;if(CASE("memory-inactive"))v.inactive=-1;if(CASE("memory-fatal"))v.i=0;
    memcpy(buffer,&v,n);return 0;
}
int router_jetsam(posix_spawnattr_t *attr,short flags,int priority,int active,int inactive)
{
    assert(flags==0x0c&&priority==17&&active==128&&inactive==128);jetsamcalls++;jetsam_attr=attr;
    return CASE("spawn-jetsam")?EINVAL:0;
}
int router_spawn(pid_t *pid,const char *path,const posix_spawn_file_actions_t *actions,
                 const posix_spawnattr_t *attr,char *const argv[],char *const env[])
{
    spawns++;short flags=0;assert(!pid&&!actions&&attr==jetsam_attr&&env==environ);
    assert(!posix_spawnattr_getflags(attr,&flags)&&flags==POSIX_SPAWN_SETEXEC);
    const struct gauguin_router_target *want=CASE("desktop")?&gauguin_router_bootstrap:&gauguin_router_retained;
    assert(!strcmp(path,want->path)&&!strcmp(argv[0],want->path)&&!strcmp(argv[1],want->argument)&&!argv[2]);
    if(CASE("spawn-error"))return EIO;
    if(CASE("spawn-return"))return 0;
    /* Model replacement; release host test attributes before leaving the router. */
    assert(!posix_spawnattr_destroy((posix_spawnattr_t *)attr));longjmp(replacement,1);
}
int main(int argc,char **argv)
{
    assert(argc==2);scenario=argv[1];pid_t before=getpid();
    if(CASE("target-hash")) {int fd=open(gauguin_router_retained.path,O_WRONLY);assert(fd>=0&&write(fd,"!",1)==1&&!close(fd));}
    if(CASE("target-symlink")) {assert(!unlink(gauguin_router_retained.path));assert(!symlink(gauguin_router_bootstrap.path,gauguin_router_retained.path));}
    bool expected=CASE("diag")||CASE("legacy")||CASE("desktop");
    char *args[]={"gauguin-gpu-probe-router","--route247",NULL};if(CASE("arguments"))args[1]="--other";
    bool replaced=false;
    if(!setjmp(replacement)) {int rc=gauguin_router_main(2,args);assert(rc!=0&&!expected);}
    else replaced=true;
    assert(getpid()==before&&replaced==expected);
    assert(spawns==(unsigned)(expected||CASE("spawn-error")||CASE("spawn-return")));
    if(expected)assert(jetsamcalls==1&&memcalls==2&&stats==2);
    printf("PASS router %s: replacement=%u spawn_calls=%u; no real spawn\n",scenario,replaced,spawns);return 0;
}
