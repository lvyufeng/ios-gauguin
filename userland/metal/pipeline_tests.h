/* Public Metal API test cases on this project's generated shaders. MIT.
 * Included after the finite probe's texture/finish/readback helpers. */
static NSData *shader_library_data(void)
{
    const char *path="/usr/local/lib/gauguin/pipeline_fixture.metallib";
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);struct stat st;
    check(fd>=0 && fstat(fd,&st)==0 && S_ISREG(st.st_mode) && st.st_uid==0 && st.st_gid==0 &&
          (st.st_mode&07777)==0644 && st.st_nlink==1 && st.st_size==GAUGUIN_METAL_SHADER_BYTES,
          "shader-library","trusted bounded library metadata");
    check(GAUGUIN_METAL_SHADER_BYTES>88 && GAUGUIN_METAL_SHADER_BYTES<1048576,"shader-library","library size");
    unsigned char *bytes=malloc(GAUGUIN_METAL_SHADER_BYTES),digest[CC_SHA256_DIGEST_LENGTH];
    check(bytes!=NULL,"shader-library","allocation");size_t at=0;
    while (at<GAUGUIN_METAL_SHADER_BYTES) {
        ssize_t n=read(fd,bytes+at,GAUGUIN_METAL_SHADER_BYTES-at);
        if (n<0 && errno==EINTR) continue;
        check(n>0,"shader-library","complete read");at+=(size_t)n;
    }
    unsigned char extra;check(read(fd,&extra,1)==0 && close(fd)==0,"shader-library","exact library length");
    check(CC_SHA256(bytes,GAUGUIN_METAL_SHADER_BYTES,digest)!=NULL,"shader-library","SHA256");
    char hex[65];for(unsigned i=0;i<32;i++)snprintf(hex+2*i,3,"%02x",digest[i]);
    check(!strcmp(hex,GAUGUIN_METAL_SHADER_SHA256),"shader-library","pinned library identity");
    receipt("library bytes=%u sha256=%s\n",(unsigned)GAUGUIN_METAL_SHADER_BYTES,hex);
    return [[[NSData alloc] initWithBytesNoCopy:bytes length:GAUGUIN_METAL_SHADER_BYTES freeWhenDone:YES] autorelease];
}

struct shader_vertex { float x,y;uint8_t color[4]; };
_Static_assert(sizeof(struct shader_vertex)==12,"vertex stride");
static const struct shader_vertex shader_triangle[3]={
    {-1,1,{255,0,0,255}},{1,1,{255,0,0,255}},{-1,-.96875f,{255,0,0,255}}};
static const struct shader_vertex shader_quad[6]={
    {-1,1,{0,0,0,255}},{1,1,{255,0,0,255}},{-1,-1,{0,255,0,255}},
    {1,1,{255,0,0,255}},{1,-1,{255,255,0,255}},{-1,-1,{0,255,0,255}}};

static id<MTLRenderPipelineState> shader_render_pipeline(id<MTLDevice> device,id<MTLFunction> vertex,
                                                       id<MTLFunction> fragment,MTLPixelFormat format,unsigned blend)
{
    MTLRenderPipelineDescriptor *d=[[[MTLRenderPipelineDescriptor alloc] init] autorelease];
    d.vertexFunction=vertex;d.fragmentFunction=fragment;d.colorAttachments[0].pixelFormat=format;
    MTLVertexDescriptor *v=[MTLVertexDescriptor vertexDescriptor];
    v.attributes[0].format=MTLVertexFormatFloat2;v.attributes[0].offset=0;v.attributes[0].bufferIndex=0;
    v.attributes[1].format=MTLVertexFormatUChar4Normalized;v.attributes[1].offset=8;v.attributes[1].bufferIndex=0;
    v.layouts[0].stride=12;v.layouts[0].stepFunction=MTLVertexStepFunctionPerVertex;v.layouts[0].stepRate=1;
    d.vertexDescriptor=v;
    if (blend) {
        MTLRenderPipelineColorAttachmentDescriptor *a=d.colorAttachments[0];
        a.blendingEnabled=YES;a.rgbBlendOperation=a.alphaBlendOperation=MTLBlendOperationAdd;
        a.sourceRGBBlendFactor=a.sourceAlphaBlendFactor=MTLBlendFactorOne;
        a.destinationRGBBlendFactor=a.destinationAlphaBlendFactor=blend==1?MTLBlendFactorOne:MTLBlendFactorOneMinusSourceAlpha;
    }
    NSError *error=nil;id<MTLRenderPipelineState> p=[device newRenderPipelineStateWithDescriptor:d error:&error];
    check(p!=nil,"render-pipeline",[[error description] UTF8String]);return p;
}
static void shader_draw(id<MTLCommandQueue> queue,id<MTLRenderPipelineState> pipeline,id<MTLTexture> target,
                        id<MTLBuffer> vertices,unsigned count,id<MTLBuffer> uniform,id<MTLTexture> source,
                        id<MTLSamplerState> sampler,MTLClearColor background,const char *phase)
{
    MTLRenderPassDescriptor *pass=[MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture=target;pass.colorAttachments[0].loadAction=MTLLoadActionClear;
    pass.colorAttachments[0].storeAction=MTLStoreActionStore;pass.colorAttachments[0].clearColor=background;
    id<MTLCommandBuffer> cb=[queue commandBuffer];id<MTLRenderCommandEncoder> encoder=[cb renderCommandEncoderWithDescriptor:pass];
    check(encoder!=nil,phase,"render encoder");[encoder setRenderPipelineState:pipeline];
    [encoder setVertexBuffer:vertices offset:0 atIndex:0];
    if (uniform) [encoder setFragmentBuffer:uniform offset:0 atIndex:0];
    if (source) [encoder setFragmentTexture:source atIndex:0];
    if (sampler) [encoder setFragmentSamplerState:sampler atIndex:0];
    [encoder drawPrimitives:MTLPrimitiveTypeTriangle vertexStart:0 vertexCount:count];[encoder endEncoding];finish(cb,phase);
}
static uint32_t shader_binary_color(uint32_t bits)
{
    return 0xff000000|((bits&1)?255:0)|((bits&2)?0xff00:0)|((bits&4)?0xff0000:0);
}
static void shader_pipelines(id<MTLDevice> device,id<MTLCommandQueue> queue,uint32_t seed)
{
    NSError *error=nil;NSData *bytes=shader_library_data();
    dispatch_data_t data=dispatch_data_create(bytes.bytes,bytes.length,NULL,DISPATCH_DATA_DESTRUCTOR_DEFAULT);
    check(data!=NULL,"shader-library","dispatch data");
    id<MTLLibrary> library=[device newLibraryWithData:data error:&error];dispatch_release(data);
    check(library!=nil,"shader-library",[[error description] UTF8String]);
    id<MTLFunction> cs=[library newFunctionWithName:@"gauguin_fill"],vs=[library newFunctionWithName:@"gauguin_vertex"];
    id<MTLFunction> fs=[library newFunctionWithName:@"gauguin_fragment"],uf=[library newFunctionWithName:@"gauguin_uniform_fragment"];
    id<MTLFunction> tf=[library newFunctionWithName:@"gauguin_texture_fragment"];
    check(cs && vs && fs && uf && tf,"shader-library","five public functions");
    id<MTLComputePipelineState> compute=[device newComputePipelineStateWithFunction:cs error:&error];
    check(compute!=nil,"compute-pipeline",[[error description] UTF8String]);memory("shader-compute-compiled");
    receipt("pipelines functions=5 compute=1\n");
    id<MTLBuffer> output=[device newBufferWithLength:1024 options:MTLResourceStorageModeShared];
    id<MTLBuffer> constant=[device newBufferWithLength:16 options:MTLResourceStorageModeShared];
    check(output && constant && output.contents && constant.contents,"shader-buffers","shared buffers");
    for (unsigned p=0;p<2;p++) @autoreleasepool {
        uint32_t current=seed^(p?0xa5a5f00du:0);memcpy(constant.contents,&current,4);memset(output.contents,0xa5,1024);
        id<MTLCommandBuffer> cb=[queue commandBuffer];id<MTLComputeCommandEncoder> encoder=[cb computeCommandEncoder];
        check(encoder!=nil,"compute","encoder");[encoder setComputePipelineState:compute];
        [encoder setBuffer:output offset:0 atIndex:0];[encoder setBuffer:constant offset:0 atIndex:1];
        [encoder dispatchThreadgroups:MTLSizeMake(4,1,1) threadsPerThreadgroup:MTLSizeMake(64,1,1)];[encoder endEncoding];
        const char *phase=p?"compute-B":"compute-A";finish(cb,phase);
        uint32_t *got=output.contents;uint64_t hash=14695981039346656037ULL;
        for (uint32_t i=0;i<256;i++) {
            check(got[i]==i*0x9e3779b1u+current,phase,"gid multiplication and seeded readback");
            for(unsigned b=0;b<4;b++)hash=(hash^(uint8_t)(got[i]>>(8*b)))*1099511628211ULL;
        }
        receipt("values phase=%s words=256 hash=%016llx PASS\n",phase,(unsigned long long)hash);
    }
    id<MTLBuffer> triangle=[device newBufferWithBytes:shader_triangle length:sizeof(shader_triangle) options:MTLResourceStorageModeShared];
    id<MTLBuffer> quad=[device newBufferWithBytes:shader_quad length:sizeof(shader_quad) options:MTLResourceStorageModeShared];
    check(triangle && quad,"shader-vertices","vertex buffer allocations");
    const MTLPixelFormat formats[]={MTLPixelFormatRGBA8Unorm,MTLPixelFormatBGRA8Unorm};
    for (unsigned f=0;f<2;f++) @autoreleasepool {
        id<MTLTexture> target=texture(device,formats[f]);id<MTLRenderPipelineState> pipeline=shader_render_pipeline(device,vs,fs,formats[f],0);
        const char *phase=f?"triangle-BGRA":"triangle-RGBA";
        shader_draw(queue,pipeline,target,triangle,3,nil,nil,nil,MTLClearColorMake(0,0,1,1),phase);
        uint32_t want[WORDS];for(unsigned i=0;i<WORDS;i++) {
            unsigned x=i%WIDTH,y=i/WIDTH;bool inside=63u*(2*x+1)+64u*(2*y+1)<8064u;
            want[i]=inside?(f?0xffff0000:0xff0000ff):(f?0xff0000ff:0xffff0000);
        }
        verify_texture(target,want,phase);[pipeline release];[target release];
    }
    id<MTLTexture> target=texture(device,MTLPixelFormatRGBA8Unorm),source=texture(device,MTLPixelFormatRGBA8Unorm);
    MTLSamplerDescriptor *sd=[[[MTLSamplerDescriptor alloc] init] autorelease];
    sd.minFilter=sd.magFilter=MTLSamplerMinMagFilterNearest;sd.mipFilter=MTLSamplerMipFilterNotMipmapped;sd.normalizedCoordinates=YES;
    sd.sAddressMode=sd.tAddressMode=MTLSamplerAddressModeClampToEdge;
    id<MTLSamplerState> sampler=[device newSamplerStateWithDescriptor:sd];check(sampler!=nil,"sampler","nearest clamp sampler");
    id<MTLRenderPipelineState> textured=shader_render_pipeline(device,vs,tf,MTLPixelFormatRGBA8Unorm,0);
    for(unsigned p=0;p<2;p++) @autoreleasepool {
        uint32_t current=seed^(p?8:0),want[WORDS];
        for(unsigned i=0;i<WORDS;i++) {unsigned x=i%WIDTH,y=i/WIDTH;want[i]=shader_binary_color((current&7)^(((x/8+y/8+(current>>3))&1)?7:0));}
        [source replaceRegion:MTLRegionMake2D(0,0,WIDTH,HEIGHT) mipmapLevel:0 withBytes:want bytesPerRow:STRIDE];
        const char *phase=p?"textured-B":"textured-A";
        shader_draw(queue,textured,target,quad,6,nil,source,sampler,MTLClearColorMake(0,0,0,0),phase);verify_texture(target,want,phase);
    }
    id<MTLRenderPipelineState> additive=shader_render_pipeline(device,vs,uf,MTLPixelFormatRGBA8Unorm,1);
    float color[4]={1,0,0,0};memcpy(constant.contents,color,sizeof(color));
    shader_draw(queue,additive,target,quad,6,constant,nil,nil,MTLClearColorMake(0,1,0,1),"additive-RGBA");
    uint32_t want[WORDS];for(unsigned i=0;i<WORDS;i++)want[i]=0xff00ffff;verify_texture(target,want,"additive-RGBA");
    id<MTLTexture> half=texture(device,MTLPixelFormatRGBA16Float);
    id<MTLRenderPipelineState> premul=shader_render_pipeline(device,vs,uf,MTLPixelFormatRGBA16Float,2);
    color[0]=color[3]=.5f;memcpy(constant.contents,color,sizeof(color));
    shader_draw(queue,premul,half,quad,6,constant,nil,nil,MTLClearColorMake(0,1,0,1),"premul-half");
    uint64_t half_values[WORDS];memset(half_values,0xa5,sizeof(half_values));
    [half getBytes:half_values bytesPerRow:WIDTH*8 fromRegion:MTLRegionMake2D(0,0,WIDTH,HEIGHT) mipmapLevel:0];
    uint64_t hash=14695981039346656037ULL;
    for(unsigned i=0;i<WORDS;i++) {
        check(half_values[i]==UINT64_C(0x3c00000038003800),"premul-half","exact RGBA16F premultiplied blending");
        for(unsigned b=0;b<8;b++)hash=(hash^(uint8_t)(half_values[i]>>(8*b)))*1099511628211ULL;
    }
    receipt("half_pixels phase=premul-half pixels=4096 hash=%016llx PASS\n",(unsigned long long)hash);
    const MTLPixelFormat srgb[]={MTLPixelFormatRGBA8Unorm_sRGB,MTLPixelFormatBGRA8Unorm_sRGB};
    for(unsigned f=0;f<2;f++) @autoreleasepool {
        id<MTLTexture> image=texture(device,srgb[f]);id<MTLRenderPipelineState> pipeline=shader_render_pipeline(device,vs,uf,srgb[f],0);
        color[0]=color[1]=color[2]=.5f;color[3]=1;memcpy(constant.contents,color,sizeof(color));
        const char *phase=f?"gamma-BGRA":"gamma-RGBA";
        shader_draw(queue,pipeline,image,quad,6,constant,nil,nil,MTLClearColorMake(0,0,0,0),phase);
        for(unsigned i=0;i<WORDS;i++)want[i]=0xffbcbcbc;verify_texture(image,want,phase);[pipeline release];[image release];
    }
    memory("shader-render-completed");receipt("pipelines render_states=7 render_jobs=8 jobs=10 pixel_checks=32768 compute_words=512 PASS\n");
    [premul release];[half release];[additive release];[textured release];[sampler release];[source release];[target release];
    [quad release];[triangle release];[constant release];[output release];[compute release];
    [tf release];[uf release];[fs release];[vs release];[cs release];[library release];
}
