/* Actual candidate is inserted below. No shadow implementation of its flow. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdarg.h>
#include <string.h>

#define GAUGUIN 1
#define KERN_SUCCESS 0
#define VOTES ((1u << 6) | (1u << 7) | (1u << 10))
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);
static struct {
    int enabled, start_result;
    unsigned starts, deallocations, sleeps, sleep_ms, terminations, maps, reads, writes;
    unsigned phase, flushed, cmd_reads, dfs_reads, cfg_reads, m_reads, n_reads;
    unsigned pll_reads, tlmm_reads, wrapper_reads, se_reads, gate_reads[3], delays;
    uint32_t mapped[32], read_address[8192], write_value[8], dfs, cfg;
    uint32_t vote, initial_vote, reject_vote, peer_set, peer_clear;
    uint32_t fail_map, map_occurrences, fail_occurrence, gate_value[3];
    uint32_t wrapper_version, fw, sfw, status;
    bool change_cmd, change_dfs, change_cfg, change_m, change_n, change_pll;
    bool stage1, restoring, reject_restore;
    thread_continue_t worker;
    void *argument;
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
bool PE_parse_boot_argn(const char *name,void *value,size_t size)
{assert(strcmp(name,"sweetnvtprobe")==0 && size==sizeof(int));*(int *)value=mock.enabled;return true;}
kern_return_t kernel_thread_start(thread_continue_t start,void *arg,thread_t *thread)
{
    assert((uintptr_t)arg==(unsigned)mock.enabled);mock.starts++;mock.worker=start;mock.argument=arg;
    if(mock.start_result)return mock.start_result;
    *thread=(thread_t)(uintptr_t)1;return 0;
}
void thread_deallocate(thread_t thread){assert(thread==(thread_t)(uintptr_t)1);mock.deallocations++;}
void thread_terminate_self(void){mock.terminations++;}
void IOSleep(unsigned ms){assert(ms==1000);mock.sleeps++;mock.sleep_ms+=ms;}
void delay(unsigned us){assert(us==1 && mock.stage1);mock.delays++;assert(mock.delays<=6000);}
void sweet_log_mark_sync(const char *text)
{
    assert(strstr(text,"SWEET NVT PROBE: stage")==text);mock.phase++;
    if(strstr(text,"stage1 "))mock.stage1=true;
    if(strstr(text,"restore only added clock votes"))mock.restoring=true;
}
void sweet_log_flush_now(void){mock.flushed=mock.phase;}
static bool allowed_pin(unsigned pin){return pin<=3 || pin==21 || pin==22;}
static void before_io(void)
{
    assert(mock.sleep_ms==30000 && mock.sleeps==30);
    assert(mock.phase>0 && mock.flushed==mock.phase);
}
vm_offset_t ml_io_map(vm_offset_t physical,vm_size_t bytes)
{
    before_io();assert(mock.maps<32);
    bool allowed=bytes==0x1000 && (physical==0x152000 || physical==0x121000 || physical==0x100000 || physical==0x106000);
    if(physical>=0xf100000 && physical<0xf117000)
        allowed=bytes==0x1000 && physical%0x1000==0 && allowed_pin((unsigned)((physical-0xf100000)/0x1000));
    if(mock.stage1 && physical==0x8c0000)allowed=bytes==0x2000;
    if(mock.stage1 && physical==0x880000)allowed=bytes==0x4000 && mock.wrapper_reads==1;
    assert(allowed && "unapproved map");
    mock.mapped[mock.maps++]=(uint32_t)physical;
    if(physical==mock.fail_map && ++mock.map_occurrences==mock.fail_occurrence)return 0;
    return physical;
}
static uint32_t fake_read(vm_offset_t base,uint32_t offset)
{
    before_io();assert(mock.reads<8192);assert(offset<=0xffc && offset%4==0);
    bool mapped=false;for(unsigned i=0;i<mock.maps;++i)mapped|=mock.mapped[i]==base;
    assert(mapped);mock.read_address[mock.reads++]=(uint32_t)base+offset;
    if(base==0x152000){assert(offset==0);return mock.vote;}
    if(base==0x121000){
        const uint32_t gates[]={4,8,0x144};
        for(unsigned i=0;i<3;++i)if(offset==gates[i]){
            if(mock.stage1){mock.gate_reads[i]++;return mock.gate_value[i];}
            return 0x80000002;
        }
        if(offset==0xc || offset==0x14)return 0x4220;
        if(offset==0x148)return ++mock.cmd_reads>1 && mock.change_cmd?1:0;
        if(offset==0x15c)return ++mock.dfs_reads>1 && mock.change_dfs?mock.dfs^2:mock.dfs;
        unsigned level=(mock.dfs>>1)&15;assert(!(mock.dfs&1) || level<8);
        uint32_t cfg=mock.dfs&1?0x164+4*level:0x14c;
        uint32_t m=mock.dfs&1?0x1a4+4*level:0x150;
        uint32_t n=mock.dfs&1?0x1e4+4*level:0x154;
        if(offset==cfg)return ++mock.cfg_reads>1 && mock.change_cfg?mock.cfg^1:mock.cfg;
        if(offset==m){assert(((mock.cfg>>12)&3)==2);return ++mock.m_reads>1 && mock.change_m?5:4;}
        if(offset==n){assert(((mock.cfg>>12)&3)==2);return ++mock.n_reads>1 && mock.change_n?0xffeb:0xffea;}
        assert(!"unexpected GCC read");
    }
    if(base==0x100000 || base==0x106000){
        unsigned selector=(mock.cfg>>8)&7;
        assert((base==0x100000 && (selector==1 || selector==6)) || (base==0x106000 && selector==2));
        assert(offset==0 || offset==4 || offset==0xc || offset==0x2c || offset==0x38);
        mock.pll_reads++;return offset+(mock.change_pll && mock.pll_reads>5?1:0);
    }
    if(base>=0xf100000 && base<0xf117000){
        assert(!mock.stage1 && allowed_pin((unsigned)((base-0xf100000)/0x1000)));
        assert(offset==0 || offset==4);mock.tlmm_reads++;return offset?0:1;
    }
    if(base==0x8c0000){
        assert(mock.stage1 && offset==4 && (mock.vote&VOTES)==VOTES);
        mock.wrapper_reads++;mock.vote=(mock.vote|mock.peer_set)&~mock.peer_clear;
        return mock.wrapper_version;
    }
    if(base==0x880000){
        static const uint32_t offsets[]={0x68,0x6c,0x40,0x64,0xe24,0xe28,0x800,0x804,
            0x48,0x7c,0x258,0x224,0x230,0x250,0x24c,0x268,0x260,0x264,0x284,0x288,0xe1c,0xe18,0x614};
        assert(mock.stage1 && mock.wrapper_reads==1 && mock.se_reads<sizeof(offsets)/sizeof(offsets[0]));
        assert(offset==offsets[mock.se_reads++]);
        if(offset==0x68)return mock.fw;
        if(offset==0x6c)return mock.sfw;
        if(offset==0x40)return mock.status;
        assert(((mock.fw>>8)&255)==1 && !(mock.status&0x1001));
        return offset;
    }
    assert(!"unapproved MMIO read");return 0;
}
static void fake_write(vm_offset_t base,uint32_t value)
{
    before_io();assert(mock.stage1 && mock.enabled==2 && base==0x152000);
    assert(mock.writes<8 && ((mock.vote^value)&~VOTES)==0);
    if(!mock.restoring){
        uint32_t delta=mock.vote^value;assert(delta && !(delta&(delta-1)) && (value&delta));
    }else assert((value&VOTES)==(mock.initial_vote&VOTES));
    mock.write_value[mock.writes++]=value;
    if(mock.restoring && mock.reject_restore)return;
    mock.vote=mock.restoring?value:value&~mock.reject_vote;
}
#define printf test_printf
@SOURCE@
#undef printf
static void reset_fixture(void)
{
    memset(&mock,0,sizeof(mock));nvt_probe_started=0;
    mock.enabled=1;mock.dfs=5;mock.cfg=(6u<<8)|5;
    mock.vote=mock.initial_vote=0x9c000003;mock.fail_occurrence=1;
    mock.gate_value[0]=0;mock.gate_value[1]=0x8000000a;mock.gate_value[2]=0x4220;
    mock.wrapper_version=0x200a0000;mock.fw=0x108;mock.sfw=0x108;
}
static void run_worker(void)
{
    sweet_nvt_probe_init();assert(mock.starts==1 && mock.deallocations==1);
    assert(!mock.maps && !mock.reads && !mock.writes && !mock.sleeps);
    sweet_nvt_probe_init();assert(mock.starts==1);
    assert(mock.worker);mock.worker(mock.argument,0);
    assert(mock.terminations==1 && mock.sleeps==30 && mock.sleep_ms==30000);
    if(mock.enabled==1)assert(!mock.writes && !mock.stage1 && !mock.wrapper_reads && !mock.se_reads);
}
static void gates(void)
{
    for(int value=-1;value<=3;++value)if(value!=1 && value!=2){
        reset_fixture();mock.enabled=value;sweet_nvt_probe_init();
        assert(!mock.starts && !mock.maps && !mock.reads && !mock.writes && !mock.phase && !mock.sleeps);
    }
    for(int mode=1;mode<=2;++mode){
        reset_fixture();mock.enabled=mode;mock.start_result=5;sweet_nvt_probe_init();sweet_nvt_probe_init();
        assert(mock.starts==1 && !mock.deallocations && !mock.maps && !mock.reads && !mock.writes && !mock.sleeps);
        assert(strstr(mock.log,"worker start failed=5; skipped"));
    }
}
static void stage0(void)
{
    for(int mode=1;mode<=2;++mode){
        for(unsigned parent=0;parent<8;++parent){
            reset_fixture();mock.enabled=mode;mock.cfg=parent<<8;run_worker();
            unsigned expected=parent==1 || parent==2 || parent==6?10:0;
            assert(mock.pll_reads==expected && mock.tlmm_reads==12);
        }
        for(unsigned level=0;level<8;++level){
            reset_fixture();mock.enabled=mode;mock.dfs=(level<<1)|1;mock.cfg|=2u<<12;run_worker();
            assert(mock.cfg_reads==2 && mock.m_reads==2 && mock.n_reads==2 && mock.tlmm_reads==12);
        }
        for(unsigned level=8;level<16;++level){
            reset_fixture();mock.enabled=mode;mock.dfs=(level<<1)|1;run_worker();
            assert(!mock.cfg_reads && !mock.m_reads && !mock.n_reads && !mock.pll_reads && !mock.tlmm_reads && !mock.stage1 && !mock.writes);
        }
        for(unsigned bad=1;bad<4;bad+=2){
            reset_fixture();mock.enabled=mode;mock.cfg|=bad<<12;run_worker();
            assert(mock.cfg_reads==1 && !mock.m_reads && !mock.n_reads && !mock.pll_reads && !mock.tlmm_reads && !mock.stage1);
        }
        for(unsigned changed=0;changed<6;++changed){
            reset_fixture();mock.enabled=mode;mock.cfg|=2u<<12;
            if(changed==0)mock.change_cmd=true;
            if(changed==1)mock.change_dfs=true;
            if(changed==2)mock.change_cfg=true;
            if(changed==3)mock.change_m=true;
            if(changed==4)mock.change_n=true;
            if(changed==5)mock.change_pll=true;
            run_worker();assert(!mock.tlmm_reads && !mock.stage1 && !mock.writes);
        }
        reset_fixture();mock.enabled=mode;mock.dfs=0;mock.cfg|=2u<<12;run_worker();
        assert(mock.m_reads==2 && mock.n_reads==2 && mock.tlmm_reads==12);
    }
}
static void stage1_success(void)
{
    reset_fixture();mock.enabled=2;run_worker();
    assert(mock.writes==4 && mock.vote==mock.initial_vote && mock.wrapper_reads==1 && mock.se_reads==23);
    assert(mock.gate_reads[0]==1 && mock.gate_reads[1]==1 && mock.gate_reads[2]==1 && !mock.delays);
    assert(strstr(mock.log,"stage1 controller snapshot complete"));
    for(unsigned subset=0;subset<8;++subset){
        reset_fixture();mock.enabled=2;unsigned present=0;
        if(subset&1){mock.vote|=1u<<6;present++;}
        if(subset&2){mock.vote|=1u<<7;present++;}
        if(subset&4){mock.vote|=1u<<10;present++;}
        mock.initial_vote=mock.vote;mock.peer_set=1u<<11;mock.peer_clear=1u<<26;run_worker();
        assert(mock.writes==(present==3?0:4-present) && mock.vote==((mock.initial_vote|mock.peer_set)&~mock.peer_clear));
    }
    reset_fixture();mock.enabled=2;mock.reject_restore=true;run_worker();
    assert((mock.vote&VOTES)==VOTES && strstr(mock.log,"restored=0"));
}
static void stage1_failures(void)
{
    for(unsigned i=0;i<3;++i){
        reset_fixture();mock.enabled=2;mock.gate_value[i]=0x80000000;run_worker();
        assert(mock.delays==2000 && mock.gate_reads[i]==2000 && !mock.wrapper_reads && !mock.se_reads);
        assert(mock.writes==i+2 && mock.vote==mock.initial_vote && strstr(mock.log,"timed out"));
        if(i<2)assert(mock.gate_reads[i+1]==0);
        reset_fixture();mock.enabled=2;mock.reject_vote=1u<<(i==2?10:6+i);run_worker();
        assert(mock.gate_reads[i]==0 && !mock.wrapper_reads && !mock.se_reads && !mock.delays);
        assert(mock.writes==i+2 && mock.vote==mock.initial_vote && strstr(mock.log,"vote rejected"));
    }
    /* S0 bit1 is not an HWCG exemption. */
    reset_fixture();mock.enabled=2;mock.gate_value[2]=0x80000002;run_worker();
    assert(mock.delays==2000 && !mock.wrapper_reads && mock.vote==mock.initial_vote);
    const uint32_t invalid[]={0,UINT32_MAX,0x000a0000};
    for(unsigned i=0;i<sizeof(invalid)/sizeof(invalid[0]);++i){
        reset_fixture();mock.enabled=2;mock.wrapper_version=invalid[i];run_worker();
        assert(mock.wrapper_reads==1 && !mock.se_reads && mock.vote==mock.initial_vote);
    }
    for(unsigned bad=0;bad<4;++bad){
        reset_fixture();mock.enabled=2;
        if(bad==0)mock.fw=0x208;
        if(bad==1)mock.status=1;
        if(bad==2)mock.status=0x1000;
        if(bad==3)mock.status=UINT32_MAX;
        run_worker();assert(mock.se_reads==3 && mock.vote==mock.initial_vote);
        assert(strstr(mock.log,"not idle SPI"));
    }
}
static void map_failures(void)
{
    const uint32_t fail[]={0x152000,0x121000,0x100000,0xf102000,0x8c0000,0x880000};
    for(unsigned i=0;i<sizeof(fail)/sizeof(fail[0]);++i){
        reset_fixture();mock.enabled=2;mock.fail_map=fail[i];run_worker();
        assert(!mock.se_reads && mock.vote==mock.initial_vote);
        if(i<4)assert(!mock.stage1 && !mock.writes);
        else assert(mock.writes==4 && mock.restoring);
    }
    for(unsigned i=0;i<2;++i){
        reset_fixture();mock.enabled=2;mock.fail_map=fail[i];mock.fail_occurrence=2;run_worker();
        assert(mock.stage1 && !mock.writes && !mock.wrapper_reads && !mock.se_reads && mock.vote==mock.initial_vote);
    }
}
int main(void)
{
    gates();stage0();stage1_success();stage1_failures();map_failures();
    puts("PASS: actual mode1 zero writes; mode2 named access, vote ownership, timeout/rejection/failure rollback and peer preservation");
    return 0;
}
