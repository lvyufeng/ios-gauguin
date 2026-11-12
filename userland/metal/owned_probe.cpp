// SPDX-License-Identifier: MIT
// Finite public-C-API check of the ownership profile, before the old router.
#include <atomic>
#include <chrono>
#include <cerrno>
#include <condition_variable>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <mutex>
#include <thread>
#include <vector>
#include <unistd.h>
#include "hakios-metal/hakios_metal.h"
#ifndef GAUGUIN_OWNED_HOST
#include <CommonCrypto/CommonDigest.h>
#include <dlfcn.h>
#include <fcntl.h>
#include <spawn.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include "GauguinOwnedIdentity.h"
extern "C" int memorystatus_control(uint32_t,int32_t,uint32_t,void*,size_t);
extern "C" int posix_spawnattr_setjetsam_ext(posix_spawnattr_t*,short,int,int,int);
extern char** environ;
#endif
using namespace std::chrono_literals;
namespace {
constexpr size_t bytes = 4096;
#ifndef GAUGUIN_OWNED_HOST
constexpr const char* corePath = "/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib";
constexpr const char* routerPath = "/usr/libexec/gauguin-gpu-probe-router";
#endif
unsigned jobs = 0, callbacks = 0, pixelChecks = 0;
[[noreturn]] void fail(const char* phase) {
    std::fprintf(stderr,"GAUGUIN OWNED FAIL phase=%s error=%.240s\n",phase,hakios_metal_error());
    std::fflush(nullptr); std::_Exit(1);
}
void need(bool ok,const char* phase) { if (!ok) fail(phase); }
uint64_t hash(const void* raw,size_t n) {
    auto* p=static_cast<const unsigned char*>(raw); uint64_t h=14695981039346656037ull;
    for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ull;} return h;
}
struct Completion {
    std::mutex mutex;
    std::condition_variable cv;
    bool done=false;
    bool error=false;
};
void releaseCompleted(hakios_metal_cb* cb,void* opaque) {
    auto& c=*static_cast<Completion*>(opaque);
    need(hakios_metal_cb_status(cb)==(c.error?HAKIOS_METAL_ERROR:HAKIOS_METAL_COMPLETED),"callback-status");
    hakios_metal_cb_wait(cb);
    hakios_metal_cb_free(cb);
    {std::lock_guard<std::mutex> g(c.mutex);c.done=true;}
    c.cv.notify_all();
}
void await(Completion& c) {
    std::unique_lock<std::mutex> g(c.mutex);
    need(c.cv.wait_for(g,5s,[&]{return c.done;}),"callback-deadline");
    callbacks++;
}
void completed(hakios_metal_cb* cb,const char* phase) {
    hakios_metal_cb_commit(cb,nullptr,nullptr); hakios_metal_cb_wait(cb);
    need(hakios_metal_cb_status(cb)==HAKIOS_METAL_COMPLETED,phase); jobs++;
    std::printf("GAUGUIN OWNED job phase=%s index=%u status=completed gpu_ns=%lld\n",phase,jobs,
                (long long)hakios_metal_cb_gpu_nanoseconds(cb));
    hakios_metal_cb_free(cb);
}
void sentinel(hakios_metal_queue* q,const char* phase) {
    auto* cb=hakios_metal_cb_new(q); need(cb,"sentinel-create"); completed(cb,phase);
}
void empty(hakios_metal_device* d,const char* phase) {
    const auto end=std::chrono::steady_clock::now()+5s;
    while(hakios_metal_device_allocated_bytes(d)!=0 && std::chrono::steady_clock::now()<end)
        std::this_thread::sleep_for(1ms);
    need(hakios_metal_device_allocated_bytes(d)==0,phase);
    std::printf("GAUGUIN OWNED cleanup phase=%s allocated=0\n",phase);
}
hakios_metal_queue* queue(hakios_metal_device* d,bool deferred) {
    auto* q=hakios_metal_queue_new(d);need(q,"queue-create");
    hakios_metal_queue_set_deferred(q,deferred);return q;
}
void fillCopy(hakios_metal_device* d,uint8_t value,bool deferred) {
    auto* q=queue(d,deferred);auto* cb=hakios_metal_cb_new(q);need(cb,"fill-cb");
    auto* from=hakios_metal_buffer_new(d,bytes);auto* to=hakios_metal_buffer_new(d,bytes);
    need(from&&to,"fill-buffers");std::memset(hakios_metal_buffer_contents(to),0xa5,bytes);
    need(hakios_metal_cb_fill(cb,from,0,bytes,value)==0,"fill-record");
    need(hakios_metal_cb_copy(cb,from,0,to,0,bytes)==0,"copy-record");
    hakios_metal_buffer_free(from); // native recorded work owns it now
    if(deferred) {
        hakios_metal_queue_set_deferred(q,0);
        need(std::strstr(hakios_metal_error(),"fixed after the first")!=nullptr,"mode-freeze");
        Completion c;hakios_metal_cb_commit(cb,releaseCompleted,&c);await(c);jobs++;
        std::printf("GAUGUIN OWNED job phase=deferred-fill-copy index=%u status=completed callback_owner_released=1\n",jobs);
        sentinel(q,"callback-fifo-barrier"); // first callback and capture destruction are over
    } else completed(cb,"synchronous-fill-copy");
    std::atomic_thread_fence(std::memory_order_seq_cst);
    auto* data=static_cast<const uint8_t*>(hakios_metal_buffer_contents(to));
    for(size_t i=0;i<bytes;i++)need(data[i]==value,"fill-copy-readback");
    pixelChecks+=bytes;
    std::printf("GAUGUIN OWNED pixels phase=%s count=%zu value=%u hash=%016llx PASS\n",
                deferred?"deferred-fill-copy":"synchronous-fill-copy",bytes,unsigned(value),(unsigned long long)hash(data,bytes));
    hakios_metal_buffer_free(to);hakios_metal_queue_free(q);empty(d,"fill-copy");
}
void clears(hakios_metal_device* d,uint32_t seed) {
    auto* q=queue(d,true);auto* t=hakios_metal_texture_new(d,2,70,64,64,5);need(t,"clear-texture");
    for(unsigned phase=0;phase<2;phase++) {
        uint32_t color=0xff000000;
        for(unsigned k=0;k<3;k++)if(((seed^phase)&(1u<<k))!=0)color|=0xffu<<(8*k);
        hakios_metal_render_pass pass{};pass.color0=t;pass.load_action=2;pass.store_action=1;
        for(unsigned k=0;k<4;k++)pass.clear_color[k]=double((color>>(8*k))&255)/255;
        auto* cb=hakios_metal_cb_new(q);need(cb,"clear-cb");
        need(hakios_metal_cb_clear(cb,&pass)==0,"clear-record");pass={};
        completed(cb,phase?"clear-B":"clear-A");
        std::vector<uint32_t> data(4096,0xa5a5a5a5);
        need(hakios_metal_texture_read(t,0,0,64,64,data.data(),256)==0,"clear-read");
        for(auto pixel:data)need(pixel==color,"clear-pixels");pixelChecks+=4096;
        std::printf("GAUGUIN OWNED pixels phase=clear-%c count=4096 value=%u hash=%016llx PASS\n",
                    phase?'B':'A',color,(unsigned long long)hash(data.data(),data.size()*4));
    }
    hakios_metal_texture_free(t);hakios_metal_queue_free(q);empty(d,"clear");
}
void append(hakios_metal_device* d,uint8_t value) {
    auto* a=queue(d,true);auto* b=queue(d,true);
    auto* source=hakios_metal_cb_new(a);auto* target=hakios_metal_cb_new(b);
    auto* data=hakios_metal_buffer_new(d,bytes);need(source&&target&&data,"append-create");
    need(hakios_metal_cb_fill(source,data,0,bytes,value)==0,"append-fill");
    need(hakios_metal_cb_append(target,source)==0,"append-record");hakios_metal_cb_free(source);
    hakios_metal_queue_free(a);completed(target,"append");
    auto* pixels=static_cast<const uint8_t*>(hakios_metal_buffer_contents(data));
    for(size_t i=0;i<bytes;i++)need(pixels[i]==value,"append-readback");pixelChecks+=bytes;
    std::printf("GAUGUIN OWNED pixels phase=append count=%zu value=%u hash=%016llx PASS\n",bytes,unsigned(value),(unsigned long long)hash(pixels,bytes));
    hakios_metal_buffer_free(data);hakios_metal_queue_free(b);empty(d,"append");
}
void refusal(hakios_metal_device* d) {
    auto* q=queue(d,true);auto* cb=hakios_metal_cb_new(q);need(cb,"refusal-cb");
    hakios_metal_cb_fail(cb,"owned-probe intentional API refusal");
    Completion c;c.error=true;hakios_metal_cb_commit(cb,releaseCompleted,&c);await(c);
    sentinel(q,"error-callback-fifo-barrier");hakios_metal_queue_free(q);empty(d,"refusal");
    std::puts("GAUGUIN OWNED refusal callback=1 own_wait=returned owner_released=1 PASS");
}
void earlyQueueRelease(hakios_metal_device* d) {
    auto* q=queue(d,true);auto* cb=hakios_metal_cb_new(q);need(cb,"early-cb");
    hakios_metal_queue_free(q);completed(cb,"queue-wrapper-released");empty(d,"early-queue-release");
}
#ifndef GAUGUIN_OWNED_HOST
bool fileMatches(const char* path,size_t size,const char* expected) {
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_CLOEXEC);if(fd<0)return false;
    struct stat a{},b{};bool ok=fstat(fd,&a)==0&&S_ISREG(a.st_mode)&&a.st_uid==0&&a.st_gid==0&&
        (a.st_mode&07777)==0755&&a.st_nlink==1&&a.st_size==(off_t)size;
    std::vector<unsigned char> data(ok?size:0);size_t at=0;
    while(ok&&at<size){ssize_t n=read(fd,data.data()+at,size-at);if(n<0&&errno==EINTR)continue;if(n<=0){ok=false;break;}at+=size_t(n);}
    unsigned char digest[32]{};char hex[65]{};
    if(ok){ok=CC_SHA256(data.data(),(CC_LONG)size,digest)!=nullptr;for(unsigned i=0;i<32;i++)std::snprintf(hex+i*2,3,"%02x",digest[i]);ok=ok&&!std::strcmp(hex,expected);}
    ok=ok&&fstat(fd,&b)==0&&a.st_ino==b.st_ino&&a.st_dev==b.st_dev&&a.st_mtime==b.st_mtime&&a.st_ctime==b.st_ctime;
    if(close(fd))ok=false;return ok;
}
struct Limits {int32_t active;uint32_t activeAttr;int32_t inactive;uint32_t inactiveAttr;};
struct Priority {int32_t pid,priority;uint64_t data;int32_t limit;uint32_t state;};
void memoryPolicy() {
    Limits l{};need(memorystatus_control(8,getpid(),0,&l,sizeof(l))==0&&l.active==128&&l.inactive==128&&l.activeAttr==1&&l.inactiveAttr==1,"128MB-policy");
}
void scope() {
    char boot[1024]{},version[64]{};size_t n=sizeof(boot)-1,v=sizeof(version)-1;
    need(getuid()==0&&geteuid()==0&&!std::strcmp(getprogname(),"gauguin-metal-owned-test"),"identity");
    need(sysctlbyname("kern.osversion",version,&v,nullptr,0)==0&&!std::strcmp(version,"20H392"),"os-version");
    need(sysctlbyname("kern.bootargs",boot,&n,nullptr,0)==0&&n<sizeof(boot)&&!std::strcmp(boot,kOwnedBootCommand),"boot-command");
    Dl_info loaded{};need(dladdr(reinterpret_cast<void*>(&hakios_metal_open),&loaded)&&loaded.dli_fname&&!std::strcmp(loaded.dli_fname,corePath),"loaded-core-path");
    need(fileMatches(corePath,kOwnedCoreBytes,kOwnedCoreSha256),"core-hash");
    need(fileMatches(routerPath,kOwnedRouterBytes,kOwnedRouterSha256),"router-hash");memoryPolicy();
    need(hakios_metal_has_compiler()==1,"native-AIR-compiler");
}
void handoff() {
    need(fileMatches(routerPath,kOwnedRouterBytes,kOwnedRouterSha256),"handoff-router-hash");memoryPolicy();
    Priority p{};need(memorystatus_control(1,getpid(),0,&p,sizeof(p))==(int)sizeof(p)&&p.pid==getpid()&&p.priority>=0,"priority");
    posix_spawnattr_t attr;need(posix_spawnattr_init(&attr)==0,"spawn-init");
    need(posix_spawnattr_setflags(&attr,POSIX_SPAWN_SETEXEC)==0&&posix_spawnattr_setjetsam_ext(&attr,0x0c,p.priority,128,128)==0,"spawn-attributes");
    char* const args[]={const_cast<char*>(routerPath),const_cast<char*>("--route247"),nullptr};
    std::printf("GAUGUIN OWNED handoff router=%s hard_mb=128\n",kOwnedRouterSha256);std::fflush(nullptr);
    int rc=posix_spawn(nullptr,routerPath,nullptr,&attr,args,environ);posix_spawnattr_destroy(&attr);(void)rc;fail("SETEXEC-returned");
}
#endif
}
int main(int argc,char** argv) {
    std::setvbuf(stdout,nullptr,_IOLBF,0);
    need(argc==2&&!std::strcmp(argv[1],"--owned300"),"arguments");
#ifdef GAUGUIN_OWNED_HOST
    std::puts("GAUGUIN OWNED HOST adapter=FakeGpu physical=0");
    auto* d=hakios_metal_open_fake();need(d,"fake-open");uint32_t seed=0x12345678;
#else
    scope();std::printf("GAUGUIN OWNED begin build=%s core=%s startup_seconds=180 work_seconds=30\n",kOwnedBuild,kOwnedCoreSha256);
    const auto start=std::chrono::steady_clock::now();hakios_metal_device* d=nullptr;
    while(std::chrono::steady_clock::now()-start<180s){d=hakios_metal_open();if(d)break;std::this_thread::sleep_for(100ms);}
    need(d,"GPU-open-deadline");alarm(30);
    uint32_t seed=uint32_t(std::chrono::steady_clock::now().time_since_epoch().count())^uint32_t(getpid());
#endif
    need(hakios_metal_gpu_id(d)==0x06010900,"A619-identity");
    std::printf("GAUGUIN OWNED identity gpu=619 chip=06010900 seed=%u\n",seed);
    fillCopy(d,uint8_t(seed),false);fillCopy(d,uint8_t(seed^0xff),true);
    clears(d,seed);append(d,uint8_t(seed^0x5a));refusal(d);earlyQueueRelease(d);
    need(jobs==8&&callbacks==2&&pixelChecks==20480,"totals");empty(d,"final");hakios_metal_close(d);
    std::printf("GAUGUIN OWNED RESULT PASS jobs=8 callbacks=2 pixel_checks=20480 allocated=0 teardown_requested=1\n");
#ifndef GAUGUIN_OWNED_HOST
    alarm(0);handoff();
#endif
    return 0;
}
