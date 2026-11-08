/* Actual probe function; only POSIX child/time boundaries are typed seams. */
#include <assert.h>
#include <errno.h>
#include <spawn.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
extern char **environ;
static struct {unsigned mode,spawns,waits,clocks,sleeps,failures;uint64_t elapsed;} model;
static int fail(const char *where){assert(where&&*where);++model.failures;return 1;}
static int fixture_spawn(pid_t *pid,const char *path,const posix_spawn_file_actions_t *actions,
    const posix_spawnattr_t *attrs,char *const args[],char *const env[])
{
    ++model.spawns;assert(!actions&&!attrs&&env==environ);
    assert(!strcmp(path,"/usr/libexec/gauguin-gpu-probe")&&!strcmp(args[0],path)&&!strcmp(args[1],"gwrt-0175-a1")&&!args[2]);
    if(model.mode==1)return EIO;*pid=101;return 0;
}
static pid_t fixture_wait(pid_t pid,int *status,int options)
{
    assert(pid==101&&!options);++model.waits;
    if(model.mode==2&&model.waits==1){errno=EINTR;return -1;}
    if(model.mode==12){errno=EIO;return -1;}
    *status=model.mode==4?256:model.mode==5?15:0;
    return model.mode==3?102:101;
}
static int fixture_clock(clockid_t clock,struct timespec *t)
{
    assert(clock==CLOCK_MONOTONIC_RAW);++model.clocks;
    if((model.mode==6&&model.clocks==1)||(model.mode==9&&model.clocks==2))return -1;
    uint64_t ns=UINT64_C(10000000000)+model.elapsed;
    if(model.clocks==2&&model.mode==10)ns=UINT64_C(99000000000); /* only89s */
    if(model.clocks==2&&model.mode==11)ns=UINT64_C(9000000000); /* backwards */
    *t=(struct timespec){(time_t)(ns/1000000000),(long)(ns%1000000000)};return 0;
}
static int fixture_sleep(const struct timespec *wanted,struct timespec *remaining)
{
    uint64_t ns=(uint64_t)wanted->tv_sec*1000000000+wanted->tv_nsec;assert(ns>0&&ns<=UINT64_C(90000000000));++model.sleeps;
    if(model.mode==7){errno=EINVAL;return -1;}
    if((model.mode==8&&model.sleeps==1)||(model.mode==13&&model.sleeps<=3)) {
        model.elapsed+=1000000000;ns-=1000000000;
        *remaining=(struct timespec){(time_t)(ns/1000000000),(long)(ns%1000000000)};errno=EINTR;return -1;
    }
    model.elapsed+=ns;return 0;
}
#define posix_spawn fixture_spawn
#define waitpid fixture_wait
#define clock_gettime fixture_clock
#define nanosleep fixture_sleep
@FUNCTION@
#undef posix_spawn
#undef waitpid
#undef clock_gettime
#undef nanosleep
int main(void)
{
    for(unsigned mode=0;mode<14;mode++) {
        memset(&model,0,sizeof(model));model.mode=mode;
        bool success=mode==0||mode==2||mode==8||mode==13;
        assert((api_then_late_workload()==0)==success&&model.spawns==1);
        if(success)assert(model.elapsed==UINT64_C(90000000000)&&model.clocks==2&&!model.failures);
        else assert(model.failures==1);
        if(mode==1)assert(!model.waits&&!model.sleeps&&!model.clocks);
        if(mode==2)assert(model.waits==2);
        if(mode==3||mode==4||mode==5||mode==12)assert(!model.sleeps&&!model.clocks);
        if(mode==8)assert(model.sleeps==2);
        if(mode==13)assert(model.sleeps==4);
    }
    puts("PASS: 14 actual child/delay ordering scenarios; no child launch, real sleep or hardware qualification");
}
