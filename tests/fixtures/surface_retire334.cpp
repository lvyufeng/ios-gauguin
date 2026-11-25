#include "hakios-metal/command.hpp"
#include <cassert>
#include <cerrno>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <map>
#include <mutex>
#include <new>
#include <thread>
#include <vector>

static thread_local bool injectAllocation=false;
static thread_local unsigned failAllocation=0,allocationAttempts=0;
void* operator new(std::size_t n){
    if(injectAllocation&&++allocationAttempts==failAllocation){
        std::fprintf(stderr,"OBS publication allocation failure=%u\n",allocationAttempts);
        throw std::bad_alloc();
    }
    if(void *p=std::malloc(n?n:1))return p;
    throw std::bad_alloc();
}
void operator delete(void *p) noexcept{std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void *p) noexcept{::operator delete(p);}

static std::mutex scheduleLock;
static std::condition_variable scheduleChanged;
static bool scheduleRace=false,oldPaused=false,allowOld=false;
static unsigned expiredLookups=0;
static thread_local unsigned role=0;
// Only schedule seams: real std::mutex/condition_variable and all ownership
// decisions remain the extracted production implementation's.
static void beforeRetireLock(){
    if(!scheduleRace||role!=1)return;
    std::unique_lock<std::mutex> g(scheduleLock);oldPaused=true;scheduleChanged.notify_all();
    scheduleChanged.wait(g,[]{return allowOld;});
}
static void observeLookup(bool expired){
    if(!scheduleRace||role!=2||!expired)return;
    std::lock_guard<std::mutex> g(scheduleLock);++expiredLookups;scheduleChanged.notify_all();
}
static void beforePublicationAlloc(){
    if(failAllocation){allocationAttempts=0;injectAllocation=true;}
}
namespace hakios::metal {
/* ACTUAL_SURFACE_BUFFER_SOURCE */
}
using namespace hakios::metal;

class SurfaceTransport final:public Transport {
    struct Slot {bool live=true;uint32_t surface=0,maps=0;std::vector<uint8_t> data=std::vector<uint8_t>(16384);};
    std::mutex mutex;std::map<uint32_t,Slot> slots;uint32_t next=1;
public:
    unsigned closes=0,badCloses=0,surfaceCalls=0;
    unsigned failSurfaceCall=0;bool recycleHandle=false;
    int call(uint32_t request,void *data,size_t bytes) override {
        std::lock_guard<std::mutex> g(mutex);
        if(request==kHakiosSurface){
            assert(bytes==sizeof(HakiosSurface));auto &s=*static_cast<HakiosSurface*>(data);
            if(++surfaceCalls==failSurfaceCall)return ENOENT;
            uint32_t handle=0;
            for(auto &[id,slot]:slots)if(slot.live&&slot.surface==s.surface)handle=id;
            if(!handle){
                if(recycleHandle)for(auto &[id,slot]:slots)if(!slot.live&&!slot.maps){handle=id;break;}
                if(!handle)handle=next++;
                auto &slot=slots[handle];slot.live=true;slot.surface=s.surface;
            }
            s.handle=handle;s.size=16384;s.offset=0;s.rowBytes=256;s.width=s.height=64;s.pixelFormat=0x42475241;s.planes=0;return 0;
        }
        if(request==kGemInfo){
            assert(bytes==sizeof(MsmGemInfo));auto &i=*static_cast<MsmGemInfo*>(data);
            auto found=slots.find(i.handle);if(found==slots.end()||!found->second.live)return EINVAL;
            assert(i.info==kInfoGetIova);i.value=0x80000000ull+65536ull*i.handle;return 0;
        }
        if(request==kGemClose){
            assert(bytes==sizeof(DrmGemClose));auto &c=*static_cast<DrmGemClose*>(data);
            auto found=slots.find(c.handle);if(found==slots.end()||!found->second.live){++badCloses;return EINVAL;}
            found->second.live=false;++closes;return 0;
        }
        assert(false);return EINVAL;
    }
    void* map(uint32_t h,uint64_t bytes) override {
        std::lock_guard<std::mutex> g(mutex);auto it=slots.find(h);if(it==slots.end()||!it->second.live)return nullptr;
        assert(bytes==it->second.data.size());++it->second.maps;return it->second.data.data();
    }
    void unmap(uint32_t h,void *address) override {
        std::lock_guard<std::mutex> g(mutex);auto it=slots.find(h);assert(it!=slots.end());
        assert(it->second.maps&&it->second.data.data()==address);--it->second.maps;
    }
    int64_t nowNs() override{return 1;}
    bool live(uint32_t h){std::lock_guard<std::mutex> g(mutex);return slots.at(h).live;}
    bool empty(){std::lock_guard<std::mutex> g(mutex);for(auto &[id,s]:slots)if(s.maps||s.live)return false;return true;}
};

static int race(unsigned count,bool recycle,bool failReimport){
    auto transport=std::make_unique<SurfaceTransport>();auto *t=transport.get();t->recycleHandle=recycle;
    Gpu gpu(std::move(transport));SurfaceInfo info;std::string why;
    auto first=surfaceBuffer(gpu,7,&info,&why);assert(first);uint32_t original=first->bo().handle();std::weak_ptr<Buffer> weak=first;
    scheduleRace=true;
    std::thread retiring([held=std::move(first)]() mutable {role=1;held.reset();});
    {std::unique_lock<std::mutex> g(scheduleLock);scheduleChanged.wait(g,[]{return oldPaused;});}
    assert(weak.expired()&&t->live(original));
    if(failReimport)t->failSurfaceCall=count+2;
    std::vector<std::shared_ptr<Buffer>> received(count);std::vector<std::thread> importing;
    for(unsigned i=0;i<count;++i)importing.emplace_back([&,i]{role=2;SurfaceInfo info;std::string why;received[i]=surfaceBuffer(gpu,7,&info,&why);if(!received[i])assert(why.find("no such surface")!=std::string::npos);});
    {std::unique_lock<std::mutex> g(scheduleLock);scheduleChanged.wait(g,[=]{return expiredLookups==count;});allowOld=true;}
    scheduleChanged.notify_all();retiring.join();for(auto &thread:importing)thread.join();
    scheduleRace=false;bool stale=false;
    if(failReimport)assert(count==1&&!received[0]);
    else for(auto &b:received){assert(b&&b==received[0]);stale|=!t->live(b->bo().handle());}
    std::printf("OBS imports=%u recycled=%u reimport_error=%u replacement_live=%u\n",count,recycle,failReimport,!stale);
    received.clear();assert(t->empty());
#ifdef SURF334_CANDIDATE
    assert(!stale&&t->badCloses==0&&t->closes==(failReimport?1u:2u));
#else
    assert(stale&&t->badCloses==1&&t->closes==1);return 42;
#endif
    return 0;
}
int main(int argc,char **argv){
    assert(argc>=2);std::string mode=argv[1];int result=0;
    if(mode=="race")result=race(1,false,false);
    else if(mode=="many")result=race(16,false,false);
    else if(mode=="recycled")result=race(16,true,false);
    else if(mode=="reimport-error")result=race(1,false,true);
    else if(mode=="allocation"){
        assert(argc==3);auto transport=std::make_unique<SurfaceTransport>();auto *t=transport.get();Gpu gpu(std::move(transport));SurfaceInfo info;std::string why;
        failAllocation=std::strtoul(argv[2],nullptr,10);bool failed=false;std::shared_ptr<Buffer> b;
        try{b=surfaceBuffer(gpu,7,&info,&why);}catch(const std::bad_alloc&){failed=true;}
        injectAllocation=false;failAllocation=0;
        assert(failed==(std::strtoul(argv[2],nullptr,10)<=3));
        if(b){assert(t->live(b->bo().handle()));b.reset();}
        assert(t->empty()&&t->closes==1&&t->badCloses==0);
        b=surfaceBuffer(gpu,7,&info,&why);assert(b&&t->live(b->bo().handle()));b.reset();assert(t->empty()&&t->badCloses==0);
    }else if(mode=="basic"||mode=="foreign"){
        auto a=std::make_unique<SurfaceTransport>();auto *ta=a.get();Gpu ga(std::move(a));SurfaceInfo info;std::string why;
        auto first=surfaceBuffer(ga,7,&info,&why),alias=surfaceBuffer(ga,7,&info,&why);assert(first==alias&&ta->closes==0);
        if(mode=="foreign"){
            auto b=std::make_unique<SurfaceTransport>();auto *tb=b.get();Gpu gb(std::move(b));auto other=surfaceBuffer(gb,7,&info,&why);
            assert(other!=first);first.reset();alias.reset();assert(ta->empty()&&tb->live(other->bo().handle()));other.reset();assert(tb->empty());
        }else{first.reset();assert(ta->live(alias->bo().handle()));alias.reset();assert(ta->empty());}
        assert(ta->badCloses==0&&ta->closes==1);
    }else if(mode=="stress"){
        auto transport=std::make_unique<SurfaceTransport>();auto *t=transport.get();Gpu gpu(std::move(transport));std::vector<std::thread> threads;
        for(unsigned worker=0;worker<8;++worker)threads.emplace_back([&,worker]{for(unsigned i=0;i<400;++i){SurfaceInfo info;std::string why;auto b=surfaceBuffer(gpu,7+(i+worker)%3,&info,&why);assert(b&&t->live(b->bo().handle()));if(i%3==0)std::this_thread::yield();}});
        for(auto &thread:threads)thread.join();assert(t->empty()&&t->badCloses==0);
    }else assert(false);
    assert(gSurfaceBuffers.empty());
    std::printf("%s %s: exact production cache/Bo lifetime observations\n",result?"RED":"PASS",mode.c_str());return result;
}
