"""Reversible diagnostic split over the exact qualified0340 implementation."""
from core_prof339_patch import matching


def patch(raw,name):
    edits=[]
    def replace(old,new,count=1):
        nonlocal raw
        assert raw.count(old)==count,(name,old,raw.count(old),count)
        raw=raw.replace(old,new);edits.append((old,new,count))
    def method(marker,transform):
        start=raw.index(marker);brace=raw.index('{',start)
        end=matching(raw,brace,'{','}')+1
        old=raw[start:end];replace(old,transform(old))
    def once(text,old,new):
        assert text.count(old)==1,(name,old);return text.replace(old,new)
    def begin(text,kind,var):
        at=text.index('{')+1
        return text[:at]+f'\n    auto* detail341=gauguin341::programData();\n    gauguin341::TimeProbe<{kind[1]}> {var}(detail341?&detail341->{kind[0]}:nullptr);'+text[at:]
    replace('#include "Recording340.hpp"','#include "Recording341.hpp"')
    for old,new in [('gauguin340','gauguin341'),('trace340','trace341'),('queued340','queued341'),
        ('waited340','waited341'),('observedJob340','observedJob341'),('draw340','draw341'),
        ('render340','render341'),('gpu340','gpu341'),('io340','io341'),('workspace340','workspace341'),('reusable340','reusable341')]:
        if raw.count(old):replace(old,new,raw.count(old))
    if name=='src/command.cpp':
        def address(s):
            s=begin(s,('address',4),'address341')
            s=once(s,'        if (same(it->second)) return it->second.gpuAddress;',
                '''        gauguin341::programCount(detail341,2);
        if (same(it->second)) {
            gauguin341::programCount(detail341,0);address341.skip();return it->second.gpuAddress;
        }''')
            s=once(s,'    (void)n;','    gauguin341::programCount(detail341,1);\n    address341.phase(1);\n    (void)n;')
            s=once(s,'    use(*b, false);','    address341.phase(2);\n    use(*b, false);')
            s=once(s,'    uploaded_.emplace(', '    address341.phase(3);\n    uploaded_.emplace(')
            s=once(s,'    return b->gpuAddress();','    gauguin341::programCount(detail341,11,4ull*k.numWords);\n    address341.complete();\n    return b->gpuAddress();')
            return s
        method('uint64_t CommandBuffer::programAddress(',address)
        def resident(s):
            s=begin(s,('resident',5),'resident341')
            s=once(s,'    const auto [first, last]', '    resident341.phase(1);\n    const auto [first, last]')
            s=once(s,'        const Resident& r = it->second;', '        gauguin341::programCount(detail341,5);\n        const Resident& r = it->second;')
            s=once(s,'        if (r.words.size() == k.numWords && std::memcmp(r.words.data(), k.words, 4ull * k.numWords) == 0) return r.buffer;',
                '''        if (r.words.size() == k.numWords && std::memcmp(r.words.data(), k.words, 4ull * k.numWords) == 0) {
            gauguin341::programCount(detail341,3);resident341.skip();return r.buffer;
        }''')
            s=once(s,'    // (past 64 MB of programs,', '    gauguin341::programCount(detail341,4);\n    // (past 64 MB of programs,')
            s=once(s,'    std::shared_ptr<Buffer> b = newBuffer(', '    resident341.phase(2);\n    std::shared_ptr<Buffer> b = newBuffer(')
            s=once(s,'    memcpy(b->contents(),','    resident341.phase(3);\n    memcpy(b->contents(),')
            s=once(s,'    return b;', '    gauguin341::programCount(detail341,12,4ull*k.numWords);\n    resident341.phase(4);resident341.complete();\n    return b;')
            return s
        method('std::shared_ptr<Buffer> CommandQueue::programBuffer(',resident)
        def piece(s):
            s=begin(s,('piece',4),'piece341')
            s=once(s,'    if (bytes > kSlabBytes / 4) {','    piece341.phase(1);\n    if (bytes > kSlabBytes / 4) {\n        gauguin341::programCount(detail341,8);')
            s=once(s,'            slab_ = queue_.takeSlab(', '            gauguin341::programCount(detail341,7);\n            slab_ = queue_.takeSlab(')
            s=once(s,'            if (slab_ != nullptr) slabs_.push_back(slab_);\n        }','            if (slab_ != nullptr) slabs_.push_back(slab_);\n        } else {gauguin341::programCount(detail341,6);}')
            s=once(s,'    if (out->buffer == nullptr) {', '    piece341.phase(2);\n    if (out->buffer == nullptr) {')
            s=once(s,'    if (out->offset == 0) {', '    piece341.phase(3);\n    if (out->offset == 0) {')
            s=once(s,'    return true;', '    piece341.complete();\n    return true;')
            return s
        method('bool CommandBuffer::piece(',piece)
        def pool(s):
            s=begin(s,('pool',6),'pool341')
            s=once(s,'        auto it = freeBuffers_.find(size);', '        pool341.phase(1);\n        auto it = freeBuffers_.find(size);')
            s=once(s,'    if (b == nullptr) return newBuffer(gpu_, size, why);',
                '''    pool341.phase(2);
    if (b == nullptr) {
        gauguin341::programCount(detail341,10);
        auto fresh341=newBuffer(gpu_,size,why);
        pool341.phase(3);pool341.phase(4);pool341.phase(5);
        if (fresh341) pool341.complete();
        return fresh341;
    }
    pool341.phase(3);gauguin341::programCount(detail341,9);''')
            s=once(s,'    return b;', '    pool341.phase(4);gauguin341::programCount(detail341,13,size);\n    pool341.phase(5);pool341.complete();\n    return b;')
            return s
        method('std::shared_ptr<Buffer> CommandQueue::takeBuffer(',pool)
    elif name=='src/render.cpp':
        replace('''    Piece table;
    if (!piece(render::kTableBytes, &table, &why)) {
        return fail(std::string("no memory for the draw's table: ") + why);
    }''','''    Piece table;
    {
        auto* detail341=gauguin341::programData();
        gauguin341::TimeProbe<1> table341(detail341?&detail341->table:nullptr);
        if (!piece(render::kTableBytes, &table, &why)) {
            return fail(std::string("no memory for the draw's table: ") + why);
        }
        table341.complete();
    }''')
    elif name=='src/iokit_transport.cpp':
        replace('''            gauguin341::IoProbe io341(request==kGemSubmit?gauguin341::activeGpu:nullptr);
            r=IOConnectCallStructMethod(c_,request,data,size,data,&returned);''',
'''            gauguin341::CpuProbe cpu341(request==kGemSubmit?gauguin341::activeGpu:nullptr);
            {
                gauguin341::IoProbe io341(request==kGemSubmit?gauguin341::activeGpu:nullptr);
                r=IOConnectCallStructMethod(c_,request,data,size,data,&returned);
            }''')
    elif name not in ('src/c_api.cpp','src/gpu.cpp'):raise ValueError(name)
    return raw,edits


def reverse(original,candidate,edits):
    for old,new,count in reversed(edits):
        assert candidate.count(new)==count,(new,count,candidate.count(new))
        candidate=candidate.replace(new,old)
    assert candidate==original
