/* SPDX-License-Identifier: MIT
 * Public Mac Metal reference for five sampler formats and padded input rows.
 * This does not model the phone's IOSurface protection, transport or lifetime. */
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static void need(BOOL ok) { if(!ok)abort(); }
struct vertex { float x,y;uint8_t color[4]; };
int main(int argc,char **argv) { @autoreleasepool {
    need(argc==3);char *end=NULL;unsigned long n=strtoul(argv[2],&end,10);need(end && !*end && n<=UINT32_MAX);
    uint32_t seed=(uint32_t)n;id<MTLDevice> device=MTLCreateSystemDefaultDevice();need(device!=nil);
    NSError *error=nil;id<MTLLibrary> lib=[device newLibraryWithURL:[NSURL fileURLWithPath:@(argv[1])] error:&error];need(lib!=nil);
    id<MTLFunction> vs=[lib newFunctionWithName:@"gauguin_vertex"],fs=[lib newFunctionWithName:@"gauguin_texture_fragment"];need(vs && fs);
    MTLRenderPipelineDescriptor *pd=[MTLRenderPipelineDescriptor new];pd.vertexFunction=vs;pd.fragmentFunction=fs;
    pd.colorAttachments[0].pixelFormat=MTLPixelFormatRGBA8Unorm;
    MTLVertexDescriptor *vd=[MTLVertexDescriptor vertexDescriptor];
    vd.attributes[0].format=MTLVertexFormatFloat2;vd.attributes[0].offset=0;vd.attributes[0].bufferIndex=0;
    vd.attributes[1].format=MTLVertexFormatUChar4Normalized;vd.attributes[1].offset=8;vd.attributes[1].bufferIndex=0;
    vd.layouts[0].stride=sizeof(struct vertex);vd.layouts[0].stepFunction=MTLVertexStepFunctionPerVertex;vd.layouts[0].stepRate=1;pd.vertexDescriptor=vd;
    id<MTLRenderPipelineState> pipeline=[device newRenderPipelineStateWithDescriptor:pd error:&error];need(pipeline!=nil);
    const struct vertex quad[]={ {-1,1,{0,0,0,255}},{1,1,{255,0,0,255}},{-1,-1,{0,255,0,255}},
        {1,1,{255,0,0,255}},{1,-1,{255,255,0,255}},{-1,-1,{0,255,0,255}} };
    id<MTLBuffer> vertices=[device newBufferWithBytes:quad length:sizeof(quad) options:MTLResourceStorageModeShared];
    MTLSamplerDescriptor *sd=[MTLSamplerDescriptor new];sd.minFilter=sd.magFilter=MTLSamplerMinMagFilterNearest;
    sd.normalizedCoordinates=YES;sd.sAddressMode=sd.tAddressMode=MTLSamplerAddressModeClampToEdge;
    id<MTLSamplerState> sampler=[device newSamplerStateWithDescriptor:sd];id<MTLCommandQueue> queue=[device newCommandQueue];need(vertices && sampler && queue);
    const MTLPixelFormat formats[]={MTLPixelFormatR8Unorm,MTLPixelFormatRG8Unorm,MTLPixelFormatBGRA8Unorm,MTLPixelFormatRGBA16Float,MTLPixelFormatRGBA32Float};
    const char *names[]={"R8","RG8","BGRA8","RGBA16F","RGBA32F"};
    printf("GAUGUIN TASK ORACLE begin seed=%u cases=5 scope=public-macOS-Metal\n",seed);
    for(unsigned i=0;i<5;i++) @autoreleasepool {
        unsigned bpe=1u<<i,pitch=64*bpe+64;uint8_t *pixels=calloc(64,pitch);need(pixels!=NULL);
        for(unsigned y=0;y<64;y++)for(unsigned x=0;x<64;x++) {
            unsigned bits=(seed^(13*x)^(7*y)^(5*i))&15;uint8_t *p=pixels+y*pitch+x*bpe;
            unsigned count=bpe<4?bpe:4;
            for(unsigned c=0;c<count;c++) {
                unsigned component=bpe==4 && c<3?2-c:c;BOOL one=(bits&(1u<<component))!=0;
                if(bpe<=4)p[c]=one?255:0;
                else if(bpe==8) {uint16_t half=one?0x3c00:0;memcpy(p+2*c,&half,2);}
                else {float f=one?1:0;memcpy(p+4*c,&f,4);}
            }
        }
        MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:formats[i] width:64 height:64 mipmapped:NO];
        td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead;
        id<MTLTexture> source=[device newTextureWithDescriptor:td];need(source!=nil);
        [source replaceRegion:MTLRegionMake2D(0,0,64,64) mipmapLevel:0 withBytes:pixels bytesPerRow:pitch];free(pixels);
        td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm width:64 height:64 mipmapped:NO];
        td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageRenderTarget;
        id<MTLTexture> target=[device newTextureWithDescriptor:td];need(target!=nil);
        MTLRenderPassDescriptor *pass=[MTLRenderPassDescriptor renderPassDescriptor];pass.colorAttachments[0].texture=target;
        pass.colorAttachments[0].loadAction=MTLLoadActionClear;pass.colorAttachments[0].storeAction=MTLStoreActionStore;
        pass.colorAttachments[0].clearColor=MTLClearColorMake(.25,.5,.75,.5);
        id<MTLCommandBuffer> cb=[queue commandBuffer];id<MTLRenderCommandEncoder> e=[cb renderCommandEncoderWithDescriptor:pass];need(e!=nil);
        [e setRenderPipelineState:pipeline];[e setVertexBuffer:vertices offset:0 atIndex:0];[e setFragmentTexture:source atIndex:0];
        [e setFragmentSamplerState:sampler atIndex:0];[e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:6];[e endEncoding];
        [cb commit];[cb waitUntilCompleted];need(cb.status==MTLCommandBufferStatusCompleted && !cb.error);
        uint8_t output[64*64*4];[target getBytes:output bytesPerRow:256 fromRegion:MTLRegionMake2D(0,0,64,64) mipmapLevel:0];
        for(unsigned y=0;y<64;y++) {printf("GAUGUIN TASK ORACLE row case=%s y=%u rgba=",names[i],y);
            for(unsigned x=0;x<256;x++)printf("%02x",output[y*256+x]);putchar('\n');}
    }
    puts("GAUGUIN TASK ORACLE end cases=5 pixels=20480 jobs=5");return 0;
} }
