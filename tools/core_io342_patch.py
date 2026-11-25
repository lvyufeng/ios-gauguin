"""Reversible user diagnostics over the exact qualified341 core."""
from core_prof339_patch import matching

def patch(raw,name):
    edits=[]
    def replace(old,new,count=1):
        nonlocal raw
        assert raw.count(old)==count,(name,old,raw.count(old));raw=raw.replace(old,new);edits.append((old,new,count))
    for old,new in [('Recording341.hpp','Recording342.hpp'),('gauguin341','gauguin342'),('trace341','trace342'),
        ('queued341','queued342'),('waited341','waited342'),('observedJob341','observedJob342'),('draw341','draw342'),
        ('render341','render342'),('gpu341','gpu342'),('io341','io342'),('workspace341','workspace342'),
        ('reusable341','reusable342'),('detail341','detail342'),('address341','address342'),('resident341','resident342'),
        ('piece341','piece342'),('pool341','pool342'),('table341','table342'),('cpu341','cpu342')]:
        if raw.count(old):replace(old,new,raw.count(old))
    def once(s,a,b):assert s.count(a)==1,(name,a);return s.replace(a,b)
    def method(marker,fn):
        start=raw.index(marker);end=matching(raw,raw.index('{',start),'{','}')+1
        old=raw[start:end];replace(old,fn(old))
    if name=='src/command.cpp':
        def program(s):
            return once(s,'    std::shared_ptr<Buffer> b = newBuffer(',
                '    gauguin342::ProgramAllocationScope allocation342(detail342?&detail342->newBo:nullptr);\n    std::shared_ptr<Buffer> b = newBuffer(')
        method('std::shared_ptr<Buffer> CommandQueue::programBuffer(',program)
    elif name=='src/gpu.cpp':
        def allocation(s):
            s=once(s,'    *error = 0;', '''    *error = 0;
    gauguin342::NewBoScope allocation342(gauguin342::activeProgramBo,error,
        gauguin342::activeJobSequence,gauguin342::wall342,gauguin342::cpuNow);''')
            s=once(s,'    if ((*error = t_->call(kGemNew,','    allocation342.phase(1);\n    if ((*error = t_->call(kGemNew,')
            s=once(s,'    MsmGemInfo info{};', '    allocation342.identity(n.handle,n.size);allocation342.phase(2);\n    MsmGemInfo info{};')
            assert s.count('        DrmGemClose c{n.handle, 0};')==2
            s=s.replace('        DrmGemClose c{n.handle, 0};','        allocation342.phase(5);\n        DrmGemClose c{n.handle, 0};')
            s=once(s,'    void* cpu = t_->map(', '    allocation342.phase(3);\n    void* cpu = t_->map(')
            s=once(s,'    std::unique_ptr<Bo> bo(', '    allocation342.phase(4);\n    std::unique_ptr<Bo> bo(')
            return once(s,'    return bo;', '    allocation342.complete();\n    return bo;')
        method('std::unique_ptr<Bo> Gpu::newBo(',allocation)
        replace('''    int e = t_->call(kGemSubmit, &s, sizeof(s));''','''    if(auto* p=gauguin342::activeGpu){
        p->driverQueue=queue;p->commandHandle=commands.handle();p->commandOffset=offsetBytes;p->commandWords=words;
        if(!gauguin342::threadID(&p->thread))p->identityFlags|=1;
    }
    int e = t_->call(kGemSubmit, &s, sizeof(s));''')
        replace('''        *fence = s.fence;''','''        *fence = s.fence;
        if(auto* p=gauguin342::activeGpu)p->driverFence=s.fence;''')
    elif name not in ('src/c_api.cpp','src/render.cpp','src/iokit_transport.cpp'):raise ValueError(name)
    return raw,edits

def reverse(original,candidate,edits):
    for old,new,count in reversed(edits):
        assert candidate.count(new)==count;candidate=candidate.replace(new,old)
    assert candidate==original
