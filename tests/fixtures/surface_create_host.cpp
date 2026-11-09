/* Production create/layout/free/map methods are inserted below. Only the
 * property decoder, IOKit VM operations and publication boundary are seams. */
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <initializer_list>
#include <map>
#include <string>
#include <vector>

using IOReturn = int;
using IOByteCount = uint64_t;
using SInt64 = int64_t;
using task_t = uintptr_t;
using IOMemoryMap = struct Mapping;
constexpr IOReturn kIOReturnSuccess=0, KERN_PROTECTION_FAILURE=2,
    kIOReturnBadArgument=0x101, kIOReturnNoMemory=0x102, kIOReturnVMError=0x103,
    kIOReturnNoResources=0x104, kIOReturnUnsupported=0x105;
constexpr unsigned kIODirectionInOut=3, kIODirectionOut=2, kIOMemoryThreadSafe=0x100000,
    kIOMemoryKernelUserShared=0x200000, kIOMapAnywhere=0x2000, kIOMapReadOnly=0x1000,
    kIOMapDefaultCache=0, SWEET_SURFACE_ROW_ALIGN=64, SWEET_SURFACE_MAX_PLANES=20;
constexpr uint32_t SWEET_SURFACE_RESULT_SIZE=0xa68, SWEET_SURFACE_MAX_DIM=16384,
    SWEET_SURFACE_MAX_ALLOC=256u<<20, SWEET_SURFACE_MAX_PROPS=64u<<10;
constexpr uint64_t SWEET_SURFACE_WIRED_MAX=1536ull<<20, PAGE_MASK=16383,
    page_size=16384;
constexpr task_t kernel_task=1;
static uint64_t sweet_surface_wired;
static uint32_t sweet_surface_creates_logged;
static uint64_t round_page(uint64_t n){return (n+PAGE_MASK)&~PAGE_MASK;}
static SInt64 OSAddAtomic64(SInt64 n,volatile SInt64 *p){return __atomic_fetch_add(p,n,__ATOMIC_SEQ_CST);}
static void proc_selfname(char *p,size_t n){std::snprintf(p,n,"fixture");}
static void IOLog(const char *,...){}
#define OSDynamicCast(T,p) dynamic_cast<T *>(p)
#define OSSafeReleaseNULL(p) do{if(p){(p)->release();(p)=nullptr;}}while(0)
static unsigned assertions, activeMaps, activePins, activeDescriptors, activeSurfaces;
static unsigned prepares, completes, allocated, buffers, published, returned;
static unsigned failDescriptorAt, failPrepareAt;
static IOReturn prepareError=kIOReturnVMError;
static bool failSurface,failPublish,failReturn,failBuffer,failMap,immutable;
static bool mapLocked;
static int *sweet_surface_lock;
static void IOLockLock(int *){assert(!mapLocked);mapLocked=true;}
static void IOLockUnlock(int *){assert(mapLocked);mapLocked=false;}
static void check(bool b){++assertions;assert(b);}

struct OSObject {
    unsigned refs=1;
    virtual ~OSObject()=default;
    virtual void free(){}
    void retain(){++refs;}
    void release(){assert(refs);if(!--refs){free();delete this;}}
};
struct OSNumber:OSObject {
    uint64_t value;
    explicit OSNumber(uint64_t v):value(v){}
    uint64_t unsigned64BitValue(){return value;}
    uint32_t unsigned32BitValue(){return uint32_t(value);}
};
struct OSDictionary:OSObject {
    std::map<std::string,OSObject *> values;
    ~OSDictionary() override{for(auto &v:values)v.second->release();}
    OSObject *getObject(const char *key){auto i=values.find(key);return i==values.end()?nullptr:i->second;}
    unsigned getCount(){return unsigned(values.size());}
    void set(const char *key,OSObject *p){auto i=values.find(key);if(i!=values.end())i->second->release();values[key]=p;}
    void num(const char *key,uint64_t v){set(key,new OSNumber(v));}
    void remove(const char *key){auto i=values.find(key);if(i!=values.end()){i->second->release();values.erase(i);}}
};
struct OSArray:OSObject {
    std::vector<OSObject *> values;
    ~OSArray() override{for(auto *v:values)v->release();}
    unsigned getCount(){return unsigned(values.size());}
    OSObject *getObject(unsigned i){return values.at(i);}
};
static OSDictionary *decoded;
static OSObject *OSUnserializeXML(const char *,uint32_t){if(decoded)decoded->retain();return decoded;}
static void *IOMallocData(size_t n){return std::malloc(n);}
static void IOFreeData(void *p,size_t){std::free(p);}

struct IOMemoryDescriptor:OSObject {
    uint64_t address=0,length=0;
    unsigned pins=0,direction=0;
    bool owned=false;
    IOMemoryDescriptor(){++activeDescriptors;}
    ~IOMemoryDescriptor() override{assert(!pins);--activeDescriptors;if(owned)std::free(reinterpret_cast<void *>(address));}
    static IOMemoryDescriptor *withAddressRange(uint64_t a,uint64_t n,unsigned flags,task_t task){
        ++allocated;check(task==42);
        check(flags==(kIODirectionInOut|kIOMemoryThreadSafe)||flags==(kIODirectionOut|kIOMemoryThreadSafe));
        if(failDescriptorAt==allocated)return nullptr;
        auto *m=new IOMemoryDescriptor;m->address=a;m->length=n;m->direction=flags&3;return m;
    }
    IOReturn prepare(){
        ++prepares;if(failPrepareAt==prepares)return prepareError;
        if(immutable&&direction==kIODirectionInOut)return KERN_PROTECTION_FAILURE;
        ++pins;++activePins;return 0;
    }
    IOReturn complete(){check(pins==1&&!activeMaps);--pins;--activePins;++completes;return 0;}
    Mapping *map(unsigned);
    Mapping *createMappingInTask(task_t,uint64_t,unsigned);
};
struct IOBufferMemoryDescriptor:IOMemoryDescriptor {
    static IOBufferMemoryDescriptor *inTaskWithOptions(task_t task,unsigned flags,uint64_t n,uint64_t alignment){
        check(task==kernel_task&&flags==(kIODirectionInOut|kIOMemoryKernelUserShared)&&alignment==page_size);
        ++buffers;if(failBuffer)return nullptr;
        auto *m=new IOBufferMemoryDescriptor;m->owned=true;m->length=n;
        m->address=reinterpret_cast<uintptr_t>(std::calloc(1,size_t(n)));check(m->address!=0);return m;
    }
    void *getBytesNoCopy(){return reinterpret_cast<void *>(address);}
};
struct Mapping:OSObject {
    IOMemoryDescriptor *memory;unsigned options;task_t task;
    Mapping(IOMemoryDescriptor *m,unsigned f,task_t t):memory(m),options(f),task(t){m->retain();++activeMaps;}
    ~Mapping() override{--activeMaps;memory->release();}
    uint64_t getVirtualAddress(){return memory->address;}
};
Mapping *IOMemoryDescriptor::map(unsigned options){check(mapLocked);return failMap?nullptr:new Mapping(this,options,kernel_task);}
Mapping *IOMemoryDescriptor::createMappingInTask(task_t task,uint64_t at,unsigned options){
    check(at==0&&(options&kIOMapAnywhere));
    if(immutable&&!owned)check(options&kIOMapReadOnly);
    return failMap?nullptr:new Mapping(this,options,task);
}
struct sweet_surface_plane {
    uint32_t width=0,height=0,bytesPerRow=0,offset=0,size=0;
    uint16_t bytesPerElement=0;uint8_t elementWidth=0,elementHeight=0;
};
struct SweetSurface:OSObject {
    uint32_t id=0,width=0,height=0,bytesPerRow=0,offset=0,pixelFormat=0,allocSize=0;
    uint16_t bytesPerElement=0;uint8_t elementWidth=0,elementHeight=0;
    uint32_t cacheMode=0,planeCount=0,parentID=0,gpuState=0,wiredSize=0;
    sweet_surface_plane planes[SWEET_SURFACE_MAX_PLANES];
    IOMemoryDescriptor *memory=nullptr,*state=nullptr;
    Mapping *kernelMap=nullptr;unsigned mapCache=0;bool memoryPrepared=false,readOnly=false;
    SweetSurface(){++activeSurfaces;}
    ~SweetSurface() override{--activeSurfaces;}
    void free() override;uintptr_t kernelAddress();Mapping *mapPixelsInTask(task_t);
};
static SweetSurface *table;
static SweetSurface *sweet_surface_alloc(){if(failSurface)return nullptr;auto *s=new SweetSurface;s->state=new IOMemoryDescriptor;return s;}
static bool sweet_surface_publish(SweetSurface *s){
    ++published;if(failPublish)return false;
    check(!table&&s->memory&&s->state);check(s->memoryPrepared||dynamic_cast<IOBufferMemoryDescriptor *>(s->memory));
    s->id=17;s->retain();table=s;return true;
}
static void dropTable(){auto *s=table;table=nullptr;if(s)s->release();}
struct StructureDescriptor {
    const void *bytes;IOByteCount length;
    IOByteCount getLength(){return length;}
    IOByteCount readBytes(IOByteCount at,void *out,IOByteCount n){check(!at&&n<=length);std::memcpy(out,bytes,size_t(n));return n;}
};
struct IOExternalMethodArguments {
    unsigned scalarInputCount=0,scalarOutputCount=0;uint64_t *scalarInput=nullptr;
    const void *structureInput=nullptr;uint32_t structureInputSize=0,structureOutputSize=SWEET_SURFACE_RESULT_SIZE;
    StructureDescriptor *structureInputDescriptor=nullptr;
};
struct IOSurfaceRootUserClient {
    task_t fTask=42;
    IOReturn create(IOExternalMethodArguments *);
    IOReturn returnSurface(SweetSurface *s,IOExternalMethodArguments *){
        ++returned;check(s==table&&s->memory&&s->state);
        if(failReturn){dropTable();return kIOReturnVMError;}return 0;
    }
};

@METHODS@

static OSDictionary *image(uint64_t address,bool client=true){
    auto *p=new OSDictionary;
    p->num("IOSurfaceWidth",180);p->num("IOSurfaceHeight",180);
    p->num("IOSurfaceBytesPerElement",4);p->num("IOSurfaceBytesPerRow",720);
    p->num("IOSurfacePixelFormat",0);p->num("IOSurfaceAllocSize",129600);
    if(client)p->num("IOSurfaceAddress",address);return p;
}

int main(){
    IOSurfaceRootUserClient client;
    alignas(16384) uint8_t pixels[262144];
    for(size_t i=0;i<sizeof(pixels);++i)pixels[i]=uint8_t(i*17+3);
    auto clear=[&](){
        dropTable();check(!activeSurfaces&&!activeDescriptors&&!activeMaps&&!activePins&&!sweet_surface_wired&&!mapLocked);
        failSurface=failPublish=failReturn=failBuffer=failMap=immutable=false;
        failDescriptorAt=failPrepareAt=allocated=buffers=prepares=completes=published=returned=0;
        prepareError=kIOReturnVMError;
    };
    auto run=[&](OSDictionary *p,bool descriptor=false){
        const char xml[]="<dict/>";IOExternalMethodArguments a;
        a.structureInput=xml;a.structureInputSize=sizeof(xml);
        StructureDescriptor input{xml,sizeof(xml)};
        if(descriptor){a.structureInput=nullptr;a.structureInputDescriptor=&input;}
        decoded=p;IOReturn ret=client.create(&a);decoded=nullptr;p->release();return ret;
    };
    const uint64_t address=reinterpret_cast<uintptr_t>(pixels);
    check(run(image(address))==0);
    if(!table||dynamic_cast<IOBufferMemoryDescriptor *>(table->memory)||table->memory->address!=address){
        std::fprintf(stderr,"FAIL IOSurfaceCreate ignored caller image storage\n");dropTable();return 42;
    }
    check(table->allocSize==129600&&table->memory->length==129600&&table->wiredSize==131072);
    check(table->width==180&&table->height==180&&table->bytesPerRow==720&&table->bytesPerElement==4);
    check(allocated==1&&prepares==1&&completes==0&&buffers==0);
    auto *first=table->mapPixelsInTask(42),*lookup=table->mapPixelsInTask(84);
    check(first&&lookup&&first->getVirtualAddress()==address&&lookup->getVirtualAddress()==address);
    uint8_t value=pixels[123];pixels[123]=77;
    check(reinterpret_cast<uint8_t *>(lookup->getVirtualAddress())[123]==77);
    reinterpret_cast<uint8_t *>(first->getVirtualAddress())[123]=value;
    check(pixels[123]==value);first->release();lookup->release();
    check(table->kernelAddress()==address&&table->kernelAddress()==address);clear();
    check(run(image(address),true)==0);clear();
    auto *p=image(address+3);check(run(p)==0&&table->wiredSize==131072);clear();
    p=image(address);p->remove("IOSurfaceAllocSize");check(run(p)==0&&table->allocSize==129600);clear();
    p=image(address);p->num("IOSurfaceWidth",179);p->num("IOSurfaceAllocSize",129596);
    check(run(p)==0&&table->allocSize==129596&&table->memory->length==129596);clear();
    p=image(address);p->num("IOSurfaceOffset",8);p->num("IOSurfaceAllocSize",129608);
    check(run(p)==0&&table->offset==8&&table->memory->length==129608);clear();
    // A writable original stays a shared writable mapping, never a snapshot.
    for(unsigned cycle=0;cycle<3;cycle++){check(run(image(address))==0&&!table->readOnly);clear();}
    immutable=true;check(run(image(address))==0&&table->readOnly&&allocated==2&&prepares==2);
    check(table->memory->direction==kIODirectionOut&&activePins==1);
    first=table->mapPixelsInTask(42);lookup=table->mapPixelsInTask(84);
    check((first->options&kIOMapReadOnly)&&(lookup->options&kIOMapReadOnly));
    first->release();lookup->release();check(table->kernelAddress()==address&&(table->kernelMap->options&kIOMapReadOnly));clear();

    // Ordinary creates keep their independent zeroed and page-rounded buffer.
    check(run(image(address,false))==0&&buffers==1&&!allocated&&!prepares);
    check(table->allocSize==131072&&!table->memoryPrepared&&!table->readOnly);
    auto *buffer=dynamic_cast<IOBufferMemoryDescriptor *>(table->memory);check(buffer&&buffer->address!=address);
    auto *bytes=static_cast<uint8_t *>(buffer->getBytesNoCopy());
    check(std::all_of(bytes,bytes+buffer->length,[](uint8_t v){return v==0;}));clear();

    for(unsigned bad=0;bad<18;bad++){
        p=image(address);
        switch(bad){
        case 0:p->num("IOSurfaceAddress",0);break;
        case 1:p->num("IOSurfaceAddress",UINT64_MAX-2);break;
        case 2:p->set("IOSurfaceAddress",new OSObject);break;
        case 3:p->num("IOSurfaceWidth",0);break;
        case 4:p->num("IOSurfaceHeight",0);break;
        case 5:p->num("IOSurfaceWidth",(uint64_t(1)<<32)+180);break;
        case 6:p->num("IOSurfaceBytesPerElement",65540);break;
        case 7:p->num("IOSurfaceElementWidth",257);break;
        case 8:p->num("IOSurfaceElementHeight",0);break;
        case 9:p->num("IOSurfaceBytesPerRow",719);break;
        case 10:p->num("IOSurfaceAllocSize",129599);break;
        case 11:p->num("IOSurfaceAllocSize",0);break;
        case 12:p->num("IOSurfaceAllocSize",uint64_t(SWEET_SURFACE_MAX_ALLOC)+1);break;
        case 13:p->num("IOSurfaceOffset",SWEET_SURFACE_MAX_ALLOC);break;
        case 14:p->set("IOSurfaceWidth",new OSObject);break;
        case 15:p->set("IOSurfacePlaneInfo",new OSObject);break;
        case 16:p->num("IOSurfaceBytesPerElement",0);break;
        case 17:p->num("IOSurfacePixelFormat",uint64_t(1)<<32);break;
        }
        check(run(p)!=0&&!allocated&&!published&&!returned);clear();
    }
    p=image(address);p->set("IOSurfaceAddressRanges",new OSArray);
    check(run(p)==kIOReturnUnsupported&&!allocated&&!published);clear();

    auto planes=[&](){
        auto *q=image(address);auto *a=new OSArray;
        for(unsigned i=0;i<2;i++){
            auto *plane=new OSDictionary;
            plane->num("IOSurfacePlaneWidth",i?90:180);plane->num("IOSurfacePlaneHeight",i?90:180);
            plane->num("IOSurfacePlaneBytesPerElement",i?2:1);plane->num("IOSurfacePlaneBytesPerRow",192);
            plane->num("IOSurfacePlaneOffset",i?49152:0);plane->num("IOSurfacePlaneSize",i?17280:34560);
            a->values.push_back(plane);
        }
        q->set("IOSurfacePlaneInfo",a);return q;
    };
    check(run(planes())==0&&table->planeCount==2&&table->allocSize==129600);clear();
    for(unsigned bad=0;bad<6;bad++){
        p=planes();auto *a=dynamic_cast<OSArray *>(p->getObject("IOSurfacePlaneInfo"));
        auto *plane=dynamic_cast<OSDictionary *>(a->getObject(0));
        switch(bad){
        case 0:plane->num("IOSurfacePlaneBytesPerRow",179);break;
        case 1:plane->num("IOSurfacePlaneSize",1);break;
        case 2:plane->num("IOSurfacePlaneBytesPerElement",65537);break;
        case 3:plane->num("IOSurfacePlaneWidth",0);break;
        case 4:plane->num("IOSurfacePlaneOffset",129599);break;
        case 5:a->values[0]->release();a->values[0]=new OSObject;break;
        }
        check(run(p)!=0&&!allocated&&!published);clear();
    }
    // Every failed preparation/publication leaves no live pin or quota charge.
    failSurface=true;check(run(image(address))==kIOReturnNoMemory);clear();
    failDescriptorAt=1;check(run(image(address))==kIOReturnNoMemory&&!prepares);clear();
    for(IOReturn error:{kIOReturnNoMemory,kIOReturnVMError,kIOReturnBadArgument}){
        failPrepareAt=1;prepareError=error;check(run(image(address))==error&&allocated==1&&!completes&&!published);clear();
    }
    immutable=true;failDescriptorAt=2;check(run(image(address))==kIOReturnNoMemory&&prepares==1&&!published);clear();
    immutable=true;failPrepareAt=2;check(run(image(address))==kIOReturnVMError&&prepares==2&&!published);clear();
    failPublish=true;check(run(image(address))==kIOReturnNoResources&&completes==1&&!returned);clear();
    failReturn=true;check(run(image(address))==kIOReturnVMError&&completes==1&&returned==1);clear();
    failMap=true;check(run(image(address))==0&&table->kernelAddress()==0);failMap=false;
    check(table->kernelAddress()==address);clear();
    sweet_surface_wired=SWEET_SURFACE_WIRED_MAX;
    check(run(image(address))==kIOReturnNoMemory&&!allocated&&sweet_surface_wired==SWEET_SURFACE_WIRED_MAX);
    sweet_surface_wired=0;clear();
    std::printf("PASS %u production caller-memory create, alias, extent, readonly, planes and cleanup assertions\n",assertions);
}
