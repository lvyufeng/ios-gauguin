/* Actual complete staging + post-CP owner C. Only OS/board/asset APIs are seams. */
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <CommonCrypto/CommonDigest.h>
#include "gauguin_pas_stage.h"
#include "gauguin_gpu_zap_asset.h"
#define GAUGUIN 1
#define PAGE_SHIFT 14
#define kSuccess 0
#define kBootArgsVersion2 2
#define SHA256_DIGEST_LENGTH 32
typedef uintptr_t vm_offset_t;typedef size_t vm_size_t;typedef unsigned ppnum_t,DTEntry;typedef int boolean_t;
typedef struct {unsigned Version;uint64_t physBase,memSize,topOfKernelData;} boot_args;
typedef CC_SHA256_CTX SHA256_CTX;
static _Alignas(16384) uint8_t metadata[16384],code[16384];
static uint8_t *target,*allocation;
static const uint64_t low_pa=UINT64_C(0xaa200000),high_pa=UINT64_C(0x180100000);
unsigned long gPhysBase=0x180000000ul,real_phys_size=0x2000000ul;
vm_offset_t arm_vm_kernelcache_phys_end;
static boot_args args;static struct {boot_args *bootArgs;} PE_state={&args};
static struct {unsigned maps,hashes,stage_barriers,copy_barriers,guards,guard_fail,view_calls,view_fail,corrupt;
    unsigned active,context,managed,attr_bad,owner_page,translation_bad,phase,accept,missing_init;
    int zap,probe,stage,init,mem;} h;
static unsigned cases;
static int host_log(const char *fmt,...){(void)fmt;return 1;}
static void SHA256_Init(SHA256_CTX *c){assert(CC_SHA256_Init(c));}
static void SHA256_Update(SHA256_CTX *c,const void *p,size_t n)
{
    assert(n==6860&&(p==metadata||p==target));
    if(p==target)assert(sweet_pas_zap_owner_state()<PSZ_INIT_ENTERED);
    ++h.hashes;assert(CC_SHA256_Update(c,p,(CC_LONG)n));
}
static void SHA256_Final(uint8_t *out,SHA256_CTX *c){assert(CC_SHA256_Final(out,c));}
bool PE_parse_boot_argn(const char *name,void *out,size_t n)
{
    assert(n==sizeof(int));
    if(!strcmp(name,"sweetgpuzap"))*(int*)out=h.zap;
    else if(!strcmp(name,"sweetpasprobe"))*(int*)out=h.probe;
    else if(!strcmp(name,"sweetpasstage"))*(int*)out=h.stage;
    else if(!strcmp(name,"sweetpasinit")){if(h.missing_init)return false;*(int*)out=h.init;}
    else {assert(!strcmp(name,"sweetpasmem"));*(int*)out=h.mem;}return true;
}
int ml_get_interrupts_enabled(void){return h.context!=1;}
int ml_at_interrupt_context(void){return h.context==2;}
int get_preemption_level(void){return h.context==3;}
int SecureDTLookupEntry(void *p,const char *path,DTEntry *out)
{assert(!p&&!strcmp(path,"/chosen/memory-map"));*out=1;return 0;}
int SecureDTGetProperty(DTEntry node,const char *name,const void **out,unsigned *n)
{static uint64_t range[2];assert(node==1&&!strcmp(name,"A615ZapMDT"));range[0]=high_pa;range[1]=16384;*out=range;*n=16;return 0;}
vm_offset_t ml_static_ptovirt(vm_offset_t pa)
{assert(pa==high_pa||pa==high_pa+16383);return (vm_offset_t)metadata+pa-high_pa;}
vm_offset_t ml_io_map_wcomb(vm_offset_t pa,vm_size_t n)
{assert(pa==low_pa&&n==16384&&!h.maps++);return (vm_offset_t)target;}
vm_offset_t ml_vtophys(vm_offset_t va)
{assert(va==(vm_offset_t)target||va==(vm_offset_t)target+16383);return low_pa+va-(vm_offset_t)target+(h.translation_bad?16384:0);}
boolean_t pmap_valid_page(ppnum_t p)
{assert(p>=low_pa/16384&&p<(low_pa+0x100000)/16384);return h.managed&&p==low_pa/16384+h.owner_page;}
unsigned pmap_cache_attributes(ppnum_t p)
{assert(p>=low_pa/16384&&p<(low_pa+0x100000)/16384);return h.attr_bad&&p==low_pa/16384+h.owner_page?0:0xd0000006;}
void sweet_log_mark_sync(const char *s){(void)s;}
void sweet_log_flush_now(void){}
bool sweet_gpu_zap_owner_phase(enum gpz_phase phase,uint64_t pa)
{return h.active&&h.phase==(unsigned)phase&&pa==low_pa;}
bool sweet_gpu_zap_owner_action_allowed(enum gpz_owner_action action,uint64_t pa)
{
    enum gpz_phase expected=action==GPZO_SEAL?GPZ_SEAL:action==GPZO_INIT_ENTER||action==GPZO_INIT_ACCEPT?GPZ_INIT:action==GPZO_MEM_ACCEPT?GPZ_MEM:GPZ_AUTH;
    return sweet_gpu_zap_owner_phase(expected,pa)&&(action<=GPZO_INIT_ENTER||h.accept);
}
bool sweet_gpu_zap_asset_view(struct gza_view *out)
{++h.view_calls;if(h.view_calls==h.view_fail)return false;*out=(struct gza_view){code,high_pa+0x20000,1984};return true;}
bool sweet_gpu_zap_copy_live(void)
{assert(h.phase==GPZ_COPY&&sweet_pas_zap_owner_state()==PSZ_COPYING);++h.guards;return h.guards!=h.guard_fail;}
static void host_dsb(void)
{
    if(sweet_pas_zap_owner_state()==PSZ_COPYING){++h.copy_barriers;if(h.corrupt&&h.copy_barriers==1)target[h.corrupt-1]^=1;}
    else {assert(!memcmp(target,metadata,6860));++h.stage_barriers;}
}
#define printf host_log
@SOURCE@
#undef printf
static void setup(void)
{
    ++cases;assert(!mprotect(target,16384,PROT_READ|PROT_WRITE));
    memset(&h,0,sizeof(h));h.active=h.zap=h.probe=h.stage=h.accept=1;
    pst_state=PST_IDLE;memset(&pst_ready,0,sizeof(pst_ready));pst_mapping=0;psz_lifecycle=PSZ_IDLE;memset(&psz_code,0,sizeof(psz_code));
    args=(boot_args){2,gPhysBase,real_phys_size,high_pa+0x40000};arm_vm_kernelcache_phys_end=high_pa;
    memset(target,0xa5,16384);sweet_pas_stage_once(low_pa,0x100000);
    struct sweet_pas_cpu_stage claim;assert(sweet_pas_cpu_stage_claim(&claim)&&claim.pa==low_pa&&h.maps==1&&h.stage_barriers==1);
    h.phase=GPZ_SEAL;
}
static void before_copy_mode(int mode)
{
    setup();h.zap=mode;assert(sweet_pas_zap_owner_live(GPZ_SEAL,low_pa));assert(sweet_pas_zap_owner_action(GPZO_SEAL));
    h.phase=GPZ_INIT;assert(sweet_pas_zap_owner_live(GPZ_INIT,low_pa));assert(sweet_pas_zap_owner_action(GPZO_INIT_ENTER));
    /* Real SCM_RW may change ANY metadata/tail byte; the new path must not
     * rehash those bytes or clear the old tail before the native code copy. */
    memset(target,0xd5,16384);unsigned hashes=h.hashes;
    assert(sweet_pas_zap_owner_live(GPZ_INIT,low_pa));assert(sweet_pas_zap_owner_action(GPZO_INIT_ACCEPT));
    h.phase=GPZ_MEM;assert(sweet_pas_zap_owner_live(GPZ_MEM,low_pa));assert(sweet_pas_zap_owner_action(GPZO_MEM_ACCEPT));
    assert(h.hashes==hashes);h.phase=GPZ_COPY;
}
static void before_copy(void){before_copy_mode(1);}
int main(int argc,char **argv)
{
    assert(argc==3);FILE *f=fopen(argv[1],"rb");assert(f&&fread(metadata,1,6860,f)==6860&&fgetc(f)==EOF);fclose(f);
    f=fopen(argv[2],"rb");assert(f&&fread(code,1,1984,f)==1984&&fgetc(f)==EOF);fclose(f);
    allocation=mmap(NULL,49152,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);assert(allocation!=MAP_FAILED);target=allocation+16384;
    before_copy();unsigned hashes=h.hashes;struct gpz_copy out;assert(sweet_pas_zap_copy(&out)&&out.written==1984&&out.checked==1984&&h.copy_barriers==2);
    assert(!memcmp(target,code,1984));for(unsigned i=1984;i<16384;i++)assert(target[i]==0xd5);
    assert(h.hashes==hashes&&h.maps==1);unsigned guards=h.guards;
    h.phase=GPZ_AUTH;assert(!mprotect(target,16384,PROT_NONE));assert(sweet_pas_zap_owner_live(GPZ_AUTH,low_pa));
    assert(sweet_pas_zap_owner_action(GPZO_AUTH_ACCEPT));assert(sweet_pas_zap_owner_state()==PSZ_AUTH_DONE&&sweet_pas_zap_owner_live(GPZ_AUTH,low_pa));
    h.phase=GPZ_FINAL;assert(sweet_pas_zap_owner_live(GPZ_FINAL,low_pa));assert(h.hashes==hashes);
    for(unsigned n=1;n<=guards;n++){
        before_copy();h.guard_fail=n;memset(&out,0xa5,sizeof(out));assert(!sweet_pas_zap_copy(&out)&&sweet_pas_zap_owner_state()==PSZ_FAILED&&h.guards==n);
        for(unsigned i=1984;i<16384;i++)assert(target[i]==0xd5);
        struct gpz_copy saved=out;assert(!sweet_pas_zap_copy(&out)&&!memcmp(&saved,&out,sizeof(out)));
    }
    for(unsigned n=1;n<=2;n++){before_copy();h.corrupt=n==1?1:1984;assert(!sweet_pas_zap_copy(&out)&&sweet_pas_zap_owner_state()==PSZ_FAILED&&out.written==1984&&out.checked==(n==1?0u:1983u));}
    before_copy();h.view_fail=2;assert(!sweet_pas_zap_copy(&out)&&!out.written&&!out.checked&&sweet_pas_zap_owner_state()==PSZ_FAILED);
    setup();h.view_fail=1;assert(!sweet_pas_zap_owner_action(GPZO_SEAL)&&sweet_pas_zap_owner_state()==PSZ_FAILED);
    for(unsigned at=0;at<3;at++)for(unsigned page=0;page<64;page++)for(unsigned attr=0;attr<2;attr++){
        if(at==0)setup();else before_copy();h.owner_page=page;if(attr)h.attr_bad=1;else h.managed=1;
        if(at==0)assert(!sweet_pas_zap_owner_action(GPZO_SEAL));
        else if(at==1)assert(!sweet_pas_zap_owner_live(GPZ_COPY,low_pa));
        else assert(!sweet_pas_zap_copy(&out));
    }
    for(unsigned n=0;n<9;n++){
        setup();switch(n){case 0:h.zap=0;break;case 1:h.zap=11;break;case 2:h.init=1;break;case 3:h.mem=1;break;
        case 4:h.active=0;break;case 5:h.context=1;break;case 6:h.context=2;break;case 7:h.context=3;break;case 8:h.translation_bad=1;break;}
        assert(!sweet_pas_zap_owner_action(GPZO_SEAL)&&sweet_pas_zap_owner_state()==PSZ_IDLE);
    }
    before_copy();h.phase=GPZ_AUTH;assert(!sweet_pas_zap_owner_action(GPZO_AUTH_ACCEPT)&&sweet_pas_zap_owner_state()==PSZ_MEM_DONE);
    before_copy();struct gpz_copy saved={11,22};out=saved;h.active=0;assert(!sweet_pas_zap_copy(&out)&&!memcmp(&out,&saved,sizeof(out)));
    before_copy();assert(!sweet_pas_zap_copy((struct gpz_copy *)target)&&sweet_pas_zap_owner_state()==PSZ_MEM_DONE);
    before_copy();assert(!sweet_pas_zap_copy((struct gpz_copy *)code)&&sweet_pas_zap_owner_state()==PSZ_MEM_DONE);
    setup();h.missing_init=1;assert(sweet_pas_zap_owner_action(GPZO_SEAL));
    setup();target[0]^=1;assert(!sweet_pas_zap_owner_live(GPZ_SEAL,low_pa));
    /* New authenticated predicate reads geometry only, including PROT_NONE
     * throughout AUTH acceptance and all subsequent permission checks. */
    for(int mode=1;mode<=10;mode++){
        before_copy_mode(mode);assert(!sweet_pas_zap_owner_authenticated(low_pa));
        assert(sweet_pas_zap_copy(&out));h.phase=GPZ_AUTH;unsigned hashes=h.hashes;
        assert(!mprotect(target,16384,PROT_NONE));assert(sweet_pas_zap_owner_action(GPZO_AUTH_ACCEPT));
        h.active=0;h.phase=GPZ_IDLE;
        assert(sweet_pas_zap_owner_authenticated(low_pa)&&!sweet_pas_zap_owner_authenticated(low_pa+0x100000));
        for(unsigned state=PSZ_IDLE;state<=PSZ_FAILED;state++){
            psz_lifecycle=state;assert(sweet_pas_zap_owner_authenticated(low_pa)==(state==PSZ_AUTH_DONE));
        }
        psz_lifecycle=PSZ_AUTH_DONE;
        for(unsigned page=0;page<64;page++){
            h.owner_page=page;h.managed=1;assert(!sweet_pas_zap_owner_authenticated(low_pa));h.managed=0;
            h.attr_bad=1;assert(!sweet_pas_zap_owner_authenticated(low_pa));h.attr_bad=0;
        }
        for(unsigned context=1;context<=3;context++){h.context=context;assert(!sweet_pas_zap_owner_authenticated(low_pa));}h.context=0;
        h.translation_bad=1;assert(!sweet_pas_zap_owner_authenticated(low_pa));h.translation_bad=0;
        assert(sweet_pas_zap_owner_authenticated(low_pa)&&h.hashes==hashes);
    }
    assert(!mprotect(target,16384,PROT_READ|PROT_WRITE));assert(!munmap(allocation,49152));
    printf("ZAP actual owner: %u cases, all%u copy guards, all64 page attributes per phase, exact1984 byte copy/no tail clear, no MDT hash after INIT_ENTER, protected region after AUTH PASS\n",cases,guards);
}
