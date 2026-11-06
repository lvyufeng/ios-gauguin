#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
typedef uintptr_t vm_offset_t;
static vm_offset_t gicd_base;
static unsigned translations,bad_translation,reads,barriers;
static uint32_t words[3];
static vm_offset_t ml_vtophys(vm_offset_t va)
{
    ++translations;return UINT64_C(0x17a00000)+va-gicd_base+(translations==bad_translation);
}
static uint32_t gicd_read32(unsigned offset)
{assert(offset==0x120||offset==0x128||offset==0x130);++reads;return words[(offset-0x120)/8];}
static void read_barrier(void){++barriers;}
@SOURCE@
static void reset(void)
{gicd_base=0x100000000;translations=bad_translation=reads=barriers=0;memset(words,0,sizeof(words));}
int main(void)
{
    static const uint32_t masks[3]={0xa0,0x30000,0xff000};unsigned cases=0;
    for(unsigned w=0;w<3;w++)for(unsigned bit=0;bit<32;bit++){
        reset();words[w]=1u<<bit;uint32_t out[3]={1,2,3};
        assert(sweet_gmu_irq_quiet(out)==!(words[w]&masks[w]));
        assert(!memcmp(out,words,sizeof(words))&&reads==3&&barriers==3);++cases;
    }
    for(unsigned i=1;i<=4;i++){
        reset();bad_translation=i;uint32_t out[3]={1,2,3};
        assert(!sweet_gmu_irq_quiet(out)&&out[0]==1&&out[1]==2&&out[2]==3);++cases;
    }
    reset();gicd_base=0;uint32_t out[3]={1,2,3};assert(!sweet_gmu_irq_quiet(out)&&!reads);
    reset();assert(!sweet_gmu_irq_quiet(NULL)&&!reads);
    printf("GMU/SMMU actual GIC NS helper: %u bit/address cases PASS\n",cases+2);
}
