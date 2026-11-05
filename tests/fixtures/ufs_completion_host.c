/* Actual candidate functions are inserted below, not reimplemented. */
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>

#define MIN(a,b) ((a)<(b)?(a):(b))
#define NSEC_PER_SEC 1000000000ull
#define NSEC_PER_USEC 1000ull
#define bzero(p,n) memset((p),0,(n))
#define __builtin_arm_dsb(x) ((void)(x))
#define THREAD_UNINT 0
#define TIMEOUT_URGENCY_SYS_CRITICAL 0
#define THREAD_WAITING 1
#define THREAD_CONTINUE_NULL NULL
#define LCK_MTX_ASSERT_OWNED 1
typedef void *event_t;
@DEFINITIONS@
static _Alignas(64) uint8_t dma[DMA_SIZE];
static struct {
    uintptr_t dma; uint64_t dma_pa; uint8_t lun;
    bool cache, wait, ready;
} su;
@HELPER@
static int sweet_dma_owner_lock;
static struct {
    bool owner, pending, complete, timeout;
    unsigned polls, rings, clears, acks, delays, sleeps, cache_ops, post_cache;
    unsigned slot, opcode, logs, barrier_check;
    uint64_t ticks;
    uint8_t ocs, upiu, response, status;
    uint32_t bit;
} mock;
static void lck_mtx_assert(int *lock,int assertion)
{assert(lock==&sweet_dma_owner_lock && assertion==LCK_MTX_ASSERT_OWNED && mock.owner);}
static unsigned ucd_offset(unsigned slot)
{
    if(slot==UFS_SLOT_MAIN)return DMA_UCD;
    if(slot==UFS_SLOT_LOG)return DMA_UCD_LOG;
    assert(slot==UFS_SLOT_MARK);return DMA_UCD_MARK;
}
static unsigned bounce_offset(unsigned slot)
{
    if(slot==UFS_SLOT_MAIN)return DMA_BOUNCE;
    if(slot==UFS_SLOT_LOG)return DMA_BOUNCE_LOG;
    assert(slot==UFS_SLOT_MARK);return DMA_MARK;
}
static uint32_t ufs_rd(uint32_t reg)
{
    assert(mock.owner);
    if(reg==REG_IS){assert(mock.complete);return 1;}
    assert(reg==REG_UTRLDBR && mock.pending);
    if(!mock.timeout && ++mock.polls==3){
        struct utrd *t=(void *)(dma+DMA_UTRL+mock.slot*sizeof(struct utrd));
        struct ucd *c=(void *)(dma+ucd_offset(mock.slot));
        assert(t->dw2==0xf);t->dw2=mock.ocs;
        c->resp[0]=mock.upiu;c->resp[6]=mock.response;c->resp[7]=mock.status;
        mock.complete=true;
    }
    return mock.complete?0:mock.bit;
}
static void ufs_wr(uint32_t reg,uint32_t value)
{
    assert(mock.owner);
    if(reg==REG_UTRLDBR){
        assert(!mock.pending && !ufs_poisoned && value==mock.bit);
        struct utrd *t=(void *)(dma+DMA_UTRL+mock.slot*sizeof(struct utrd));
        struct ucd *c=(void *)(dma+ucd_offset(mock.slot));
        assert(c->cmd[3]==mock.slot && t->dw2==0xf);
        assert(((uint64_t)t->ucdbau<<32|t->ucdba)==su.dma_pa+ucd_offset(mock.slot));
        mock.opcode=c->cmd[16];mock.rings++;mock.pending=true;
        return;
    }
    if(reg==REG_UTRLCLR){
        assert(mock.timeout && ufs_poisoned && value==~mock.bit);
        mock.clears++;return; /* Deliberately leave outstanding DMA owned. */
    }
    assert(reg==REG_IS && value==1 && mock.complete);mock.acks++;
}
static void dma_sync(uint32_t off,uint32_t len)
{
    assert(mock.owner && off<=DMA_SIZE && len<=DMA_SIZE-off);
    mock.cache_ops++;
    if(mock.complete)mock.post_cache++;
}
static void dma_clean(uint32_t off,uint32_t len){dma_sync(off,len);}
static void nanoseconds_to_absolutetime(uint64_t ns,uint64_t *out)
{(void)ns;*out=10;}
static uint64_t mach_absolute_time(void){assert(mock.owner);return ++mock.ticks;}
static void delay(unsigned usec){assert(mock.owner && usec==1);mock.delays++;}
static bool ml_get_interrupts_enabled(void){return false;}
static bool ml_at_interrupt_context(void){return false;}
static int get_preemption_level(void){return 0;}
static int PE_parse_boot_argn(const char *name,void *v,size_t n)
{assert(n==sizeof(int));*(int *)v=!strcmp(name,"sweetufsquiet")?1:0;return 1;}
static void sweet_ufs_log(const char *format,...){(void)format;mock.logs++;}
static int assert_wait_deadline_with_leeway(event_t e,int i,int u,uint64_t d,int l)
{(void)e;(void)i;(void)u;(void)d;(void)l;mock.sleeps++;return THREAD_WAITING;}
static void thread_block(void *continuation){(void)continuation;mock.sleeps++;}
@FUNCTIONS@
static void setup(unsigned slot,bool cache)
{
    memset(&mock,0,sizeof(mock));memset(dma,0xa5,sizeof(dma));
    ufs_poisoned=false;su.dma=(uintptr_t)dma;su.dma_pa=0x184724000ull;
    su.cache=cache;su.wait=su.ready=true;
    mock.owner=true;mock.slot=slot;mock.bit=1u<<slot;mock.upiu=0x21;
}
static void completion_matrix(void)
{
    const unsigned slots[]={UFS_SLOT_MAIN,UFS_SLOT_LOG,UFS_SLOT_MARK};
    for(unsigned i=0;i<3;++i)for(unsigned cache=0;cache<2;++cache)for(unsigned wr=0;wr<2;++wr){
        setup(slots[i],cache);
        uint8_t cdb[10]={wr?0x2a:0x28};
        int rc=ufs_scsi_slot(cdb,10,UFS_BLOCK,wr,su.dma_pa+bounce_offset(slots[i]),slots[i]);
        assert(rc==0 && mock.complete && mock.rings==1 && mock.polls==3 && mock.acks==1);
        assert(mock.cache_ops>mock.post_cache && mock.post_cache==(cache&&wr?2u:3u));
        assert(!ufs_poisoned && !mock.clears && !mock.sleeps && mock.delays==2);
    }
    for(unsigned bad=0;bad<4;++bad){
        setup(UFS_SLOT_MAIN,true);
        if(bad==0)mock.ocs=1;
        if(bad==1)mock.upiu=0x20;
        if(bad==2)mock.response=1;
        if(bad==3)mock.status=2;
        uint8_t cdb[10]={0x28};
        assert(ufs_scsi_slot(cdb,10,UFS_BLOCK,false,su.dma_pa+DMA_BOUNCE,UFS_SLOT_MAIN)==EIO);
        assert(mock.complete && mock.acks==1 && mock.post_cache==3 && !ufs_poisoned);
    }
}
static void sync_cache_actual(void)
{
    for(unsigned error=0;error<5;++error){
        setup(UFS_SLOT_LOG,true);
        if(error==1)mock.ocs=1;
        if(error==2)mock.response=1;
        if(error==3)mock.status=2;
        if(error==4)mock.timeout=true;
        int result=sweet_log_sync_cache();
        assert(result==(error==0?0:error==4?ETIMEDOUT:EIO));
        assert(mock.opcode==0x35 && mock.rings==1 && !mock.sleeps);
        if(error==4){
            assert(ufs_poisoned && mock.clears==1 && !mock.complete && !mock.acks);
            unsigned cache_before=mock.cache_ops;
            uint8_t saved[sizeof(struct ucd)];memcpy(saved,dma+DMA_UCD_LOG,sizeof(saved));
            assert(sweet_log_sync_cache()==EIO && mock.rings==1 && mock.cache_ops==cache_before);
            assert(memcmp(saved,dma+DMA_UCD_LOG,sizeof(saved))==0);
        }else assert(mock.complete && mock.acks==1 && mock.post_cache==2 && !ufs_poisoned);
    }
}
static void legacy_stage_noop(void)
{
    static uint8_t before[DMA_SIZE];
    for(unsigned poisoned=0;poisoned<2;++poisoned){
        setup(UFS_SLOT_MAIN,false);mock.owner=false;ufs_poisoned=poisoned;
        memcpy(before,dma,sizeof(dma));
        sweet_stage(UINT32_MAX,UINT32_MAX);
        sweet_stage_panic(UINT32_MAX,UINT32_MAX,UINT64_MAX,UINT64_MAX,(void *)(uintptr_t)1);
        assert(memcmp(before,dma,sizeof(dma))==0 && !mock.rings && !mock.cache_ops && !mock.logs && !mock.ticks);
    }
}
int main(void)
{
    completion_matrix();sync_cache_actual();legacy_stage_noop();
    puts("PASS: actual 0/2/4 completion/cache/IRQ-off polling, OCS+UPIU errors, sync-cache error propagation and inert legacy stage");
    return 0;
}
