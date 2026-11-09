/* Typed IOKit/memory seams around the ACTUAL transport source. Host checks
 * exercise ownership, scatter pages, wire dispatch, cache calls and failure
 * retention. Neither the service nor a physical GPU is running here. */
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <map>
#include <mutex>
#include <vector>
#include "gauguin_gpu_runtime.h"
/* The baseline lacks this new capacity constant; still compile it to obtain a functional RED. */
#ifndef GGR_MAX_QUEUES
#define GGR_MAX_QUEUES 32u
#endif
#ifndef GGR_MAX_CLIENT_BUFFERS
#define GGR_MAX_CLIENT_BUFFERS 1024u
#endif
#define GAUGUIN 1
#define SWEET 1
#define APPLE_KEXT_OVERRIDE override
#define PAGE_SHIFT 14
#define PAGE_SIZE 16384u
#define PAGE_MASK (PAGE_SIZE-1)
#define OSDeclareDefaultStructors(C) public:C();~C() override;private:
#define OSDefineMetaClassAndStructors(C,B) C::C()=default;C::~C()=default;
#define OSTypeAlloc(C) new C()
#define OSDynamicCast(C,p) dynamic_cast<C *>(p)
#define OSSafeReleaseNULL(p) do{if(p){(p)->release();(p)=nullptr;}}while(0)
#define IONew(C,n) new C[n]
#define IONewZero(C,n) new C[n]()
#define IODelete(p,C,n) delete[] (p)
static void test_log(const char *format,...){(void)format;}
#define IOLog test_log
/* CPU-only monotonic clock seam for the production elapsed wrappers. */
[[maybe_unused]] static uint64_t mach_absolute_time(){static uint64_t ticks;return ++ticks;}
[[maybe_unused]] static void absolutetime_to_nanoseconds(uint64_t ticks,uint64_t *ns){*ns=ticks;}
using UInt32=uint32_t;using IOOptionBits=uint32_t;using IOReturn=int;
using IOByteCount=uint64_t;using addr64_t=uint64_t;using vm_size_t=uint64_t;
using uintptr_t=std::uintptr_t;using task_t=void *;using ppnum_t=uint64_t;
using boolean_t=int;using mach_port_name_t=uint32_t;
static task_t kernel_task=(void *)1;
#ifdef GAUGUIN_GPU_PILOT_HOST
static task_t mock_task = kernel_task;
static bool pilot_mode, pilot_job;
static unsigned mock_task_refs;
struct mock_proc { int pid; };
static mock_proc compositor = {57};
static task_t current_task() { return mock_task; }
static mock_proc *current_proc() { return &compositor; }
[[maybe_unused]] static int proc_pid(mock_proc *p) { return p->pid; }
static bool sweet_eagl_gpu_pilot_enabled() { return pilot_mode; }
static bool sweet_eagl_gpu_pilot_caller(mock_proc *p) { return pilot_mode && pilot_job && p == &compositor; }
static void task_reference(task_t task) { assert(task == (void *)2); ++mock_task_refs; }
static void task_deallocate(task_t task) { assert(task == (void *)2 && mock_task_refs); --mock_task_refs; }
#endif
enum {kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNoResources=2,kIOReturnNoMemory=3,
    kIOReturnVMError=4,kIOReturnNotReady=5,kIOReturnNotFound=6,kIOReturnUnsupported=7,kIOReturnTimeout=8,
    kIOReturnNotPrivileged=9};
enum {kIODirectionInOut=1,kIOMapWriteCombineCache=0x1000,kIOMemoryKernelUserShared=2,kIOMemoryMapperNone=0};
static const char *kIOUserClientClassKey="IOUserClientClass";
static const char *kIOClientPrivilegeAdministrator="administrator";
static const bool kOSBooleanTrue=true;
struct OSDictionary {};
struct IOExternalMethodDispatch {};
struct IOExternalMethodArguments {
    const void *structureInput;void *structureOutput;size_t structureInputSize;uint32_t structureOutputSize;
    uint32_t scalarInputCount,scalarOutputCount;void *structureInputDescriptor,*structureOutputDescriptor;
};
struct OSObject {
    static void *operator new(size_t n){void *p=calloc(1,n);assert(p);return p;}
    static void operator delete(void *p){::free(p);}
    unsigned refs=1;
    virtual ~OSObject()=default;
    virtual bool init(){return true;}
    virtual void free(){delete this;}
    void retain(){++refs;}
    void release(){assert(refs);if(!--refs)free();}
};
struct IOMemoryMap : OSObject {};
struct IOService : OSObject {
    virtual bool start(IOService *){return true;}
    static IOService *getPlatform(){static IOService p;return &p;}
    bool attach(IOService *){retain();return true;}
    void detach(IOService *){release();}
    template<class T>void setProperty(const char *,T){}
    void setName(const char *){}
    void registerService(){}
};
struct IOUserClient : IOService {
    static IOReturn clientHasPrivilege(task_t task,const char *){return task==kernel_task?0:1;}
    virtual bool initWithTask(task_t,void *,UInt32,OSDictionary *){return true;}
    virtual IOReturn clientClose(){return 0;}
    virtual IOReturn clientMemoryForType(UInt32,IOOptionBits *,struct IOMemoryDescriptor **){return 1;}
    virtual IOReturn externalMethod(uint32_t,IOExternalMethodArguments *,IOExternalMethodDispatch *,OSObject *,void *){return 1;}
    bool inactive=false;bool isInactive(){return inactive;}
    void terminate(){inactive=true;}
};
using IOLock=std::mutex;
static unsigned lock_depth,heartbeat_calls;
static IOLock *IOLockAlloc(){return new std::mutex;}
static void IOLockLock(IOLock *m){m->lock();++lock_depth;}
static void IOLockUnlock(IOLock *m){assert(lock_depth);--lock_depth;m->unlock();}
static unsigned allocations,frees,cache_calls,sync_calls,submit_calls;
static uint64_t next_pa=0x90000000;
struct IOMemoryDescriptor : OSObject {
    virtual uint64_t getPhysicalSegment(uint64_t,IOByteCount *,unsigned)=0;
    virtual IOReturn prepare()=0;virtual void complete()=0;
};
static std::map<uint64_t,uint8_t *> physical_pages;
struct IOBufferMemoryDescriptor : IOMemoryDescriptor {
    uint8_t *bytes=nullptr;uint64_t size=0,base=0;unsigned prepared=0;
    static IOBufferMemoryDescriptor *inTaskWithOptions(task_t,unsigned,uint64_t size,uint64_t align) {
        auto m=new IOBufferMemoryDescriptor;m->size=size;m->base=next_pa;next_pa+=2*size+65536;
        assert(!posix_memalign((void **)&m->bytes,(size_t)align,(size_t)size));memset(m->bytes,0,(size_t)size);
        /* Physically scattered CPU16KiB pages, each with four GPU4KiB leaves. */
        for(uint64_t off=0;off<size;off+=4096)physical_pages[m->base+(off/16384)*32768+off%16384]=m->bytes+off;
        ++allocations;return m;
    }
    uint64_t getPhysicalSegment(uint64_t off,IOByteCount *length,unsigned) override {
        if(off>=size){*length=0;return 0;}
        *length=std::min(size-off,16384-off%16384);return base+(off/16384)*32768+off%16384;
    }
    IOReturn prepare() override {++prepared;return 0;}
    void complete() override {assert(prepared);--prepared;}
    void *getBytesNoCopy(){return bytes;}
    void free() override {
        assert(!prepared);
        for(uint64_t off=0;off<size;off+=4096)physical_pages.erase(base+(off/16384)*32768+off%16384);
        ::free(bytes);++frees;OSObject::free();
    }
};
extern "C" boolean_t pmap_valid_page(ppnum_t n)
{
    for(uint64_t i=0;i<16384;i+=4096)if(physical_pages.count((n<<14)+i))return 1;
    return 0;
}
extern "C" void flush_dcache64(addr64_t p,unsigned n,int phys)
{assert(p&&n&&!phys);++cache_calls;}
static int copyin(uint64_t p,void *out,size_t n){if(!p)return 1;memcpy(out,(const void *)(uintptr_t)p,n);return 0;}

@SURFACE_HEADER@

OSDefineMetaClassAndStructors(SweetSurface,OSObject);
static std::map<uint32_t,SweetSurface *> surface_table;
void SweetSurface::free(){OSSafeReleaseNULL(memory);OSObject::free();}
uintptr_t SweetSurface::kernelAddress(){return (uintptr_t)dynamic_cast<IOBufferMemoryDescriptor *>(memory)->getBytesNoCopy();}
SweetSurface *sweet_surface_copy(uint32_t id)
{auto i=surface_table.find(id);if(i==surface_table.end())return nullptr;i->second->retain();return i->second;}

static bool hardware_ready,fail_sync,fail_submit;
static uint64_t root_pa;static uint32_t completed;
static uint8_t *physical(uint64_t p)
{auto i=physical_pages.find(p&~UINT64_C(4095));assert(i!=physical_pages.end());return i->second+(p&4095);}
static uint64_t *pte(uint64_t va)
{
    auto dir=(uint64_t *)physical(root_pa);
    uint64_t index=(va-GGR_VA_START)/4096;
    auto table=(uint64_t *)physical(dir[index/512]&UINT64_C(0x0000fffffffff000));
    return table+index%512;
}
static uint32_t *gpu_word(uint64_t va,bool write=false)
{
    assert(va>=GGR_VA_START&&va<GGR_VA_END&&!(va&3));
    uint64_t entry=*pte(va);assert((entry&3)==3&&(!write||!(entry&0x80)));
    return (uint32_t *)physical((entry&UINT64_C(0x0000fffffffff000))+(va&4095));
}
extern "C" bool sweet_gpu_runtime_ready(){return hardware_ready;}
extern "C" bool sweet_gpu_runtime_install_root(uint64_t p){assert(!root_pa);root_pa=p;return hardware_ready;}
extern "C" bool sweet_gpu_runtime_sync(){++sync_calls;if(fail_sync)hardware_ready=false;return hardware_ready;}
extern "C" void sweet_gpu_runtime_stop(){hardware_ready=false;}
extern "C" bool sweet_gpu_runtime_heartbeat(){assert(lock_depth==1);++heartbeat_calls;return hardware_ready;}
extern "C" bool sweet_gpu_runtime_done(uint32_t f){return hardware_ready&&f&&f<=completed;}
extern "C" bool sweet_gpu_runtime_parameter(uint32_t which,uint64_t *v){if(which!=1)return false;*v=619;return true;}
extern "C" bool sweet_gpu_runtime_submit(const uint64_t *addresses,const uint32_t *words,uint32_t count,uint32_t *f)
{
    ++submit_calls;if(fail_submit){hardware_ready=false;return false;}
    for(uint32_t i=0;i<count;i++)for(uint32_t at=0;at<words[i];at+=4) {
        assert(*gpu_word(addresses[i]+4*at)==0x703d8003u);
        uint64_t address=*gpu_word(addresses[i]+4*(at+1));assert(!*gpu_word(addresses[i]+4*(at+2)));
        *gpu_word(address,true)=*gpu_word(addresses[i]+4*(at+3));
    }
    *f=++completed;return true;
}

@SOURCE@

static unsigned checks;
#define CHECK(x) do{++checks;assert(x);}while(0)
template<class T>static IOReturn request(GauguinGPUUserClient *c,uint32_t selector,T *r,int shape=0)
{
    T out;memset(&out,0xa5,sizeof(out));T unchanged=out;IOExternalMethodArguments a={r,&out,sizeof(T),sizeof(T),0,0,nullptr,nullptr};
    if(shape==1)--a.structureInputSize;if(shape==2)--a.structureOutputSize;
    if(shape==3)a.scalarInputCount=1;if(shape==4)a.structureInputDescriptor=r;
    IOReturn result=c->externalMethod(selector,&a,nullptr,nullptr,nullptr);
    if(result==0)*r=out;
    else CHECK(memcmp(&out,&unchanged,sizeof(out))==0);
    return result;
}
static uint32_t new_bo(GauguinGPUUserClient *c,uint64_t size,uint32_t flags=0)
{struct ggr_new n={size,flags,0};static unsigned attempt;attempt++;IOReturn rc=request(c,0x42,&n);
 if(rc||!n.handle)fprintf(stderr,"BO new failed attempt=%u size=%llu rc=%d\n",attempt,(unsigned long long)size,rc);
 CHECK(rc==0&&n.handle);return n.handle;}
static uint64_t address(GauguinGPUUserClient *c,uint32_t h)
{struct ggr_info i={h,1,0,0,0};CHECK(request(c,0x43,&i)==0);return i.value;}
static IOBufferMemoryDescriptor *mapped(GauguinGPUUserClient *c,uint32_t h)
{IOOptionBits opts=99;IOMemoryDescriptor *m=nullptr;CHECK(c->clientMemoryForType(h,&opts,&m)==0&&m&&opts==0);return dynamic_cast<IOBufferMemoryDescriptor *>(m);}
int main(int argc,char **argv)
{
#ifdef GAUGUIN_GPU_PILOT_HOST
    bool pilot = argc > 1 && strcmp(argv[1], "pilot") == 0;
    task_t mobile = (void *)2;
    pilot_mode = pilot;
#endif
    CHECK(!GauguinGPUHeartbeat()&&!heartbeat_calls);
    CHECK(!GauguinGPUStart());hardware_ready=true;CHECK(GauguinGPUStart());
    CHECK(GauguinGPUHeartbeat()&&heartbeat_calls==1&&!lock_depth);
#ifdef GAUGUIN_GPU_PILOT_HOST
    if (pilot) {
        auto trial = new GauguinGPUUserClient;
        mock_task = mobile;
        CHECK(!trial->initWithTask(mobile, nullptr, 0, nullptr));
        pilot_job = true;
        CHECK(!trial->initWithTask((void *)3, nullptr, 0, nullptr));
        CHECK(!trial->initWithTask(mobile, nullptr, 1, nullptr));
        CHECK(trial->initWithTask(mobile, nullptr, 0, nullptr));
        CHECK(mock_task_refs == 1);
        CHECK(!trial->start(IOService::getPlatform()));
        trial->release();
        CHECK(mock_task_refs == 0);
        mock_task = kernel_task;
        pilot_job = false;
    }
#endif
    auto c=new GauguinGPUUserClient;
    CHECK(!c->initWithTask((void *)2,nullptr,0,nullptr));CHECK(c->initWithTask(kernel_task,nullptr,0,nullptr)&&c->start(IOService::getPlatform()));
    auto other=new GauguinGPUUserClient;CHECK(other->initWithTask(kernel_task,nullptr,0,nullptr));CHECK(!other->start(IOService::getPlatform()));other->release();
    struct ggr_param p={0x10,1,0,0,0};CHECK(request(c,0x40,&p)==0&&p.value==619);
    for(int shape=1;shape<=4;shape++)CHECK(request(c,0x40,&p,shape)==kIOReturnBadArgument);
    p.pipe=0;CHECK(request(c,0x40,&p)==kIOReturnBadArgument);
    struct ggr_new invalid={0,0,0};CHECK(request(c,0x42,&invalid)==kIOReturnBadArgument);
    invalid.size=GGR_MAX_BO_BYTES+1;CHECK(request(c,0x42,&invalid)==kIOReturnBadArgument);
    if(argc>1&&strcmp(argv[1],"slots")==0) {
        static_assert(GGR_MAX_BUFFERS==256u,"per-submit ABI limit stays256");
        static_assert(GGR_MAX_CLIENT_BYTES==(256u<<20),"byte residency quota stays256MiB");
        static_assert(GGR_MAX_CLIENT_BUFFERS==1024u,"bounded private live-object table");
        uint32_t previous=0;unsigned persistent=allocations-frees;
        for(unsigned cycle=0;cycle<3;cycle++) {
            std::vector<uint32_t> handles;
            for(unsigned i=0;i<GGR_MAX_CLIENT_BUFFERS;i++) {
                uint32_t h=new_bo(c,16384,(i&1)?GGR_BO_READONLY:0);
                CHECK(h>previous);previous=h;handles.push_back(h);
            }
            struct ggr_new full={16384,GGR_BO_READONLY,0};
            CHECK(request(c,0x42,&full)==kIOReturnNoResources&&full.handle==0&&hardware_ready);
            CHECK(allocations-frees==persistent+GGR_MAX_CLIENT_BUFFERS);
            CHECK(address(c,handles.back())>=GGR_VA_START);
            uint32_t old=handles[0];uint64_t old_va=address(c,old);
            struct ggr_close close={old,0};CHECK(request(c,0x09,&close)==0);
            struct ggr_info missing={old,0,0,0,0};CHECK(request(c,0x43,&missing)==kIOReturnBadArgument);
            uint32_t replacement=new_bo(c,16384);CHECK(replacement>previous);
            previous=replacement;handles[0]=replacement;
            CHECK(address(c,replacement)==old_va);
            for(uint32_t h:handles){close={h,0};CHECK(request(c,0x09,&close)==0);}
            CHECK(allocations-frees==persistent&&hardware_ready);
        }
        std::vector<uint32_t> large;
        for(unsigned i=0;i<4;i++)large.push_back(new_bo(c,GGR_MAX_BO_BYTES));
        struct ggr_new quota={16384,0,0};CHECK(request(c,0x42,&quota)==kIOReturnNoResources&&quota.handle==0);
        CHECK(allocations-frees==persistent+4&&hardware_ready);
        for(uint32_t h:large){struct ggr_close close={h,0};CHECK(request(c,0x09,&close)==0);}
        struct ggr_submit oversized={};oversized.flags=0x10;oversized.nr_bos=GGR_MAX_BUFFERS+1;
        oversized.nr_cmds=1;oversized.fence_fd=-1;oversized.bos=1;oversized.cmds=1;
        CHECK(request(c,0x46,&oversized)==kIOReturnBadArgument&&hardware_ready);
        CHECK(c->clientClose()==0&&allocations-frees==persistent&&!gOwner);c->release();
        printf("PASS: %u private BO-slot saturation/reuse/byte-quota/submit-bound assertions\n",checks);
        return 0;
    }
    uint32_t data=new_bo(c,20000),commands=new_bo(c,16384,GGR_BO_READONLY);
    uint64_t data_va=address(c,data),command_va=address(c,commands);
    CHECK(!(data_va&65535)&&!(command_va&65535)&&data_va!=command_va);
    auto data_m=mapped(c,data);auto command_m=mapped(c,commands);
    CHECK(data_m->size==32768&&command_m->size==16384);
    IOByteCount length=0;CHECK((*pte(data_va)&UINT64_C(0x0000fffffffff000))==data_m->getPhysicalSegment(0,&length,0));
    CHECK((*pte(data_va+16384)&UINT64_C(0x0000fffffffff000))==data_m->getPhysicalSegment(16384,&length,0));
    CHECK((*pte(data_va+16384)&UINT64_C(0x0000fffffffff000))!=data_m->base+16384);
    CHECK((*pte(command_va)&0x80)&&!(*pte(data_va)&0x80));
    auto words=(uint32_t *)command_m->getBytesNoCopy();
    uint32_t cmdwords[]={0x703d8003u,(uint32_t)data_va,0,0x11223344,0x703d8003u,(uint32_t)(data_va+32764),0,0x55667788};
    memcpy(words,cmdwords,sizeof(cmdwords));
    struct ggr_submit_bo bos[]={{3,data,data_va},{1,commands,command_va}};
    struct ggr_submit_cmd cmd={1,1,0,sizeof(cmdwords),0,0,0};
    struct ggr_submit s={};s.flags=0x10;s.nr_bos=2;s.nr_cmds=1;s.bos=(uintptr_t)bos;s.cmds=(uintptr_t)&cmd;s.fence_fd=-1;
#ifdef GAUGUIN_GPU_PILOT_HOST
    if (pilot) {
        for (uint32_t n = 1; n <= 6; n++) {
            s.fence = 0;
            CHECK(request(c, 0x46, &s) == 0 && s.fence == n && completed == n);
        }
        CHECK(gReleasedRootFence == 0 && gOwner == c);
        auto waiting = new GauguinGPUUserClient;
        mock_task = mobile;
        pilot_job = true;
        CHECK(waiting->initWithTask(mobile, nullptr, 0, nullptr));
        CHECK(!waiting->start(IOService::getPlatform()));
        waiting->release();
        mock_task = kernel_task;
        data_m->release();
        command_m->release();
        CHECK(c->clientClose() == 0 && gReleasedRootFence == 6 && !gOwner);
        c->release();
        auto client = new GauguinGPUUserClient;
        mock_task = mobile;
        CHECK(client->initWithTask(mobile, nullptr, 0, nullptr));
        CHECK(mock_task_refs == 1);
        CHECK(client->start(IOService::getPlatform()) && gOwner == client);
        struct ggr_param parameter = {0x10, 1, 0, 0, 0};
        CHECK(request(client, 0x40, &parameter) == 0 && parameter.value == 619);
        uint32_t handle = new_bo(client, 16384);
        IOOptionBits options = 99;
        IOMemoryDescriptor *mapped_buffer = nullptr;
        mock_task = (void *)3;
        CHECK(request(client, 0x40, &parameter) == kIOReturnNotPrivileged);
        CHECK(client->clientMemoryForType(handle, &options, &mapped_buffer) == kIOReturnNotPrivileged);
        CHECK(options == 99 && !mapped_buffer);
        mock_task = mobile;
        mapped(client, handle)->release();
        CHECK(client->clientClose() == 0 && !gOwner && gReleasedRootFence == 6);
        client->release();
        CHECK(mock_task_refs == 0);
        printf("PASS: %u owning-task and root-to-compositor pilot assertions\n", checks);
        return 0;
    }
#endif
    if(argc>1&&strcmp(argv[1],"queues")==0) {
        struct ggr_queue q1={0,0,0},q2={0,0,0},bad={1,0,0};
        CHECK(request(c,0x4a,&bad)==kIOReturnBadArgument);
        bad={0,1,0};CHECK(request(c,0x4a,&bad)==kIOReturnBadArgument);
        bad={0,0,123};CHECK(request(c,0x4a,&bad)==kIOReturnBadArgument);
        CHECK(request(c,0x4a,&q1)==0&&q1.id==1);
        CHECK(request(c,0x4a,&q2)==0&&q2.id==2);
        s.queueid=q1.id;CHECK(request(c,0x46,&s)==0&&s.fence==1&&completed==1);
        s.queueid=q2.id;s.fence=0;CHECK(request(c,0x46,&s)==0&&s.fence==1&&completed==2);
        struct ggr_wait w={2,0,{1,0},q1.id};
        CHECK(request(c,0x47,&w)==kIOReturnBadArgument); /* q2's hardware2 is not q1's fence2 */
        w.fence=1;CHECK(request(c,0x47,&w)==0);
        w.queueid=q2.id;CHECK(request(c,0x47,&w)==0);
        w.queueid=0;CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        s.queueid=0;s.fence=0;CHECK(request(c,0x46,&s)==kIOReturnBadArgument&&submit_calls==2);
        s.queueid=q1.id;CHECK(request(c,0x46,&s)==0&&s.fence==2&&completed==3);
        w={2,0,{1,0},q1.id};CHECK(request(c,0x47,&w)==0);
        w.queueid=q2.id;CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        uint32_t closing=q2.id;CHECK(request(c,0x4b,&closing)==0);
        CHECK(request(c,0x4b,&closing)==kIOReturnBadArgument);
        w.fence=1;CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        w.queueid=0;w.fence=2;CHECK(request(c,0x47,&w)==0); /* unambiguous legacy alias */
        std::vector<uint32_t> ids={q1.id};
        for(unsigned i=1;i<GGR_MAX_QUEUES;i++) {
            struct ggr_queue q={0,0,0};CHECK(request(c,0x4a,&q)==0&&q.id>q2.id);
            ids.push_back(q.id);
            w={1,0,{1,0},q.id};CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        }
        struct ggr_queue full={0,0,0};CHECK(request(c,0x4a,&full)==kIOReturnNoResources&&full.id==0);
        s.queueid=ids.back();s.fence=0;CHECK(request(c,0x46,&s)==0&&s.fence==1&&completed==4);
        w={2,0,{1,0},ids.back()};CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        w.fence=1;CHECK(request(c,0x47,&w)==0);
        closing=0;CHECK(request(c,0x4b,&closing)==kIOReturnBadArgument);
        for(auto id:ids){closing=id;CHECK(request(c,0x4b,&closing)==0);}
        w={1,0,{1,0},q1.id};CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        /* Empty default namespace cannot inherit a closed explicit queue's completion. */
        w.queueid=0;CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        s.queueid=0;s.fence=0;CHECK(request(c,0x46,&s)==0&&s.fence==1&&completed==5);
        struct ggr_queue later={0,0,0};CHECK(request(c,0x4a,&later)==0&&later.id>ids.back());
        w={1,0,{1,0},0};CHECK(request(c,0x47,&w)==0); /* default keeps its identity */
        w.queueid=later.id;CHECK(request(c,0x47,&w)==kIOReturnBadArgument);
        data_m->release();command_m->release();CHECK(c->clientClose()==0);c->release();
        CHECK(!*pte(data_va)&&!*pte(command_va));
        printf("PASS: %u actual IOKit queue assertions; interleaved native completions, local fences, no hardware claim\n",checks);
        return 0;
    }
    cmd.submit_offset=32768;CHECK(request(c,0x46,&s)==kIOReturnBadArgument&&submit_calls==0);cmd.submit_offset=0;
    bos[1].flags=3;CHECK(request(c,0x46,&s)==kIOReturnBadArgument&&submit_calls==0);bos[1].flags=1;
    bos[1].handle=data;CHECK(request(c,0x46,&s)==kIOReturnBadArgument&&submit_calls==0);bos[1].handle=commands;
    CHECK(request(c,0x46,&s)==0&&s.fence==1&&submit_calls==1);
    CHECK(((uint32_t *)data_m->bytes)[0]==0x11223344&&((uint32_t *)data_m->bytes)[8191]==0x55667788);
    struct ggr_wait wait={1,0,{1,0},0};CHECK(request(c,0x47,&wait)==0);wait.fence=2;CHECK(request(c,0x47,&wait)==kIOReturnBadArgument);
    struct ggr_close close={data,0};CHECK(request(c,9,&close)==0&&!*pte(data_va));
    struct ggr_info stale={data,1,0,0,0};CHECK(request(c,0x43,&stale)==kIOReturnBadArgument);
    uint32_t replacement=new_bo(c,20000);CHECK(replacement!=data&&address(c,replacement)==data_va);
    /* Closing the handle does not revoke/alias a still-held CPU descriptor. */
    CHECK(((uint32_t *)data_m->bytes)[0]==0x11223344);data_m->release();
    auto surface=new SweetSurface;CHECK(surface->init());surface->id=123;
    surface->memory=IOBufferMemoryDescriptor::inTaskWithOptions(kernel_task,0,16384,16384);
    surface->width=64;surface->height=32;surface->offset=128;surface->allocSize=16384;
    surface->bytesPerElement=4;surface->bytesPerRow=256;surface->pixelFormat=0x42475241;surface->planeCount=0;
    surface_table[123]=surface;
    struct ggr_surface surf={};surf.surface=123;surf.handle=UINT32_MAX;
    CHECK(request(c,0x7e,&surf)==0&&surf.handle==0&&surf.offset==128&&surf.rowBytes==256);
    CHECK(request(c,0x7e,&surf)==0&&surf.handle);uint32_t surface_handle=surf.handle;
    uint64_t surface_va=address(c,surf.handle);
    CHECK((*pte(surface_va)&UINT64_C(0x0000fffffffff000))==surface->memory->getPhysicalSegment(0,&length,0));
    CHECK(request(c,0x7e,&surf)==0&&surf.handle==surface_handle);
    words[1]=(uint32_t)(surface_va+128);words[3]=0xff336699;
    bos[0]={3,surf.handle,surface_va};cmd.size=16;s.fence=0;
    CHECK(request(c,0x46,&s)==0&&s.fence==2&&cache_calls==2&&surface->gpuState==0);
    CHECK(*(uint32_t *)(surface->kernelAddress()+128)==0xff336699);
    uint32_t token=GauguinGPUSurfaceBegin(surface);CHECK(token==2);GauguinGPUSurfaceEnd(token);
    surface->gpuState=2;CHECK(!GauguinGPUSurfaceBegin(surface));surface->gpuState=0;
    /* A completed close/new client is allowed; all PTEs are gone before the
     * old memory is completed/released. A failed close is never recycled. */
    command_m->release();CHECK(c->clientClose()==0&&!*pte(command_va)&&!*pte(surface_va));c->release();
    c=new GauguinGPUUserClient;CHECK(c->initWithTask(kernel_task,nullptr,0,nullptr)&&c->start(IOService::getPlatform()));
    unsigned freed=frees;
    if(argc>1&&strcmp(argv[1],"sync")==0) {
        fail_sync=true;struct ggr_new n={16384,0,0};CHECK(request(c,0x42,&n)==kIOReturnNotReady&&n.handle==0);
    } else {
        commands=new_bo(c,16384,GGR_BO_READONLY);command_m=mapped(c,commands);command_va=address(c,commands);
        surf.handle=0;CHECK(request(c,0x7e,&surf)==0);surface_va=address(c,surf.handle);
        words=(uint32_t *)command_m->getBytesNoCopy();words[0]=0x703d8003u;words[1]=(uint32_t)surface_va;words[2]=0;words[3]=0xabcdef;
        bos[0]={3,surf.handle,surface_va};bos[1]={1,commands,command_va};s.fence=0;s.bos=(uintptr_t)bos;fail_submit=true;
        CHECK(request(c,0x46,&s)==kIOReturnTimeout&&s.fence==0&&surface->gpuState==2);
        CHECK(!GauguinGPUSurfaceBegin(surface));command_m->release();
    }
    CHECK(!hardware_ready&&c->clientClose()==0&&frees==freed);c->release();
    CHECK(!GauguinGPUHeartbeat()&&heartbeat_calls==2&&!lock_depth&&frees==freed);
    c=new GauguinGPUUserClient;CHECK(c->initWithTask(kernel_task,nullptr,0,nullptr)&&!c->start(IOService::getPlatform()));c->release();
    CHECK(allocations>frees&&sync_calls>0);
    printf("PASS: %u actual IOKit transport assertions (%s); typed seams, no hardware qualification\n",checks,argc>1?argv[1]:"submit");
}
