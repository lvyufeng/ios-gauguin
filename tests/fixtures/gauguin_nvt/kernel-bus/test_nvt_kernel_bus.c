#define NVT_BUS_HOST_TEST 1
#include <nvt_kernel_bus.c> /* actual adapter control flow, not a reimplementation */
#include <assert.h>
#include <stdio.h>

/* Reuse the frozen transport's finite16-word FIFO model. This imports its
 * test helpers only; the actual PIO implementation is linked separately. */
#define main frozen_pio_suite_main
#include "../test_geni_spi_pio.c"
#undef main

static struct mock spi;
static struct {
    uint32_t vote, clock[0x1000/4], wrapper, cfg[6], io[6];
    uint32_t cfg_before[6], io_before[6], se_before[0x1000/4];
    struct { uintptr_t base; uint32_t off, value; } trace[4096];
    unsigned writes, reads, maps, marks, barriers, time_conversions, delays, forces;
    unsigned se_maps, pin_maps, dfs_reads, fail_writes, cfg_reads;
    uintptr_t fail_map, fail_base;
    uint32_t fail_offset;
    uint64_t ticks;
    thread_t thread;
    int legacy, probe, preemption;
    bool irqs, interrupt, freeze, change_dfs, gate_stuck, partial_unvote, refuse_revote;
} hw;
static struct nvt_bus_status *final_at_unlock;
static bool final_seen, replace_after_unlock;

thread_t current_thread(void) { return hw.thread; }
bool ml_get_interrupts_enabled(void) { return hw.irqs; }
bool ml_at_interrupt_context(void) { return hw.interrupt; }
int get_preemption_level(void) { return hw.preemption; }
bool lck_mtx_try_lock(struct test_mutex *m)
{ if (m->owner) return false; m->owner=hw.thread; return true; }
void lck_mtx_unlock(struct test_mutex *m)
{
    assert(m->owner==hw.thread);
    if(final_at_unlock) {
        assert(final_at_unlock->state==nv_bus.status.state);
        assert(final_at_unlock->error==nv_bus.status.error);
        assert(!memcmp(&final_at_unlock->setup,&nv_bus.setup.report,sizeof(nv_bus.setup.report)));
        assert(!memcmp(&final_at_unlock->pio,&nv_bus.pio.diag,sizeof(nv_bus.pio.diag)));
        final_seen=true;
    }
    m->owner=0;
    /* Simulate another opener replacing the released singleton immediately.
     * Final-report consumers must not read it after unlocking. */
    if(replace_after_unlock) memset(&nv_bus,0xa5,sizeof(nv_bus));
}
bool PE_parse_boot_argn(const char *name, void *out, int size)
{
    assert(size==(int)sizeof(int));
    if (!strcmp(name,"sweettouchmode")) *(int *)out=hw.legacy;
    else { assert(!strcmp(name,"sweetnvtprobe")); *(int *)out=hw.probe; }
    return true;
}
static int pin_index(uintptr_t pa)
{
    for (unsigned i=0;i<6;i++) if(pa==NV_TLMM_PA+nv_pins[i]*0x1000u) return (int)i;
    return -1;
}
vm_offset_t ml_io_map(vm_offset_t pa, vm_size_t size)
{
    hw.maps++;
    bool valid=(pa==NV_CLOCK_PA || pa==NV_VOTE_PA) && size==0x1000;
    valid|=pa==NV_WRAPPER_PA && size==0x2000;
    valid|=pa==NV_SE_PA && size==0x4000;
    if(pa==NV_SE_PA) hw.se_maps++;
    if(pin_index(pa)>=0) { valid|=size==0x1000; hw.pin_maps++; }
    assert(valid);
    return pa==hw.fail_map?0:pa;
}
uint64_t mach_absolute_time(void) { return hw.ticks; }
void absolutetime_to_nanoseconds(uint64_t ticks,uint64_t *ns)
{ hw.time_conversions++; *ns=ticks*50; } /* deliberately NOT1tick==1ns */
void delay(int us)
{ assert(us==1); hw.delays++; if(!hw.freeze) hw.ticks+=(uint64_t)us*20; }
void sweet_log_mark_sync(const char *s) { assert(s && *s); hw.marks++; }
void test_barrier(void) { hw.barriers++; }
static bool se_offset(uint32_t off)
{
    static const uint32_t offsets[]={0x20,0x24,0x28,0x40,0x48,0x64,0x68,0x6c,0x7c,
        0x224,0x22c,0x230,0x24c,0x250,0x254,0x258,0x25c,0x260,0x264,0x268,
        0x26c,0x270,0x278,0x284,0x288,0x600,0x604,0x610,0x614,0x618,0x640,
        0x644,0x648,0x700,0x780,0x800,0x804,0x80c,0x810,0x814,0xe18,0xe1c,
        0xe24,0xe28,0xe30};
    for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++) if(off==offsets[i]) return true;
    return false;
}
uint32_t test_mmio_read(vm_offset_t base,uint32_t off)
{
    assert(nvt_bus_mutex.owner==hw.thread); hw.reads++;
    if(base==NV_VOTE_PA) { assert(off==0); return hw.vote; }
    if(base==NV_CLOCK_PA) {
        assert(off==4 || off==8 || off==0x144 || off==0x15c || off==0x164);
        if(off==0x15c && hw.change_dfs && ++hw.dfs_reads>=2) return 0x23;
        if(off==0x164) hw.cfg_reads++;
        if(off==0x144 && hw.gate_stuck) return 0x80004220;
        return hw.clock[off/4];
    }
    if(base==NV_WRAPPER_PA) { assert(off==4 && (hw.vote&NV_VOTES)==NV_VOTES); return hw.wrapper; }
    if(base==NV_SE_PA) {
        assert(se_offset(off) && (hw.vote&NV_VOTES)==NV_VOTES);
        return read32(&spi,off);
    }
    int i=pin_index(base); assert(i>=0 && (off==0 || off==4));
    return off==0?hw.cfg[i]:hw.io[i];
}
void test_mmio_write(vm_offset_t base,uint32_t off,uint32_t value)
{
    assert(nvt_bus_mutex.owner==hw.thread && hw.writes<4096);
    hw.trace[hw.writes].base=base;hw.trace[hw.writes].off=off;
    hw.trace[hw.writes++].value=value;
    bool reject=hw.fail_writes && base==hw.fail_base && off==hw.fail_offset;
    if(reject) hw.fail_writes--;
    if(base==NV_VOTE_PA) {
        assert(off==0 && ((value^hw.vote)&~NV_VOTES)==0);
        if(hw.partial_unvote && !(value&NV_VOTES)) {
            hw.vote=value|0x40;hw.partial_unvote=false;return;
        }
        if(hw.refuse_revote && (value&NV_VOTES)>(hw.vote&NV_VOTES)) return;
        if(!reject) hw.vote=value;
        return;
    }
    if(base==NV_SE_PA) {
        assert(se_offset(off) && (hw.vote&NV_VOTES)==NV_VOTES);
        if(reject) return;
        if(off==0x20) { assert(value==1); hw.forces++;return; }
        if(off==0x648) { spi.reg[0x640/4]&=~value;return; }
        if(off==GS_M_CMD || off==GS_M_CTRL || off==GS_TX_FIFO || off==GS_M_IRQ_CLEAR)
            write32(&spi,off,value);
        else spi.reg[off/4]=value;
        return;
    }
    int i=pin_index(base);assert(i>=0 && (off==0 || off==4));
    if(off==4) {
        assert(i==4 && ((value^hw.io[i])&~NV_GPIO_OUT)==0);
        if(!reject) hw.io[i]=value;
    } else {
        uint32_t mask=NV_PIN_FIELDS|NV_EGPIO_ENABLE|(i>=4?NV_OE:0);
        assert(((value^hw.cfg[i])&~mask)==0);
        if(!reject) hw.cfg[i]=value;
    }
}
static void init(void)
{
    assert(!nvt_bus_mutex.owner);
    final_at_unlock=NULL;final_seen=false;replace_after_unlock=false;
    memset(&hw,0,sizeof(hw));memset(&nv_bus,0,sizeof(nv_bus));
    memset(&nv_maps,0,sizeof(nv_maps));nv_quarantined=false;nv_generation=0;
    (void)setup(&spi);
    spi.reg[GS_FW_REVISION/4]=spi.reg[0x6c/4]=0x101;
    spi.reg[GS_HW_PARAM0/4]=0x201029e4;spi.reg[GS_HW_PARAM1/4]=0x20104800;
    spi.reg[0x48/4]=0x11;spi.reg[GS_WORD_LEN/4]=0;
    spi.reg[GS_TX_PACK0/4]=spi.reg[GS_RX_PACK0/4]=0x7f807;
    spi.reg[GS_IRQ_EN/4]=15;spi.reg[GS_M_IRQ_EN/4]=0x33c0007e;
    spi.reg[GS_M_IRQ_STATUS/4]=0;spi.reg[GS_TRANS_CFG/4]=0;
    hw.vote=0x9c000003;hw.wrapper=0x20070000;hw.thread=1;hw.irqs=true;
    hw.clock[8/4]=0x8000000a;hw.clock[0x144/4]=0x4220;
    hw.clock[0x15c/4]=0x21;hw.clock[0x164/4]=1;
    for(unsigned i=0;i<6;i++) {
        hw.cfg[i]=0xa5000801|(i==1?NV_OE:0);
        hw.io[i]=(i==0 || i==3?1:0);
    }
    memcpy(hw.cfg_before,hw.cfg,sizeof(hw.cfg));memcpy(hw.io_before,hw.io,sizeof(hw.io));
    memcpy(hw.se_before,spi.reg,sizeof(spi.reg));
}
static struct nvt_bus *prepared(bool pins)
{
    struct nvt_bus *b=NULL;
    assert(!nvt_bus_open(&b) && b && !hw.pin_maps && !spi.command_count);
    assert(!nvt_bus_configure(b,1000000));
    assert(b->status.sck_hz==960000 && spi.reg[0x48/4]==0x141);
    assert(!hw.pin_maps && !spi.command_count);
    if(pins) assert(!nvt_bus_activate_native_pins(b));
    return b;
}
static void restored(void)
{
    assert(hw.vote==0x9c000003);
    assert(!memcmp(hw.cfg_before,hw.cfg,sizeof(hw.cfg)));
    assert(!memcmp(hw.io_before,hw.io,sizeof(hw.io)));
    for(unsigned i=0;i<sizeof(spi.reg)/sizeof(spi.reg[0]);i++) {
        /* IRQ history and command/FIFO data are deliberately not restored. */
        if(i==GS_M_IRQ_STATUS/4 || i==GS_M_IRQ_CLEAR/4 || i==GS_M_CMD/4 ||
           i==GS_TX_FIFO/4 || i==0x648/4) continue;
        assert(spi.reg[i]==hw.se_before[i]);
    }
}
static void success(void)
{
    init();assert(!hw.maps && !hw.reads && !hw.writes); /* no startup hook */
    struct nvt_bus *b=prepared(true);
    assert(hw.pin_maps==6 && (hw.cfg[4]&0x3ff)==0x3c3 && (hw.io[4]&2)==0);
    assert((hw.cfg[5]&0x3ff)==0x1c1);
    for(unsigned i=0;i<4;i++) {
        assert((hw.cfg[i]&0x1ff)==nv_pin_values[i]);
        assert((hw.cfg[i]&NV_OE)==(hw.cfg_before[i]&NV_OE));
        assert(hw.io[i]==hw.io_before[i]);
    }
    unsigned first_pin=0;while(first_pin<hw.writes && pin_index(hw.trace[first_pin].base)<0) first_pin++;
    assert(first_pin+1<hw.writes && hw.trace[first_pin].base==NV_TLMM_PA+21*0x1000);
    assert(hw.trace[first_pin].off==4 && !(hw.trace[first_pin].value&2));
    assert(hw.trace[first_pin+1].off==0 && (hw.trace[first_pin+1].value&NV_OE));
    uint8_t tx[67],rx[67];for(unsigned i=0;i<67;i++) tx[i]=(uint8_t)(i+2);
    unsigned before_invalid=hw.writes;
    assert(nvt_bus_xfer(b,tx,tx,67)==EINVAL && nvt_bus_xfer(b,tx,tx+1,66)==EINVAL);
    assert(hw.writes==before_invalid && !spi.command_count);
    /* Native eng-reset is legal with RST LOW. No dummy or prefix modification. */
    assert(!nvt_bus_xfer(b,tx,rx,67) && spi.command_count==1 && spi.shifted==67);
    assert(!memcmp(spi.wire,tx,67));for(unsigned i=0;i<67;i++) assert(rx[i]==response(tx[i]));
    assert(!nvt_bus_set_reset(b,true) && (hw.io[4]&2));
    assert(!nvt_bus_xfer(b,tx,NULL,3) && spi.command_count==2);
    struct nvt_bus_status status;
    assert(!nvt_bus_close(b,&status));restored();
    struct nvt_bus_status untouched=status;
    assert(nvt_bus_get_status(b,&status)==EPERM && !memcmp(&status,&untouched,sizeof(status)));
    assert(status.state==NVT_BUS_CLOSED && status.pins_restored && status.clocks_restored);
    assert(status.setup.config_restored && status.setup.effects==GSS_FORCE_ISSUED);
    assert(nvt_bus_xfer(b,tx,rx,67)==EPERM);
    /* New invocation requalifies hardware even though mappings are retained. */
    unsigned before_reads=hw.reads;hw.wrapper=0;struct nvt_bus *again=b;
    assert(nvt_bus_open(&again)==ENOTSUP && !again && hw.reads>before_reads);
    assert(hw.vote==0x9c000003);
}
static void exclusions(void)
{
    for(unsigned why=0;why<6;why++) {
        init();if(why==0) hw.legacy=1;if(why==1) hw.probe=2;
        if(why==2) hw.irqs=false;if(why==3) hw.interrupt=true;
        if(why==4) hw.preemption=1;if(why==5) hw.thread=0;
        struct nvt_bus *b=(void*)1;
        assert(nvt_bus_open(&b)!=0 && !b && !hw.maps && !hw.writes && !hw.reads);
    }
    init();struct nvt_bus *b=prepared(false),*second=NULL;
    unsigned writes=hw.writes;assert(nvt_bus_open(&second)==EBUSY && !second);
    hw.thread=2;assert(nvt_bus_activate_native_pins(b)==EPERM);
    assert(nvt_bus_close(b,NULL)==EPERM);assert(hw.writes==writes);hw.thread=1;
    assert(!nvt_bus_close(b,NULL));restored();
}
static void open_failures(void)
{
    const uintptr_t maps[]={NV_CLOCK_PA,NV_VOTE_PA,NV_WRAPPER_PA,NV_SE_PA};
    for(unsigned i=0;i<4;i++) {
        init();hw.fail_map=maps[i];struct nvt_bus *b=NULL;
        assert(nvt_bus_open(&b)==ENOMEM && !b && !nvt_bus_mutex.owner);
        assert(hw.vote==0x9c000003 && !hw.pin_maps && !spi.command_count);
    }
    for(unsigned mode=0;mode<6;mode++) {
        init();if(mode==0) hw.clock[0x15c/4]=0x23;
        if(mode==1) hw.clock[0x164/4]=0x101;
        if(mode==2) hw.change_dfs=true;
        if(mode==3) spi.reg[0x6c/4]=0x201;
        if(mode==4) spi.reg[GS_HW_PARAM0/4]=0x200829e4;
        if(mode==5) spi.reg[GS_DMA_MODE/4]=1;
        struct nvt_bus *b=NULL;assert(nvt_bus_open(&b)!=0 && !b);
        assert(hw.vote==0x9c000003 && !spi.command_count && !hw.pin_maps);
        if(mode<3) assert(!hw.writes && !hw.se_maps);
        if(mode==0) assert(!hw.cfg_reads);
    }
    init();hw.gate_stuck=true;hw.freeze=true;struct nvt_bus *b=NULL;
    assert(nvt_bus_open(&b)==ETIMEDOUT && !b && hw.delays==2000);
    assert(hw.time_conversions>0 && hw.vote==0x9c000003 && !hw.se_maps);
    hw.ticks=1000;assert(nv_now_us()==50); /* catches rawticks-as-us/ns regression */
}
static void failure_boundaries(void)
{
    init();struct nvt_bus *b=NULL;assert(!nvt_bus_open(&b));
    unsigned writes=hw.writes;
    assert(nvt_bus_configure(b,0)==EINVAL && nvt_bus_configure(b,1000001)==EINVAL);
    assert(writes==hw.writes && !nvt_bus_close(b,NULL));restored();
    init();b=prepared(false);hw.fail_map=NV_TLMM_PA+22*0x1000;
    writes=hw.writes;assert(nvt_bus_activate_native_pins(b)==ENOMEM);
    assert(hw.writes==writes && !nvt_bus_close(b,NULL));restored();
    init();b=prepared(false);hw.fail_base=NV_TLMM_PA+21*0x1000;hw.fail_offset=0;hw.fail_writes=1;
    assert(nvt_bus_activate_native_pins(b)==EIO && nv_quarantined);
    uint32_t vote=hw.vote;assert(nvt_bus_close(b,NULL)==EIO && hw.vote==vote);
    assert(!nvt_bus_mutex.owner && !spi.reg[GS_IRQ_EN/4] && !spi.reg[GS_GSI_EVENT_EN/4]);
    init();b=prepared(true);spi.fault=STALL;hw.freeze=true;b->pio.max_polls=8;
    uint8_t tx[67]={0},rx[67];assert(nvt_bus_xfer(b,tx,rx,67)==ETIMEDOUT);
    assert(nv_quarantined && spi.command_count==1 && b->pio.diag.polls==8);
    writes=hw.writes;assert(nvt_bus_xfer(b,tx,rx,67)==EBUSY && hw.writes==writes);
    uint32_t cfg[6],io[6];memcpy(cfg,hw.cfg,sizeof(cfg));memcpy(io,hw.io,sizeof(io));vote=hw.vote;
    assert(nvt_bus_close(b,NULL)!=0 && hw.vote==vote);
    assert(!memcmp(cfg,hw.cfg,sizeof(cfg)) && !memcmp(io,hw.io,sizeof(io)));
    assert(!spi.reg[GS_IRQ_EN/4] && !spi.reg[GS_GSI_EVENT_EN/4]);
    struct nvt_bus *other=NULL;writes=hw.writes;assert(nvt_bus_open(&other)==EIO && !other);
    assert(writes==hw.writes);
    init();b=prepared(true);hw.clock[0x164/4]=0x101;
    assert(nvt_bus_xfer(b,tx,rx,3)==EIO && !spi.command_count && nv_quarantined);
    nvt_bus_abort(b,EIO,NULL);assert(!nvt_bus_mutex.owner && (hw.vote&NV_VOTES)==NV_VOTES);
    init();b=prepared(true);hw.fail_base=NV_TLMM_PA+21*0x1000;hw.fail_offset=0;hw.fail_writes=1;
    assert(nvt_bus_close(b,NULL)==EIO && nv_quarantined && (hw.vote&NV_VOTES)==NV_VOTES);
    assert(!spi.reg[GS_IRQ_EN/4] && !spi.reg[GS_GSI_EVENT_EN/4]);
    init();b=prepared(false);nvt_bus_abort(b,ECANCELED,NULL);
    assert(nv_quarantined && (hw.vote&NV_VOTES)==NV_VOTES && !hw.pin_maps);
    /* Restoring an originally nonzero output IRQ route fails: retain every
     * added gate and all active pins, even though the SE is command-idle. */
    init();b=prepared(true);hw.fail_base=NV_SE_PA;hw.fail_offset=GS_IRQ_EN;
    /* A pending new status forces setup quarantine without re-enabling IRQ. */
    spi.reg[0x640/4]=1;
    memcpy(cfg,hw.cfg,sizeof(cfg));vote=hw.vote;
    assert(nvt_bus_close(b,NULL)==EIO && hw.vote==vote);
    assert(!memcmp(cfg,hw.cfg,sizeof(cfg)) && !spi.reg[GS_IRQ_EN/4]);
    /* Refused vote removal cannot masquerade as a successful close. */
    init();b=prepared(false);hw.fail_base=NV_VOTE_PA;hw.fail_offset=0;hw.fail_writes=1;
    struct nvt_bus_status status;
    assert(nvt_bus_close(b,&status)==EIO && nv_quarantined && (hw.vote&NV_VOTES)==NV_VOTES);
    assert(!status.clocks_restored && status.state==NVT_BUS_QUARANTINED);
    for(unsigned refuse=0;refuse<2;refuse++) {
        init();b=prepared(false);hw.partial_unvote=true;hw.refuse_revote=refuse!=0;
        assert(nvt_bus_close(b,&status)==EIO && nv_quarantined);
        assert(!status.clocks_restored && nvt_bus_get_status(b,&status)==EPERM);
        if(refuse) { assert(!status.mask_confirmed && (hw.vote&NV_VOTES)==0x40); }
        else { assert(status.mask_confirmed && (hw.vote&NV_VOTES)==NV_VOTES); }
        /* Model asserts every SE access has all3clock votes. In the refuse
         * case no containment read/write is allowed on the partially gated SE. */
    }
}
static void final_reports(void)
{
    struct nvt_bus_status final,before;
    init();struct nvt_bus *b=prepared(true);
    memset(&final,0x5a,sizeof(final));final_at_unlock=&final;replace_after_unlock=true;
    assert(!nvt_bus_close(b,&final) && final_seen);
    assert(final.state==NVT_BUS_CLOSED && final.clocks_restored && final.pins_restored);
    assert(final.setup.config_restored && !nvt_bus_mutex.owner);
    before=final;assert(nvt_bus_get_status(b,&final)==EPERM);
    assert(!memcmp(&final,&before,sizeof(final))); /* no invalid-handle output */
    for(unsigned use_abort=0;use_abort<2;use_abort++) {
        init();b=prepared(true);spi.fault=STALL;hw.freeze=true;b->pio.max_polls=8;
        uint8_t tx[67]={0},rx[67];assert(nvt_bus_xfer(b,tx,rx,67)==ETIMEDOUT);
        memset(&final,0x5a,sizeof(final));final_at_unlock=&final;replace_after_unlock=true;
        if(use_abort) nvt_bus_abort(b,ETIMEDOUT,&final);
        else assert(nvt_bus_close(b,&final)==ETIMEDOUT);
        assert(final_seen && final.state==NVT_BUS_QUARANTINED && final.mask_confirmed);
        assert(final.error==ETIMEDOUT && final.pio_result==GS_TIMEOUT && final.pio.polls==8);
        assert(final.setup.transport_status==GS_TIMEOUT && !final.clocks_restored);
        before=final;assert(nvt_bus_get_status(b,&final)==EPERM);
        assert(!memcmp(&final,&before,sizeof(final)) && !nvt_bus_mutex.owner);
    }
    init();b=prepared(true);assert(!nvt_bus_get_status(b,&final));
    assert(final.state==NVT_BUS_CONFIGURED && final.setup.sck_hz==960000);
    before=final;hw.thread=2;
    assert(nvt_bus_get_status(b,&final)==EPERM && nvt_bus_close(b,&final)==EPERM);
    nvt_bus_abort(b,EIO,&final);assert(!memcmp(&final,&before,sizeof(final)));
    hw.thread=1;assert(!nvt_bus_close(b,NULL));
}
int main(void)
{
    success();exclusions();open_failures();failure_boundaries();final_reports();
    puts("actual XNU adapter flow: ownership/maps/clock qualification/GPIO ordering/restore/quarantine PASS");
    return 0;
}
