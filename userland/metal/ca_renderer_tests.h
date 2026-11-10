/* SPDX-License-Identifier: MIT
 * Real CARenderer/CALayer offscreen scenes. No default-device interposition.
 * The CPU oracle uses linear sRGB, pixel-aligned edges and nearest filtering.
 */
#import <QuartzCore/QuartzCore.h>
#import <CoreGraphics/CoreGraphics.h>

static NSDictionary *ca_stats(id<MTLDevice> device)
{
    SEL selector = sel_registerName("gauguinCAExactStats");
    check([device respondsToSelector:selector], "CA-profile", "exact profile stats missing");
    NSDictionary *stats = ((id (*)(id, SEL))objc_msgSend)(device, selector);
    check([stats isKindOfClass:[NSDictionary class]] && [stats[@"profile"] unsignedIntValue] == 1 &&
          [stats[@"refusals"] unsignedLongLongValue] == 0, "CA-profile", "exact draw contract");
    return stats;
}
static void ca_color(CALayer *layer, CGColorSpaceRef space, CGFloat r, CGFloat g, CGFloat b, CGFloat a)
{
    CGFloat values[] = {r, g, b, a};
    CGColorRef color = CGColorCreate(space, values);
    check(color != NULL, "CA-color", "CGColorCreate");
    layer.backgroundColor = color;
    CGColorRelease(color);
}
static CALayer *ca_layer(CGRect frame)
{
    CALayer *layer = [CALayer layer];
    layer.frame = frame;
    layer.contentsScale = 1;
    layer.minificationFilter = kCAFilterNearest;
    layer.magnificationFilter = kCAFilterNearest;
    return layer;
}
static uint32_t ca_bgra(unsigned r, unsigned g, unsigned b, unsigned a)
{
    return b | (g << 8) | (r << 16) | (a << 24);
}
static void ca_image(CALayer *layer, CGColorSpaceRef space, const uint32_t *pixels)
{
    /* CFData owns a copy: later stack reuse cannot change queued layer contents. */
    CFDataRef data = CFDataCreate(kCFAllocatorDefault, (const UInt8 *)pixels, WORDS * 4);
    CGDataProviderRef provider = data ? CGDataProviderCreateWithCFData(data) : NULL;
    CGImageRef image = provider ? CGImageCreate(WIDTH, HEIGHT, 8, 32, STRIDE, space,
            kCGBitmapByteOrder32Little | kCGImageAlphaPremultipliedFirst, provider, NULL, false,
            kCGRenderingIntentDefault) : NULL;
    check(image != NULL, "CA-image", "owned premultiplied BGRA image");
    layer.contents = (id)image;
    CGImageRelease(image); CGDataProviderRelease(provider); CFRelease(data);
}
static void ca_readback(id<MTLDevice> device, id<MTLCommandQueue> queue, id<MTLTexture> target,
                        const uint32_t *want, const char *phase, unsigned tolerance)
{
    id<MTLBuffer> buffer = [device newBufferWithLength:WORDS * 4 options:MTLResourceStorageModeShared];
    check(buffer != nil, phase, "readback buffer");
    id<MTLCommandBuffer> cb = [queue commandBuffer];
    id<MTLBlitCommandEncoder> blit = [cb blitCommandEncoder];
    check(blit != nil, phase, "ordered readback encoder");
    [blit copyFromTexture:target sourceSlice:0 sourceLevel:0 sourceOrigin:MTLOriginMake(0, 0, 0)
              sourceSize:MTLSizeMake(WIDTH, HEIGHT, 1) toBuffer:buffer destinationOffset:0
      destinationBytesPerRow:STRIDE destinationBytesPerImage:WORDS * 4];
    [blit endEncoding];
    finish(cb, phase); /* Same supplied queue: waits for all earlier CA commits. */
    const uint32_t *got = [buffer contents];
    check(got != NULL, phase, "mapped readback");
    /* Own synthetic scenes only, no UI capture. Preserve even a failed scene's
     * full readback so a host reviewer can compare every channel independently. */
    for (unsigned y = 0; y < HEIGHT; y++) {
        char hex[WIDTH * 8 + 1];
        for (unsigned x = 0; x < WIDTH; x++) for (unsigned c = 0; c < 4; c++)
            snprintf(hex + x * 8 + c * 2, 3, "%02x", (got[y * WIDTH + x] >> (c * 8)) & 255);
        receipt("CA-readback scene=%s row=%u hex=%s\n", phase, y, hex);
    }
    uint64_t hash = 14695981039346656037ULL;
    unsigned maximum = 0;
    for (unsigned i = 0; i < WORDS; i++) {
        for (unsigned c = 0; c < 4; c++) {
            unsigned a = (got[i] >> (c * 8)) & 255, b = (want[i] >> (c * 8)) & 255;
            unsigned delta = a > b ? a - b : b - a;
            if (delta > tolerance) {
                char reason[160];
                snprintf(reason, sizeof(reason), "pixel=%u channel=%u actual=%u expected=%u tolerance=%u",
                         i, c, a, b, tolerance);
                fail(phase, reason);
            }
            if (delta > maximum) maximum = delta;
            hash = (hash ^ a) * 1099511628211ULL;
        }
    }
    receipt("CA-pixels scene=%s pixels=4096 tolerance=%u max_error=%u hash=%016llx PASS\n",
            phase, tolerance, maximum, (unsigned long long)hash);
    [buffer release];
}
static void ca_render_scenes(id<MTLDevice> device, id<MTLCommandQueue> queue)
{
    Class cls = objc_getClass("CARenderer");
    Method constructor = cls ? class_getClassMethod(cls, @selector(rendererWithMTLTexture:options:)) : NULL;
    check(constructor && !strcmp(method_getTypeEncoding(constructor), "@32@0:8@16@24"),
          "CA-ABI", "actual20H392 CARenderer constructor encoding");
    static const struct { const char *name, *type; } methods[] = {
        {"setLayer:", "v24@0:8@16"},
        {"setBounds:", "v48@0:8{CGRect={CGPoint=dd}{CGSize=dd}}16"},
        {"addUpdateRect:", "v48@0:8{CGRect={CGPoint=dd}{CGSize=dd}}16"},
        {"beginFrameAtTime:timeStamp:", "v32@0:8d16^{?=IiqQdq{CVSMPTETime=ssIIIssss}QQ}24"},
        {"render", "v16@0:8"}, {"endFrame", "v16@0:8"},
    };
    for (unsigned i = 0; i < sizeof(methods) / sizeof(methods[0]); i++) {
        Method method = class_getInstanceMethod(cls, sel_registerName(methods[i].name));
        check(method && !strcmp(method_getTypeEncoding(method), methods[i].type), "CA-ABI", methods[i].name);
    }
    receipt("CA-ABI OS=20H392 class_methods=1 instance_methods=6 PASS\n");
    trusted_file(@"/System/Library/Frameworks/QuartzCore.framework/default.metallib");
    /* Pin the exact image's full library, including its own EDR/luma functions. */
    NSData *library = [NSData dataWithContentsOfFile:@"/System/Library/Frameworks/QuartzCore.framework/default.metallib"];
    unsigned char digest[CC_SHA256_DIGEST_LENGTH]; char hex[65];
    check(library.length == 1014944, "CA-library", "20H392 library length");
    CC_SHA256(library.bytes, (CC_LONG)library.length, digest);
    for (unsigned i = 0; i < sizeof(digest); i++) snprintf(hex + i * 2, 3, "%02x", digest[i]);
    check(!strcmp(hex, "11c74cc42ce5137b73d44d427f75764f886656d4ddb374422d56b609ed2762d9"),
          "CA-library", "20H392 library digest");
    ca_stats(device);
    CGColorSpaceRef space = CGColorSpaceCreateWithName(kCGColorSpaceLinearSRGB);
    check(space != NULL, "CA-colorspace", "linear sRGB");
    id<MTLTexture> target = texture(device, MTLPixelFormatBGRA8Unorm);
    CARenderer *renderer = [[CARenderer rendererWithMTLTexture:target
                     options:@{kCARendererMetalCommandQueue: queue,
                               kCARendererColorSpace: (id)space}] retain];
    check(renderer != nil, "CA-renderer", "explicit texture/queue renderer");
    renderer.bounds = CGRectMake(0, 0, WIDTH, HEIGHT);
    CALayer *root = [ca_layer(renderer.bounds) retain];
    CALayer *content = [ca_layer(root.bounds) retain];
    root.opaque = YES;
    ca_color(root, space, 0, 0, 0, 1);
    [root addSublayer:content];
    renderer.layer = root;
    static const char *const names[] = {"opaque", "image", "alpha", "mask", "updated-image"};
    uint32_t source[WORDS], expected[WORDS];
    for (unsigned scene = 0; scene < 5; scene++) {
        @autoreleasepool {
        memory(names[scene]);
        uint64_t before = [ca_stats(device)[@"draws"] unsignedLongLongValue];
        clear(queue, target, MTLClearColorMake(1, 0, 1, 1), "CA-poison");
        [CATransaction begin]; [CATransaction setDisableActions:YES];
        content.sublayers = nil;
        content.mask = nil;
        content.contents = nil;
        if (scene == 0) {
            for (unsigned stripe = 0; stripe < 4; stripe++) {
                CALayer *band = ca_layer(CGRectMake(stripe * 16, 0, 16, HEIGHT));
                CGFloat value = (CGFloat)(stripe * 64) / 255;
                ca_color(band, space, value, value, value, 1);
                [content addSublayer:band];
            }
        } else {
            for (unsigned y = 0; y < HEIGHT; y++) for (unsigned x = 0; x < WIDTH; x++) {
                unsigned r = (x / 16) * 64, g = 192 - r, b = scene == 4 ? 192 : 64;
                if (scene == 2) { r /= 2; g /= 2; b /= 2; }
                source[y * WIDTH + x] = ca_bgra(r, g, b, scene == 2 ? 128 : 255);
            }
            ca_image(content, space, source);
        }
        if (scene == 3) {
            CALayer *mask = ca_layer(CGRectMake(16, 0, 32, HEIGHT));
            ca_color(mask, space, 1, 1, 1, 1);
            content.mask = mask;
        }
        for (unsigned y = 0; y < HEIGHT; y++) for (unsigned x = 0; x < WIDTH; x++) {
            unsigned r = (x / 16) * 64, g = 192 - r, b = scene == 4 ? 192 : 64;
            if (scene == 0) g = b = r;
            if (scene == 2) { r /= 2; g /= 2; b /= 2; }
            if (scene == 3 && (x < 16 || x >= 48)) r = g = b = 0;
            expected[y * WIDTH + x] = ca_bgra(r, g, b, 255);
        }
        [CATransaction commit];
        [CATransaction flush];
        [renderer beginFrameAtTime:CACurrentMediaTime() timeStamp:NULL];
        [renderer addUpdateRect:renderer.bounds];
        [renderer render];
        [renderer endFrame];
        ca_readback(device, queue, target, expected, names[scene], scene == 2 ? 2 : 1);
        uint64_t after = [ca_stats(device)[@"draws"] unsignedLongLongValue];
        check(after > before, names[scene], "CoreAnimation must encode real draws");
        receipt("CA-draws scene=%s before=%llu after=%llu omitted=0 PASS\n", names[scene],
                (unsigned long long)before, (unsigned long long)after);
        }
    }
    renderer.layer = nil;
    [content release]; [root release]; [renderer release]; [target release]; CGColorSpaceRelease(space);
    memory("CA-scenes-completed");
}
