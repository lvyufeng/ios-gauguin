/* Test shell: the marked method bodies are extracted from the real frontend. */
#import <Foundation/Foundation.h>
#import <objc/runtime.h>
#include <dispatch/dispatch.h>
#include <pthread.h>
#include <stdatomic.h>
#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

#define HM_ONCE(...) ((void)0)
@protocol MTLCommandBuffer @end
typedef void (^MTLCommandBufferHandler)(id);
typedef enum { MTLCommandBufferStatusCommitted = 2 } MTLCommandBufferStatus;
enum hakios_metal_status { HAKIOS_METAL_NOT_ENQUEUED = 0, HAKIOS_METAL_COMMITTED = 2,
                           HAKIOS_METAL_SCHEDULED = 3, HAKIOS_METAL_COMPLETED = 4,
                           HAKIOS_METAL_ERROR = 5 };
typedef struct FakeCB {
    pthread_mutex_t lock;
    pthread_cond_t changed;
    int posted, status, done, refused, id;
    dispatch_semaphore_t submitGate, finishGate;
} hakios_metal_cb;
static dispatch_queue_t g_core;
static pthread_mutex_t g_order_lock = PTHREAD_MUTEX_INITIALIZER;
static int g_order[8];
static atomic_int g_order_count;
static pthread_mutex_t g_handler_lock = PTHREAD_MUTEX_INITIALIZER;
static char g_handlers[16];
static atomic_int g_handler_count;
static atomic_int g_scheduled_waits, g_completed_waits, g_error_waits;

static void need(BOOL ok, const char *message) {
    if (!ok) { fprintf(stderr, "FAIL: %s\n", message); exit(2); }
}
static void record(char c) {
    pthread_mutex_lock(&g_handler_lock);
    int count=atomic_load(&g_handler_count);
    g_handlers[count]=c;
    atomic_store(&g_handler_count,count+1);
    pthread_mutex_unlock(&g_handler_lock);
}
static void until(BOOL (^condition)(void), const char *message) {
    for (int i=0;i<1000;i++) { if (condition()) return; usleep(10000); }
    need(NO, message);
}
static double hm_now(void) { return CFAbsoluteTimeGetCurrent(); }
static void hm_fps_encoded(double seconds, BOOL held) { (void)seconds; (void)held; }
static void hm_fps_commit(double seconds) { (void)seconds; }
static void hm_fps_waited(double seconds) { (void)seconds; }
static Ivar hm_completion_ivar(void) { return NULL; }

@interface FakeEvent : NSObject { NSCondition *_lock; BOOL _reached; }
- (BOOL)hakiosReached:(unsigned long long)value;
- (void)hakiosWaitFor:(unsigned long long)value;
- (void)signal;
- (void)hakiosSignal:(unsigned long long)value;
@end
@implementation FakeEvent
- (id)init { if ((self=[super init])) _lock=[[NSCondition alloc] init]; return self; }
- (void)dealloc { [_lock release]; [super dealloc]; }
- (BOOL)hakiosReached:(unsigned long long)value { (void)value; [_lock lock]; BOOL yes=_reached; [_lock unlock]; return yes; }
- (void)hakiosWaitFor:(unsigned long long)value { (void)value; [_lock lock]; while (!_reached) [_lock wait]; [_lock unlock]; }
- (void)signal { [_lock lock]; _reached=YES; [_lock broadcast]; [_lock unlock]; }
- (void)hakiosSignal:(unsigned long long)value { (void)value; [self signal]; }
@end

@interface HakiosMetalTexture : NSObject
- (void)hakiosTurnInto:(hakios_metal_cb *)cb;
@end
@implementation HakiosMetalTexture
- (void)hakiosTurnInto:(hakios_metal_cb *)cb { (void)cb; }
@end

@interface HakiosMetalCommandQueue : NSObject {
    dispatch_queue_t _deferred, _completionQueue;
}
- (void)hakiosAdmit:(dispatch_block_t)commit;
- (void)setCompletionQueue:(dispatch_queue_t)queue;
- (dispatch_queue_t)hakiosCompletionQueue;
@end
@implementation HakiosMetalCommandQueue
/* QUEUE_METHODS */
- (void)dealloc { [_completionQueue release]; if (_deferred) dispatch_release(_deferred); [super dealloc]; }
@end

@interface HakiosMetalCommandBuffer : NSObject {
@public
    HakiosMetalCommandQueue *_queue;
    hakios_metal_cb *_cb;
    NSMutableArray *_scheduled, *_completed, *_signals, *_waits, *_turned;
    NSCondition *_stateCondition;
    BOOL _committed, _reached, _finished;
    dispatch_queue_t _handlerQueue;
    double _committedAt, _createdAt;
}
- (id)initWithQueue:(HakiosMetalCommandQueue *)queue core:(hakios_metal_cb *)cb;
- (void)commit;
- (void)waitUntilScheduled;
- (void)waitUntilCompleted;
- (void)hakiosMarkScheduled;
- (void)hakiosCompletedNow;
- (void)hakiosDeliver:(MTLCommandBufferHandler)handler;
- (void)addScheduledHandler:(MTLCommandBufferHandler)handler;
- (void)addCompletedHandler:(MTLCommandBufferHandler)handler;
- (void)hakiosPaySlot;
- (NSError *)error;
@end
static void hm_completed(hakios_metal_cb *cb, void *context);
static void hakios_metal_cb_commit(hakios_metal_cb *cb, void (*callback)(hakios_metal_cb *, void *), void *context) {
    pthread_mutex_lock(&g_order_lock); int count=atomic_load(&g_order_count);
    g_order[count]=cb->id; atomic_store(&g_order_count,count+1); pthread_mutex_unlock(&g_order_lock);
    pthread_mutex_lock(&cb->lock); cb->posted=1; cb->status=HAKIOS_METAL_COMMITTED;
    pthread_cond_broadcast(&cb->changed); pthread_mutex_unlock(&cb->lock);
    dispatch_async(g_core, ^{
        if (!cb->refused) {
            dispatch_semaphore_wait(cb->submitGate, DISPATCH_TIME_FOREVER);
            pthread_mutex_lock(&cb->lock); cb->status=HAKIOS_METAL_SCHEDULED;
            pthread_cond_broadcast(&cb->changed); pthread_mutex_unlock(&cb->lock);
        }
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT,0), ^{
            dispatch_semaphore_wait(cb->finishGate, DISPATCH_TIME_FOREVER);
            pthread_mutex_lock(&cb->lock); cb->status=cb->refused ? HAKIOS_METAL_ERROR : HAKIOS_METAL_COMPLETED;
            pthread_cond_broadcast(&cb->changed); pthread_mutex_unlock(&cb->lock);
            callback(cb, context);
            pthread_mutex_lock(&cb->lock); cb->done=1;
            pthread_cond_broadcast(&cb->changed); pthread_mutex_unlock(&cb->lock);
        });
    });
}
static enum hakios_metal_status hakios_metal_cb_status(hakios_metal_cb *cb) {
    pthread_mutex_lock(&cb->lock);
    while (!cb->posted || (!cb->refused && cb->status < HAKIOS_METAL_SCHEDULED)) pthread_cond_wait(&cb->changed,&cb->lock);
    int state=cb->status; pthread_mutex_unlock(&cb->lock); return (enum hakios_metal_status)state;
}
static void hakios_metal_cb_wait(hakios_metal_cb *cb) {
    pthread_mutex_lock(&cb->lock); while (!cb->done) pthread_cond_wait(&cb->changed,&cb->lock); pthread_mutex_unlock(&cb->lock);
}
@implementation HakiosMetalCommandBuffer
- (id)initWithQueue:(HakiosMetalCommandQueue *)queue core:(hakios_metal_cb *)cb {
    if ((self=[super init])) { _queue=[queue retain]; _cb=cb; _stateCondition=[[NSCondition alloc] init];
        _handlerQueue=dispatch_queue_create("c4.host.handlers",DISPATCH_QUEUE_SERIAL); _createdAt=hm_now(); }
    return self;
}
- (void)dealloc { [_queue release]; [_stateCondition release]; [_scheduled release]; [_completed release];
    [_waits release]; if (_handlerQueue) dispatch_release(_handlerQueue); [super dealloc]; }
- (NSError *)error { return nil; }
- (void)hakiosPaySlot { }
/* CB_METHODS */
@end
static void hm_completed(hakios_metal_cb *cb, void *context) {
    (void)cb; HakiosMetalCommandBuffer *buffer=(HakiosMetalCommandBuffer *)context;
    @autoreleasepool { [buffer hakiosCompletedNow]; } [buffer release];
}
static void init_core(hakios_metal_cb *cb, int id, int refused) {
    pthread_mutex_init(&cb->lock,NULL); pthread_cond_init(&cb->changed,NULL);
    cb->posted=cb->status=cb->done=0; cb->id=id; cb->refused=refused;
    cb->submitGate=dispatch_semaphore_create(0); cb->finishGate=dispatch_semaphore_create(0);
}
int main(void) { @autoreleasepool {
    g_core=dispatch_queue_create("c4.host.core",DISPATCH_QUEUE_SERIAL);
    HakiosMetalCommandQueue *queue=[[HakiosMetalCommandQueue alloc] init];
    dispatch_queue_t external=dispatch_queue_create("c4.host.concurrent",DISPATCH_QUEUE_CONCURRENT);
    [queue setCompletionQueue:external];
    hakios_metal_cb a={0},b={0},err={0}; init_core(&a,1,0); init_core(&b,2,0); init_core(&err,3,1);
    FakeEvent *event=[[FakeEvent alloc] init];
    HakiosMetalCommandBuffer *first=[[HakiosMetalCommandBuffer alloc] initWithQueue:queue core:&a];
    HakiosMetalCommandBuffer *second=[[HakiosMetalCommandBuffer alloc] initWithQueue:queue core:&b];
    first->_waits=[@[ @[event,@(1)] ] mutableCopy];
    [first addScheduledHandler:^(id cb) { (void)cb; usleep(100000); record('S'); }];
    [first addCompletedHandler:^(id cb) { (void)cb; record('C'); }];
    dispatch_semaphore_signal(a.submitGate); dispatch_semaphore_signal(b.submitGate);
    [first commit]; [second commit];
    for (int i=0;i<3;i++) {
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT,0), ^{ [first waitUntilScheduled]; atomic_fetch_add(&g_scheduled_waits,1); });
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT,0), ^{ [second waitUntilScheduled]; atomic_fetch_add(&g_scheduled_waits,1); });
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT,0), ^{ [first waitUntilCompleted]; atomic_fetch_add(&g_completed_waits,1); });
    }
    usleep(100000);
    need(atomic_load(&g_order_count)==0 && atomic_load(&g_scheduled_waits)==0 && atomic_load(&g_completed_waits)==0,
         "ordinary commit or waiter bypassed the held buffer");
    [event signal];
    until(^BOOL{ return atomic_load(&g_order_count)==2 && atomic_load(&g_scheduled_waits)==6; }, "both ordered submits and all scheduled waiters");
    need(g_order[0]==1 && g_order[1]==2, "FIFO commit order");
    need(atomic_load(&g_completed_waits)==0, "completion wait returned before callback");
    [first addScheduledHandler:^(id cb) { (void)cb; record('L'); }];
    dispatch_semaphore_signal(a.finishGate); dispatch_semaphore_signal(b.finishGate);
    until(^BOOL{ return atomic_load(&g_completed_waits)==3; }, "all completion waiters released");
    until(^BOOL{ return atomic_load(&g_handler_count)==3; }, "scheduled, late scheduled and completed handlers ran");
    need(g_handlers[0]=='S' && g_handlers[1]=='L' && g_handlers[2]=='C', "handler invocation order on concurrent queue");
    [first addCompletedHandler:^(id cb) { (void)cb; record('D'); }];
    until(^BOOL{ return atomic_load(&g_handler_count)==4; }, "late completion handler ran");
    need(g_handlers[3]=='D', "late handler order");
    [first commit]; need(atomic_load(&g_order_count)==2, "double commit submitted twice");
    HakiosMetalCommandBuffer *bad=[[HakiosMetalCommandBuffer alloc] initWithQueue:queue core:&err];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT,0), ^{ [bad waitUntilScheduled]; atomic_fetch_add(&g_error_waits,1); });
    [bad commit]; until(^BOOL{ return atomic_load(&g_order_count)==3; }, "error buffer admitted");
    usleep(50000); need(atomic_load(&g_error_waits)==0, "error scheduled before terminal callback");
    dispatch_semaphore_signal(err.finishGate);
    until(^BOOL{ return atomic_load(&g_error_waits)==1; }, "error wakes scheduled waiter");
    [bad waitUntilCompleted];
    printf("PASS: actual frontend methods preserve FIFO, broadcast waits and handler order\n");
    [bad release]; [first release]; [second release]; [event release]; [queue release]; dispatch_release(external);
    return 0;
} }
