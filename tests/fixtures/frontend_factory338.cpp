#define main imported_ownership_main338
#pragma clang diagnostic push
#pragma clang diagnostic ignored "-Wreturn-type"
#include "metal_owned_recording.cpp"
#pragma clang diagnostic pop
#undef main
struct FrontFactory338 {
    Events events;
    hakios_metal_device* d=deviceOn(std::make_unique<CountingFake>(events));
    hakios_metal_queue* q=queue(d);
    Gate gate;
};
extern "C" {
void* front_factory338(hakios_metal_device** deviceOut,hakios_metal_queue** queueOut) {
    auto* f=new FrontFactory338;*deviceOut=f->d;*queueOut=f->q;return f;
}
void front_block338(void* pointer,hakios_metal_cb* cb) {
    auto* f=static_cast<FrontFactory338*>(pointer);
    cb->deferrer->post(cb,[f]{f->gate.block();});CHECK(f->gate.entered.wait());
}
void front_release338(void* pointer) {static_cast<FrontFactory338*>(pointer)->gate.release.set();}
void front_failure338(void* pointer,int failure) {static_cast<FrontFactory338*>(pointer)->events.failure=failure;}
void front_close_device338(void* pointer) {hakios_metal_close(static_cast<FrontFactory338*>(pointer)->d);}
void front_destroy338(void* pointer) {
    auto* f=static_cast<FrontFactory338*>(pointer);CHECK(f->events.destroyed.wait());delete f;
}
}
