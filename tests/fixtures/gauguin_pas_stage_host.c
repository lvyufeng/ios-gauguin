/* Execute production staging C with DT/map/translation/crypto platform seams.
 * The crypto seam accepts ONLY the exact synthetic6860-byte image (byte
 * comparison against independent fixture bytes) and then returns the real
 * production SHA256 literal; any other bytes yield a different digest. The
 * production kernel links the native SHA256 implementation. These checks prove
 * flow, strict bytes, negative paths and guard-page bounds, NOT host or
 * hardware cryptographic qualification. The staged page is an anonymous span
 * bracketed by inaccessible guard pages, so any access outside the one mapped
 *16KiB page faults. */
#define _GNU_SOURCE 1
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <sys/mman.h>
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define kSuccess 0
#define kBootArgsVersion2 2
#define SHA256_DIGEST_LENGTH 32
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef unsigned DTEntry;
typedef struct { unsigned Version; uint64_t physBase,memSize,topOfKernelData; } boot_args;
typedef struct { int match; } SHA256_CTX;
static boot_args args;
static struct { boot_args *bootArgs; } PE_state={ &args };
unsigned long gPhysBase=0x180000000ul,real_phys_size=0x10000000ul;
vm_offset_t arm_vm_kernelcache_phys_end;
static uint8_t *asset,*target;
static uint8_t synthetic[6860];
static uint64_t descriptor[2],low_pa=0x94000000;
static const uint8_t raw_pin[32]={
    0x6f,0x2a,0x0e,0x35,0x32,0x50,0x97,0xf9,0x8f,0xde,0xd6,0x12,0x3d,0x75,0x52,0x66,
    0xcd,0xbb,0x44,0xca,0xa9,0x32,0xbe,0x61,0x25,0x1b,0x65,0xb5,0xc5,0x16,0xac,0x7b};
static struct {
    int bad_context,missing,property_error,map_error,translation_error,corrupt,alias_error;
    unsigned maps,translations,hashes,barriers,markers,flushes,properties;
    char log[8192];size_t used;
} mock;
static int test_printf(const char *format,...);
static int test_printf(const char *format,...)
{
    va_list ap;va_start(ap,format);
    int n=vsnprintf(mock.log+mock.used,sizeof(mock.log)-mock.used,format,ap);
    va_end(ap);assert(n>=0 && (size_t)n<sizeof(mock.log)-mock.used);mock.used+=(size_t)n;return n;
}
int ml_get_interrupts_enabled(void) { return mock.bad_context!=1; }
int ml_at_interrupt_context(void) { return mock.bad_context==2; }
int get_preemption_level(void) { return mock.bad_context==3; }
int SecureDTLookupEntry(void *parent,const char *name,DTEntry *entry)
{
    assert(!parent && !strcmp(name,"/chosen/memory-map"));
    if(mock.missing==1)return -1;*entry=1;return 0;
}
int SecureDTGetProperty(DTEntry entry,const char *name,const void **out,unsigned *bytes)
{
    assert(entry==1 && !strcmp(name,"A615ZapMDT"));++mock.properties;
    if(mock.missing==2)return -1;
    *out=mock.property_error==1?NULL:descriptor;*bytes=mock.property_error==2?15:16;return 0;
}
vm_offset_t ml_static_ptovirt(vm_offset_t pa)
{
    uint64_t actual=gPhysBase+0x2000000;
    if(pa!=actual && pa!=actual+0x3fff)return 0; /* unmapped direct-map range */
    if(pa==actual && mock.alias_error==1)return 0;
    if(pa!=actual && mock.alias_error==2)return (vm_offset_t)(asset+0x4000);
    return (vm_offset_t)(asset+(pa-actual));
}
vm_offset_t ml_io_map_wcomb(vm_offset_t pa,vm_size_t bytes)
{
    assert(!mock.bad_context && pa==low_pa && bytes==16384 && !mock.maps);
    assert(strstr(mock.log,"pinned MDT verified; mapping first16KiB"));
    ++mock.maps;return mock.map_error?0:(vm_offset_t)target;
}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    assert(va==(vm_offset_t)target || va==(vm_offset_t)target+0x3fff);++mock.translations;
    if(mock.translation_error==1 && va==(vm_offset_t)target)return low_pa+0x4000;
    if(mock.translation_error==2 && va!=(vm_offset_t)target)return low_pa+0x4000;
    return low_pa+va-(vm_offset_t)target;
}
/* Crypto seam: only the exact synthetic digest input is accepted as the pin. */
void SHA256_Init(SHA256_CTX *ctx) { ctx->match=0; }
void SHA256_Update(SHA256_CTX *ctx,const void *p,size_t bytes)
{
    assert(bytes==6860 && (p==asset || p==target));
    if(p==asset)assert(!mock.maps);else assert(mock.barriers==1);
    ctx->match=!memcmp(p,synthetic,bytes);
    ++mock.hashes;
}
void SHA256_Final(uint8_t *out,SHA256_CTX *ctx)
{ if(ctx->match)memcpy(out,raw_pin,32);else memset(out,0,32); }
void sweet_log_mark_sync(const char *line) { assert(!mock.bad_context && strstr(mock.log,line));++mock.markers; }
void sweet_log_flush_now(void) { assert(mock.markers==mock.flushes+1);++mock.flushes; }
static void fake_dsb(void)
{
    assert(mock.maps==1 && mock.translations==2 && !memcmp(target,synthetic,6860));
    assert(strstr(mock.log,"before zero/copy"));
    for(unsigned i=6860;i<16384;i++)assert(!target[i]);++mock.barriers;
    if(mock.corrupt==1)target[0]^=1;
    if(mock.corrupt==2)target[16383]=1;
}
#define printf test_printf
@SOURCE@
#undef printf
static void reset(void)
{
    memset(&mock,0,sizeof(mock));pst_attempted=0;pst_mapping=0;
    real_phys_size=0x10000000ul;arm_vm_kernelcache_phys_end=gPhysBase+0x2000000;
    args=(boot_args){2,gPhysBase,real_phys_size,gPhysBase+0x200C000};PE_state.bootArgs=&args;
    descriptor[0]=gPhysBase+0x2000000;descriptor[1]=6860;
    memcpy(asset,synthetic,sizeof(synthetic));memset(asset+6860,0,sizeof(synthetic));
    memset(target,0xa5,16384);
}
static void untouched(void) { for(unsigned i=0;i<16384;i++)assert(target[i]==0xa5);assert(!mock.barriers); }
int main(void)
{
    void *memory=NULL;assert(!posix_memalign(&memory,16384,16384*2));asset=memory;
    size_t span=5*16384;
    void *lo=mmap(NULL,span,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);assert(lo!=MAP_FAILED);
    target=(uint8_t*)(((uintptr_t)lo+32767)&~(uintptr_t)16383);
    assert(!mprotect(target,16384,PROT_READ|PROT_WRITE));
    assert(((uintptr_t)target&16383)==0 && target>=(uint8_t*)lo+16384 && target+16384<=(uint8_t*)lo+span-16384);
    for(unsigned i=0;i<6860;i++)synthetic[i]=(uint8_t)(i%251);
    assert(PST_BYTES==6860 && PST_PAGE==16384 && PST_REGION==0x100000);
    assert(!memcmp(pst_expected,raw_pin,sizeof(raw_pin)));
    reset();sweet_pas_stage_once(low_pa,0x100000);
    assert(mock.maps==1 && mock.hashes==2 && mock.translations==2 && mock.barriers==1 && pst_mapping==(vm_offset_t)target);
    assert(strstr(mock.log,"complete metadata_bytes=6860 zero_tail_bytes=9524"));
    assert(strstr(mock.log,"sha256=6f2a0e35325097f98fded6123d755266cdbb44caa932be61251b65b5c516ac7b"));
    sweet_pas_stage_once(low_pa,0x100000);assert(mock.maps==1 && mock.hashes==2);
    /* Positive exact boundary: canonical descriptor page ending exactly at
     * topOfKernelData (nothing between it and top) is legal and must stage. */
    reset();args.topOfKernelData=descriptor[0]+PST_PAGE;
    sweet_pas_stage_once(low_pa,0x100000);
    assert(mock.maps==1 && mock.hashes==2 && mock.barriers==1);
    assert(strstr(mock.log,"complete metadata_bytes=6860 zero_tail_bytes=9524"));
    /* One step past the exact boundary (pa == top) must be refused: the
     * remaining-length check and the DRAM-end bound both reject it. */
    reset();descriptor[0]=args.topOfKernelData;
    /* The ADT property must be read to learn pa==top: properties==1 is expected;
     * only the mapping must not happen. */
    sweet_pas_stage_once(low_pa,0x100000);assert(!mock.maps && mock.properties==1);untouched();
    for(int mode=1;mode<=3;mode++) {reset();mock.bad_context=mode;sweet_pas_stage_once(low_pa,0x100000);assert(!mock.maps && !mock.properties);untouched();}
    for(unsigned mode=0;mode<5;mode++) {
        reset();uint64_t pa=low_pa,bytes=0x100000;
        if(mode==0)pa=0;if(mode==1)pa++;if(mode==2)pa=0x100000000ull;if(mode==3)bytes--;if(mode==4)bytes++;
        sweet_pas_stage_once(pa,bytes);assert(!mock.maps && !mock.properties);untouched();
        assert(strstr(mock.log,"invalid entry/context; stopped"));
    }
    for(unsigned mode=0;mode<24;mode++) {
        reset();
        if(mode==0)mock.missing=1;if(mode==1)mock.missing=2;
        if(mode==2)mock.property_error=1;if(mode==3)mock.property_error=2;
        /* boot_args-space rejections (checked in pst_asset before the ADT) */
        if(mode==4)args.Version=1;if(mode==5)args.physBase++;
        if(mode==6)real_phys_size=0;if(mode==7)args.memSize=real_phys_size+1;
        if(mode==8)args.topOfKernelData++;if(mode==9)args.topOfKernelData=args.physBase;
        if(mode==10)arm_vm_kernelcache_phys_end=args.topOfKernelData+16384;
        if(mode==11)PE_state.bootArgs=NULL;
        /* boot_args rejections come first; then genuine descriptor rejections:
         * zero, raw6861, unaligned, below kernelcache, exactly at top. */
        if(mode==12)descriptor[0]=0;if(mode==13)descriptor[1]++;
        if(mode==14)descriptor[0]+=1;if(mode==15)descriptor[0]-=16384;
        if(mode==16)descriptor[0]=arm_vm_kernelcache_phys_end-16384;
        if(mode==17)descriptor[0]=args.topOfKernelData;
        if(mode==18)descriptor[0]=args.physBase+args.memSize-16384;
        /* content/alias rejections: corrupted asset, unmapped endpoints. */
        if(mode==19)PE_state.bootArgs=NULL;
        if(mode==20)asset[100]^=1;if(mode==21)asset[6859]^=0x80;
        if(mode==22||mode==23)mock.alias_error=(int)mode-21;
        sweet_pas_stage_once(low_pa,0x100000);assert(!mock.maps);untouched();
    }
    for(unsigned mode=0;mode<5;mode++) {
        reset();if(mode==0)mock.map_error=1;
        if(mode==1 || mode==2)mock.translation_error=(int)mode;
        if(mode>=3)mock.corrupt=(int)mode-2;
        sweet_pas_stage_once(low_pa,0x100000);assert(!strstr(mock.log,"complete metadata_bytes="));
        assert(mock.maps==1);if(mode<=2)untouched();
        else assert(pst_mapping==(vm_offset_t)target && mock.barriers==1);
        sweet_pas_stage_once(low_pa,0x100000);assert(mock.maps==1);
    }
    free(asset);assert(!munmap(lo,span));puts("PAS staging: bounds/hash before mapping, guarded readback, translation/corruption failures and retention pass");return 0;
}