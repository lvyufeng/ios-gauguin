#include "inherited-workspace342.inc"
#include "fixtures/tri_flat_vs_air.hpp"
#include "fixtures/tri_flat_fs_air.hpp"

namespace {
struct ProgramScope342 {
    gauguin342::DrawData* previous;
    uint64_t previousJob;
    explicit ProgramScope342(gauguin342::DrawData& d) : previous(gauguin342::activeDraw),previousJob(gauguin342::activeJobSequence) {
        gauguin342::activeDraw=&d;gauguin342::activeJobSequence=101;
    }
    ~ProgramScope342() {gauguin342::activeDraw=previous;gauguin342::activeJobSequence=previousJob;}
};
void pool342() {
    Events events;auto* d=device(events);auto* q=queue(d,false);
    auto& native=*q->control->storage->queue;gauguin342::DrawData data;std::string why;
    {
        ProgramScope342 scope(data);
        auto b=native.takeBuffer(4096,&why);CHECK(b);
        auto* pointer=b.get();std::memset(b->contents(),0xab,4096);
        native.giveBuffer(std::move(b));CHECK(!b);
        b=native.takeBuffer(4096,&why);CHECK(b && b.get()==pointer);
        auto* bytes=static_cast<const uint8_t*>(b->contents());for (unsigned i=0;i<4096;i++) CHECK(bytes[i]==0);
        CHECK(data.program.pool.calls==2 && data.program.pool.ok==2 && !data.program.pool.flags);
        CHECK(data.program.counts[9]==1 && data.program.counts[10]==1 && data.program.counts[13]==4096);
        native.giveBuffer(std::move(b));
    }
    CHECK(gauguin342::activeDraw==nullptr);close(q,d,events);
}
void resident342(bool failure) {
    Events events;auto* d=device(events);auto* q=queue(d,false);auto& native=*q->control->storage->queue;
    std::array<uint32_t,64> words{};words[0]=0x12345678;
    Kernel k{};k.words=words.data();k.numWords=words.size();std::string why;gauguin342::DrawData data;
    if (failure) {
        {ProgramScope342 scope(data);rejectAllocation=true;
            try {(void)native.programBuffer(k,&why);CHECK(false);}catch(const std::bad_alloc&) {}
            rejectAllocation=false;
        }
        CHECK(data.program.resident.failed==1 && data.program.resident.flags);
        // The same production lock must be available after allocation unwinds.
        auto recovered=native.programBuffer(k,&why);CHECK(recovered);recovered.reset();
    } else {
        ProgramScope342 scope(data);
        auto a=native.programBuffer(k,&why);auto same=native.programBuffer(k,&why);CHECK(a && a==same);
        words[0]=0xfedcba98;auto changed=native.programBuffer(k,&why);CHECK(changed && changed!=a);
        CHECK(*static_cast<const uint32_t*>(a->contents())==0x12345678);
        CHECK(*static_cast<const uint32_t*>(changed->contents())==0xfedcba98);
        CHECK(data.program.resident.calls==3 && data.program.resident.ok==2 && data.program.resident.skipped==1);
        CHECK(data.program.counts[3]==1 && data.program.counts[4]==2 && data.program.counts[5]==2);
        CHECK(data.program.counts[12]==512 && data.program.resident.flags==0);
    }
    close(q,d,events);
}
void draw342() {
    Events events;auto* d=device(events);auto* q=queue(d,false);auto& native=*q->control->storage->queue;
    TextureDesc desc;desc.width=64;desc.height=64;desc.format=PixelFormat::kRGBA8Unorm;
    desc.usage=kTextureUsageRenderTarget|kTextureUsageRead;std::string why;
    auto target=Texture::make(*d->gpu,desc,&why);CHECK(target);
    Program program{kernels::tri_flat_vs_air,kernels::tri_flat_fs_air,Linkage{},"342-flat"};
    RenderPass pass;pass.color0=target.get();Draw draw;draw.vertexCount=3;draw.viewport=Viewport{0,0,64,64,0,1};
    for (unsigned round=0;round<2;round++) {
        gauguin342::DrawData data;auto cb=native.commandBuffer();CHECK(cb);
        {
            ProgramScope342 scope(data);
            for (unsigned i=0;i<3;i++) CHECK(cb->draw(program,pass,draw,hakios::metal::Bindings{},hakios::metal::Bindings{}));
        }
        auto& p=data.program;
        CHECK(data.render.calls==3 && data.render.ok==3 && data.render.flags==0);
        CHECK(p.address.calls==6 && p.address.ok==2 && p.address.skipped==4 && p.address.flags==0);
        CHECK(p.counts[0]==4 && p.counts[1]==2 && p.table.calls==3 && p.table.ok==3);
        CHECK(p.resident.calls==2 && p.piece.calls>=3 && p.pool.calls>0);
        CHECK(p.resident.ok==(round?0u:2u) && p.resident.skipped==(round?2u:0u));
        CHECK(p.resident.flags==0 && p.table.flags==0 && p.piece.flags==0 && p.pool.flags==0);
        uint64_t addressNs342=0;for (auto n:p.address.ns) addressNs342+=n;
        CHECK(addressNs342+p.table.ns[0]<=data.render.ns[2]);
        cb->commit();cb->waitUntilCompleted();CHECK(cb->status()==CommandBuffer::kCompleted);cb.reset();
    }
    target.reset();close(q,d,events);
}
}
int main(int argc,char** argv) {
    CHECK(argc==2);const std::string name=argv[1];
    if(name=="diag-pool") pool342();
    else if(name=="diag-resident") resident342(false);
    else if(name=="diag-failure") resident342(true);
    else if(name=="diag-draw") draw342();
    else return workspace342_dispatch(argc,argv);
    std::printf("PASS342 %s\n",name.c_str());return 0;
}
