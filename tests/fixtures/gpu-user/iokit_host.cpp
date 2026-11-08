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
#define IOLog(...) ((void)0)
using UInt32=uint32_t;using IOOptionBits=uint32_t;using IOReturn=int;
using IOByteCount=uint64_t;using addr64_t=uint64_t;using vm_size_t=uint64_t;
using uintptr_t=std::uintptr_t;using task_t=void *;using ppnum_t=uint64_t;
using boolean_t=int;using mach_port_name_t=uint32_t;
static task_t kernel_task=(void *)1;
enum {kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNoResources=2,kIOReturnNoMemory=3,
    kIOReturnVMError=4,kIOReturnNotReady=5,kIOReturnNotFound=6,kIOReturnUnsupported=7,kIOReturnTimeout=8};
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
    T out={};IOExternalMethodArguments a={r,&out,sizeof(T),sizeof(T),0,0,nullptr,nullptr};
    if(shape==1)--a.structureInputSize;if(shape==2)--a.structureOutputSize;
    if(shape==3)a.scalarInputCount=1;if(shape==4)a.structureInputDescriptor=r;
    IOReturn result=c->externalMethod(selector,&a,nullptr,nullptr,nullptr);
    if(result==0)*r=out;
    return result;
}
static uint32_t new_bo(GauguinGPUUserClient *c,uint64_t size,uint32_t flags=0)
{struct ggr_new n={size,flags,0};CHECK(request(c,0x42,&n)==0&&n.handle);return n.handle;}
static uint64_t address(GauguinGPUUserClient *c,uint32_t h)
{struct ggr_info i={h,1,0,0,0};CHECK(request(c,0x43,&i)==0);return i.value;}
static IOBufferMemoryDescriptor *mapped(GauguinGPUUserClient *c,uint32_t h)
{IOOptionBits opts=99;IOMemoryDescriptor *m=nullptr;CHECK(c->clientMemoryForType(h,&opts,&m)==0&&m&&opts==0);return dynamic_cast<IOBufferMemoryDescriptor *>(m);}
int main(int argc,char **argv)
{
    CHECK(!GauguinGPUHeartbeat()&&!heartbeat_calls);
    CHECK(!GauguinGPUStart());hardware_ready=true;CHECK(GauguinGPUStart());
    CHECK(GauguinGPUHeartbeat()&&heartbeat_calls==1&&!lock_depth);
    auto c=new GauguinGPUUserClient;
    CHECK(!c->initWithTask((void *)2,nullptr,0,nullptr));CHECK(c->initWithTask(kernel_task,nullptr,0,nullptr)&&c->start(IOService::getPlatform()));
    auto other=new GauguinGPUUserClient;CHECK(other->initWithTask(kernel_task,nullptr,0,nullptr));CHECK(!other->start(IOService::getPlatform()));other->release();
    struct ggr_param p={0x10,1,0,0,0};CHECK(request(c,0x40,&p)==0&&p.value==619);
    for(int shape=1;shape<=4;shape++)CHECK(request(c,0x40,&p,shape)==kIOReturnBadArgument);
    p.pipe=0;CHECK(request(c,0x40,&p)==kIOReturnBadArgument);
    struct ggr_new invalid={0,0,0};CHECK(request(c,0x42,&invalid)==kIOReturnBadArgument);
    invalid.size=GGR_MAX_BO_BYTES+1;CHECK(request(c,0x42,&invalid)==kIOReturnBadArgument);
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
