/* Host fixture template. test_nvt_probe.py inserts actual stage0 source;
 * only the architecture load/barrier primitive and XNU services are mocked. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define GAUGUIN 1
#define KERN_SUCCESS 0
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);

static struct {
    int enabled, start_result;
    unsigned starts, deallocations, sleeps, sleep_ms, terminations, maps, reads;
    unsigned phase, flushed, cmd_reads, dfs_reads, cfg_reads, m_reads, n_reads;
    unsigned pll_reads, tlmm_reads;
    uint32_t mapped[24], read_address[128], dfs, cfg;
    uint32_t fail_map;
    bool change_cmd, change_dfs, change_cfg, change_m, change_n, change_pll;
    thread_continue_t worker;
    char log[32768];
    size_t log_length;
} mock;

static int test_printf(const char *format, ...)
{
    char line[512];va_list args;va_start(args,format);
    int n=vsnprintf(line,sizeof(line),format,args);va_end(args);
    assert(n>=0 && (size_t)n<sizeof(line));
    assert(mock.log_length+(size_t)n<sizeof(mock.log));
    memcpy(mock.log+mock.log_length,line,(size_t)n+1);mock.log_length+=(size_t)n;
    return n;
}
bool PE_parse_boot_argn(const char *name, void *value, size_t size)
{
    assert(strcmp(name,"sweetnvtprobe")==0 && size==sizeof(int));
    *(int *)value=mock.enabled;return true;
}
kern_return_t kernel_thread_start(thread_continue_t start,void *arg,thread_t *thread)
{
    assert(arg==NULL);mock.starts++;mock.worker=start;
    if(mock.start_result) return mock.start_result;
    *thread=(thread_t)(uintptr_t)1;return 0;
}
void thread_deallocate(thread_t thread) {assert(thread==(thread_t)(uintptr_t)1);mock.deallocations++;}
void thread_terminate_self(void) {mock.terminations++;}
void IOSleep(unsigned milliseconds) {assert(milliseconds==1000);mock.sleeps++;mock.sleep_ms+=milliseconds;}
void sweet_log_mark_sync(const char *text)
{
    assert(strstr(text,"SWEET NVT PROBE: stage0 ")==text);mock.phase++;
}
void sweet_log_flush_now(void) {mock.flushed=mock.phase;}

static bool allowed_pin(unsigned pin)
{return pin<=3 || pin==21 || pin==22;}
static void before_io(void)
{
    assert(mock.sleep_ms==30000 && mock.sleeps==30);
    assert(mock.phase>0 && mock.flushed==mock.phase);
}
vm_offset_t ml_io_map(vm_offset_t physical,vm_size_t bytes)
{
    before_io();assert(bytes==0x1000);assert(mock.maps<24);
    bool allowed=physical==0x152000 || physical==0x121000 || physical==0x100000 || physical==0x106000;
    if(physical>=0xf100000 && physical<0xf117000)
        allowed=physical%0x1000==0 && allowed_pin((unsigned)((physical-0xf100000)/0x1000));
    assert(allowed && "unapproved map (including SE/wrapper)");
    mock.mapped[mock.maps++]=(uint32_t)physical;
    return physical==mock.fail_map?0:physical;
}
static uint32_t fake_read(vm_offset_t base,uint32_t offset)
{
    before_io();assert(mock.reads<128);assert(offset<=0xffc && offset%4==0);
    bool mapped=false;for(unsigned i=0;i<mock.maps;++i) mapped|=mock.mapped[i]==base;
    assert(mapped && base!=mock.fail_map);
    uint32_t address=(uint32_t)base+offset;mock.read_address[mock.reads++]=address;
    if(base==0x152000) {assert(offset==0);return 0x000044c0;}
    if(base==0x121000) {
        if(offset==4 || offset==8 || offset==0xc || offset==0x14 || offset==0x144) return 0x80000002;
        if(offset==0x148) return ++mock.cmd_reads>1 && mock.change_cmd?1:0;
        if(offset==0x15c) return ++mock.dfs_reads>1 && mock.change_dfs?mock.dfs^2:mock.dfs;
        unsigned level=(mock.dfs>>1)&15;
        assert(!(mock.dfs&1) || level<8);
        uint32_t cfg=mock.dfs&1?0x164+4*level:0x14c;
        uint32_t m=mock.dfs&1?0x1a4+4*level:0x150;
        uint32_t n=mock.dfs&1?0x1e4+4*level:0x154;
        if(offset==cfg) return ++mock.cfg_reads>1 && mock.change_cfg?mock.cfg^1:mock.cfg;
        if(offset==m) {assert(((mock.cfg>>12)&3)==2);return ++mock.m_reads>1 && mock.change_m?5:4;}
        if(offset==n) {assert(((mock.cfg>>12)&3)==2);return ++mock.n_reads>1 && mock.change_n?0xffeb:0xffea;}
        assert(!"unexpected GCC read, including unproven BCR");
    }
    if(base==0x100000 || base==0x106000) {
        unsigned selector=(mock.cfg>>8)&7;
        assert((base==0x100000 && (selector==1 || selector==6)) || (base==0x106000 && selector==2));
        assert(offset==0 || offset==4 || offset==0xc || offset==0x2c || offset==0x38);
        mock.pll_reads++;
        return offset+(mock.change_pll && mock.pll_reads>5?1:0);
    }
    if(base>=0xf100000 && base<0xf117000) {
        assert(allowed_pin((unsigned)((base-0xf100000)/0x1000)));
        assert(offset==0 || offset==4);mock.tlmm_reads++;return offset?2:0x3c3;
    }
    assert(!"unapproved MMIO read");return 0;
}

#define printf test_printf
@SOURCE@
#undef printf

static void reset_fixture(void)
{
    memset(&mock,0,sizeof(mock));nvt_probe_started=0;
    mock.enabled=1;mock.dfs=5;mock.cfg=(6u<<8)|5;
}
static void run_worker(void)
{
    sweet_nvt_probe_init();assert(mock.starts==1 && mock.deallocations==1);
    assert(!mock.maps && !mock.reads && !mock.sleeps); /* never inline */
    sweet_nvt_probe_init();assert(mock.starts==1);
    assert(mock.worker);mock.worker(NULL,0);
    assert(mock.terminations==1 && mock.sleeps==30 && mock.sleep_ms==30000);
}
static void gates(void)
{
    for(int value=-1;value<=2;++value) if(value!=1) {
        reset_fixture();mock.enabled=value;sweet_nvt_probe_init();
        assert(!mock.starts && !mock.maps && !mock.reads && !mock.phase && !mock.sleeps);
    }
    reset_fixture();mock.start_result=5;sweet_nvt_probe_init();sweet_nvt_probe_init();
    assert(mock.starts==1 && !mock.deallocations && !mock.maps && !mock.reads && !mock.sleeps);
    assert(strstr(mock.log,"worker start failed=5; skipped"));
}
static void selected_registers(void)
{
    reset_fixture();run_worker();
    assert(mock.cmd_reads==2 && mock.dfs_reads==2 && mock.cfg_reads==2);
    assert(!mock.m_reads && !mock.n_reads && mock.pll_reads==10 && mock.tlmm_reads==12);
    assert(strstr(mock.log,"stage0 snapshot complete"));
    for(unsigned parent=0;parent<8;++parent) {
        reset_fixture();mock.cfg=parent<<8;run_worker();
        unsigned expected=parent==1 || parent==2 || parent==6?10:0;
        assert(mock.pll_reads==expected && mock.tlmm_reads==12);
    }
    reset_fixture();mock.dfs=0;mock.cfg=(2u<<8)|(2u<<12)|1;run_worker();
    assert(mock.m_reads==2 && mock.n_reads==2 && mock.pll_reads==10 && mock.tlmm_reads==12);
    for(unsigned level=0;level<8;++level) {
        reset_fixture();mock.dfs=(level<<1)|1;run_worker();
        assert(mock.cfg_reads==2 && !mock.m_reads && mock.tlmm_reads==12);
    }
}
static void refuse_unqualified(void)
{
    for(unsigned level=8;level<16;++level) {
        reset_fixture();mock.dfs=(level<<1)|1;run_worker();
        assert(!mock.cfg_reads && !mock.m_reads && !mock.n_reads && !mock.pll_reads && !mock.tlmm_reads);
        assert(strstr(mock.log,"invalid DFS level="));
    }
    for(unsigned mode=1;mode<4;mode+=2) {
        reset_fixture();mock.cfg|=mode<<12;run_worker();
        assert(mock.cfg_reads==1 && !mock.m_reads && !mock.n_reads && !mock.pll_reads && !mock.tlmm_reads);
        assert(strstr(mock.log,"unsupported mode="));
    }
    for(unsigned changed=0;changed<5;++changed) {
        reset_fixture();mock.cfg|=2u<<12;
        if(changed==0) mock.change_cmd=true;
        if(changed==1) mock.change_dfs=true;
        if(changed==2) mock.change_cfg=true;
        if(changed==3) mock.change_m=true;
        if(changed==4) mock.change_n=true;
        run_worker();assert(!mock.pll_reads && !mock.tlmm_reads);
        assert(!strstr(mock.log,"stage0 snapshot complete"));
    }
    reset_fixture();mock.change_pll=true;run_worker();
    assert(mock.pll_reads==10 && !mock.tlmm_reads);
}
static void map_failures(void)
{
    const uint32_t fail[]={0x152000,0x121000,0x100000,0xf102000};
    for(unsigned i=0;i<sizeof(fail)/sizeof(fail[0]);++i) {
        reset_fixture();mock.fail_map=fail[i];run_worker();
        assert(strstr(mock.log,"mapping failed; stop"));
        assert(!strstr(mock.log,"stage0 snapshot complete"));
        if(i<2) assert(!mock.reads);
        if(i==2) assert(!mock.pll_reads && !mock.tlmm_reads);
        if(i==3) assert(mock.tlmm_reads==4);
    }
}
int main(void)
{
    gates();selected_registers();refuse_unqualified();map_failures();
    puts("PASS: actual stage0 default-off/thread gates/delay/named MMIO/DFS+PLL stability/failures");
    return 0;
}
