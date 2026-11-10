// SPDX-License-Identifier: MIT
// Public macOS Metal execution of our image shaders; no A619/phone claims.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <array>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <vector>

static void need(bool ok, const char* why) {
    if (!ok) { std::fprintf(stderr, "image oracle failed: %s\n", why); std::exit(1); }
}
struct Vertex { float xy[2]; float color[4]; };
struct alignas(16) DeviceVertex { float position[4]; float color[4]; };
static_assert(sizeof(Vertex)==24 && sizeof(DeviceVertex)==32);
static constexpr float positions[6][2]={{-1,1},{1,1},{-1,-1},{1,1},{1,-1},{-1,-1}};

static id<MTLTexture> texture(id<MTLDevice> d, MTLPixelFormat f, NSUInteger w,
                               NSUInteger h, MTLTextureUsage usage) {
    auto desc=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:f width:w height:h mipmapped:NO];
    desc.storageMode=MTLStorageModeShared; desc.usage=usage;
    auto t=[d newTextureWithDescriptor:desc]; need(t!=nil,"texture allocation"); return t;
}
static id<MTLRenderPipelineState> pipeline(id<MTLDevice> d,id<MTLLibrary> lib,
                                          NSString* vs,NSString* fs,bool attributes) {
    auto p=[MTLRenderPipelineDescriptor new];
    p.vertexFunction=[lib newFunctionWithName:vs];p.fragmentFunction=[lib newFunctionWithName:fs];
    need(p.vertexFunction&&p.fragmentFunction,"shader functions");
    p.colorAttachments[0].pixelFormat=MTLPixelFormatRGBA8Unorm;
    if(attributes) {
        auto v=[MTLVertexDescriptor vertexDescriptor];
        v.attributes[0].format=MTLVertexFormatFloat2;v.attributes[0].offset=0;v.attributes[0].bufferIndex=0;
        v.attributes[1].format=MTLVertexFormatFloat4;v.attributes[1].offset=8;v.attributes[1].bufferIndex=0;
        v.layouts[0].stride=sizeof(Vertex);v.layouts[0].stepFunction=MTLVertexStepFunctionPerVertex;
        p.vertexDescriptor=v;
    }
    NSError* error=nil;auto result=[d newRenderPipelineStateWithDescriptor:p error:&error];
    if(!result)std::fprintf(stderr,"pipeline: %s\n",error.localizedDescription.UTF8String);
    need(result!=nil,"pipeline creation");return result;
}
static void dump(id<MTLTexture> t,unsigned phase,const char* plane) {
    std::vector<uint32_t> words(4096);
    [t getBytes:words.data() bytesPerRow:256 fromRegion:MTLRegionMake2D(0,0,64,64) mipmapLevel:0];
    for(unsigned y=0;y<64;y++) {
        std::printf("GAUGUIN IMAGE ORACLE row phase=%u plane=%s y=%u data=",phase,plane,y);
        for(unsigned x=0;x<64;x++)std::printf("%08x",words[y*64+x]);
        std::putchar('\n');
    }
}
int main(int argc,char** argv) {
    @autoreleasepool {
        need(argc==3,"usage: oracle library seed");char* end=nullptr;
        unsigned long input=std::strtoul(argv[2],&end,10);
        need(end&&!*end&&input<=UINT32_MAX,"seed bounds");uint32_t seed=uint32_t(input);
        auto d=MTLCreateSystemDefaultDevice();need(d!=nil,"Metal device");NSError* error=nil;
        auto lib=[d newLibraryWithURL:[NSURL fileURLWithPath:[NSString stringWithUTF8String:argv[1]]] error:&error];
        if(!lib)std::fprintf(stderr,"library: %s\n",error.localizedDescription.UTF8String);
        need(lib!=nil,"own shader library");auto q=[d newCommandQueue];need(q!=nil,"queue");
        id<MTLRenderPipelineState> stores[]={pipeline(d,lib,@"image_vertex",@"image_write_fragment",true),
            pipeline(d,lib,@"image_vertex_texture",@"image_write_fragment",true),
            pipeline(d,lib,@"image_buffer_vertex",@"image_write_fragment",false)};
        auto update=pipeline(d,lib,@"image_vertex",@"image_rw_fragment",true);
        auto sample=pipeline(d,lib,@"image_vertex",@"image_sample_fragment",true);
        auto image=texture(d,MTLPixelFormatR32Uint,64,64,MTLTextureUsageShaderRead|MTLTextureUsageShaderWrite);
        auto vertexImage=texture(d,MTLPixelFormatR32Uint,6,1,MTLTextureUsageShaderRead);
        auto scratch=texture(d,MTLPixelFormatRGBA8Unorm,64,64,MTLTextureUsageRenderTarget|MTLTextureUsageShaderRead);
        auto target=texture(d,MTLPixelFormatRGBA8Unorm,64,64,MTLTextureUsageRenderTarget|MTLTextureUsageShaderRead);
        auto attr=[d newBufferWithLength:6*sizeof(Vertex) options:MTLResourceStorageModeShared];
        auto dv=[d newBufferWithLength:6*sizeof(DeviceVertex) options:MTLResourceStorageModeShared];
        auto constant=[d newBufferWithLength:4 options:MTLResourceStorageModeShared];
        auto xorConstant=[d newBufferWithLength:4 options:MTLResourceStorageModeShared];
        need(attr&&dv&&constant&&xorConstant,"buffers");std::vector<uint32_t> poison(4096,0xa5a5a5a5);
        [image replaceRegion:MTLRegionMake2D(0,0,64,64) mipmapLevel:0 withBytes:poison.data() bytesPerRow:256];
        std::printf("GAUGUIN IMAGE ORACLE begin seed=%u jobs=9 draws=27 scope=macos-public-Metal\n",seed);
        for(unsigned phase=0;phase<9;phase++) {
            unsigned mode=phase%3,bits=(seed^(phase*5u))&7u;
            uint32_t value=seed^(phase*0x9e3779b9u),xorValue=0x5a17c3e9u^(phase*0x01010101u);
            std::array<Vertex,6> a{};std::array<DeviceVertex,6> v{};std::array<uint32_t,6> vi{};
            uint32_t mask=mode==2?1u:0u;
            for(unsigned i=0;i<6;i++) {
                a[i].xy[0]=positions[i][0];a[i].xy[1]=positions[i][1];
                for(unsigned c=0;c<3;c++)a[i].color[c]=bits&(1u<<c)?1:0;
                a[i].color[3]=1;v[i].position[0]=a[i].xy[0];v[i].position[1]=a[i].xy[1];
                v[i].position[3]=1;v[i].color[0]=float(mask);vi[i]=bits^mask;
            }
            std::memcpy(attr.contents,a.data(),sizeof(a));std::memcpy(dv.contents,v.data(),sizeof(v));
            std::memcpy(constant.contents,&value,4);std::memcpy(xorConstant.contents,&xorValue,4);
            [vertexImage replaceRegion:MTLRegionMake2D(0,0,6,1) mipmapLevel:0 withBytes:vi.data() bytesPerRow:24];
            auto cb=[q commandBuffer];need(cb!=nil,"command buffer");
            MTLViewport viewport={0,0,64,64,0,1};
            MTLScissorRect scissor=phase&1?MTLScissorRect{8,8,40,32}:MTLScissorRect{0,0,64,64};
            for(unsigned draw=0;draw<3;draw++) {
                auto pass=[MTLRenderPassDescriptor renderPassDescriptor];auto c=pass.colorAttachments[0];
                c.texture=draw==2?target:scratch;c.storeAction=MTLStoreActionStore;
                c.loadAction=draw==0?MTLLoadActionClear:(draw==1?MTLLoadActionLoad:MTLLoadActionDontCare);
                c.clearColor=MTLClearColorMake(0,0,1,1);
                auto e=[cb renderCommandEncoderWithDescriptor:pass];need(e!=nil,"render encoder");
                [e setRenderPipelineState:draw==0?stores[mode]:(draw==1?update:sample)];
                [e setViewport:viewport];[e setScissorRect:draw==2?MTLScissorRect{0,0,64,64}:scissor];
                [e setVertexBuffer:draw==0&&mode==2?dv:attr offset:0 atIndex:0];
                if(draw==0&&mode)[e setVertexTexture:vertexImage atIndex:0];
                [e setFragmentTexture:image atIndex:draw==2?0:3];
                if(draw!=2)[e setFragmentBuffer:draw==0?constant:xorConstant offset:0 atIndex:0];
                [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:6];[e endEncoding];
            }
            [cb commit];[cb waitUntilCompleted];
            if(cb.status!=MTLCommandBufferStatusCompleted)std::fprintf(stderr,"command: %s\n",cb.error.localizedDescription.UTF8String);
            need(cb.status==MTLCommandBufferStatusCompleted,"command completion");
            dump(image,phase,"image");dump(target,phase,"sample");dump(scratch,phase,"coverage");
            std::printf("GAUGUIN IMAGE ORACLE phase=%u completed=1\n",phase);
        }
        std::printf("GAUGUIN IMAGE ORACLE RESULT COMPLETE seed=%u jobs=9 draws=27 raw_pixels=110592\n",seed);
    }
    return 0;
}
