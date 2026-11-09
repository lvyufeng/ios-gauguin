/* No GPU emulation: compare the exact accepted/new guard hardware traces. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uintptr_t vm_offset_t;
#define GSM_BANKS 8
#define GSM_STREAMS 16
#define GSM_FSR_FAULT_MASK UINT32_C(0xc00001fe)
enum { GMF_AO, GGS_FINAL=10 };
struct gsm_receipt {
    uint32_t bank[2],slot[2],cr0_after,micro_after,sctlr[2],actlr[2],tcr2,tcr,mair0,mair1;
    uint32_t s2cr_after[2],smr_after[2];uint64_t ttbr0[2],ttbr1[2];bool stream_match;
};
static struct { struct gsm_receipt smmu; } gmb_work;
static struct { uint32_t state,halt_attempted,phase,probe_active,probe_hole,probe_bank; } ggb_context;
static struct fw_work { uint32_t gfsr,fsr[2],host_info,ao_status; } gfw_work;
static vm_offset_t gmb_reset=0x100000,gfw_map[1];
static unsigned assertions,calls,fail_at,mutate_at;
static uint64_t mutation;
static uint8_t mmio[65536];
static struct io_record { uint32_t kind,space,offset,ok;uint64_t value; } trace[64];
static uint32_t host_value,ao_value;
#define CHECK(x) do { ++assertions;assert(x); } while(0)
static uint64_t record(unsigned kind,unsigned space,unsigned off,uint64_t value,bool *ok) {
    assert(calls<64);unsigned index=calls++;struct io_record *t=&trace[index];
    if(calls==mutate_at)value^=mutation;
    if(kind!=2)value=(uint32_t)value;
    *ok=calls!=fail_at;
    if(kind==3){if(!*ok)value=UINT32_MAX;*ok=true;}
    t->kind=kind;t->space=space;t->offset=off;t->ok=*ok;t->value=*ok?value:0;return value;
}
static bool gmb_read32(void *cookie,uint32_t off,uint32_t *out) {
    assert(!cookie&&out&&off<=sizeof(mmio)-4&&!(off&3));uint32_t value;memcpy(&value,mmio+off,4);bool ok;
    value=(uint32_t)record(1,0,off,value,&ok);if(ok)*out=value;return ok;
}
static bool gmb_read64(void *cookie,uint32_t off,uint64_t *out) {
    assert(!cookie&&out&&off<=sizeof(mmio)-8&&!(off&7));uint64_t value;memcpy(&value,mmio+off,8);bool ok;
    value=record(2,0,off,value,&ok);if(ok)*out=value;return ok;
}
static uint32_t gfw_load32(vm_offset_t address) {
    bool ok;
    if(address==gmb_reset+0x2648)return (uint32_t)record(3,1,0x2648,host_value,&ok);
    assert(gfw_map[GMF_AO]&&address==gfw_map[GMF_AO]+0x2c14);
    return (uint32_t)record(3,2,0x2c14,ao_value,&ok);
}

@HELPERS@
@BASELINE@
@CURRENT@

static void put32(unsigned off,uint32_t value){memcpy(mmio+off,&value,4);}
static void put64(unsigned off,uint64_t value){memcpy(mmio+off,&value,8);}
static void setup(unsigned config,unsigned fail,unsigned corrupt,uint64_t bits) {
    memset(&gmb_work,0,sizeof(gmb_work));memset(&ggb_context,0,sizeof(ggb_context));
    memset(&gfw_work,0xa5,sizeof(gfw_work));memset(mmio,0,sizeof(mmio));memset(trace,0,sizeof(trace));
    calls=0;fail_at=fail;mutate_at=corrupt;mutation=bits;host_value=ao_value=0;
    struct gsm_receipt *s=&gmb_work.smmu;s->stream_match=config&1;gfw_map[GMF_AO]=(config&2)?0x200000:0;
    s->bank[0]=0;s->bank[1]=1;s->slot[0]=2;s->slot[1]=3;
    s->cr0_after=0x100037;s->micro_after=0x2378;s->tcr2=0x8;s->tcr=0x9a801900;
    s->mair0=0xff44;s->mair1=0;
    put32(0x48,0);put32(0,s->cr0_after);put32(0x6000,s->micro_after);
    for(unsigned n=0;n<2;++n){
        s->sctlr[n]=0xc01167;s->actlr[n]=0x70000000;s->s2cr_after[n]=n;s->smr_after[n]=0x80000000+n;
        s->ttbr0[n]=0x30000aa280000ull+n*0x1000;s->ttbr1[n]=0x30000aa290000ull+n*0x1000;
        unsigned cb=0x8000+0x1000*n;
        put32(cb+0x58,0x400);put32(cb,s->sctlr[n]);put32(cb+4,s->actlr[n]);put32(cb+0x10,s->tcr2);
        put32(cb+0x30,s->tcr);put32(cb+0x38,s->mair0);put32(cb+0x3c,s->mair1);
        put32(0x1000+4*n,0x1f300);put32(0x1800+4*n,1);put32(0xc00+4*s->slot[n],s->s2cr_after[n]);
        put32(0x800+4*s->slot[n],s->smr_after[n]);put64(cb+0x20,s->ttbr0[n]);put64(cb+0x28,s->ttbr1[n]);
    }
    if(config&4){ggb_context.state=1;ggb_context.halt_attempted=1;ggb_context.phase=5;put32(0x6000,s->micro_after|4);}
    if(config&8){ggb_context.state=1;ggb_context.probe_active=1;ggb_context.probe_hole=1;ggb_context.probe_bank=0;put32(0x8058,0x402);}
    if(config&16)s->bank[0]=GSM_BANKS;
    if(config&32)s->slot[1]=GSM_STREAMS;
}
static unsigned compare(unsigned config,bool probe,unsigned fail,unsigned corrupt,uint64_t bits) {
    setup(config,fail,corrupt,bits);bool before=baseline_faults(probe);unsigned count=calls;
    struct fw_work state=gfw_work;struct io_record prior[64];memcpy(prior,trace,sizeof(prior));
    setup(config,fail,corrupt,bits);memset(&gfw_read_sample,0,sizeof(gfw_read_sample));
    CHECK(gfw_faults(probe)==before);CHECK(calls==count);CHECK(!memcmp(prior,trace,sizeof(prior)));
    CHECK(!memcmp(&state,&gfw_work,sizeof(state)));CHECK(calls>0);
    struct io_record *last=&trace[calls-1];CHECK(gfw_read_sample.kind==last->kind);
    CHECK(gfw_read_sample.space==last->space);CHECK(gfw_read_sample.offset==last->offset);
    CHECK(gfw_read_sample.ok==last->ok);CHECK(gfw_read_sample.value==last->value);
    return count;
}
int main(void) {
    for(unsigned config=0;config<16;++config){
        bool probe=(config&12)!=0;unsigned count=compare(config,probe,0,0,0);
        CHECK(count>=27&&count<=31);
        for(unsigned i=1;i<=count;++i){
            compare(config,probe,i,0,0);
            for(unsigned bit=0;bit<64;++bit)compare(config,probe,0,i,UINT64_C(1)<<bit);
        }
        if(probe)compare(config,false,0,0,0);
    }
    compare(16,false,0,0,0);compare(32,false,0,0,0);
    printf("GFW cache: %u assertions; real old/new IO/results identical across read failures, all bit corruptions, probes and invalid routes\n",assertions);
}
