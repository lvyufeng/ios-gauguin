/* Actual probe bodies, real Objective-C dispatch, typed UIKit event seams. */
#import <Foundation/Foundation.h>
#import <QuartzCore/QuartzCore.h>
#include <assert.h>
#include <math.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>

typedef NSInteger UIEventType;
enum { UIEventTypeTouches=0 };
@interface UITouch : NSObject { NSInteger _phase; }
@property(nonatomic,readonly) NSInteger phase;
- (id)view;
- (id)window;
- (id)initWithPhase:(NSInteger)phase;
@end
@implementation UITouch
- (id)initWithPhase:(NSInteger)phase {if((self=[super init]))_phase=phase;return self;}
- (NSInteger)phase {return _phase;}
- (id)view {return self;}
- (id)window {return nil;}
@end
@interface UIEvent : NSObject { UIEventType _type; NSTimeInterval _timestamp; NSSet *_touches; }
@property(nonatomic,readonly) UIEventType type;
@property(nonatomic,readonly) NSTimeInterval timestamp;
@property(nonatomic,readonly) NSSet *allTouches;
- (id)initWithType:(UIEventType)type timestamp:(NSTimeInterval)stamp touches:(NSSet *)touches;
@end
@implementation UIEvent
- (id)initWithType:(UIEventType)type timestamp:(NSTimeInterval)stamp touches:(NSSet *)touches
{if((self=[super init])){_type=type;_timestamp=stamp;_touches=[touches retain];}return self;}
- (UIEventType)type {return _type;}
- (NSTimeInterval)timestamp {return _timestamp;}
- (NSSet *)allTouches {return _touches;}
- (void)dealloc {[_touches release];[super dealloc];}
@end
@interface MetadataThrows : UIEvent @end
@implementation MetadataThrows
- (NSTimeInterval)timestamp {@throw [NSException exceptionWithName:@"metadata" reason:@"fixture" userInfo:nil];}
@end
static void host_original(id,SEL,UIEvent *);
@interface InputParent : NSObject
- (void)sendEvent:(UIEvent *)event;
@end
@implementation InputParent
- (void)sendEvent:(UIEvent *)event {host_original(self,_cmd,event);}
@end
@interface SpringBoard : InputParent @end
@implementation SpringBoard @end
@interface OwnInput : InputParent @end
@implementation OwnInput
- (void)sendEvent:(UIEvent *)event {host_original(self,_cmd,event);}
@end
@interface WrongReturn : NSObject
- (long)sendEvent:(UIEvent *)event;
@end
@implementation WrongReturn
- (long)sendEvent:(UIEvent *)event {(void)event;return 0;}
@end
@interface WrongArgument : NSObject
- (void)sendEvent:(double)value;
@end
@implementation WrongArgument
- (void)sendEvent:(double)value {(void)value;}
@end

@SOURCE@

static unsigned checks,calls;
static id expected_receiver,last_event;
static UIEvent *nested_event,*throw_event;
static NSException *expected_exception;
static bool nesting;
static void check(bool ok){++checks;assert(ok);}
static void host_original(id self,SEL selector,UIEvent *event)
{
    check(self==expected_receiver&&selector==@selector(sendEvent:));
    ++calls;last_event=event;
    if(event==throw_event&&event!=nil)@throw expected_exception;
    if(nested_event&&!nesting){nesting=true;[(InputParent *)self sendEvent:nested_event];nesting=false;}
}
static UIEvent *event(NSInteger type,double stamp,NSSet *touches)
{return [[[UIEvent alloc] initWithType:type timestamp:stamp touches:touches] autorelease];}
static UITouch *touch(NSInteger phase){return [[[UITouch alloc] initWithPhase:phase] autorelease];}
static void reset(void)
{
    rows_head=rows_count=0;memset(rows,0,sizeof(rows));
    atomic_store(&rows_lost,0);atomic_store(&observed_inputs,0);
    atomic_store(&input_metadata_errors,0);
    atomic_store(&output_errors,0);
    calls=0;last_event=nil;nested_event=throw_event=nil;nesting=false;
}
static void wrong_arity(id self,SEL selector,id one,id two){(void)self;(void)selector;(void)one;(void)two;}
struct thread_args {id receiver;UIEvent *event;};
static void *worker(void *pointer)
{@autoreleasepool {struct thread_args *args=pointer;[(InputParent *)args->receiver sendEvent:args->event];}return NULL;}

int main(int argc,char **argv)
{
    @autoreleasepool {
        check(argc==2);
        check(mach_timebase_info(&timebase)==KERN_SUCCESS&&timebase.numer&&timebase.denom);
        atomic_store(&enabled,true);
        if(strcmp(argv[1],"stack-format")==0) {
            struct sb_stack_result sample={0};
            sample.requested_us=230000000;sample.us=230000010;
            sample.held_us=230000020;sample.resumed_us=230000100;
            sample.expected_watch=sample.stopped_watch=(UINT64_C(226000000)<<2)|2;
            sample.registers=(struct sb_stack_registers){(uintptr_t)start_rate_trace,(uintptr_t)main_turn,0x10000,0x10020};
            sample.frames=1;sample.frame_fp[0]=0x10020;sample.frame_lr[0]=(uintptr_t)sample_stack;
            sample.registers_valid=true;sample.stop=SB_STACK_FRAME_END;
            write_line(stack_configuration);flush_stack_sample(1,&sample);
            sample.resume_result=5;flush_stack_sample(2,&sample); /* Must emit nothing after uncertain resume. */
            check(atomic_load(&output_errors)==0);
            printf("PASS SpringBoard probe actual stack formatting checks=%u; fixture addresses, no sampling\n",checks);
            return 0;
        }
        if(strcmp(argv[1],"abi")==0) {
            check(!install_input_hook(Nil)&&old_send_event==NULL);
            for(Class target in @[[WrongReturn class],[WrongArgument class]]) {
                IMP before=method_getImplementation(class_getInstanceMethod(target,@selector(sendEvent:)));
                check(!install_input_hook(target)&&old_send_event==NULL);
                check(method_getImplementation(class_getInstanceMethod(target,@selector(sendEvent:)))==before);
            }
            Class bad=objc_allocateClassPair([NSObject class],"WrongArity",0);
            check(bad!=Nil&&class_addMethod(bad,@selector(sendEvent:),(IMP)wrong_arity,"v32@0:8@16@24"));
            objc_registerClassPair(bad);check(!install_input_hook(bad)&&old_send_event==NULL);
            printf("PASS SpringBoard probe ABI refusals checks=%u\n",checks);return 0;
        }
        Class target=strcmp(argv[1],"own")==0?[OwnInput class]:[SpringBoard class];
        IMP parent=method_getImplementation(class_getInstanceMethod([InputParent class],@selector(sendEvent:)));
        IMP original=method_getImplementation(class_getInstanceMethod(target,@selector(sendEvent:)));
        check(install_input_hook(target));
        check((IMP)old_send_event==original);
        check(method_getImplementation(class_getInstanceMethod([InputParent class],@selector(sendEvent:)))==parent);
        check(!install_input_hook(target));
        id app=[[[target alloc] init] autorelease];expected_receiver=app;
        NSSet *contacts=[NSSet setWithObjects:touch(0),touch(1),touch(3),nil];
        UIEvent *sample=event(UIEventTypeTouches,1.25,contacts);
        reset();[(InputParent *)app sendEvent:sample];
        check(calls==1&&last_event==sample&&rows_count==2&&atomic_load(&observed_inputs)==1);
        check(rows[0].kind==RATE_INPUT_BEGIN&&rows[0].a==1&&rows[0].b==1250000&&rows[0].c==3);
        check(rows[0].phases==((1u<<0)|(1u<<1)|(1u<<3))&&rows[0].flags==0);
        check(!strcmp(rows[0].class_name,"UITouch"));
        check(rows[1].kind==RATE_INPUT_END&&rows[1].a==1&&rows[1].b==rows[0].us&&rows[1].us>=rows[0].us&&rows[1].c==1);
        check(sample.timestamp==1.25&&sample.allTouches==contacts&&sample.type==UIEventTypeTouches);
        flush_row(&rows[0]);flush_row(&rows[1]);

        // Non-touch, nil and non-UIEvent inputs are passed through unobserved.
        reset();UIEvent *key=event(3,2.0,contacts);[(InputParent *)app sendEvent:key];
        check(calls==1&&last_event==key&&rows_count==0&&atomic_load(&observed_inputs)==0);
        [(InputParent *)app sendEvent:nil];check(calls==2&&last_event==nil&&rows_count==0);
        id other=[[[NSObject alloc] init] autorelease];[(InputParent *)app sendEvent:other];
        check(calls==3&&last_event==other&&rows_count==0);

        reset();UIEvent *broken=[[[MetadataThrows alloc] initWithType:0 timestamp:1 touches:contacts] autorelease];
        [(InputParent *)app sendEvent:broken];
        check(calls==1&&last_event==broken&&rows_count==0&&atomic_load(&input_metadata_errors)==1);

        // Preserve the original exception and still end the diagnostic span.
        reset();throw_event=sample;expected_exception=[NSException exceptionWithName:@"original" reason:@"fixture" userInfo:nil];
        bool caught=false;
        @try {[(InputParent *)app sendEvent:sample];}
        @catch(NSException *error){caught=true;check(error==expected_exception);}
        check(caught&&calls==1&&rows_count==2&&rows[1].c==0);

        // Reentrant dispatch retains distinct, correctly nested spans.
        reset();nested_event=event(0,1.3,[NSSet setWithObject:touch(4)]);
        [(InputParent *)app sendEvent:sample];
        check(calls==2&&rows_count==4&&atomic_load(&observed_inputs)==2);
        check(rows[0].kind==RATE_INPUT_BEGIN&&rows[1].kind==RATE_INPUT_BEGIN&&rows[2].kind==RATE_INPUT_END&&rows[3].kind==RATE_INPUT_END);
        check(rows[0].a==rows[3].a&&rows[1].a==rows[2].a&&rows[0].a!=rows[1].a);

        // Full/contended logging never suppresses or blocks the original.
        reset();rows_count=RATE_ROWS;[(InputParent *)app sendEvent:sample];
        check(calls==1&&rows_count==RATE_ROWS&&atomic_load(&rows_lost)==2);
        reset();pthread_mutex_lock(&rows_lock);[(InputParent *)app sendEvent:sample];pthread_mutex_unlock(&rows_lock);
        check(calls==1&&rows_count==0&&atomic_load(&rows_lost)==2);

        // Invalid metadata is labelled, never used for an unchecked cast.
        reset();UIEvent *invalid=event(0,NAN,[NSSet setWithObjects:touch(32),other,nil]);
        [(InputParent *)app sendEvent:invalid];check(calls==1&&rows[0].flags==3&&rows[0].b==0);
        reset();UIEvent *huge=event(0,HUGE_VAL,contacts);[(InputParent *)app sendEvent:huge];
        check(calls==1&&(rows[0].flags&1)&&rows[0].b==0);
        NSMutableSet *many=[NSMutableSet set];for(unsigned i=0;i<17;++i)[many addObject:touch(0)];
        reset();UIEvent *bounded=event(0,1.0,many);[(InputParent *)app sendEvent:bounded];
        check(calls==1&&(rows[0].flags&4)&&rows[0].c==17&&bounded.allTouches.count==17);

        // Off-main delivery is explicitly marked while preserving forwarding.
        reset();struct thread_args args={app,sample};pthread_t thread;
        check(pthread_create(&thread,NULL,worker,&args)==0);check(pthread_join(thread,NULL)==0);
        check(calls==1&&rows_count==2&&(rows[0].flags&8));

        // The watch observes existing callbacks; no main-thread timer is created.
        reset();main_woke=commit_began=0;atomic_store(&observed_turns,0);atomic_store(&turn_watch,3);
        main_turn(NULL,kCFRunLoopBeforeWaiting,NULL);check(atomic_load(&turn_watch)==3);
        main_turn(NULL,kCFRunLoopAfterWaiting,NULL);
        uint64_t woke=main_woke;check(woke>0&&atomic_load(&turn_watch)==((woke<<2)|1));
        main_turn(NULL,kCFRunLoopBeforeWaiting,NULL);check(atomic_load(&turn_watch)==((woke<<2)|2));
        main_turn(NULL,kCFRunLoopBeforeWaiting,(void *)1);
        check(atomic_load(&turn_watch)==((woke<<2)|3)&&atomic_load(&observed_turns)==1&&rows_count==1);
        main_turn(NULL,kCFRunLoopBeforeWaiting,(void *)2);check(atomic_load(&turn_watch)==0);
        check(rows[0].kind==RATE_MAIN_TURN&&rows[0].a==woke&&rows[0].a<=rows[0].b&&rows[0].b<=rows[0].c);
        flush_row(&rows[0]);
        int saved=dup(STDERR_FILENO);check(saved>=0);check(close(STDERR_FILENO)==0);
        write_line("cannot reach closed descriptor\n");check(atomic_load(&output_errors)==1);
        check(dup2(saved,STDERR_FILENO)==STDERR_FILENO);check(close(saved)==0);
        printf("PASS SpringBoard probe %s checks=%u; actual wrappers/runtime dispatch, UIKit seams, no device claim\n",argv[1],checks);
    }
    return 0;
}
