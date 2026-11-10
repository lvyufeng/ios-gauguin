#include <stdint.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define GAUGUIN 1
#define NSEC_PER_SEC UINT64_C(1000000000)
#define Z_WAITOK 1
#define Z_ZERO 2
typedef struct {uint32_t numer,denom;} mach_timebase_info_data_t;
static uint64_t board_ticks=1000000;
static uint32_t selector;
static bool desktop=true,allocation_fails;
static unsigned allocations,frees,clocks;
static bool PE_parse_boot_argn(const char *key,void *out,int size)
{assert(!strcmp(key,"sweettrace")&&size==4);memcpy(out,&selector,4);return selector!=0;}
static bool sweet_metal_desktop_enabled(void){return desktop;}
static uint64_t mach_absolute_time(void){clocks++;return board_ticks;}
static void nanoseconds_to_absolutetime(uint64_t n,uint64_t *v){*v=(n/125)*3;}
static void clock_timebase_info(mach_timebase_info_data_t *p){*p=(mach_timebase_info_data_t){125,3};}
static void *kalloc_data(size_t n,int flags){assert(n==4096*64&&flags==3);allocations++;return allocation_fails?NULL:calloc(1,n);}
static void kfree_data(void *p,size_t n){assert(n==4096*64);frees++;free(p);}
