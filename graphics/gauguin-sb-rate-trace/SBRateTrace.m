/* SPDX-License-Identifier: MIT
 * Read-only SpringBoard CA timing probe for iOS 16.7 (20H392).
 * The observation points follow HakiOS's inject_sb.c at 63fc2b4, but no
 * animation, display-link range, or CoreAnimation policy is changed here.
 */
#import <Foundation/Foundation.h>
#import <QuartzCore/QuartzCore.h>
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <mach/mach_time.h>
#include <objc/runtime.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysctl.h>
#include <unistd.h>

#define RATE_ROWS 256u
#define CA_COMMIT_ORDER 2000000

enum rate_kind { RATE_ANIMATION=1, RATE_LINK_FPS, RATE_LINK_RANGE, RATE_MAIN_TURN };
struct rate_row {
    uint64_t us, a, b, c;
    uintptr_t caller;
    uint32_t kind;
    float minimum, maximum, preferred;
    long fps;
    char class_name[40], key[40];
};

static struct rate_row rows[RATE_ROWS];
static pthread_mutex_t rows_lock=PTHREAD_MUTEX_INITIALIZER;
static uint32_t rows_head, rows_count;
static _Atomic uint64_t rows_lost;
static mach_timebase_info_data_t timebase;
static _Atomic bool enabled;
static uint64_t main_woke, commit_began;
static void (*old_add_animation)(id,SEL,id,id);
static void (*old_link_fps)(id,SEL,long);
static void (*old_link_range)(id,SEL,CAFrameRateRange);

static uint64_t
now_us(void)
{
    return (uint64_t)(((__uint128_t)mach_absolute_time()*timebase.numer)/timebase.denom/1000);
}

static bool
has_token(const char *line,const char *token)
{
    size_t n=strlen(token);
    for(const char *p=line;(p=strstr(p,token))!=NULL;++p)
        if((p==line||p[-1]==' ')&&(p[n]==' '||p[n]=='\0'))return true;
    return false;
}

static void
copy_printable(char *out,size_t capacity,const char *in)
{
    size_t at=0;
    if(in!=NULL)for(;at+1<capacity&&in[at]!='\0';++at) {
        unsigned char ch=(unsigned char)in[at];
        out[at]=(ch>=33&&ch<=126)?(char)ch:'?';
    }
    out[at]='\0';
}

static void
record_row(const struct rate_row *row)
{
    if(!atomic_load_explicit(&enabled,memory_order_acquire))return;
    if(pthread_mutex_trylock(&rows_lock)!=0) {
        atomic_fetch_add_explicit(&rows_lost,1,memory_order_relaxed);
        return;
    }
    rows[rows_head]=*row;
    rows_head=(rows_head+1)%RATE_ROWS;
    if(rows_count<RATE_ROWS)++rows_count;
    else atomic_fetch_add_explicit(&rows_lost,1,memory_order_relaxed);
    pthread_mutex_unlock(&rows_lock);
}

static void
write_line(const char *line)
{
    size_t left=strlen(line);
    while(left) {
        ssize_t n=write(STDERR_FILENO,line,left);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)break;
        left-=(size_t)n;
        line+=n;
    }
}

static void
caller_name(uintptr_t address,char *out,size_t capacity)
{
    Dl_info info;
    if(dladdr((void *)address,&info)==0||info.dli_fname==NULL) {
        snprintf(out,capacity,"unknown");
        return;
    }
    const char *slash=strrchr(info.dli_fname,'/');
    const char *name=slash?slash+1:info.dli_fname;
    snprintf(out,capacity,"%.48s+%#llx",name,
        (unsigned long long)(address-(uintptr_t)info.dli_fbase));
}

static void
flush_row(const struct rate_row *row)
{
    char line[320],caller[80];
    if(row->kind==RATE_MAIN_TURN) {
        snprintf(line,sizeof(line),"SWEET SB TURN: woke_us=%llu before_ca_us=%llu after_ca_us=%llu\n",
            (unsigned long long)row->a,(unsigned long long)row->b,
            (unsigned long long)row->c);
    } else {
        caller_name(row->caller,caller,sizeof(caller));
        if(row->kind==RATE_ANIMATION) {
            snprintf(line,sizeof(line),"SWEET SB RATE: us=%llu kind=animation class=%s key=%s min=%.1f max=%.1f preferred=%.1f caller=%s\n",
                (unsigned long long)row->us,row->class_name,row->key,
                row->minimum,row->maximum,row->preferred,caller);
        } else if(row->kind==RATE_LINK_FPS) {
            snprintf(line,sizeof(line),"SWEET SB RATE: us=%llu kind=link-fps asked=%ld caller=%s\n",
                (unsigned long long)row->us,row->fps,caller);
        } else {
            snprintf(line,sizeof(line),"SWEET SB RATE: us=%llu kind=link-range min=%.1f max=%.1f preferred=%.1f caller=%s\n",
                (unsigned long long)row->us,row->minimum,row->maximum,
                row->preferred,caller);
        }
    }
    write_line(line);
}

static void *
flush_thread(void *unused)
{
    (void)unused;
    struct rate_row batch[RATE_ROWS];
    for(;;) {
        sleep(1);
        pthread_mutex_lock(&rows_lock);
        uint32_t count=rows_count;
        uint32_t start=(rows_head+RATE_ROWS-count)%RATE_ROWS;
        for(uint32_t i=0;i<count;++i)batch[i]=rows[(start+i)%RATE_ROWS];
        rows_count=0;
        pthread_mutex_unlock(&rows_lock);
        uint64_t lost=atomic_exchange_explicit(&rows_lost,0,memory_order_relaxed);
        for(uint32_t i=0;i<count;++i)flush_row(batch+i);
        if(lost) {
            char line[100];
            snprintf(line,sizeof(line),"SWEET SB RATE: lost=%llu\n",(unsigned long long)lost);
            write_line(line);
        }
    }
    return NULL;
}

static void
add_animation(id self,SEL selector,id animation,id key)
{
    if(animation!=nil&&[animation respondsToSelector:@selector(preferredFrameRateRange)]) {
        CAFrameRateRange range=[(CAAnimation *)animation preferredFrameRateRange];
        struct rate_row row={0};
        row.kind=RATE_ANIMATION;
        row.us=now_us();
        row.caller=(uintptr_t)__builtin_return_address(0);
        row.minimum=range.minimum;
        row.maximum=range.maximum;
        row.preferred=range.preferred;
        copy_printable(row.class_name,sizeof(row.class_name),object_getClassName(animation));
        if([key isKindOfClass:[NSString class]])
            copy_printable(row.key,sizeof(row.key),[(NSString *)key UTF8String]);
        record_row(&row);
    }
    old_add_animation(self,selector,animation,key);
}

static void
set_link_fps(id self,SEL selector,long fps)
{
    struct rate_row row={0};
    row.kind=RATE_LINK_FPS;
    row.us=now_us();
    row.caller=(uintptr_t)__builtin_return_address(0);
    row.fps=fps;
    record_row(&row);
    old_link_fps(self,selector,fps);
}

static void
set_link_range(id self,SEL selector,CAFrameRateRange range)
{
    struct rate_row row={0};
    row.kind=RATE_LINK_RANGE;
    row.us=now_us();
    row.caller=(uintptr_t)__builtin_return_address(0);
    row.minimum=range.minimum;
    row.maximum=range.maximum;
    row.preferred=range.preferred;
    record_row(&row);
    old_link_range(self,selector,range);
}

static void
main_turn(CFRunLoopObserverRef observer,CFRunLoopActivity activity,void *info)
{
    (void)observer;
    if(activity==kCFRunLoopAfterWaiting) {
        main_woke=now_us();
        commit_began=0;
    } else if(activity==kCFRunLoopBeforeWaiting&&info==NULL) {
        commit_began=now_us();
    } else if(activity==kCFRunLoopBeforeWaiting&&main_woke) {
        struct rate_row row={0};
        row.kind=RATE_MAIN_TURN;
        row.us=now_us();
        row.a=main_woke;
        row.b=commit_began;
        row.c=row.us;
        record_row(&row);
        main_woke=0;
    }
}

static void
add_observer(CFRunLoopActivity activity,CFIndex order,void *info)
{
    CFRunLoopObserverContext context={0};
    context.info=info;
    CFRunLoopObserverRef observer=CFRunLoopObserverCreate(NULL,activity,true,order,main_turn,&context);
    if(observer!=NULL) {
        CFRunLoopAddObserver(CFRunLoopGetMain(),observer,kCFRunLoopCommonModes);
        CFRelease(observer);
    }
}

__attribute__((constructor))
static void
start_rate_trace(void)
{
    const char *process=getprogname();
    char args[1024]={0};
    size_t size=sizeof(args)-1;
    if(process==NULL||strcmp(process,"SpringBoard")!=0||
        sysctlbyname("kern.bootargs",args,&size,NULL,0)!=0||
        !has_token(args,"touch_lat=1")||
        mach_timebase_info(&timebase)!=KERN_SUCCESS||
        !timebase.numer||!timebase.denom)return;
    Class layer=objc_getClass("CALayer");
    Class link=objc_getClass("CADisplayLink");
    Method add=layer?class_getInstanceMethod(layer,sel_registerName("addAnimation:forKey:")):NULL;
    Method fps=link?class_getInstanceMethod(link,sel_registerName("setPreferredFramesPerSecond:")):NULL;
    Method range=link?class_getInstanceMethod(link,sel_registerName("setPreferredFrameRateRange:")):NULL;
    if(add==NULL||method_getNumberOfArguments(add)!=4)return;
    pthread_t thread;
    if(pthread_create(&thread,NULL,flush_thread,NULL)!=0)return;
    pthread_detach(thread);
    atomic_store_explicit(&enabled,true,memory_order_release);
    old_add_animation=(void (*)(id,SEL,id,id))method_getImplementation(add);
    method_setImplementation(add,(IMP)add_animation);
    if(fps!=NULL&&method_getNumberOfArguments(fps)==3) {
        old_link_fps=(void (*)(id,SEL,long))method_getImplementation(fps);
        method_setImplementation(fps,(IMP)set_link_fps);
    }
    if(range!=NULL&&method_getNumberOfArguments(range)==3) {
        old_link_range=(void (*)(id,SEL,CAFrameRateRange))method_getImplementation(range);
        method_setImplementation(range,(IMP)set_link_range);
    }
    add_observer(kCFRunLoopAfterWaiting,LONG_MIN,NULL);
    add_observer(kCFRunLoopBeforeWaiting,CA_COMMIT_ORDER-1,NULL);
    add_observer(kCFRunLoopBeforeWaiting,CA_COMMIT_ORDER+1,(void *)1);
    char line[160];
    snprintf(line,sizeof(line),"SWEET SB RATE: active animation=1 link_fps=%u link_range=%u loop=1 flush=1; read-only\n",
        old_link_fps!=NULL,old_link_range!=NULL);
    write_line(line);
}
