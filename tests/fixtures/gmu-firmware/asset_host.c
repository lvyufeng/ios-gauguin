#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <CommonCrypto/CommonDigest.h>
#include "gauguin_gmu_asset.h"
#define GAUGUIN 1
#define kBootArgsVersion2 2
#define kSuccess 0
typedef uintptr_t vm_offset_t;typedef unsigned DTEntry;
typedef struct {unsigned Version;uint64_t physBase,memSize,topOfKernelData;} boot_args;
typedef CC_SHA256_CTX SHA256_CTX;
static void SHA256_Init(SHA256_CTX *c){assert(CC_SHA256_Init(c));}
static void SHA256_Update(SHA256_CTX *c,const void *data,size_t n){assert(n==32768&&CC_SHA256_Update(c,data,(CC_LONG)n));}
static void SHA256_Final(uint8_t *d,SHA256_CTX *c){assert(CC_SHA256_Final(d,c));}
unsigned long gPhysBase=0x180000000ul,real_phys_size=0x2000000ul;
vm_offset_t arm_vm_kernelcache_phys_end;
static boot_args args;static struct {boot_args *bootArgs;} PE_state={&args};
static _Alignas(16384) uint8_t image[32768];static uint8_t original[32768];
static uint64_t descriptor[2],emitted[2];static unsigned missing,propbad,mapbad,reads,cases;
static int SecureDTLookupEntry(void *root,const char *path,DTEntry *out)
{assert(!root&&!strcmp(path,"/chosen/memory-map"));if(missing==1)return -1;*out=1;return 0;}
static int SecureDTGetProperty(DTEntry node,const char *name,const void **out,unsigned *n)
{assert(node==1&&!strcmp(name,"A619GMUFirmware"));if(missing==2)return -1;*out=propbad==1?NULL:descriptor;*n=propbad==2?15:16;return 0;}
static vm_offset_t ml_static_ptovirt(vm_offset_t pa)
{
    ++reads;assert(pa==descriptor[0]||pa==descriptor[0]+32767);
    if(mapbad==1)return 0;
    if(mapbad==2)return UINTPTR_MAX-1;
    if(mapbad==3&&pa!=descriptor[0])return (vm_offset_t)image+32768;
    return (vm_offset_t)image+pa-descriptor[0];
}
@SOURCE@
static void reset(void)
{
    ++cases;args=(boot_args){2,gPhysBase,real_phys_size,emitted[0]+0x10000};PE_state.bootArgs=&args;
    arm_vm_kernelcache_phys_end=emitted[0];memcpy(descriptor,emitted,sizeof(emitted));
    memcpy(image,original,sizeof(image));missing=propbad=mapbad=reads=0;
}
static void bad(void)
{struct gma_view v,b;memset(&v,0xa5,sizeof(v));b=v;assert(!sweet_gmu_asset_view(&v)&&!memcmp(&v,&b,sizeof(v)));}
int main(int argc,char **argv)
{
    assert(argc==3);FILE *f=fopen(argv[1],"rb");assert(f&&fread(emitted,1,16,f)==16&&fgetc(f)==EOF);fclose(f);
    f=fopen(argv[2],"rb");assert(f&&fread(original,1,32768,f)==32768&&fgetc(f)==EOF);fclose(f);
    reset();struct gma_view v;assert(sweet_gmu_asset_view(&v)&&v.pa==emitted[0]&&v.bytes==32768&&v.data==image&&reads==2);
    assert(!sweet_gmu_asset_view(NULL));
    for(unsigned n=0;n<18;n++){
        reset();switch(n){
        case 0:PE_state.bootArgs=NULL;break;case 1:args.Version=1;break;
        case 2:args.physBase++;break;case 3:args.memSize=0;break;
        case 4:args.memSize=real_phys_size+1;break;case 5:args.topOfKernelData++;break;
        case 6:arm_vm_kernelcache_phys_end=args.topOfKernelData+1;break;
        case 7:descriptor[0]++;break;case 8:descriptor[1]=32767;break;
        case 9:descriptor[1]=32769;break;case 10:descriptor[0]=arm_vm_kernelcache_phys_end-16384;break;
        case 11:descriptor[0]=args.topOfKernelData-16384;break;
        case 12:missing=1;break;case 13:missing=2;break;
        case 14:propbad=1;break;case 15:propbad=2;break;
        case 16:image[0]^=1;break;case 17:image[32767]^=1;break;
        }bad();
    }
    for(unsigned n=1;n<=3;n++){reset();mapbad=n;bad();}
    reset();assert(sweet_gmu_asset_view(&v));
    printf("GMU asset consumer: %u real-SHA256/bounds/descriptor cases PASS\n",cases);
}
