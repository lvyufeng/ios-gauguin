#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <CommonCrypto/CommonDigest.h>
#include "gauguin_gpu_sqe_asset.h"
#define GAUGUIN 1
#define kBootArgsVersion2 2
#define kSuccess 0
typedef uintptr_t vm_offset_t;typedef unsigned DTEntry;
typedef struct {unsigned Version;uint64_t physBase,memSize,topOfKernelData;} boot_args;
typedef CC_SHA256_CTX SHA256_CTX;
static void SHA256_Init(SHA256_CTX *c){assert(CC_SHA256_Init(c));}
static void SHA256_Update(SHA256_CTX *c,const void *data,size_t n){assert(n==32304&&CC_SHA256_Update(c,data,(CC_LONG)n));}
static void SHA256_Final(uint8_t *d,SHA256_CTX *c){assert(CC_SHA256_Final(d,c));}
unsigned long gPhysBase=0x180000000ul,real_phys_size=0x2000000ul;
vm_offset_t arm_vm_kernelcache_phys_end;
static boot_args args;static struct {boot_args *bootArgs;} PE_state={&args};
static _Alignas(16384) uint8_t image[32768];static uint8_t original[32768];
static uint64_t descriptor[4][2],emitted[4][2];
static unsigned missing,propbad,indexbad,mapbad,reads,cases;
static int SecureDTLookupEntry(void *root,const char *path,DTEntry *out)
{assert(!root&&!strcmp(path,"/chosen/memory-map"));if(missing==1)return -1;*out=1;return 0;}
static int SecureDTGetProperty(DTEntry node,const char *name,const void **out,unsigned *n)
{
    static const char *const names[]={"A630SQEFirmware","NovatekFirmware","A615ZapMDT","A619GMUFirmware"};
    assert(node==1);unsigned i;for(i=0;i<4;i++)if(!strcmp(name,names[i]))break;assert(i<4);
    if(missing==2+i)return -1;*out=propbad==1&&indexbad==i?NULL:descriptor[i];*n=propbad==2&&indexbad==i?15:16;return 0;
}
static vm_offset_t ml_static_ptovirt(vm_offset_t pa)
{
    ++reads;assert(pa==descriptor[0][0]||pa==descriptor[0][0]+32767);
    if(mapbad==1)return 0;if(mapbad==2)return UINTPTR_MAX-1;
    if(mapbad==3&&pa!=descriptor[0][0])return (vm_offset_t)image+32768;
    return (vm_offset_t)image+pa-descriptor[0][0];
}
@SOURCE@
static void reset(void)
{
    ++cases;gPhysBase=0x180000000ul;real_phys_size=0x2000000ul;
    args=(boot_args){2,gPhysBase,real_phys_size,emitted[0][0]+0x10000};PE_state.bootArgs=&args;
    arm_vm_kernelcache_phys_end=emitted[1][0];memcpy(descriptor,emitted,sizeof(emitted));
    memcpy(image,original,sizeof(image));missing=propbad=mapbad=reads=0;indexbad=5;
}
static void bad(void)
{struct gsa_view v,b;memset(&v,0xa5,sizeof(v));b=v;assert(!sweet_gpu_sqe_asset_view(&v)&&!memcmp(&v,&b,sizeof(v)));}
int main(int argc,char **argv)
{
    assert(argc==3);FILE *f=fopen(argv[1],"rb");assert(f&&fread(emitted,1,sizeof(emitted),f)==sizeof(emitted)&&fgetc(f)==EOF);fclose(f);
    f=fopen(argv[2],"rb");assert(f&&fread(original,1,32304,f)==32304&&fgetc(f)==EOF);fclose(f);
    reset();struct gsa_view v;assert(sweet_gpu_sqe_asset_view(&v)&&v.pa==emitted[0][0]&&v.bytes==32304&&v.data==image&&reads==2);
    assert(!sweet_gpu_sqe_asset_view(NULL));
    for(unsigned n=0;n<24;n++){
        reset();switch(n){
        case 0:PE_state.bootArgs=NULL;break;case 1:args.Version=1;break;
        case 2:args.physBase++;break;case 3:args.memSize=0;break;
        case 4:args.memSize=real_phys_size+1;break;case 5:args.topOfKernelData++;break;
        case 6:arm_vm_kernelcache_phys_end=args.topOfKernelData+1;break;
        case 7:descriptor[0][0]++;break;case 8:descriptor[0][1]=32303;break;
        case 9:descriptor[0][1]=32305;break;case 10:descriptor[0][0]=arm_vm_kernelcache_phys_end-16384;break;
        case 11:descriptor[0][0]=args.topOfKernelData-16384;break;
        case 12:missing=1;break;case 13:missing=2;break;
        case 14:propbad=1;indexbad=0;break;case 15:propbad=2;indexbad=0;break;
        case 16:image[0]^=1;break;case 17:image[32303]^=1;break;
        case 18:image[32304]=1;break;case 19:image[32767]=1;break;
        case 20:args.topOfKernelData=args.physBase-16384;break;
        case 21:real_phys_size=UINT64_MAX;break;case 22:args.topOfKernelData=args.physBase+args.memSize+16384;break;
        case 23:arm_vm_kernelcache_phys_end=args.physBase-1;break;
        }bad();
    }
    for(unsigned i=1;i<4;i++)for(unsigned n=0;n<7;n++){
        reset();switch(n){
        case 0:missing=2+i;break;case 1:propbad=1;indexbad=i;break;case 2:propbad=2;indexbad=i;break;
        case 3:descriptor[i][1]--;break;case 4:descriptor[i][0]++;break;
        case 5:descriptor[0][0]=descriptor[i][0];break;case 6:descriptor[i][0]=0;break;
        }bad();
    }
    reset();descriptor[2][0]=descriptor[1][0]+147456-16384;bad();
    for(unsigned n=1;n<=3;n++){reset();mapbad=n;bad();}
    reset();args.topOfKernelData=emitted[0][0]+32768;args.memSize=args.topOfKernelData-args.physBase;
    assert(sweet_gpu_sqe_asset_view(&v));
    printf("SQE asset consumer: %u real-SHA256/padding/bounds/disjoint-descriptor cases PASS\n",cases);
}
