#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <CommonCrypto/CommonDigest.h>
#include "gauguin_gpu_zap_asset.h"
#define GAUGUIN 1
#define kBootArgsVersion2 2
#define kSuccess 0
typedef uintptr_t vm_offset_t;typedef unsigned DTEntry;
typedef struct {unsigned Version;uint64_t physBase,memSize,topOfKernelData;} boot_args;
typedef CC_SHA256_CTX SHA256_CTX;
static unsigned hashes;
static void SHA256_Init(SHA256_CTX *c){assert(CC_SHA256_Init(c));}
static void SHA256_Update(SHA256_CTX *c,const void *data,size_t n){++hashes;assert(n==1984&&CC_SHA256_Update(c,data,(CC_LONG)n));}
static void SHA256_Final(uint8_t *d,SHA256_CTX *c){assert(CC_SHA256_Final(d,c));}
unsigned long gPhysBase=0x180000000ul,real_phys_size=0x2000000ul;
vm_offset_t arm_vm_kernelcache_phys_end;
static boot_args args;static struct {boot_args *bootArgs;} PE_state={&args};
static _Alignas(16384) uint8_t image[16384];static uint8_t original[16384];
static uint64_t descriptor[5][2],emitted[5][2];
static unsigned missing,propbad,indexbad,mapbad,reads,cases;
static int SecureDTLookupEntry(void *root,const char *path,DTEntry *out)
{assert(!root&&!strcmp(path,"/chosen/memory-map"));if(missing==1)return -1;*out=1;return 0;}
static int SecureDTGetProperty(DTEntry node,const char *name,const void **out,unsigned *n)
{
    static const char *const names[]={"A615ZapCode","NovatekFirmware","A615ZapMDT","A619GMUFirmware","A630SQEFirmware"};
    assert(node==1);unsigned i;for(i=0;i<5;i++)if(!strcmp(name,names[i]))break;assert(i<5);
    if(missing==2+i)return -1;*out=propbad==1&&indexbad==i?NULL:descriptor[i];*n=propbad==2&&indexbad==i?15:16;return 0;
}
static vm_offset_t ml_static_ptovirt(vm_offset_t pa)
{
    ++reads;assert(pa==descriptor[0][0]||pa==descriptor[0][0]+16383);
    if(mapbad==1)return 0;if(mapbad==2)return UINTPTR_MAX-1;
    if(mapbad==3&&pa!=descriptor[0][0])return (vm_offset_t)image+16384;
    if(mapbad==4&&pa!=descriptor[0][0])return 0;
    return (vm_offset_t)image+pa-descriptor[0][0];
}
@SOURCE@
static void reset(void)
{
    ++cases;gPhysBase=0x180000000ul;real_phys_size=0x2000000ul;
    args=(boot_args){2,gPhysBase,real_phys_size,emitted[0][0]+0x10000};PE_state.bootArgs=&args;
    arm_vm_kernelcache_phys_end=emitted[1][0];memcpy(descriptor,emitted,sizeof(emitted));
    memcpy(image,original,sizeof(image));missing=propbad=mapbad=reads=hashes=0;indexbad=6;
}
static void bad(bool before_map)
{
    struct gza_view v,b;uint8_t frozen[16384];memcpy(frozen,image,sizeof(image));
    memset(&v,0xa5,sizeof(v));b=v;
    assert(!sweet_gpu_zap_asset_view(&v)&&!memcmp(&v,&b,sizeof(v)));
    assert(!memcmp(frozen,image,sizeof(image)));if(before_map)assert(!reads&&!hashes);
}
int main(int argc,char **argv)
{
    static const uint64_t reserved[]={16384,147456,16384,32768,32768};
    assert(argc==3);FILE *f=fopen(argv[1],"rb");assert(f&&fread(emitted,1,sizeof(emitted),f)==sizeof(emitted)&&fgetc(f)==EOF);fclose(f);
    f=fopen(argv[2],"rb");assert(f&&fread(original,1,1984,f)==1984&&fgetc(f)==EOF);fclose(f);
    reset();struct gza_view v;assert(sweet_gpu_zap_asset_view(&v)&&v.pa==emitted[0][0]&&v.bytes==1984&&v.data==image&&reads==2&&hashes==1);
    assert(!memcmp(image,original,sizeof(image)));assert(!sweet_gpu_zap_asset_view(NULL));
    for(unsigned n=0;n<28;n++){
        reset();switch(n){
        case 0:PE_state.bootArgs=NULL;break;case 1:args.Version=1;break;
        case 2:args.physBase++;break;case 3:args.memSize=0;break;
        case 4:args.memSize=real_phys_size+1;break;case 5:args.topOfKernelData++;break;
        case 6:arm_vm_kernelcache_phys_end=args.topOfKernelData+1;break;
        case 7:descriptor[0][0]++;break;case 8:descriptor[0][1]=1983;break;
        case 9:descriptor[0][1]=1985;break;case 10:descriptor[0][0]=arm_vm_kernelcache_phys_end-16384;break;
        case 11:descriptor[0][0]=args.topOfKernelData;break;
        case 12:missing=1;break;case 13:missing=2;break;
        case 14:propbad=1;indexbad=0;break;case 15:propbad=2;indexbad=0;break;
        case 16:args.topOfKernelData=args.physBase-16384;break;
        case 17:real_phys_size=UINT64_MAX;break;case 18:args.topOfKernelData=args.physBase+args.memSize+16384;break;
        case 19:arm_vm_kernelcache_phys_end=args.physBase-1;break;
        case 20:descriptor[0][0]=UINT64_MAX-16383;break;
        case 21:args.topOfKernelData=emitted[0][0];break;
        case 22:real_phys_size=0;break;case 23:descriptor[0][0]=0;break;
        case 24:descriptor[0][1]=16384;break;case 25:args.physBase=gPhysBase=0;break;
        case 26:{uint64_t delta=gPhysBase-UINT64_C(0x80000000);
            args.physBase=gPhysBase=0x80000000;args.topOfKernelData-=delta;arm_vm_kernelcache_phys_end-=delta;
            for(unsigned i=0;i<5;i++)descriptor[i][0]-=delta;break;}
        case 27:args.memSize=real_phys_size=0x4000;args.topOfKernelData=gPhysBase+0x4000;arm_vm_kernelcache_phys_end=gPhysBase;break;
        }bad(true);
    }
    for(unsigned i=1;i<5;i++)for(unsigned n=0;n<10;n++){
        reset();switch(n){
        case 0:missing=2+i;break;case 1:propbad=1;indexbad=i;break;case 2:propbad=2;indexbad=i;break;
        case 3:descriptor[i][1]--;break;case 4:descriptor[i][0]++;break;
        case 5:descriptor[0][0]=descriptor[i][0];break;case 6:descriptor[i][0]=0;break;
        case 7:descriptor[i][0]=args.topOfKernelData;break;
        case 8:descriptor[i][0]=UINT64_MAX-16383;break;
        case 9:descriptor[0][0]=descriptor[i][0]+reserved[i]-16384;break;
        }bad(true);
    }
    for(unsigned i=1;i<5;i++)for(unsigned j=1;j<i;j++){
        reset();descriptor[i][0]=descriptor[j][0]+reserved[j]-16384;bad(true);
    }
    for(unsigned n=1;n<=4;n++){reset();mapbad=n;bad(false);}
    for(unsigned n=0;n<4;n++){
        reset();static const unsigned offsets[]={0,1983,1984,16383};image[offsets[n]]^=1;bad(false);
    }
    reset();args.topOfKernelData=emitted[0][0]+16384;args.memSize=args.topOfKernelData-args.physBase;
    assert(sweet_gpu_zap_asset_view(&v)&&!memcmp(image,original,sizeof(image)));
    printf("ZAP b02 asset: %u real-SHA256/padding/bounds/five-descriptor cases PASS\n",cases);
}
