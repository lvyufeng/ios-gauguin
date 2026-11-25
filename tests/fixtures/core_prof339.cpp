// Includes the exact previous async scenarios (only dispatch main renamed).
#include "inherited-async338.inc"
#include "Recording339.hpp"
#include <cstring>

namespace {
uint64_t clock339=100;
uint64_t testClock339() {return clock339;}

void partition339() {
    using namespace gauguin339;
    WorkMeter meter;Trace trace;trace.identify(1,225000000,1,1);
    meter.begin(100,gauguin339::Bindings);CHECK(meter.snapshot(125)==25);
    CHECK(meter.snapshotCategories(125)[gauguin339::Bindings]==25);
    meter.finish(160);CHECK(meter.snapshotCategories(200)[gauguin339::Bindings]==60);meter.retire(160);
    meter.begin(200,Render);trace.queued(9,meter.snapshotCategories(225));
    meter.finish(260);meter.retire(260);
    meter.begin(300,Compute);meter.finish(340);meter.retire(340);
    const auto parts=trace.waited(9,meter.completedByClass,75);
    CHECK(parts[Render]==35 && parts[Compute]==40 && sum(parts)==75 && trace.flags.load()==0);
    trace.queued(10,{});CHECK(trace.flags.load()&badPrefix);
    Trace wrong;wrong.identify(2,225000000,1,2);wrong.queued(1,{});
    (void)wrong.waited(2,meter.completedByClass,75);CHECK(wrong.flags.load()&badPrefix);
}

void phases339(bool error) {
    using namespace gauguin339;
    Trace trace;trace.identify(1,225000000,1,1);clock339=100;
    {SubmitScope scope(trace);CHECK(activeSubmit==&trace.submit);
        {SubmitProbe probe(testClock339);
            if (error) {clock339=120;probe.phase(Publication);clock339=150;probe.outcome(2);}
            else {for (unsigned i=1;i<SubmitCount;i++) {clock339+=10;probe.phase(i);}clock339+=10;probe.outcome(0);}
        }
        CHECK(trace.submit.calls==1 && trace.submit.flags==0);
    CHECK(sum(trace.submit.elapsed)==trace.submit.endNs-trace.submit.beginNs);
    }
    CHECK(activeSubmit==nullptr);
    if (error) CHECK(trace.submit.mask==129 && trace.submit.elapsed[Entry]==20 && trace.submit.elapsed[Publication]==30);
    else {CHECK(trace.submit.mask==255 && sum(trace.submit.elapsed)==80);for (auto n:trace.submit.elapsed) CHECK(n==10);}
}

void nested339() {
    using namespace gauguin339;
    Trace outer,inner;outer.identify(1,225000000,1,1);inner.identify(2,225000000,1,2);
    {SubmitScope a(outer);CHECK(activeSubmit==&outer.submit);
        try {SubmitScope b(inner);SubmitProbe probe(testClock339);clock339+=20;throw std::runtime_error("unwind probe");}
        catch (const std::runtime_error&) {}
        CHECK(activeSubmit==&outer.submit && inner.submit.calls==1 && inner.submit.outcome==5);
        Trace disabled;
        {SubmitScope c(disabled);CHECK(activeSubmit==nullptr);SubmitProbe probe(testClock339);}
        CHECK(activeSubmit==&outer.submit);
    }
    CHECK(activeSubmit==nullptr);
}

void native339(int failure) {
    using namespace gauguin339;
    Events events;auto* d=device(events);auto* q=queue(d);auto* cb=hakios_metal_cb_new(q);
    cb->trace339.identify(0x1234,225000000,1,0);
    auto* b=hakios_metal_buffer_new(d,64);CHECK(b);
    CHECK(hakios_metal_cb_fill(cb,b,0,64,3)==0);hakios_metal_buffer_free(b);
    Results338 results;Context338 context{1,results};context.requireError=failure!=0;
    if (failure==3) CHECK(hakios_metal_cb_refuse(cb,"339 refusal")==-1);
    else if (failure==4) cb->deferrer->post(cb,[]{throw std::runtime_error("339 recording failure");});
    else events.failure=failure;
    cb->trace339.identify(0x1234,225000000,1,1);
    hakios_metal_cb_commit(cb,recordCompletion338,&context);
    hakios_metal_cb_notify_recorded338(cb,recordNotice338,&context);
    CHECK(context.notified.wait() && context.completed.wait());
    (void)hakios_metal_cb_status(cb); // drain before reading worker-only totals
    auto& trace=cb->trace339;
    CHECK(trace.counts[Transfer]==1 && trace.counts[Commit]==1 && trace.counts[Notify]==1);
    CHECK(sum(trace.counts)==trace.jobs && sum(trace.executionByClass)==trace.execution && trace.flags.load()==0);
    CHECK(trace.submit.calls==1 && trace.submit.flags==0);
    CHECK(sum(trace.submit.elapsed)==trace.submit.endNs-trace.submit.beginNs);
    CHECK(sum(trace.submit.elapsed)<=trace.executionByClass[Commit]);
    if (!failure) CHECK(trace.submit.mask==255 && trace.submit.outcome==0);
    else if (failure==1) CHECK(trace.submit.mask==135 && trace.submit.outcome==2);
    else if (failure==2) CHECK(trace.submit.mask==255 && trace.submit.outcome==3);
    else CHECK(trace.submit.mask==129 && trace.submit.outcome==1);
    Signal checked;
    cb->deferrer->post(cb,[&]{CHECK(activeSubmit==nullptr);checked.set();});CHECK(checked.wait());
    (void)hakios_metal_cb_status(cb);
    hakios_metal_cb_free(cb);close(q,d,events);
    CHECK(results.notifications.size()==1 && results.completions.size()==1);
}

void limits339() {
    using namespace gauguin339;
    Values maximum;maximum.fill(UINT64_MAX);
    Line line;line.add("%s","GAUGUIN CR339: ");
    line.values("counts",maximum);line.values("exec_ns",maximum);line.values("wait_ns",maximum);
    line.values("max_exec_ns",maximum);line.values("submit_ns",maximum);
    CHECK(line.valid && line.size<lineLimit);
    Line refused;refused.add("%s",std::string(lineLimit+1,'x').c_str());CHECK(!refused.valid);
    Trace overflow;overflow.identify(1,225000000,1,1);overflow.jobs=UINT64_MAX;overflow.counts[Control]=UINT64_MAX;
    observe(overflow,0,Control,1,1,2,3,0,{},0,false);CHECK(overflow.flags.load()&badCounter);
    records.store(recordLimit-1);std::vector<std::thread> writers;
    for (unsigned i=0;i<8;i++) writers.emplace_back([i]{
        Trace value;value.identify(100+i,225000000,1,1);
        observe(value,1,Commit,1,100,200,300,0,{},3,false);
    });
    for (auto& writer:writers) writer.join();CHECK(records.load()==recordLimit+1);
    records.store(UINT32_MAX);Trace noWrap;noWrap.identify(1,225000000,1,1);
    observe(noWrap,1,Commit,1,100,200,300,0,{},3,false);CHECK(records.load()==UINT32_MAX);
}

// Same members and ABI as the private Job declarations, with the new category
// occupying the padding preceding its existing uint64 sequence fields.
struct OldJobShape {CbLease lease;hakios_metal_cb* cb;std::atomic<int>* pending;std::function<void()> f;unsigned kind;uint64_t seq,enq,prefix;};
struct NewJobShape {CbLease lease;hakios_metal_cb* cb;std::atomic<int>* pending;std::function<void()> f;unsigned kind,category;uint64_t seq,enq,prefix;};
static_assert(sizeof(OldJobShape)==sizeof(NewJobShape));
}

int main(int argc,char** argv) {
    CHECK(argc==2);const std::string value=argv[1];
    if (value.rfind("old-",0)==0) {char* args[]={argv[0],argv[1]+4,nullptr};return inherited338_dispatch(2,args);}
    if (value=="partition") partition339();
    else if (value=="phases") phases339(false);
    else if (value=="early-phases") phases339(true);
    else if (value=="nested-unwind") nested339();
    else if (value=="success") native339(0);
    else if (value=="allocation") native339(1);
    else if (value=="submission") native339(2);
    else if (value=="refusal") native339(3);
    else if (value=="worker-exception") native339(4);
    else if (value=="limits") limits339();
    else CHECK(false);
    std::printf("PASS339 %s\n",value.c_str());return 0;
}
