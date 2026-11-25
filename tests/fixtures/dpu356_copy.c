#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "gauguin_copy356.h"

static void panel_copy(void (*copy_row)(void *,const void *),unsigned char *dst,const unsigned char *src)
{
    for (unsigned y=0; y<SCAN352_HEIGHT; ++y)
        copy_row(dst+y*SCAN352_PANEL_STRIDE,src+y*SCAN352_SOURCE_STRIDE);
}

static uint64_t now_ns(void)
{
    struct timespec t;
    assert(clock_gettime(CLOCK_MONOTONIC,&t)==0);
    return (uint64_t)t.tv_sec*UINT64_C(1000000000)+(uint64_t)t.tv_nsec;
}

int main(void)
{
    const size_t source_bytes=SCAN352_SOURCE_STRIDE*SCAN352_HEIGHT;
    const size_t panel_bytes=SCAN352_PANEL_STRIDE*SCAN352_HEIGHT;
    unsigned char *source=NULL,*panel=NULL,*old=NULL;
    assert(posix_memalign((void **)&source,64,source_bytes+128)==0);
    assert(posix_memalign((void **)&panel,64,panel_bytes+128)==0);
    assert(posix_memalign((void **)&old,64,panel_bytes+128)==0);
    assert(SCAN352_PANEL_STRIDE%SCAN356_COPY_BLOCK_BYTES==0);
    for (size_t i=0; i<source_bytes+128; ++i) source[i]=(unsigned char)(i^(i>>9)^(i>>19));
    for (unsigned i=0; i<3; ++i) {
        size_t sx=8+16*i;
        unsigned char *start=source+sx;
        unsigned char *dst=panel+64;
        memset(panel,0xa5,panel_bytes+128);
        assert(scan352_copy_supported((uintptr_t)dst,(uintptr_t)start,1080,2400,4320,4608));
        panel_copy(scan356_copy_row,dst,start);
        for (unsigned y=0; y<SCAN352_HEIGHT; ++y)
            assert(!memcmp(dst+y*SCAN352_PANEL_STRIDE,start+y*SCAN352_SOURCE_STRIDE,SCAN352_PANEL_STRIDE));
        for (unsigned boundary=0; boundary<64; ++boundary) {
            assert(panel[boundary]==0xa5);
            assert(dst[panel_bytes+boundary]==0xa5);
        }
    }
    /* A local write-back mapping is an instruction-path comparison.
     * The phone's write-combined mapping is only measured in the trial. */
    for (int i=0; i<24; ++i) {
        uint64_t base_ns,new_ns,start;
        if (i%2) {
            start=now_ns();panel_copy(scan356_copy_row,panel,source+24);new_ns=now_ns()-start;
            start=now_ns();panel_copy(scan352_copy_row,old,source+24);base_ns=now_ns()-start;
        } else {
            start=now_ns();panel_copy(scan352_copy_row,old,source+24);base_ns=now_ns()-start;
            start=now_ns();panel_copy(scan356_copy_row,panel,source+24);new_ns=now_ns()-start;
        }
        assert(!memcmp(panel,old,panel_bytes));
        printf("%llu %llu\n",(unsigned long long)base_ns,(unsigned long long)new_ns);
    }
    free(old);
    free(panel);
    free(source);
    return 0;
}
