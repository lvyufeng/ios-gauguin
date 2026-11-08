/* The actual board parameter function and actual config table; typed READY
 * boundary only. A returned aperture is configured state, never measured RAM. */
#include <assert.h>
#include <stdio.h>
#include "gauguin_gpu_core.h"
static bool ready;
static unsigned queries,checks;
static bool sweet_gpu_runtime_ready(void){++queries;return ready;}
#define CHECK(x) do{++checks;assert(x);}while(0)
@PARAMETER@
int main(void)
{
    uint64_t value=0xa5a5;
    CHECK(!sweet_gpu_runtime_parameter(6,&value)&&value==0xa5a5&&queries==1);
    ready=true;queries=0;
    CHECK(!sweet_gpu_runtime_parameter(6,NULL)&&!queries);
    CHECK(sweet_gpu_runtime_parameter(6,&value)&&value==0x100000&&queries==1);
    CHECK(sweet_gpu_runtime_parameter(2,&value)&&value==512*1024);
    CHECK(sweet_gpu_runtime_parameter(1,&value)&&value==619);
    CHECK(sweet_gpu_runtime_parameter(3,&value)&&value==0x06010900);
    CHECK(sweet_gpu_runtime_parameter(7,&value)&&value==1);
    value=123;
    for(unsigned p=0;p<32;p++)if(p!=1&&p!=2&&p!=3&&p!=6&&p!=7)
        CHECK(!sweet_gpu_runtime_parameter(p,&value)&&value==123);
    ready=false;queries=0;
    for(unsigned p=0;p<32;p++)CHECK(!sweet_gpu_runtime_parameter(p,&value)&&value==123);
    CHECK(queries==32);
    printf("PASS: %u actual GMEM/identity parameter checks; READY-gated config state, host-only\n",checks);
}
