// Exercise the actual encoder and its upstream render suite. Access is exposed
// only to this test TU; production sources and class layout stay unchanged.
#include <atomic>
#include <condition_variable>
#include <cstdint>
#include <deque>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <algorithm>
#include <unordered_map>
#include <vector>
#include <chrono>
#include <cstdlib>
#include <new>
#include <stdexcept>
#include "hakios-metal/compute.hpp"
#include "hakios-metal/render.hpp"
#include "hakios-metal/gpu.hpp"
#include "hakios-metal/pm4.hpp"
#define private public
#include "hakios-metal/command.hpp"
#undef private
#include "render_test.cpp"

thread_local bool countAllocations = false;
thread_local uint64_t allocationCount = 0, allocationBytes = 0;
thread_local int64_t allocationFailure = -1;
void* operator new(std::size_t n) {
    if (allocationFailure == 0) throw std::bad_alloc();
    if (allocationFailure > 0) --allocationFailure;
    if (countAllocations) { ++allocationCount; allocationBytes += n; }
    if (void* p = std::malloc(n ? n : 1)) return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept { std::free(p); }
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete[](void* p) noexcept { ::operator delete(p); }

static void scratchEmpty(CommandBuffer& cb) {
#ifdef DR329_CANDIDATE
    for (auto* s : {&cb.drawScratch_.head, &cb.drawScratch_.body, &cb.drawScratch_.headSys, &cb.drawScratch_.bodySys}) {
        CHECK(s->words().empty());
        CHECK(s->words().capacity() <= 4096);
    }
#else
    (void)cb;
#endif
}
static void bytes(const void* p, size_t n) { CHECK(std::fwrite(p,1,n,stdout)==n); }
static void number(uint64_t n) { bytes(&n,sizeof n); }
static void snapshot(CommandBuffer& cb) {
    cb.closePass();
    const auto& w = cb.stream_.words();
    number(w.size()); bytes(w.data(),w.size()*sizeof(uint32_t));
    number(cb.slabs_.size());
    for (const auto& b : cb.slabs_) {
        number(b->gpuAddress()); number(b->length()); bytes(b->contents(),b->length());
    }
}
static void configure(CommandBuffer& cb, render::Options& o, unsigned mode) {
    o.gmem = mode >= 2;
    cb.setGmem(mode >= 2);
    cb.setGmemMinDraws(mode == 3 ? 16 : 0);
    o.dedupRegs = mode != 0;
}
static void equivalence() {
    unsigned cases = 0;
    for (unsigned mode = 0; mode < 4; ++mode) for (unsigned program = 0; program < 2; ++program)
    for (unsigned draws : {1u,3u,80u}) for (bool vary : {false,true}) {
        Rig r; auto t = target(r), t2 = target(r);
        auto cb = r.queue->commandBuffer(); render::Options o; configure(*cb,o,mode);
        auto p = program ? colorProgram() : flatProgram();
        RenderPass pass; pass.color0 = t.get(); auto d = wholeDraw();
        for (unsigned i = 0; i < draws; ++i) {
            if (vary) { d.viewport.x = i % 7; d.viewport.width = 64-d.viewport.x; pass.color0 = (i/13)%2 ? t2.get() : t.get(); }
            CHECK(cb->draw(p,pass,d,{}, {},o)); scratchEmpty(*cb);
        }
        number(mode);number(program);number(draws);number(vary);snapshot(*cb);
        cb->commit();cb->waitUntilCompleted();CHECK(cb->status()==CommandBuffer::kCompleted);
        scratchEmpty(*cb);++cases;
    }
    std::fprintf(stderr,"equivalence cases=%u failures=%d\n",cases,test::failures());
}
static void failures() {
    unsigned caught = 0, successes = 0;
    // Fail each allocation in a real second draw, after one draw has warmed the
    // scratch. Scope cleanup must also run when encoding throws midway through.
    for (unsigned mode = 0; mode < 4; ++mode) for (int64_t at = 0; at < 80; ++at) {
        Rig r; auto t = target(r); auto cb = r.queue->commandBuffer();
        render::Options o; configure(*cb,o,mode); RenderPass pass;pass.color0=t.get();
        auto p=flatProgram();auto d=wholeDraw(); CHECK(cb->draw(p,pass,d,{}, {},o));
        allocationFailure = at;
        try { if (cb->draw(p,pass,d,{}, {},o)) ++successes; }
        catch (const std::bad_alloc&) { ++caught; }
        allocationFailure=-1;scratchEmpty(*cb);
        // A partially failed direct C++ recording is discarded, as the C API
        // ownership suite checks its deferred error and completion contract.
    }
    CHECK(caught>0);CHECK(successes>0);
#ifdef DR329_CANDIDATE
    CommandBuffer::DrawScratch scratch;
    for (auto* s : {&scratch.head,&scratch.body,&scratch.headSys,&scratch.bodySys}) {
        s->packet(pm4::kNop,nullptr,0);
    }
    auto cap=scratch.body.words().capacity();scratch.reset();CHECK(scratch.body.words().capacity()==cap);
    for (unsigned i=0;i<5000;++i) scratch.body.packet(pm4::kNop,nullptr,0);
    CHECK(scratch.body.words().capacity()>4096);
    try { CommandBuffer::DrawScratch::Scope scope(scratch); CHECK(scratch.body.words().capacity()==0);
        for (unsigned i=0;i<5000;++i) scratch.bodySys.packet(pm4::kNop,nullptr,0);
        throw std::runtime_error("unwind");
    } catch (const std::runtime_error&) {}
    CHECK(scratch.bodySys.words().empty());CHECK(scratch.bodySys.words().capacity()==0);
    std::puts("capacity and scope unwinding passed");
#endif
    std::printf("fault injection caught=%u successes=%u failures=%d\n",caught,successes,test::failures());
}
static void bench(unsigned mode) {
    Rig r;auto t=target(r);auto cb=r.queue->commandBuffer();
    render::Options o;configure(*cb,o,mode);auto p=flatProgram();RenderPass pass;pass.color0=t.get();auto d=wholeDraw();
    CHECK(cb->draw(p,pass,d,{}, {},o));
    allocationCount=allocationBytes=0;countAllocations=true;
    auto begin=std::chrono::steady_clock::now();
    for (unsigned i=0;i<1000;++i) CHECK(cb->draw(p,pass,d,{}, {},o));
    auto end=std::chrono::steady_clock::now();countAllocations=false;
    auto count=allocationCount, total=allocationBytes;
    scratchEmpty(*cb);
    auto us=std::chrono::duration<double,std::micro>(end-begin).count();
    cb->commit();cb->waitUntilCompleted();CHECK(cb->status()==CommandBuffer::kCompleted);
    std::printf("{\"mode\":%u,\"draws\":1000,\"allocations\":%llu,\"allocated_bytes\":%llu,\"recording_us\":%.3f,\"failures\":%d}\n",
        mode,(unsigned long long)count,(unsigned long long)total,us,test::failures());
}
int main(int argc,char** argv) {
    if (argc<2) return 2;
    std::string mode=argv[1];
    if (mode=="equivalence") equivalence();
    else if (mode=="failures") failures();
    else if (mode=="bench" && argc==3) bench(unsigned(std::strtoul(argv[2],nullptr,10)));
    else if (mode=="regression") {
        for (const auto& c:test::cases()) { int before=test::failures();c.run();std::printf("%s %s\n",before==test::failures()?"PASS":"FAIL",c.name); }
        std::printf("render tests=%zu failures=%d\n",test::cases().size(),test::failures());
    } else return 2;
    return test::failures()?1:0;
}
