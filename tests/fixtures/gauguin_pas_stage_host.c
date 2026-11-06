/* Execute production staging C with DT/map/translation/crypto platform seams.
 * The crypto seam accepts ONLY the exact synthetic6860-byte image (byte
 * comparison against independent fixture bytes) and then returns the real
 * production SHA256 literal; any other bytes yield a different digest. The
 * production kernel links the native SHA256 implementation. These checks prove
 * flow, strict bytes, negative paths and guard-page bounds, NOT host or
 * hardware cryptographic qualification. The staged page is an anonymous span
 * bracketed by inaccessible guard pages, so any access outside the one mapped
 *16KiB page faults.
 *
 * The DT descriptor and the asset page are not invented here: main() reads
 * exactly16 descriptor bytes and exactly16384 asset bytes (EOF required) from
 * the files named on the command line, as serialized by the real packer. The
 * descriptor is copied back from those bytes on every reset, so the second
 * word of the property is exercised exactly as emitted rather than regenerated
 * by the fixture. */
#define _GNU_SOURCE 1
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <sys/mman.h>
#include <string.h>
#include <pthread.h>
#include "gauguin_pas_stage.h"
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
/* Emitted by the packer (main() loads them) and copied verbatim on reset. */
static uint64_t descriptor[2],asset_pa;
static uint8_t emitted_descriptor[16],emitted_page[16384];
static uint64_t low_pa=0x94000000;
static const uint8_t raw_pin[32]={
    0x6f,0x2a,0x0e,0x35,0x32,0x50,0x97,0xf9,0x8f,0xde,0xd6,0x12,0x3d,0x75,0x52,0x66,
    0xcd,0xbb,0x44,0xca,0xa9,0x32,0xbe,0x61,0x25,0x1b,0x65,0xb5,0xc5,0x16,0xac,0x7b};
static struct {
    int bad_context,missing,property_error,map_error,translation_error,corrupt,alias_error;
    int probe_flag,stage_flag; unsigned claim_checks;
    unsigned maps,translations,hashes,barriers,markers,flushes,properties;
    char log[8192];size_t used;
} mock;
static void assert_not_claimable(void)
{
    struct sweet_pas_cpu_stage out={UINT64_C(0x8877665544332211),0x12345678,0x87654321};
    const struct sweet_pas_cpu_stage saved=out;
    assert(!sweet_pas_cpu_stage_claim(&out));
    assert(!memcmp(&out,&saved,sizeof(out)));
    assert(!sweet_pas_cpu_stage_claim(NULL));
    ++mock.claim_checks;
}
bool PE_parse_boot_argn(const char *name,void *out,size_t bytes)
{
    assert(bytes==sizeof(int));
    if(!strcmp(name,"sweetpasprobe")) *(int*)out=mock.probe_flag;
    else { assert(!strcmp(name,"sweetpasstage")); *(int*)out=mock.stage_flag; }
    return true;
}
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
    uint64_t actual=asset_pa;
    if(pa!=actual && pa!=actual+0x3fff)return 0; /* unmapped direct-map range */
    if(pa==actual && mock.alias_error==1)return 0;
    if(pa!=actual && mock.alias_error==2)return (vm_offset_t)(asset+0x4000);
    return (vm_offset_t)(asset+(pa-actual));
}
vm_offset_t ml_io_map_wcomb(vm_offset_t pa,vm_size_t bytes)
{
    assert(!mock.bad_context && pa==low_pa && bytes==16384 && !mock.maps);
    assert(strstr(mock.log,"pinned MDT verified; mapping first16KiB"));
    assert_not_claimable();
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
    assert_not_claimable();
    assert(bytes==6860 && (p==asset || p==target));
    if(p==asset)assert(!mock.maps);else assert(mock.barriers==1);
    ctx->match=!memcmp(p,synthetic,bytes);
    ++mock.hashes;
}
void SHA256_Final(uint8_t *out,SHA256_CTX *ctx)
{ if(ctx->match)memcpy(out,raw_pin,32);else memset(out,0,32); }
void sweet_log_mark_sync(const char *line) { assert(!mock.bad_context && strstr(mock.log,line));++mock.markers; }
void sweet_log_flush_now(void) { assert_not_claimable();assert(mock.markers==mock.flushes+1);++mock.flushes; }
static void fake_dsb(void)
{
    assert_not_claimable();
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
    memset(&mock,0,sizeof(mock));pst_state=PST_IDLE;memset(&pst_ready,0,sizeof(pst_ready));pst_mapping=0;
    mock.probe_flag=mock.stage_flag=1;
    real_phys_size=0x10000000ul;arm_vm_kernelcache_phys_end=asset_pa;
    args=(boot_args){2,gPhysBase,real_phys_size,asset_pa+3*16384};PE_state.bootArgs=&args;
    /* Verbatim emitted property; only tests that must corrupt it or move it
     * past topOfKernelData write descriptor[] after this. */
    memcpy(descriptor,emitted_descriptor,sizeof(descriptor));
    memcpy(asset,emitted_page,sizeof(emitted_page));
    memset(target,0xa5,16384);
}
static void assert_failed(void)
{
    assert(pst_state==PST_FAILED); assert_not_claimable();
    unsigned maps=mock.maps,hashes=mock.hashes,properties=mock.properties;
    sweet_pas_stage_once(low_pa,0x100000);
    assert(pst_state==PST_FAILED && mock.maps==maps && mock.hashes==hashes && mock.properties==properties);
}
static void untouched(void) { for(unsigned i=0;i<16384;i++)assert(target[i]==0xa5);assert(!mock.barriers);assert_failed(); }
static void assert_claim_ready(uint64_t expected_pa)
{
    assert(pst_state==PST_READY && mock.claim_checks>0);
    assert(!sweet_pas_cpu_stage_claim(NULL) && pst_state==PST_READY);
    struct sweet_pas_cpu_stage out={0,0,0};
    assert(sweet_pas_cpu_stage_claim(&out));
    assert(pst_state==PST_CLAIMED && out.pa==expected_pa && out.metadata_bytes==6860 && out.reserved_bytes==16384);
    const struct sweet_pas_cpu_stage saved=out;
    assert(!sweet_pas_cpu_stage_claim(&out) && !memcmp(&out,&saved,sizeof(out)));
    assert_not_claimable();
    unsigned maps=mock.maps,hashes=mock.hashes,properties=mock.properties;
    sweet_pas_stage_once(expected_pa,0x100000);
    assert(pst_state==PST_CLAIMED && mock.maps==maps && mock.hashes==hashes && mock.properties==properties);
    assert(!memcmp(&pst_ready,&saved,sizeof(saved)));
}
struct claim_thread_result { bool claimed; struct sweet_pas_cpu_stage record; };
static void *claim_thread(void *opaque)
{
    struct claim_thread_result *result=opaque;
    result->record=(struct sweet_pas_cpu_stage){UINT64_C(0x8877665544332211),0x12345678,0x87654321};
    const struct sweet_pas_cpu_stage saved=result->record;
    result->claimed=sweet_pas_cpu_stage_claim(&result->record);
    if(!result->claimed)assert(!memcmp(&result->record,&saved,sizeof(saved)));
    return NULL;
}
static void load_exact(const char *path,void *out,size_t bytes)
{
    FILE *file=fopen(path,"rb");assert(file);
    assert(fread(out,1,bytes,file)==bytes);
    assert(fgetc(file)==EOF);assert(!ferror(file));assert(!fclose(file));
}
int main(int argc,char **argv)
{
    if(argc!=3){fprintf(stderr,"usage: %s descriptor.bin page.bin\n",argv[0]);return 2;}
    load_exact(argv[1],emitted_descriptor,sizeof(emitted_descriptor));
    load_exact(argv[2],emitted_page,sizeof(emitted_page));
    memcpy(&asset_pa,emitted_descriptor,sizeof(asset_pa));
    /* The descriptor word restored by reset() describes the page the C
     * consumer stages: it must be exactly one emitted16KiB page. */
    uint64_t length;memcpy(&length,emitted_descriptor+8,sizeof(length));
    assert(length==16384);
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
    assert_claim_ready(low_pa);
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
         * zero, emitted+1, unaligned, below kernelcache, exactly at top. */
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
    /* Descriptor second word: only the reserved page is accepted. The raw or
     * near-raw metadata lengths, and one byte either side of16KiB, are refused
     * before any mapping. */
    static const uint64_t lengths[]={6860,16383,16385};
    for(unsigned mode=0;mode<3;mode++) {
        reset();descriptor[1]=lengths[mode];
        sweet_pas_stage_once(low_pa,0x100000);
        assert(!mock.maps && mock.properties==1);untouched();
        assert(strstr(mock.log,"missing/invalid pinned MDT asset; no low mapping"));
    }
    for(unsigned mode=0;mode<5;mode++) {
        reset();if(mode==0)mock.map_error=1;
        if(mode==1 || mode==2)mock.translation_error=(int)mode;
        if(mode>=3)mock.corrupt=(int)mode-2;
        sweet_pas_stage_once(low_pa,0x100000);assert(!strstr(mock.log,"complete metadata_bytes="));
        assert(mock.maps==1);assert_failed();if(mode<=2)untouched();
        else assert(pst_mapping==(vm_offset_t)target && mock.barriers==1);
        sweet_pas_stage_once(low_pa,0x100000);assert(mock.maps==1);
    }
    /* Disabled flags leave IDLE and cannot consume the one staging attempt. */
    static const int off_values[]={0,2,-1};
    for(unsigned flag=0;flag<2;++flag) for(unsigned i=0;i<3;++i) {
        reset();
        if(flag==0)mock.probe_flag=off_values[i];else mock.stage_flag=off_values[i];
        assert(pst_state==PST_IDLE);assert_not_claimable();
        sweet_pas_stage_once(low_pa,0x100000);
        assert(pst_state==PST_IDLE && !mock.maps && !mock.hashes && !mock.properties && !mock.markers);
        assert_not_claimable();
        for(unsigned j=0;j<16384;++j)assert(target[j]==0xa5);
        mock.probe_flag=mock.stage_flag=1;
        sweet_pas_stage_once(low_pa,0x100000);assert_claim_ready(low_pa);
    }
    /* Pure boot reset fixture: production has no IDLE reset or unclaim API.
     * A second valid dynamic reservation must be returned, never a fixed PA. */
    reset();low_pa=UINT64_C(0x98200000);
    sweet_pas_stage_once(low_pa,0x100000);assert_claim_ready(low_pa);
    /* Eight concurrent consumers compete for the one immutable record. */
    reset();sweet_pas_stage_once(low_pa,0x100000);assert(pst_state==PST_READY);
    pthread_t consumers[8];struct claim_thread_result claims[8];unsigned winners=0;
    memset(claims,0,sizeof(claims));
    for(unsigned i=0;i<8;++i)assert(!pthread_create(&consumers[i],NULL,claim_thread,&claims[i]));
    for(unsigned i=0;i<8;++i) {
        assert(!pthread_join(consumers[i],NULL));
        if(claims[i].claimed) {
            ++winners;assert(claims[i].record.pa==low_pa && claims[i].record.metadata_bytes==6860 && claims[i].record.reserved_bytes==16384);
        }
    }
    assert(winners==1 && pst_state==PST_CLAIMED);assert_not_claimable();
    /* Failed entry is terminal and must not export a formerly valid record. */
    reset();sweet_pas_stage_once(0,0x100000);assert_failed();
    assert(pst_ready.pa==0 && pst_ready.metadata_bytes==0 && pst_ready.reserved_bytes==0);
    free(asset);assert(!munmap(lo,span));puts("PAS staging: bounds/hash before mapping, guarded readback, translation/corruption failures and retention pass");return 0;
}