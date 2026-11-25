#include "test_runtime_shim.h"
#include <stdarg.h>
#include <stdlib.h>
#include "nvt_kernel_bus.h"
#include "nvt_bootstrap.h"
#include "nvt_protocol.h"
#include <IOKit/SweetHIDTouchFrame.h>

struct test_pe_state PE_state;
unsigned long gPhysBase,real_phys_size;
vm_offset_t arm_vm_kernelcache_phys_end;
struct nvt_bus {unsigned token;};
static struct nvt_bus bus;
static uint8_t original[NBS_FIRMWARE_BYTES],firmware[147456];
static boot_args args;
static uint64_t asset[2];
enum stream_case { STREAM_ESD, STREAM_BAD, STREAM_WDT, STREAM_HID, STREAM_RECOVER };
static struct {
    int enabled,diagnostic,legacy,start_error,open_error,configure_error,pins_error,bootstrap_error;
    bool missing,wrong_version,noncontiguous,irq,in_interrupt,poisoned,held,configured,pins,reset_high;
    bool bootstrap_ready,bad_map,bad_verify,release_fails;
    int preemption;
    unsigned property_bytes,starts,deallocations,terminations,dt_reads,maps;
    unsigned opens,configures,activations,resets,bootstraps,xfers,aborts,closes,status_calls;
    unsigned long_delay,short_delay,hid_calls,release_calls,recorded,frame_count;
    unsigned fail_xfer,fail_hid_after;
    uint32_t sck,geometry_x,geometry_y;
    uint64_t us;
    enum stream_case stream;
    thread_continue_t worker;
    struct sweet_hid_touch_snapshot frames[32];
    char log[32768];size_t log_length;
} mock;

int nrt_test_printf(const char *format,...)
{
    char line[512];va_list list;va_start(list,format);int n=vsnprintf(line,sizeof(line),format,list);va_end(list);
    assert(n>=0 && (size_t)n<sizeof(line) && mock.log_length+(size_t)n<sizeof(mock.log));
    memcpy(mock.log+mock.log_length,line,(size_t)n+1);mock.log_length+=(size_t)n;return n;
}
bool PE_parse_boot_argn(const char *name,void *out,size_t bytes)
{
    assert(bytes==sizeof(int));
    if(!strcmp(name,"sweetnvt"))*(int *)out=mock.enabled;
    else if(!strcmp(name,"sweetnvtprobe"))*(int *)out=mock.diagnostic;
    else {assert(!strcmp(name,"sweettouchmode"));*(int *)out=mock.legacy;}
    return true;
}
kern_return_t kernel_thread_start(thread_continue_t start,void *argument,thread_t *out)
{assert(!argument);mock.starts++;mock.worker=start;*out=(thread_t)(uintptr_t)1;return mock.start_error;}
void thread_deallocate(thread_t t){assert(t==(thread_t)(uintptr_t)1);mock.deallocations++;}
void thread_terminate_self(void){mock.terminations++;}
void IOSleep(unsigned ms){if(ms==1000)mock.long_delay++;else mock.short_delay++;mock.us+=(uint64_t)ms*1000;}
uint64_t mach_absolute_time(void){return mock.us*1000;}
void absolutetime_to_nanoseconds(uint64_t t,uint64_t *out){*out=t;}
bool ml_get_interrupts_enabled(void){return mock.irq;}
bool ml_at_interrupt_context(void){return mock.in_interrupt;}
int get_preemption_level(void){return mock.preemption;}
int SecureDTLookupEntry(DTEntry unused,const char *path,DTEntry *out)
{assert(!unused && !strcmp(path,"/chosen/memory-map"));mock.dt_reads++;*out=(void *)(uintptr_t)1;return mock.missing?-1:0;}
int SecureDTGetProperty(DTEntry entry,const char *name,const void **out,unsigned *bytes)
{assert(entry==(void *)(uintptr_t)1 && !strcmp(name,"NovatekFirmware"));*out=asset;*bytes=mock.property_bytes;return 0;}
vm_offset_t ml_static_ptovirt(vm_offset_t pa)
{
    mock.maps++;assert(!mock.opens && pa>=asset[0] && pa-asset[0]<sizeof(firmware));
    return (uintptr_t)firmware+(pa-asset[0])+(mock.noncontiguous && mock.maps>1?1:0);
}
void sweet_log_mark_sync(const char *line){assert(strstr(line,"SWEET NVT:")==line);}
void sweet_log_flush_now(void){}
void sweet_log_append(const char *line,int n){assert(n>0);nrt_test_printf("%.*s",n,line);}

int nvt_bus_open(struct nvt_bus **out)
{
    assert(mock.long_delay==30 && mock.maps==2 && !mock.held && !mock.poisoned);
    assert(!memcmp(firmware,original,NBS_FIRMWARE_BYTES)); /* The actual hash already accepted it. */
    mock.opens++;if(mock.open_error){*out=NULL;return mock.open_error;}
    *out=&bus;mock.held=true;return 0;
}
int nvt_bus_configure(struct nvt_bus *b,uint32_t max_hz)
{assert(b==&bus && mock.held && !mock.pins && max_hz==1000000);mock.configures++;mock.configured=!mock.configure_error;return mock.configure_error;}
int nvt_bus_activate_native_pins(struct nvt_bus *b)
{assert(b==&bus && mock.held && mock.configured);mock.activations++;mock.pins=!mock.pins_error;mock.reset_high=false;return mock.pins_error;}
int nvt_bus_set_reset(struct nvt_bus *b,bool high)
{assert(b==&bus && mock.held && mock.pins && !mock.poisoned);mock.resets++;mock.reset_high=high;return 0;}
int nvt_bus_get_status(struct nvt_bus *b,struct nvt_bus_status *out)
{
    assert(b==&bus && mock.held);mock.status_calls++;
    memset(out,0,sizeof(*out));out->state=mock.configured?NVT_BUS_CONFIGURED:NVT_BUS_OPEN;out->sck_hz=mock.sck;
    return 0;
}
static void point(uint8_t *rx,unsigned record,unsigned id,unsigned x,unsigned y)
{
    uint8_t *p=rx+2+record*6;p[0]=(uint8_t)(id<<3)|1;p[1]=(uint8_t)(x>>4);p[2]=(uint8_t)(y>>4);
    p[3]=(uint8_t)(((x&15)<<4)|(y&15));p[4]=1;p[5]=1;
}
int nvt_bus_xfer(struct nvt_bus *b,const uint8_t *tx,uint8_t *rx,size_t length)
{
    assert(b==&bus && mock.held && mock.pins && mock.reset_high && !mock.poisoned);
    assert(++mock.xfers<1000);mock.us+=600;
    if(mock.xfers==mock.fail_xfer){mock.poisoned=true;return EIO;}
    if(!rx){assert(length==3 && tx[0]==0xff && tx[1]==4 && tx[2]==0x5a);return 0;}
    assert(length==67 && tx[0]==0);for(unsigned i=1;i<67;i++)assert(tx[i]==0);
    memset(rx,0,67);rx[0]=0x9a;rx[1]=0x67; /* Undefined response/dummy are not checked. */
    unsigned frame=++mock.frame_count;
    if(frame==1 || mock.stream==STREAM_HID){point(rx,0,1,mock.geometry_x,mock.geometry_y);return 0;}
    if(mock.stream==STREAM_BAD){point(rx,0,1,10,20);point(rx,1,1,11,21);return 0;}
    if(mock.stream==STREAM_WDT){for(unsigned i=0;i<6;i++)rx[2+i]=0xfd;return 0;}
    if(mock.stream==STREAM_RECOVER && frame==2){point(rx,0,11,10,20);return 0;}
    if(mock.stream==STREAM_RECOVER && frame==3){point(rx,0,10,0,0);return 0;}
    memset(rx+2,0x77,6);return 0;
}
void nvt_bus_abort(struct nvt_bus *b,int error,struct nvt_bus_status *out)
{
    assert(b==&bus && mock.held && error>0 && mock.aborts==0);mock.aborts++;mock.poisoned=true;
    if(out){memset(out,0,sizeof(*out));out->state=NVT_BUS_QUARANTINED;out->error=error;out->mask_confirmed=true;}
    mock.held=false;
}
int nvt_bus_close(struct nvt_bus *b,struct nvt_bus_status *out)
{(void)b;(void)out;mock.closes++;assert(!"fault coordinator must abort, not reuse/restore bus");return EIO;}
int nbs_bootstrap(struct nbs_session *s,const struct nbs_io *io,const uint8_t *image,size_t bytes)
{
    assert(mock.held && mock.configured && mock.pins && !mock.reset_high);
    assert(image==firmware && bytes==NBS_FIRMWARE_BYTES && !memcmp(image,original,bytes));
    mock.bootstraps++;assert(io->xfer && io->reset && io->delay_ms && io->now_us && io->progress);
    io->progress(io->cookie,NBS_VALIDATE,0,96936);io->progress(io->cookie,NBS_VALIDATE,1,96936);
    assert(io->now_us(io->cookie)>=30000000);io->delay_ms(io->cookie,1);
    if(mock.bootstrap_error){s->report.callback_error=EIO;return mock.bootstrap_error;}
    assert(io->reset(io->cookie,true)==0);
    s->report.valid=0xfff;s->report.ready=mock.bootstrap_ready;s->report.trim_verified=true;s->report.event_base=mock.bad_map?0:NVT_EVENT_BASE;
    s->report.hw_crc=2;s->report.bytes_written=96936;s->report.bytes_verified=mock.bad_verify?1:96936;
    s->report.fwinfo.max_x=(uint16_t)mock.geometry_x;s->report.fwinfo.max_y=(uint16_t)mock.geometry_y;
    s->report.fwinfo.version=16;s->report.fwinfo.firmware_type=1;s->report.pid=0x5937;
    return 0; /* Only the orchestration dependency is mocked; no hardware claim. */
}
int sweet_hid_touch_frame(const struct sweet_hid_touch_snapshot *snapshot)
{
    assert(mock.bootstraps==1 && mock.held);mock.hid_calls++;
    if(!snapshot->active_mask){mock.release_calls++;if(mock.release_fails)return 0x123;}
    else if(mock.fail_hid_after && mock.hid_calls>=mock.fail_hid_after)return 0x123;
    assert(mock.recorded<32);mock.frames[mock.recorded++]=*snapshot;return 0;
}
void sweet_hid_touch(int finger,int down,int x,int y)
{(void)finger;(void)down;(void)x;(void)y;assert(!"legacy per-finger dispatch is forbidden");}

#define NVT_RUNTIME_HOST_TEST 1
#include NRT_SOURCE_PATH

static void reset(void)
{
    memset(&mock,0,sizeof(mock));memcpy(firmware,original,sizeof(original));memset(firmware+sizeof(original),0,sizeof(firmware)-sizeof(original));
    nrt_started=0;mock.enabled=1;mock.irq=true;mock.bootstrap_ready=true;mock.sck=960000;
    mock.geometry_x=540;mock.geometry_y=1200;mock.property_bytes=16;
    gPhysBase=0x180000000ull;real_phys_size=0x20000000;asset[0]=gPhysBase+0x200000;asset[1]=NBS_FIRMWARE_BYTES;
    args=(boot_args){.Version=2,.physBase=gPhysBase,.memSize=real_phys_size,.topOfKernelData=asset[0]+sizeof(firmware)+0x8000};
    arm_vm_kernelcache_phys_end=asset[0];PE_state.bootArgs=&args;
}
static void worker(void)
{
    sweet_nvt_start();assert(mock.starts==1 && mock.deallocations==1 && !mock.dt_reads && !mock.opens);
    sweet_nvt_start();assert(mock.starts==1);mock.worker(NULL,0);assert(mock.terminations==1 && mock.long_delay==30);
}
static void enable_gates(void)
{
    for(int mode=-1;mode<3;mode++)if(mode!=1){reset();mock.enabled=mode;sweet_nvt_start();assert(!mock.starts && !mock.dt_reads && !mock.maps && !mock.opens && !mock.hid_calls);}
    for(unsigned i=0;i<2;i++){reset();if(i)mock.legacy=1;else mock.diagnostic=2;sweet_nvt_start();assert(!mock.starts && !mock.dt_reads && !mock.opens);}
    reset();mock.start_error=5;sweet_nvt_start();sweet_nvt_start();assert(mock.starts==1 && !mock.dt_reads && !mock.opens && !mock.deallocations);
}
static void reject_assets_before_bus(void)
{
    for(unsigned bad=0;bad<13;bad++){
        reset();
        if(bad==0)mock.missing=true;
        if(bad==1)mock.property_bytes=8;
        if(bad==2)asset[1]--;
        if(bad==3)asset[0]++;
        if(bad==4)asset[0]-=0x4000;
        if(bad==5)args.topOfKernelData=asset[0]+0x20000;
        if(bad==6)args.physBase++;
        if(bad==7)args.memSize=UINT64_MAX;
        if(bad==8)PE_state.bootArgs=NULL;
        if(bad==9)mock.noncontiguous=true;
        if(bad==10)firmware[0]^=1;
        if(bad==11)args.Version=1;
        if(bad==12)args.topOfKernelData++;
        worker();assert(!mock.opens && !mock.configures && !mock.bootstraps && !mock.xfers && !mock.hid_calls && !mock.aborts);
        if(bad!=9 && bad!=10)assert(!mock.maps);
    }
}
static void setup_failures(void)
{
    for(unsigned bad=0;bad<3;bad++){
        reset();if(bad==0)mock.irq=false;if(bad==1)mock.in_interrupt=true;if(bad==2)mock.preemption=1;
        worker();assert(!mock.dt_reads && !mock.maps && !mock.opens);
    }
    for(unsigned stage=0;stage<8;stage++){
        reset();
        if(stage==0)mock.open_error=EIO;
        if(stage==1)mock.configure_error=EIO;
        if(stage==2)mock.sck=19200000;
        if(stage==3)mock.pins_error=EIO;
        if(stage==4)mock.bootstrap_error=NBS_CRC;
        if(stage==5)mock.bootstrap_ready=false;
        if(stage==6)mock.bad_map=true;
        if(stage==7)mock.bad_verify=true;
        worker();assert(mock.opens==1 && !mock.xfers && !mock.hid_calls && mock.aborts==(stage?1u:0u));
        assert(!mock.held && !mock.closes);
        if(stage>=4)assert(strstr(mock.log,"bootstrap summary"));
        if(stage==4)assert(strstr(mock.log,"trim=unread") && strstr(mock.log,"golden_ILM=unread"));
    }
    reset();mock.geometry_x=1;worker();assert(mock.aborts==1 && !mock.xfers && !mock.hid_calls);
}
static void physical_streams(void)
{
    reset();worker();assert(mock.recorded==2 && mock.frames[0].active_mask==1 && !mock.frames[1].active_mask);
    assert(mock.frames[0].x[0]==1079 && mock.frames[0].y[0]==2399 && mock.frame_count==2 && mock.xfers==6);
    assert(mock.aborts==1 && mock.release_calls==1 && !mock.held);
    assert(strstr(mock.log,"bootstrap summary") && strstr(mock.log,"FWINFO=540x1200/ver16/type1"));
    assert(strstr(mock.log,"last PIO snapshot irq_seen=unread"));
    reset();mock.stream=STREAM_RECOVER;worker();
    assert(mock.frame_count==4 && mock.recorded==3 && mock.frames[1].active_mask==(1u<<9));
    assert(mock.frames[1].x[9]==0 && mock.frames[1].y[9]==0 && !mock.frames[2].active_mask);
    reset();mock.stream=STREAM_BAD;worker();assert(mock.frame_count==4 && mock.recorded==2 && mock.aborts==1);
    reset();mock.stream=STREAM_WDT;worker();assert(mock.frame_count==12 && mock.recorded==2 && mock.aborts==1);
    for(unsigned fail=4;fail<=6;fail++){reset();mock.fail_xfer=fail;worker();assert(mock.xfers==fail && mock.recorded==2 && mock.aborts==1);}
    reset();mock.stream=STREAM_HID;mock.fail_hid_after=2;worker();assert(mock.frame_count==9 && mock.recorded==2 && mock.release_calls==1);
    reset();mock.stream=STREAM_HID;mock.fail_hid_after=2;mock.release_fails=true;worker();
    assert(mock.release_calls==3 && mock.recorded==1 && mock.aborts==1 && strstr(mock.log,"release unconfirmed"));
}
int main(int argc,char **argv)
{
    assert(argc==2 || argc==3);FILE *f=fopen(argv[1],"rb");assert(f);assert(fread(original,1,sizeof(original),f)==sizeof(original));assert(fgetc(f)==EOF);fclose(f);
    /* The real XNU SHA wrapper and LTC implementation, not a canned digest. */
    SHA256_CTX ctx;uint8_t digest[32];SHA256_Init(&ctx);SHA256_Update(&ctx,"abc",3);SHA256_Final(digest,&ctx);
    static const uint8_t abc[32]={0xba,0x78,0x16,0xbf,0x8f,0x01,0xcf,0xea,0x41,0x41,0x40,0xde,0x5d,0xae,0x22,0x23,0xb0,0x03,0x61,0xa3,0x96,0x17,0x7a,0x9c,0xb4,0x10,0xff,0x61,0xf2,0x00,0x15,0xad};
    assert(!memcmp(abc,digest,32));
    if(argc==3){
        assert(!strcmp(argv[2],"reject-synthetic"));reset();worker();
        assert(mock.maps==2 && !mock.opens && !mock.xfers && !mock.hid_calls);
        puts("PASS: unmodified production pin rejects synthetic asset with real SHA before bus");return 0;
    }
    enable_gates();reject_assets_before_bus();setup_failures();physical_streams();
    puts("PASS: actual runtime gating/reserved asset+real SHA, setup ordering, real protocol frames, geometry, bounded faults and HID release");
    return 0;
}
