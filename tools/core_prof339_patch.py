"""Exact reversible diagnostics on the consumed0338 C API/command sources."""
import re

CATEGORIES={
    'hakios_metal_cb_copy':'Transfer','hakios_metal_cb_fill':'Transfer',
    'hakios_metal_cb_blit':'Transfer','hakios_metal_cb_blit_rotated':'Transfer',
    'hakios_metal_cb_generate_mipmaps':'Transfer','hakios_metal_cb_append':'Transfer',
    'hakios_metal_cb_dispatch2':'Compute','hakios_metal_cb_dispatch_indirect':'Compute',
    'hakios_metal_cb_set_threadgroup_length':'Bindings','hakios_metal_cb_set_indirect':'Bindings',
    'hakios_metal_cb_set_vertex_textures':'Bindings','hakios_metal_cb_draw2':'Render',
    'hakios_metal_cb_draw3':'Render','hakios_metal_cb_draw_indexed':'Render',
    'hakios_metal_cb_clear':'Clear',
}


def matching(text,start,left,right):
    assert text[start]==left
    i=start;depth=0;quote=None;comment=None
    while i<len(text):
        c=text[i];next=text[i:i+2]
        if comment=='line':
            if c=='\n':comment=None
        elif comment=='block':
            if next=='*/':comment=None;i+=1
        elif quote:
            if c=='\\':i+=1
            elif c==quote:quote=None
        elif next=='//':comment='line';i+=1
        elif next=='/*':comment='block';i+=1
        elif c in ('"',"'"):quote=c
        elif c==left:depth+=1
        elif c==right:
            depth-=1
            if not depth:return i
        i+=1
    raise ValueError('unmatched source delimiter')


def function(text,name):
    hits=list(re.finditer(r'^(?:int|void) '+re.escape(name)+r'\(',text,re.M))
    assert len(hits)==1,name
    begin=hits[0].start();brace=text.index('{',hits[0].end())
    return begin,matching(text,brace,'{','}')+1


def patch(raw,name):
    edits=[];audit={}
    def replace(old,new):
        nonlocal raw
        assert raw.count(old)==1,(name,old)
        raw=raw.replace(old,new);edits.append((old,new))
    if name=='src/c_api.cpp':
        replace('#include "Recording338.hpp"','#include "Recording339.hpp"\nnamespace gauguin339 { __attribute__((visibility("hidden"))) thread_local SubmitData* activeSubmit=nullptr; }')
        replace('void observedJob338(hakios_metal_cb*,unsigned,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,bool) noexcept;',
'''void queued339(hakios_metal_cb*,uint64_t,const gauguin339::Values&) noexcept;
gauguin339::Values waited339(hakios_metal_cb*,uint64_t,const gauguin339::Values&,uint64_t) noexcept;
void observedJob339(hakios_metal_cb*,unsigned,unsigned,uint64_t,uint64_t,uint64_t,uint64_t,uint64_t,const gauguin339::Values&,bool) noexcept;''')
        replace('        unsigned kind=0;','        unsigned kind=0,category=gauguin339::Control;')
        replace('        gauguin338::WorkMeter meter;','        gauguin339::WorkMeter meter;')
        replace('    void post(hakios_metal_cb* cb, std::function<void()> f, unsigned kind=0, bool marksRecording=true) {',
'''    void post(hakios_metal_cb* cb, std::function<void()> f, unsigned kind=0, bool marksRecording=true,
              unsigned category=gauguin339::Control) {''')
        replace('        job.kind=kind;','''        job.kind=kind;
        job.category=kind==1?gauguin339::Commit:(kind==2?gauguin339::Notify:category);''')
        replace('            admitted.busyPrefix=state->meter.snapshot(admitted.enqueued);',
'''            admitted.busyPrefix=state->meter.snapshot(admitted.enqueued);
            if (kind==1) queued339(cb,admitted.sequence,state->meter.snapshotCategories(admitted.enqueued));''')
        replace('            const uint64_t busyWait=state->meter.completed-job.busyPrefix;',
'''            const uint64_t busyWait=state->meter.completed-job.busyPrefix;
            const auto byClass=job.kind==1?waited339(job.cb,job.sequence,state->meter.completedByClass,busyWait):gauguin339::Values{};''')
        replace('            state->meter.begin(began);','            state->meter.begin(began,job.category);')
        replace('            observedJob338(job.cb,job.kind,job.sequence,job.enqueued,began,ended,busyWait,failed);',
'''            observedJob339(job.cb,job.kind,job.category,job.sequence,job.enqueued,began,ended,busyWait,byClass,failed);''')
        replace('    int invoke(hakios_metal_cb* cb, std::function<int()> f) {',
                '    int invoke(hakios_metal_cb* cb, std::function<int()> f, unsigned category=gauguin339::Control) {')
        replace('            call->done.notify_all();\n        });',
                '            call->done.notify_all();\n        },0,true,category);')
        replace('    gauguin338::Trace trace338;','    gauguin339::Trace trace339;')
        replace('''void observedJob338(hakios_metal_cb* cb,unsigned kind,uint64_t sequence,uint64_t enqueued,
                    uint64_t began,uint64_t ended,uint64_t busyWait,bool failed) noexcept {
    gauguin338::observe(cb->trace338,kind,sequence,enqueued,began,ended,busyWait,
                        unsigned(cb->cb->status()),failed);
}''','''void queued339(hakios_metal_cb* cb,uint64_t sequence,const gauguin339::Values& prefix) noexcept {
    cb->trace339.queued(sequence,prefix);
}
gauguin339::Values waited339(hakios_metal_cb* cb,uint64_t sequence,const gauguin339::Values& completed,uint64_t scalar) noexcept {
    return cb->trace339.waited(sequence,completed,scalar);
}
void observedJob339(hakios_metal_cb* cb,unsigned kind,unsigned category,uint64_t sequence,uint64_t enqueued,
                    uint64_t began,uint64_t ended,uint64_t busyWait,const gauguin339::Values& byClass,bool failed) noexcept {
    gauguin339::observe(cb->trace339,kind,category,sequence,enqueued,began,ended,busyWait,byClass,
                        unsigned(cb->cb->status()),failed);
}''')
        replace('    if (callback != nullptr) {\n        cb->cb->addCompletedHandler',
                '    gauguin339::SubmitScope submitScope339(cb->trace339);\n    if (callback != nullptr) {\n        cb->cb->addCompletedHandler')
        replace('    if (cb) cb->trace338.identify(object,made_us,queue,ticket);',
                '    if (cb) cb->trace339.identify(object,made_us,queue,ticket);')
        for api,category in CATEGORIES.items():
            begin,end=function(raw,api);old=raw[begin:end];changed=old;count=0
            calls=list(re.finditer(r'cb->deferrer->(post|invoke)\(',old))
            assert calls,api
            for call in reversed(calls):
                close=matching(old,call.end()-1,'(',')')
                suffix=(',0,true,gauguin339::' if call[1]=='post' else ',gauguin339::')+category
                changed=changed[:close]+suffix+changed[close:];count+=1
            replace(old,changed);audit[api]=dict(category=category,calls=count)
    elif name=='src/command.cpp':
        replace('#include <map>','#include <map>\n#include "Recording339.hpp"')
        begin=raw.index('void CommandQueue::submit(std::shared_ptr<CommandBuffer> cb) {')
        brace=raw.index('{',begin);end=matching(raw,brace,'{','}')+1;old=raw[begin:end];changed=old
        points=[
            ('void CommandQueue::submit(std::shared_ptr<CommandBuffer> cb) {',
             'void CommandQueue::submit(std::shared_ptr<CommandBuffer> cb) {\n    gauguin339::SubmitProbe probe339;'),
            ('        completeError(std::move(cb)); // no GPU work; same completion FIFO in deferred mode',
             '        probe339.phase(gauguin339::Publication);probe339.outcome(1);\n        completeError(std::move(cb)); // no GPU work; same completion FIFO in deferred mode'),
            ('    cb->closePass();   // the last pass\'s tail','    probe339.phase(gauguin339::PassTail);\n    cb->closePass();   // the last pass\'s tail'),
            ('    cb->commands_ = takeCommandBo(4 * w.size(), &error);','    probe339.phase(gauguin339::CommandBo);\n    cb->commands_ = takeCommandBo(4 * w.size(), &error);'),
            ('    if (cb->commands_ == nullptr) {','    if (cb->commands_ == nullptr) {\n        probe339.phase(gauguin339::Publication);probe339.outcome(2);'),
            ('    memcpy(cb->commands_->cpu(), w.data(), 4 * w.size());','    probe339.phase(gauguin339::CommandCopy);\n    memcpy(cb->commands_->cpu(), w.data(), 4 * w.size());\n    probe339.phase(gauguin339::QueueLock);'),
            ('    cb->status_ = CommandBuffer::kCommitted;','    probe339.phase(gauguin339::FaultQuery);\n    cb->status_ = CommandBuffer::kCommitted;'),
            ('    int e = gpu_.submit(id_, *cb->commands_, 0, uint32_t(w.size()), cb->uses_, &cb->fence_);',
             '    probe339.phase(gauguin339::NativeSubmit);\n    int e = gpu_.submit(id_, *cb->commands_, 0, uint32_t(w.size()), cb->uses_, &cb->fence_);\n    probe339.phase(gauguin339::Publication);'),
            ('    if (e != 0) {','    if (e != 0) {\n        probe339.outcome(3);'),
            ('    changed_.notify_all();','    changed_.notify_all();\n    probe339.outcome(0);'),
        ]
        for before,after in points:
            assert changed.count(before)==1,before;changed=changed.replace(before,after)
        replace(old,changed)
    else:raise ValueError(name)
    return raw,edits,audit


def check_reverse(original,changed,edits):
    for old,new in reversed(edits):
        assert changed.count(new)==1
        changed=changed.replace(new,old)
    assert changed==original
