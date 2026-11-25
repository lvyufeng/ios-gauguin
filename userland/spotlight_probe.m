/* SPDX-License-Identifier: MIT */
/* A passive input and keyboard observer for a single Gauguin test boot. */
#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#include <limits.h>
#include <mach/mach_time.h>
#include <math.h>
#include <objc/runtime.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysctl.h>

static mach_timebase_info_data_t timebase;
static void (*originalSendEvent)(UIApplication *, SEL, UIEvent *);
static dispatch_queue_t output;
static __weak UITouch *trackedTouch;
static NSUInteger inputID, rows;
static CGPoint startPoint;
static uint64_t traceStart;
static BOOL scriptedTiming;
static uint64_t timingUntil;
static NSUInteger timingRows;
static void (*originalCommit)(id, SEL);
static void (*originalFlush)(id, SEL);

static uint64_t ticksForSeconds(double seconds)
{
    return (uint64_t)llround(seconds * 1e9 * timebase.denom / timebase.numer);
}

static BOOL sampleAt(uint64_t tick)
{
    return rows < 256 && traceStart && tick - traceStart < ticksForSeconds(75);
}

static void logTiming(unsigned kind, uint64_t start, uint64_t stop)
{
    if (!scriptedTiming || start > timingUntil || timingRows >= 640)
        return;
    NSUInteger identifier = inputID;
    ++timingRows;
    dispatch_async(output, ^{
        fprintf(stderr, "GAUGUIN SEARCH TIME: input=%lu kind=%u start=%llu stop=%llu\n",
                (unsigned long)identifier,kind,(unsigned long long)start,(unsigned long long)stop);
    });
}

static void observeLoop(CFRunLoopObserverRef observer, CFRunLoopActivity activity, void *context)
{
    (void)observer;
    unsigned kind = activity == kCFRunLoopAfterWaiting ? 1 : (context ? 3 : 2);
    uint64_t tick = mach_absolute_time();
    logTiming(kind,tick,tick);
}

static void observeTransaction(id receiver, SEL command, void (*original)(id,SEL), unsigned kind)
{
    if (!NSThread.isMainThread) {
        original(receiver,command);
        return;
    }
    uint64_t tick = mach_absolute_time();
    @try {
        original(receiver,command);
    } @finally {
        logTiming(kind,tick,mach_absolute_time());
    }
}

static void observeCommit(id receiver, SEL command)
{
    observeTransaction(receiver,command,originalCommit,4);
}

static void observeFlush(id receiver, SEL command)
{
    observeTransaction(receiver,command,originalFlush,5);
}

static BOOL installTransaction(SEL selector, IMP replacement, void (**original)(id,SEL))
{
    Method method = class_getClassMethod(CATransaction.class,selector);
    if (!method || method_getNumberOfArguments(method) != 2)
        return NO;
    char type[4] = {0};
    method_getReturnType(method,type,sizeof(type));
    if (strcmp(type,"v"))
        return NO;
    *original = (void (*)(id,SEL))method_getImplementation(method);
    method_setImplementation(method,replacement);
    return YES;
}

static void installLoop(void)
{
    const CFRunLoopActivity activity[] = {kCFRunLoopAfterWaiting,kCFRunLoopBeforeWaiting,kCFRunLoopBeforeWaiting};
    const CFIndex order[] = {LONG_MIN,1999999,2000001};
    unsigned installed = 0;
    for (unsigned index = 0; index < sizeof(order)/sizeof(order[0]); ++index) {
        CFRunLoopObserverContext context = {0,(void *)(uintptr_t)(index == 2),NULL,NULL,NULL};
        CFRunLoopObserverRef observer = CFRunLoopObserverCreate(NULL,activity[index],true,
                                                               order[index],observeLoop,&context);
        if (observer) {
            CFRunLoopAddObserver(CFRunLoopGetMain(),observer,kCFRunLoopCommonModes);
            CFRelease(observer);
            ++installed;
        }
    }
    BOOL commit = installTransaction(@selector(commit),(IMP)observeCommit,&originalCommit);
    BOOL flush = installTransaction(@selector(flush),(IMP)observeFlush,&originalFlush);
    fprintf(stderr,"GAUGUIN SEARCH TIME: armed loop=%u commit=%u flush=%u\n",installed,commit,flush);
}

static void logInput(NSUInteger identifier, UITouchPhase phase, unsigned shape,
                     uint64_t event, uint64_t begin, uint64_t end)
{
    ++rows;
    dispatch_async(output, ^{
        fprintf(stderr, "GAUGUIN SEARCH: input=%lu phase=%ld shape=%u event=%llu begin=%llu end=%llu\n",
                (unsigned long)identifier, (long)phase, shape, (unsigned long long)event,
                (unsigned long long)begin, (unsigned long long)end);
    });
}

static void observeEvent(UIApplication *app, SEL command, UIEvent *event)
{
    UITouch *touch = event.type == UIEventTypeTouches && event.allTouches.count == 1
        ? event.allTouches.anyObject : nil;
    UITouchPhase phase = touch ? touch.phase : UITouchPhaseStationary;
    BOOL recorded = NO;
    unsigned shape = 0;
    uint64_t begin = 0, eventTick = 0;
    if (touch && (phase == UITouchPhaseBegan || phase == UITouchPhaseEnded || phase == UITouchPhaseCancelled)) {
        begin = mach_absolute_time();
        if (!traceStart && phase == UITouchPhaseBegan)
            traceStart = begin;
        if (sampleAt(begin) && isfinite(touch.timestamp) && touch.timestamp > 0) {
            eventTick = ticksForSeconds(touch.timestamp);
            if (phase == UITouchPhaseBegan) {
                ++inputID;
                trackedTouch = touch;
                startPoint = [touch locationInView:nil];
                if (scriptedTiming) {
                    timingUntil = begin + ticksForSeconds(0.9);
                    const char *view = touch.view ? object_getClassName(touch.view) : "nil";
                    NSUInteger identifier = inputID;
                    dispatch_async(output, ^{
                        fprintf(stderr,"GAUGUIN SEARCH TARGET: input=%lu view=%.80s\n",
                                (unsigned long)identifier,view);
                    });
                }
                recorded = YES;
            } else if (trackedTouch == touch) {
                CGPoint endPoint = [touch locationInView:nil];
                CGFloat x = endPoint.x - startPoint.x, y = endPoint.y - startPoint.y;
                if (fabs(x) <= 18 && fabs(y) <= 18)
                    shape = 1; // Tap.
                else if (fabs(y) >= 45 && fabs(y) > fabs(x))
                    shape = y > 0 ? 2 : 3; // Vertical swipe.
                else
                    shape = 4;
                trackedTouch = nil;
                recorded = YES;
            }
        }
    }
    NSUInteger identifier = inputID;
    originalSendEvent(app,command,event);
    if (recorded)
        logInput(identifier,phase,shape,eventTick,begin,mach_absolute_time());
}

static void observeNotification(NSNotification *notification, unsigned stage)
{
    uint64_t tick = mach_absolute_time();
    if (!NSThread.isMainThread || !sampleAt(tick))
        return;
    NSUInteger length = 0;
    if (stage == 4) {
        id field = notification.object;
        if ([field isKindOfClass:UITextField.class])
            length = ((UITextField *)field).text.length;
        else if ([field isKindOfClass:UITextView.class])
            length = ((UITextView *)field).text.length;
        else
            return;
    }
    ++rows;
    CGRect keyboard = CGRectZero;
    if (scriptedTiming && stage == 2)
        keyboard = [notification.userInfo[UIKeyboardFrameEndUserInfoKey] CGRectValue];
    dispatch_async(output, ^{
        fprintf(stderr, "GAUGUIN SEARCH: stage=%u tick=%llu length=%lu\n",
                stage, (unsigned long long)tick, (unsigned long)length);
        if (!CGRectIsEmpty(keyboard)) {
            fprintf(stderr,"GAUGUIN SEARCH GEOMETRY: tick=%llu x=%.1f y=%.1f w=%.1f h=%.1f\n",
                    (unsigned long long)tick,keyboard.origin.x,keyboard.origin.y,keyboard.size.width,keyboard.size.height);
        }
    });
}

__attribute__((constructor))
static void installObserver(void)
{
    const char *process = getprogname();
    char args[1024] = {0};
    size_t size = sizeof(args) - 1;
    if (!process || strcmp(process,"SpringBoard") != 0 ||
        sysctlbyname("kern.bootargs",args,&size,NULL,0) != 0 ||
        !strstr(args," sbp=1 ") ||
        mach_timebase_info(&timebase) != KERN_SUCCESS || !timebase.numer || !timebase.denom)
        return;
    scriptedTiming = strstr(args," sweetnvt=0 ") && strstr(args," swp=5 ") && strstr(args," s426=1 ");
    if (!scriptedTiming && !(strstr(args," sweetnvt=1 ") && strstr(args," swp=0 ")))
        return;

    Class springBoard = objc_getClass("SpringBoard");
    SEL selector = @selector(sendEvent:);
    Method method = springBoard ? class_getInstanceMethod(springBoard,selector) : NULL;
    if (!method || method_getNumberOfArguments(method) != 3)
        return;
    char result[4] = {0}, input[4] = {0};
    method_getReturnType(method,result,sizeof(result));
    method_getArgumentType(method,2,input,sizeof(input));
    if (strcmp(result,"v") || input[0] != '@')
        return;

    output = dispatch_queue_create("org.gauguin.search-probe",DISPATCH_QUEUE_SERIAL);
    originalSendEvent = (void (*)(UIApplication *,SEL,UIEvent *))method_getImplementation(method);
    if (!class_addMethod(springBoard,selector,(IMP)observeEvent,method_getTypeEncoding(method)))
        originalSendEvent = (void (*)(UIApplication *,SEL,UIEvent *))
            class_replaceMethod(springBoard,selector,(IMP)observeEvent,method_getTypeEncoding(method));
    dispatch_async(dispatch_get_main_queue(), ^{
        if (scriptedTiming)
            installLoop();
        NSNotificationCenter *center = NSNotificationCenter.defaultCenter;
        NSArray<NSNotificationName> *names = @[UIKeyboardWillShowNotification, UIKeyboardDidShowNotification,
            UIKeyboardDidHideNotification, UITextFieldTextDidChangeNotification, UITextViewTextDidChangeNotification];
        [names enumerateObjectsUsingBlock:^(NSNotificationName name, NSUInteger index, BOOL *stop) {
            (void)stop;
            [center addObserverForName:name object:nil queue:nil usingBlock:^(NSNotification *note) {
                observeNotification(note,(unsigned)MIN(index + 1,4));
            }];
        }];
        fprintf(stderr,"GAUGUIN SEARCH: active numer=%u denom=%u\n",timebase.numer,timebase.denom);
    });
}
