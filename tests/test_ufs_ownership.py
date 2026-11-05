#!/usr/bin/env python3
"""Exercise actual UFS ownership, failed completions and reserved-tail geometry."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
ufs = (SOURCE / 'bsd/dev/sweet_ufs.c').read_text()
fixed = 'static bool ufs_poisoned;' in ufs
reserved = 'ufs_configure_geometry(void)' in ufs
if not (fixed and reserved):
    if 'XNU_SOURCE' in os.environ:
        raise AssertionError('explicit staged source lacks UFS ownership/geometry fixes')
    print('skip UFS ownership test: default cache lacks new patches')
    raise SystemExit(0)
hfs = (SOURCE / 'bsd/sweet_hfs/core/hfs.h').read_text()
definitions = '\n'.join(re.findall(
    r'^#define (?:REG_\w+|HCS_\w+|CAP_\w+|UFS_SLOT_\w+|DMA_\w+|UFS_BLOCK|'
    r'BOUNCE_SIZE|PRDT_CHUNK|PRDT_MAX|CMD_\w+|SWEET_LOG_SIZE|SWEET_LOG_BLOCKS|'
    r'SWEET_MARK_BLOCKS|UFS_RESERVED_TAIL_BLOCKS)\s+[^\n]+', ufs, re.M))
for name in ('utrd', 'ucd', 'sweet_log_header'):
    begin = ufs.index('struct ' + name + ' {')
    definitions += '\n' + ufs[begin:ufs.index('\n};', begin) + 3]
begin = ufs.index('static int\nufs_scsi_slot(')
transfer = ufs[begin:ufs.index('\n}\n', begin) + 3]
begin = ufs.index('static void\nsweet_ufs_strategy(')
strategy = ufs[begin:ufs.index('\n}\n', begin) + 3]
helper = ''
if fixed:
    begin = ufs.index('static bool ufs_poisoned;')
    helper = ufs[begin:ufs.index('\n}\n', begin) + 3]
geometry = ''
if reserved:
    begin = ufs.index('static int\nufs_configure_geometry(void)')
    geometry = ufs[begin:ufs.index('\n}\n', begin) + 3]
log_functions = ''
for signature in ('static uint32_t\nsweet_log_mark_flush(void)',
                  'static int\nsweet_log_flush('):
    begin = ufs.index(signature)
    log_functions += ufs[begin:ufs.index('\n}\n', begin) + 3] + '\n'
capacity = re.search(r'case DKIOCGETBLOCKCOUNT:\s*([^;]+;)', ufs)[1]
alt_sector = re.search(r'^#define HFS_ALT_SECTOR[^\n]+', hfs, re.M)[0]
code = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#define MIN(a,b) ((a)<(b)?(a):(b))
#define NSEC_PER_SEC 1000000000ull
#define NSEC_PER_USEC 1000ull
#define bzero(p,n) memset((p),0,(n))
#define __builtin_arm_dsb(x) ((void)(x))
#define THREAD_UNINT 0
#define TIMEOUT_URGENCY_SYS_CRITICAL 0
#define THREAD_WAITING 1
#define THREAD_CONTINUE_NULL NULL
#define DEV_BSIZE 512
#define B_READ 1
#define TRUE true
#define os_atomic_load(p,order) __atomic_load_n((p),__ATOMIC_RELAXED)
#define LCK_MTX_ASSERT_OWNED 1
typedef void *event_t;
typedef uint64_t addr64_t;
typedef char *caddr_t;
@DEFINITIONS@
@ALT_SECTOR@
static _Alignas(64) uint8_t dma[DMA_SIZE];
static struct {
    uintptr_t dma; uint64_t dma_pa, first_block, nblocks, fs_nblocks;
    uint8_t lun; unsigned secsize; bool cache, wait, ready, writable;
} su;
@HELPER@
static pthread_mutex_t sweet_dma_owner_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t sweet_io_serial_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t sweet_log_lock=PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t sweet_mark_lock=PTHREAD_MUTEX_INITIALIZER;
static _Thread_local unsigned owner_depth;
static unsigned global_waiters;
static void lck_mtx_lock(pthread_mutex_t *p)
{
    if (p==&sweet_dma_owner_lock) {
        assert(!owner_depth);
        __atomic_add_fetch(&global_waiters,1,__ATOMIC_RELEASE);
    }
    assert(!pthread_mutex_lock(p));
    if (p==&sweet_dma_owner_lock) {
        __atomic_sub_fetch(&global_waiters,1,__ATOMIC_RELEASE);
        owner_depth=1;
    }
}
static void lck_mtx_unlock(pthread_mutex_t *p)
{
    if (p==&sweet_dma_owner_lock) { assert(owner_depth==1);owner_depth=0; }
    assert(!pthread_mutex_unlock(p));
}
static int lck_mtx_try_lock(pthread_mutex_t *p)
{
    if (pthread_mutex_trylock(p)) return 0;
    if (p==&sweet_dma_owner_lock) { assert(!owner_depth);owner_depth=1; }
    return 1;
}
#if @FIXED@
static void lck_mtx_assert(pthread_mutex_t *p,int assertion)
{ assert(p==&sweet_dma_owner_lock && assertion==LCK_MTX_ASSERT_OWNED && owner_depth==1); }
#endif
static uint32_t doorbell;
static unsigned rings, clear_attempts, reused_while_owned;
static uint64_t ticks;
static uint8_t first_cdb;
static uint32_t ufs_rd(uint32_t reg) { return reg == REG_UTRLDBR ? doorbell : 0; }
static void ufs_wr(uint32_t reg, uint32_t value)
{
    if (reg == REG_UTRLDBR) {
        struct ucd *c = (void *)(dma + DMA_UCD);
        if (doorbell && c->cmd[16] != first_cdb) reused_while_owned++;
        if (!rings) first_cdb = c->cmd[16];
        rings++;
        doorbell |= value;
    }
    if (reg == REG_UTRLCLR) {
        clear_attempts++; /* Hardware deliberately has NOT acknowledged clear. */
        assert(value == ~(1u << UFS_SLOT_MAIN));
    }
}
static void dma_sync(uint32_t off, uint32_t len) { (void)off; (void)len; }
static void dma_clean(uint32_t off, uint32_t len) { (void)off; (void)len; }
static void nanoseconds_to_absolutetime(uint64_t ns, uint64_t *out) { (void)ns; *out=5; }
static uint64_t mach_absolute_time(void) { return ++ticks; }
static void delay(unsigned usec) { (void)usec; }
static bool ml_get_interrupts_enabled(void) { return true; }
static bool ml_at_interrupt_context(void) { return false; }
static int get_preemption_level(void) { return 0; }
static int PE_parse_boot_argn(const char *name, void *v, size_t n)
{ (void)n; *(int *)v = !strcmp(name,"sweetufsquiet") ? 1 : 0; return 1; }
static void sweet_ufs_log(const char *fmt, ...) { (void)fmt; }
static int assert_wait_deadline_with_leeway(event_t e,int i,int u,uint64_t d,int l)
{ (void)e;(void)i;(void)u;(void)d;(void)l;return 0; }
static void thread_block(void *f) { (void)f; }
@TRANSFER@
struct buffer { int64_t blkno; uint32_t count, resid; int flags,error,done; char data[4096]; };
typedef struct buffer *buf_t;
static int fake_read_error;
static int64_t buf_blkno(buf_t b) { return b->blkno; }
static uint32_t buf_count(buf_t b) { return b->count; }
static int buf_flags(buf_t b) { return b->flags; }
static void buf_setresid(buf_t b,uint32_t r) { b->resid=r; }
static int buf_map(buf_t b,char **p) { *p=b->data;return 0; }
static void buf_unmap(buf_t b) { (void)b; }
static void buf_seterror(buf_t b,int e) { b->error=e; }
static void buf_biodone(buf_t b) { b->done=1; }
static int ufs_read_blocks(uint64_t lba,uint32_t count)
{ (void)lba;(void)count;return fake_read_error; }
static int ufs_write_blocks(uint64_t lba,uint32_t count)
{ (void)lba;(void)count;return EIO; }
@STRATEGY@
@GEOMETRY@
static char sweet_log_ring[SWEET_LOG_SIZE], sweet_mark_ram[SWEET_MARK_BLOCKS*4096];
static uint32_t sweet_mark_dirty[SWEET_MARK_BLOCKS/32];
static uint64_t sweet_log_total;
static unsigned log_submissions;
static int sweet_log_write_blocks(uint64_t lba,uint32_t count)
{ (void)lba;(void)count;log_submissions++;return EIO; }
static int sweet_log_sync_cache(void) { log_submissions++;return EIO; }
static void clean_dcache64(uint64_t pa,unsigned len,bool phys)
{ (void)pa;(void)len;(void)phys; }
@LOG_FUNCTIONS@
#if @FIXED@
struct contender { int kind, result; struct buffer b; };
static void *contend(void *opaque)
{
    struct contender *c=opaque;
    if(c->kind==0) {
        sweet_ufs_strategy(&c->b);c->result=c->b.error;
    } else if(c->kind==1) {
        uint64_t flushed=0,seq=0;
        c->result=sweet_log_flush(&flushed,&seq,false);
        assert(!flushed && !seq);
    } else c->result=(int)sweet_log_mark_flush();
    return NULL;
}
static void concurrent_ownership(void)
{
    uint8_t cdb[10]={0x28};
    for(int kind=0;kind<3;kind++) {
        ufs_poisoned=false;doorbell=0;rings=clear_attempts=ticks=0;
        su.first_block=0x100000;su.nblocks=su.fs_nblocks=4096;su.ready=su.writable=true;
        sweet_log_total=16;sweet_mark_dirty[0]=1;log_submissions=0;
        memset(dma+DMA_BOUNCE,0x73,4096);
        memset(dma+DMA_BOUNCE_LOG,0x73,4096);memset(dma+DMA_MARK,0x73,4096);
        struct contender c={.kind=kind,.b={.count=4096}};
        memset(c.b.data,0xcc,4096);
        lck_mtx_lock(&sweet_dma_owner_lock);
        pthread_t thread;assert(!pthread_create(&thread,NULL,contend,&c));
        unsigned spins=0;
        while(!__atomic_load_n(&global_waiters,__ATOMIC_ACQUIRE) && ++spins<1000000) sched_yield();
        assert(spins<1000000);
        /* A different owner is waiting before its first bounce mutation. */
        assert(dma[DMA_BOUNCE]==0x73 && dma[DMA_BOUNCE_LOG]==0x73 && dma[DMA_MARK]==0x73);
        assert(ufs_scsi_slot(cdb,10,4096,false,su.dma_pa+DMA_BOUNCE,UFS_SLOT_MAIN)==ETIMEDOUT);
        lck_mtx_unlock(&sweet_dma_owner_lock);
        assert(!pthread_join(thread,NULL));
        assert(c.result==(kind==2?0:EIO) && rings==1 && !log_submissions);
        assert(dma[DMA_BOUNCE]==0x73 && dma[DMA_BOUNCE_LOG]==0x73 && dma[DMA_MARK]==0x73);
    }
    /* Panic must not block when another owner (including a stopped CPU) exists. */
    lck_mtx_lock(&sweet_dma_owner_lock);
    uint64_t flushed=0,seq=0;
    assert(sweet_log_flush(&flushed,&seq,true)==EBUSY);
    lck_mtx_unlock(&sweet_dma_owner_lock);
    assert(lck_mtx_try_lock(&sweet_log_lock));lck_mtx_unlock(&sweet_log_lock);
    puts("PASS: actual strategy/log/mark contenders cannot enter DMA before timed-out owner releases; panic skips busy owner");
}
#endif
static uint64_t exposed_blocks(void)
{
    uint64_t value, *o=&value;
    @CAPACITY@
    return value;
}
int main(void)
{
    su.dma=(uintptr_t)dma; su.dma_pa=0x184724000ull; su.secsize=512;
    uint8_t read_cdb[10]={0x28}, write_cdb[10]={0x2a};
    lck_mtx_lock(&sweet_dma_owner_lock);
    assert(ufs_scsi_slot(read_cdb,10,4096,false,su.dma_pa+DMA_BOUNCE,UFS_SLOT_MAIN)==ETIMEDOUT);
    assert(doorbell == 1 && rings == 1 && clear_attempts == 1);
    int second=ufs_scsi_slot(write_cdb,10,4096,true,su.dma_pa+DMA_BOUNCE,UFS_SLOT_MAIN);
    if (@FIXED@) {
        assert(second==EIO && doorbell==1 && rings==1 && clear_attempts==1 && !reused_while_owned);
        puts("PASS: poisoned transfer rejects reuse before descriptor mutation or doorbell");
    } else {
        assert(second==ETIMEDOUT && doorbell==1 && rings==2 && clear_attempts==2 && reused_while_owned==1);
        puts("REPRODUCED: actual transfer reuses outstanding descriptor and rings again after unacknowledged timeout clear");
    }
    lck_mtx_unlock(&sweet_dma_owner_lock);
    su.writable=true; su.nblocks=su.fs_nblocks=1024;
    struct buffer b={.count=4096}; memset(b.data,0xcc,sizeof(b.data));
    memset(dma+DMA_BOUNCE,0x5a,4096);
    sweet_ufs_strategy(&b);
    assert(b.error==EIO && b.done && b.resid==4096);
    if (@FIXED@) {
        for (unsigned i=0;i<4096;i++) assert(dma[DMA_BOUNCE+i]==0x5a);
        puts("PASS: actual strategy cannot prewrite an owned bounce buffer after poison");
        su.first_block=0x100000;su.nblocks=4096;su.ready=true;
        sweet_log_total=16;sweet_mark_dirty[0]=1;
        memset(dma+DMA_BOUNCE_LOG,0x62,BOUNCE_SIZE);
        memset(dma+DMA_MARK,0x62,4096);
        uint64_t flushed=0, seq=0;
        assert(sweet_log_flush(&flushed,&seq,false)==EIO);
        assert(sweet_log_flush(&flushed,&seq,true)==EIO);
        assert(!sweet_log_mark_flush());
        assert(!flushed && !seq && !log_submissions && sweet_mark_dirty[0]==1);
        for (unsigned i=0;i<BOUNCE_SIZE;i++) assert(dma[DMA_BOUNCE_LOG+i]==0x62);
        for (unsigned i=0;i<4096;i++) assert(dma[DMA_MARK+i]==0x62);
        const unsigned slots[]={UFS_SLOT_LOG,UFS_SLOT_MARK};
        lck_mtx_lock(&sweet_dma_owner_lock);
        for (unsigned i=0;i<2;i++) {
            assert(ufs_scsi_slot(write_cdb,10,4096,true,su.dma_pa+DMA_MARK,slots[i])==EIO);
            assert(rings==1);
        }
        lck_mtx_unlock(&sweet_dma_owner_lock);
        puts("PASS: actual normal/panic log flush and marker paths preserve DMA and issue nothing after poison");
    } else {
        assert(dma[DMA_BOUNCE]==0xcc);
        puts("REPRODUCED: actual strategy prewrites bounce before discovering IO failure");
    }
#if @FIXED@
    concurrent_ownership();
#endif
    @RESET_POISON@

    su.first_block=0x100000; su.nblocks=28056571; /* actual captured partition size */
    su.fs_nblocks=su.nblocks-SWEET_LOG_BLOCKS-SWEET_MARK_BLOCKS;
    uint64_t last_log=su.first_block+su.nblocks-SWEET_LOG_BLOCKS+1+
                      (SWEET_LOG_SIZE/UFS_BLOCK-1);
    uint64_t alternate_sector=HFS_ALT_SECTOR(su.secsize, exposed_blocks());
    uint64_t alternate_block=su.first_block+alternate_sector*su.secsize/UFS_BLOCK;
    assert(last_log==su.first_block+su.nblocks-1);
    if (@RESERVED@) assert(alternate_block<su.first_block+su.nblocks-SWEET_LOG_BLOCKS-SWEET_MARK_BLOCKS);
    else assert(last_log==alternate_block);
    uint64_t exposed_bytes=(su.nblocks-SWEET_LOG_BLOCKS-SWEET_MARK_BLOCKS)*UFS_BLOCK;
    assert(exposed_bytes > 4194304ull*4096); /* actual HFS totalBlocks*blockSize */
    printf("%s: HFS alternate LBA=%llu, log last=%llu, exposed bytes=%llu\n",
           @RESERVED@ ? "PASS separated" : "REPRODUCED overlap", (unsigned long long)alternate_block,
           (unsigned long long)last_log,(unsigned long long)exposed_bytes);
    @GEOMETRY_TEST@
#if @RESERVED@
    su.secsize=512;su.writable=true;su.fs_nblocks=1024;
    const int64_t invalid_blocks[]={-1,INT64_MIN,INT64_MAX,(int64_t)(1ull<<55),8193};
    for(unsigned i=0;i<sizeof(invalid_blocks)/sizeof(invalid_blocks[0]);i++) {
        struct buffer invalid={.blkno=invalid_blocks[i],.count=512};
        memset(dma+DMA_BOUNCE,0x6e,4096);
        sweet_ufs_strategy(&invalid);
        assert(invalid.done && invalid.error==EINVAL && invalid.resid==512);
        assert(dma[DMA_BOUNCE]==0x6e);
    }
    struct buffer empty_end={.blkno=8192,.count=0};
    sweet_ufs_strategy(&empty_end);assert(empty_end.done && !empty_end.error);
    struct buffer crossing={.blkno=8191,.count=1024};
    sweet_ufs_strategy(&crossing);assert(crossing.error==EINVAL && crossing.resid==1024);
    struct buffer zero_sector={.blkno=0,.count=512};su.secsize=0;
    sweet_ufs_strategy(&zero_sector);assert(zero_sector.error==EINVAL);
    puts("PASS: actual strategy rejects negative/overflowing/end-crossing sectors before DMA, accepts zero-length EOF");
#endif
    return 0;
}
'''.replace('@DEFINITIONS@', definitions).replace('@ALT_SECTOR@', alt_sector).replace(
    '@TRANSFER@', transfer).replace('@CAPACITY@', capacity).replace('@HELPER@', helper).replace(
    '@STRATEGY@', strategy).replace('@GEOMETRY@', geometry).replace('@LOG_FUNCTIONS@', log_functions).replace('@FIXED@', str(int(fixed))).replace(
    '@RESERVED@', str(int(reserved))).replace('@RESET_POISON@', 'ufs_poisoned=false;' if fixed else '')
geometry_test = r'''
    uint8_t *vh=dma+DMA_BOUNCE+1024;
    memset(vh,0,512);
    vh[0]=0x48; vh[1]=0x58; vh[3]=5; vh[42]=0x10; vh[45]=0x40; /*4K,4194304 blocks*/
    su.fs_nblocks=0;
    assert(ufs_configure_geometry()==0 && su.fs_nblocks*4096==exposed_bytes);
    su.fs_nblocks=0;
    vh[44]=0xff; vh[45]=vh[46]=vh[47]=0xff;
    assert(ufs_configure_geometry()==ENXIO && !su.fs_nblocks); /*too large*/
    vh[0]=0; assert(ufs_configure_geometry()==ENXIO && !su.fs_nblocks); /*unknown fs*/
    vh[0]=0x48; vh[44]=0; vh[45]=0x40; vh[46]=vh[47]=0;
    vh[43]=1; assert(ufs_configure_geometry()==ENXIO && !su.fs_nblocks); /*bad allocation size*/
    vh[43]=0; fake_read_error=EIO;
    assert(ufs_configure_geometry()==EIO && !su.fs_nblocks);
    puts("PASS: actual geometry gate accepts captured16GiB shape, rejects oversized/unknown/malformed/read-error before exposing disk");
''' if reserved else ''
code = code.replace('@GEOMETRY_TEST@', geometry_test)
with tempfile.TemporaryDirectory(prefix='ufs-ownership-') as directory:
    tmp = Path(directory)
    (tmp / 'repro.c').write_text(code)
    subprocess.run([os.environ.get('CC', 'cc'), '-std=c11', '-Wall', '-Wextra',
                    '-Werror', '-fsanitize=address,undefined', '-g', str(tmp / 'repro.c'),
                    '-o', str(tmp / 'repro')], check=True)
    subprocess.run([str(tmp / 'repro')], check=True)
