// SPDX-License-Identifier: MIT
// Finite root probe of A619 graphics images. No device publication or UI hooks.
#include <TargetConditionals.h>
#include <mach/mach.h>
#include <sys/sysctl.h>
#include <array>
#include <atomic>
#include <cerrno>
#include <csignal>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <time.h>
#include <unistd.h>
#include <vector>
#include "hakios-metal/compiler.hpp"
#include "hakios-metal/command.hpp"
#include "hakios-metal/metallib.hpp"
#include "GauguinMetalProfile.h"
#include "graphics_images_bytes.h"

#if !TARGET_OS_IPHONE || !defined(HAKIOS_METAL_TARGET_A619)
#error This probe requires the native iOS A619 target
#endif
#if !defined(GAUGUIN_IMAGE_PROBE_BUILD) || !defined(GAUGUIN_IMAGE_CORE_SHA256)
#error Explicit build and graphics-image core identities are required
#endif

using namespace hakios::metal;
constexpr uint32_t kWidth=64,kHeight=64,kPixels=kWidth*kHeight,kJobs=9;
extern "C" int memorystatus_control(uint32_t,int32_t,uint32_t,void*,size_t);
struct MemLimit { int32_t active;uint32_t activeAttr;int32_t inactive;uint32_t inactiveAttr; };
static_assert(sizeof(MemLimit)==16);
static std::atomic<bool> connectionClosed{false};

[[noreturn]] static void fail(const char* stage,const std::string& why) {
    std::fprintf(stderr,"GAUGUIN IMAGE232 FAIL stage=%s why=%.320s\n",stage,why.c_str());
    std::fflush(nullptr);std::_Exit(1); // Failed in-flight work remains the kernel client's responsibility.
}
static void need(bool ok,const char* stage,const std::string& why) { if(!ok)fail(stage,why); }
static uint64_t clockNs() {
    timespec t{};need(!clock_gettime(CLOCK_MONOTONIC_RAW,&t),"clock","monotonic read");
    need(t.tv_sec>=0&&t.tv_nsec>=0&&t.tv_nsec<1000000000,"clock","invalid clock");
    return uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);
}
static void expired(int) { std::_Exit(124); }
static void memory(const char* phase) {
    MemLimit m{};task_vm_info_data_t vm{};mach_msg_type_number_t count=TASK_VM_INFO_REV1_COUNT;
    need(!memorystatus_control(8,getpid(),0,&m,sizeof(m)),"memory","GET8");
    need(task_info(mach_task_self(),TASK_VM_INFO,reinterpret_cast<task_info_t>(&vm),&count)==KERN_SUCCESS&&count>=TASK_VM_INFO_REV1_COUNT,"memory","footprint");
    std::printf("GAUGUIN IMAGE232 memory phase=%s active=%d inactive=%d hard=%u/%u footprint=%llu\n",phase,m.active,m.inactive,m.activeAttr,m.inactiveAttr,(unsigned long long)vm.phys_footprint);
    need(m.active==128&&m.inactive==128&&m.activeAttr==1&&m.inactiveAttr==1&&vm.phys_footprint&&vm.phys_footprint<=128ull*1024*1024,"memory","128MiB active/inactive hard limits required");
}

class Audited final:public Transport {
    std::unique_ptr<Transport> inner_;
    std::mutex lock_;
    std::set<std::pair<uint32_t,uint32_t>> submitted_,completed_;
    std::set<uint32_t> writes_;
public:
    explicit Audited(std::unique_ptr<Transport> t):inner_(std::move(t)) {}
    ~Audited() override {inner_.reset();connectionClosed.store(true);}
    void requireWrites(std::set<uint32_t> handles) {writes_=std::move(handles);}
    int call(uint32_t request,void* data,size_t size) override {
        if(request==kGetParam)need(size==sizeof(MsmParam)&&static_cast<MsmParam*>(data)->pipe==0x10,"wire","query pipe/layout");
        if(request==kGemSubmit) {
            need(size==sizeof(MsmGemSubmit),"wire","submit layout");auto* s=static_cast<MsmGemSubmit*>(data);
            need((s->flags&0x1f)==0x10&&s->nr_bos&&s->nr_bos<=1024&&s->bos,"wire","bounded A619 submit");
            auto* bos=reinterpret_cast<const MsmSubmitBo*>(uintptr_t(s->bos));std::set<uint32_t> seen,written;
            for(uint32_t i=0;i<s->nr_bos;i++) {
                need(bos[i].handle&&seen.insert(bos[i].handle).second,"permissions","duplicate BO");
                if(bos[i].flags&kSubmitBoWrite)written.insert(bos[i].handle);
            }
            for(auto h:writes_)need(written.count(h)==1,"permissions","image or render target omitted WRITE flag");
        }
        int rc=inner_->call(request,data,size);
        if(!rc&&request==kGemSubmit) {
            auto* s=static_cast<MsmGemSubmit*>(data);std::lock_guard<std::mutex> guard(lock_);
            need(s->fence&&submitted_.size()<kJobs&&submitted_.insert({s->queueid,s->fence}).second,"fence","invalid/duplicate submit");
        }
        if(!rc&&request==kWaitFence) {
            auto* f=static_cast<MsmWaitFence*>(data);std::lock_guard<std::mutex> guard(lock_);
            need(submitted_.count({f->queueid,f->fence})==1,"fence","wait does not name this client's submission");
            completed_.insert({f->queueid,f->fence});
        }
        return rc;
    }
    void* map(uint32_t h,uint64_t n) override {return inner_->map(h,n);}
    void unmap(uint32_t h,void* p) override {inner_->unmap(h,p);}
    int64_t nowNs() override {return inner_->nowNs();}
    size_t completed() {std::lock_guard<std::mutex> guard(lock_);return completed_.size();}
    void final() {
        std::lock_guard<std::mutex> guard(lock_);
        need(submitted_==completed_&&completed_.size()==kJobs,"fence","all nine submissions must complete");
        for(auto f:completed_)std::printf("GAUGUIN IMAGE232 fence queue=%u value=%u complete=1\n",f.first,f.second);
    }
};

static void cpu(Gpu& gpu,const Buffer& b,uint32_t op) {
    need(!gpu.cpuPrep(b.bo(),op,5000000000ll),"CPU-sync","CPU prep failed");
}
static void upload(Gpu& gpu,const std::shared_ptr<Buffer>& b,const void* p,size_t n) {
    need(b&&b->contents()&&n<=b->length(),"upload","bounds");cpu(gpu,*b,2);
    std::memcpy(b->contents(),p,n);gpu.cpuFini(b->bo());
}
static std::shared_ptr<Texture> texture(Gpu& gpu,PixelFormat f,uint32_t w,uint32_t h,uint32_t usage) {
    TextureDesc d;d.format=f;d.width=w;d.height=h;d.usage=usage;std::string why;
    auto t=Texture::make(gpu,d,&why);need(bool(t),"texture",why);return t;
}
static void replace(Gpu& gpu,const Texture& t,const uint32_t* p,uint32_t w,uint32_t h) {
    std::string why;cpu(gpu,*t.buffer(),2);bool ok=const_cast<Texture&>(t).replace(0,0,w,h,p,w*4,&why);
    gpu.cpuFini(t.buffer()->bo());need(ok,"texture-upload",why);
}
static std::vector<uint32_t> read(Gpu& gpu,const Texture& t) {
    std::vector<uint32_t> out(kPixels);std::string why;cpu(gpu,*t.buffer(),1);
    bool ok=t.read(0,0,kWidth,kHeight,out.data(),kWidth*4,&why);gpu.cpuFini(t.buffer()->bo());need(ok,"readback",why);return out;
}
static uint32_t rgba(uint32_t bits) {return (bits&1?255:0)|(bits&2?0xff00:0)|(bits&4?0xff0000:0)|0xff000000u;}
static uint64_t verify(unsigned phase,const char* plane,const std::vector<uint32_t>& actual,const std::vector<uint32_t>& expected) {
    need(actual.size()==kPixels&&expected.size()==kPixels,"pixels","geometry");uint64_t hash=14695981039346656037ull;size_t bad=kPixels;
    for(uint32_t y=0;y<kHeight;y++) {
        std::printf("GAUGUIN IMAGE232 row phase=%u plane=%s y=%u data=",phase,plane,y);
        for(uint32_t x=0;x<kWidth;x++) {
            uint32_t i=y*kWidth+x,v=actual[i];std::printf("%08x",v);
            if(v!=expected[i]&&bad==kPixels)bad=i;
            for(unsigned c=0;c<4;c++)hash=(hash^uint8_t(v>>(8*c)))*1099511628211ull;
        }
        std::putchar('\n');
    }
    if(bad!=kPixels)fail("pixels",std::string(plane)+" first mismatch at "+std::to_string(bad)+" actual="+std::to_string(actual[bad])+" expected="+std::to_string(expected[bad]));
    std::printf("GAUGUIN IMAGE232 pixels phase=%u plane=%s compared=%u hash=%016llx PASS\n",phase,plane,kPixels,(unsigned long long)hash);return hash;
}

struct Vertex {float x,y;float color[4];};
struct alignas(16) DeviceVertex {float position[4];float color[4];};
static_assert(sizeof(Vertex)==24&&sizeof(DeviceVertex)==32);
static constexpr float positions[6][2]={{-1,1},{1,1},{-1,-1},{1,1},{1,-1},{-1,-1}};
static std::shared_ptr<CompiledStage> stage(MetalLibrary& lib,const char* name,uint32_t base=0) {
    const MetalFunction* selected=nullptr;for(const auto& f:lib.functions())if(f.name==name)selected=&f;
    need(selected!=nullptr,"library",std::string("missing ")+name);const uint8_t* bc=nullptr;uint64_t bytes=0;
    need(lib.bitcode(*selected,&bc,&bytes)&&bc&&bytes,"library","AIR bounds");std::string why;
    auto compiled=compileStage(bc,size_t(bytes),&why,{},base);need(bool(compiled),"compile",why);
    return std::shared_ptr<CompiledStage>(std::move(compiled));
}
static std::shared_ptr<CompiledProgram> pipeline(MetalLibrary& lib,const char* vsName,const char* fsName,bool attributes) {
    auto vs=stage(lib,vsName);auto fs=stage(lib,fsName,vs->stage.k.numIbos);std::string why;
    auto p=linkProgram(vs,fs,PixelFormat::kRGBA8Unorm,&why);need(bool(p),"link",why);
    if(attributes) {
        p->program.vertexDescriptor.attributes[0]=VertexAttribute{VertexFormat::kFloat2,0,0};
        p->program.vertexDescriptor.attributes[1]=VertexAttribute{VertexFormat::kFloat4,8,0};
        p->program.vertexDescriptor.layouts[0]=VertexLayout{sizeof(Vertex),VertexStep::kPerVertex,1};
    }
    return std::shared_ptr<CompiledProgram>(std::move(p));
}

static void run(uint32_t seed) {
    std::string why;auto t=openKernelGpu(&why);need(bool(t),"open",why);
    auto audited=std::make_unique<Audited>(std::move(t));auto* audit=audited.get();Gpu gpu(std::move(audited));
    const uint32_t ids[]={kParamGpuId,kParamChipId,kParamGmemSize,kParamGmemBase};
    const uint64_t wants[]={619,0x06010900,524288,0x100000};
    for(unsigned i=0;i<4;i++){uint64_t value=0;need(!gpu.param(ids[i],&value)&&value==wants[i],"identity","A619 parameter mismatch");}
    const uint64_t faults=gpu.faults();need(hasCompiler(),"compiler","AIR compiler absent");MetalLibrary lib;
    need(lib.parse(kGauguinImageLibrary,sizeof(kGauguinImageLibrary)),"library",lib.why());need(lib.functions().size()==6,"library","six own functions required");
    auto queue=CommandQueue::make(gpu,&why);need(bool(queue),"queue",why);
    const char* vsNames[]={"image_vertex","image_vertex_texture","image_buffer_vertex"};
    std::array<std::shared_ptr<CompiledProgram>,3> stores;
    for(unsigned i=0;i<3;i++)stores[i]=pipeline(lib,vsNames[i],"image_write_fragment",i!=2);
    auto update=pipeline(lib,"image_vertex","image_rw_fragment",true),sample=pipeline(lib,"image_vertex","image_sample_fragment",true);
    need(stores[2]->vs->stage.k.numIbos==1&&stores[2]->program.fsIboBase==1,"layout","VS buffer must reserve FS image base");
    auto image=texture(gpu,PixelFormat::kR32Uint,kWidth,kHeight,kTextureUsageRead|kTextureUsageWrite);
    auto verticesTexture=texture(gpu,PixelFormat::kR32Uint,6,1,kTextureUsageRead);
    auto scratch=texture(gpu,PixelFormat::kRGBA8Unorm,kWidth,kHeight,kTextureUsageRenderTarget|kTextureUsageRead);
    auto target=texture(gpu,PixelFormat::kRGBA8Unorm,kWidth,kHeight,kTextureUsageRenderTarget|kTextureUsageRead);
    audit->requireWrites({image->buffer()->bo().handle(),scratch->buffer()->bo().handle(),target->buffer()->bo().handle()});
    auto attr=newBuffer(gpu,6*sizeof(Vertex),&why),deviceVertices=newBuffer(gpu,6*sizeof(DeviceVertex),&why);
    auto constants=newBuffer(gpu,16384,&why),xorConstants=newBuffer(gpu,16384,&why);need(attr&&deviceVertices&&constants&&xorConstants,"buffers",why);
    std::vector<uint32_t> expected(kPixels,0xa5a5a5a5u);replace(gpu,*image,expected.data(),kWidth,kHeight);
    memory("compiled");render::Options options;options.gmem=false;
    for(unsigned phase=0;phase<kJobs;phase++) {
        const unsigned mode=phase%3,bits=(seed^(phase*5u))&7u;const uint32_t value=seed^(phase*0x9e3779b9u),xorValue=0x5a17c3e9u^(phase*0x01010101u);
        std::array<Vertex,6> a{};std::array<DeviceVertex,6> d{};std::array<uint32_t,6> input{};
        const uint32_t mask=mode==2?1u:0u;
        for(unsigned i=0;i<6;i++) {
            a[i].x=positions[i][0];a[i].y=positions[i][1];
            for(unsigned c=0;c<3;c++)a[i].color[c]=(bits&(1u<<c))?1.0f:0.0f;a[i].color[3]=1;
            d[i].position[0]=a[i].x;d[i].position[1]=a[i].y;d[i].position[3]=1;d[i].color[0]=float(mask);input[i]=bits^mask;
        }
        upload(gpu,attr,a.data(),sizeof(a));upload(gpu,deviceVertices,d.data(),sizeof(d));upload(gpu,constants,&value,4);upload(gpu,xorConstants,&xorValue,4);replace(gpu,*verticesTexture,input.data(),6,1);
        Bindings vb;vb.buffers={{mode==2?deviceVertices.get():attr.get(),0}};if(mode)vb.textures={verticesTexture.get()};
        Bindings plain;plain.buffers={{attr.get(),0}};Bindings fs;fs.buffers={{constants.get(),0}};fs.textures.resize(4);fs.textures[3]=image.get();
        Bindings rw=fs;rw.buffers={{xorConstants.get(),0}};Bindings sampled;sampled.textures={image.get()};
        Draw draw;draw.vertexCount=6;draw.viewport=Viewport{0,0,kWidth,kHeight,0,1};draw.scissor=phase&1?Scissor{8,8,40,32}:Scissor{0,0,kWidth,kHeight};
        RenderPass pass;pass.color0=scratch.get();pass.load=LoadAction::kClear;pass.clearColor[2]=pass.clearColor[3]=1;
        auto cb=queue->commandBuffer();cb->keepAlive(stores[mode]);cb->keepAlive(update);cb->keepAlive(sample);
        need(cb->draw(stores[mode]->program,pass,draw,vb,fs,options),"store",cb->error());
        pass.load=LoadAction::kLoad;need(cb->draw(update->program,pass,draw,plain,rw,options),"read-write",cb->error());
        pass.color0=target.get();pass.load=LoadAction::kDontCare;Draw full=draw;full.scissor={0,0,kWidth,kHeight};
        need(cb->draw(sample->program,pass,full,plain,sampled,options),"sample",cb->error());
        need(cb->counts().draws==3&&cb->counts().gmemPasses==0,"encoding","three actual sysmem draws required");
        const size_t before=audit->completed();cb->commit();cb->waitUntilCompleted();
        need(cb->status()==CommandBuffer::kCompleted&&audit->completed()==before+1,"completion",cb->error());
        for(uint32_t y=draw.scissor.y;y<draw.scissor.y+draw.scissor.height;y++)for(uint32_t x=draw.scissor.x;x<draw.scissor.x+draw.scissor.width;x++)expected[y*kWidth+x]=value^(x*17u)^(y*29u)^bits^xorValue;
        std::vector<uint32_t> colors(kPixels);for(unsigned i=0;i<kPixels;i++)colors[i]=rgba(expected[i]);
        verify(phase,"image",read(gpu,*image),expected);verify(phase,"sample",read(gpu,*target),colors);
        auto coverage=read(gpu,*scratch);for(uint32_t y=0;y<kHeight;y++)for(uint32_t x=0;x<kWidth;x++) {
            bool inside=x>=draw.scissor.x&&x<draw.scissor.x+draw.scissor.width&&y>=draw.scissor.y&&y<draw.scissor.y+draw.scissor.height;
            need(coverage[y*kWidth+x]==(inside?0xff000000u:0xffff0000u),"coverage","raster/scissor color mismatch");
        }
        std::printf("GAUGUIN IMAGE232 phase=%u mode=%u seed=%u xor=%u bits=%u draws=3 completed=1 gpu_ns=%lld\n",phase,mode,value,xorValue,bits,(long long)cb->gpuNanoseconds());
    }
    audit->final();need(gpu.faults()==faults,"faults","GPU reset counter changed");memory("completed");
}
int main(int argc,char** argv) {
    std::setvbuf(stdout,nullptr,_IOLBF,0);if(argc!=2||std::strcmp(argv[1],"--images232"))return 2;
    need(getuid()==0&&geteuid()==0,"scope","root only");char args[2048]{};size_t n=sizeof(args)-1;
    need(!sysctlbyname("kern.bootargs",args,&n,nullptr,0)&&n<sizeof(args)&&gauguin_metal_boot_profile(args),"scope","mode1/gmt1 required");
    std::signal(SIGALRM,expired);alarm(210);
    std::printf("GAUGUIN IMAGE232 begin build=%s core=%s library=%s jobs=9 draws=27 scope=root-core-not-MTLDevice\n",GAUGUIN_IMAGE_PROBE_BUILD,GAUGUIN_IMAGE_CORE_SHA256,kGauguinImageLibrarySHA256);
    memory("before-delay");const uint64_t start=clockNs();timespec rest{90,0};while(nanosleep(&rest,&rest))need(errno==EINTR,"delay","nanosleep");
    need(clockNs()-start>=90000000000ull,"delay","90s monotonic delay");const uint32_t seed=uint32_t(clockNs())^(uint32_t(getpid())*0x9e3779b9u);
    try {run(seed);}catch(const std::exception& e){fail("exception",e.what());}
    need(connectionClosed.load(),"close","sole connection not released");memory("released");
    need(clockNs()-start<210000000000ull,"deadline","finite deadline");alarm(0);
    std::printf("GAUGUIN IMAGE232 RESULT PASS build=%s seed=%u jobs=9 draws=27 compared=110592 raw_pixels=73728 connection_closed=1\n",GAUGUIN_IMAGE_PROBE_BUILD,seed);return 0;
}
