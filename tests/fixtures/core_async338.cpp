// Actual C API and FakeGpu; reuse the established ownership fixture primitives.
#define main ownership_fixture_main
#pragma clang diagnostic push
// The imported main's implicit return0 is special only while it is named main.
// Its renamed dispatch function is never called by this fixture.
#pragma clang diagnostic ignored "-Wreturn-type"
#include "metal_owned_recording.cpp"
#pragma clang diagnostic pop
#undef main
#include <array>

namespace {
struct Results338 {
    std::mutex mutex;
    std::vector<unsigned> notifications, completions;
    Results338() { notifications.reserve(32);completions.reserve(32); }
};
struct Context338 {
    unsigned id;
    Results338& results;
    Signal notified,completed;
    std::thread::id notifyingThread;
    hakios_metal_queue* releaseQueue=nullptr;
    hakios_metal_device* releaseDevice=nullptr;
    bool releaseInCompletion=false,releaseInNotice=false;
    bool requireError=false;
    Context338(unsigned value,Results338& target) : id(value),results(target) {}
};
void recordNotice338(hakios_metal_cb* cb,void* pointer) {
    auto& c=*static_cast<Context338*>(pointer);
    const auto status=hakios_metal_cb_status(cb);
    CHECK(status>=HAKIOS_METAL_COMMITTED);
    c.notifyingThread=std::this_thread::get_id();
    {std::lock_guard<std::mutex> lock(c.results.mutex);c.results.notifications.push_back(c.id);}
    if (c.releaseInNotice) {
        hakios_metal_cb_free(cb);hakios_metal_queue_free(c.releaseQueue);hakios_metal_close(c.releaseDevice);
    }
    c.notified.set();
}
void recordCompletion338(hakios_metal_cb* cb,void* pointer) {
    auto& c=*static_cast<Context338*>(pointer);
    // Raw atomic status allows the forced completion-before-notification case.
    CHECK(cb->cb->status()==(c.requireError?CommandBuffer::kError:CommandBuffer::kCompleted));
    {std::lock_guard<std::mutex> lock(c.results.mutex);c.results.completions.push_back(c.id);}
    if (c.releaseInCompletion) {
        hakios_metal_cb_free(cb);hakios_metal_queue_free(c.releaseQueue);hakios_metal_close(c.releaseDevice);
    }
    c.completed.set();
}
void blockedFrontend338() {
    Events events;auto* d=device(events);auto* q=queue(d);auto* a=hakios_metal_cb_new(q);auto* b=hakios_metal_cb_new(q);
    Results338 results;Context338 ac{1,results},bc{2,results};Gate gate;
    auto* buffer=hakios_metal_buffer_new(d,64);CHECK(buffer);
    CHECK(hakios_metal_cb_fill(a,buffer,0,64,1)==0);CHECK(hakios_metal_cb_fill(b,buffer,0,64,2)==0);
    hakios_metal_buffer_free(buffer);
    a->deferrer->post(a,[&]{gate.block();});CHECK(gate.entered.wait());
    hakios_metal_cb_commit(a,recordCompletion338,&ac);hakios_metal_cb_notify_recorded338(a,recordNotice338,&ac);
    hakios_metal_cb_commit(b,recordCompletion338,&bc);hakios_metal_cb_notify_recorded338(b,recordNotice338,&bc);
    // Both frontend admissions return while the actual recorder remains gated.
    CHECK(!ac.notified.value && !bc.notified.value);CHECK(a->pending.load()>0 && b->pending.load()>0);
    // Public CB free intentionally waits on non-worker callers; keep those
    // owners until terminal callbacks. Queue/device wrappers can go now.
    hakios_metal_queue_free(q);hakios_metal_close(d);
    gate.release.set();CHECK(ac.notified.wait() && bc.notified.wait());
    CHECK(ac.completed.wait() && bc.completed.wait());
    hakios_metal_cb_free(a);hakios_metal_cb_free(b);CHECK(events.destroyed.wait());
    CHECK((results.notifications==std::vector<unsigned>{1,2}));CHECK((results.completions==std::vector<unsigned>{1,2}));
}
void completionFirst338() {
    Events events;auto* d=device(events);auto* q=queue(d);auto* cb=hakios_metal_cb_new(q);
    Results338 results;Context338 c{1,results};Gate before,gate;
    c.releaseInCompletion=true;c.releaseQueue=q;c.releaseDevice=d;
    cb->deferrer->post(cb,[&]{before.block();});CHECK(before.entered.wait());
    hakios_metal_cb_commit(cb,recordCompletion338,&c);
    cb->deferrer->post(cb,[&]{gate.block();});
    hakios_metal_cb_notify_recorded338(cb,recordNotice338,&c);
    before.release.set();
    CHECK(gate.entered.wait());CHECK(c.completed.wait());CHECK(!c.notified.value);
    gate.release.set();CHECK(c.notified.wait());CHECK(events.destroyed.wait());
    CHECK(results.notifications.size()==1 && results.completions.size()==1);
}
void callbackOwner338(bool deferred,int failure,bool noticeRelease) {
    Events events;auto* d=device(events);auto* q=queue(d,deferred);auto* cb=hakios_metal_cb_new(q);
    auto* b=hakios_metal_buffer_new(d,64);CHECK(b);CHECK(hakios_metal_cb_fill(cb,b,0,64,3)==0);hakios_metal_buffer_free(b);
    Results338 results;Context338 c{1,results};c.requireError=failure!=0;
    c.releaseQueue=q;c.releaseDevice=d;c.releaseInNotice=noticeRelease;
    if (failure==3) CHECK(hakios_metal_cb_refuse(cb,"338 ordered refusal")==-1);
    else if (failure==4) cb->deferrer->post(cb,[]{throw std::runtime_error("338 recording exception");});
    else events.failure=failure;
    hakios_metal_cb_commit(cb,recordCompletion338,&c);hakios_metal_cb_notify_recorded338(cb,recordNotice338,&c);
    CHECK(c.notified.wait() && c.completed.wait());
    if (!noticeRelease) {hakios_metal_cb_free(cb);close(q,d,events);}
    CHECK(events.destroyed.wait());CHECK(results.notifications.size()==1 && results.completions.size()==1);
}
void notificationAllocation338() {
    Events events;auto* d=device(events);auto* q=queue(d);auto* cb=hakios_metal_cb_new(q);
    Gate gate;cb->deferrer->post(cb,[&]{gate.block();});CHECK(gate.entered.wait());
    Results338 results;Context338 c{1,results};Signal entering;
    hakios_metal_cb_commit(cb,recordCompletion338,&c);
    std::thread notifier([&]{
        rejectAllocation=true;entering.set();
        hakios_metal_cb_notify_recorded338(cb,recordNotice338,&c);
        rejectAllocation=false;
    });
    const auto caller=notifier.get_id();CHECK(entering.wait());gate.release.set();notifier.join();
    CHECK(c.notified.wait() && c.completed.wait());CHECK(c.notifyingThread==caller);
    CHECK(hakios_metal_cb_error(cb)[0]==0);CHECK(cb->pending.load()==0);
    hakios_metal_cb_free(cb);close(q,d,events);
    CHECK(results.notifications.size()==1 && results.completions.size()==1);
}
void meter338() {
    gauguin338::WorkMeter meter;CHECK(meter.snapshot(90)==0);
    meter.begin(100);CHECK(meter.snapshot(125)==25);const uint64_t prefix=meter.snapshot(125);
    meter.finish(160);CHECK(meter.snapshot(200)==60);meter.retire(160);
    CHECK(meter.completed-prefix==35);CHECK(200-125-(meter.completed-prefix)==40);
    meter.begin(200);meter.finish(220);meter.retire(220);CHECK(meter.completed==80);
    gauguin338::Trace trace;trace.identify(1,225000000,1,0);trace.identify(1,225000000,1,3);
    gauguin338::observe(trace,0,1,100,200,300,50,0,false);
    CHECK(trace.jobs==1 && trace.execution==100 && trace.queueSum==100 && trace.queueMax==100);
    CHECK(trace.ticket.load()==3);
}
}
int main(int argc,char** argv) {
    CHECK(argc==2);const std::string s=argv[1];
    if (s=="blocked-front") blockedFrontend338();
    else if (s=="completion-first") completionFirst338();
    else if (s=="notification-allocation") notificationAllocation338();
    else if (s=="meter") meter338();
    else if (s=="notice-owner-release") callbackOwner338(true,0,true);
    else if (s=="synchronous") callbackOwner338(false,0,false);
    else if (s=="success") callbackOwner338(true,0,false);
    else if (s=="allocation") callbackOwner338(true,1,false);
    else if (s=="submission") callbackOwner338(true,2,false);
    else if (s=="refusal") callbackOwner338(true,3,false);
    else if (s=="worker-exception") callbackOwner338(true,4,false);
    else {CHECK(false);}
    std::printf("PASS338 %s\n",s.c_str());return 0;
}
