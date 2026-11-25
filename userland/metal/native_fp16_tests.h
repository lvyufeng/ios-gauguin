/* SPDX-License-Identifier: MIT
 * Included after the frontend probe's check/finish/texture helpers. The Mac
 * oracle uses the same rendering workload but independently reviews raw rows.
 */
#include "GauguinFP16Proof.h"
#include "gauguin_native_fp16_library.h"

static uint64_t native_fp16_pixels(id<MTLDevice> device, id<MTLCommandQueue> queue, uint32_t seed)
{
    unsigned char digest[CC_SHA256_DIGEST_LENGTH]; char hex[65];
    CC_SHA256(gauguin_native_fp16_library, sizeof(gauguin_native_fp16_library), digest);
    for (unsigned i = 0; i < sizeof(digest); i++) snprintf(hex + 2 * i, 3, "%02x", digest[i]);
    check(!strcmp(hex, GAUGUIN_NATIVE_FP16_LIBRARY_SHA256), "FP16-library", "embedded own shader digest");
    dispatch_data_t bytes = dispatch_data_create(gauguin_native_fp16_library, sizeof(gauguin_native_fp16_library), NULL, ^{});
    NSError *error = nil;
    id<MTLLibrary> library = [device newLibraryWithData:bytes error:&error];
    dispatch_release(bytes);
    check(library != nil, "FP16-library", [[error description] UTF8String]);
    id<MTLFunction> vertex = [library newFunctionWithName:@"gauguin_fp16_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"gauguin_fp16_fragment"];
    check(vertex && fragment, "FP16-library", "own half entrypoints");
    MTLRenderPipelineDescriptor *descriptor = [[MTLRenderPipelineDescriptor alloc] init];
    descriptor.vertexFunction = vertex; descriptor.fragmentFunction = fragment;
    descriptor.colorAttachments[0].pixelFormat = MTLPixelFormatRGBA16Float;
    id<MTLRenderPipelineState> pipeline = [device newRenderPipelineStateWithDescriptor:descriptor error:&error];
    check(pipeline != nil, "FP16-pipeline", [[error description] UTF8String]);
    const float triangle[3][4] = {{-1, -1, 0, 1}, {3, -1, 0, 1}, {-1, 3, 0, 1}};
    const uint16_t colors[4][4] = {
        {0x3800, 0x3400, 0x3a00, 0x3c00}, {0x3c00, 0xb800, 0x3800, 0x3c00},
        {0xb800, 0x3c00, 0x3400, 0x3c00}, {0x3a00, 0x3a00, 0x3c00, 0x3c00},
    };
    float positions[12][4]; uint16_t inputs[12][4];
    for (unsigned band = 0; band < 4; band++) for (unsigned i = 0; i < 3; i++) {
        memcpy(positions[band * 3 + i], triangle[i], sizeof(triangle[i]));
        memcpy(inputs[band * 3 + i], colors[(band + (seed & 3)) & 3], sizeof(colors[0]));
    }
    const uint16_t params[8] = {0x3800, 0x3c00, 0x4000, 0x3800, 0x3000, 0x3400, 0xb000, 0x3800};
    id<MTLBuffer> pos = [device newBufferWithBytes:positions length:sizeof(positions) options:MTLResourceStorageModeShared];
    id<MTLBuffer> color = [device newBufferWithBytes:inputs length:sizeof(inputs) options:MTLResourceStorageModeShared];
    id<MTLBuffer> parameters = [device newBufferWithBytes:params length:sizeof(params) options:MTLResourceStorageModeShared];
    check(pos && color && parameters, "FP16-buffer", "runtime half inputs");
    id<MTLTexture> target = texture(device, MTLPixelFormatRGBA16Float);
    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = target;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(1, 0, 1, 1);
    id<MTLCommandBuffer> cb = [queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [cb renderCommandEncoderWithDescriptor:pass];
    check(encoder != nil, "FP16-encoder", "render encoder");
    [encoder setRenderPipelineState:pipeline];
    [encoder setViewport:(MTLViewport){0, 0, WIDTH, HEIGHT, 0, 1}];
    [encoder setVertexBuffer:pos offset:0 atIndex:0];
    [encoder setVertexBuffer:color offset:0 atIndex:1];
    [encoder setFragmentBuffer:parameters offset:0 atIndex:0];
    for (unsigned band = 0; band < 4; band++) {
        [encoder setScissorRect:(MTLScissorRect){band * 16, 0, 16, HEIGHT}];
        [encoder drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:band * 3 vertexCount:3];
    }
    [encoder endEncoding]; finish(cb, "FP16-native");
    uint16_t got[WORDS * 4]; memset(got, 0xa5, sizeof(got));
    [target getBytes:got bytesPerRow:WIDTH * 8 fromRegion:MTLRegionMake2D(0, 0, WIDTH, HEIGHT) mipmapLevel:0];
    uint64_t hash = UINT64_C(14695981039346656037);
    printf("GAUGUIN FP16 begin seed=%u width=64 height=64 format=115 GPU_jobs=1\n", seed);
    for (unsigned y = 0; y < HEIGHT; y++) {
        char row[WIDTH * 16 + 1];
        for (unsigned x = 0; x < WIDTH; x++) for (unsigned c = 0; c < 4; c++) {
            uint16_t value = got[(y * WIDTH + x) * 4 + c];
            for (unsigned b = 0; b < 2; b++) {
                uint8_t byte = (uint8_t)(value >> (8 * b));
                snprintf(row + x * 16 + c * 4 + b * 2, 3, "%02x", byte);
                hash = (hash ^ byte) * UINT64_C(1099511628211);
            }
        }
        printf("GAUGUIN FP16 row=%u hex=%s\n", y, row);
    }
    for (unsigned y = 0; y < HEIGHT; y++) for (unsigned x = 0; x < WIDTH; x++) for (unsigned c = 0; c < 4; c++)
        check(got[(y * WIDTH + x) * 4 + c] == gauguin_fp16_expected(x, c, seed), "FP16-pixels", "exact half arithmetic/varying readback");
    check(hash == gauguin_fp16_expected_hash(seed), "FP16-pixels", "readback hash");
    printf("GAUGUIN FP16 pixels=4096 half_channels=16384 hash=%016llx PASS\n", (unsigned long long)hash);
    [target release]; [pos release]; [color release]; [parameters release];
    [pipeline release]; [descriptor release]; [vertex release]; [fragment release]; [library release];
    return hash;
}
