/* SPDX-License-Identifier: MIT */
#import <UIKit/UIKit.h>
#import <QuartzCore/QuartzCore.h>
#include <mach/mach_time.h>
#include <limits.h>
#include <math.h>
#include <os/log.h>
#include <stdlib.h>
#ifdef GAUGUIN_REFRESH_OVERLAY
#include <stdio.h>
#include <string.h>
#include <sys/sysctl.h>
#endif

enum { marker_bits = 12, marker_cells = 2 + marker_bits * 2, sample_limit = 1 << marker_bits };
static const CFTimeInterval warmup_seconds = 1.0;
static const CFTimeInterval default_sample_seconds = 5.0;
static const CFTimeInterval steady_sample_seconds = 32.0;
static NSString *const opt_in_key = @"CADisableMinimumFrameDurationOnPhone";
static NSString *const sample_seconds_key = @"GauguinRefreshSampleSeconds";

struct sample {
    double observed;
    double timestamp;
    double target;
    uint64_t tick;
    unsigned frame;
};

static int compare_time(const void *left, const void *right)
{
    double a = *(const double *)left, b = *(const double *)right;
    return (a > b) - (a < b);
}

static unsigned marker_gray(unsigned frame)
{
    return frame ^ (frame >> 1);
}

@interface GauguinRefreshView : UIViewController
- (void)runRate:(NSInteger)rate;
- (void)stopWithStatus:(NSString *)status;
#ifdef GAUGUIN_REFRESH_OVERLAY
- (void)displayFrame:(unsigned)frame;
#endif
@end

@implementation GauguinRefreshView {
    UILabel *_status;
    NSArray<UIButton *> *_buttons;
    CALayer *_cells[marker_cells];
    UIView *_marker;
    CADisplayLink *_link;
    NSTimer *_stopTimer;
    struct sample _samples[sample_limit];
    CFTimeInterval _sampleStart, _sampleEnd, _sampleDuration;
    NSUInteger _count;
    unsigned _frame, _gray;
    NSInteger _request, _screenMaximum;
    BOOL _optIn;
}

- (void)viewDidLoad
{
    [super viewDidLoad];
    self.view.backgroundColor = UIColor.systemBackgroundColor;
    NSBundle *bundle = NSBundle.mainBundle;
    _optIn = [[bundle objectForInfoDictionaryKey:opt_in_key] boolValue];
    NSNumber *duration = [bundle objectForInfoDictionaryKey:sample_seconds_key];
    _sampleDuration = [duration isKindOfClass:NSNumber.class] && duration.doubleValue == steady_sample_seconds
        ? steady_sample_seconds : default_sample_seconds;
#ifdef GAUGUIN_REFRESH_OVERLAY
    _sampleDuration = steady_sample_seconds;
    self.view.backgroundColor = UIColor.whiteColor;
    self.view.opaque = YES;
#endif

    _status = [[UILabel alloc] init];
    _status.numberOfLines = 0;
    _status.textAlignment = NSTextAlignmentCenter;
    _status.font = [UIFont monospacedDigitSystemFontOfSize:16 weight:UIFontWeightMedium];
    [_status.heightAnchor constraintEqualToConstant:104].active = YES;
    _status.text = _optIn ? @"High refresh opt-in enabled\nSelect a test rate" : @"Control\nSelect a test rate";

    _marker = [[UIView alloc] init];
    _marker.layer.borderColor = UIColor.grayColor.CGColor;
    _marker.layer.borderWidth = 1;
    [_marker.heightAnchor constraintEqualToConstant:30].active = YES;
    for (NSUInteger i = 0; i < marker_cells; ++i) {
        _cells[i] = [CALayer layer];
        [_marker.layer addSublayer:_cells[i]];
    }
    _cells[0].backgroundColor = UIColor.whiteColor.CGColor;
    _cells[1].backgroundColor = UIColor.blackColor.CGColor;
    _gray = UINT_MAX;
    [self displayFrame:0];

    NSMutableArray<UIButton *> *buttons = [NSMutableArray array];
    for (NSNumber *rate in @[@60, @90, @120]) {
        UIButton *button = [UIButton buttonWithType:UIButtonTypeSystem];
        button.tag = rate.integerValue;
        [button setTitle:[NSString stringWithFormat:@"%@ Hz", rate] forState:UIControlStateNormal];
        [button.heightAnchor constraintGreaterThanOrEqualToConstant:44].active = YES;
        [button addTarget:self action:@selector(startButton:) forControlEvents:UIControlEventTouchUpInside];
        [buttons addObject:button];
    }
    _buttons = [buttons copy];
    UIStackView *choices = [[UIStackView alloc] initWithArrangedSubviews:_buttons];
    choices.distribution = UIStackViewDistributionFillEqually;
    UIStackView *stack = [[UIStackView alloc] initWithArrangedSubviews:@[_status, _marker, choices]];
#ifdef GAUGUIN_REFRESH_OVERLAY
    _status.hidden = YES;
    choices.hidden = YES;
#endif
    stack.axis = UILayoutConstraintAxisVertical;
    stack.spacing = 18;
    stack.translatesAutoresizingMaskIntoConstraints = NO;
    [self.view addSubview:stack];
    UILayoutGuide *safe = self.view.safeAreaLayoutGuide;
    [NSLayoutConstraint activateConstraints:@[
        [stack.leadingAnchor constraintEqualToAnchor:safe.leadingAnchor constant:20],
        [stack.trailingAnchor constraintEqualToAnchor:safe.trailingAnchor constant:-20],
        [stack.centerYAnchor constraintEqualToAnchor:safe.centerYAnchor],
    ]];
}

#ifdef GAUGUIN_REFRESH_OVERLAY
- (BOOL)prefersStatusBarHidden
{
    return YES;
}

- (BOOL)prefersHomeIndicatorAutoHidden
{
    return YES;
}
#endif

- (void)viewDidLayoutSubviews
{
    [super viewDidLayoutSubviews];
    CGSize size = _marker.bounds.size;
    [CATransaction begin];
    [CATransaction setDisableActions:YES];
    for (NSUInteger i = 0; i < marker_cells; ++i) {
        CGFloat x = floor(size.width * i / marker_cells);
        CGFloat end = floor(size.width * (i + 1) / marker_cells);
        _cells[i].frame = CGRectMake(x, 0, end - x, size.height);
    }
    [CATransaction commit];
}

- (void)displayFrame:(unsigned)frame
{
    unsigned gray = marker_gray(frame);
    unsigned changed = gray ^ _gray;
    CGColorRef white = UIColor.whiteColor.CGColor;
    CGColorRef black = UIColor.blackColor.CGColor;
    [CATransaction begin];
    [CATransaction setDisableActions:YES];
    for (unsigned bit = 0; bit < marker_bits; ++bit) {
        if (!(changed & (1u << bit)))
            continue;
        BOOL high = !!(gray & (1u << bit));
        _cells[2 + bit * 2].backgroundColor = high ? white : black;
        _cells[3 + bit * 2].backgroundColor = high ? black : white;
    }
    [CATransaction commit];
    _gray = gray;
}

- (void)startButton:(UIButton *)sender
{
    [self runRate:sender.tag];
}

- (void)runRate:(NSInteger)rate
{
    UIScreen *screen = self.view.window.screen;
    if (_link || !screen || (rate != 60 && rate != 90 && rate != 120))
        return;
    _request = rate;
    _screenMaximum = screen.maximumFramesPerSecond;
    _frame = 0;
    _count = 0;
    [self displayFrame:_frame];
    for (UIButton *button in _buttons)
        button.enabled = NO;
    _status.text = [NSString stringWithFormat:@"Measuring %ld Hz\nReported maximum %ld Hz",
                    (long)_request, (long)_screenMaximum];
    [self.view layoutIfNeeded];

    NSProcessInfo *process = NSProcessInfo.processInfo;
    mach_timebase_info_data_t timebase = {0};
    (void)mach_timebase_info(&timebase);
    os_log(OS_LOG_DEFAULT, "GAUGUIN REFRESH v1 begin request=%ld opt_in=%d screen_max=%ld low_power=%d thermal=%ld numer=%u denom=%u",
           (long)_request, _optIn, (long)_screenMaximum, process.lowPowerModeEnabled,
           (long)process.thermalState, timebase.numer, timebase.denom);

    CFTimeInterval start = CACurrentMediaTime();
    _sampleStart = start + warmup_seconds;
    _sampleEnd = _sampleStart + _sampleDuration;
#ifdef GAUGUIN_REFRESH_OVERLAY
    double ticksPerSecond = 1e9 * timebase.denom / timebase.numer;
    fprintf(stderr, "GAUGUIN MARKER: begin=%llu start=%llu end=%llu numer=%u denom=%u max=%ld rate=%ld\n",
            (unsigned long long)llround(start * ticksPerSecond),
            (unsigned long long)llround(_sampleStart * ticksPerSecond),
            (unsigned long long)llround(_sampleEnd * ticksPerSecond),
            timebase.numer, timebase.denom, (long)_screenMaximum, (long)_request);
#endif
    _link = [CADisplayLink displayLinkWithTarget:self selector:@selector(tick:)];
    float requested = (float)rate;
    _link.preferredFrameRateRange = CAFrameRateRangeMake(requested, requested, requested);
    [_link addToRunLoop:NSRunLoop.mainRunLoop forMode:NSRunLoopCommonModes];
    _stopTimer = [NSTimer timerWithTimeInterval:warmup_seconds + _sampleDuration target:self
                 selector:@selector(windowEnded:) userInfo:nil repeats:NO];
    [NSRunLoop.mainRunLoop addTimer:_stopTimer forMode:NSRunLoopCommonModes];
}

- (void)windowEnded:(NSTimer *)timer
{
    if (timer == _stopTimer)
        [self stopWithStatus:@"complete"];
}

- (void)tick:(CADisplayLink *)link
{
    double now = CACurrentMediaTime();
    if (now >= _sampleEnd) {
        [self stopWithStatus:@"complete"];
        return;
    }
    if (_frame + 1 >= (1u << marker_bits) || _count == sample_limit) {
        [self stopWithStatus:@"capacity"];
        return;
    }
    if (now >= _sampleStart) {
        _samples[_count++] = (struct sample){now, link.timestamp, link.targetTimestamp,
                                            mach_absolute_time(), _frame + 1};
    }
    [self displayFrame:++_frame];
}

- (void)stopWithStatus:(NSString *)status
{
    if (!_link)
        return;
    [_link invalidate];
    _link = nil;
    [_stopTimer invalidate];
    _stopTimer = nil;
    for (UIButton *button in _buttons)
        button.enabled = YES;

    double intervals[sample_limit];
    NSUInteger count = _count;
#ifdef GAUGUIN_REFRESH_OVERLAY
    for (NSUInteger i = 0; i < count; ++i) {
        struct sample entry = _samples[i];
        fprintf(stderr, "GAUGUIN MARKER: id=%u tick=%llu target=%.9f\n",
                entry.frame, (unsigned long long)entry.tick, entry.target);
    }
    fprintf(stderr, "GAUGUIN MARKER: status=%s count=%lu stop=%llu\n",
            status.UTF8String, (unsigned long)count, (unsigned long long)mach_absolute_time());
#endif
    if (count < 2) {
        _status.text = [NSString stringWithFormat:@"%@: insufficient callbacks (%lu)", status, (unsigned long)count];
        os_log(OS_LOG_DEFAULT, "GAUGUIN REFRESH v1 end status=%{public}@ request=%ld callbacks=%lu sufficient=0",
               status, (long)_request, (unsigned long)count);
        return;
    }
    struct sample first = _samples[0], last = _samples[count - 1];
    NSUInteger late = 0, invalidTargets = 0;
    double targetIntervals[sample_limit];
    NSUInteger targetCount = 0;
    for (NSUInteger i = 0; i < count; ++i) {
        struct sample entry = _samples[i];
        if (i)
            intervals[i - 1] = (entry.observed - _samples[i - 1].observed) * 1000.0;
        double interval = entry.target - entry.timestamp;
        if (!isfinite(interval) || interval <= 0.0 || !isfinite(entry.timestamp)) {
            ++invalidTargets;
            continue;
        }
        targetIntervals[targetCount++] = interval * 1000.0;
        late += entry.observed >= entry.target;
    }
    qsort(intervals, count - 1, sizeof(intervals[0]), compare_time);
    qsort(targetIntervals, targetCount, sizeof(targetIntervals[0]), compare_time);
    double elapsed = last.observed - first.observed;
    double rate = elapsed > 0.0 ? (count - 1) / elapsed : 0.0;
    double p50 = intervals[(count - 2) / 2];
    double p95 = intervals[(count - 2) * 95 / 100];
    double targetP50 = targetCount ? targetIntervals[(targetCount - 1) / 2] : 0.0;
    _status.text = [NSString stringWithFormat:@"%@ · %@\n%ld requested / %ld reported Hz\n%.1f callbacks/s · p95 %.2f ms\nCamera IDs %u–%u",
                    status, _optIn ? @"opt-in" : @"control", (long)_request, (long)_screenMaximum,
                    rate, p95, first.frame, last.frame];
    os_log(OS_LOG_DEFAULT, "GAUGUIN REFRESH v1 end status=%{public}@ request=%ld opt_in=%d screen_max=%ld callbacks=%lu callback_hz=%.3f callback_p50_ms=%.3f callback_p95_ms=%.3f target_p50_ms=%.3f late=%lu invalid_targets=%lu first_id=%u last_id=%u first_tick=%llu last_tick=%llu",
           status, (long)_request, _optIn, (long)_screenMaximum, (unsigned long)count, rate,
           p50, p95, targetP50, (unsigned long)late, (unsigned long)invalidTargets,
           first.frame, last.frame, first.tick, last.tick);
}
@end

#ifdef GAUGUIN_REFRESH_OVERLAY

/* Fixed boot-clock schedule within the existing 0419 45-second CRC capture.
 * The opaque non-key window consumes the diagnostic drag over the Home Screen.
 * Its held Gray words give the host independent CRC references. */
static const unsigned calibration[] = {
    0, 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 0x735, 0xaca, 0,
};
static const uint64_t overlayStart = 229500;
static const uint64_t calibrationStart = 230650;
static const uint64_t calibrationStep = 180;
static const uint64_t sampleStart = 234000;
static const uint64_t overlayEnd = 269500;
static mach_timebase_info_data_t overlayTimebase;
static UIWindow *probeWindow;
static GauguinRefreshView *probeView;

static void probeAt(uint64_t bootMilliseconds, dispatch_block_t action)
{
    uint64_t elapsed = (uint64_t)(((__uint128_t)mach_absolute_time() * overlayTimebase.numer)
                                  / overlayTimebase.denom);
    uint64_t target = bootMilliseconds * NSEC_PER_MSEC;
    int64_t delay = target > elapsed ? (int64_t)(target - elapsed) : 0;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, delay), dispatch_get_main_queue(), action);
}

static unsigned frameForGray(unsigned gray)
{
    unsigned frame = 0;
    for (; gray; gray >>= 1)
        frame ^= gray;
    return frame;
}

static UIWindow *makeProbeWindow(UIApplication *app)
{
    for (UIScene *scene in app.connectedScenes) {
        if ([scene isKindOfClass:UIWindowScene.class] &&
            scene.activationState == UISceneActivationStateForegroundActive)
            return [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    }
    // SpringBoard also supports the legacy screen-attached window path.
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wdeprecated-declarations"
    UIScreen *screen = app.keyWindow.screen ?: UIScreen.mainScreen;
#pragma clang diagnostic pop
    return screen ? [[UIWindow alloc] initWithFrame:screen.bounds] : nil;
}

static void showProbe(void)
{
    probeWindow = makeProbeWindow(UIApplication.sharedApplication);
    if (!probeWindow) {
        fputs("GAUGUIN MARKER: unavailable window\n", stderr);
        return;
    }
    probeWindow.windowLevel = UIWindowLevelAlert + 20;
    probeWindow.opaque = YES;
    probeView = [[GauguinRefreshView alloc] init];
    probeWindow.rootViewController = probeView;
    probeWindow.hidden = NO;
    [probeView.view layoutIfNeeded];
    fprintf(stderr, "GAUGUIN MARKER: window=%llu width=%.0f height=%.0f key=%d\n",
            (unsigned long long)mach_absolute_time(), probeWindow.bounds.size.width,
            probeWindow.bounds.size.height, probeWindow.isKeyWindow);

    for (unsigned index = 0; index < sizeof(calibration) / sizeof(calibration[0]); ++index) {
        unsigned gray = calibration[index];
        probeAt(calibrationStart + calibrationStep * index, ^{
            [probeView displayFrame:frameForGray(gray)];
            fprintf(stderr, "GAUGUIN MARKER: cal=%u gray=%u tick=%llu\n", index, gray,
                    (unsigned long long)mach_absolute_time());
        });
    }
    probeAt(sampleStart, ^{ [probeView runRate:60]; });
    probeAt(overlayEnd, ^{
        [probeView stopWithStatus:@"interrupted"];
        probeWindow.hidden = YES;
        probeWindow.rootViewController = nil;
        probeView = nil;
        probeWindow = nil;
        fprintf(stderr, "GAUGUIN MARKER: removed=%llu\n", (unsigned long long)mach_absolute_time());
    });
}

__attribute__((constructor))
static void scheduleProbe(void)
{
    char args[1024] = {0};
    size_t size = sizeof(args) - 1;
    if (strcmp(getprogname(), "SpringBoard") != 0 ||
        sysctlbyname("kern.bootargs", args, &size, NULL, 0) != 0 ||
        !strstr(args, " swp=5 ") || !strstr(args, " sbp=1 ") ||
        strncmp(args, "debug=", 6) != 0 ||
        mach_timebase_info(&overlayTimebase) != KERN_SUCCESS || !overlayTimebase.numer || !overlayTimebase.denom)
        return;
    uint64_t now = mach_absolute_time();
    if (((__uint128_t)now * overlayTimebase.numer) / overlayTimebase.denom >= overlayStart * NSEC_PER_MSEC)
        return;
    fprintf(stderr, "GAUGUIN MARKER: armed=%llu\n", (unsigned long long)now);
    probeAt(overlayStart, ^{ showProbe(); });
}

#else

@interface GauguinRefreshScene : UIResponder <UIWindowSceneDelegate>
@property(nonatomic, strong) UIWindow *window;
@end

@implementation GauguinRefreshScene
- (void)scene:(UIScene *)scene willConnectToSession:(UISceneSession *)session
      options:(UISceneConnectionOptions *)options
{
    (void)session;
    (void)options;
    if (![scene isKindOfClass:UIWindowScene.class])
        return;
    self.window = [[UIWindow alloc] initWithWindowScene:(UIWindowScene *)scene];
    self.window.rootViewController = [[GauguinRefreshView alloc] init];
    [self.window makeKeyAndVisible];
}

- (void)sceneWillResignActive:(UIScene *)scene
{
    (void)scene;
    [(GauguinRefreshView *)self.window.rootViewController stopWithStatus:@"interrupted"];
}
@end

@interface GauguinRefreshApp : UIResponder <UIApplicationDelegate>
@end
@implementation GauguinRefreshApp
@end

int main(int argc, char **argv)
{
    @autoreleasepool {
        return UIApplicationMain(argc, argv, nil, NSStringFromClass(GauguinRefreshApp.class));
    }
}
#endif
