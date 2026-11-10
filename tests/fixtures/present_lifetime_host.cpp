// Actual table/handoff methods run over typed object/lock seams. Not XNU VM or a panel.
#include <algorithm>
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <mutex>
#include <strings.h>
#include <thread>
#include <vector>
#define GAUGUIN 1
#define SWEET_SURFACE_MAX_ID 4096
#define SWEET_FB_SWAP_REC_SIZE 0x46c
#define SWEET_FB_LAYERS 4
static std::atomic<unsigned> checks{0},live{0};
static void check(bool v){++checks;assert(v);}
using IOLock=std::mutex;
static void IOLockLock(IOLock *p){p->lock();}
static void IOLockUnlock(IOLock *p){p->unlock();}
static void IOLog(const char *,...){ }
struct SweetSurface {
    uint32_t id,pixel;
    std::atomic<unsigned> refs{1};
    SweetSurface(uint32_t i,uint32_t p):id(i),pixel(p){++live;}
    void retain(){check(refs.fetch_add(1)>0);}
    void release(){unsigned was=refs.fetch_sub(1);check(was>0);if(was==1){--live;delete this;}}
};
static IOLock surfaceLock;
static IOLock *sweet_surface_lock=&surfaceLock;
static SweetSurface *sweet_surface_table[SWEET_SURFACE_MAX_ID];
static uint32_t sweet_surface_users[SWEET_SURFACE_MAX_ID];
@SURFACE_METHODS@
struct IOMobileFramebufferUserClient { unsigned name; };
struct OSArray {
    std::vector<IOMobileFramebufferUserClient *> clients;
    unsigned getNextIndexOfObject(IOMobileFramebufferUserClient *c,unsigned from){
        for(unsigned i=from;i<clients.size();i++)if(clients[i]==c)return i;
        return static_cast<unsigned>(-1);
    }
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
    bool fHoldPresent=true,fHeldActive=false;
    sweet_fb_frame fHeldPending={};
    uint64_t fHeldSubmitted=0,fHeldReplaced=0,fHeldConsumed=0,fHeldRetired=0,fHeldCanceled=0,fHeldRejected=0;
    bool swap(const uint8_t *,IOMobileFramebufferUserClient *);
    bool takeHeldFrameLocked(sweet_fb_frame *);
    void cancelHeldFrameLocked(sweet_fb_frame *,IOMobileFramebufferUserClient *);
    void finishHeldFrame(sweet_fb_frame *);
    void removeClient(IOMobileFramebufferUserClient *);
#else
    void swap(const uint8_t *);
#endif
};
static uint64_t sweet_fb_swap_count;
@GET32@
@FRAME_METHODS@
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
    std::printf("PASS held presentation checks=%u original-ID lifetime, replacement, close, active/pending bounds, off/on, concurrent producers; host seams only\n",checks.load());
#endif
}
