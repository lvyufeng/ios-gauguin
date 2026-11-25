// Execute exact extracted production commit/notification/completion/handler
// methods with Foundation and the actual deferred core/FakeGpu on the host.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <sys/sysctl.h>
#include <dispatch/dispatch.h>
#include <atomic>
#include "hakios-metal/hakios_metal.h"
#include "Recording338.hpp"
#define gauguin_c4_queue_trace original_trace338
#include "GauguinC4QueueTrace.h"
#undef gauguin_c4_queue_trace
#include "GauguinQueue337.h"
#include "GauguinAsync338.h"
#define REQUIRE(x) do { if (!(x)) {fprintf(stderr,"front338 failure %d: %s\n",__LINE__,#x);abort();} } while(0)
#define HM_ONCE(...) fprintf(stderr,__VA_ARGS__)
static dispatch_semaphore_t beforeNotice338,continueNotice338;
static std::atomic<bool> delayFirstNotice338{false};
static void gauguin_c4_queue_trace(unsigned phase,const void* object,double start,double end,unsigned value) {
    original_trace338(phase,object,start,end,value);
    if (phase==3 && delayFirstNotice338.exchange(false)) {
        dispatch_semaphore_signal(beforeNotice338);
        REQUIRE(dispatch_semaphore_wait(continueNotice338,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
    }
}
extern "C" {
void* front_factory338(hakios_metal_device**,hakios_metal_queue**);
void front_block338(void*,hakios_metal_cb*);
void front_release338(void*);
void front_failure338(void*,int);
void front_close_device338(void*);
void front_destroy338(void*);
}
static std::atomic<unsigned> commandDeaths{0},queueDeaths{0},paidSlots{0},completedHandlers{0};
static unsigned paidOrder[8];
static bool scheduledSeen[8];
static double hm_now(void) {return double(gauguin338::nowNs())/1e9;}
static void hm_timeline(double,double,double,double) {}
static void hm_fps_note(BOOL,double,double,hakios_metal_cb*) {}
static void hm_fps_encoded(double,BOOL) {}
static void hm_fps_commit(double) {}
static int gauguin_edr_loader_attempted=1;
static void gauguin_edr_load_after_completion(void) {abort();}

@interface HakiosMetalCommandQueue : NSObject {
    hakios_metal_queue* _native;
    dispatch_queue_t _deferred;
    dispatch_semaphore_t _first;
    uint64_t _admitted,_retired;
}
- (instancetype)initWithNative:(hakios_metal_queue*)queue;
- (hakios_metal_queue*)hakiosQueue;
- (dispatch_queue_t)hakiosCompletionQueue;
- (void)hakiosAdmit:(dispatch_block_t)body;
- (void)marker:(dispatch_semaphore_t)semaphore;
- (void)waitForFirstRetire;
- (uint64_t)hakiosTraceQueue;
- (uint64_t)hakiosTraceAdmit;
- (uint64_t)hakiosTraceRetired;
- (uint64_t)hakiosTraceRetire;
@end
@implementation HakiosMetalCommandQueue
- (instancetype)initWithNative:(hakios_metal_queue*)queue {
    if ((self=[super init])) {_native=queue;_deferred=dispatch_queue_create("front338.fifo",DISPATCH_QUEUE_SERIAL);_first=dispatch_semaphore_create(0);}return self;
}
- (hakios_metal_queue*)hakiosQueue {return _native;}
- (dispatch_queue_t)hakiosCompletionQueue {return nil;}
- (void)hakiosAdmit:(dispatch_block_t)body {dispatch_async(_deferred,body);}
- (void)marker:(dispatch_semaphore_t)semaphore {dispatch_async(_deferred,^{dispatch_semaphore_signal(semaphore);});}
- (void)waitForFirstRetire {REQUIRE(dispatch_semaphore_wait(_first,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);}
- (uint64_t)hakiosTraceQueue {return 1;}
- (uint64_t)hakiosTraceAdmit {return ++_admitted;}
- (uint64_t)hakiosTraceRetired {return __atomic_load_n(&_retired,__ATOMIC_ACQUIRE);}
- (uint64_t)hakiosTraceRetire {uint64_t n=__atomic_add_fetch(&_retired,1,__ATOMIC_RELEASE);if(n==1)dispatch_semaphore_signal(_first);return n;}
- (void)dealloc {hakios_metal_queue_free(_native);[_deferred release];[_first release];queueDeaths++;[super dealloc];}
@end
@interface HakiosMetalCommandBuffer : NSObject {
    HakiosMetalCommandQueue* _queue;
    hakios_metal_cb* _cb;
    NSCondition* _stateCondition;
    BOOL _committed,_reached,_finished;
    double _committedAt,_createdAt;
    NSArray* _waits;
    NSArray* _turned;
    NSArray* _signals;
    NSMutableArray* _scheduled;
    NSMutableArray* _completed;
    dispatch_queue_t _handlerQueue;
    unsigned _tag;
}
- (instancetype)initWithQueue:(HakiosMetalCommandQueue*)queue tag:(unsigned)tag;
- (void)commit;
- (void)hakiosMarkScheduled;
- (void)hakiosCompletedNow;
- (void)hakiosPaySlot;
- (void)hakiosDeliver:(MTLCommandBufferHandler)handler;
- (void)addScheduledHandler:(MTLCommandBufferHandler)handler;
- (void)addCompletedHandler:(MTLCommandBufferHandler)handler;
- (double)hakiosCreatedAt;
- (double)GPUStartTime;
- (NSError*)error;
- (hakios_metal_cb*)native;
- (void)waits:(NSArray*)waits signals:(NSArray*)signals turns:(NSArray*)turns;
@end
// Most cases keep event/turn arrays empty; the dependency case executes both.
@interface HakiosMetalTexture : NSObject {
    hakios_metal_texture *_texture,*_turnedSurface;
    unsigned _turn;
}
- (instancetype)initWithDevice:(hakios_metal_device*)device;
- (void)hakiosTurnInto:(hakios_metal_cb*)cb;
@end
@implementation HakiosMetalTexture
- (instancetype)initWithDevice:(hakios_metal_device*)device {
    if ((self=[super init])) {
        _texture=hakios_metal_texture_new(device,2,70,16,16,5);
        _turnedSurface=hakios_metal_texture_new(device,2,70,16,16,5);
        REQUIRE(_texture && _turnedSurface);_turn=0;
    }return self;
}
#include "frontend338-turn.inc"
- (void)dealloc {hakios_metal_texture_free(_texture);hakios_metal_texture_free(_turnedSurface);[super dealloc];}
@end
@interface HakiosMetalEvent : NSObject {
    NSCondition* _lock;
    uint64_t _value;
    NSMutableArray* _listeners;
}
- (BOOL)hakiosReached:(uint64_t)value;
- (void)hakiosWaitFor:(uint64_t)value;
- (void)hakiosSignal:(uint64_t)value;
- (uint64_t)signaledValue;
@end
@implementation HakiosMetalEvent
- (instancetype)init {if ((self=[super init])) _lock=[NSCondition new];return self;}
- (uint64_t)signaledValue {[_lock lock];uint64_t value=_value;[_lock unlock];return value;}
#include "frontend338-event.inc"
- (void)dealloc {[_lock release];[_listeners release];[super dealloc];}
@end

#include "frontend338-callbacks.inc"
@implementation HakiosMetalCommandBuffer
- (instancetype)initWithQueue:(HakiosMetalCommandQueue*)queue tag:(unsigned)tag {
    if ((self=[super init])) {
        _queue=[queue retain];_cb=hakios_metal_cb_new([queue hakiosQueue]);_tag=tag;
        _stateCondition=[NSCondition new];_createdAt=hm_now();
        _handlerQueue=dispatch_queue_create("front338.handlers",DISPATCH_QUEUE_SERIAL);
    }return self;
}
- (double)hakiosCreatedAt {return _createdAt;}
- (double)GPUStartTime {return _committedAt;}
- (NSError*)error {return nil;}
- (hakios_metal_cb*)native {return _cb;}
- (void)waits:(NSArray*)waits signals:(NSArray*)signals turns:(NSArray*)turns {
    _waits=[waits copy];_signals=[signals copy];_turned=[turns copy];
}
- (void)hakiosPaySlot {unsigned n=paidSlots.fetch_add(1);REQUIRE(n<8);paidOrder[n]=_tag;}
- (void)dealloc {
    hakios_metal_cb_free(_cb);[_queue release];[_stateCondition release];[_handlerQueue release];
    [_waits release];[_turned release];[_signals release];[_scheduled release];[_completed release];
    commandDeaths++;[super dealloc];
}
#include "frontend338-methods.inc"
@end

int main(int argc,char**argv) {
    REQUIRE(argc==2 || argc==3);const int failure=atoi(argv[1]);
    const bool dependency=argc==3 && !strcmp(argv[2],"event-turn");
    const bool lateNotice=argc==3 && !strcmp(argv[2],"late-notice");
    void* factory=nullptr;
    @autoreleasepool {
        hakios_metal_device* d;hakios_metal_queue* q;factory=front_factory338(&d,&q);
        (void)d;
        HakiosMetalCommandQueue* queue=[[HakiosMetalCommandQueue alloc]initWithNative:q];
        HakiosMetalCommandBuffer* a=[[HakiosMetalCommandBuffer alloc]initWithQueue:queue tag:1];
        HakiosMetalCommandBuffer* b=[[HakiosMetalCommandBuffer alloc]initWithQueue:queue tag:2];
        HakiosMetalEvent* event=nil;
        if (dependency) {
            event=[HakiosMetalEvent new];
            HakiosMetalTexture* texture=[[HakiosMetalTexture alloc]initWithDevice:d];
            NSArray* pair=@[event,@1];
            [a waits:nil signals:@[pair] turns:nil];
            [b waits:@[pair] signals:nil turns:@[texture]];[texture release];
        }
        dispatch_semaphore_t finished=dispatch_semaphore_create(0),front=dispatch_semaphore_create(0);
        if (lateNotice) {
            beforeNotice338=dispatch_semaphore_create(0);continueNotice338=dispatch_semaphore_create(0);
            delayFirstNotice338=true;
        }
        for (unsigned tag=1;tag<=2;tag++) {
            HakiosMetalCommandBuffer* cb=tag==1?a:b;
            [cb addScheduledHandler:^(id<MTLCommandBuffer> unused){(void)unused;scheduledSeen[tag]=true;}];
            [cb addCompletedHandler:^(id<MTLCommandBuffer> unused){
                (void)unused;REQUIRE(scheduledSeen[tag]);completedHandlers++;
                if (dependency && tag==2) REQUIRE([event signaledValue]>=1);
                dispatch_semaphore_signal(finished);
            }];
        }
        front_block338(factory,[a native]);front_failure338(factory,failure);
        [a commit];[a commit];[b commit];[queue marker:front];
        if (lateNotice) {
            REQUIRE(dispatch_semaphore_wait(beforeNotice338,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
            front_release338(factory);
            REQUIRE(dispatch_semaphore_wait(finished,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
            REQUIRE(paidSlots.load()==1 && completedHandlers.load()==1 && commandDeaths.load()==0);
            dispatch_semaphore_signal(continueNotice338);
        }
        if (dependency) {
            [queue waitForFirstRetire];REQUIRE([queue hakiosTraceRetired]==1);
            REQUIRE(dispatch_semaphore_wait(front,DISPATCH_TIME_NOW)!=0);
        } else {
            REQUIRE(dispatch_semaphore_wait(front,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
            REQUIRE([queue hakiosTraceRetired]==2);
        }
        [a release];[b release];[queue release];
        // Real Metal textures retain their device through the Apple base.
        // This small test class owns raw C texture handles, so retain the
        // factory device until its surrounding autorelease pool is drained.
        if (!dependency) front_close_device338(factory);
        if (!lateNotice) REQUIRE(commandDeaths.load()==0); // completion+notification own both objects while gated
        if (!lateNotice) front_release338(factory);
        if (dependency) REQUIRE(dispatch_semaphore_wait(front,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
        if (!lateNotice) REQUIRE(dispatch_semaphore_wait(finished,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
        REQUIRE(dispatch_semaphore_wait(finished,dispatch_time(DISPATCH_TIME_NOW,4*NSEC_PER_SEC))==0);
        if (lateNotice) {[beforeNotice338 release];[continueNotice338 release];}
        [front release];[finished release];
        [event release];
        // Drain copied-handler autoreleases before checking final ownership.
    }
    // The core's reaper/last callbacks may still be releasing their final lease;
    // the wrapper scope must have destroyed both CBs and native queue eventually.
    for (unsigned n=0;n<500 && (commandDeaths.load()!=2 || queueDeaths.load()!=1);n++) usleep(1000);
    if (dependency) front_close_device338(factory);
    front_destroy338(factory);
    REQUIRE(commandDeaths.load()==2 && queueDeaths.load()==1);
    REQUIRE(paidSlots.load()==2 && paidOrder[0]==1 && paidOrder[1]==2 && completedHandlers.load()==2);
    printf("PASS actual frontend338 failure=%d scheduled-before-completed/FIFO/retains\n",failure);
    return 0;
}
