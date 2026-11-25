"""Exact reversible0340 timing and worker-owned CPU scratch transformations."""
from core_prof339_patch import matching


def patch(raw,name):
    edits=[]
    def replace(old,new,count=1):
        nonlocal raw
        assert raw.count(old)==count,(name,old,raw.count(old),count)
        raw=raw.replace(old,new);edits.append((old,new,count))
    def part(marker):
        begin=raw.index(marker);brace=raw.index('{',begin)
        return begin,matching(raw,brace,'{','}')+1
    if name=='src/c_api.cpp':
        replace('#include "Recording339.hpp"','#include "Recording340.hpp"')
        for old,new in [('gauguin339','gauguin340'),('trace339','trace340'),('queued339','queued340'),('waited339','waited340'),('observedJob339','observedJob340')]:
            replace(old,new,raw.count(old))
        replace('namespace gauguin340 { __attribute__((visibility("hidden"))) thread_local SubmitData* activeSubmit=nullptr; }',
'''namespace gauguin340 {
__attribute__((visibility("hidden"))) thread_local SubmitData* activeSubmit=nullptr;
__attribute__((visibility("hidden"))) thread_local Workspace* activeWorkspace=nullptr;
__attribute__((visibility("hidden"))) thread_local uint64_t activeJobSequence=0;
__attribute__((visibility("hidden"))) thread_local DrawData* activeDraw=nullptr;
__attribute__((visibility("hidden"))) thread_local FineSubmitData* activeGpu=nullptr;
}''')
        replace('        gauguin340::WorkMeter meter;','        gauguin340::WorkMeter meter;\n        gauguin340::Workspace workspace;')
        replace('            try { job.f(); } catch (...) { recordingFailed(job.cb);failed=true; }',
                '            try { gauguin340::WorkspaceScope workspace340(state->workspace,job.sequence); job.f(); } catch (...) { recordingFailed(job.cb);failed=true; }')
        begin,end=part('int drawCommon(');old=raw[begin:end];new=old
        def draw(a,b):
            nonlocal new
            assert new.count(a)==1,a;new=new.replace(a,b)
        brace=new.index('{');new=new[:brace+1]+'''
    gauguin340::DrawScope draw340(cb->trace340.enabled.load(std::memory_order_acquire)?&cb->trace340.draw:nullptr);'''+new[brace+1:]
        draw('''    auto table = [](hakios_metal_buffer* const* buffers, const uint64_t* offsets, unsigned count) {
        Bindings b;''','''    gauguin340::DrawLease reusable340(draw340.reuse());
    Bindings& vsb=reusable340.get().vs;
    Bindings& fsb=reusable340.get().fs;
    draw340.phase(1);
    auto table = [](Bindings& b, hakios_metal_buffer* const* buffers, const uint64_t* offsets, unsigned count) {''')
        draw('''        return b;
    };
    Bindings vsb = table(vsBuffers, vsOffsets, vsCount);''','''    };
    table(vsb,vsBuffers,vsOffsets,vsCount);''')
        draw('    Bindings fsb = table(fsBuffers, fsOffsets, fsCount);','    draw340.phase(2);\n    table(fsb,fsBuffers,fsOffsets,fsCount);')
        draw('    std::vector<std::shared_ptr<const void>> members;','    draw340.phase(3);\n    auto& members=reusable340.get().members;')
        draw('    const RenderPass rp = passOf(pass);','    draw340.phase(4);\n    const RenderPass rp = passOf(pass);')
        draw('    if (!cb->cb->draw(p->program->program, rp, d, vsb, fsb)) {','    draw340.phase(5);\n    if (!cb->cb->draw(p->program->program, rp, d, vsb, fsb)) {')
        draw('    // the bound buffers live until the GPU has read them, whatever the caller frees meanwhile','    draw340.phase(6);\n    // the bound buffers live until the GPU has read them, whatever the caller frees meanwhile')
        draw('    return 0;','    draw340.phase(7);draw340.complete();\n    return 0;')
        replace(old,new)
    elif name=='src/command.cpp':
        replace('#include "Recording339.hpp"','#include "Recording340.hpp"')
        replace('gauguin339','gauguin340',raw.count('gauguin339'))
    elif name=='src/render.cpp':
        replace('#include "hakios-metal/command.hpp"','#include "hakios-metal/command.hpp"\n#include "Recording340.hpp"')
        begin,end=part('bool CommandBuffer::draw(');old=raw[begin:end];new=old
        def render(a,b):
            nonlocal new
            assert new.count(a)==1,a;new=new.replace(a,b)
        brace=new.index('{');new=new[:brace+1]+'''
    gauguin340::TimeProbe<8> render340(gauguin340::activeDraw?&gauguin340::activeDraw->render:nullptr);'''+new[brace+1:]
        render('    Bindings vsWithNull, fsWithNull;','    render340.phase(1);\n    Bindings vsWithNull, fsWithNull;')
        render('    const uint64_t vsProgram = programAddress(program.vs.k, &why);','    render340.phase(2);\n    const uint64_t vsProgram = programAddress(program.vs.k, &why);')
        render('    bool joins = open_ != nullptr','    render340.phase(3);\n    bool joins = open_ != nullptr')
        render('    if (!render::encodeInPass(body, program','    render340.phase(4);\n    if (!render::encodeInPass(body, program')
        render('''    if (!joins) {
        {
            const Texture* first''','''    render340.phase(5);
    if (!joins) {
        {
            const Texture* first''')
        render('    // a stage with device buffers may write them (ldib\'s table is stib\'s): its whole table is used for writing',
               '    render340.phase(6);\n    // a stage with device buffers may write them (ldib\'s table is stib\'s): its whole table is used for writing')
        render('    return true;','    render340.phase(7);render340.complete();\n    return true;')
        replace(old,new)
    elif name=='src/gpu.cpp':
        replace('#include "hakios-metal/gpu.hpp"','#include "hakios-metal/gpu.hpp"\n#include "Recording340.hpp"')
        begin,end=part('int Gpu::submit(');old=raw[begin:end];new=old
        brace=new.index('{');new=new[:brace+1]+'''
    gauguin340::TimeProbe<5> gpu340(gauguin340::activeGpu?&gauguin340::activeGpu->stages:nullptr);'''+new[brace+1:]
        a=new.index('    std::vector<MsmSubmitBo> bos;');z=new.index('    MsmSubmitCmd cmd{};',a)
        new=new[:a]+'''    gpu340.phase(1);
    gauguin340::SubmitLease reusable340(gauguin340::activeGpu?&gauguin340::activeGpu->reuse:nullptr);
    auto& bos=reusable340.get();
    reusable340.seed(MsmSubmitBo{kSubmitBoRead,commands.handle(),commands.gpuAddress()},
                     uses.size()<gauguin340::boCapacity?uses.size()+1:gauguin340::boCapacity);
    for (const BoUse& u:uses) {
        if (u.bo==&commands) continue;
        reusable340.add(MsmSubmitBo{u.write?kSubmitBoWrite:kSubmitBoRead,u.bo->handle(),u.bo->gpuAddress()});
    }
    if (auto* profile=gauguin340::activeGpu) {
        profile->uses=uses.size();profile->unique=bos.size();profile->comparisons=reusable340.comparisons;
        profile->mode=reusable340.mode();profile->reserveFailures=reusable340.reserveFailures;
    }
    gpu340.phase(2);
'''+new[z:]
        a='    int e = t_->call(kGemSubmit, &s, sizeof(s));';assert new.count(a)==1
        new=new.replace(a,'    gpu340.phase(3);\n'+a+'\n    gpu340.phase(4);')
        assert new.count('    return e;')==1;new=new.replace('    return e;','    gpu340.complete();\n    return e;')
        replace(old,new)
    elif name=='src/iokit_transport.cpp':
        replace('#include "GauguinFaultQueryCache.hpp"','#include "GauguinFaultQueryCache.hpp"\n#include "Recording340.hpp"')
        replace('        kern_return_t r = IOConnectCallStructMethod(c_, request, data, size, data, &returned);',
'''        kern_return_t r;
        {
            gauguin340::IoProbe io340(request==kGemSubmit?gauguin340::activeGpu:nullptr);
            r=IOConnectCallStructMethod(c_,request,data,size,data,&returned);
        }''')
    else:raise ValueError(name)
    return raw,edits


def reverse(original,candidate,edits):
    for old,new,count in reversed(edits):
        assert candidate.count(new)==count,(new,count,candidate.count(new))
        candidate=candidate.replace(new,old)
    assert candidate==original
