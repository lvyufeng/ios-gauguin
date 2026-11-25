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
typedef void (^MTLCommandBufferHandler)(id<MTLCommandBuffer>);
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
    NSUInteger _scheduledPending, _completedPending;
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
- (void)hakiosQueueHandler:(MTLCommandBufferHandler)handler scheduled:(BOOL)scheduled;
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
/* CALLBACK_SUPPORT */
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
/* Appended to the existing fake-core shell, with production frontend methods. */
static atomic_int wait_started, wait_returned, returned_before_handler, handler_finished;
static atomic_int scope_stage_returned, scope_completed_handlers;
static int regression_case(void);
static int scope_case(const char *phase);

static int scope_case(const char *phase) {
    g_core = dispatch_queue_create("c4.scope.core", DISPATCH_QUEUE_SERIAL);
    HakiosMetalCommandQueue *queue = [[HakiosMetalCommandQueue alloc] init];
    dispatch_queue_t external = dispatch_queue_create("c4.scope.external", DISPATCH_QUEUE_CONCURRENT);
    [queue setCompletionQueue:external];
    hakios_metal_cb a={0}, b={0}; init_core(&a, 1, 0); init_core(&b, 2, 0);
    HakiosMetalCommandBuffer *first = [[HakiosMetalCommandBuffer alloc] initWithQueue:queue core:&a];
    HakiosMetalCommandBuffer *second = [[HakiosMetalCommandBuffer alloc] initWithQueue:queue core:&b];
    dispatch_semaphore_t entered = dispatch_semaphore_create(0);
    dispatch_semaphore_t other_entered = dispatch_semaphore_create(0);
    dispatch_semaphore_t release_handler = dispatch_semaphore_create(0);
    dispatch_semaphore_t returned = dispatch_semaphore_create(0);
    BOOL second_used = NO;
    dispatch_semaphore_signal(a.submitGate); dispatch_semaphore_signal(b.submitGate);

    if (strcmp(phase, "scope-scheduled-self-complete") == 0) {
        [first addScheduledHandler:^(id cb) {
            [(HakiosMetalCommandBuffer *)cb waitUntilScheduled];
            atomic_store(&scope_stage_returned, 1);
            dispatch_semaphore_signal(entered);
            [(HakiosMetalCommandBuffer *)cb waitUntilCompleted];
            dispatch_semaphore_signal(returned);
        }];
        [first addCompletedHandler:^(id cb) { (void)cb; atomic_fetch_add(&scope_completed_handlers, 1); }];
        [first commit];
        need(dispatch_semaphore_wait(entered, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
             "scheduled handler deadlocked waiting on its own stage");
        need(atomic_load(&scope_stage_returned) == 1, "self scheduled wait did not return");
        need(dispatch_semaphore_wait(returned, dispatch_time(DISPATCH_TIME_NOW, 300*NSEC_PER_MSEC)) != 0,
             "same-buffer callback bypassed unfinished GPU work");
        dispatch_semaphore_signal(a.finishGate);
    } else if (strcmp(phase, "scope-completed-self") == 0) {
        [first addCompletedHandler:^(id cb) {
            [(HakiosMetalCommandBuffer *)cb waitUntilScheduled];
            [(HakiosMetalCommandBuffer *)cb waitUntilCompleted];
            atomic_fetch_add(&scope_completed_handlers, 1);
            dispatch_semaphore_signal(returned);
        }];
        [first commit]; dispatch_semaphore_signal(a.finishGate);
    } else if (strcmp(phase, "scope-cross-buffer") == 0) {
        second_used = YES;
        [second addCompletedHandler:^(id cb) {
            (void)cb; dispatch_semaphore_signal(other_entered);
            dispatch_semaphore_wait(release_handler, DISPATCH_TIME_FOREVER);
            atomic_fetch_add(&scope_completed_handlers, 1);
        }];
        [second commit]; dispatch_semaphore_signal(b.finishGate);
        need(dispatch_semaphore_wait(other_entered, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
             "other buffer's handler did not enter");
        [first addCompletedHandler:^(id cb) {
            (void)cb; dispatch_semaphore_signal(entered);
            [second waitUntilCompleted];
            need(atomic_load(&scope_completed_handlers) == 1, "foreign callback bypassed other buffer's handlers");
            dispatch_semaphore_signal(returned);
        }];
        [first commit]; dispatch_semaphore_signal(a.finishGate);
        need(dispatch_semaphore_wait(entered, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
             "waiting buffer's handler did not enter");
        need(dispatch_semaphore_wait(returned, dispatch_time(DISPATCH_TIME_NOW, 300*NSEC_PER_MSEC)) != 0,
             "callback scope incorrectly bypassed another buffer");
        dispatch_semaphore_signal(release_handler);
    } else if (strcmp(phase, "scope-late-completed") == 0) {
        [first commit]; dispatch_semaphore_signal(a.finishGate); [first waitUntilCompleted];
        [first addCompletedHandler:^(id cb) {
            (void)cb; dispatch_semaphore_signal(entered);
            dispatch_semaphore_wait(release_handler, DISPATCH_TIME_FOREVER);
            atomic_fetch_add(&scope_completed_handlers, 1);
        }];
        need(dispatch_semaphore_wait(entered, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
             "late handler did not enter");
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT, 0), ^{
            [first waitUntilCompleted]; dispatch_semaphore_signal(returned);
        });
        need(dispatch_semaphore_wait(returned, dispatch_time(DISPATCH_TIME_NOW, 300*NSEC_PER_MSEC)) != 0,
             "wait bypassed an already-admitted late handler");
        dispatch_semaphore_signal(release_handler);
    } else need(NO, "unknown scope case");

    need(dispatch_semaphore_wait(returned, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
         "callback or waiter remained deadlocked");
    [first waitUntilCompleted];
    if (second_used) [second waitUntilCompleted];
    dispatch_semaphore_t drained = dispatch_semaphore_create(0);
    @synchronized(queue) { [queue hakiosAdmit:^{ dispatch_semaphore_signal(drained); }]; }
    need(dispatch_semaphore_wait(drained, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
         "scope admission drain timed out");
    dispatch_sync(first->_handlerQueue, ^{}); dispatch_sync(second->_handlerQueue, ^{});
    need(atomic_load(&scope_completed_handlers) == 1, "handler completion count mismatch");
    printf("WAIT_SCOPE phase=%s passed=1 handlers=1\n", phase);
    [first release]; [second release]; [queue release]; dispatch_release(external);
    dispatch_release(entered); dispatch_release(other_entered); dispatch_release(release_handler);
    dispatch_release(returned); dispatch_release(drained);
    dispatch_release(a.submitGate); dispatch_release(a.finishGate);
    dispatch_release(b.submitGate); dispatch_release(b.finishGate);
    pthread_mutex_destroy(&a.lock); pthread_cond_destroy(&a.changed);
    pthread_mutex_destroy(&b.lock); pthread_cond_destroy(&b.changed);
    dispatch_release(g_core);
    return 0;
}

int main(int argc, char **argv) { @autoreleasepool {
    need(argc == 3, "phase and expected behavior required");
    if (strcmp(argv[1], "regression") == 0) return regression_case();
    if (strncmp(argv[1], "scope-", 6) == 0) return scope_case(argv[1]);
    BOOL completed = strncmp(argv[1], "completed", 9) == 0;
    BOOL error = strstr(argv[1], "-error") != NULL;
    BOOL expect_early = strcmp(argv[2], "early") == 0;
    need(completed || strncmp(argv[1], "scheduled", 9) == 0, "unknown phase");
    g_core = dispatch_queue_create("c4.wait-contract.core", DISPATCH_QUEUE_SERIAL);
    HakiosMetalCommandQueue *queue = [[HakiosMetalCommandQueue alloc] init];
    dispatch_queue_t external = dispatch_queue_create("c4.wait-contract.external", DISPATCH_QUEUE_CONCURRENT);
    [queue setCompletionQueue:external];
    hakios_metal_cb core = {0}; init_core(&core, 1, error);
    HakiosMetalCommandBuffer *buffer = [[HakiosMetalCommandBuffer alloc] initWithQueue:queue core:&core];
    dispatch_semaphore_t entered = dispatch_semaphore_create(0);
    dispatch_semaphore_t release_handler = dispatch_semaphore_create(0);
    dispatch_semaphore_t returns = dispatch_semaphore_create(0);
    MTLCommandBufferHandler handler = ^(id cb) {
        (void)cb;
        dispatch_semaphore_signal(entered);
        dispatch_semaphore_wait(release_handler, DISPATCH_TIME_FOREVER);
        atomic_store(&handler_finished, 1);
    };
    if (completed) [buffer addCompletedHandler:handler];
    else [buffer addScheduledHandler:handler];
    dispatch_semaphore_signal(core.submitGate);
    [buffer commit];
    if (completed || error) dispatch_semaphore_signal(core.finishGate);
    need(dispatch_semaphore_wait(entered, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
         "handler did not start");
    for (int i=0; i<3; ++i) {
        dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT, 0), ^{
            atomic_fetch_add(&wait_started, 1);
            if (completed) [buffer waitUntilCompleted];
            else [buffer waitUntilScheduled];
            if (!atomic_load(&handler_finished)) atomic_fetch_add(&returned_before_handler, 1);
            atomic_fetch_add(&wait_returned, 1);
            dispatch_semaphore_signal(returns);
        });
    }
    until(^BOOL{ return atomic_load(&wait_started) == 3; }, "waiters did not start");
    BOOL early = dispatch_semaphore_wait(returns, dispatch_time(DISPATCH_TIME_NOW, 300*NSEC_PER_MSEC)) == 0;
    need(atomic_load(&handler_finished) == 0, "handler gate was not held");
    if (expect_early) need(early && atomic_load(&returned_before_handler) > 0, "baseline violation not reproduced");
    else need(!early && atomic_load(&wait_returned) == 0, "wait returned before its handler finished");
    dispatch_semaphore_signal(release_handler);
    until(^BOOL{ return atomic_load(&wait_returned) == 3; }, "waiters did not finish after handler release");
    if (!completed && !error) dispatch_semaphore_signal(core.finishGate);
    [buffer waitUntilCompleted];
    dispatch_semaphore_t admission_drained = dispatch_semaphore_create(0);
    @synchronized (queue) { [queue hakiosAdmit:^{ dispatch_semaphore_signal(admission_drained); }]; }
    need(dispatch_semaphore_wait(admission_drained, dispatch_time(DISPATCH_TIME_NOW, 2*NSEC_PER_SEC)) == 0,
         "frontend admission did not drain");
    dispatch_sync(buffer->_handlerQueue, ^{});
    printf("WAIT_CONTRACT phase=%s early=%d early_waiters=%d finished=%d waiters=%d\n",
           argv[1], early, atomic_load(&returned_before_handler), atomic_load(&handler_finished), atomic_load(&wait_returned));
    [buffer release]; [queue release]; dispatch_release(external);
    dispatch_release(entered); dispatch_release(release_handler); dispatch_release(returns);
    dispatch_release(admission_drained);
    dispatch_release(core.submitGate); dispatch_release(core.finishGate);
    pthread_mutex_destroy(&core.lock); pthread_cond_destroy(&core.changed);
    dispatch_release(g_core);
    return 0;
} }

static int regression_case(void) { @autoreleasepool {
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
    [bad commit];
    dispatch_async(dispatch_get_global_queue(QOS_CLASS_DEFAULT,0), ^{ [bad waitUntilScheduled]; atomic_fetch_add(&g_error_waits,1); });
    until(^BOOL{ return atomic_load(&g_order_count)==3; }, "error buffer admitted");
    usleep(50000); need(atomic_load(&g_error_waits)==0, "error scheduled before terminal callback");
    dispatch_semaphore_signal(err.finishGate);
    until(^BOOL{ return atomic_load(&g_error_waits)==1; }, "error wakes scheduled waiter");
    [bad waitUntilCompleted];
    printf("PASS: actual frontend methods preserve FIFO, broadcast waits and handler order\n");
    [bad release]; [first release]; [second release]; [event release]; [queue release]; dispatch_release(external);
    return 0;
} }
