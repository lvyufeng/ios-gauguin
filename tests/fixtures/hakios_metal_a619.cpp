// SPDX-License-Identifier: MIT
// Production Metal core + real Mesa AIR/NIR/IR3. No hardware execution.
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <stdexcept>
#include "hakios-metal/device_profile.hpp"
#include "hakios-metal/a6xx.hpp"
#include "hakios-metal/compiler.hpp"
#include "hakios-metal/command.hpp"
#include "hakios-metal/fake_gpu.hpp"
#include "hakios-metal/hakios_metal.h"
#include "fixtures/fill_id_bc.hpp"
#include "fixtures/tri_color_vs_bc.hpp"
#include "fixtures/tri_color_fs_bc.hpp"
extern "C" {
#include "common/freedreno_dev_info.h"
}

using namespace hakios::metal;
static unsigned checks;
#define CHECK(c) do { ++checks; if (!(c)) throw std::runtime_error(#c); } while (0)
#define SAME(a,b) CHECK((a)==(b))

class Recorded final : public Transport {
public:
    FakeGpu gpu;
    unsigned queries=0,submits=0;
    int call(uint32_t request,void* p,size_t n) override {
        if (request==kGetParam) { CHECK(n==sizeof(MsmParam)); SAME(static_cast<MsmParam*>(p)->pipe,0x10u); ++queries; }
        if (request==kGemSubmit) { CHECK(n==sizeof(MsmGemSubmit)); SAME(static_cast<MsmGemSubmit*>(p)->flags & 0x1fu,0x10u); ++submits; }
        return gpu.call(request,p,n);
    }
    void* map(uint32_t h,uint64_t n) override { return gpu.map(h,n); }
    void unmap(uint32_t h,void* p) override { gpu.unmap(h,p); }
    int64_t nowNs() override { return gpu.nowNs(); }
};

static size_t findReg(const pm4::Stream& s,uint32_t r) {
    const auto& w=s.words();
    for (size_t i=0;i<w.size();) {
        auto h=pm4::decode(w[i]); CHECK(i+1+h.count<=w.size());
        if (h.kind==pm4::Header::kRegisters && r>=h.reg && r<h.reg+h.count) return i+1+r-h.reg;
        i+=1+h.count;
    }
    return size_t(-1);
}
static size_t findOp(const pm4::Stream& s,uint32_t op) {
    const auto& w=s.words();
    for (size_t i=0;i<w.size();) {
        auto h=pm4::decode(w[i]); CHECK(i+1+h.count<=w.size());
        if (h.kind==pm4::Header::kCommand && h.opcode==op) return i;
        i+=1+h.count;
    }
    return size_t(-1);
}

int main() try {
    const auto& p=device::kTarget;
    fd_dev_id id{};id.chip_id=0x06010900;
    const struct fd_dev_info* m=fd_dev_info_raw(&id);CHECK(m);
    SAME(p.chipId,0x06010900u);SAME(p.pipe,0x10u);
    SAME(p.numSp,m->num_sp_cores);SAME(p.numCcu,m->num_ccu);
    SAME(p.fibersPerSp,m->fibers_per_sp);SAME(p.instrCacheSize,m->a6xx.instr_cache_size);
    SAME(p.regSizeVec4,m->a6xx.reg_size_vec4);SAME(p.csSharedBytes,m->cs_shared_mem_size);
    SAME(p.threadsizeBase,m->threadsize_base);SAME(p.maxWaves,m->max_waves);SAME(p.waveGranularity,m->wave_granularity);
    SAME(p.tileAlignW,m->tile_align_w);SAME(p.tileAlignH,m->tile_align_h);
    SAME(p.gmemAlignW,m->gmem_align_w);SAME(p.gmemAlignH,m->gmem_align_h);
    SAME(p.tileMaxW,m->tile_max_w);SAME(p.tileMaxH,m->tile_max_h);SAME(p.numVscPipes,m->num_vsc_pipes);
    SAME(p.highestBankBit,m->highest_bank_bit);SAME(p.ubwcSwizzle,m->ubwc_swizzle);SAME(p.macrotileMode,m->macrotile_mode);
    SAME(p.depthCacheBytes,m->a6xx.sysmem_per_ccu_depth_cache_size);SAME(p.colorCacheBytes,m->a6xx.sysmem_per_ccu_color_cache_size);
    SAME(p.gmemColorCacheDivisor,1u<<m->a6xx.gmem_ccu_color_cache_fraction);
    SAME(a6xx::kGmemCcuColorOffset,p.gmemBytes-m->num_ccu*m->a6xx.sysmem_per_ccu_color_cache_size/(1u<<m->a6xx.gmem_ccu_color_cache_fraction));
    SAME(p.hasLpac,m->a6xx.has_lpac);SAME(p.supportsDoubleThreadsize,m->a6xx.supports_double_threadsize);
    SAME(p.hasGmemFastClear,m->a6xx.has_gmem_fast_clear);SAME(p.concurrentResolve,m->a6xx.concurrent_resolve);
    SAME(p.hasEarlyPreamble,m->a6xx.has_early_preamble);SAME(p.hasCubicFilter,m->a6xx.has_tex_filter_cubic);
    SAME(p.indirectDrawWfm,m->a6xx.indirect_draw_wfm_quirk);SAME(p.depthBoundsRequireDepthTest,m->a6xx.depth_bounds_require_depth_test_quirk);
    SAME(p.hasScalarAlu,m->a6xx.has_scalar_alu);SAME(p.hasGetFiberId,m->a6xx.has_getfiberid);
    SAME(p.hasDp2Acc,m->a6xx.has_dp2acc);SAME(p.hasDp4Acc,m->a6xx.has_dp4acc);
    SAME(p.hasCpRegWrite,m->a6xx.has_cp_reg_write);SAME(p.has8bppUbwc,m->a6xx.has_8bpp_ubwc);
    SAME(p.magic.pcPower,m->a6xx.magic.PC_POWER_CNTL);SAME(p.magic.tpl1Dbg,m->a6xx.magic.TPL1_DBG_ECO_CNTL);
    SAME(p.magic.grasDbg,m->a6xx.magic.GRAS_DBG_ECO_CNTL);SAME(p.magic.spChicken,m->a6xx.magic.SP_CHICKEN_BITS);
    SAME(p.magic.ucheClient,m->a6xx.magic.UCHE_CLIENT_PF);SAME(p.magic.pcMode,m->a6xx.magic.PC_MODE_CNTL);
    SAME(p.magic.spDbg,m->a6xx.magic.SP_DBG_ECO_CNTL);SAME(p.magic.rbDbg,m->a6xx.magic.RB_DBG_ECO_CNTL);
    SAME(p.magic.hlsqDbg,m->a6xx.magic.HLSQ_DBG_ECO_CNTL);SAME(p.magic.rbUnknown8e01,m->a6xx.magic.RB_UNKNOWN_8E01);
    SAME(p.magic.vpcDbg,m->a6xx.magic.VPC_DBG_ECO_CNTL);SAME(p.magic.ucheUnknown0e12,m->a6xx.magic.UCHE_UNKNOWN_0E12);
    CHECK(device::acceptsChip(0x06010900));CHECK(!device::acceptsChip(0));CHECK(!device::acceptsChip(0x06030500));
    CHECK(hakios_metal_chip_known(0x06010900));CHECK(!hakios_metal_chip_known(0));
    CHECK(hasCompiler());
    std::string why;
    auto ck=compileAir(kernels::fill_id_bc,sizeof(kernels::fill_id_bc),&why);CHECK(ck);
    auto vs=compileStage(kernels::tri_color_vs_bc,sizeof(kernels::tri_color_vs_bc),&why);CHECK(vs);
    auto fs=compileStage(kernels::tri_color_fs_bc,sizeof(kernels::tri_color_fs_bc),&why);CHECK(fs);
    auto prog=linkProgram(std::shared_ptr<CompiledStage>(std::move(vs)),std::shared_ptr<CompiledStage>(std::move(fs)),PixelFormat::kRGBA8Unorm,&why);CHECK(prog);
    auto tr=std::make_unique<Recorded>();auto* trace=tr.get();Gpu gpu(std::move(tr));
    SAME(gpu.chipId(),0x06010900u);CHECK(trace->queries);
    auto queue=CommandQueue::make(gpu,&why);CHECK(queue);
    PrivateMemory priv{};
    auto scratch=queue->privateMemory(513,false,&priv,&why);CHECK(scratch);
    SAME(priv.perFiber,1024u);SAME(priv.perSp,1024u*m->fibers_per_sp);SAME(scratch->length(),uint64_t(priv.perSp)*m->num_sp_cores);
    auto dst=newBuffer(gpu,65536,&why);CHECK(dst);
    auto constant=newBuffer(gpu,16384,&why);CHECK(constant);
    uint32_t addend=0x51;std::memcpy(constant->contents(),&addend,sizeof(addend));
    Bindings binds;binds.buffers={Binding{dst.get(),0},Binding{constant.get(),0}};
    uint32_t groups[3]={1,1,1},local[3]={64,1,1};
    auto cb=queue->commandBuffer();bool dispatched=cb->dispatch(ck->kernel,groups,local,binds);
    if (!dispatched) std::fprintf(stderr,"dispatch refused: %s\n",cb->error().c_str());CHECK(dispatched);
    cb->commit();cb->waitUntilCompleted();
    if (cb->status()!=CommandBuffer::kCompleted) std::fprintf(stderr,"fake submission: %s / %s\n",cb->error().c_str(),trace->gpu.stats().lastFault.c_str());
    SAME(cb->status(),CommandBuffer::kCompleted);CHECK(trace->submits);
    // A long program is only encoded, never executed. Its words are dummy
    // storage; inspect the real preload and workaround emitted from metadata.
    Kernel longK=ck->kernel;longK.instrlen=96;longK.numWords=96*32;
    auto program=newBuffer(gpu,uint64_t(longK.numWords)*4,&why);CHECK(program);
    auto table=newBuffer(gpu,compute::kTableBytes,&why);CHECK(table);
    pm4::Stream stream;compute::Options opt;opt.hlsqCopies=true;
    CHECK(compute::encode(stream,longK,groups,local,binds,nullptr,program->gpuAddress(),table->gpuAddress(),static_cast<uint8_t*>(table->contents()),&why,opt));
    SAME(findReg(stream,a6xx::REG_A6XX_HLSQ_CS_CTRL_REG1),size_t(-1));
    SAME(findReg(stream,a6xx::REG_A6XX_SP_CS_CNTL_0),size_t(-1));
    size_t fsLen=findReg(stream,a6xx::REG_A6XX_SP_FS_INSTRLEN);CHECK(fsLen!=size_t(-1));SAME(stream.words()[fsLen],96u);
    unsigned preloads=0;
    for (size_t i=0;i<stream.words().size();) {
        auto h=pm4::decode(stream.words()[i]);
        if (h.kind==pm4::Header::kCommand && h.opcode==a6xx::CP_LOAD_STATE6_FRAG) {
            uint32_t v=stream.words()[i+1];
            auto type=(v&a6xx::CP_LOAD_STATE6_0_STATE_TYPE__MASK)>>a6xx::CP_LOAD_STATE6_0_STATE_TYPE__SHIFT;
            auto block=(v&a6xx::CP_LOAD_STATE6_0_STATE_BLOCK__MASK)>>a6xx::CP_LOAD_STATE6_0_STATE_BLOCK__SHIFT;
            if (type==a6xx::ST6_SHADER && block==a6xx::SB6_CS_SHADER) {
                SAME((v&a6xx::CP_LOAD_STATE6_0_NUM_UNIT__MASK)>>a6xx::CP_LOAD_STATE6_0_NUM_UNIT__SHIFT,64u);++preloads;
            }
        }
        i+=1+h.count;
    }
    SAME(preloads,1u);
    Sampler sampler;SamplerDesc sd;CHECK(makeSampler(sd,&sampler,&why));
    sd.minFilter=1;sd.magFilter=1;CHECK(makeSampler(sd,&sampler,&why));
    sd.minFilter=2;CHECK(!makeSampler(sd,&sampler,&why));CHECK(why.find("not supported")!=std::string::npos);
    sd.minFilter=0;sd.magFilter=2;CHECK(!makeSampler(sd,&sampler,&why));
    // Actual AIR VS/FS, linked above, in a sysmem indirect draw.
    TextureDesc td;td.width=64;td.height=64;td.usage=kTextureUsageRenderTarget|kTextureUsageRead;
    auto target=Texture::make(gpu,td,&why);CHECK(target);
    RenderPass pass;pass.color0=target.get();
    auto args=newBuffer(gpu,64,&why);CHECK(args);
    uint32_t counts[4]={3,1,0,0};std::memcpy(args->contents(),counts,sizeof(counts));
    Draw draw;draw.vertexCount=3;draw.viewport=Viewport{0,0,64,64,0,1};draw.indirect=args.get();
    auto vp=newBuffer(gpu,4ull*prog->program.vs.k.numWords,&why);CHECK(vp);
    auto fp=newBuffer(gpu,4ull*prog->program.fs.k.numWords,&why);CHECK(fp);
    auto rt=newBuffer(gpu,render::kTableBytes,&why);CHECK(rt);
    pm4::Stream rs;render::Options ro;ro.gmem=false;
    CHECK(render::encode(rs,prog->program,pass,draw,Bindings{},Bindings{},vp->gpuAddress(),fp->gpuAddress(),rt->gpuAddress(),static_cast<uint8_t*>(rt->contents()),&why,ro));
    auto wfm=findOp(rs,a6xx::CP_WAIT_FOR_ME),ind=findOp(rs,a6xx::CP_DRAW_INDIRECT_MULTI);
    CHECK(wfm!=size_t(-1) && ind!=size_t(-1) && wfm<ind);
    for (auto rw:a6xx::kStaticState) {
        if (rw.reg==a6xx::REG_A6XX_SP_CHICKEN_BITS) SAME(rw.value,m->a6xx.magic.SP_CHICKEN_BITS);
        if (rw.reg==a6xx::REG_A6XX_TPL1_DBG_ECO_CNTL) SAME(rw.value,m->a6xx.magic.TPL1_DBG_ECO_CNTL);
    }
    std::printf("%u A619 production-core/Mesa/compiler/encoder checks; hardware unqualified\n",checks);
    return 0;
} catch (const std::exception& e) { std::fprintf(stderr,"FAIL %s\n",e.what());return 1; }
