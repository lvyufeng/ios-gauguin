/* SPDX-License-Identifier: MIT
 * Same project-owned workload on a Mac GPU, with raw rows for an independent
 * Python binary16 oracle. This does not qualify the A619 GPU or iOS runtime.
 */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <CommonCrypto/CommonDigest.h>
#include <dispatch/dispatch.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum {WIDTH=64, HEIGHT=64, WORDS=4096};
static void check(bool ok, const char *phase, const char *reason)
{
    if (!ok) {fprintf(stderr,"oracle failed %s: %s\n",phase,reason ?: "unknown");exit(2);}
}
static void finish(id<MTLCommandBuffer> cb, const char *phase)
{
    [cb commit]; [cb waitUntilCompleted];
    check(cb.status==MTLCommandBufferStatusCompleted && cb.error==nil,phase,cb.error.description.UTF8String);
}
static id<MTLTexture> texture(id<MTLDevice> device, MTLPixelFormat format)
{
    MTLTextureDescriptor *d=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:format width:64 height:64 mipmapped:NO];
    d.storageMode=MTLStorageModeShared;d.usage=MTLTextureUsageRenderTarget|MTLTextureUsageShaderRead;
    id<MTLTexture> result=[device newTextureWithDescriptor:d];check(result!=nil,"texture","allocation");return result;
}
#include "native_fp16_tests.h"
int main(void)
{
    @autoreleasepool {
        id<MTLDevice> device=MTLCreateSystemDefaultDevice();check(device!=nil,"device","Mac GPU missing");
        id<MTLCommandQueue> queue=[device newCommandQueue];check(queue!=nil,"queue","Mac queue missing");
        for(uint32_t seed=0;seed<4;seed++) @autoreleasepool {native_fp16_pixels(device,queue,seed);}
        [queue release];[device release];
    }
    return 0;
}
