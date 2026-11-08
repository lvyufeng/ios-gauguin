/* Standalone iOS root probe for the real msm-numbered GPU IOUserClient.
 * It allocates/maps its own buffers, supplies dynamic PM4 and waits for real
 * fences. CPU stores only initialize inputs; results are read after completion.
 * Run once as root after HakiosGPU appears, normally via a temporary job. */
#include <IOKit/IOKitLib.h>
#include <IOSurface/IOSurfaceRef.h>
#include <CoreFoundation/CoreFoundation.h>
#include <mach/mach.h>
#include <sys/sysctl.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include "gauguin_gpu_runtime.h"

struct bo {uint32_t handle;uint64_t iova,size;mach_vm_address_t cpu;};
static io_connect_t connection;
static int console=-1;
static const char *trial="gpu-user-175";
static uint32_t queue;
static uint64_t now_ns(void)
{struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000+(uint64_t)t.tv_nsec;}
static void message(const char *event,uint64_t a,uint64_t b)
{
    char line[256];snprintf(line,sizeof(line),"SWEET GPU PROBE: trial=%s event=%s a=%llu b=%llu\n",trial,event,(unsigned long long)a,(unsigned long long)b);
    fputs(line,stdout);fflush(stdout);
    if(console>=0)(void)write(console,line,strlen(line));
}
static kern_return_t call(uint32_t selector,void *p,size_t n)
{size_t out=n;return IOConnectCallStructMethod(connection,selector,p,n,p,&out);}
static int failure(const char *event,uint64_t status)
{message(event,status,0);return 1;}
static int allocate(struct bo *b,uint64_t bytes,uint32_t flags)
{
    struct ggr_new n={bytes,flags,0};kern_return_t rc=call(0x42,&n,sizeof(n));
    if(rc)return failure("new-failed",rc);
    b->handle=n.handle;
    struct ggr_info info={b->handle,1,0,0,0};rc=call(0x43,&info,sizeof(info));
    if(rc)return failure("info-failed",rc);
    b->iova=info.value;mach_vm_size_t size=0;
    rc=IOConnectMapMemory64(connection,b->handle,mach_task_self(),&b->cpu,&size,kIOMapAnywhere);
    if(rc||size<bytes||b->iova<GGR_VA_START||b->iova>=GGR_VA_END||size>GGR_VA_END-b->iova)
        return failure("map-failed",rc?rc:size);
    b->size=size;message("bo",b->handle,b->iova);return 0;
}
static int close_bo(struct bo *b)
{
    if(b->cpu) {
        kern_return_t r=IOConnectUnmapMemory64(connection,b->handle,mach_task_self(),b->cpu);
        if(r)return failure("unmap-failed",r);
        b->cpu=0;
    }
    if(b->handle) {
        struct ggr_close c={b->handle,0};kern_return_t r=call(9,&c,sizeof(c));
        if(r)return failure("close-failed",r);
        b->handle=0;
    }
    return 0;
}
static int submit(struct bo *commands,const struct bo *target,uint32_t words,uint32_t *previous)
{
    struct ggr_submit_bo bos[]={{1,commands->handle,commands->iova},{3,target->handle,target->iova}};
    struct ggr_submit_cmd cmd={1,0,0,words*4,0,0,0};
    struct ggr_submit s={0};s.flags=0x10;s.nr_bos=2;s.nr_cmds=1;
    s.bos=(uint64_t)(uintptr_t)bos;s.cmds=(uint64_t)(uintptr_t)&cmd;s.fence_fd=-1;s.queueid=queue;
    __sync_synchronize();kern_return_t r=call(0x46,&s,sizeof(s));
    if(r||!s.fence||s.fence<=*previous)return failure("submit-failed",r?r:s.fence);
    struct ggr_wait wait={0};wait.fence=s.fence;wait.queueid=queue;
    struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);
    wait.timeout.seconds=t.tv_sec+2;wait.timeout.nanoseconds=t.tv_nsec;
    r=call(0x47,&wait,sizeof(wait));
    if(r)return failure("fence-failed",r);
    __sync_synchronize();message("fence",s.fence,words);*previous=s.fence;return 0;
}
static void mem_write(uint32_t *words,unsigned index,uint64_t address,uint32_t value)
{words[4*index]=0x703d8003u;words[4*index+1]=(uint32_t)address;words[4*index+2]=(uint32_t)(address>>32);words[4*index+3]=value;}
static void number(CFMutableDictionaryRef d,CFStringRef key,int32_t value)
{CFNumberRef n=CFNumberCreate(kCFAllocatorDefault,kCFNumberSInt32Type,&value);CFDictionarySetValue(d,key,n);CFRelease(n);}

int main(int argc,char **argv)
{
    if(argc==2)trial=argv[1];
    if(strlen(trial)>48||strspn(trial,"abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")!=strlen(trial))return 2;
    console=open("/dev/console",O_WRONLY|O_NOCTTY);
    message("start",getpid(),getuid());
    char version[2048];size_t version_bytes=sizeof(version);
    if(!sysctlbyname("kern.version",version,&version_bytes,NULL,0)) {
        version[sizeof(version)-1]=0;
        printf("SWEET GPU PROBE KERNEL: %s\n",version);fflush(stdout);
        if(console>=0)dprintf(console,"SWEET GPU PROBE KERNEL: %s\n",version);
    }
    uint64_t end=now_ns()+100000000000ull;io_service_t service=IO_OBJECT_NULL;
    while(!service&&now_ns()<end) {
        service=IOServiceGetMatchingService(kIOMainPortDefault,IOServiceMatching("HakiosGPU"));
        if(!service)usleep(100000);
    }
    if(!service)return failure("service-timeout",0);
    kern_return_t r=IOServiceOpen(service,mach_task_self(),0,&connection);IOObjectRelease(service);
    if(r)return failure("open-failed",r);
    struct ggr_param id={0x10,1,0,0,0};r=call(0x40,&id,sizeof(id));
    if(r||id.value!=619)return failure("wrong-gpu",r?r:id.value);
    struct ggr_param chip={0x10,3,0,0,0};r=call(0x40,&chip,sizeof(chip));
    if(r||chip.value!=0x06010900)return failure("wrong-chip",r?r:chip.value);
    struct ggr_queue q={0};r=call(0x4a,&q,sizeof(q));if(r||!q.id)return failure("queue-failed",r);
    queue=q.id;message("identity",id.value,chip.value);
    struct bo commands={0},target={0};
    if(allocate(&commands,16384,GGR_BO_READONLY|GGR_BO_WC)||allocate(&target,32768,GGR_BO_WC))return 1;
    uint32_t seed=(uint32_t)now_ns()^((uint32_t)getpid()*0x9e3779b9u);
    uint32_t a=seed^0x13579bdfu,b=seed^0x2468ace0u,c=seed^0x55aa55aau,d=seed^0xa55aa55au;
    uint32_t *cmd=(uint32_t *)(uintptr_t)commands.cpu;
    uint32_t *data=(uint32_t *)(uintptr_t)target.cpu;
    for(unsigned i=0;i<target.size/4;i++)if(data[i])return failure("new-bo-not-zero",i);
    message("seed",seed,target.size);
    mem_write(cmd,0,target.iova,a);mem_write(cmd,1,target.iova+target.size-4,b);
    uint32_t fence=0;if(submit(&commands,&target,8,&fence))return 1;
    for(unsigned i=0;i<target.size/4;i++) {
        uint32_t expected=i==0?a:i==target.size/4-1?b:0;
        if(data[i]!=expected)return failure("first-readback-mismatch",i);
    }
    /* Change the command contents and target offsets at runtime. The second
     * job crosses a CPU16KiB boundary and preserves the first job's pixels. */
    mem_write(cmd,0,target.iova+16380,c);mem_write(cmd,1,target.iova+16384,d);
    if(submit(&commands,&target,8,&fence))return 1;
    uint32_t hash=2166136261u;
    for(unsigned i=0;i<target.size/4;i++) {
        uint32_t expected=i==0?a:i==target.size/4-1?b:i==4095?c:i==4096?d:0;
        if(data[i]!=expected)return failure("second-readback-mismatch",i);
        hash=(hash^data[i])*16777619u;
    }
    message("normal-bo-readback",target.size/4,hash);
    CFMutableDictionaryRef props=CFDictionaryCreateMutable(kCFAllocatorDefault,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
    number(props,kIOSurfaceWidth,32);number(props,kIOSurfaceHeight,32);number(props,kIOSurfaceBytesPerRow,128);
    number(props,kIOSurfaceBytesPerElement,4);number(props,kIOSurfacePixelFormat,0x42475241);
    number(props,CFSTR("IOSurfaceOffset"),64);number(props,kIOSurfaceAllocSize,16384);
    IOSurfaceRef surface=IOSurfaceCreate(props);CFRelease(props);
    if(!surface)return failure("surface-create-failed",0);
    struct ggr_surface imported={0};imported.surface=IOSurfaceGetID(surface);
    r=call(0x7e,&imported,sizeof(imported));
    if(r||!imported.handle||imported.width!=32||imported.height!=32||imported.rowBytes!=128||imported.offset!=64||imported.size!=16384)
        return failure("surface-import-failed",r?r:imported.offset);
    struct bo shared={.handle=imported.handle,.size=imported.size};
    struct ggr_info info={shared.handle,1,0,0,0};r=call(0x43,&info,sizeof(info));
    if(r)return failure("surface-info-failed",r);shared.iova=info.value;
    r=IOSurfaceLock(surface,0,NULL);if(r)return failure("surface-lock-init-failed",r);
    void *pixels=IOSurfaceGetBaseAddress(surface);
    if(!pixels)return failure("surface-base-failed",0);
    memset(pixels,0,4096);r=IOSurfaceUnlock(surface,0,NULL);
    if(r)return failure("surface-unlock-init-failed",r);
    mem_write(cmd,0,shared.iova+imported.offset,a^0xff000000u);
    mem_write(cmd,1,shared.iova+imported.offset+4092,b^0xff000000u);
    if(submit(&commands,&shared,8,&fence))return 1;
    r=IOSurfaceLock(surface,kIOSurfaceLockReadOnly,NULL);if(r)return failure("surface-lock-result-failed",r);
    volatile uint32_t *read=(volatile uint32_t *)IOSurfaceGetBaseAddress(surface);hash=2166136261u;
    for(unsigned i=0;i<1024;i++) {
        uint32_t expected=i==0?(a^0xff000000u):i==1023?(b^0xff000000u):0;
        if(read[i]!=expected)return failure("surface-readback-mismatch",i);
        hash=(hash^read[i])*16777619u;
    }
    r=IOSurfaceUnlock(surface,kIOSurfaceLockReadOnly,NULL);if(r)return failure("surface-unlock-result-failed",r);
    message("surface-readback",1024,hash);
    if(close_bo(&shared)||close_bo(&target)||close_bo(&commands))return 1;
    CFRelease(surface);r=call(0x4b,&queue,sizeof(queue));if(r)return failure("queue-close-failed",r);
    r=IOServiceClose(connection);if(r)return failure("connection-close-failed",r);
    message("PASS-dynamic-BO-map-submit-fence-IOSurface",fence,seed);
    if(console>=0)close(console);return 0;
}
