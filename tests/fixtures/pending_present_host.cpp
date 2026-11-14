// Actual table/handoff methods run over typed object/lock seams. Not XNU VM or a panel.
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdarg>
#include <string>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <strings.h>
#include <thread>
#include <vector>
#include "SweetPresentStats.h"
#define GAUGUIN 1
#define SWEET_SURFACE_MAX_ID 4096
#define SWEET_FB_SWAP_REC_SIZE 0x46c
#define SWEET_FB_LAYERS 4
static std::atomic<unsigned> checks{0},live{0};
static void check(bool v){++checks;assert(v);}
using IOLock=std::mutex;
static IOLock gpuLock;
static IOLock *gLock=&gpuLock,*surfaceKindLock;
static thread_local bool gpuHeld;
static thread_local unsigned framebufferLocks;
static void IOLockLock(IOLock *p){
    if(p==&gpuLock){check(!gpuHeld);p->lock();gpuHeld=true;}
    else {if(p!=surfaceKindLock){check(!gpuHeld);++framebufferLocks;}p->lock();}
}
static void IOLockUnlock(IOLock *p){
    if(p==&gpuLock){check(gpuHeld);gpuHeld=false;}
    else if(p!=surfaceKindLock){check(framebufferLocks>0);--framebufferLocks;}
    p->unlock();
}
static uint64_t hostClock;
static uint64_t mach_absolute_time(){return ++hostClock;}
static uint64_t sweet_ui_trace_clock(){return mach_absolute_time();}
#define GUT_READ_LOCK 24
#define GUT_READ_END 25
#define GUT_SWAP 20
static unsigned readBegins,readEnds;
static void sweet_ui_trace_record(uint32_t kind,uint64_t,uint32_t,uint32_t,uint64_t,uint64_t,uint64_t){
    if(kind==GUT_READ_LOCK){check(gpuHeld);++readBegins;}
    if(kind==GUT_READ_END){check(gpuHeld);++readEnds;}
}
static uint32_t gTraceReader;
static std::vector<std::string> rejectionLogs;
static std::mutex logLock;
static void IOLog(const char *format,...){
    char text[1024];va_list args;va_start(args,format);
    int n=std::vsnprintf(text,sizeof(text),format,args);va_end(args);
    check(n>=0&&static_cast<size_t>(n)<sizeof(text));
    if(std::strstr(text,"SWEET FB REJECT: ")){
        std::lock_guard<std::mutex> guard(logLock);rejectionLogs.emplace_back(text);
    }
}
struct SweetSurface {
    uint32_t id,pixel,gpuState=0;
    std::atomic<unsigned> refs{1};
    SweetSurface(uint32_t i,uint32_t p):id(i),pixel(p){++live;}
    void retain(){check(refs.fetch_add(1)>0);}
    void release(){unsigned was=refs.fetch_sub(1);check(was>0);if(was==1){--live;delete this;}}
};
static IOLock surfaceLock;
static IOLock *sweet_surface_lock=&surfaceLock;
static bool initializeSurfaceLock=(surfaceKindLock=&surfaceLock,true);
static SweetSurface *sweet_surface_table[SWEET_SURFACE_MAX_ID];
static uint32_t sweet_surface_users[SWEET_SURFACE_MAX_ID];
@SURFACE_METHODS@
struct IOMobileFramebufferUserClient {
    unsigned name;std::atomic<unsigned> refs{1};
    void retain(){check(refs.fetch_add(1)>0);}
    void release(){check(!gpuHeld&&framebufferLocks==0);check(refs.fetch_sub(1)>0);}
};
struct OSArray {
    std::vector<IOMobileFramebufferUserClient *> clients;
    unsigned getNextIndexOfObject(IOMobileFramebufferUserClient *c,unsigned from){
        for(unsigned i=from;i<clients.size();i++)if(clients[i]==c)return i;
        return static_cast<unsigned>(-1);
    }
    unsigned getCount(){return static_cast<unsigned>(clients.size());}
    void removeObject(unsigned i){check(i<clients.size());clients.erase(clients.begin()+i);}
};
@FRAME_TYPE@
struct AppleCLCD {
    IOLock lock;
    OSArray clients;
    IOLock *fLock=&lock;
    OSArray *fClients=&clients;
    uint8_t fPending[SWEET_FB_SWAP_REC_SIZE]={};
    bool fDirty=false,fPowerOff=false;
#if HAS_HELD
    bool fHoldPresent=true,fHeldActive=false,fDeferGpuPresent=true;
    sweet_fb_frame fHeldPending={},fHeldDeferred={};
    uint64_t fHeldGPUDeferred=0;
    SweetPresentSample *fPresentSample=nullptr;
    uint64_t fHeldSubmitted=0,fHeldReplaced=0,fHeldConsumed=0,fHeldRetired=0,fHeldCanceled=0,fHeldRejected=0;
    uint64_t fHeldRejectReasons[8]={};
    bool swap(const uint8_t *,IOMobileFramebufferUserClient *);
    bool takeHeldFrameLocked(sweet_fb_frame *);
    void cancelHeldFrameLocked(sweet_fb_frame *,IOMobileFramebufferUserClient *);
    void cancelDeferredFrameLocked(sweet_fb_frame *,IOMobileFramebufferUserClient *);
    void finishHeldFrame(sweet_fb_frame *,bool=false);
    bool renderHeldFrame(sweet_fb_frame *,bool *);
    void present(const uint8_t *,SweetSurface *const *,uint32_t=0);
    void removeClient(IOMobileFramebufferUserClient *);
#else
    void swap(const uint8_t *);
#endif
};
static uint64_t sweet_fb_swap_count;
@GET32@
enum PollResult {PENDING,COMPLETE,FAULT,INCONSISTENT};
static PollResult pollResult=PENDING;
static unsigned polls,presentCalls,copiedLayers,blockedWriters;
static uint32_t copiedPixels[4];
static bool completePendingOwnerLocked(bool wait,bool reap){
    check(gpuHeld&&!wait&&!reap);++polls;
    for(auto *s:sweet_surface_table)if(s&&s->gpuState==1){
        if(pollResult==COMPLETE)s->gpuState=0;
        if(pollResult==FAULT)s->gpuState=2;
    }
    return pollResult==COMPLETE||pollResult==INCONSISTENT;
}
@GPU_HEADER@
@GPU_METHODS@
@FRAME_METHODS@
void AppleCLCD::present(const uint8_t *rec,SweetSurface *const *held,uint32_t frameToken){
    ++presentCalls;
    for(unsigned layer=0;layer<4;layer++){
        auto *s=sweet_fb_present_surface(rec,held,layer);if(!s)continue;
        SweetSurfaceGPURead read(s,frameToken);
        if(read.valid()){
            check(frameToken==1||gpuHeld);
            if(frameToken==2){
                bool acquired=false;
                std::thread competingWriter([&](){acquired=gpuLock.try_lock();if(acquired)gpuLock.unlock();});
                competingWriter.join();check(!acquired);++blockedWriters;
            }
            copiedPixels[layer]=s->pixel;++copiedLayers;
        }
        s->release();
    }
}
@SWAP_METHOD@

// Allocation and creator close are seams. The actual production put/copy/hold/drop run unchanged.
static SweetSurface *publish(uint32_t id,uint32_t pixel){
    std::lock_guard<IOLock> guard(surfaceLock);
    if(sweet_surface_table[id])return nullptr;
    auto *s=new SweetSurface(id,pixel);s->retain();
    sweet_surface_table[id]=s;sweet_surface_users[id]=1;return s;
}
static void closeCreator(SweetSurface *s){sweet_surface_put(s);s->release();}
static uint32_t users(uint32_t id){std::lock_guard<IOLock> guard(surfaceLock);return sweet_surface_users[id];}
using Record=std::array<uint8_t,SWEET_FB_SWAP_REC_SIZE>;
static void word(Record &rec,unsigned off,uint32_t value){std::memcpy(rec.data()+off,&value,4);}
static void word(uint8_t *rec,unsigned off,uint32_t value){std::memcpy(rec+off,&value,4);}
static Record record(uint32_t id,uint32_t mask=1,uint32_t second=0){
    Record rec={};word(rec,0x50,71);word(rec,0x54,id);word(rec,0x58,second);word(rec,0x104,mask);return rec;
}
static void empty(){
    check(live==0);
    check(std::all_of(std::begin(sweet_surface_table),std::end(sweet_surface_table),[](auto *s){return s==nullptr;}));
}
#if HAS_HELD
static bool take(AppleCLCD &fb,sweet_fb_frame &frame){
    std::lock_guard<IOLock> guard(fb.lock);return fb.takeHeldFrameLocked(&frame);
}
static void cancel(AppleCLCD &fb,sweet_fb_frame &frame){
    std::lock_guard<IOLock> guard(fb.lock);fb.cancelHeldFrameLocked(&frame,nullptr);
}
static void accounting(AppleCLCD &fb){
    check(fb.fHeldSubmitted==fb.fHeldReplaced+fb.fHeldConsumed+fb.fHeldCanceled+(fb.fHeldPending.owner!=nullptr));
    check(fb.fHeldConsumed==fb.fHeldRetired+fb.fHeldActive);
}
static void view(sweet_fb_frame &frame,uint32_t pixel,unsigned layer=0){
    auto *s=sweet_fb_present_surface(frame.record,frame.surfaces,layer);check(s&&s->pixel==pixel);s->release();
}
#endif
int main(){
    IOMobileFramebufferUserClient a{1},b{2};
#if !HAS_HELD
    AppleCLCD fb;auto *s=publish(17,0x11223344);auto rec=record(17);
    fb.swap(rec.data());closeCreator(s);auto *replacement=publish(17,0xaabbccdd);check(replacement!=nullptr);
    auto *wrong=sweet_surface_copy(get32(fb.fPending,0x54));check(wrong&&wrong->pixel!=0x11223344);
    wrong->release();closeCreator(replacement);empty();
    std::fputs("FAIL pending display ID resolved a replacement surface after creator close\n",stderr);return 42;
#else
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(17,0x11223344);auto rec=record(17);
        check(fb.swap(rec.data(),&a));check(users(17)==2);closeCreator(s);
        check(publish(17,99)==nullptr&&users(17)==1);sweet_fb_frame frame={};check(take(fb,frame));
        check(!fb.fDirty&&fb.fHeldPending.owner==nullptr&&frame.owner==&a);view(frame,0x11223344);
        fb.finishHeldFrame(&frame);check(frame.owner==nullptr&&live==0);accounting(fb);
        auto *replacement=publish(17,99);check(replacement);closeCreator(replacement);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a,&b};auto *first=publish(21,21),*second=publish(22,22);
        check(fb.swap(record(21).data(),&a));closeCreator(first);
        check(fb.swap(record(22).data(),&b));check(fb.fHeldReplaced==1);closeCreator(second);check(live==1);
        fb.removeClient(&a);check(fb.fHeldPending.owner==&b);sweet_fb_frame frame={};check(take(fb,frame));view(frame,22);
        fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(25,25);
        check(fb.swap(record(25).data(),&a));closeCreator(s);fb.removeClient(&a);
        check(!fb.fDirty&&fb.fHeldCanceled==1&&live==0);auto *late=publish(25,26);
        check(!fb.swap(record(25).data(),&a));check(users(25)==1&&fb.fHeldRejected==1);closeCreator(late);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a,&b};auto *s=publish(31,31);check(fb.swap(record(31).data(),&a));closeCreator(s);
        sweet_fb_frame active={},pending={};check(take(fb,active));
        auto *next=publish(32,32);check(fb.swap(record(32).data(),&b));closeCreator(next);
        check(!take(fb,pending)&&pending.owner==nullptr);fb.removeClient(&a);check(live==2);
        view(active,31);fb.finishHeldFrame(&active);check(live==1);check(take(fb,pending));view(pending,32);
        fb.finishHeldFrame(&pending);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(40,40);
        check(fb.swap(record(40,3,40).data(),&a)&&users(40)==3);closeCreator(s);
        sweet_fb_frame frame={};check(take(fb,frame));view(frame,40,0);view(frame,40,1);
        fb.finishHeldFrame(&frame);fb.finishHeldFrame(&frame);check(fb.fHeldRetired==1);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(50,50);check(fb.swap(record(50).data(),&a));closeCreator(s);
        auto *valid=publish(51,51);check(!fb.swap(record(51,3,52).data(),&a));
        check(users(51)==1&&valid->refs==2&&fb.fHeldPending.surfaces[0]->id==50);
        check(!fb.swap(record(51,1u<<8).data(),&a));check(fb.fHeldRejected==2);
        closeCreator(valid);sweet_fb_frame frame={};check(take(fb,frame));view(frame,50);
        word(frame.record,0x54,53);
        check(sweet_fb_present_surface(frame.record,frame.surfaces,0)==nullptr);
        word(frame.record,0x54,50);
        check(sweet_fb_present_surface(frame.record,frame.surfaces,SWEET_FB_LAYERS)==nullptr);
        fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(60,60);
        check(fb.swap(record(60).data(),&a));closeCreator(s);fb.fPowerOff=true;
        sweet_fb_frame canceled={};cancel(fb,canceled);sweet_fb_frame_release(&canceled);
        auto *off=publish(61,61);check(fb.swap(record(61).data(),&a));check(users(61)==1&&!fb.fDirty);
        closeCreator(off);check(fb.fHeldCanceled==2);accounting(fb);empty();
        fb.fPowerOff=false;auto *on=publish(62,62);check(fb.swap(record(62).data(),&a));closeCreator(on);
        sweet_fb_frame frame={};check(take(fb,frame));view(frame,62);fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(70,70);check(fb.swap(record(70).data(),&a));closeCreator(s);
        fb.fPowerOff=true;auto *off=publish(71,71);check(fb.swap(record(71).data(),&a));closeCreator(off);
        check(fb.fHeldCanceled==2&&!fb.fDirty);accounting(fb);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(80,80);
        check(fb.swap(record(80,0).data(),&a));check(users(80)==1);closeCreator(s);
        sweet_fb_frame frame={};check(take(fb,frame));check(sweet_fb_present_surface(frame.record,frame.surfaces,0)==nullptr);
        fb.finishHeldFrame(&frame);accounting(fb);empty();
        check(fb.swap(record(0).data(),&a));check(take(fb,frame));fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        auto *s=publish(90,90);sweet_surface_users[90]=UINT32_MAX;
        check(sweet_surface_hold(90)==nullptr&&s->refs==2);sweet_surface_users[90]=1;
        check(sweet_surface_hold(0)==nullptr&&sweet_surface_hold(4096)==nullptr);
        sweet_surface_lock=nullptr;check(sweet_surface_hold(90)==nullptr);sweet_surface_lock=&surfaceLock;
        closeCreator(s);empty();
    }
    {
        AppleCLCD fb;fb.fHoldPresent=false;fb.clients.clients={&a};auto *s=publish(100,100);
        auto rec=record(100);check(fb.swap(rec.data(),&a)&&fb.fDirty&&users(100)==1);
        auto *view=sweet_fb_present_surface(fb.fPending,nullptr,0);check(view&&view->pixel==100);view->release();
        check(fb.fHeldSubmitted==0&&fb.fHeldPending.owner==nullptr);closeCreator(s);empty();
    }
    {
        AppleCLCD fb;fb.clients.clients={&a,&b};auto *s=publish(110,110),*t=publish(111,111);
        auto worker=[&](IOMobileFramebufferUserClient *owner,uint32_t id){for(unsigned i=0;i<500;i++)check(fb.swap(record(id).data(),owner));};
        std::thread one(worker,&a,110),two(worker,&b,111);one.join();two.join();
        check(fb.fHeldSubmitted==1000&&fb.fHeldReplaced==999);closeCreator(s);closeCreator(t);check(live==1);
        sweet_fb_frame frame={};check(take(fb,frame));view(frame,frame.surfaces[0]->pixel);fb.finishHeldFrame(&frame);
        accounting(fb);empty();
    }
    {
        // Execute every new reason branch from the production methods, with
        // partial holds, prior pending ownership and unchanged rejected input.
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(120,120);
        auto rec=record(120);sweet_fb_frame scratch={};uint32_t reason=99;
        check(!sweet_fb_frame_prepare(&scratch,rec.data(),nullptr,&reason)&&reason==1);
        check(scratch.owner==nullptr&&users(120)==1);
        const size_t first=rejectionLogs.size();
        check(!fb.swap(rec.data(),&b)&&fb.fHeldRejectReasons[7]==1);
        check(rejectionLogs.back().find("reason=7 owner=1 registered=0 clients=1 mask=0x1 ids=120,0,0,0")!=std::string::npos);
        check(!fb.swap(record(120,0x101).data(),&a)&&fb.fHeldRejectReasons[2]==1);
        check(rejectionLogs.back().find("reason=2 owner=1 registered=1 clients=1 mask=0x101")!=std::string::npos);
        check(fb.swap(rec.data(),&a)&&users(120)==2);
        for(unsigned layer=0;layer<4;layer++){
            auto missing=record(120,(1u<<(layer+1))-1u);
            for(unsigned i=0;i<layer;i++)word(missing,0x54+4*i,120);
            word(missing,0x54+4*layer,121);
            auto original=missing;
            check(!fb.swap(missing.data(),&a)&&fb.fHeldRejectReasons[3+layer]==1);
            check(missing==original&&users(120)==2&&s->refs==3);
            check(rejectionLogs.back().find("reason="+std::to_string(3+layer))!=std::string::npos);
            check(fb.fHeldPending.surfaces[0]==s&&fb.fHeldSubmitted==1);
        }
        // Invalid IDs and exhausted table users use the same safe hold failure.
        check(!fb.swap(record(SWEET_SURFACE_MAX_ID).data(),&a));
        sweet_surface_users[120]=UINT32_MAX;
        check(!fb.swap(rec.data(),&a));sweet_surface_users[120]=2;
        check(rejectionLogs.size()==first+8);
        auto rejectWorker=[&](){for(unsigned i=0;i<128;i++)check(!fb.swap(record(121).data(),&a));};
        std::thread one(rejectWorker),two(rejectWorker);one.join();two.join();
        check(fb.fHeldRejected==264&&rejectionLogs.size()==first+8);
        uint64_t classified=0;for(auto count:fb.fHeldRejectReasons)classified+=count;
        check(classified==fb.fHeldRejected&&users(120)==2&&s->refs==3);
        closeCreator(s);sweet_fb_frame frame={};check(take(fb,frame));view(frame,120);
        fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        // A ready first layer must not be copied before the second is ready.
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(201,0x201),*t=publish(202,0x202);
        t->gpuState=1;check(fb.swap(record(201,3,202).data(),&a));closeCreator(s);closeCreator(t);
        check(a.refs==2);sweet_fb_frame frame={};bool presented=true;
        const unsigned beforePoll=polls,beforePresent=presentCalls,beforeCopy=copiedLayers;
        const unsigned beforeReads=readBegins,beforeEnds=readEnds,beforeBlocked=blockedWriters;
        SweetPresentSample sample={};sample.timingValid=true;fb.fPresentSample=&sample;
        pollResult=PENDING;
        for(unsigned beat=0;beat<3;beat++){
            check(take(fb,frame));check(fb.renderHeldFrame(&frame,&presented)&&!presented);
            check(!gpuHeld&&polls==beforePoll+beat+1&&presentCalls==beforePresent&&copiedLayers==beforeCopy);
            fb.finishHeldFrame(&frame,true);
            check(!frame.owner&&fb.fHeldDeferred.owner==&a&&fb.fHeldActive&&fb.fDirty);
            check(fb.fHeldConsumed==1&&fb.fHeldRetired==0&&a.refs==2&&live==2);accounting(fb);
        }
        check(readBegins==beforeReads&&readEnds==beforeEnds);
        check(sample.gpuGuards==3&&sample.gpuRefusals==3&&sample.waitTicks>0&&sample.timingValid);
        pollResult=COMPLETE;check(take(fb,frame));check(!fb.renderHeldFrame(&frame,&presented)&&presented);
        check(!gpuHeld&&polls==beforePoll+4&&presentCalls==beforePresent+1&&copiedLayers==beforeCopy+2);
        check(copiedPixels[0]==0x201&&copiedPixels[1]==0x202);
        check(readBegins==beforeReads+2&&readEnds==beforeEnds+2&&blockedWriters==beforeBlocked+2);
        fb.finishHeldFrame(&frame);check(fb.fHeldGPUDeferred==3&&fb.fHeldConsumed==1&&fb.fHeldRetired==1);
        check(a.refs==1&&!fb.fDirty&&!fb.fHeldActive&&!fb.fHeldDeferred.owner);accounting(fb);empty();
    }
    {
        // Invalid replacement leaves the waiting frame intact; valid latest wins.
        AppleCLCD fb;fb.clients.clients={&a,&b};auto *old=publish(211,211);old->gpuState=1;
        check(fb.swap(record(211).data(),&a));closeCreator(old);sweet_fb_frame frame={};bool presented;
        pollResult=PENDING;check(take(fb,frame));check(fb.renderHeldFrame(&frame,&presented)&&!presented);
        fb.finishHeldFrame(&frame,true);check(!fb.swap(record(4096).data(),&b));
        check(fb.fHeldDeferred.owner==&a&&fb.fHeldActive&&fb.fDirty&&a.refs==2);accounting(fb);
        auto *next=publish(212,212);check(fb.swap(record(212).data(),&b));closeCreator(next);
        check(!fb.fHeldDeferred.owner&&!fb.fHeldActive&&fb.fHeldPending.owner==&b);
        check(a.refs==1&&b.refs==2&&live==1&&fb.fHeldRetired==1);accounting(fb);
        const unsigned before=polls;check(take(fb,frame));check(!fb.renderHeldFrame(&frame,&presented)&&presented);
        check(polls==before&&copiedPixels[0]==212);fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    {
        // A producer wins while an active timer callback is checking the fence.
        AppleCLCD fb;fb.clients.clients={&a,&b};auto *old=publish(221,221);old->gpuState=1;
        check(fb.swap(record(221).data(),&a));closeCreator(old);sweet_fb_frame frame={};bool presented;
        pollResult=PENDING;check(take(fb,frame));check(fb.renderHeldFrame(&frame,&presented));
        auto *next=publish(222,222);check(fb.swap(record(222).data(),&b));closeCreator(next);
        fb.finishHeldFrame(&frame,true);check(!fb.fHeldDeferred.owner&&!fb.fHeldActive&&fb.fHeldPending.owner==&b);
        check(fb.fHeldRetired==1&&a.refs==1&&live==1);accounting(fb);
        check(take(fb,frame));check(!fb.renderHeldFrame(&frame,&presented)&&presented);
        check(copiedPixels[0]==222);fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    for(bool deferred:{false,true}){
        // Closing either before requeue or between beats must not resurrect work.
        AppleCLCD fb;IOMobileFramebufferUserClient client{3};fb.clients.clients={&client};
        auto *s=publish(231,231);s->gpuState=1;check(fb.swap(record(231).data(),&client));closeCreator(s);
        sweet_fb_frame frame={};bool presented;pollResult=PENDING;check(take(fb,frame));
        check(fb.renderHeldFrame(&frame,&presented)&&!presented);
        if(deferred)fb.finishHeldFrame(&frame,true);
        check(client.refs==2);fb.removeClient(&client);client.release();
        if(!deferred){check(client.refs==1&&live==1);fb.finishHeldFrame(&frame,true);}
        check(client.refs==0&&!fb.fHeldDeferred.owner&&!fb.fHeldActive&&!fb.fDirty);
        check(fb.fHeldRetired==1);accounting(fb);empty();
    }
    for(bool deferred:{false,true}){
        // Sleep cancellation, including an already-active callback, is balanced.
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(241,241);s->gpuState=1;
        check(fb.swap(record(241).data(),&a));closeCreator(s);sweet_fb_frame frame={};bool presented;
        pollResult=PENDING;check(take(fb,frame));check(fb.renderHeldFrame(&frame,&presented)&&!presented);
        if(deferred)fb.finishHeldFrame(&frame,true);
        sweet_fb_frame canceled={},waiting={};
        IOLockLock(fb.fLock);fb.fPowerOff=true;fb.cancelHeldFrameLocked(&canceled,nullptr);
        fb.cancelDeferredFrameLocked(&waiting,nullptr);IOLockUnlock(fb.fLock);
        sweet_fb_frame_release(&canceled);sweet_fb_frame_release(&waiting);
        if(!deferred)fb.finishHeldFrame(&frame,true);
        check(a.refs==1&&!fb.fHeldActive&&!fb.fHeldDeferred.owner&&!fb.fDirty);accounting(fb);empty();
    }
    for(auto result:{FAULT,INCONSISTENT}){
        // A fault or inconsistent owner is terminal, not a forever-pending frame.
        AppleCLCD fb;fb.clients.clients={&a};auto *s=publish(251,251);s->gpuState=1;
        check(fb.swap(record(251).data(),&a));closeCreator(s);sweet_fb_frame frame={};bool presented=true;
        pollResult=result;const unsigned beforePoll=polls,beforeCopy=copiedLayers;
        check(take(fb,frame));check(!fb.renderHeldFrame(&frame,&presented)&&!presented);
        check(polls==beforePoll+1&&copiedLayers==beforeCopy&&!gpuHeld);
        fb.finishHeldFrame(&frame);check(fb.fHeldRetired==1&&fb.fHeldGPUDeferred==0);accounting(fb);empty();
    }
    {
        // A preexisting invalid layer rejects the entire frame without polling.
        auto *s=publish(261,261),*t=publish(262,262);s->gpuState=1;t->gpuState=2;
        SweetSurface *layers[4]={s,t,nullptr,nullptr};const unsigned before=polls;
        {SweetFrameGPURead guard(layers,4);check(!guard.valid()&&!guard.pending()&&!gpuHeld);}
        check(polls==before);closeCreator(s);closeCreator(t);empty();
    }
    {
        // The prepublication CPU token never unlocks a subsequently published lock.
        auto *s=publish(271,271);SweetSurface *layers[4]={s,nullptr,nullptr,nullptr};gLock=nullptr;
        {SweetFrameGPURead guard(layers,4);check(guard.valid()&&!guard.pending()&&guard.lockToken()==1);
         gLock=&gpuLock;{SweetSurfaceGPURead read(s,guard.lockToken());check(read.valid()&&!gpuHeld);}}
        check(!gpuHeld);closeCreator(s);empty();
    }
    {
        SweetSurface *layers[4]={};uint32_t state=99;const unsigned before=polls;
        check(!GauguinGPUFrameBegin(nullptr,4,&state)&&state==SWEET_GPU_FRAME_INVALID);
        check(!GauguinGPUFrameBegin(layers,0,&state)&&state==SWEET_GPU_FRAME_INVALID);
        check(!GauguinGPUFrameBegin(layers,5,&state)&&state==SWEET_GPU_FRAME_INVALID);
        check(!GauguinGPUFrameBegin(layers,4,nullptr)&&!gpuHeld&&polls==before);
        {SweetFrameGPURead guard(layers,4);check(guard.valid()&&!guard.pending()&&gpuHeld);}
        check(!gpuHeld);
    }
    {
        // Default synchronous rendering still uses the legacy surface guard.
        AppleCLCD fb;fb.fDeferGpuPresent=false;fb.clients.clients={&a};auto *s=publish(281,281);
        check(fb.swap(record(281).data(),&a));closeCreator(s);sweet_fb_frame frame={};bool presented;
        const unsigned before=readBegins,beforeEnd=readEnds;check(take(fb,frame));
        check(!fb.renderHeldFrame(&frame,&presented)&&presented&&!gpuHeld);
        check(readBegins==before+1&&readEnds==beforeEnd+1&&copiedPixels[0]==281);
        fb.finishHeldFrame(&frame);accounting(fb);empty();
    }
    check(a.refs==1&&b.refs==1&&!gpuHeld&&framebufferLocks==0);
    std::printf("PASS pending GPU and held presentation checks=%u original-ID lifetime, replacement, close, active/pending bounds, off/on, concurrent producers; host seams only\n",checks.load());
#endif
}
