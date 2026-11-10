/* SPDX-License-Identifier: MIT
 * Root-only real task memory, prepared immutable before IOSurfaceCreate.
 * This suite never requests a shadow copy or publishes an MTLDevice. */
#include <sys/mman.h>
#include "task_surface_permissions.h"

static uint64_t task_hash(const void *data, size_t size)
{
    const uint8_t *p=data;uint64_t h=UINT64_C(14695981039346656037);
    for(size_t i=0;i<size;i++)h=(h^p[i])*UINT64_C(1099511628211);
    return h;
}
static void *task_project_pointer(id object, const char *class_name, const char *selector, const char *encoding)
{
    check(!strcmp(class_getName(object_getClass(object)),class_name),"task-ABI","project object class");
    SEL sel=sel_registerName(selector);Method m=class_getInstanceMethod(object_getClass(object),sel);
    check(m && method_getNumberOfArguments(m)==2,"task-ABI","project getter selector");
    char *type=method_copyReturnType(m);bool valid=type && !strcmp(type,encoding);free(type);
    check(valid,"task-ABI","project getter return encoding");
    void *p=((void *(*)(id,SEL))objc_msgSend)(object,sel);
    check(p!=NULL,"task-ABI","project core handle");return p;
}
static id<MTLLibrary> task_library(id<MTLDevice> device)
{
    const char *path="/usr/local/lib/gauguin/pipeline_fixture.metallib";
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);struct stat st;
    check(fd>=0 && fstat(fd,&st)==0 && S_ISREG(st.st_mode) && st.st_uid==0 && st.st_gid==0 &&
          (st.st_mode&07777)==0644 && st.st_nlink==1 && st.st_size==GAUGUIN_TASK_SHADER_BYTES,
          "task-library","exact root-owned own library");
    uint8_t *bytes=malloc(GAUGUIN_TASK_SHADER_BYTES);check(bytes!=NULL,"task-library","allocation");
    size_t at=0;
    while(at<GAUGUIN_TASK_SHADER_BYTES) {
        ssize_t n=read(fd,bytes+at,GAUGUIN_TASK_SHADER_BYTES-at);
        if(n<0 && errno==EINTR)continue;check(n>0,"task-library","bounded read");at+=(size_t)n;
    }
    unsigned char extra,digest[32];check(read(fd,&extra,1)==0 && close(fd)==0,"task-library","exact bytes");
    check(CC_SHA256(bytes,GAUGUIN_TASK_SHADER_BYTES,digest)!=NULL,"task-library","hash");
    char hex[65];for(unsigned i=0;i<32;i++)snprintf(hex+2*i,3,"%02x",digest[i]);
    check(!strcmp(hex,GAUGUIN_TASK_SHADER_SHA256),"task-library","pinned identity");
    dispatch_data_t data=dispatch_data_create(bytes,GAUGUIN_TASK_SHADER_BYTES,NULL,^{ free(bytes); });
    check(data!=NULL,"task-library","dispatch data");NSError *error=nil;
    id<MTLLibrary> library=[device newLibraryWithData:data error:&error];dispatch_release(data);
    check(library!=nil,"task-library",[[error description] UTF8String]);return library;
}
static unsigned task_bits(uint32_t seed,unsigned x,unsigned y,unsigned index)
{
    return (seed^(x*13u)^(y*7u)^(index*5u))&15;
}
struct task_vertex { float x,y;uint8_t uv[4]; };
_Static_assert(sizeof(struct task_vertex)==12,"task vertex stride");
static void task_surface_scenes(id<MTLDevice> device,id<MTLCommandQueue> queue,uint32_t seed)
{
    static const struct {const char *name;MTLPixelFormat format;uint32_t fourcc,bpe,bias;} cases[]={
        {"R8",MTLPixelFormatR8Unorm,0x4c303038,1,64},
        {"RG8",MTLPixelFormatRG8Unorm,0x4c413038,2,4032},
        {"BGRA8",MTLPixelFormatBGRA8Unorm,0x42475241,4,16448},
        {"RGBA16F",MTLPixelFormatRGBA16Float,0x52476841,8,0},
        {"RGBA32F",MTLPixelFormatRGBA32Float,0x52476641,16,8192}};
    static const struct task_vertex quad[]={
        {-1,1,{0,0,0,255}},{1,1,{255,0,0,255}},{-1,-1,{0,255,0,255}},
        {1,1,{255,0,0,255}},{1,-1,{255,255,0,255}},{-1,-1,{0,255,0,255}}};
    hakios_metal_device *core=task_project_pointer(device,"HakiosMetalDevice","hakiosDevice",@encode(hakios_metal_device*));
    id<MTLLibrary> library=task_library(device);
    id<MTLFunction> vs=[library newFunctionWithName:@"gauguin_vertex"],fs=[library newFunctionWithName:@"gauguin_texture_fragment"];
    check(vs && fs,"task-pipeline","own sampler functions");
    MTLRenderPipelineDescriptor *pd=[[[MTLRenderPipelineDescriptor alloc] init] autorelease];
    pd.vertexFunction=vs;pd.fragmentFunction=fs;pd.colorAttachments[0].pixelFormat=MTLPixelFormatRGBA8Unorm;
    MTLVertexDescriptor *vd=[MTLVertexDescriptor vertexDescriptor];
    vd.attributes[0].format=MTLVertexFormatFloat2;vd.attributes[0].offset=0;vd.attributes[0].bufferIndex=0;
    vd.attributes[1].format=MTLVertexFormatUChar4Normalized;vd.attributes[1].offset=8;vd.attributes[1].bufferIndex=0;
    vd.layouts[0].stride=12;vd.layouts[0].stepFunction=MTLVertexStepFunctionPerVertex;vd.layouts[0].stepRate=1;pd.vertexDescriptor=vd;
    NSError *error=nil;id<MTLRenderPipelineState> pipeline=[device newRenderPipelineStateWithDescriptor:pd error:&error];
    check(pipeline!=nil,"task-pipeline",[[error description] UTF8String]);
    id<MTLBuffer> vertices=[device newBufferWithBytes:quad length:sizeof(quad) options:MTLResourceStorageModeShared];
    MTLSamplerDescriptor *sd=[[[MTLSamplerDescriptor alloc] init] autorelease];
    sd.minFilter=sd.magFilter=MTLSamplerMinMagFilterNearest;sd.mipFilter=MTLSamplerMipFilterNotMipmapped;
    sd.normalizedCoordinates=YES;sd.sAddressMode=sd.tAddressMode=MTLSamplerAddressModeClampToEdge;
    id<MTLSamplerState> sampler=[device newSamplerStateWithDescriptor:sd];
    check(vertices && sampler,"task-pipeline","vertices and sampler");
    printf("GAUGUIN SURFACE237 begin build=%s seed=%u cases=5\n",GAUGUIN_METAL_FRONTEND_BUILD,seed);
    for(unsigned index=0;index<5;index++) @autoreleasepool {
        const unsigned bpe=cases[index].bpe,bias=cases[index].bias,pitch=WIDTH*bpe+64;
        const size_t size=pitch*HEIGHT+13,map_size=(bias+size+128+vm_page_size-1)&~((size_t)vm_page_size-1);
        uint8_t *mapping=mmap(NULL,map_size,PROT_READ|PROT_WRITE,MAP_ANON|MAP_PRIVATE,-1,0);
        check(mapping!=MAP_FAILED,"task-memory","fresh anonymous VM");
        for(size_t i=0;i<map_size;i++)mapping[i]=(uint8_t)(seed+(i*29u)+(index*17u));
        uint8_t *pixels=mapping+bias;uint32_t want[WORDS];
        for(unsigned y=0;y<HEIGHT;y++)for(unsigned x=0;x<WIDTH;x++) {
            const unsigned bits=task_bits(seed,x,y,index);uint8_t channels[4]={0,0,0,255};
            for(unsigned c=0;c<(bpe==1?1:bpe==2?2:4);c++)channels[c]=(bits&(1u<<c))?255:0;
            uint8_t *p=pixels+y*pitch+x*bpe;
            if(bpe<=2)memcpy(p,channels,bpe);
            else if(bpe==4) {p[0]=channels[2];p[1]=channels[1];p[2]=channels[0];p[3]=channels[3];}
            else if(bpe==8) {uint16_t v[4];for(unsigned c=0;c<4;c++)v[c]=channels[c]?0x3c00:0;memcpy(p,v,8);}
            else {float v[4];for(unsigned c=0;c<4;c++)v[c]=channels[c]?1:0;memcpy(p,v,16);}
            want[y*WIDTH+x]=channels[0]|((uint32_t)channels[1]<<8)|((uint32_t)channels[2]<<16)|((uint32_t)channels[3]<<24);
        }
        uint8_t *snapshot=malloc(size);check(snapshot!=NULL,"task-memory","source snapshot");memcpy(snapshot,pixels,size);
        const uint64_t before=task_hash(pixels,size),full_before=task_hash(mapping,map_size);
        check(mprotect(mapping,map_size,PROT_READ)==0,"task-memory","immutable VM before prepare");
        NSDictionary *properties=@{@"IOSurfaceAddress":@((uint64_t)(uintptr_t)pixels),
            (id)kIOSurfaceWidth:@(WIDTH),(id)kIOSurfaceHeight:@(HEIGHT),(id)kIOSurfaceBytesPerElement:@(bpe),
            (id)kIOSurfaceBytesPerRow:@(pitch),(id)kIOSurfaceAllocSize:@(size),(id)kIOSurfacePixelFormat:@(cases[index].fourcc)};
        IOSurfaceRef surface=IOSurfaceCreate((CFDictionaryRef)properties);
        check(surface && IOSurfaceGetAllocSize(surface)==size && IOSurfaceGetBytesPerRow(surface)==pitch &&
              IOSurfaceGetWidth(surface)==WIDTH && IOSurfaceGetHeight(surface)==HEIGHT,
              "task-surface","exact task-backed layout");
        const uint32_t surface_id=IOSurfaceGetID(surface);check(surface_id!=0,"task-surface","surface ID");
        MTLTextureDescriptor *td=[MTLTextureDescriptor texture2DDescriptorWithPixelFormat:cases[index].format width:WIDTH height:HEIGHT mipmapped:NO];
        td.storageMode=MTLStorageModeShared;td.usage=MTLTextureUsageShaderRead;
        id<MTLTexture> source=[device newTextureWithDescriptor:td iosurface:surface plane:0];
        check(source && source.iosurface==surface && source.iosurfacePlane==0 && source.device==device,"task-surface","same IOSurface and owner");
        SEL shadow=sel_registerName("hakiosIsShadow");Method sm=class_getInstanceMethod(object_getClass(source),shadow);
        check(sm && !strcmp(method_getTypeEncoding(sm),"B16@0:8") &&
              !((BOOL(*)(id,SEL))objc_msgSend)(source,shadow),"task-surface","direct import; shadow copy forbidden");
        hakios_metal_texture *native=task_project_pointer(source,"HakiosMetalTexture","hakiosTexture",@encode(hakios_metal_texture*));
        struct gauguin_surface_permissions permissions;
        bool permitted=gauguin_task_surface_permissions(core,native,surface_id,size,bias&4095,&permissions);
        printf("GAUGUIN SURFACE237 permissions case=%s handle=%u gpu_bias=%llu bytes=%llu flags=%llu cpu_write=%d gpu_write=%d fence=%u close=%d uncertain=%u phase=%s\n",
               cases[index].name,permissions.handle,(unsigned long long)(permissions.gpu_address&4095),
               (unsigned long long)permissions.bytes,(unsigned long long)permissions.flags,permissions.cpu_write_errno,
               permissions.gpu_write_errno,permissions.fence,permissions.close_errno,permissions.uncertain_dma,permissions.phase);
        check(permitted,"task-permissions",permissions.phase);
        const bool early=index>=3;
        if(early) {
            CFRelease(surface);surface=NULL;
            check(munmap(mapping,map_size)==0,"task-lifetime","drop original task VA before submit");mapping=NULL;
        }
        printf("GAUGUIN SURFACE237 case name=%s index=%u id=%u bpe=%u bias=%u pitch=%u bytes=%zu early=%u\n",
               cases[index].name,index,surface_id,bpe,bias,pitch,size,early);
        id<MTLTexture> target=texture(device,MTLPixelFormatRGBA8Unorm);
        MTLRenderPassDescriptor *pass=[MTLRenderPassDescriptor renderPassDescriptor];
        pass.colorAttachments[0].texture=target;pass.colorAttachments[0].loadAction=MTLLoadActionClear;
        pass.colorAttachments[0].storeAction=MTLStoreActionStore;pass.colorAttachments[0].clearColor=MTLClearColorMake(.25,.5,.75,.5);
        id<MTLCommandBuffer> cb=[queue commandBuffer];id<MTLRenderCommandEncoder> e=[cb renderCommandEncoderWithDescriptor:pass];
        check(e!=nil,"task-draw","encoder");[e setRenderPipelineState:pipeline];[e setVertexBuffer:vertices offset:0 atIndex:0];
        [e setFragmentTexture:source atIndex:0];[e setFragmentSamplerState:sampler atIndex:0];
        [e drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:6];[e endEncoding];finish(cb,"task-sample");
        uint32_t got[WORDS];memset(got,0xa5,sizeof(got));
        [target getBytes:got bytesPerRow:STRIDE fromRegion:MTLRegionMake2D(0,0,WIDTH,HEIGHT) mipmapLevel:0];
        check(!memcmp(got,want,sizeof(got)),"task-pixels",cases[index].name);
        for(unsigned y=0;y<HEIGHT;y++) {
            printf("GAUGUIN SURFACE237 row case=%s y=%u rgba=",cases[index].name,y);
            for(unsigned x=0;x<STRIDE;x++)printf("%02x",((uint8_t*)got)[y*STRIDE+x]);putchar('\n');
        }
        IOSurfaceRef held=source.iosurface;check(held && IOSurfaceGetID(held)==surface_id,"task-lifetime","texture retained surface");
        check(IOSurfaceLock(held,kIOSurfaceLockReadOnly,NULL)==KERN_SUCCESS,"task-source","read lock after fence");
        const void *after_pixels=IOSurfaceGetBaseAddress(held);
        check(after_pixels && !memcmp(after_pixels,snapshot,size),"task-source","all source/padding/tail bytes unchanged");
        const uint64_t after=task_hash(after_pixels,size);
        check(IOSurfaceUnlock(held,kIOSurfaceLockReadOnly,NULL)==KERN_SUCCESS,"task-source","read unlock");
        if(mapping)check(task_hash(mapping,map_size)==full_before,"task-source","original VM and exterior guards unchanged");
        printf("GAUGUIN SURFACE237 pixels case=%s pixels=4096 hash=%016llx source_before=%016llx source_after=%016llx early=%u full_guard=%u PASS\n",
               cases[index].name,(unsigned long long)task_hash(got,sizeof(got)),(unsigned long long)before,
               (unsigned long long)after,early,!early);
        [target release];[source release];if(surface)CFRelease(surface);
        if(mapping)check(munmap(mapping,map_size)==0,"task-lifetime","VM release after resources");free(snapshot);
    }
    [sampler release];[vertices release];[pipeline release];[fs release];[vs release];[library release];
    memory("task-surfaces-completed");
    printf("GAUGUIN SURFACE237 end cases=5 pixels=20480 jobs=5 direct=1 immutable=1 PASS\n");
}
