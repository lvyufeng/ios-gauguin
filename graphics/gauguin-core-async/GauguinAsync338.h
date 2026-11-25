#ifndef GAUGUIN_ASYNC338_H
#define GAUGUIN_ASYNC338_H
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static unsigned gn338_records;
static int gauguin_async338_scope(double created) {
    const char *name=getprogname(),*mode=getenv("GAUGUIN_EAGL_MODE");
    return created>=220 && created<270 && name && !strcmp(name,"backboardd") &&
        getuid()==501 && geteuid()==501 && mode && !strcmp(mode,"edr-default318");
}
static uint64_t gauguin_async338_us(double seconds) {
    /* Exact same printf rounding as the independent C4 lifecycle key. */
    char text[32];snprintf(text,sizeof(text),"%.0f",seconds*1e6);
    return strtoull(text,NULL,10);
}
static void gauguin_async338_notice(const void *object,double made,double now,unsigned state) {
    if (!object || !gauguin_async338_scope(made) || !(now>=made && now<900)) return;
    unsigned n=__atomic_load_n(&gn338_records,__ATOMIC_RELAXED);
    do { if (n>4096) return; }
    while (!__atomic_compare_exchange_n(&gn338_records,&n,n+1,1,__ATOMIC_RELAXED,__ATOMIC_RELAXED));
    if (n==4096) {fputs("GAUGUIN N338: limit=4096 coverage=incomplete\n",stderr);return;}
    fprintf(stderr,"GAUGUIN N338: object=%p made_us=%.0f tick_us=%.0f state=%u\n",object,made*1e6,now*1e6,state);
}
#endif
