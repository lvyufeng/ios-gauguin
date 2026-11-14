/* SPDX-License-Identifier: MIT
 * Read-only SpringBoard CA timing probe for iOS 16.7 (20H392).
 * The observation points follow HakiOS's inject_sb.c at 63fc2b4, but no
 * animation, display-link range, or CoreAnimation policy is changed here.
 */
#import <Foundation/Foundation.h>
#import <QuartzCore/QuartzCore.h>
#import <UIKit/UIKit.h>
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <math.h>
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

#define RATE_ROWS 512u
#define CA_COMMIT_ORDER 2000000

enum rate_kind { RATE_ANIMATION=1, RATE_LINK_FPS, RATE_LINK_RANGE, RATE_MAIN_TURN,
                 RATE_INPUT_BEGIN, RATE_INPUT_END };
struct rate_row {
    uint64_t us, a, b, c;
    uintptr_t caller;
    uint32_t kind, flags, phases;
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
/* One coherent word: turn start in us, low bits 0=last before-wait observer,
 * 1=body, 2=before-CA, 3=after-CA (zero start means unobserved/invalid).
 * These are observer milestones, not a sampled CPU backtrace. The watch never
 * wakes or suspends the main thread and creates no extra display link. */
static _Atomic uint64_t turn_watch=3, observed_turns, observed_inputs;
static _Atomic uint64_t input_metadata_errors;
static _Atomic uint64_t output_errors;
static void (*old_add_animation)(id,SEL,id,id);
static void (*old_link_fps)(id,SEL,long);
static void (*old_link_range)(id,SEL,CAFrameRateRange);
static void (*old_send_event)(id,SEL,UIEvent *);

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
        if(n<=0){atomic_fetch_add_explicit(&output_errors,1,memory_order_relaxed);break;}
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
    if(row->kind==RATE_INPUT_BEGIN) {
        snprintf(line,sizeof(line),"SWEET SB INPUT: begin id=%llu us=%llu event_us=%llu touches=%llu phases=%x flags=%x view=%s window=%s\n",
            (unsigned long long)row->a,(unsigned long long)row->us,
            (unsigned long long)row->b,(unsigned long long)row->c,row->phases,row->flags,row->class_name,row->key);
    } else if(row->kind==RATE_INPUT_END) {
        snprintf(line,sizeof(line),"SWEET SB INPUT: end id=%llu us=%llu entered_us=%llu returned=%llu\n",
            (unsigned long long)row->a,(unsigned long long)row->us,
            (unsigned long long)row->b,(unsigned long long)row->c);
    } else if(row->kind==RATE_MAIN_TURN) {
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
        uint64_t watch=atomic_load_explicit(&turn_watch,memory_order_acquire);
        char line[256];
        snprintf(line,sizeof(line),"SWEET SB WATCH: us=%llu phase=%u turn_start_us=%llu inputs=%llu turns=%llu metadata_errors=%llu write_errors=%llu\n",
            (unsigned long long)now_us(),(unsigned)(watch&3),
            (unsigned long long)(watch>>2),
            (unsigned long long)atomic_load_explicit(&observed_inputs,memory_order_relaxed),
            (unsigned long long)atomic_load_explicit(&observed_turns,memory_order_relaxed),
            (unsigned long long)atomic_load_explicit(&input_metadata_errors,memory_order_relaxed),
            (unsigned long long)atomic_load_explicit(&output_errors,memory_order_relaxed));
        write_line(line);
    }
    return NULL;
}

static bool
method_argument_is(Method method,unsigned argument,const char *expected)
{
    char *actual=method_copyArgumentType(method,argument);
    bool matches=actual!=NULL&&strcmp(actual,expected)==0;
    free(actual);
    return matches;
}

static bool
void_method(Method method,unsigned count)
{
    if(method==NULL||method_getNumberOfArguments(method)!=count)return false;
    char *result=method_copyReturnType(method);
    bool matches=result!=NULL&&strcmp(result,"v")==0;
    free(result);
    return matches&&method_argument_is(method,0,"@")&&method_argument_is(method,1,":");
}

static bool
void_object_method(Method method,unsigned count)
{
    if(!void_method(method,count))return false;
    for(unsigned i=2;i<count;++i) {
        char *argument=method_copyArgumentType(method,i);
        bool matches=argument!=NULL&&argument[0]=='@'&&argument[1]!='?';
        free(argument);
        if(!matches)return false;
    }
    return true;
}

static bool
input_metadata(UIEvent *event,struct rate_row *begin)
{
    /* Observe only UIKit touch events. No coordinates, text, keys or event
     * descriptions are logged; the original receiver and argument are forwarded. */
    @try {
    if(![event isKindOfClass:[UIEvent class]]||event.type!=UIEventTypeTouches)return false;
    NSTimeInterval seconds=event.timestamp;
    if(isfinite(seconds)&&seconds>=0&&seconds<=(double)(UINT64_MAX/1000000ULL))
        begin->b=(uint64_t)(seconds*1000000.0);
    else begin->flags|=1;
    NSSet *touches=event.allTouches;
    begin->c=touches.count;
    unsigned seen=0;
    for(id touch in touches) {
        if(seen++==16){begin->flags|=4;break;}
        if(![touch isKindOfClass:[UITouch class]]){begin->flags|=2;continue;}
        if(seen==1) {
            copy_printable(begin->class_name,sizeof(begin->class_name),object_getClassName([(UITouch *)touch view]));
            copy_printable(begin->key,sizeof(begin->key),object_getClassName([(UITouch *)touch window]));
        }
        NSInteger phase=[(UITouch *)touch phase];
        if(phase<0||phase>=32)begin->flags|=2;
        else begin->phases|=1u<<(unsigned)phase;
    }
    return true;
    } @catch(id error) {
        (void)error;
        atomic_fetch_add_explicit(&input_metadata_errors,1,memory_order_relaxed);
        return false; /* an observer getter must never prevent the original call */
    }
}

static void
send_event(id self,SEL selector,UIEvent *event)
{
    struct rate_row begin={0};
    begin.kind=RATE_INPUT_BEGIN;
    begin.us=now_us();
    if(!input_metadata(event,&begin)){old_send_event(self,selector,event);return;}
    begin.a=atomic_fetch_add_explicit(&observed_inputs,1,memory_order_relaxed)+1;
    if(!pthread_main_np())begin.flags|=8;
    record_row(&begin);
    bool returned=false;
    @try {
        old_send_event(self,selector,event);
        returned=true;
    } @finally {
        struct rate_row end={0};
        end.kind=RATE_INPUT_END;end.a=begin.a;end.b=begin.us;
        end.us=now_us();end.c=returned;
        record_row(&end);
    }
}

static bool
install_input_hook(Class target)
{
    SEL selector=sel_registerName("sendEvent:");
    Method method=target?class_getInstanceMethod(target,selector):NULL;
    if(!void_object_method(method,3)||old_send_event!=NULL)return false;
    old_send_event=(void (*)(id,SEL,UIEvent *))method_getImplementation(method);
    /* If inherited, add an override only on SpringBoard rather than changing
     * UIApplication's superclass implementation. Constructor runs once. */
    if(!class_addMethod(target,selector,(IMP)send_event,method_getTypeEncoding(method))) {
        unsigned count=0;
        Method *owned=class_copyMethodList(target,&count);
        Method selected=NULL;
        for(unsigned i=0;i<count;++i)if(method_getName(owned[i])==selector)selected=owned[i];
        if(!void_object_method(selected,3)) {
            free(owned);old_send_event=NULL;return false;
        }
        old_send_event=(void (*)(id,SEL,UIEvent *))method_getImplementation(selected);
        method_setImplementation(selected,(IMP)send_event);
        free(owned);
    }
    return true;
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
        atomic_store_explicit(&turn_watch,main_woke<(UINT64_MAX>>2)?(main_woke<<2)|1:3,memory_order_release);
    } else if(activity==kCFRunLoopBeforeWaiting&&info==NULL) {
        commit_began=now_us();
        atomic_store_explicit(&turn_watch,main_woke&&main_woke<(UINT64_MAX>>2)?(main_woke<<2)|2:3,memory_order_release);
    } else if(activity==kCFRunLoopBeforeWaiting&&info==(void *)1&&main_woke) {
        struct rate_row row={0};
        row.kind=RATE_MAIN_TURN;
        row.us=now_us();
        row.a=main_woke;
        row.b=commit_began;
        row.c=row.us;
        record_row(&row);
        main_woke=0;
        atomic_fetch_add_explicit(&observed_turns,1,memory_order_relaxed);
        atomic_store_explicit(&turn_watch,row.a<(UINT64_MAX>>2)?(row.a<<2)|3:3,memory_order_release);
    } else if(activity==kCFRunLoopBeforeWaiting&&info==(void *)2) {
        main_woke=0;
        atomic_store_explicit(&turn_watch,0,memory_order_release);
    }
}

static bool
install_loop_observers(void)
{
    CFRunLoopActivity activities[]={kCFRunLoopAfterWaiting,kCFRunLoopBeforeWaiting,kCFRunLoopBeforeWaiting,kCFRunLoopBeforeWaiting};
    CFIndex orders[]={LONG_MIN,CA_COMMIT_ORDER-1,CA_COMMIT_ORDER+1,LONG_MAX};
    CFRunLoopObserverRef observers[4]={NULL,NULL,NULL,NULL};
    for(unsigned i=0;i<4;++i) {
        CFRunLoopObserverContext context={0};
        context.info=i>=2?(void *)(uintptr_t)(i-1):NULL;
        observers[i]=CFRunLoopObserverCreate(NULL,activities[i],true,orders[i],main_turn,&context);
        if(observers[i]==NULL) {
            for(unsigned j=0;j<i;++j)CFRelease(observers[j]);
            return false;
        }
    }
    for(unsigned i=0;i<4;++i) {
        CFRunLoopAddObserver(CFRunLoopGetMain(),observers[i],kCFRunLoopCommonModes);
        CFRelease(observers[i]);
    }
    return true;
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
    pthread_t thread;
    if(pthread_create(&thread,NULL,flush_thread,NULL)!=0)return;
    pthread_detach(thread);
    atomic_store_explicit(&enabled,true,memory_order_release);
    if(void_object_method(add,4)) {
        old_add_animation=(void (*)(id,SEL,id,id))method_getImplementation(add);
        method_setImplementation(add,(IMP)add_animation);
    }
    if(void_method(fps,3)&&method_argument_is(fps,2,@encode(long))) {
        old_link_fps=(void (*)(id,SEL,long))method_getImplementation(fps);
        method_setImplementation(fps,(IMP)set_link_fps);
    }
    if(void_method(range,3)&&method_argument_is(range,2,@encode(CAFrameRateRange))) {
        old_link_range=(void (*)(id,SEL,CAFrameRateRange))method_getImplementation(range);
        method_setImplementation(range,(IMP)set_link_range);
    }
    bool loop=install_loop_observers();
    bool input=install_input_hook(objc_getClass("SpringBoard"));
    char line[160];
    snprintf(line,sizeof(line),"SWEET SB RATE: active animation=%u link_fps=%u link_range=%u loop=%u flush=1; read-only\n",
        old_add_animation!=NULL,old_link_fps!=NULL,old_link_range!=NULL,loop);
    write_line(line);
    snprintf(line,sizeof(line),"SWEET SB INPUT: active send_event=%u target=SpringBoard watch=1; unchanged forwarding\n",input);
    write_line(line);
}
