// SPDX-License-Identifier: MIT
// Finite root diagnostic of the actual A619 Metal core, not an MTLDevice plug-in.
#include <TargetConditionals.h>
#include <mach/mach.h>
#include <cerrno>
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
#include "fixtures/fill_id_bc.hpp"
#include "fixtures/tri_attr_vs_bc.hpp"
#include "fixtures/tri_color_fs_bc.hpp"
#include "fixtures/tri_cflat_fs_bc.hpp"
#include "fixtures/tri_tex_fs_bc.hpp"
#include "probe_pixels.hpp"
#ifdef GAUGUIN_METAL_BOOTSTRAP
#include <sys/sysctl.h>
#include "GauguinMetalDesktopPolicy.h"
#include "GauguinMetalBootstrapWait.h"
#include "gauguin_metal_bootstrap.h"
#endif

#if !TARGET_OS_IPHONE
#error This executable is an iOS-only root diagnostic
#endif
#if !defined(HAKIOS_METAL_TARGET_A619) || !defined(GAUGUIN_METAL_PROBE_BUILD) || !defined(GAUGUIN_METAL_CORE_SHA256)
#error Explicit target, probe build and core identity are required
#endif

using namespace hakios::metal;
namespace px=gauguin::metal_probe;
constexpr uint32_t kCpuRead=1,kCpuWrite=2; // MSM_PREP_READ / MSM_PREP_WRITE.
extern "C" int memorystatus_control(uint32_t,int32_t,uint32_t,void*,size_t);
struct MemLimit { int32_t active;uint32_t activeAttr;int32_t inactive;uint32_t inactiveAttr; };
static_assert(sizeof(MemLimit)==16);

[[noreturn]] static void fail(const char* stage,const std::string& why) {
    std::fprintf(stderr,"GAUGUIN METAL223 FAIL stage=%s why=%.320s\n",stage,why.c_str());
    std::fflush(nullptr);
    // In-flight DMA stays the kernel client's responsibility; do not unwind
    // buffers after a failed fence and accidentally recycle its pages.
    std::_Exit(1);
}
static void require(bool ok,const char* stage,const std::string& why) { if (!ok) fail(stage,why); }
static uint64_t nowNs() {
    timespec t{};require(clock_gettime(CLOCK_MONOTONIC_RAW,&t)==0,"clock","monotonic read");
    require(t.tv_sec>=0 && t.tv_nsec>=0 && t.tv_nsec<1000000000,"clock","invalid clock");
    return uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);
}
static void memory(const char* phase) {
    MemLimit m{};task_vm_info_data_t vm{};mach_msg_type_number_t count=TASK_VM_INFO_REV1_COUNT;
    require(memorystatus_control(8,getpid(),0,&m,sizeof(m))==0,"memory","GET8");
    require(task_info(mach_task_self(),TASK_VM_INFO,reinterpret_cast<task_info_t>(&vm),&count)==KERN_SUCCESS && count>=TASK_VM_INFO_REV1_COUNT,"memory","VM footprint query");
    std::printf("GAUGUIN METAL223 memory phase=%s active_mb=%d inactive_mb=%d active_attr=%u inactive_attr=%u footprint=%llu\n",phase,m.active,m.inactive,m.activeAttr,m.inactiveAttr,(unsigned long long)vm.phys_footprint);
    require(m.active==128 && m.inactive==128 && m.activeAttr==1 && m.inactiveAttr==1 && vm.phys_footprint>0 && vm.phys_footprint<=128ull*1024*1024,"memory","expected finite128MiB hard limits");
}

class Audited final : public Transport {
    std::unique_ptr<Transport> inner_;
    std::mutex lock_;
    std::set<std::pair<uint32_t,uint32_t>> submitted_,completed_;
public:
    explicit Audited(std::unique_ptr<Transport> t):inner_(std::move(t)) {}
    int call(uint32_t request,void* data,size_t size) override {
        if (request==kGetParam) require(size==sizeof(MsmParam) && static_cast<MsmParam*>(data)->pipe==0x10,"wire","query pipe/layout");
        if (request==kGemSubmit) require(size==sizeof(MsmGemSubmit) && (static_cast<MsmGemSubmit*>(data)->flags&0x1f)==0x10,"wire","submit pipe/layout");
        int rc=inner_->call(request,data,size);
        if (rc==0 && request==kGemSubmit) {
            auto* s=static_cast<MsmGemSubmit*>(data);std::lock_guard<std::mutex> guard(lock_);
            require(s->fence!=0 && submitted_.size()<64 && submitted_.insert({s->queueid,s->fence}).second,"fence","invalid/duplicate submit receipt");
        }
        if (rc==0 && request==kWaitFence) {
            auto* w=static_cast<MsmWaitFence*>(data);std::lock_guard<std::mutex> guard(lock_);
            require(submitted_.count({w->queueid,w->fence})==1,"fence","wait did not name a submitted queue/fence");
            completed_.insert({w->queueid,w->fence});
        }
        return rc;
    }
    void* map(uint32_t h,uint64_t n) override { return inner_->map(h,n); }
    void unmap(uint32_t h,void* p) override { inner_->unmap(h,p); }
    int64_t nowNs() override { return inner_->nowNs(); }
    size_t completed() { std::lock_guard<std::mutex> guard(lock_);return completed_.size(); }
    void final() {
        std::lock_guard<std::mutex> guard(lock_);
        require(submitted_==completed_ && completed_.size()>=8,"fence","all eight jobs must complete before handoff");
        for (auto p:completed_) std::printf("GAUGUIN METAL223 fence queue=%u value=%u complete=1\n",p.first,p.second);
    }
};

static void cpu(Gpu& gpu,const Buffer& b,uint32_t op,const char* phase) {
    int rc=gpu.cpuPrep(b.bo(),op,5000000000ll);
    require(rc==0,phase,"CPU prepare rc="+std::to_string(rc));
}
static void upload(Gpu& gpu,const std::shared_ptr<Buffer>& b,const void* data,size_t bytes) {
    require(b && b->contents() && bytes<=b->length(),"upload","buffer bounds");
    cpu(gpu,*b,kCpuWrite,"upload");std::memcpy(b->contents(),data,bytes);gpu.cpuFini(b->bo());
}
static void finish(const std::shared_ptr<CommandBuffer>& cb,Audited& audit,const char* phase,size_t before) {
    std::printf("GAUGUIN METAL223 submit phase=%s\n",phase);
    cb->commit();cb->waitUntilCompleted();
    require(cb->status()==CommandBuffer::kCompleted,phase,cb->error());
    require(audit.completed()==before+1,phase,"one completed queue/fence per job");
    std::printf("GAUGUIN METAL223 completed phase=%s gpu_ns=%lld fences=%zu\n",phase,(long long)cb->gpuNanoseconds(),audit.completed());
}
template<class T,class Expected>
static void verify(Gpu& gpu,const Texture& t,const char* phase,Expected expected) {
    std::string why;std::vector<T> image(px::kPixels);
    cpu(gpu,*t.buffer(),kCpuRead,phase);
    bool ok=t.read(0,0,px::kWidth,px::kHeight,image.data(),px::kWidth*sizeof(T),&why);
    gpu.cpuFini(t.buffer()->bo());require(ok,phase,why);
    auto r=px::compare(image.data(),image.size(),expected);
    if (!r.equal) {
        char msg[160];std::snprintf(msg,sizeof(msg),"pixel=%zu actual=%016llx expected=%016llx",r.firstBad,(unsigned long long)r.actual,(unsigned long long)r.expected);
        fail(phase,msg);
    }
    std::printf("GAUGUIN METAL223 pixels phase=%s compared=%zu hash=%016llx PASS\n",phase,r.checked,(unsigned long long)r.hash);
}
static std::shared_ptr<Texture> texture(Gpu& gpu,PixelFormat format,uint32_t usage) {
    TextureDesc d;d.width=px::kWidth;d.height=px::kHeight;d.format=format;d.usage=usage;
    std::string why;auto t=Texture::make(gpu,d,&why);require(bool(t),"texture",why);return t;
}
static void poison(Gpu& gpu,Texture& t,size_t cpp) {
    std::vector<uint8_t> bytes(px::kPixels*cpp,0xa5);std::string why;
    cpu(gpu,*t.buffer(),kCpuWrite,"poison");
    bool ok=t.replace(0,0,px::kWidth,px::kHeight,bytes.data(),px::kWidth*cpp,&why);
    gpu.cpuFini(t.buffer()->bo());require(ok,"poison",why);
}
static std::shared_ptr<CompiledProgram> program(std::shared_ptr<CompiledStage> vs,std::shared_ptr<CompiledStage> fs,PixelFormat format) {
    std::string why;auto p=linkProgram(std::move(vs),std::move(fs),format,&why);require(bool(p),"pipeline",why);
    p->program.vertexDescriptor.attributes[0]=VertexAttribute{VertexFormat::kFloat2,0,0};
    p->program.vertexDescriptor.attributes[1]=VertexAttribute{VertexFormat::kUChar4Normalized,8,0};
    p->program.vertexDescriptor.layouts[0]=VertexLayout{12,VertexStep::kPerVertex,1};
    return std::shared_ptr<CompiledProgram>(std::move(p));
}
static std::shared_ptr<CompiledStage> stage(const void* bc,size_t size) {
    std::string why;auto s=compileStage(bc,size,&why);require(bool(s),"AIR-stage",why);return std::shared_ptr<CompiledStage>(std::move(s));
}

#ifdef GAUGUIN_METAL_BOOTSTRAP
/* GAUGUIN_BOOTSTRAP_WAIT_BEGIN: execute these actual bodies in host controls. */
static bool bootstrapWaitClock(void*,uint64_t* out) {
    timespec t{};
    if(clock_gettime(CLOCK_MONOTONIC_RAW,&t)||t.tv_sec<0||t.tv_nsec<0||t.tv_nsec>=1000000000||
       uint64_t(t.tv_sec)>(UINT64_MAX-uint64_t(t.tv_nsec))/1000000000)return false;
    *out=uint64_t(t.tv_sec)*1000000000+uint64_t(t.tv_nsec);return true;
}
static bool bootstrapWaitSleep(void*,uint64_t ns) {
    timespec pause{time_t(ns/1000000000),long(ns%1000000000)};
    for(unsigned n=0;n<100;n++) {
        if(!nanosleep(&pause,&pause))return true;
        if(errno!=EINTR)return false;
    }
    return false;
}
static void* bootstrapWaitOpen(void* why) {
    return openKernelGpu(static_cast<std::string*>(why)).release();
}
static void bootstrapWaitClose(void*,void* transport) { delete static_cast<Transport*>(transport); }
static std::unique_ptr<Transport> bootstrapOpen(std::string* why) {
    gauguin_metal_wait_ops ops{why,bootstrapWaitClock,bootstrapWaitSleep,bootstrapWaitOpen,bootstrapWaitClose};
    gauguin_metal_wait_result result{};
    auto* transport=static_cast<Transport*>(gauguin_metal_wait_open(&ops,&result));
    std::printf("GAUGUIN METAL279 startup-open reason=%u attempts=%u elapsed_ns=%llu connected=%u\n",
                unsigned(result.reason),result.attempts,(unsigned long long)result.elapsed_ns,transport!=nullptr);
    return std::unique_ptr<Transport>(transport);
}
/* GAUGUIN_BOOTSTRAP_WAIT_END */
#endif

static void run(uint32_t seed) {
    std::string why;
#ifdef GAUGUIN_METAL_BOOTSTRAP
    auto transport=bootstrapOpen(&why);require(bool(transport),"GPU-open",why);
    // The startup wait has its own monotonic deadline. Keep the independent
    // thirty-second GPU-work watchdog after a real owner has been acquired.
    alarm(30);
#else
    auto transport=openKernelGpu(&why);require(bool(transport),"GPU-open",why);
#endif
    auto wrapped=std::make_unique<Audited>(std::move(transport));auto* audit=wrapped.get();
    Gpu gpu(std::move(wrapped));
    const uint32_t ids[4]={kParamGpuId,kParamChipId,kParamGmemSize,kParamGmemBase};
    const uint64_t expected[4]={619,0x06010900,524288,0x100000};
    for (unsigned i=0;i<4;i++) {uint64_t value=0;require(gpu.param(ids[i],&value)==0 && value==expected[i],"identity","actual A619 parameter mismatch");}
    std::printf("GAUGUIN METAL223 identity gpu=619 chip=06010900 gmem=524288 base=100000 seed=%u\n",seed);
    require(hasCompiler(),"compiler","AIR compiler absent");
    const uint64_t start=nowNs();
    auto queue=CommandQueue::make(gpu,&why);require(bool(queue),"queue",why);
    auto ck=compileAir(kernels::fill_id_bc,sizeof(kernels::fill_id_bc),&why);require(bool(ck),"AIR-compute",why);
    auto vs=stage(kernels::tri_attr_vs_bc,sizeof(kernels::tri_attr_vs_bc));
    auto fs=stage(kernels::tri_color_fs_bc,sizeof(kernels::tri_color_fs_bc));
    auto tf=stage(kernels::tri_tex_fs_bc,sizeof(kernels::tri_tex_fs_bc));
    auto cf=stage(kernels::tri_cflat_fs_bc,sizeof(kernels::tri_cflat_fs_bc));
    auto tri=program(vs,fs,PixelFormat::kRGBA8Unorm),sample=program(vs,tf,PixelFormat::kRGBA8Unorm);
    auto add=program(vs,cf,PixelFormat::kRGBA8Unorm),premul=program(vs,cf,PixelFormat::kRGBA16Float);
    memory("compiled");
    auto target=texture(gpu,PixelFormat::kRGBA8Unorm,kTextureUsageRenderTarget|kTextureUsageRead);
    render::Options options;options.gmem=false; // sysmem first; no compression or GMEM qualification here.
    for (unsigned i=0;i<2;i++) {
        poison(gpu,*target,4);uint32_t color=px::binaryColor((seed&7)^(i?7:0));
        RenderPass pass;pass.color0=target.get();pass.load=LoadAction::kClear;
        for (unsigned c=0;c<4;c++) pass.clearColor[c]=double((color>>(8*c))&255)/255.0;
        auto cb=queue->commandBuffer();require(cb->clear(pass,options),"clear",cb->error());
        const char* phase=i?"clear-B":"clear-A";size_t before=audit->completed();finish(cb,*audit,phase,before);
        verify<uint32_t>(gpu,*target,phase,[=](size_t){return color;});
    }
    auto out=newBuffer(gpu,1024,&why),constant=newBuffer(gpu,16384,&why);require(out && constant,"compute","allocation");
    std::vector<uint32_t> blank(256,0xa5a5a5a5);upload(gpu,out,blank.data(),1024);upload(gpu,constant,&seed,4);
    Bindings cbinding;cbinding.buffers={{out.get(),0},{constant.get(),0}};uint32_t groups[3]={4,1,1},local[3]={64,1,1};
    auto cb=queue->commandBuffer();require(cb->dispatch(ck->kernel,groups,local,cbinding),"compute",cb->error());
    size_t before=audit->completed();finish(cb,*audit,"compute",before);
    cpu(gpu,*out,kCpuRead,"compute-read");std::vector<uint32_t> got(256);std::memcpy(got.data(),out->contents(),1024);gpu.cpuFini(out->bo());
    auto cr=px::compare(got.data(),got.size(),[=](size_t i){return px::computeWord(seed,uint32_t(i));});
    require(cr.equal,"compute-read","exact gid*0x9e3779b1+seed readback");
    std::printf("GAUGUIN METAL223 pixels phase=compute compared=256 hash=%016llx PASS\n",(unsigned long long)cr.hash);
    auto vertices=newBuffer(gpu,sizeof(px::kQuad),&why);require(bool(vertices),"vertices",why);
    upload(gpu,vertices,px::kTriangle,sizeof(px::kTriangle));
    Bindings vb;vb.buffers={{vertices.get(),0}};Draw draw;draw.vertexCount=3;draw.viewport=Viewport{0,0,64,64,0,1};
    poison(gpu,*target,4);RenderPass pass;pass.color0=target.get();pass.load=LoadAction::kClear;pass.clearColor[2]=pass.clearColor[3]=1;
    cb=queue->commandBuffer();require(cb->draw(tri->program,pass,draw,vb,Bindings{},options),"triangle",cb->error());
    before=audit->completed();finish(cb,*audit,"triangle",before);
    verify<uint32_t>(gpu,*target,"triangle",[](size_t i){return px::triangle(uint32_t(i%64),uint32_t(i/64));});
    upload(gpu,vertices,px::kQuad,sizeof(px::kQuad));draw.vertexCount=6;
    auto source=texture(gpu,PixelFormat::kRGBA8Unorm,kTextureUsageRead);
    SamplerDesc sd;Sampler sampler;require(makeSampler(sd,&sampler,&why),"sampler",why);
    Bindings fb;fb.textures={source.get()};fb.samplers={&sampler};
    for (unsigned phase=0;phase<2;phase++) {
        uint32_t s=seed^(phase?8:0);std::vector<uint32_t> pixels(px::kPixels);
        for (uint32_t i=0;i<px::kPixels;i++) pixels[i]=px::checker(s,i%64,i/64);
        cpu(gpu,*source->buffer(),kCpuWrite,"texture-upload");
        bool ok=source->replace(0,0,64,64,pixels.data(),256,&why);gpu.cpuFini(source->buffer()->bo());require(ok,"texture-upload",why);
        poison(gpu,*target,4);pass.load=LoadAction::kDontCare;
        cb=queue->commandBuffer();require(cb->draw(sample->program,pass,draw,vb,fb,options),"texture",cb->error());
        const char* label=phase?"texture-B":"texture-A";before=audit->completed();finish(cb,*audit,label,before);
        verify<uint32_t>(gpu,*target,label,[=](size_t i){return px::checker(s,uint32_t(i%64),uint32_t(i/64));});
    }
    float color[4]={1,0,0,0};upload(gpu,constant,color,sizeof(color));Bindings uniform;uniform.buffers={{constant.get(),0}};
    add->program.blend.enabled=true;add->program.blend.dstRgb=add->program.blend.dstAlpha=1;
    pass.load=LoadAction::kClear;pass.clearColor[0]=pass.clearColor[2]=0;pass.clearColor[1]=pass.clearColor[3]=1;
    cb=queue->commandBuffer();require(cb->draw(add->program,pass,draw,vb,uniform,options),"additive",cb->error());
    before=audit->completed();finish(cb,*audit,"additive",before);
    verify<uint32_t>(gpu,*target,"additive",[](size_t){return px::rgba(255,255,0);});
    auto half=texture(gpu,PixelFormat::kRGBA16Float,kTextureUsageRenderTarget|kTextureUsageRead);poison(gpu,*half,8);
    color[0]=color[3]=0.5f;upload(gpu,constant,color,sizeof(color));
    premul->program.blend.enabled=true;premul->program.blend.dstRgb=premul->program.blend.dstAlpha=5;
    pass.color0=half.get();
    cb=queue->commandBuffer();require(cb->draw(premul->program,pass,draw,vb,uniform,options),"premultiplied",cb->error());
    before=audit->completed();finish(cb,*audit,"premultiplied-half",before);
    verify<uint64_t>(gpu,*half,"premultiplied-half",[](size_t){return px::kPremultipliedHalf;});
    audit->final();uint64_t end=nowNs();require(end>=start && end-start<120ull*1000000000,"deadline","probe exceeded120s or clock reversed");memory("completed");
#ifdef GAUGUIN_METAL_BOOTSTRAP
    ggr_bootstrap arm={GGR_BOOTSTRAP_VERSION,uint32_t(audit->completed()),0,0,0};
    require(audit->call(GGR_BOOTSTRAP_SELECTOR,&arm,sizeof(arm))==0 &&
            arm.version==GGR_BOOTSTRAP_VERSION && arm.checks==audit->completed() &&
            arm.fence && arm.epoch && !arm.reserved,"bootstrap-arm","kernel did not arm this exact owner");
    std::printf("GAUGUIN METAL245 armed epoch=%llu jobs=%u fence=%u ready=0\n",
                (unsigned long long)arm.epoch,arm.checks,arm.fence);
#endif
}

int main(int argc,char** argv) {
    std::setvbuf(stdout,nullptr,_IOLBF,0);
#ifdef GAUGUIN_METAL_BOOTSTRAP
    if(argc!=2 || std::strcmp(argv[1],"--bootstrap245") || std::strcmp(getprogname(),"gauguin-metal-bootstrap"))return 2;
    char bootargs[1024]={0};size_t bootbytes=sizeof(bootargs)-1;
    require(sysctlbyname("kern.bootargs",bootargs,&bootbytes,nullptr,0)==0 && bootbytes<sizeof(bootargs) &&
            gauguin_desktop_boot(bootargs),"bootstrap-scope","exact mode2/gmt2/dyld1 required");
#else
    if (argc!=2 || std::strcmp(argv[1],"--metal223")) return 2;
#endif
    require(getuid()==0 && geteuid()==0,"scope","root diagnostic only");
    std::printf("GAUGUIN METAL223 begin build=%s core=%s scope=offscreen-core-not-MTLDevice\n",GAUGUIN_METAL_PROBE_BUILD,GAUGUIN_METAL_CORE_SHA256);
#ifdef GAUGUIN_METAL_BOOTSTRAP
    memory("bootstrap-start");
    std::printf("GAUGUIN METAL245 begin build=%s startup_budget=180 work_deadline=30\n",GAUGUIN_METAL_PROBE_BUILD);
#else
    memory("before-delay");
    uint64_t start=nowNs();timespec rest{90,0};
    while (nanosleep(&rest,&rest)!=0) require(errno==EINTR,"delay","nanosleep");
    uint64_t end=nowNs();require(end>=start && end-start>=90ull*1000000000,"delay","monotonic90s");
#endif
    uint32_t seed=uint32_t(nowNs())^(uint32_t(getpid())*0x9e3779b9u);
    try { run(seed); } catch (const std::exception& e) { fail("exception",e.what()); }
#ifdef GAUGUIN_METAL_BOOTSTRAP
    alarm(0);
    std::printf("GAUGUIN METAL245 RESULT PASS build=%s seed=%u arm=1 teardown-requested=1 stages=8 ready=kernel-close-required\n",GAUGUIN_METAL_PROBE_BUILD,seed);
#endif
    // All buffers, queue and the sole GPU connection are closed before PASS.
    std::printf("GAUGUIN METAL223 RESULT PASS build=%s seed=%u connection-teardown-requested=1 stages=8\n",GAUGUIN_METAL_PROBE_BUILD,seed);
    return 0;
}
