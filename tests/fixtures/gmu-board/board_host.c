#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <sys/mman.h>
#include "gauguin_gmu_board.h"
#include "gauguin_gmu_clock.h"
#include "gauguin_wdt_lease.h"
#include "gauguin_gmu_asset.h"
#include "gauguin_gpu_sqe_asset.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define VM_PROT_READ 1
#define VM_PROT_WRITE 2
#define NSEC_PER_SEC UINT64_C(1000000000)
typedef uintptr_t vm_offset_t;typedef size_t vm_size_t;typedef unsigned ppnum_t,vm_prot_t;typedef int boolean_t;
static _Alignas(16384) uint8_t ram[1048576],reset_page[16384],smmu[65536];
static _Alignas(16384) uint8_t fw_page[5][49152],fw_asset[32768];
static const uint64_t fw_bases[5]={0x03d8c000,0x0b294000,0x0b490000,0x03d6c000,0x03d0c000};
static const unsigned fw_sizes[5]={16384,16384,16384,49152,16384};
static struct {unsigned maps,nc_maps,translations,fail_translation,map_fail,misalign,pmap_calls,pmap_fail,attr_fail,overflow;
    unsigned owner_calls,owner_fail,budgets,budget_fail,expire,allocs,frees,alloc_fail,smmu_calls,smmu_fail,barriers,corrupt;
    unsigned clock_bad,irq_bad,context,quarantine,reads,writes,writes64;bool live;uint64_t now;
    unsigned firmware,asset_calls,asset_fail,engine_calls,engine_fail,gx_on,allow_gx,core_irq,
        fw_read_corrupt,fw_fail_phase,fw_stop_at,fw_steps,fw_stores,fw_forbidden,diag_lines,impl_lines,atos_lines,ctx_fault,fw_diag_lines,fw_impl_lines,fw_pdc_lines,fw_ao_lines,fw_cm3_lines,fw_bootcfg_lines,fw_reply_lines,fw_word_lines,
        perf_mode,perf_engine_calls,perf_complete_lines,perf_partial_lines,
        bw_mode,bw_engine_calls,bw_complete_lines,bw_partial_lines,test_complete_lines,test_partial_lines,dcvs_mode,dcvs_engine_calls,dcvs_request_lines,dcvs_complete_lines,dcvs_partial_lines,dcvs_missing,
        gpu_mode,gpu_context_calls,gpu_context_fail,gpu_smc_calls,gpu_smc_mode,gpu_drift,gpu_complete_lines,gpu_partial_lines,gpu_ap_complete_lines,gpu_input_lines;} h;
static _Alignas(16384) uint8_t core_page[16384];
static unsigned start_mode,start_sticky,start_missing,start_busy,start_allones,start_expire,start_reads,start_complete,start_partial;
static _Alignas(16384) uint8_t sqe_asset[32304];
static unsigned sqe_mode,sqe_calls,sqe_fail,sqe_corrupt,sqe_complete,sqe_partial,sqe_entry_budget,sqe_exit_budget,sqe_drift;
static _Alignas(16384) uint8_t core_extra[6][16384];
static const uint32_t core_offsets[6]={0x20000,0x24000,0x28000,0x2c000,0x3c000,0x68000};
static unsigned core_mode,core_active,core_reads,core_stores,core_memstores,core_complete,core_partial,core_rgl_lines;
static unsigned core_fail_phase,core_fail_kind,core_fired,core_attr_bad,core_overflow,core_stop_after,core_expire;
static unsigned core_phys_fail,core_dev_bad,core_dev_valid,core_corrupt_word;
static unsigned core_ram_reads,core_ram_stop,core_mem_stop,core_batch_expire,core_guard_lines,core_memory_lines;
static unsigned cp_mode,cp_active,cp_complete,cp_partial,cp_words,cp_guard_lines;
static unsigned cp_stores,cp_memstores,cp_memreads,cp_drop,cp_fences,cp_submits,cp_accepted,cp_keep;
static unsigned cp_shadow_delay,cp_busy_delay,cp_shadow_reads,cp_busy_reads,cp_bad_rptr,cp_bad_busy;
static unsigned cp_fail_phase,cp_fail_kind,cp_fired,cp_nc_page,cp_nc_bad,cp_dev_bad,cp_physical_bad;
static unsigned cp_stop_store,cp_expire_store,cp_stop_mem,cp_expire_mem,cp_corrupt_read,cp_drop_write,cp_counter_reads,cp_wrap;
static uint64_t cp_time_step;
static void host_cp_budget(void);
static void host_cp_read(vm_offset_t,uint32_t *);
static bool host_cp_store(vm_offset_t,uint32_t);
static void host_core_budget(void);
static struct {unsigned enabled,owner_state,owner_checks,owner_fail_at,owner_actions,owner_action_fail,copies,copy_fail,bad_copy,copy_guards,copy_expire;
    unsigned smc_calls[3],cont[3],busy[3],interrupted,auth_done,bad_smc_phase,bad_service,complete,partial,fault_phase,fault_kind,fired,bad_flag,bad_off,missing_init;
    int flag;struct gpa_registers last;} z;
static struct {unsigned active,owner_checks,owner_bad,budgets,budget_fail,kind,fired,phase,reads,drop,fences,accepted,busy_reads,busy_delay,counter_reads,wrap,memreads,shadow_reads,shadow_delay,bad_shadow,corrupt_read,stores,memstores,drop_write,kept,submits,stop_store,expire_store,complete,partial;} u;
static unsigned fixture_gpu_mode;
static struct {unsigned active,owner_bad,budgets,budget_fail,kind,phase,fired,reads,stores,memstores,memreads,
    drop,fences,accepted,submits,kept,device_done,device_writes,drop_data,corrupt_data,
    shadow_reads,shadow_delay,bad_shadow,busy_reads,busy_delay,counter_reads,wrap,
    drop_write,stop_store,expire_store,complete,partial,corrupt_phase,corrupt_mem,corrupt_off,
    nc_kind,nc_page,phys_bad;uint64_t time_step;} w;
static struct {unsigned active,owner_bad,budgets,budget_fail,kind,phase,fired,reads,stores,memstores,memreads,
    drop,fences,accepted,submits,kept,device_done,device_writes,drop_data,corrupt_data,
    shadow_reads,shadow_delay,bad_shadow,busy_reads,busy_delay,counter_reads,wrap,
    drop_write,stop_store,expire_store,complete,partial,corrupt_phase,corrupt_mem,corrupt_off,
    nc_kind,nc_page,phys_bad;uint64_t time_step;} ibf;
static bool host_ib_active(void);
static void host_ib_budget(void);
static void host_ib_read(vm_offset_t,uint32_t *);
static bool host_ib_store(vm_offset_t,uint32_t);
static bool host_write_active(void);
static void host_write_budget(void);
static void host_write_read(vm_offset_t,uint32_t *);
static bool host_write_store(vm_offset_t,uint32_t);
static bool host_unsecure_active(void);
static void host_unsecure_budget(void);
static void host_unsecure_read(vm_offset_t,uint32_t *);
static bool host_unsecure_store(vm_offset_t,uint32_t);
static void host_zap_budget(void);
static void host_zap_smc(struct gpa_registers *);
static unsigned cases;
#define CHECK(x) do {if(!(x)){fprintf(stderr,"GMU board failure case%u line%d\n",cases,__LINE__);abort();}}while(0)
static const uint64_t owner=UINT64_C(0xaa200000);
static int host_printf(const char *s,...)
{
    char text[256];va_list ap;va_start(ap,s);int n=vsnprintf(text,sizeof(text),s,ap);va_end(ap);
    CHECK(n>0&&(unsigned)n<sizeof(text));
    if(strstr(text,"SWEET GPU IB: complete")){CHECK(ibf.active&&h.live&&!h.quarantine&&sweet_gpu_ib_state()==GMB_READY&&ibf.complete++==0);}
    if(strstr(text,"SWEET GPU IB: partial")){CHECK(ibf.active&&!h.live&&h.quarantine==1&&sweet_gpu_ib_state()==GMB_QUARANTINED&&ibf.partial++==0);}
    if(strstr(text,"SWEET GPU WRITE: complete")){CHECK(w.active&&h.live&&!h.quarantine&&sweet_gpu_write_state()==GMB_READY&&w.complete++==0);}
    if(strstr(text,"SWEET GPU WRITE: partial")){CHECK(w.active&&!h.live&&h.quarantine==1&&sweet_gpu_write_state()==GMB_QUARANTINED&&w.partial++==0);}
    if(strstr(text,"SWEET GPU UNSECURE: complete")){CHECK(u.active&&h.live&&!h.quarantine&&sweet_gpu_unsecure_state()==GMB_READY&&u.complete++==0);}
    if(strstr(text,"SWEET GPU UNSECURE: partial")){CHECK(u.active&&!h.live&&h.quarantine==1&&sweet_gpu_unsecure_state()==GMB_QUARANTINED&&u.partial++==0);}
    if(strstr(text,"SWEET GPU ZAP: complete")){CHECK(z.enabled&&h.live&&!h.quarantine&&sweet_gpu_zap_state()==GMB_READY&&z.complete++==0&&z.owner_state==PSZ_AUTH_DONE);}
    if(strstr(text,"SWEET GPU ZAP: partial")){CHECK(z.enabled&&!h.live&&h.quarantine==1&&sweet_gpu_zap_state()==GMB_QUARANTINED&&z.partial++==0&&z.owner_state==PSZ_FAILED);}
    if(strstr(text,"SWEET GPU CP: complete")){CHECK(cp_active&&core_complete&&h.live&&!h.quarantine&&sweet_gpu_cp_state()==GMB_READY&&cp_complete++==0);}
    if(strstr(text,"SWEET GPU CP: partial")){CHECK(cp_active&&!h.live&&h.quarantine==1&&sweet_gpu_cp_state()==GMB_QUARANTINED&&cp_partial++==0);}
    if(strstr(text,"SWEET GPU CP WORD:")){CHECK(cp_complete==1&&h.live&&!h.quarantine);++cp_words;}
    if(strstr(text,"SWEET GPU CP GUARD:")){CHECK(cp_active&&(cp_complete||cp_partial)&&(!cp_partial||(!h.live&&h.quarantine==1)));++cp_guard_lines;}
    if(strstr(text,"SWEET GPU CORE: complete")){CHECK(core_mode&&h.live&&!h.quarantine&&sweet_gpu_core_state()==GMB_READY&&core_complete++==0);}
    if(strstr(text,"SWEET GPU CORE: partial")){CHECK(core_mode&&!h.live&&h.quarantine==1&&sweet_gpu_core_state()==GMB_QUARANTINED&&core_partial++==0);}
    if(strstr(text,"SWEET GPU CORE RGL:")){CHECK(core_complete==1&&h.live&&!h.quarantine);++core_rgl_lines;}
    if(strstr(text,"SWEET GPU CORE GUARD:")||strstr(text,"SWEET GPU CORE MEMORY:")){
        CHECK(core_mode&&(core_complete||core_partial));
        CHECK(core_complete?(h.live&&!h.quarantine):(!h.live&&h.quarantine==1));
        if(strstr(text,"SWEET GPU CORE GUARD:"))++core_guard_lines;else ++core_memory_lines;
    }
    if(strstr(text,"SWEET GPU SQE: complete")){CHECK(sqe_mode&&h.live&&!h.quarantine&&strstr(text,"copied=8192 checked=8192 pad=468 loaded=1")&&sqe_complete++==0);}
    if(strstr(text,"SWEET GPU SQE: partial")){CHECK(sqe_mode&&!h.live&&h.quarantine==1&&sqe_partial++==0);}
    if(strstr(text,"SWEET GPU START: complete")){CHECK(start_mode&&h.live&&!h.quarantine&&sweet_gpu_start_state()==GMB_READY&&start_complete++==0);}
    if(strstr(text,"SWEET GPU START: partial")){CHECK(start_mode&&!h.live&&h.quarantine==1&&start_partial++==0);}
    if(strstr(text,"SWEET GPU SMMU: complete")){CHECK(h.gpu_mode&&h.live&&!h.quarantine&&h.gpu_complete_lines++==0);}
    if(strstr(text,"SWEET GPU SMMU: partial")){CHECK(h.gpu_mode&&!h.live&&h.quarantine==1);++h.gpu_partial_lines;}
    if(strstr(text,"SWEET GPU APERTURE: complete")){CHECK(h.gpu_mode&&h.gpu_complete_lines==1&&h.live&&!h.quarantine);++h.gpu_ap_complete_lines;}
    if(strstr(text,"SWEET GPU INPUT:")){CHECK(h.gpu_mode&&h.gpu_context_fail==3&&!h.live&&h.quarantine==1);++h.gpu_input_lines;}
    if(strstr(text,"SWEET GMU PERF: complete")){
        CHECK(h.perf_mode&&h.perf_engine_calls==1&&h.live&&!h.quarantine&&h.perf_complete_lines++==0);
        CHECK(!strcmp(text,"SWEET GMU PERF: complete request=00302b04 words=43 ack=0002047e/00300000/00000000; no BW/TEST/normal HFI_ON/GPU/Metal qualification\n"));
    }
    if(strstr(text,"SWEET GMU PERF: partial")){
        CHECK(h.perf_mode&&h.quarantine==1&&!h.live&&h.perf_partial_lines++==0);
    }
    if(strstr(text,"SWEET GMU BW: complete")){
        CHECK(h.bw_mode&&h.bw_engine_calls==1&&h.live&&!h.quarantine&&h.bw_complete_lines++==0&&h.perf_complete_lines==1);
        CHECK(!strcmp(text,"SWEET GMU BW: complete request=0040a003 words=160 levels=13 cnoc=1 ddr=3 waits=00000000/00000000 ack=0002047e/00400000/00000000\n"));
    }
    if(strstr(text,"SWEET GMU TEST: complete")){
        CHECK(h.bw_mode&&h.bw_engine_calls==1&&h.live&&!h.quarantine&&h.test_complete_lines++==0&&h.bw_complete_lines==1);
        CHECK(!strcmp(text,"SWEET GMU TEST: complete request=00500105 words=1 ack=0002047e/00500000/00000000; native legacy startup only\n"));
    }
    if(strstr(text,"SWEET GMU BW: partial"))CHECK(h.bw_mode&&h.quarantine==1&&!h.live&&h.bw_partial_lines++==0);
    if(strstr(text,"SWEET GMU TEST: partial"))CHECK(h.bw_mode&&h.quarantine==1&&!h.live&&h.test_partial_lines++==0);
    if(strstr(text,"SWEET GMU DCVS: request")){
        CHECK(h.dcvs_mode&&h.dcvs_engine_calls==1&&h.live&&!h.quarantine&&h.dcvs_request_lines++==0&&h.test_complete_lines==1);
        CHECK(!strcmp(text,"SWEET GMU DCVS: request perf_index=1 hz=253000000 bw_index=5 Bps=2188000000 option=00000000 perf=30000001 bw=00005005; requested, not measured\n"));
    }
    if(strstr(text,"SWEET GMU DCVS: complete")){
        CHECK(h.dcvs_mode&&h.dcvs_engine_calls==1&&h.live&&!h.quarantine&&h.dcvs_complete_lines++==0&&h.dcvs_request_lines==1);
        CHECK(!strcmp(text,"SWEET GMU DCVS: complete before=00000000 ack=80000000 cleared=00000000 return=00000000; native register/OOB request only\n"));
    }
    if(strstr(text,"SWEET GMU DCVS: partial"))CHECK(h.dcvs_mode&&h.quarantine==1&&!h.live&&h.dcvs_partial_lines++<2);
    if(strstr(text,"SWEET GMU SMMU FAIL:")){CHECK(h.quarantine==1&&!h.live);++h.diag_lines;}
    if(strstr(text,"SWEET GMU SMMU IMPL:")){
        CHECK(!strcmp(text,"SWEET GMU SMMU IMPL: off=06b68 requested=9a82a382 readback=0a800082 policy=native-write; equality unqualified\n"));
        CHECK(h.live?!h.quarantine:h.quarantine==1);++h.impl_lines;
    }
    if(strstr(text,"SWEET GMU ATOS FAIL:")){
        CHECK(h.quarantine==1&&!h.live);
        CHECK(!strcmp(text,"SWEET GMU ATOS FAIL: stream=5 bank=4 iova=00000000 expected=ffffffffffffffff par=0000000300000211 mapped=131 level=3\n"));
        ++h.atos_lines;
    }
    if(strstr(text,"SWEET GMU FW READBACK:")){
        CHECK(h.quarantine==1&&!h.live);
        CHECK(!strcmp(text,"SWEET GMU FW READBACK: phase=0 check=1 window=1 off=01038 mask=ffffffff expected=00000000 actual=12340000\n"));
        ++h.fw_diag_lines;
    }
    if(strstr(text,"SWEET GMU FW IMPL:")){
        unsigned index=h.fw_impl_lines++;CHECK(index<3);char expected[192];
        static const uint32_t raw[]={0x82204514,0x12345678,0x60001000};
        snprintf(expected,sizeof(expected),"SWEET GMU FW IMPL: off=%05x requested=00000000 readback=%08x policy=native-write; equality unqualified\n",0x1034+8*index,raw[index]);
        CHECK(!strcmp(text,expected));CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU PDC MSGID:")){
        unsigned index=h.fw_pdc_lines++;CHECK(index<6);char expected[192];
        unsigned off=index<3?0x15d4+16*index:0x1764+16*(index-3);
        snprintf(expected,sizeof(expected),"SWEET GMU PDC MSGID: off=%05x requested=00010108 readback=00010100 checked_mask=00010100 policy=native-write; other bits unqualified\n",off);
        CHECK(!strcmp(text,expected));CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU AO MASK:")){
        CHECK(h.fw_ao_lines++==0);
        CHECK(!strcmp(text,"SWEET GMU AO MASK: off=02c18 requested=ffffffff readback=0000003f checked_mask=0000003b policy=native-write; other bits unqualified\n"));
        CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU CM3 CFG:")){
        CHECK(h.fw_cm3_lines++==0);
        CHECK(!strcmp(text,"SWEET GMU CM3 CFG: off=020b4 requested=00004052 readback=00000052 checked_mask=00000200 expected=00000000 policy=native-write; other bits unqualified\n"));
        CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU BOOT CFG:")){
        unsigned index=h.fw_bootcfg_lines++;CHECK(index<3&&h.fw_cm3_lines==1&&h.fw_ao_lines==1);
        static const unsigned offsets[]={0x103c,0x1000,0x1004};
        static const uint32_t raw[]={0,0,0x80000001};char expected[192];
        snprintf(expected,sizeof(expected),"SWEET GMU BOOT CFG: off=%05x requested=00000001 readback=%08x policy=native-write; equality unqualified\n",offsets[index],raw[index]);
        CHECK(!strcmp(text,expected));CHECK(h.live?!h.quarantine:h.quarantine==1);
    }
    if(strstr(text,"SWEET GMU HFI REPLY:")){
        CHECK(h.quarantine==1&&!h.live&&h.fw_reply_lines++==0&&h.fw_bootcfg_lines==3);
        const char *expected=h.engine_fail==17?
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=0040a003 expected=3 words=3 captured=3\n":h.engine_fail==19?
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=00500105 expected=3 words=3 captured=3\n":h.engine_fail==14?
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=00302b04 expected=3 words=3 captured=3\n":h.engine_fail==13?
            "SWEET GMU HFI REPLY: phase=5 site=1 reason=7 queue=2 request=00100500 expected=3 words=0 captured=0\n":
            "SWEET GMU HFI REPLY: phase=5 site=2 reason=4 queue=1 request=00100500 expected=3 words=19 captured=19\n";
        CHECK(!strcmp(text,expected));
    }
    if(strstr(text,"SWEET GMU HFI WORD:")){
        unsigned index=h.fw_word_lines++;CHECK(h.quarantine==1&&!h.live&&h.fw_reply_lines==1&&index<19&&(h.engine_fail==12||h.engine_fail==14||h.engine_fail==17||h.engine_fail==19));
        uint32_t raw=(h.engine_fail==17||h.engine_fail==19)?(index==0?0x0002037e:index==1?0x00300000:0):h.engine_fail==14?(index==0?0x0002037e:index==1?0x00200000:0):index==0?0x0012137e:index==1?0x00000500:0xa5000000u+index;char expected[192];
        snprintf(expected,sizeof(expected),"SWEET GMU HFI WORD: index=%u value=%08x\n",index,raw);CHECK(!strcmp(text,expected));
    }
    return n;
}
bool PE_parse_boot_argn(const char *name,void *out,size_t n)
{
 CHECK(n==sizeof(int));static const char *const on[]={"sweetgpuzap","sweetbusvote","sweetpasprobe","sweetpasstage","sweetcxpower","sweetgmuclk","sweetgmufw","sweetgmuperf","sweetgmubw","sweetgmudcvs","sweetgpucontext","sweetgpustart"};
 static const char *const off[]={"sweetpasinit","sweetpasmem","sweettouchmode","sweetwdtpet","sweetreboot","sweetbusprobe","sweetgpuprobe","sweetscmprobe","sweetwdttest"};
 for(unsigned i=0;i<12;i++)if(!strcmp(name,on[i])){*(int*)out=i==0?z.flag:z.bad_flag==i+1?0:1;return true;}
 for(unsigned i=0;i<9;i++)if(!strcmp(name,off[i])){if(i==0&&z.missing_init)return false;*(int*)out=z.bad_off==i+1?1:0;return true;}
 CHECK(false);return false;
}
int ml_get_interrupts_enabled(void){return h.context!=1;}
int ml_at_interrupt_context(void){return h.context==2;}
int get_preemption_level(void){return h.context==3;}
uint64_t mach_absolute_time(void){return h.now;}
void clock_interval_to_deadline(unsigned n,uint64_t scale,uint64_t *out)
{
    bool seconds=n==8||(h.gpu_mode&&n==5)||(start_mode&&n==4)||(cp_active&&n==2)||
        (z.enabled&&(n==1||n==2||n==5||n==20));
    CHECK((seconds&&scale==NSEC_PER_SEC)||(start_mode&&(n==2000||n==100||n==4000)&&scale==NSEC_PER_SEC/1000));
    *out=h.now+n*scale;
}
bool gauguin_wdt_lease_check_budget(uint32_t n)
{
    CHECK(n==3u*32765||n==13u*32765||(h.gpu_mode&&n==10u*32765)||(start_mode&&n==8u*32765));++h.budgets;
    host_core_budget();
    host_cp_budget();
    host_zap_budget();
    host_unsecure_budget();
    host_write_budget();
    host_ib_budget();
    if(h.budgets==h.expire)h.now=8*NSEC_PER_SEC;
    if(h.budgets==h.budget_fail)h.live=false;
    return h.live;
}
void gauguin_wdt_lease_quarantine(void){++h.quarantine;h.live=false;}
bool sweet_gmu_clock_quiet(uint32_t *gx){if(h.clock_bad||(start_mode&&h.gx_on))return false;*gx=0;return true;}
bool sweet_gmu_clock_live(bool allow,uint32_t *gx)
{CHECK(!z.auth_done||host_unsecure_active()||host_write_active()||host_ib_active());h.allow_gx+=allow;*gx=h.gx_on?0x80000000u:0;return !h.clock_bad&&(allow||!h.gx_on);}
bool sweet_gmu_irq_quiet(uint32_t raw[3]){CHECK(!z.auth_done||host_unsecure_active()||host_write_active()||host_ib_active());raw[0]=raw[2]=0;raw[1]=h.core_irq?0x1000:0;return !h.irq_bad;}
bool sweet_pas_stage_owner_valid(const struct sweet_pas_cpu_stage *p)
{CHECK(!z.auth_done);++h.owner_calls;return h.owner_calls!=h.owner_fail&&p&&p->pa==owner&&p->metadata_bytes==6860&&p->reserved_bytes==16384;}
boolean_t pmap_valid_page(ppnum_t pn)
{
    bool found=(start_mode&&pn==0x3d00000/16384)||(pn>=owner/16384&&pn<(owner+1048576)/16384)||pn==0x3d7c000/16384||
        (pn>=0x3d40000/16384&&pn<0x3d50000/16384);
    for(unsigned n=0;n<5;n++)found|=pn>=fw_bases[n]/16384&&pn<(fw_bases[n]+fw_sizes[n])/16384;
    if(core_mode)for(unsigned n=0;n<6;n++)found|=pn==(0x03d00000+core_offsets[n])/16384;
    CHECK(found);
    return (ibf.active&&ibf.nc_kind==2&&pn==(owner+0x9c000+16384*ibf.nc_page)/16384)||(w.active&&w.nc_kind==2&&pn==(owner+0x9c000+16384*w.nc_page)/16384)||++h.pmap_calls==h.pmap_fail||(core_dev_valid&&pn==(0x03d00000+core_offsets[core_dev_valid-1])/16384)||
        ((cp_active||u.active||w.active||ibf.active)&&cp_nc_bad==2&&pn==(owner+0xa8000+16384*(cp_nc_page-1))/16384);
}
unsigned pmap_cache_attributes(ppnum_t pn)
{return (ibf.active&&ibf.nc_kind==1&&pn==(owner+0x9c000+16384*ibf.nc_page)/16384)||(w.active&&w.nc_kind==1&&pn==(owner+0x9c000+16384*w.nc_page)/16384)||h.pmap_calls==h.attr_fail||(core_attr_bad&&pn==(owner+0xb4000)/16384)||(core_dev_bad&&pn==(0x03d00000+core_offsets[core_dev_bad-1])/16384)||
    ((cp_active||u.active||w.active||ibf.active)&&((cp_nc_bad==1&&pn==(owner+0xa8000+16384*(cp_nc_page-1))/16384)||(cp_dev_bad&&pn==0x03d00000/16384)))?0:pn>=owner/16384?0xd0000006u:0xd0000007u;}
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t bytes,vm_prot_t prot)
{
    ++h.maps;CHECK(prot==3&&h.maps<=(core_mode?14u:start_mode?8u:h.firmware?7u:2u));
    if(h.maps>8){
        CHECK(core_mode&&core_active&&sweet_gpu_start_state()==GMB_READY&&bytes==16384&&pa==0x03d00000+core_offsets[h.maps-9]);
        if(h.map_fail==h.maps)return 0;
        if(core_overflow==h.maps)return UINTPTR_MAX-16383u;
        return (vm_offset_t)core_extra[h.maps-9]+(h.misalign==h.maps);
    }
    if(h.maps<=2)CHECK(h.maps==1?(pa==0x3d7c000&&bytes==16384):(pa==0x3d40000&&bytes==65536));
    else if(h.maps==8)CHECK(start_mode&&pa==0x3d00000&&bytes==16384);
    else CHECK(pa==fw_bases[h.maps-3]&&bytes==fw_sizes[h.maps-3]);
    if(h.map_fail==h.maps)return 0;
    if(h.overflow==1&&h.maps==2)return UINTPTR_MAX-16383u;
    if(h.maps==8)return (vm_offset_t)core_page+(h.misalign==8);
    return (vm_offset_t)(h.maps==1?reset_page:h.maps==2?smmu:fw_page[h.maps-3])+(h.misalign==h.maps);
}
vm_offset_t ml_io_map_wcomb(vm_offset_t pa,vm_size_t bytes)
{CHECK(pa==owner+16384&&bytes==1048576-16384&&!h.nc_maps);++h.nc_maps;return h.overflow==2?UINTPTR_MAX-16383u:(vm_offset_t)(ram+16384);}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    ++h.translations;uint64_t pa=0;
    if(va>=(uintptr_t)reset_page&&va<(uintptr_t)reset_page+sizeof(reset_page))pa=0x3d7c000+va-(uintptr_t)reset_page;
    else if(va>=(uintptr_t)smmu&&va<(uintptr_t)smmu+sizeof(smmu))pa=0x3d40000+va-(uintptr_t)smmu;
    else if(va>=(uintptr_t)ram+16384&&va<(uintptr_t)ram+sizeof(ram))pa=owner+va-(uintptr_t)ram;
    else if(start_mode&&va>=(uintptr_t)core_page&&va<(uintptr_t)core_page+sizeof(core_page))pa=0x3d00000+va-(uintptr_t)core_page;
    else if(core_mode&&va>=(uintptr_t)core_extra&&va<(uintptr_t)core_extra+sizeof(core_extra)){
        unsigned n=(unsigned)(va-(uintptr_t)core_extra)/16384;pa=0x03d00000+core_offsets[n]+va-(uintptr_t)core_extra[n];
        if(core_phys_fail==n+9)++pa;
    }
    else if(core_mode&&core_overflow&&va>=UINTPTR_MAX-16383u)pa=0;
    else {bool found=false;for(unsigned n=0;n<5;n++)if(va>=(uintptr_t)fw_page[n]&&va<(uintptr_t)fw_page[n]+fw_sizes[n]){found=true;pa=fw_bases[n]+va-(uintptr_t)fw_page[n];break;}CHECK(found);}
    if(cp_active&&cp_physical_bad&&va>=(uintptr_t)ram+0xa8000+16384*(cp_physical_bad-1)&&va<(uintptr_t)ram+0xa8000+16384*cp_physical_bad)++pa;
    if(ibf.active&&ibf.phys_bad&&va>=(uintptr_t)ram+0x9c000+16384*(ibf.phys_bad-1)&&va<(uintptr_t)ram+0x9c000+16384*ibf.phys_bad)++pa;
    if(w.active&&w.phys_bad&&va>=(uintptr_t)ram+0x9c000+16384*(w.phys_bad-1)&&va<(uintptr_t)ram+0x9c000+16384*w.phys_bad)++pa;
    return pa+(h.translations==h.fail_translation);
}
void *IOMalloc(size_t n){CHECK(n==65536||n==16384);++h.allocs;return h.alloc_fail?NULL:malloc(n);}
void IOFree(void *p,size_t n){CHECK((n==65536||n==16384)&&p);++h.frees;free(p);}
void delay(unsigned us){CHECK(us==5||us==10||us==100);if(start_mode)h.now+=(uint64_t)us*1000;}
void IOSleep(unsigned ms){CHECK(h.gpu_mode&&ms==30&&(h.gpu_smc_calls||z.enabled)&&h.live);h.now+=(uint64_t)ms*1000000;}
void sweet_log_mark_sync(const char *s){CHECK(s);if(!strncmp(s,"SWEET GPU UNSECURE",18)||!strncmp(s,"SWEET GPU WRITE",15)||!strncmp(s,"SWEET GPU IB",12))CHECK(strlen(s)<256);else CHECK(strlen(s)<192);}
void sweet_log_flush_now(void){}
static uint32_t mmio_read32(vm_offset_t address)
{
    CHECK(h.live&&(!z.auth_done||host_unsecure_active()||host_write_active()||host_ib_active()));++h.reads;
    if(address==(uintptr_t)reset_page+0x2000){uint32_t v;memcpy(&v,reset_page+0x2000,4);return v;}
    CHECK(address>=(uintptr_t)smmu&&address+4<=(uintptr_t)smmu+65536);uint32_t v;memcpy(&v,(void *)address,4);
    unsigned off=(unsigned)(address-(uintptr_t)smmu);
    if(start_mode&&start_busy&&off>=0x8000&&(off&0xfff)==0x7f4)return 1;
    if(off>=0x8000&&(off&0xfff)==0x58){
        unsigned bank=(off-0x8000)/4096;uint32_t cbar,cba2r;
        memcpy(&cbar,smmu+0x1000+4*bank,4);memcpy(&cba2r,smmu+0x1800+4*bank,4);
        if(((cbar>>16)&3)==1&&(cba2r&1))v=(v&~0x600u)|0x400u;
    }
    return v;
}
static void mmio_write32(vm_offset_t address,uint32_t v)
{CHECK(h.live&&!z.auth_done&&address>=(uintptr_t)smmu&&address+4<=(uintptr_t)smmu+65536);++h.writes;memcpy((void *)address,&v,4);}
static uint64_t mmio_read64(vm_offset_t address)
{CHECK(h.live&&(!z.auth_done||host_unsecure_active()||host_write_active()||host_ib_active())&&address>=(uintptr_t)smmu&&address+8<=(uintptr_t)smmu+65536);uint64_t v;memcpy(&v,(void *)address,8);++h.reads;return v;}
static void mmio_write64(vm_offset_t address,uint64_t v)
{CHECK(h.live&&!z.auth_done&&address>=(uintptr_t)smmu&&address+8<=(uintptr_t)smmu+65536);++h.writes64;memcpy((void *)address,&v,8);}
static void host_barrier(void)
{
    ++h.barriers;
}
static void host_sqe_dsb(void);
static void host_dsb(void)
{host_sqe_dsb();host_barrier();if(h.corrupt==1&&h.nc_maps&&h.allocs&&!h.frees){ram[0x10000]=0x71;h.corrupt=2;}}
enum gsm_result gsm_configure_once(struct gsm_context *ctx,const struct gsm_ops *o,
    const struct ggm_plan *p,struct gsm_receipt *out)
{
    ++h.smmu_calls;CHECK(ctx&&o&&p&&out&&p->owner_pa==owner);
    if(h.smmu_fail==1)return GSM_INHERITED;
    if(!o->guard(o->cookie))return GSM_IO;
    struct ggm_s1_config cfg;
    if(!o->prepare(o->cookie,39,36,&cfg)||!o->guard(o->cookie))return GSM_IO;
    CHECK(cfg.kernel_ttbr0==owner+0x4000&&h.nc_maps==1&&h.allocs==1&&h.frees==1);
    uint32_t a;uint64_t b;
    if(!o->read32(o->cookie,0x20,&a)||!o->write32(o->cookie,0x6060,0x1055)||
       !o->write64(o->cookie,0xa020,UINT64_C(0x30000aa204000))||!o->barrier(o->cookie)||
       !o->read64(o->cookie,0xa020,&b)||!o->guard(o->cookie))return GSM_IO;
    CHECK(b==UINT64_C(0x30000aa204000));
    unsigned reads=h.reads,writes=h.writes,writes64=h.writes64;
    CHECK(!o->read32(NULL,65536,&a)&&!o->read32(NULL,1,&a)&&!o->write32(NULL,65536,0)&&!o->write32(NULL,1,0));
    CHECK(!o->read64(NULL,65536,&b)&&!o->read64(NULL,4,&b)&&!o->write64(NULL,65536,0)&&!o->write64(NULL,4,0));
    CHECK(reads==h.reads&&writes==h.writes&&writes64==h.writes64);
    ctx->implementation=(struct gsm_impl_sample){1,0x9a82a382,0x0a800082};
    if(h.smmu_fail==2){ctx->diagnostic=(struct gsm_diagnostics){GSP_USER,GSD_STORE32,0xe000,UINT32_MAX,0xc01067,0};return GSM_READBACK;}
    if(h.smmu_fail==3){
        ctx->diagnostic.phase=GSP_ATOS;
        ctx->translation=(struct gsm_atos_sample){UINT64_MAX,UINT64_C(0x300000211),1,5,4,0,131,3};
        ctx->work.translations=132;ctx->work.mapped_pages=131;return GSM_TRANSLATION;
    }
    memset(out,0,sizeof(*out));out->mapped_pages=131;out->translations=140;
    if(h.firmware){
        out->banks=8;out->groups=128;out->stream_match=1;out->micro_after=0x2378;
        out->tcr=(uint32_t)cfg.tcr;out->tcr2=(uint32_t)(cfg.tcr>>32)|0x38010;out->mair0=cfg.mair0;out->mair1=cfg.mair1;
        memcpy(smmu+0x6000,&out->micro_after,4);
        for(unsigned n=0;n<2;n++){
            out->bank[n]=n+1;out->slot[n]=n+4;out->sctlr[n]=0x00c01067;
            out->actlr[n]=0x70000000;
            out->smr_after[n]=0x80000004u+n;out->s2cr_after[n]=n+1;
            out->ttbr0[n]=owner+0x4000+0x4000*n;out->ttbr1[n]=owner+0x5000+0x4000*n;
            unsigned cb=0x8000+0x1000*(n+1);
            memcpy(smmu+cb,&out->sctlr[n],4);memcpy(smmu+cb+0x20,&out->ttbr0[n],8);memcpy(smmu+cb+0x28,&out->ttbr1[n],8);
            memcpy(smmu+cb+4,&out->actlr[n],4);memcpy(smmu+cb+0x10,&out->tcr2,4);memcpy(smmu+cb+0x30,&out->tcr,4);
            memcpy(smmu+cb+0x38,&out->mair0,4);memcpy(smmu+cb+0x3c,&out->mair1,4);
            uint32_t cbar=0x1f300,cba2r=1;memcpy(smmu+0x1000+4*(n+1),&cbar,4);memcpy(smmu+0x1800+4*(n+1),&cba2r,4);
            memcpy(smmu+0x800+4*(n+4),&out->smr_after[n],4);memcpy(smmu+0xc00+4*(n+4),&out->s2cr_after[n],4);
        }
    }
    return GSM_OK;
}
bool sweet_gmu_asset_view(struct gma_view *out)
{++h.asset_calls;if(h.asset_fail==h.asset_calls)return false;*out=(struct gma_view){fw_asset,0xb0000000,32768};return true;}
bool sweet_gpu_sqe_asset_view(struct gsa_view *out)
{CHECK(sqe_mode&&h.gpu_mode&&out);++sqe_calls;
 if(sqe_calls==1)CHECK(!h.maps&&!h.smmu_calls&&!h.gpu_smc_calls&&!h.engine_calls);
 if(sqe_calls==2)sqe_entry_budget=h.budgets;
 if(sqe_calls==3)sqe_exit_budget=h.budgets;
 if(sqe_calls==sqe_fail)return false;
 *out=(struct gsa_view){sqe_asset,UINT64_C(0x182600000),32304};
 if(sqe_calls==3){if(sqe_drift==1)out->data+=4;else if(sqe_drift==2)out->pa+=16384;else if(sqe_drift==3)out->bytes-=4;}
 return true;}
bool gmf_plan_valid(const struct gmf_plan *p){return p&&p->address[0]==0x30000;}
/* Typed dependency seam; actual policy decoder is exercised in its own suite. */
bool gmf_bw_plan_valid(const struct gmf_bw_plan *p){return p&&p->db[0].address==0x50000&&p->db[3].address==0x50054;}
static uint32_t fw_read32(vm_offset_t address);
static void fw_write32(vm_offset_t address,uint32_t value);
static void host_gpu_smc(void *,struct gpa_registers *);
static bool host_core_store(vm_offset_t,uint32_t);
static void host_core_read(vm_offset_t);
enum gmf_result gmf_bootstrap_once(struct gmf_context *,const struct gmf_ops *,const struct gmf_plan *,struct gmf_receipt *);
#define printf host_printf
@SOURCE@
#undef printf
static void host_sqe_dsb(void)
{if(sqe_mode&&sqe_corrupt&&ggb_sqe_written==8192&&!ggb_sqe_checked){ram[0xa0000+4*(sqe_corrupt-1)]^=1;sqe_corrupt=0;}}
static void host_core_budget(void)
{
    if(!core_active||ggc_context.phase!=core_fail_phase||core_fired||!core_fail_kind)return;
    core_fired=1;uint32_t v=1;
    if(core_fail_kind==1)h.clock_bad=1;
    else if(core_fail_kind==2)h.irq_bad=1;
    else if(core_fail_kind==3)memcpy(smmu+0x48,&v,4);
    else if(core_fail_kind==4){uint64_t r=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&r,8);}
    else if(core_fail_kind==5){v=0;memcpy(smmu+0xc00+4*ggb_smmu.slot,&v,4);}
    else if(core_fail_kind==6)core_attr_bad=1;
    else if(core_fail_kind==7)ggb_sqe_loaded=0;
    else if(core_fail_kind==8)memcpy(reset_page+0x2000,&v,4);
    else if(core_fail_kind==9)h.now=ggc_deadline;
    else if(core_fail_kind==10)memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x34,&v,4);
    else CHECK(false);
}
static void reset(void)
{
    CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));memset(&u,0,sizeof(u));memset(&w,0,sizeof(w));memset(&ibf,0,sizeof(ibf));
    ggib_lifecycle=ggib_phase=ggib_sealed=ggib_samples=0;ggib_entry=ggib_phase_entry=ggib_deadline=ggib_phase_end=ggib_last_now=0;
    memset(&ggib_context,0,sizeof(ggib_context));memset(&ggib_work,0,sizeof(ggib_work));memset(&ggib_diagnostic,0,sizeof(ggib_diagnostic));ggib_result=GGI_OK;
    ggib_before_first=ggib_before_last=ggib_after_first=ggib_after_last=0;
    ggwb_lifecycle=ggwb_phase=ggwb_sealed=ggwb_samples=0;ggwb_entry=ggwb_phase_entry=ggwb_deadline=ggwb_phase_end=ggwb_last_now=0;
    memset(&ggwb_context,0,sizeof(ggwb_context));memset(&ggwb_work,0,sizeof(ggwb_work));memset(&ggwb_diagnostic,0,sizeof(ggwb_diagnostic));ggwb_result=GGW_OK;
    ggwb_before_first=ggwb_before_last=ggwb_after_first=ggwb_after_last=0;
    ggb_data_selected=ggb_data_ready=ggb_data_mode=0;memset(&ggb_data_plan,0,sizeof(ggb_data_plan));
    ggub_lifecycle=ggub_phase=ggub_sealed=0;ggub_entry=ggub_phase_entry=ggub_deadline=ggub_phase_end=ggub_last_now=0;
    memset(&ggub_context,0,sizeof(ggub_context));memset(&ggub_work,0,sizeof(ggub_work));memset(&ggub_diagnostic,0,sizeof(ggub_diagnostic));ggub_result=GGU_OK;
    memset(&z,0,sizeof(z));z.flag=(int)fixture_gpu_mode;gpzb_lifecycle=0;gpzb_last_now=0;memset(&gpzb_context,0,sizeof(gpzb_context));memset(&gpzb_work,0,sizeof(gpzb_work));memset(&gpzb_diagnostic,0,sizeof(gpzb_diagnostic));
    ++cases;memset(&h,0,sizeof(h));h.live=true;memset(ram,0xa5,sizeof(ram));memset(reset_page,0,sizeof(reset_page));memset(smmu,0,sizeof(smmu));
    cp_mode=cp_active=cp_complete=cp_partial=cp_words=cp_guard_lines=0;
    cp_stores=cp_memstores=cp_memreads=cp_drop=cp_fences=cp_submits=cp_accepted=cp_keep=0;
    cp_shadow_delay=cp_busy_delay=cp_shadow_reads=cp_busy_reads=cp_bad_rptr=cp_bad_busy=0;
    cp_fail_phase=cp_fail_kind=cp_fired=cp_nc_page=cp_nc_bad=cp_dev_bad=cp_physical_bad=0;
    cp_stop_store=cp_expire_store=cp_stop_mem=cp_expire_mem=cp_corrupt_read=cp_drop_write=cp_counter_reads=cp_wrap=0;cp_time_step=0;
    ggq_board_lifecycle=ggq_board_phase=0;ggq_deadline=ggq_phase_deadline=ggq_entry=ggq_phase_entry=0;ggq_result=0;
    memset(&ggq_guard_diagnostic,0,sizeof(ggq_guard_diagnostic));memset(&ggq_context,0,sizeof(ggq_context));memset(&ggq_work,0,sizeof(ggq_work));
    core_mode=core_active=core_reads=core_stores=core_memstores=core_complete=core_partial=core_rgl_lines=0;
    core_fail_phase=core_fail_kind=core_fired=core_attr_bad=core_overflow=core_stop_after=core_expire=0;
    core_phys_fail=core_dev_bad=core_dev_valid=core_corrupt_word=0;
    core_ram_reads=core_ram_stop=core_mem_stop=core_batch_expire=core_guard_lines=core_memory_lines=0;
    ggc_board_lifecycle=ggc_board_phase=ggc_maps_ready=ggc_created=0;ggc_deadline=ggc_phase_deadline=0;ggc_result=0;
    ggc_entry=ggc_phase_entry=0;memset(&ggc_guard_diagnostic,0,sizeof(ggc_guard_diagnostic));
    memset(ggc_alias,0,sizeof(ggc_alias));memset(&ggc_context,0,sizeof(ggc_context));memset(&ggc_work,0,sizeof(ggc_work));memset(core_extra,0,sizeof(core_extra));
    *(uint32_t *)(void *)(reset_page+0x2000)=1;gmb_lifecycle=0;gmb_deadline=0;gmb_reset=gmb_smmu=gmb_ram=0;
    memset(&gmb_context,0,sizeof(gmb_context));memset(&gmb_work,0,sizeof(gmb_work));memset(&gmb_stage,0,sizeof(gmb_stage));
    gfw_lifecycle=0;gfw_deadline=0;memset(gfw_map,0,sizeof(gfw_map));memset(&gfw_context,0,sizeof(gfw_context));memset(&gfw_work,0,sizeof(gfw_work));memset(&gfw_asset,0,sizeof(gfw_asset));
    gfw_copy_issued=gfw_copy_compared=0;
    sqe_mode=sqe_calls=sqe_fail=sqe_corrupt=sqe_complete=sqe_partial=sqe_entry_budget=sqe_exit_budget=sqe_drift=0;
    memset(&ggb_sqe_asset,0,sizeof(ggb_sqe_asset));ggb_sqe_requested=ggb_sqe_loaded=ggb_sqe_written=ggb_sqe_checked=0;
    for(unsigned n=0;n<sizeof(sqe_asset);n++)sqe_asset[n]=(uint8_t)((n*23+11)%251);
    start_mode=start_sticky=start_missing=start_busy=start_allones=start_expire=start_reads=start_complete=start_partial=0;
    ggx_board_lifecycle=ggx_board_phase=0;ggx_deadline=ggx_phase_deadline=0;ggx_core=0;ggx_result=0;
    memset(&ggx_context,0,sizeof(ggx_context));memset(&ggx_work,0,sizeof(ggx_work));memset(core_page,0,sizeof(core_page));
    memset(&ggb_context,0,sizeof(ggb_context));memset(&ggb_plan,0,sizeof(ggb_plan));memset(&ggb_smmu,0,sizeof(ggb_smmu));
    memset(&ggb_aperture,0,sizeof(ggb_aperture));memset(&ggb_secure,0,sizeof(ggb_secure));ggb_deadline=0;ggb_started=0;ggb_result=0;ggb_secure_result=0;ggb_argument=0;
    memset(fw_page,0,sizeof(fw_page));for(unsigned n=0;n<sizeof(fw_asset);n++)fw_asset[n]=(uint8_t)(n*19+3);
}
static enum gmb_result run(struct gmb_receipt *out)
{struct sweet_pas_cpu_stage s={owner,6860,16384};return sweet_gmu_smmu_once(&s,out);}
static void failed(void)
{
    struct gmb_receipt out,before;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(run(&out)!=GMB_OK&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!memcmp(&out,&before,sizeof(out)));
    unsigned reads=h.reads,maps=h.maps,budgets=h.budgets;
    CHECK(run(&out)==GMB_ALREADY&&reads==h.reads&&maps==h.maps&&budgets==h.budgets&&!memcmp(&out,&before,sizeof(out)));
    for(unsigned i=0;i<16384;i++)CHECK(ram[i]==0xa5);
    for(unsigned i=0x9c000;i<1048576;i++)CHECK(ram[i]==0xa5);
}
static void happy(void)
{
    reset();struct gmb_receipt out;CHECK(run(&out)==GMB_OK&&sweet_gmu_board_state()==GMB_READY&&!h.quarantine);
    CHECK(out.owner_pa==owner&&out.reset_before==1&&out.smmu.mapped_pages==131&&out.smmu.translations==140);
    CHECK(h.maps==2&&h.nc_maps==1&&h.allocs==1&&h.frees==1&&h.writes64==1);
    unsigned char *expected=malloc(1048576);CHECK(expected);memset(expected,0xa5,1048576);
    struct ggm_plan p;struct ggm_s1_config cfg;CHECK(ggm_plan_build(owner,&p));
    for(unsigned r=0;r<GGM_COUNT;r++)memset(expected+p.region[r].offset,0,p.region[r].reserved);
    CHECK(ggm_emit_tables(&p,39,36,expected+0x4000,32768,&cfg));
    CHECK(ggm_emit_hfi(&p,expected+0x8c000,32768));CHECK(!memcmp(expected,ram,1048576));free(expected);
    unsigned budgets=h.budgets;CHECK(run(&out)==GMB_ALREADY&&h.budgets==budgets);
}
static uint8_t *fw_address(vm_offset_t address)
{
    if((cp_active||u.active||w.active||ibf.active)&&address>=(uintptr_t)ram+0xa8000&&address+4<=(uintptr_t)ram+0xb1000)return (uint8_t *)address;
    if((w.active||ibf.active)&&address>=(uintptr_t)ram+0xb8000&&address+4<=(uintptr_t)ram+0xb9000)return (uint8_t *)address;
    if(address>=(uintptr_t)reset_page&&address+4<=(uintptr_t)reset_page+sizeof(reset_page))return (uint8_t *)address;
    if(address>=(uintptr_t)ram+0x8c000&&address+4<=(uintptr_t)ram+0x94000)return (uint8_t *)address;
    if(core_active&&address>=(uintptr_t)ram+0xb4000&&address+4<=(uintptr_t)ram+0xb5000)return (uint8_t *)address;
    for(unsigned n=0;n<5;n++)if(address>=(uintptr_t)fw_page[n]&&address+4<=(uintptr_t)fw_page[n]+fw_sizes[n])return (uint8_t *)address;
    if(start_mode&&address>=(uintptr_t)core_page&&address+4<=(uintptr_t)core_page+sizeof(core_page)){
        CHECK((core_mode?h.maps>=8:h.maps==8)&&ggx_context.work.ack_valid&&ggx_context.work.ack_clear_attempted&&!(gfw_work.host_info&(1u<<24)));return (uint8_t *)address;
    }
    if(core_active)for(unsigned n=0;n<6;n++)if(address>=(uintptr_t)core_extra[n]&&address+4<=(uintptr_t)core_extra[n]+16384){CHECK(h.maps>n+8&&ggc_context.phase>=GGC_ADDRESS);return (uint8_t *)address;}
    CHECK(false);return NULL;
}
static uint32_t fw_read32(vm_offset_t address)
{
    CHECK(h.live&&(!z.auth_done||host_unsecure_active()||host_write_active()||host_ib_active()));uint32_t value;memcpy(&value,fw_address(address),4);
    host_write_read(address,&value);
    host_ib_read(address,&value);
    host_unsecure_read(address,&value);
    host_cp_read(address,&value);
    host_core_read(address);
    if(start_mode&&(!core_mode||ggc_context.phase==GGC_MMU_OOB)&&address>=(uintptr_t)core_page&&address<(uintptr_t)core_page+sizeof(core_page)){
        ++start_reads;if(start_allones)value=UINT32_MAX;if(start_expire)h.now=ggx_deadline;
    }
    if(h.fw_read_corrupt&&address==(uintptr_t)fw_page[3]+0x1000+4*(h.fw_read_corrupt-1))value^=1;
    return value;
}
static uint32_t host_core_reg(vm_offset_t address)
{
    if(address>=(uintptr_t)core_page&&address+4<=(uintptr_t)core_page+16384)return (uint32_t)(address-(uintptr_t)core_page)/4;
    if(address>=(uintptr_t)reset_page&&address+4<=(uintptr_t)reset_page+16384)return (uint32_t)(0x7c000+address-(uintptr_t)reset_page)/4;
    if(address>=(uintptr_t)fw_page[0]&&address+4<=(uintptr_t)fw_page[0]+16384)return (uint32_t)(0x8c000+address-(uintptr_t)fw_page[0])/4;
    if(address>=(uintptr_t)fw_page[4]&&address+4<=(uintptr_t)fw_page[4]+16384)return (uint32_t)(0xc000+address-(uintptr_t)fw_page[4])/4;
    for(unsigned n=0;n<6;n++)if(address>=(uintptr_t)core_extra[n]&&address+4<=(uintptr_t)core_extra[n]+16384)return (uint32_t)(core_offsets[n]+address-(uintptr_t)core_extra[n])/4;
    return UINT32_MAX;
}
static void host_core_read(vm_offset_t address)
{
    if(!core_active||ggc_context.phase<GGC_ADDRESS||ggc_context.phase>GGC_REGLIST)return;
    if(address>=(uintptr_t)ram+0xb4000&&address<(uintptr_t)ram+0xb5000){
        ++core_ram_reads;
        if(core_ram_stop==core_ram_reads){if(core_batch_expire)h.now=ggc_phase_deadline;else h.clock_bad=1;}
    }
    uint32_t reg=host_core_reg(address);if(ggc_register_allowed(reg,false))++core_reads;
}
static bool host_core_store(vm_offset_t address,uint32_t value)
{
    if(!core_active)return false;
    if(ggc_context.phase==GGC_BUS){CHECK(address==(uintptr_t)fw_page[4]+0x3114&&!value&&!core_stores&&sweet_gpu_start_state()==GMB_IDLE);}
    else if(ggc_context.phase<GGC_ADDRESS||ggc_context.phase>GGC_REGLIST)return false;
    else if(address>=(uintptr_t)ram+0xb4000&&address+4<=(uintptr_t)ram+0xb5000){
        CHECK(ggc_context.phase==GGC_REGLIST&&h.maps==14);++core_memstores;
        if(core_mem_stop==core_memstores){if(core_batch_expire)h.now=ggc_phase_deadline;else h.clock_bad=1;}
        if(address==(uintptr_t)ram+0xb400c&&core_corrupt_word){ram[0xb4000+4*(core_corrupt_word-1)]^=1;core_corrupt_word=0;}
        return true;
    }else CHECK(ggc_maps_ready&&ggc_register_allowed(host_core_reg(address),true));
    ++core_stores;if(core_stop_after==core_stores)h.clock_bad=1;
    if(core_expire==core_stores)h.now=ggc_phase_deadline;
    return true;
}
static void host_cp_budget(void)
{
    if(!cp_active)return;
    if(ggq_context.phase==GGQ_WAIT)h.now+=cp_time_step;
    if(ggq_context.phase!=cp_fail_phase||cp_fired||!cp_fail_kind)return;
    cp_fired=1;uint32_t v=1;
    if(cp_fail_kind==1)h.clock_bad=1;
    else if(cp_fail_kind==2)h.irq_bad=1;
    else if(cp_fail_kind==3)memcpy(smmu+0x48,&v,4);
    else if(cp_fail_kind==4){uint64_t root=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&root,8);}
    else if(cp_fail_kind==5){v=0;memcpy(smmu+0xc00+4*ggb_smmu.slot,&v,4);}
    else if(cp_fail_kind==6){cp_nc_bad=cp_nc_page=1;}
    else if(cp_fail_kind==7)ggb_sqe_loaded=0;
    else if(cp_fail_kind==8)memcpy(reset_page+0x2000,&v,4);
    else if(cp_fail_kind==9)h.now=ggq_deadline;
    else if(cp_fail_kind==10)memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x34,&v,4);
    else if(cp_fail_kind==11)h.now=ggq_phase_deadline;
    else if(cp_fail_kind==12)ggc_context.zero_checked=1023;
    else if(cp_fail_kind==13)cp_dev_bad=1;
    else if(cp_fail_kind==14){v=1u<<9;memcpy(core_page+4*0x201,&v,4);}
    else if(cp_fail_kind==15)memcpy(core_page+4*0x823,&v,4);
    else if(cp_fail_kind==16){v=1u<<24;memcpy(reset_page+0x2648,&v,4);}
    else if(cp_fail_kind==17)h.live=false;
    else if(cp_fail_kind==18)gfw_context.perf_valid=0;
    else if(cp_fail_kind==19)ggc_board_lifecycle=GMB_RUNNING;
    else if(cp_fail_kind==20)ggb_aperture.state=1;
    else CHECK(false);
}
static void host_cp_read(vm_offset_t address,uint32_t *value)
{
    if(!cp_active)return;
    if(address==(uintptr_t)fw_page[0]+0x2c4c){*value=cp_fences++<cp_drop?3u:2u;if(!(*value&1u))cp_accepted=1;}
    if(address==(uintptr_t)fw_page[0]+0x2c30){*value=cp_bad_busy?UINT32_MAX:cp_busy_reads++<cp_busy_delay?0x80800000u:0x80000000u;}
    if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
        unsigned n=cp_counter_reads++;
        *value=!cp_wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
            n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
    }
    if(address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb1000){
        ++cp_memreads;
        if(ggq_context.phase==GGQ_WAIT){
            CHECK(address==(uintptr_t)ram+0xb0000&&cp_accepted&&cp_submits&&!cp_keep);
            if(cp_shadow_reads++>=cp_shadow_delay){*value=cp_bad_rptr?cp_bad_rptr:15;memcpy(ram+0xb0000,value,4);}
        }
        if(cp_corrupt_read==cp_memreads)*value^=1;
    }
}
static bool host_cp_store(vm_offset_t address,uint32_t value)
{
    if(!cp_active)return false;
    if(address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb1000){
        CHECK(ggq_context.phase==GGQ_MEMORY||ggq_context.phase==GGQ_COMMANDS);
        bool scratch=address>=(uintptr_t)ram+0xb0000;
        if(scratch)CHECK(ggq_context.phase==GGQ_MEMORY&&!ggq_context.work.sqe_start_attempted&&value==0);
        else if(ggq_context.phase==GGQ_MEMORY)CHECK(value==0xaaaaaaaa&&!ggq_context.work.sqe_start_attempted);
        else{CHECK(cp_memstores>=9216&&cp_memstores<9231&&address==(uintptr_t)ram+0xa8000+4*(cp_memstores-9216));CHECK(value==ggq_context.command.word[cp_memstores-9216]);}
        ++cp_memstores;
        if(cp_stop_mem==cp_memstores)h.clock_bad=1;
        if(cp_expire_mem==cp_memstores)h.now=ggq_phase_deadline;
        return true;
    }
    uint32_t reg=host_core_reg(address);CHECK(ggq_register_allowed(reg,true));
    if(reg==0x808)CHECK(ggq_context.phase==GGQ_START&&value==1&&cp_memstores==9216);
    if(reg==0x1f8c3){CHECK(ggq_context.phase==GGQ_SUBMIT&&value<=1);cp_keep=value;}
    if(reg==0x807){CHECK(value==15&&cp_keep&&cp_memstores==9231&&ggq_context.work.commands_checked==8192);++cp_submits;uint32_t ctl;memcpy(&ctl,core_page+4*0x802,4);CHECK(ctl==0x0800020c);}
    ++cp_stores;
    if(cp_stop_store==cp_stores)h.clock_bad=1;
    if(cp_expire_store==cp_stores)h.now=ggq_phase_deadline;
    return true;
}

static void fw_write32(vm_offset_t address,uint32_t value)
{
    CHECK(h.live);uint8_t *p=fw_address(address);++h.fw_stores;
    if(host_write_store(address,value))return;
    if(host_ib_store(address,value))return;
    if(host_unsecure_store(address,value))return;
    if(host_cp_store(address,value)){if(cp_memstores!=cp_drop_write||address<(uintptr_t)ram+0xa8000||address>=(uintptr_t)ram+0xb1000)memcpy(p,&value,4);return;}
    if(host_core_store(address,value)){memcpy(p,&value,4);return;}
    if(address==(uintptr_t)reset_page+0x2000){CHECK(gfw_work.release_attempted==1&&gfw_work.phase==GMF_RELEASING&&value==0);if(h.fw_fail_phase==24)return;}
    if(address==(uintptr_t)reset_page+0x2650&&value==(1u<<22)){CHECK(gfw_work.oob_attempted&&gfw_work.phase==GMF_GX_REQUEST);h.gx_on=1;}
    if(address==(uintptr_t)reset_page+0x2650&&value==(1u<<23)){
        CHECK(h.dcvs_mode&&gfw_work.phase==GMF_HANDSHAKE);uint32_t ret=h.engine_fail==23?7:0;memcpy(fw_page[3]+0x6ffc,&ret,4);
    }
    if(start_mode&&address==(uintptr_t)reset_page+0x2650&&value==(1u<<16)){
        CHECK(sweet_gmu_firmware_state()==GMB_READY&&ggx_context.work.request_attempted&&ggx_context.phase==GGX_REQUEST);
        if(!start_missing){uint32_t info;memcpy(&info,reset_page+0x2648,4);info|=1u<<24;memcpy(reset_page+0x2648,&info,4);}
    }
    if(start_mode&&address==(uintptr_t)reset_page+0x2644&&value==(1u<<24)){
        CHECK(ggx_context.work.ack_valid&&ggx_context.work.ack_clear_attempted);
        if(!start_sticky){uint32_t info;memcpy(&info,reset_page+0x2648,4);info&=~(1u<<24);memcpy(reset_page+0x2648,&info,4);}
    }
    CHECK(!(start_mode&&address==(uintptr_t)reset_page+0x2650&&value==(1u<<24)));
    memcpy(p,&value,4);
}
/* Typed engine seam: exercise every actual board callback and both critical
 * ownership transitions. Real GMF sequencing/rings are tested separately by
 * test_gmu_firmware.py; these synthetic receipts are not firmware ACK evidence. */
enum gmf_result gmf_bootstrap_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,struct gmf_receipt *out)
{
    ++h.engine_calls;CHECK(ctx&&p&&out&&gmf_plan_valid(p));
    if(h.gpu_drift==1){uint32_t bad=0;memcpy(smmu+0x8000+4096*ggb_smmu.bank,&bad,4);}
    if(h.engine_fail==1)return GMF_TIMEOUT;
    if(h.engine_fail==5){ctx->diagnostic=(struct gmf_diagnostic){1,GMF_RESET,GMFD_STORE32,GMF_AO,0x1038,UINT32_MAX,0,0x12340000};return GMF_READBACK;}
    ctx->hidden_valid=h.engine_fail==6?1u:7u;
    ctx->hidden_readback[0]=0x82204514;ctx->hidden_readback[1]=0x12345678;ctx->hidden_readback[2]=0x60001000;
    if(h.engine_fail==6)return GMF_TIMEOUT;
    ctx->pdc_msgid_valid=h.engine_fail==7?1u:63u;
    for(unsigned n=0;n<6;n++)ctx->pdc_msgid_readback[n]=0x10100;
    if(h.engine_fail==7)return GMF_TIMEOUT;
    const uint8_t *data=NULL;size_t bytes=0;struct gmf_copy copy;
    if(!o->guard(NULL,GMF_RESET)||!o->asset(NULL,&data,&bytes)||
       !o->copy(NULL,data,bytes,&copy))return GMF_ASSET;
    CHECK(copy.written==8192&&copy.checked==8192&&!memcmp(fw_page[3]+0x1000,fw_asset,32768));
    ctx->ao_mask_valid=1;ctx->ao_mask_readback=0x3f;
    if(h.engine_fail==8)return GMF_TIMEOUT;
    ctx->cm3_config_valid=1;ctx->cm3_config_readback=0x52;
    if(h.engine_fail==9)return GMF_TIMEOUT;
    ctx->boot_config_valid=h.engine_fail==10?1u:7u;
    ctx->boot_config_readback[0]=0;ctx->boot_config_readback[1]=0;ctx->boot_config_readback[2]=0x80000001;
    if(h.engine_fail==10||h.engine_fail==11)return GMF_TIMEOUT;
    for(unsigned i=0;i<4096;i++)CHECK(!fw_page[3][i]);
    for(unsigned i=0x9000;i<49152;i++)CHECK(!fw_page[3][i]);
    uint32_t v;unsigned stores=h.fw_stores;
    CHECK(!o->read(NULL,GMF_WINDOWS,0,&v)&&!o->read(NULL,GMF_CSR,1,&v)&&!o->read(NULL,GMF_CSR,0x4000,&v));
    CHECK(!o->write(NULL,GMF_TCM,0xc000,0)&&!o->write(NULL,GMF_CSR,0x2000,0));
    CHECK(!o->shared_read(NULL,8192,&v)&&!o->shared_write(NULL,8192,1)&&h.fw_stores==stores);
    if(!o->shared_read(NULL,0,&v)||!o->shared_write(NULL,8191,0x98761234)||
       !o->shared_read(NULL,8191,&v)||v!=0x98761234)return GMF_IO;
    CHECK(!o->delay_us(NULL,1)&&o->delay_us(NULL,100));
    if(h.fw_fail_phase==1)h.core_irq=1;
    if(!o->guard(NULL,GMF_RELEASING)||!o->write(NULL,GMF_CSR,0x2000,0)||
       !o->barrier(NULL)||!o->guard(NULL,GMF_RELEASING))return GMF_IO;
    CHECK(!o->write(NULL,GMF_CSR,0x2000,0)&&!o->write(NULL,GMF_CSR,0x2000,1));
    if(h.engine_fail==2)return GMF_FAULT;
    if(h.fw_fail_phase==2)h.gx_on=1;
    if(!o->guard(NULL,GMF_BOOTING)||!o->guard(NULL,GMF_GX_REQUEST)||
       !o->write(NULL,GMF_CSR,0x2650,1u<<22)||!o->guard(NULL,GMF_GX_REQUEST))return GMF_IO;
    CHECK(!o->write(NULL,GMF_CSR,0x2650,1u<<22)&&h.allow_gx);
    if(h.engine_fail==3)return GMF_FAULT;
    if(h.fw_fail_phase==3){uint32_t one=1;memcpy(reset_page+0x2000,&one,4);}
    if(h.fw_fail_phase==4){uint32_t one=1;memcpy(smmu+0x48,&one,4);}
    if(h.fw_fail_phase==5){uint32_t one=2;memcpy(smmu+0x9058,&one,4);}
    if(h.fw_fail_phase==6){uint32_t one=1;memcpy(fw_page[0]+0x2c14,&one,4);}
    if(h.fw_fail_phase==7){uint32_t one=0x8000;memcpy(reset_page+0x2648,&one,4);}
    if(h.fw_fail_phase==8){uint32_t one=1;memcpy(smmu+0x810,&one,4);}
    const unsigned changed[]={0x9004,0x9010,0x9030,0x9038,0x903c,0x1004,0x1804,0x9020,0x902c,0xc10,0x6000,0};
    if(h.fw_fail_phase>=9&&h.fw_fail_phase<9+sizeof(changed)/sizeof(*changed))smmu[changed[h.fw_fail_phase-9]]^=1;
    if(h.fw_fail_phase==21)h.live=false;
    if(h.fw_fail_phase==22)h.now=gfw_deadline;
    if(h.fw_fail_phase==23)h.budget_fail=h.budgets+2;
    if(h.ctx_fault)memcpy(smmu+0x9058,&h.ctx_fault,4);
    if(!o->guard(NULL,GMF_HFI_START)||!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;
    if(h.engine_fail==4)return GMF_FAULT;
    if(h.engine_fail==12||h.engine_fail==13){
        struct gmf_reply_diagnostic *d=&ctx->reply_diagnostic;
        *d=(struct gmf_reply_diagnostic){.valid=1,.phase=GMF_HANDSHAKE,.site=h.engine_fail==13?GMFR_DRAIN:GMFR_REQUEST,.reason=h.engine_fail==13?GMFR_LIMIT:GMFR_ECHO,.queue=h.engine_fail==13?2:1,.request_header=0x00100500,.expected_words=3,.words=h.engine_fail==13?0:19,.captured=h.engine_fail==13?0:19};
        for(unsigned i=0;i<d->captured;i++)d->data[i]=i==0?0x0012137e:i==1?0x00000500:0xa5000000u+i;
        return GMF_ACK;
    }
    CHECK(!o->guard(NULL,GMF_RESET)&&!o->guard(NULL,GMF_DONE+1));
    memset(out,0,sizeof(*out));out->phase=GMF_DONE;out->fw_result=0xbabeface;out->reported_version=0x100b0000;return GMF_OK;
}
enum gmf_result gmf_bootstrap_perf_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,struct gmf_receipt *out)
{
    CHECK(h.perf_mode&&h.perf_engine_calls++==0);ctx->perf_requested=1;
    enum gmf_result rc=gmf_bootstrap_once(ctx,o,p,out);if(rc)return rc;
    ctx->perf_started=1;
    if(h.engine_fail==14){
        ctx->reply_diagnostic=(struct gmf_reply_diagnostic){.valid=1,.phase=GMF_HANDSHAKE,.site=GMFR_REQUEST,.reason=GMFR_ECHO,.queue=1,.request_header=0x00302b04,.expected_words=3,.words=3,.captured=3,.data={0x0002037e,0x00200000,0}};
        return GMF_ACK;
    }
    if(h.engine_fail!=15){ctx->perf_valid=1;ctx->perf_ack[0]=0x0002047e;ctx->perf_ack[1]=0x00300000;}
    if(h.engine_fail==16)h.now=gfw_deadline;
    return GMF_OK;
}
enum gmf_result gmf_bootstrap_bw_test_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmf_receipt *out)
{
    CHECK(h.bw_mode&&h.bw_engine_calls++==0&&gmf_bw_plan_valid(bw));ctx->bw_requested=1;
    enum gmf_result rc=gmf_bootstrap_perf_once(ctx,o,p,out);if(rc)return rc;
    if(!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;
    ctx->bw_started=1;
    if(h.engine_fail==17||h.engine_fail==19){
        unsigned test=h.engine_fail==19;
        if(test){ctx->bw_valid=1;ctx->test_started=1;}
        ctx->reply_diagnostic=(struct gmf_reply_diagnostic){.valid=1,.phase=GMF_HANDSHAKE,.site=GMFR_REQUEST,.reason=GMFR_ECHO,.queue=1,.request_header=test?0x00500105:0x0040a003,.expected_words=3,.words=3,.captured=3,.data={0x0002037e,0x00300000,0}};
        return GMF_ACK;
    }
    ctx->bw_ack[0]=0x0002047e;ctx->bw_ack[1]=0x00400000;
    ctx->bw_valid=h.engine_fail!=18;
    ctx->test_started=1;ctx->test_valid=h.engine_fail!=20;
    ctx->test_ack[0]=0x0002047e;ctx->test_ack[1]=0x00500000;
    if(h.engine_fail==21)h.now=gfw_deadline;
    return GMF_OK;
}
enum gmf_result gmf_bootstrap_dcvs_once(struct gmf_context *ctx,const struct gmf_ops *o,
    const struct gmf_plan *p,const struct gmf_bw_plan *bw,struct gmf_receipt *out)
{
    CHECK(h.dcvs_mode&&h.dcvs_engine_calls++==0);ctx->dcvs_requested=1;
    enum gmf_result rc=gmf_bootstrap_bw_test_once(ctx,o,p,bw,out);if(rc)return rc;
    if(!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;ctx->dcvs_started=1;
    const unsigned window[]={GMF_TCM,GMF_TCM,GMF_TCM,GMF_CSR,GMF_CSR,GMF_CSR};
    const uint32_t off[]={0x6ff0,0x6ff4,0x6ff8,0x2650,0x2644,0x2650};
    const uint32_t value[]={0,0x30000001,0x5005,1u<<23,1u<<31,1u<<31};
    for(unsigned n=0;n<6;n++){
        if(n==3)ctx->dcvs_trigger_attempted=1;
        if(n==4){if(h.engine_fail==22)return GMF_TIMEOUT;ctx->dcvs_ack_valid=1;ctx->dcvs_ack=0x80000000;}
        if(n==5){if(!o->read(NULL,GMF_TCM,0x6ffc,&ctx->dcvs_return))return GMF_IO;ctx->dcvs_return_valid=1;ctx->dcvs_clear_attempted=1;}
        if(!o->guard(NULL,GMF_HANDSHAKE)||!o->barrier(NULL)||!o->write(NULL,(enum gmf_window)window[n],off[n],value[n])||!o->guard(NULL,GMF_HANDSHAKE))return GMF_IO;
    }
    if(ctx->dcvs_return)return GMF_DCVS_RESULT;
    ctx->dcvs_valid=h.engine_fail!=24;
    if(h.dcvs_missing){uint32_t *flag[]={&ctx->dcvs_requested,&ctx->dcvs_started,&ctx->dcvs_trigger_attempted,&ctx->dcvs_ack_valid,&ctx->dcvs_return_valid,&ctx->dcvs_clear_attempted,&ctx->dcvs_valid};
        CHECK(h.dcvs_missing<=8);if(h.dcvs_missing==8)ctx->dcvs_return=1;else *flag[h.dcvs_missing-1]=0;}
    if(h.engine_fail==25)h.now=gfw_deadline;
    if(h.gpu_drift==2){uint32_t bad=0x20000;memcpy(smmu+0xc00+4*ggb_smmu.slot,&bad,4);}
    ctx->state=2;return GMF_OK;
}
static enum gmb_result firmware_run(struct gmb_firmware_receipt *out)
{struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;struct gmf_bw_plan bw={0};bw.db[0].address=0x50000;bw.db[3].address=0x50054;return sqe_mode?sweet_gmu_firmware_gpu_sqe_once(&s,&p,&bw,out):h.gpu_mode?sweet_gmu_firmware_gpu_once(&s,&p,&bw,out):h.dcvs_mode?sweet_gmu_firmware_dcvs_once(&s,&p,&bw,out):h.bw_mode?sweet_gmu_firmware_bw_test_once(&s,&p,&bw,out):h.perf_mode?sweet_gmu_firmware_perf_once(&s,&p,out):sweet_gmu_firmware_once(&s,&p,out);}
static void firmware_failed(void)
{
    struct gmb_firmware_receipt out,before;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(firmware_run(&out)!=GMB_OK&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!memcmp(&out,&before,sizeof(out)));
    unsigned maps=h.maps,budgets=h.budgets,stores=h.fw_stores;
    CHECK(firmware_run(&out)==GMB_ALREADY&&maps==h.maps&&budgets==h.budgets&&stores==h.fw_stores&&!memcmp(&out,&before,sizeof(out)));
}
static void firmware_cases(void)
{
    unsigned first=cases;
    reset();h.firmware=1;struct gmb_firmware_receipt out;
    CHECK(firmware_run(&out)==GMB_OK&&h.maps==7&&h.nc_maps==1&&h.engine_calls==1&&!h.quarantine);
    CHECK(h.impl_lines==1&&!h.fw_reply_lines&&!h.fw_word_lines);
    CHECK(out.reset==0&&out.release_attempted==1&&out.oob_attempted==1&&out.phase==GMF_DONE&&h.allow_gx);
    CHECK(out.firmware.fw_result==0xbabeface&&out.asset_pa==0xb0000000&&h.fw_impl_lines==3&&h.fw_pdc_lines==6&&h.fw_ao_lines==1&&h.fw_cm3_lines==1&&h.fw_bootcfg_lines==3);
    CHECK(out.fsr[0]==0x400&&out.fsr[1]==0x400);
    CHECK(sweet_gmu_firmware_state()==GMB_READY&&sweet_gmu_board_state()==GMB_READY);
    unsigned budgets=h.budgets,maps=h.maps;CHECK(firmware_run(&out)==GMB_ALREADY&&h.budgets==budgets&&h.maps==maps);
    for(unsigned n=1;n<=2;n++){reset();h.firmware=1;h.asset_fail=n;firmware_failed();if(n==1)CHECK(!h.maps&&!h.fw_stores);}
    for(unsigned n=3;n<=7;n++){reset();h.firmware=1;h.map_fail=n;firmware_failed();CHECK(!h.engine_calls);reset();h.firmware=1;h.misalign=n;firmware_failed();}
    for(unsigned n=1;n<=4;n++){reset();h.firmware=1;h.engine_fail=n;firmware_failed();CHECK(gfw_work.release_attempted==(n>=2));CHECK(gfw_work.oob_attempted==(n>=3));}
    reset();h.firmware=1;h.engine_fail=5;firmware_failed();CHECK(h.fw_diag_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=6;firmware_failed();CHECK(h.fw_impl_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=7;firmware_failed();CHECK(h.fw_impl_lines==3&&h.fw_pdc_lines==1&&!gfw_work.release_attempted&&!gfw_copy_issued);
    reset();h.firmware=1;h.engine_fail=8;firmware_failed();CHECK(h.fw_ao_lines==1&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=9;firmware_failed();CHECK(h.fw_cm3_lines==1&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=10;firmware_failed();CHECK(h.fw_bootcfg_lines==1&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=11;firmware_failed();CHECK(h.fw_bootcfg_lines==3&&!gfw_work.release_attempted&&gfw_copy_issued==8192&&gfw_copy_compared==8192);
    reset();h.firmware=1;h.engine_fail=12;firmware_failed();CHECK(h.fw_reply_lines==1&&h.fw_word_lines==19&&gfw_work.release_attempted&&gfw_work.oob_attempted);
    reset();h.firmware=1;h.engine_fail=13;firmware_failed();CHECK(h.fw_reply_lines==1&&!h.fw_word_lines&&gfw_work.release_attempted&&gfw_work.oob_attempted);
    for(unsigned n=1;n<=24;n++){reset();h.firmware=1;h.fw_fail_phase=n;firmware_failed();}
    const unsigned faultbits[]={1,2,3,4,5,6,7,8,30,31};
    for(unsigned n=0;n<sizeof(faultbits)/sizeof(*faultbits);n++){reset();h.firmware=1;h.ctx_fault=1u<<faultbits[n];firmware_failed();}
    reset();h.firmware=1;h.ctx_fault=UINT32_MAX;firmware_failed();
    for(unsigned n=1;n<=8192;n+=257){reset();h.firmware=1;h.fw_read_corrupt=n;firmware_failed();CHECK(!gfw_work.release_attempted);}
    reset();h.firmware=1;h.core_irq=1;firmware_failed();CHECK(!h.maps&&!h.engine_calls&&!h.fw_stores);
    reset();h.firmware=1;h.gx_on=1;firmware_failed();CHECK(!h.engine_calls);
    printf("GMU firmware board: %u real callback/map/copy/phase/IRQ/fault cases PASS (typed engine seam, no hardware ACKs)\n",cases-first);
}
/* Typed SMMU engine seam: actual transaction/ATOS is covered separately.
 * This exercises the real board NC publisher, retained aliases and guards. */
static enum gsm_result host_gpu_configure(struct ggs_context *c,const struct ggs_ops *o,
    const struct ggp_plan *p,const struct gsm_receipt *gmu,struct ggs_receipt *out,bool data)
{
    CHECK(h.gpu_mode&&h.gpu_context_calls++==0&&h.live&&!h.engine_calls&&!h.gpu_smc_calls);
    CHECK(gmu==&gmb_work.smmu&&p->owner_pa==owner&&ggp_plan_valid(p));
    if(h.gpu_context_fail==3)return GSM_ARGUMENT;
    c->state=1;c->phase=GGS_PREPARE;c->ops=*o;c->plan=*p;c->gmu=*gmu;c->layout=data?GGS_DATA19:GGS_BOOTSTRAP18;
    if(h.gpu_context_fail==1)return GSM_INHERITED;
    struct ggp_s1_config cfg;
    if(!o->guard(NULL)||!o->prepare(NULL,39,36,&cfg)||!o->guard(NULL))return GSM_IO;
    CHECK(h.nc_maps==1&&h.maps==2&&cfg.ttbr0==owner+0x9c000&&cfg.ttbr1==owner+0x9f000);
    CHECK(h.allocs==2&&h.frees==2);
    if(h.gpu_context_fail==2)return GSM_READBACK;
    struct ggs_receipt s={.slot=0,.bank=3,.asid=4,.ias=39,.oas=36,.groups=128,.banks=8,.stream_match=1,
        .cr0=gmu->cr0_after,.micro_before=gmu->micro_after,.micro_after=gmu->micro_after,
        .smr=0x80000000,.s2cr=3,.sctlr=0xc01167,.tcr=(uint32_t)cfg.tcr,.tcr2=(uint32_t)(cfg.tcr>>32)|0x38010,
        .mair0=cfg.mair0,.mair1=cfg.mair1,.writes=200,.polls=169,.gpu_pages=data?19u:18u,.gmu_pages=131,.translations=data?171u:168u,.layout=data?GGS_DATA19:GGS_BOOTSTRAP18,
        .ttbr0=cfg.ttbr0|UINT64_C(4)<<48,.ttbr1=cfg.ttbr1|UINT64_C(4)<<48};
    const unsigned offs[]={0xb000,0xb004,0xb010,0xb030,0xb038,0xb03c,0x100c,0x180c,0x800,0xc00};
    const uint32_t vals[]={s.sctlr,0x70000000,s.tcr2,s.tcr,s.mair0,s.mair1,0x1f300,1,s.smr,s.s2cr};
    for(unsigned i=0;i<10;i++)memcpy(smmu+offs[i],&vals[i],4);
    memcpy(smmu+0xb020,&s.ttbr0,8);memcpy(smmu+0xb028,&s.ttbr1,8);
    c->work=s;*out=s;c->phase=GGS_DONE;c->state=2;return GSM_OK;
}
enum gsm_result ggs_configure_once(struct ggs_context *c,const struct ggs_ops *o,
    const struct ggp_plan *p,const struct gsm_receipt *gmu,struct ggs_receipt *out)
{CHECK(!ggb_data_selected);return host_gpu_configure(c,o,p,gmu,out,false);}
enum gsm_result ggs_configure_data_once(struct ggs_context *c,const struct ggs_ops *o,
    const struct ggd_plan *p,const struct gsm_receipt *gmu,struct ggs_receipt *out)
{CHECK(ggb_data_selected==1&&(z.flag==3||z.flag==4)&&ggd_plan_valid(p));return host_gpu_configure(c,o,&p->bootstrap,gmu,out,true);}
unsigned ggs_data_argument_reason(const struct ggs_context *c,const struct ggs_ops *o,
    const struct ggd_plan *p,const struct gsm_receipt *gmu,const struct ggs_receipt *out)
{CHECK(c&&o&&p&&gmu&&out&&ggd_plan_valid(p)&&ggb_data_selected==1);return h.gpu_context_fail==3?15u:0u;}
unsigned ggs_argument_reason(const struct ggs_context *c,const struct ggs_ops *o,
    const struct ggp_plan *p,const struct gsm_receipt *gmu,const struct ggs_receipt *out)
{CHECK(c&&o&&p&&gmu&&out&&!h.gpu_context_calls&&!h.gpu_smc_calls&&!h.engine_calls);return h.gpu_context_fail==3?15u:0u;}
static void host_gpu_smc(void *cookie,struct gpa_registers *r)
{
    if(z.enabled){CHECK(!cookie);host_zap_smc(r);return;}
    CHECK(!cookie&&h.gpu_mode&&h.live&&!h.quarantine&&!h.engine_calls&&ggb_context_valid());
    uint32_t reset;memcpy(&reset,reset_page+0x2000,4);CHECK(reset==1&&!h.gx_on);
    ++h.gpu_smc_calls;
    if(h.gpu_smc_calls==1||h.gpu_smc_mode!=2){
        const uint64_t want[]={0x42000c1b,4,0xffff0003,0xffffffff,0xffffffff,0xffffffff,0};CHECK(!memcmp(r->x,want,sizeof(want)));
    }else CHECK(r->x[0]==1&&r->x[6]==0x619);
    r->x[0]=h.gpu_smc_mode==1?UINT64_C(0xfffffffffffffffe):h.gpu_smc_mode==2&&h.gpu_smc_calls==1?1:0;
    r->x[1]=0x111;r->x[6]=0x619; /* native CP callsite does not require x1==0 */
    if(h.gpu_smc_mode==3){uint32_t bad=0;memcpy(smmu+0xb000,&bad,4);}
}
static void firmware_perf_cases(void)
{
    unsigned first=cases;
    reset();h.firmware=h.perf_mode=1;struct gmb_firmware_receipt out;
    CHECK(firmware_run(&out)==GMB_OK&&h.perf_engine_calls==1&&h.engine_calls==1&&h.perf_complete_lines==1&&!h.perf_partial_lines);
    CHECK(out.phase==GMF_DONE&&h.maps==7&&h.nc_maps==1&&!h.quarantine);
    struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;
    unsigned budgets=h.budgets,stores=h.fw_stores,maps=h.maps;
    CHECK(sweet_gmu_firmware_once(&s,&p,&out)==GMB_ALREADY&&firmware_run(&out)==GMB_ALREADY);
    CHECK(h.budgets==budgets&&h.fw_stores==stores&&h.maps==maps&&h.perf_complete_lines==1);
    for(unsigned n=1;n<=16;n++){reset();h.firmware=h.perf_mode=1;h.engine_fail=n;firmware_failed();CHECK(h.perf_partial_lines==1&&!h.perf_complete_lines);}
    for(unsigned n=1;n<=24;n++){reset();h.firmware=h.perf_mode=1;h.fw_fail_phase=n;firmware_failed();CHECK(!h.perf_complete_lines);}
    for(unsigned n=3;n<=7;n++){reset();h.firmware=h.perf_mode=1;h.map_fail=n;firmware_failed();CHECK(!h.perf_engine_calls&&!h.perf_partial_lines);}
    for(unsigned n=1;n<=2;n++){reset();h.firmware=h.perf_mode=1;h.asset_fail=n;firmware_failed();CHECK(!h.perf_complete_lines);}
    reset();h.firmware=1;CHECK(firmware_run(&out)==GMB_OK&&!h.perf_engine_calls&&!h.perf_complete_lines);
    budgets=h.budgets;maps=h.maps;CHECK(sweet_gmu_firmware_perf_once(&s,&p,&out)==GMB_ALREADY&&h.budgets==budgets&&h.maps==maps);
    printf("GMU PERF board: %u shared lifecycle, dependency/refusal/guard and post-quarantine logging cases PASS (typed engine seam)\n",cases-first);
}
static void firmware_bw_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out,before;
    reset();h.firmware=h.perf_mode=h.bw_mode=1;
    CHECK(firmware_run(&out)==GMB_OK&&h.bw_engine_calls==1&&h.perf_engine_calls==1&&h.engine_calls==1);
    CHECK(h.perf_complete_lines==1&&h.bw_complete_lines==1&&h.test_complete_lines==1&&!h.bw_partial_lines&&!h.test_partial_lines);
    CHECK(out.phase==GMF_DONE&&h.maps==7&&h.nc_maps==1&&!h.quarantine);
    struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;
    struct gmf_bw_plan bw={0};bw.db[0].address=0x50000;bw.db[3].address=0x50054;
    unsigned budgets=h.budgets,stores=h.fw_stores,maps=h.maps;
    CHECK(sweet_gmu_firmware_once(&s,&p,&out)==GMB_ALREADY&&sweet_gmu_firmware_perf_once(&s,&p,&out)==GMB_ALREADY&&firmware_run(&out)==GMB_ALREADY);
    CHECK(h.budgets==budgets&&h.fw_stores==stores&&h.maps==maps&&h.test_complete_lines==1);
    for(unsigned n=1;n<=21;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.engine_fail=n;firmware_failed();
        CHECK(h.bw_partial_lines==1&&h.test_partial_lines==1&&!h.perf_complete_lines&&!h.bw_complete_lines&&!h.test_complete_lines);
    }
    for(unsigned n=1;n<=24;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.fw_fail_phase=n;firmware_failed();
        CHECK(!h.perf_complete_lines&&!h.bw_complete_lines&&!h.test_complete_lines);
    }
    for(unsigned n=3;n<=7;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.map_fail=n;firmware_failed();
        CHECK(!h.bw_engine_calls&&!h.bw_partial_lines&&!h.test_partial_lines);
    }
    for(unsigned n=1;n<=2;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=1;h.asset_fail=n;firmware_failed();CHECK(!h.bw_complete_lines&&!h.test_complete_lines);
    }
    reset();h.firmware=h.perf_mode=h.bw_mode=1;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,NULL,&out)==GMB_ARGUMENT);
    bw.db[3].address^=4;CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ARGUMENT);
    CHECK(!gfw_lifecycle&&!h.maps&&!h.budgets&&!h.engine_calls&&!memcmp(&out,&before,sizeof(out)));
    reset();h.firmware=1;CHECK(firmware_run(&out)==GMB_OK&&!h.bw_engine_calls&&!h.bw_complete_lines&&!h.test_complete_lines);
    bw.db[3].address^=4;CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ALREADY);
    reset();h.firmware=h.perf_mode=1;CHECK(firmware_run(&out)==GMB_OK&&!h.bw_engine_calls&&!h.bw_complete_lines&&!h.test_complete_lines);
    CHECK(sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ALREADY);
    printf("GMU BW/TEST board: %u shared ownership/once-state, prerequisites, ACK/guard refusals, post-quarantine partial and final-only completion cases PASS (typed seams)\n",cases-first);
}
static void firmware_dcvs_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out,before;
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;
    CHECK(firmware_run(&out)==GMB_OK&&h.dcvs_engine_calls==1&&h.bw_engine_calls==1&&h.perf_engine_calls==1&&h.engine_calls==1);
    CHECK(h.dcvs_request_lines==1&&h.dcvs_complete_lines==1&&!h.dcvs_partial_lines&&h.test_complete_lines==1&&out.phase==GMF_DONE&&!h.quarantine);
    struct sweet_pas_cpu_stage s={owner,6860,16384};struct gmf_plan p={0};p.address[0]=0x30000;
    struct gmf_bw_plan bw={0};bw.db[0].address=0x50000;bw.db[3].address=0x50054;
    unsigned stores=h.fw_stores,maps=h.maps,budgets=h.budgets;
    CHECK(sweet_gmu_firmware_once(&s,&p,&out)==GMB_ALREADY&&sweet_gmu_firmware_perf_once(&s,&p,&out)==GMB_ALREADY&&sweet_gmu_firmware_bw_test_once(&s,&p,&bw,&out)==GMB_ALREADY&&firmware_run(&out)==GMB_ALREADY);
    CHECK(h.fw_stores==stores&&h.maps==maps&&h.budgets==budgets&&h.dcvs_complete_lines==1);
    for(unsigned n=1;n<=25;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.engine_fail=n;firmware_failed();
        CHECK(h.dcvs_partial_lines==2&&!h.dcvs_request_lines&&!h.dcvs_complete_lines&&!h.test_complete_lines);
    }
    for(unsigned n=1;n<=8;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.dcvs_missing=n;firmware_failed();
        CHECK(!h.dcvs_complete_lines&&!h.dcvs_request_lines);
    }
    for(unsigned n=1;n<=24;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.fw_fail_phase=n;firmware_failed();CHECK(!h.dcvs_complete_lines);
    }
    for(unsigned n=3;n<=7;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.map_fail=n;firmware_failed();CHECK(!h.dcvs_engine_calls&&!h.dcvs_partial_lines);
    }
    for(unsigned n=1;n<=2;n++){
        reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;h.asset_fail=n;firmware_failed();CHECK(h.dcvs_engine_calls==n-1&&h.dcvs_partial_lines==2*(n-1)&&!gfw_context.dcvs_started);
    }
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=1;memset(&out,0xa3,sizeof(out));before=out;
    CHECK(sweet_gmu_firmware_dcvs_once(&s,&p,NULL,&out)==GMB_ARGUMENT);
    bw.db[3].address^=4;CHECK(sweet_gmu_firmware_dcvs_once(&s,&p,&bw,&out)==GMB_ARGUMENT);bw.db[3].address^=4;
    CHECK(!gfw_lifecycle&&!h.maps&&!h.budgets&&!memcmp(&out,&before,sizeof(out)));
    for(unsigned mode=0;mode<3;mode++){
        reset();h.firmware=1;h.perf_mode=mode>0;h.bw_mode=mode>1;
        CHECK(firmware_run(&out)==GMB_OK&&!h.dcvs_engine_calls&&!h.dcvs_request_lines&&!h.dcvs_complete_lines);
        CHECK(sweet_gmu_firmware_dcvs_once(&s,&p,&bw,&out)==GMB_ALREADY);
    }
    printf("GMU DCVS board: %u native mailbox callback/owner/receipt/guard/four-entry once-state and quarantine cases PASS (typed engine seams)\n",cases-first);
}
static void firmware_gpu_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out;
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;
    CHECK(firmware_run(&out)==GMB_OK&&h.gpu_context_calls==1&&h.gpu_smc_calls==1&&h.engine_calls==1);
    CHECK(h.gpu_complete_lines==1&&h.gpu_ap_complete_lines==1&&!h.gpu_partial_lines&&h.maps==7&&h.nc_maps==1);
    unsigned budgets=h.budgets,owners=h.owner_calls,translations=h.translations,pmaps=h.pmap_calls;
    CHECK(ggb_secure.returned.x[1]==0x111&&ggb_secure.returned.x[0]==0&&ggb_secure.calls==1);
    for(unsigned n=0;n<16384;n++)CHECK(ram[n]==0xa5);
    for(unsigned n=GGP_ARENA_END;n<sizeof(ram);n++)CHECK(ram[n]==0xa5);
    struct ggm_plan old;CHECK(ggm_plan_build(owner,&old));
    for(unsigned n=0;n<GGM_COUNT;n++)if(n!=GGM_HFI)for(unsigned j=0;j<old.region[n].reserved;j++)CHECK(ram[old.region[n].offset+j]==0);
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_smc_mode=2;
    CHECK(firmware_run(&out)==GMB_OK&&h.gpu_smc_calls==2&&ggb_secure.continuations==1);
    for(unsigned n=1;n<=2;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_context_fail=n;firmware_failed();CHECK(!h.gpu_smc_calls&&!h.engine_calls&&!h.gpu_complete_lines&&h.gpu_partial_lines==1);}
    reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_context_fail=3;firmware_failed();CHECK(ggb_argument==15&&h.gpu_input_lines==3&&!h.gpu_smc_calls&&!h.engine_calls&&!ggb_context.state);
    for(unsigned n=1;n<=3;n+=2){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_smc_mode=n;firmware_failed();CHECK(h.gpu_smc_calls==1&&!h.engine_calls&&!h.gpu_complete_lines);}
    for(unsigned n=1;n<=2;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.gpu_drift=n;firmware_failed();CHECK(h.gpu_smc_calls==1&&!h.gpu_complete_lines&&!h.gpu_ap_complete_lines);}
    for(unsigned n=1;n<=budgets;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.budget_fail=n;firmware_failed();CHECK(!h.gpu_complete_lines&&!h.gpu_ap_complete_lines);}
    for(unsigned n=1;n<=owners;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.owner_fail=n;firmware_failed();}
    for(unsigned n=1;n<=translations;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.fail_translation=n;firmware_failed();}
    for(unsigned n=1;n<=pmaps;n++){reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.pmap_fail=n;firmware_failed();reset();h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;h.attr_fail=n;firmware_failed();}
    printf("GPU context board: %u retained-alias/NC-publication/SCM-order/continuation/owner/budget/translation/attribute/final-drift cases PASS (typed SMMU/SMC seams, actual aperture engine)\n",cases-first);
}
static void start_setup(void)
{
    reset();start_mode=1;h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;
    struct gmb_firmware_receipt fw;CHECK(firmware_run(&fw)==GMB_OK&&gfw_context.state==2&&h.gpu_complete_lines==1);
    uint32_t a=0x12340000,b=0x56780000;memcpy(core_page+0x840,&a,4);memcpy(core_page+0x84c,&b,4);
}
static void start_failed(void)
{
    struct ggx_receipt out,before;memset(&out,0xa3,sizeof(out));before=out;
    enum ggx_result rc=sweet_gpu_start_once(&out);
    if(rc==GGX_OK)fprintf(stderr,"unexpected start success case%u bank%u reads%u\n",cases,out.bank,start_reads);
    CHECK(rc!=GGX_OK&&sweet_gpu_start_state()==GMB_QUARANTINED&&
        sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!h.live);
    CHECK(!memcmp(&out,&before,sizeof(out))&&start_partial==1&&!start_complete);
    unsigned reads=h.reads,stores=h.fw_stores,maps=h.maps,budgets=h.budgets;
    CHECK(sweet_gpu_start_once(&out)==GGX_ALREADY&&!memcmp(&out,&before,sizeof(out))&&reads==h.reads&&stores==h.fw_stores&&maps==h.maps&&budgets==h.budgets);
}
static void gpu_start_cases(void)
{
    unsigned first=cases;start_setup();struct ggx_receipt out;
    CHECK(sweet_gpu_start_once(NULL)==GGX_ARGUMENT&&!ggx_board_lifecycle);
    unsigned before_b=h.budgets,before_o=h.owner_calls,before_p=h.pmap_calls,before_t=h.translations;
    uint8_t *before=malloc(sizeof(smmu));CHECK(before);memcpy(before,smmu,sizeof(smmu));
    CHECK(sweet_gpu_start_once(&out)==GGX_OK&&sweet_gpu_start_state()==GMB_READY&&start_complete==1&&!start_partial&&start_reads==2);
    CHECK(h.maps==8&&h.nc_maps==1&&out.bank==3&&out.asid==4&&out.core_opened&&out.request_retained&&out.writes32==7&&out.writes64==1&&out.status==0x12340000&&out.status3==0x56780000);
    /* Apart from native HUM/DORA and this owned CB's PT/context/TLB registers,
     * every byte including the other contexts and stream routes is preserved. */
    const unsigned offsets[]={0x6800,0x64a0,0xb020,0xb024,0xb034,0xb618,0xb7f0};
    for(unsigned i=0;i<sizeof(smmu);i++){
        bool allowed=false;for(unsigned n=0;n<sizeof(offsets)/sizeof(*offsets);n++)allowed|=i>=offsets[n]&&i<offsets[n]+4;
        if(!allowed)CHECK(before[i]==smmu[i]);
    }
    free(before);unsigned nb=h.budgets-before_b,no=h.owner_calls-before_o,np=h.pmap_calls-before_p,nt=h.translations-before_t;
    unsigned reads=h.reads,stores=h.fw_stores,budgets=h.budgets;CHECK(sweet_gpu_start_once(&out)==GGX_ALREADY&&reads==h.reads&&stores==h.fw_stores&&budgets==h.budgets);
    for(unsigned n=1;n<=nb;n++){start_setup();h.budget_fail=h.budgets+n;start_failed();}
    for(unsigned n=1;n<=no;n++){start_setup();h.owner_fail=h.owner_calls+n;start_failed();}
    for(unsigned n=1;n<=np;n++){start_setup();h.pmap_fail=h.pmap_calls+n;start_failed();start_setup();h.attr_fail=h.pmap_calls+n;start_failed();}
    for(unsigned n=1;n<=nt;n++){start_setup();h.fail_translation=h.translations+n;start_failed();}
    start_setup();uint32_t reserved=1;memcpy(smmu+0x9058,&reserved,4);CHECK(sweet_gpu_start_once(&out)==GGX_OK&&start_complete==1);
    for(unsigned n=0;n<18;n++){
        start_setup();uint32_t v=1;
        if(n==0)h.clock_bad=1;else if(n==1)h.irq_bad=1;else if(n==2){v=2;memcpy(smmu+0x9058,&v,4);}
        else if(n==3)memcpy(reset_page+0x2000,&v,4);else if(n==4)gfw_context.dcvs_valid=0;
        else if(n==5)gfw_context.state=0;else if(n==6)memcpy(smmu+0xb000,&v,4);
        else if(n==7){v=0x8000;memcpy(reset_page+0x2648,&v,4);}else if(n==8){v=1u<<24;memcpy(reset_page+0x2648,&v,4);}
        else if(n==9)h.map_fail=8;else if(n==10)h.misalign=8;else if(n==11)start_allones=1;
        else if(n==12)start_missing=1;else if(n==13)start_sticky=1;else if(n==14)start_busy=1;
        else if(n==15)start_expire=1;else if(n==16)h.core_irq=1;else ggb_secure_result=GPA_TRANSPORT;
        start_failed();if(n<=8||n==12||n==13||n==14||n>=16)CHECK(!start_reads);
        if(n==14)CHECK(!ggx_context.work.request_attempted);
        if(n==15)CHECK(start_reads==1);
    }
    printf("GPU start board: %u live firmware/context/alias/map/lease/owner/TLB/OOB/core/quarantine cases PASS (actual start engine)\n",cases-first);
}
static void sqe_setup(void)
{reset();sqe_mode=1;h.firmware=h.perf_mode=h.bw_mode=h.dcvs_mode=h.gpu_mode=1;}
static void gpu_sqe_cases(void)
{
    unsigned first=cases;struct gmb_firmware_receipt out;
    sqe_setup();CHECK(firmware_run(&out)==GMB_OK&&sqe_calls==3&&sqe_complete==1&&!sqe_partial&&ggb_sqe_loaded);
    CHECK(ggb_sqe_written==8192&&ggb_sqe_checked==8192&&h.gpu_smc_calls==1&&h.engine_calls==1&&h.maps==7&&h.nc_maps==1);
    CHECK(!memcmp(ram+0xa0000,sqe_asset+4,32300));for(unsigned n=32300;n<32768;n++)CHECK(!ram[0xa0000+n]);
    for(unsigned n=0;n<16384;n++)CHECK(ram[n]==0xa5);
    for(unsigned n=GGP_ARENA_END;n<sizeof(ram);n++)CHECK(ram[n]==0xa5);
    unsigned entry=sqe_entry_budget,exit=sqe_exit_budget;CHECK(entry&&exit>entry);
    unsigned calls=sqe_calls,maps=h.maps,stores=h.fw_stores;CHECK(firmware_run(&out)==GMB_ALREADY&&sqe_calls==calls&&h.maps==maps&&h.fw_stores==stores);
    for(unsigned n=1;n<=3;n++){
        sqe_setup();sqe_fail=n;firmware_failed();CHECK(sqe_partial==1&&!sqe_complete&&!ggb_sqe_loaded&&!h.gpu_smc_calls&&!h.engine_calls);
        CHECK(n==1?!h.maps:h.maps==2);CHECK(n<3?!ggb_sqe_written:ggb_sqe_written==8192);
    }
    const unsigned corrupt[]={1,4096,8076,8192};
    for(unsigned n=0;n<sizeof(corrupt)/sizeof(*corrupt);n++){
        sqe_setup();sqe_corrupt=corrupt[n];firmware_failed();
        CHECK(!sqe_corrupt&&!ggb_sqe_loaded&&ggb_sqe_written==8192&&ggb_sqe_checked==corrupt[n]-1&&!h.gpu_smc_calls&&!h.engine_calls&&!sqe_complete);
    }
    for(unsigned n=1;n<=3;n++){
        sqe_setup();sqe_drift=n;firmware_failed();CHECK(ggb_sqe_written==8192&&ggb_sqe_checked==8192&&!ggb_sqe_loaded&&!h.gpu_smc_calls&&!h.engine_calls);
    }
    for(unsigned n=entry+1;n<=exit+2;n++){
        sqe_setup();h.budget_fail=n;firmware_failed();CHECK(!sqe_complete&&!h.gpu_smc_calls&&!h.engine_calls);
    }
    sqe_setup();start_mode=1;CHECK(firmware_run(&out)==GMB_OK&&ggb_sqe_loaded);struct ggx_receipt core;
    CHECK(sweet_gpu_start_once(&core)==GGX_OK&&core.request_retained&&start_reads==2&&sqe_complete==1);
    sqe_setup();start_mode=1;CHECK(firmware_run(&out)==GMB_OK);ggb_sqe_loaded=0;start_failed();
    printf("SQE cold board: %u header-skip/payload/padding/guard/digest-identity/once-state and combined live-start cases PASS (typed SHA view seam)\n",cases-first);
}
static void core_setup(void)
{
    sqe_setup();core_mode=start_mode=1;
    struct gmb_firmware_receipt fw;CHECK(firmware_run(&fw)==GMB_OK&&ggb_sqe_loaded&&sqe_calls==3);
    core_active=1;uint32_t v=0xf00d1234;memcpy(core_page+4*0x841,&v,4);
}
static void core_failed(void)
{
    struct ggc_receipt out,old;memset(&out,0xa3,sizeof(out));old=out;
    CHECK(sweet_gpu_core_once(&out)!=GGC_OK&&!memcmp(&out,&old,sizeof(out))&&core_partial==1&&!core_complete&&!core_rgl_lines);
    CHECK(sweet_gpu_core_state()==GMB_QUARANTINED&&sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!h.live);
    CHECK(core_guard_lines==1&&core_memory_lines==1);
    unsigned reads=h.reads,stores=h.fw_stores,maps=h.maps,budgets=h.budgets;
    CHECK(sweet_gpu_core_once(&out)==GGC_ALREADY&&!memcmp(&out,&old,sizeof(out))&&h.reads==reads&&h.fw_stores==stores&&h.maps==maps&&h.budgets==budgets);
}
static void gpu_core_cases(void)
{
    unsigned first=cases;
    for(unsigned skip=0;skip<2;skip++){
        core_setup();if(skip){uint32_t v=0x8aa8aa82;memcpy(core_page+4*0xae,&v,4);}
        uint8_t *saved=malloc(sizeof(ram));CHECK(saved);memcpy(saved,ram,sizeof(ram));
        struct ggc_receipt out;CHECK(sweet_gpu_core_once(&out)==GGC_OK&&sweet_gpu_core_state()==GMB_READY&&sweet_gpu_start_state()==GMB_READY&&h.live&&!h.quarantine);
        CHECK(h.maps==14&&h.nc_maps==1&&ggc_created==6&&ggc_maps_ready&&start_complete==1&&start_reads==2&&sqe_calls==4);
        CHECK(out.writes==(skip?80u:146u)&&out.reads==(skip?69u:71u)&&out.hwcg_skipped==skip&&out.configured&&out.requests_retained);
        CHECK(core_stores==out.writes&&core_reads==out.reads&&core_memstores==133&&out.mem_written==133&&out.mem_compared==1024&&core_complete==1&&core_rgl_lines==66);
        CHECK(ggc_context.zero_checked==1024&&core_ram_reads==2048&&core_guard_lines==1&&core_memory_lines==1&&ggc_guard_diagnostic.reason==GCD_NONE);
        uint32_t v;memcpy(&v,core_extra[2]+0x3808,4);CHECK(v==2);memcpy(&v,core_page+0x3804,4);CHECK(v==0x200000);
        memcpy(&v,ram+0xb4010,4);CHECK(v==0x841);memcpy(&v,ram+0xb4014,4);CHECK(v==0xf00d1234);
        memcpy(saved+0xb4000,ggc_context.reglist,sizeof(ggc_context.reglist));CHECK(!memcmp(saved,ram,sizeof(ram)));free(saved);
        unsigned budgets=h.budgets,maps=h.maps,stores=h.fw_stores;CHECK(sweet_gpu_core_once(&out)==GGC_ALREADY&&budgets==h.budgets&&maps==h.maps&&stores==h.fw_stores);
    }
    for(unsigned phase=GGC_BUS;phase<=GGC_FINAL;phase++)for(unsigned kind=1;kind<=10;kind++){
        if(kind==10&&phase<GGC_MAP)continue;
        core_setup();core_fail_phase=phase;core_fail_kind=kind;core_failed();CHECK(core_fired);
        const enum ggc_guard_reason expected[]={GCD_NONE,GCD_CLOCK,GCD_IRQ,GCD_FAULT,GCD_CONTEXT,GCD_CONTEXT,GCD_NC,GCD_SQE,GCD_RESET,GCD_TOTAL_TIME,GCD_GPU_CONTEXT};
        CHECK(ggc_guard_diagnostic.reason==expected[kind]&&ggc_guard_diagnostic.phase==phase);
    }
    for(unsigned n=9;n<=14;n++){
        core_setup();h.map_fail=n;core_failed();CHECK(h.maps==n&&core_stores==1);
        core_setup();h.misalign=n;core_failed();CHECK(h.maps==n&&core_stores==1);
        core_setup();core_overflow=n;core_failed();CHECK(h.maps==n&&core_stores==1);
        core_setup();core_phys_fail=n;core_failed();CHECK(h.maps==n&&core_stores==1);
    }
    for(unsigned n=1;n<=6;n++){
        core_setup();core_dev_bad=n;core_failed();CHECK(h.maps==n+7&&core_stores==1);
        core_setup();core_dev_valid=n;core_failed();CHECK(h.maps==n+7&&core_stores==1);
    }
    const unsigned stops[]={1,2,13,17,18,81,82,83,84,113,114,146};
    for(unsigned n=0;n<sizeof(stops)/sizeof(*stops);n++){
        core_setup();core_stop_after=stops[n];core_failed();CHECK(core_stores==stops[n]);
        core_setup();core_expire=stops[n];core_failed();CHECK(core_stores==stops[n]);
    }
    const unsigned words[]={1,5,136,1024};
    for(unsigned n=0;n<sizeof(words)/sizeof(*words);n++){core_setup();core_corrupt_word=words[n];core_failed();CHECK(!core_corrupt_word&&core_memstores==133);}
    /* Change live conditions just inside/on/outside each kind of NC batch.
     * Stop at its next guard, before another batch or header publication. */
    const unsigned ram_stops[]={1,64,65,1024,1025,1088,1089,2048};
    for(unsigned expire=0;expire<2;expire++)for(unsigned n=0;n<sizeof(ram_stops)/sizeof(*ram_stops);n++){
        core_setup();core_ram_stop=ram_stops[n];core_batch_expire=expire;core_failed();
        CHECK(core_ram_reads==((core_ram_stop+63)/64)*64&&core_memstores==(core_ram_stop<=1024?0u:133u));
        CHECK(ggc_context.zero_checked==(core_ram_stop<=1024?core_ram_reads:1024u));
        CHECK(ggc_guard_diagnostic.phase==GGC_REGLIST&&ggc_guard_diagnostic.reason==(expire?GCD_PHASE_TIME:GCD_CLOCK));
    }
    const unsigned mem_stops[]={1,64,65,128,129,132,133};
    for(unsigned expire=0;expire<2;expire++)for(unsigned n=0;n<sizeof(mem_stops)/sizeof(*mem_stops);n++){
        core_setup();core_mem_stop=mem_stops[n];core_batch_expire=expire;core_failed();
        unsigned expected=core_mem_stop<=64?64u:core_mem_stop<=128?128u:core_mem_stop<=132?132u:133u;
        CHECK(core_memstores==expected&&core_ram_reads==1024&&ggc_context.zero_checked==1024);
        CHECK(ggc_guard_diagnostic.phase==GGC_REGLIST&&ggc_guard_diagnostic.reason==(expire?GCD_PHASE_TIME:GCD_CLOCK));
    }
    core_setup();sqe_fail=4;core_failed();CHECK(core_stores==0&&h.maps==7);
    core_setup();ggb_sqe_loaded=0;core_failed();CHECK(!core_stores&&h.maps==7);
    core_setup();uint32_t stale=1u<<24;memcpy(reset_page+0x2648,&stale,4);core_failed();CHECK(!core_stores&&h.maps==7);
    core_setup();start_missing=1;core_failed();CHECK(core_stores==1&&start_partial==1&&h.quarantine==1);
    core_setup();core_attr_bad=1;core_failed();CHECK(!core_stores&&h.maps==7);
    core_setup();CHECK(sweet_gpu_core_once(NULL)==GGC_ARGUMENT&&sweet_gpu_core_state()==GMB_IDLE&&!core_stores);
    printf("GPU core board: %u retained-map/phase/owner/fault/deadline/SQE/NC/parent/once-state cases PASS (actual core+MMU engines)\n",cases-first);
}
static void cp_setup(unsigned skip)
{
    core_setup();cp_mode=1;
    if(skip){uint32_t v=0x8aa8aa82;memcpy(core_page+4*0xae,&v,4);}
    struct ggc_receipt core;CHECK(sweet_gpu_core_once(&core)==GGC_OK&&core_complete==1&&sqe_calls==4);
    /* Nonzero private memory makes a dropped zero store observable. */
    memset(ram+0xa8000,0x5a,32768);memset(ram+0xb0000,0xa5,4096);
    cp_active=1;
}
static void cp_failed(void)
{
    struct ggq_receipt out,old;memset(&out,0xa3,sizeof(out));old=out;
    CHECK(sweet_gpu_cp_once(&out)!=GGQ_OK&&!memcmp(&out,&old,sizeof(out))&&cp_partial==1&&!cp_complete&&!cp_words&&cp_guard_lines==1);
    CHECK(sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&sweet_gpu_start_state()==GMB_QUARANTINED&&sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&h.quarantine==1&&!h.live);
    unsigned reads=h.reads,stores=h.fw_stores,maps=h.maps,budgets=h.budgets;
    CHECK(sweet_gpu_cp_once(&out)==GGQ_ALREADY&&!memcmp(&out,&old,sizeof(out))&&h.reads==reads&&h.fw_stores==stores&&h.maps==maps&&h.budgets==budgets);
}
static void gpu_cp_cases(void)
{
    unsigned first=cases;
    for(unsigned scenario=0;scenario<6;scenario++){
        cp_setup(scenario==5);cp_drop=scenario==1?1:scenario==2?100:scenario==3?199:0;
        cp_shadow_delay=cp_busy_delay=scenario==1?2:0;cp_wrap=scenario==4;
        uint8_t *saved=malloc(sizeof(ram));CHECK(saved);memcpy(saved,ram,sizeof(ram));
        struct ggq_receipt out;CHECK(sweet_gpu_cp_once(&out)==GGQ_OK&&sweet_gpu_cp_state()==GMB_READY);
        CHECK(h.live&&!h.quarantine&&h.maps==14&&h.nc_maps==1&&cp_complete==1&&cp_words==15&&cp_guard_lines==1&&sqe_calls==5);
        CHECK(out.writes==11+cp_drop&&cp_stores==out.writes&&cp_submits==cp_drop+1&&out.fence_checks==cp_drop+1&&out.fence_slow==(cp_drop>=100));
        CHECK(out.complete==1&&out.requests_retained==1&&out.rptr==15&&!(out.busy&(1u<<23))&&!cp_keep&&cp_accepted);
        CHECK(cp_memstores==9231&&cp_memreads==17408+out.idle_polls&&out.ring_checked==8192&&out.scratch_checked==1024&&out.commands_checked==8192);
        CHECK(ggq_guard_diagnostic.reason==GQD_NONE&&ggq_guard_diagnostic.phase==GGQ_FINAL&&ggq_guard_diagnostic.now<ggq_deadline&&ggq_guard_diagnostic.now<ggq_phase_deadline);
        CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60));
        for(unsigned i=15;i<8192;i++){uint32_t v;memcpy(&v,ram+0xa8000+4*i,4);CHECK(v==0xaaaaaaaa);}
        uint32_t v;memcpy(&v,ram+0xb0000,4);CHECK(v==15);
        for(unsigned i=1;i<1024;i++){memcpy(&v,ram+0xb0000+4*i,4);CHECK(v==0);}
        memcpy(saved+0xa8000,ram+0xa8000,32768);memcpy(saved+0xb0000,ram+0xb0000,4096);CHECK(!memcmp(saved,ram,sizeof(ram)));free(saved);
        unsigned reads=h.reads,stores=h.fw_stores,maps=h.maps,budgets=h.budgets;
        CHECK(sweet_gpu_cp_once(&out)==GGQ_ALREADY&&h.reads==reads&&h.fw_stores==stores&&h.maps==maps&&h.budgets==budgets);
    }
    const enum ggq_guard_reason reasons[]={GQD_NONE,GQD_CLOCK,GQD_IRQ,GQD_FAULT,GQD_CONTEXT,GQD_CONTEXT,
        GQD_NC,GQD_SQE,GQD_RESET,GQD_TOTAL_TIME,GQD_GPU_CONTEXT,GQD_PHASE_TIME,GQD_CORE,GQD_DEVICE,
        GQD_GPU_FAULT,GQD_GPU_FAULT,GQD_ACK,GQD_WDT,GQD_FIRMWARE,GQD_LIFECYCLE,GQD_APERTURE};
    for(unsigned phase=GGQ_CAPTURE;phase<=GGQ_FINAL;phase++)for(unsigned kind=1;kind<=20;kind++){
        cp_setup(0);cp_fail_phase=phase;cp_fail_kind=kind;cp_failed();
        CHECK(cp_fired&&ggq_guard_diagnostic.reason==reasons[kind]&&ggq_guard_diagnostic.phase==phase);
    }
    for(unsigned n=1;n<=11;n++){
        cp_setup(0);cp_stop_store=n;cp_failed();CHECK(cp_stores==n&&ggq_guard_diagnostic.reason==GQD_CLOCK);
        cp_setup(0);cp_expire_store=n;cp_failed();CHECK(cp_stores==n&&ggq_guard_diagnostic.reason==GQD_PHASE_TIME);
    }
    const unsigned memory_stops[]={1,64,65,8192,8193,9216,9217,9231};
    for(unsigned n=0;n<sizeof(memory_stops)/sizeof(*memory_stops);n++){
        unsigned stop=memory_stops[n],end=stop<=9216?((stop+63)/64)*64:9231;
        cp_setup(0);cp_stop_mem=stop;cp_failed();CHECK(cp_memstores==end&&ggq_guard_diagnostic.reason==GQD_CLOCK&&!cp_submits);
        cp_setup(0);cp_expire_mem=stop;cp_failed();CHECK(cp_memstores==end&&ggq_guard_diagnostic.reason==GQD_PHASE_TIME&&!cp_submits);
        cp_setup(0);cp_drop_write=stop;cp_failed();CHECK(ggq_result==GGQ_MEMORY_ERROR&&!cp_submits);
    }
    const unsigned reads[]={1,8192,8193,9216,9217,17408};
    for(unsigned n=0;n<sizeof(reads)/sizeof(*reads);n++){cp_setup(0);cp_corrupt_read=reads[n];cp_failed();CHECK(ggq_result==GGQ_MEMORY_ERROR&&!cp_submits);}
    for(unsigned page=1;page<=3;page++){
        cp_setup(0);cp_nc_page=page;cp_nc_bad=1;cp_failed();CHECK(!cp_memstores&&ggq_guard_diagnostic.reason==GQD_NC);
        cp_setup(0);cp_nc_page=page;cp_nc_bad=2;cp_failed();CHECK(!cp_memstores&&ggq_guard_diagnostic.reason==GQD_NC);
        cp_setup(0);cp_physical_bad=page;cp_failed();CHECK(!cp_memstores&&ggq_guard_diagnostic.reason==GQD_NC);
    }
    cp_setup(0);cp_drop=200;cp_failed();CHECK(ggq_result==GGQ_TIMEOUT&&cp_submits==201&&cp_fences==200&&cp_keep&&!cp_shadow_reads&&!ggq_context.work.keepalive_clear_attempted);
    cp_setup(0);cp_shadow_delay=UINT32_MAX;cp_time_step=1000000;cp_failed();CHECK(cp_shadow_reads>0&&ggq_guard_diagnostic.reason==GQD_PHASE_TIME);
    cp_setup(0);cp_busy_delay=UINT32_MAX;cp_time_step=1000000;cp_failed();CHECK(cp_busy_reads>0&&ggq_guard_diagnostic.reason==GQD_PHASE_TIME);
    cp_setup(0);cp_bad_rptr=8192;cp_failed();CHECK(ggq_result==GGQ_MEMORY_ERROR&&cp_shadow_reads==1);
    cp_setup(0);cp_bad_busy=1;cp_failed();CHECK(ggq_result==GGQ_FAULT&&cp_shadow_reads==1);
    cp_setup(0);h.budget_fail=h.budgets+1;cp_failed();CHECK(ggq_guard_diagnostic.reason==GQD_ENTRY_WDT&&!cp_memstores);
    cp_setup(0);sqe_fail=5;cp_failed();CHECK(ggq_guard_diagnostic.reason==GQD_SQE_ASSET&&!cp_memstores&&sqe_calls==5);
    cp_setup(0);ggc_work.mem_compared=1023;cp_failed();CHECK(ggq_result==GGQ_ARGUMENT&&!cp_memstores);
    cp_setup(0);uint32_t v=1;memcpy(core_page+4*0x806,&v,4);cp_failed();CHECK(ggq_result==GGQ_DIRTY_STATE&&!cp_memstores);
    cp_setup(0);ggc_alias[0]++;cp_failed();CHECK(ggq_guard_diagnostic.reason==GQD_DEVICE&&!cp_memstores);
    cp_setup(0);CHECK(sweet_gpu_cp_once(NULL)==GGQ_ARGUMENT&&sweet_gpu_cp_state()==GMB_IDLE&&!cp_memstores);
    printf("GPU CP board: %u actual CP/core/MMU/native-fence/NC/owner/phase/fault/deadline/output/once cases PASS\n",cases-first);
}

enum psz_state sweet_pas_zap_owner_state(void){return (enum psz_state)z.owner_state;}
bool sweet_pas_zap_owner_live(enum gpz_phase phase,uint64_t pa)
{
    ++z.owner_checks;
    return z.enabled&&pa==owner&&sweet_gpu_zap_owner_phase(phase,pa)&&
        z.owner_checks!=z.owner_fail_at&&z.owner_state!=PSZ_FAILED;
}
bool sweet_pas_zap_owner_action(enum gpz_owner_action action)
{
    CHECK(z.enabled&&sweet_gpu_zap_owner_action_allowed(action,owner));++z.owner_actions;
    if(z.owner_actions==z.owner_action_fail)return false;
    if(action==GPZO_SEAL){CHECK(z.owner_state==PSZ_IDLE);z.owner_state=PSZ_SEALED;}
    else if(action==GPZO_INIT_ENTER){CHECK(z.owner_state==PSZ_SEALED);z.owner_state=PSZ_INIT_ENTERED;}
    else if(action==GPZO_INIT_ACCEPT){CHECK(z.owner_state==PSZ_INIT_ENTERED);z.owner_state=PSZ_INIT_DONE;}
    else if(action==GPZO_MEM_ACCEPT){CHECK(z.owner_state==PSZ_INIT_DONE);z.owner_state=PSZ_MEM_DONE;}
    else {CHECK(action==GPZO_AUTH_ACCEPT&&z.owner_state==PSZ_COPIED&&z.auth_done);z.owner_state=PSZ_AUTH_DONE;}
    return true;
}
void sweet_pas_zap_quarantine(void){z.owner_state=PSZ_FAILED;}
bool sweet_pas_zap_copy(struct gpz_copy *out)
{
    CHECK(z.enabled&&z.owner_state==PSZ_MEM_DONE&&sweet_gpu_zap_owner_phase(GPZ_COPY,owner));++z.copies;
    z.owner_state=PSZ_COPYING;*out=(struct gpz_copy){0};
    for(unsigned base=0;base<1984;base+=64){
        ++z.copy_guards;if(z.copy_guards==z.copy_expire)h.now=gpzb_context.phase_end;
        if(!sweet_gpu_zap_copy_live())return false;
        for(unsigned i=base;i<base+64;i++){ram[i]=(uint8_t)(i*31+5);++out->written;}
        ++z.copy_guards;if(z.copy_guards==z.copy_expire)h.now=gpzb_context.phase_end;
        if(!sweet_gpu_zap_copy_live())return false;
        if(z.copy_fail)return false;
    }
    out->checked=z.bad_copy?1983:1984;z.owner_state=PSZ_COPIED;return true;
}
static void host_zap_smc(struct gpa_registers *r)
{
    unsigned phase=gpzb_context.phase;CHECK(phase==GPZ_INIT||phase==GPZ_MEM||phase==GPZ_AUTH);
    unsigned id=phase==GPZ_INIT?0:phase==GPZ_MEM?1:2,n=z.smc_calls[id]++;
    CHECK(sweet_gpu_zap_state()==GMB_RUNNING&&h.live&&!h.quarantine);
    CHECK(z.owner_state==(id==0?PSZ_INIT_ENTERED:id==1?PSZ_INIT_DONE:PSZ_COPIED));
    CHECK(!sweet_gpu_zap_owner_action_allowed(id==0?GPZO_INIT_ACCEPT:id==1?GPZO_MEM_ACCEPT:GPZO_AUTH_ACCEPT,owner));
    if(z.interrupted){CHECK(!memcmp(r->x,z.last.x,sizeof(r->x)));}
    else {const uint64_t expected[]={id==0?0x42000201u:id==1?0x42000202u:0x42000205u,id==0?0x82u:id==1?3u:1u,13,id==2?0:owner,id==1?4096u:0,0,0};CHECK(!memcmp(r->x,expected,sizeof(expected)));}
    for(unsigned i=0;i<7;i++)r->x[i]=UINT64_C(0x1234567890)+i+n*16;
    if(n<z.cont[id]){r->x[0]=1;z.interrupted=1;}
    else if(n-z.cont[id]<z.busy[id]){r->x[0]=UINT64_C(0xfffffffffffffff4);z.interrupted=0;}
    else {r->x[0]=r->x[1]=0;z.interrupted=0;
        if(z.bad_smc_phase==phase){if(z.bad_service)r->x[1]=UINT64_C(0x100000000);else r->x[0]=UINT64_C(0x100000000);}
        if(id==2&&!r->x[0]&&!r->x[1])z.auth_done=1;
    }
    z.last=*r;
}
static void host_zap_budget(void)
{
    if(!z.enabled||gpzb_context.state!=1||!z.fault_kind||z.fired||gpzb_context.phase!=z.fault_phase)return;
    z.fired=1;uint32_t v=1;
    if(z.fault_kind==1)h.clock_bad=1;
    else if(z.fault_kind==2)h.irq_bad=1;
    else if(z.fault_kind==3)memcpy(reset_page+0x2000,&v,4);
    else if(z.fault_kind==4)memcpy(smmu+0x48,&v,4);
    else if(z.fault_kind==5)ggq_work.complete=0;
    else if(z.fault_kind==6)gfw_context.dcvs_return=1;
    else if(z.fault_kind==7){cp_nc_page=3;cp_nc_bad=1;}
    else if(z.fault_kind==8)ggc_maps_ready=0;
    else if(z.fault_kind==9){uint64_t t=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&t,8);}
    else if(z.fault_kind==10)ggx_work.ttbr0^=4096;
    else if(z.fault_kind==11)h.now=gpzb_context.phase_end;
    else CHECK(false);
}
static void zap_setup(void)
{
    cp_setup(0);struct ggq_receipt cp;CHECK(sweet_gpu_cp_once(&cp)==GGQ_OK);z.enabled=1;z.flag=1;
    CHECK(sweet_gpu_zap_state()==GMB_IDLE&&z.owner_state==PSZ_IDLE);
}
static void zap_failed(void)
{
    struct gpz_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
    CHECK(sweet_gpu_zap_once(&out)!=GPZ_OK&&!memcmp(&out,&saved,sizeof(out))&&z.partial==1&&!z.complete);
    CHECK(sweet_gpu_zap_state()==GMB_QUARANTINED&&sweet_gpu_cp_state()==GMB_QUARANTINED&&
        sweet_gpu_core_state()==GMB_QUARANTINED&&sweet_gpu_start_state()==GMB_QUARANTINED&&
        sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&
        z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
    unsigned calls=z.smc_calls[0]+z.smc_calls[1]+z.smc_calls[2],checks=z.owner_checks,budgets=h.budgets;
    CHECK(sweet_gpu_zap_once(&out)==GPZ_ALREADY&&!memcmp(&out,&saved,sizeof(out))&&z.smc_calls[0]+z.smc_calls[1]+z.smc_calls[2]==calls&&checks==z.owner_checks&&budgets==h.budgets);
}
static void gpu_zap_cases(void)
{
    unsigned first=cases,owner_checks=0,copy_guards=0;
    for(unsigned mode=0;mode<4;mode++){
        zap_setup();if(mode==1)for(unsigned i=0;i<3;i++)z.cont[i]=2;
        if(mode==2)for(unsigned i=0;i<3;i++)z.busy[i]=1;
        z.missing_init=mode==3;
        unsigned maps=h.maps,nc_maps=h.nc_maps;struct gpz_receipt out;
        CHECK(sweet_gpu_zap_once(&out)==GPZ_OK&&sweet_gpu_zap_state()==GMB_READY&&z.complete==1&&!z.partial&&z.owner_state==PSZ_AUTH_DONE);
        CHECK(out.complete==1&&out.copy.written==1984&&out.copy.checked==1984&&out.owner_pa==owner&&h.maps==maps&&h.nc_maps==nc_maps&&h.live&&!h.quarantine);
        CHECK(z.owner_actions==5&&z.copies==1&&z.auth_done&&gpzb_diagnostic.reason==PZB_NONE&&gpzb_diagnostic.scope==GPZ_LATE);
        if(!mode){owner_checks=z.owner_checks;copy_guards=z.copy_guards;}
    }
    for(unsigned n=1;n<=owner_checks;n++){zap_setup();z.owner_fail_at=n;zap_failed();}
    for(unsigned n=1;n<=5;n++){zap_setup();z.owner_action_fail=n;zap_failed();}
    for(unsigned phase=GPZ_SEAL;phase<=GPZ_AUTH;phase++)for(unsigned kind=1;kind<=11;kind++){
        zap_setup();z.fault_phase=phase;z.fault_kind=kind;zap_failed();CHECK(z.fired);
    }
    for(unsigned n=1;n<=copy_guards;n++){
        zap_setup();z.copy_expire=n;zap_failed();CHECK(z.copy_guards==n&&gpzb_diagnostic.reason==PZB_TIME&&!z.smc_calls[2]);
    }
    for(unsigned id=0;id<3;id++)for(unsigned service=0;service<2;service++){
        zap_setup();z.bad_smc_phase=id==0?GPZ_INIT:id==1?GPZ_MEM:GPZ_AUTH;z.bad_service=service;zap_failed();
        for(unsigned j=id+1;j<3;j++)CHECK(!z.smc_calls[j]);
    }
    zap_setup();z.copy_fail=1;zap_failed();CHECK(!z.smc_calls[2]);
    zap_setup();z.bad_copy=1;zap_failed();CHECK(!z.smc_calls[2]);
    zap_setup();z.cont[2]=9;zap_failed();CHECK(z.smc_calls[2]==9&&gpzb_context.work.transaction[2].continuations==8);
    zap_setup();z.busy[2]=68;zap_failed();CHECK(z.smc_calls[2]==68);
    for(unsigned n=2;n<=12;n++){zap_setup();z.bad_flag=n;zap_failed();CHECK(!z.smc_calls[0]);}
    for(unsigned n=1;n<=9;n++){zap_setup();z.bad_off=n;zap_failed();CHECK(!z.smc_calls[0]);}
    zap_setup();z.flag=0;struct gpz_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
    CHECK(sweet_gpu_zap_once(&out)==GPZ_ARGUMENT&&!memcmp(&out,&saved,sizeof(out))&&sweet_gpu_zap_state()==GMB_IDLE&&!z.smc_calls[0]);
    printf("GPU signed ZAP board: %u actual CP+ZAP/owner-seam/lifecycle/live-CPU-late/fault/copy/deadline/once cases PASS; no hardware authentication proof\n",cases-first);
}

/* New stage uses actual CP+ZAP+GGU engines and exact private receipts. */
static bool host_unsecure_active(void)
{
 return u.active&&z.auth_done&&(z.flag==2||z.flag==3||z.flag==4)&&sweet_gpu_unsecure_state()==GMB_RUNNING&&
  ((ggub_context.state==1&&ggub_context.phase>=GGU_SEAL&&ggub_context.phase<=GGU_FINAL)||
   (ggub_context.state==2&&ggub_context.phase==GGU_DONE&&ggub_phase==GGU_FINAL));
}
bool sweet_pas_zap_owner_authenticated(uint64_t pa)
{++u.owner_checks;return (u.active||w.active||ibf.active)&&z.enabled&&z.auth_done&&pa==owner&&z.owner_state==PSZ_AUTH_DONE&&!u.owner_bad&&!w.owner_bad&&!ibf.owner_bad;}
static void host_unsecure_budget(void)
{
 if(!u.active)return;++u.budgets;
 if(u.budgets==u.budget_fail)h.live=false;
 if(!u.kind||u.fired||ggub_context.state!=1||ggub_context.phase!=u.phase)return;
 u.fired=1;uint32_t v=1;
 switch(u.kind){
 case 1:h.clock_bad=1;break;case 2:h.irq_bad=1;break;case 3:memcpy(reset_page+0x2000,&v,4);break;
 case 4:memcpy(smmu+0x48,&v,4);break;case 5:v=1u<<9;memcpy(core_page+4*0x201,&v,4);break;
 case 6:memcpy(core_page+4*0x823,&v,4);break;case 7:h.now=ggub_deadline;break;case 8:h.now=ggub_phase_end;break;
 case 9:u.owner_bad=1;break;case 10:gpzb_work.copy.checked=1983;break;case 11:gfw_context.dcvs_return=1;break;
 case 12:core_attr_bad=1;break;case 13:ggc_alias[0]++;break;case 14:h.context=1;break;
 case 15:{uint64_t t=ggb_smmu.ttbr0^4096;memcpy(smmu+0x8000+4096*ggb_smmu.bank+0x20,&t,8);break;}
 case 16:v=1u<<24;memcpy(reset_page+0x2648,&v,4);break;case 17:ggc_work.mem_compared=1023;break;
 case 18:h.now=ggub_last_now?ggub_last_now-1:UINT64_MAX;break;
 case 19:cp_nc_bad=2;cp_nc_page=1;break;case 20:cp_nc_bad=1;cp_nc_page=3;break;case 21:cp_dev_bad=1;break;default:CHECK(false);
 }
}
static void host_unsecure_read(vm_offset_t address,uint32_t *value)
{
 if(!u.active)return;CHECK(host_unsecure_active());++u.reads;
 if(address==(uintptr_t)fw_page[0]+0x2c4c){*value=u.fences++<u.drop?3:2;if(!(*value&1))u.accepted=1;}
 if(address==(uintptr_t)fw_page[0]+0x2c30){*value=ggub_context.phase==GGU_WAIT&&u.busy_reads++<u.busy_delay?0x71800000:0x71000000;}
 if(address==(uintptr_t)reset_page+0x2220||address==(uintptr_t)reset_page+0x2224){
  unsigned n=u.counter_reads++;*value=!u.wrap?(address==(uintptr_t)reset_page+0x2224?1u:0x12345678u):
   n==0?1u:n==1?0xfffffff0u:n==2?2u:n==3?0x10u:address==(uintptr_t)reset_page+0x2224?2u:0x20u;
 }
 if(address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb1000){
  ++u.memreads;
  if(ggub_context.phase==GGU_WAIT){CHECK(address==(uintptr_t)ram+0xb0000&&u.accepted&&u.submits&&!u.kept);
   if(u.shadow_reads++>=u.shadow_delay){*value=u.bad_shadow?u.bad_shadow:20;memcpy(ram+0xb0000,value,4);}}
  if(u.corrupt_read==u.memreads)*value^=1;
 }
}
static bool host_unsecure_store(vm_offset_t address,uint32_t value)
{
 if(!u.active)return false;CHECK(host_unsecure_active());++u.stores;
 if(address>=(uintptr_t)ram+0xa8000&&address<(uintptr_t)ram+0xb1000){
  CHECK(ggub_context.phase==GGU_COMMANDS&&u.memstores<5&&address==(uintptr_t)ram+0xa8000+60+4*u.memstores&&value==ggub_context.command.word[u.memstores]);
  ++u.memstores;
  if(u.memstores!=u.drop_write)memcpy((void *)address,&value,4);
 }else{
  uint32_t reg=host_core_reg(address);CHECK(ggub_context.phase==GGU_SUBMIT&&ggu_register_allowed(reg,true)&&u.memstores==5&&ggub_context.work.commands_checked==5);
  if(reg==0x807){CHECK(value==20&&u.kept);++u.submits;}else{CHECK(value<=1);u.kept=value;}
  memcpy((void *)address,&value,4);
 }
 if(u.stores==u.stop_store)h.clock_bad=1;
 if(u.stores==u.expire_store)h.now=ggub_phase_end;
 return true;
}
static void unsecure_setup(void)
{
 zap_setup();z.flag=2;struct gpz_receipt signed_load;CHECK(sweet_gpu_zap_once(&signed_load)==GPZ_OK);
 cp_active=0;u.active=1;CHECK(!mprotect(ram,16384,PROT_NONE));
 CHECK(sweet_gpu_unsecure_state()==GMB_IDLE&&ggub_context.state==0);
}
static void unsecure_failed(void)
{
 struct ggu_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 CHECK(sweet_gpu_unsecure_once(&out)!=GGU_OK&&!memcmp(&out,&saved,sizeof(out))&&u.partial==1&&!u.complete);
 CHECK(sweet_gpu_unsecure_state()==GMB_QUARANTINED&&sweet_gpu_zap_state()==GMB_QUARANTINED&&
  sweet_gpu_cp_state()==GMB_QUARANTINED&&sweet_gpu_core_state()==GMB_QUARANTINED&&sweet_gpu_start_state()==GMB_QUARANTINED&&
  sweet_gmu_firmware_state()==GMB_QUARANTINED&&sweet_gmu_board_state()==GMB_QUARANTINED&&z.owner_state==PSZ_FAILED&&!h.live&&h.quarantine==1);
 unsigned reads=u.reads,stores=u.stores,budgets=u.budgets;
 CHECK(sweet_gpu_unsecure_once(&out)==GGU_ALREADY&&!memcmp(&out,&saved,sizeof(out))&&reads==u.reads&&stores==u.stores&&budgets==u.budgets);
}
static void unsecure_good(void)
{
 struct ggu_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;
 unsigned maps=h.maps,nc=h.nc_maps,owner_calls=h.owner_calls;
 CHECK(sweet_gpu_unsecure_once(&out)==GGU_OK&&sweet_gpu_unsecure_state()==GMB_READY&&u.complete==1&&!u.partial&&z.owner_state==PSZ_AUTH_DONE);
 CHECK(out.complete==1&&out.sealed==1&&out.commands_written==5&&out.commands_checked==5&&out.prefix_checked==15&&out.clean_checked==5&&out.requests_retained==1&&out.rptr==20);
 CHECK(out.initial_wptr==15&&out.initial_shadow==15&&out.writes==u.drop+3&&out.fence_checks==u.drop+1&&u.memstores==5&&u.submits==u.drop+1&&!u.kept);
 CHECK(h.maps==maps&&h.nc_maps==nc&&h.owner_calls==owner_calls&&h.live&&!h.quarantine&&ggub_diagnostic.reason==UGD_NONE);
 CHECK(!memcmp(ram+0xa8000,ggq_context.command.word,60));for(unsigned i=20;i<8192;i++)CHECK(*(uint32_t *)(void *)(ram+0xa8000+4*i)==0xaaaaaaaa);
 unsigned reads=u.reads,stores=u.stores,budgets=u.budgets;
 CHECK(sweet_gpu_unsecure_once(&out)==GGU_ALREADY&&reads==u.reads&&stores==u.stores&&budgets==u.budgets);
 (void)saved;
}
static void gpu_unsecure_cases(void)
{
 unsigned first=cases;
 for(unsigned scenario=0;scenario<5;scenario++){
  unsecure_setup();u.drop=scenario==1?1:scenario==2?100:scenario==3?199:0;u.wrap=scenario==4;
  if(scenario==1)u.shadow_delay=u.busy_delay=2;unsecure_good();
 }
 for(unsigned phase=GGU_SEAL;phase<=GGU_FINAL;phase++)for(unsigned kind=1;kind<=21;kind++){
  unsecure_setup();u.phase=phase;u.kind=kind;unsecure_failed();CHECK(u.fired);
 }
 for(unsigned n=1;n<=8;n++){unsecure_setup();u.stop_store=n;unsecure_failed();CHECK(u.stores==n);}
 for(unsigned n=1;n<=8;n++){unsecure_setup();u.expire_store=n;unsecure_failed();CHECK(u.stores==n);}
 for(unsigned n=1;n<=5;n++){unsecure_setup();u.drop_write=n;unsecure_failed();CHECK(!u.submits);}
 for(unsigned n=1;n<=26;n++){unsecure_setup();u.corrupt_read=n;unsecure_failed();CHECK(!u.submits);}
 for(unsigned n=0;n<20;n++){
  unsecure_setup();uint32_t *p=(uint32_t *)(void *)(ram+0xa8000+4*n);*p^=1;unsecure_failed();CHECK(!u.stores);
 }
 for(unsigned n=0;n<12;n++){
  unsecure_setup();
  if(n==0)gpzb_lifecycle=GMB_RUNNING;else if(n==1)gpzb_context.state=1;else if(n==2)gpzb_context.phase=GPZ_AUTH;else if(n==3)gpzb_context.pending_raw=1;
  else if(n==4)gpzb_work.owner_pa+=0x100000;else if(n==5)z.owner_state=PSZ_COPIED;
  else {unsigned id=(n-6)/2;gpzb_work.transaction[id].returned.x[(n-6)%2]=UINT64_C(0x100000000);gpzb_context.work=gpzb_work;}
  unsecure_failed();CHECK(!u.stores&&!u.memreads);
 }
 unsecure_setup();u.drop=200;unsecure_failed();CHECK(u.kept&&u.submits==201&&u.fences==200);
 unsecure_setup();u.bad_shadow=8192;unsecure_failed();
 unsecure_setup();u.budget_fail=1;unsecure_failed();CHECK(ggub_diagnostic.reason==UGD_ENTRY_BUDGET&&!u.stores);
 unsecure_setup();u.phase=GGU_WAIT;u.kind=8;unsecure_failed();
 for(int mode=0;mode<=5;mode++)if(mode!=2&&mode!=3&&mode!=4){
  unsecure_setup();z.flag=mode;struct ggu_receipt out,saved;memset(&out,0xa5,sizeof(out));saved=out;unsigned budgets=h.budgets;
  CHECK(sweet_gpu_unsecure_once(&out)==GGU_ARGUMENT&&!memcmp(&out,&saved,sizeof(out))&&sweet_gpu_unsecure_state()==GMB_IDLE&&h.budgets==budgets&&!u.stores);
 }
 CHECK(!mprotect(ram,16384,PROT_READ|PROT_WRITE));
 printf("GPU unsecure live board: %u actual CP+ZAP+GGU/private-receipt/owner-seam/mode/PROT_NONE/fault/deadline/once cases PASS; no hardware mode proof\n",cases-first);
}

@WRITE_FIXTURE@
@IB_FIXTURE@

int main(void)
{
    happy();unsigned budgets=h.budgets,translations=h.translations,pmaps=h.pmap_calls;
    reset();CHECK(sweet_gmu_smmu_once(NULL,NULL)==GMB_ARGUMENT&&!gmb_lifecycle);
    for(unsigned i=1;i<=3;i++){reset();h.context=i;failed();CHECK(!h.maps);}
    reset();h.clock_bad=1;failed();reset();h.irq_bad=1;failed();
    for(unsigned i=1;i<=4;i++){reset();h.owner_fail=i;failed();}
    for(unsigned i=1;i<=2;i++){reset();h.map_fail=i;failed();reset();h.misalign=i;failed();}
    for(unsigned i=1;i<=2;i++){reset();h.overflow=i;failed();}
    for(unsigned i=1;i<=translations;i++){reset();h.fail_translation=i;failed();}
    for(unsigned i=1;i<=pmaps;i++){reset();h.pmap_fail=i;failed();reset();h.attr_fail=i;failed();}
    reset();*(uint32_t *)(void *)(reset_page+0x2000)=0;failed();CHECK(h.maps==1&&!h.smmu_calls);
    reset();*(uint32_t *)(void *)(reset_page+0x2000)=UINT32_MAX;failed();CHECK(h.maps==1&&!h.smmu_calls);
    reset();h.smmu_fail=1;failed();CHECK(!h.nc_maps&&!h.impl_lines);reset();h.smmu_fail=2;failed();CHECK(h.diag_lines==2&&h.impl_lines==1);
    reset();h.smmu_fail=3;failed();CHECK(h.diag_lines==2&&h.impl_lines==1&&h.atos_lines==1);
    reset();h.alloc_fail=1;failed();CHECK(h.allocs==1&&!h.frees);
    reset();h.corrupt=1;failed();CHECK(h.allocs==1&&h.frees==1);
    reset();h.expire=10;failed();
    for(unsigned i=1;i<=budgets;i++){reset();h.budget_fail=i;failed();}
    printf("GMU actual board adapter: %u mapping/owner/reset/budget/failure cases PASS\n",cases);
    firmware_cases();
    firmware_perf_cases();
    firmware_bw_cases();
    firmware_dcvs_cases();
    firmware_gpu_cases();
    gpu_start_cases();
    gpu_sqe_cases();
    gpu_core_cases();
    gpu_cp_cases();
    gpu_zap_cases();
    gpu_unsecure_cases();
    gpu_write_cases();
    gpu_ib_cases();
}
