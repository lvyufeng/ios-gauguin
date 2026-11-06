#include "cmd_db_snapshot.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
/* Synthetic BINARY format model; levels separately checked against the actual
 * native text export by the runner. No real physical snapshot exists yet. */
static uint8_t blob[2048];
static const char *names[]={"cx.lvl","mx.lvl","gfx.lvl","xo.lvl"};
static const unsigned counts[]={7,8,8,4};
static const uint16_t levels[4][8]={
    {0,16,64,128,192,256,384}, {0,16,64,128,192,256,320,384},
    {0,64,128,192,256,320,384,416}, {0,32,80,128}};
static const uint32_t addresses[]={0x30000,0x30010,0x30050,0x300a0};
static void p16(uint8_t *p,uint16_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static void p32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(v>>(8*i));}
static void init(void)
{
    memset(blob,0,sizeof(blob));p32(blob,1);p32(blob+4,0x0c0330db);
    p16(blob+8,3);p16(blob+10,0);p16(blob+12,256);p16(blob+14,5);p16(blob+16,0x100);
    p16(blob+144+256,128); /* genuine zero-address cx.mol metadata */
    for(unsigned i=0;i<4;++i) {
        uint8_t *e=blob+144+24*i;memcpy(e,names[i],strlen(names[i]));p32(e+16,addresses[i]);
        p16(e+20,32);p16(e+22,(uint16_t)(2+32*i));
        for(unsigned j=0;j<counts[i];++j)p16(blob+144+256+2+32*i+2*j,levels[i][j]);
    }
    uint8_t *meta=blob+144+4*24;memcpy(meta,"cx.mol",6);p16(meta+20,2);
}
static void unchanged(enum ndb_result expected,size_t bytes,const char *name,size_t length)
{
    struct ndb_entry out,prior;memset(&out,0xa5,sizeof(out));memcpy(&prior,&out,sizeof(out));
    assert(ndb_lookup(blob,bytes,name,length,&out)==expected);
    assert(!memcmp(&out,&prior,sizeof(out)));
}
int main(void)
{
    struct ndb_entry e;struct ndb_arc_levels a;
    init();
    for(unsigned i=0;i<4;++i) {
        assert(ndb_lookup(blob,sizeof(blob),names[i],strlen(names[i]),&e)==NDB_OK);
        assert(e.address==addresses[i]&&e.owner_slave==3&&e.bank_version==0x100);
        assert(ndb_decode_arc(&e,&a)==NDB_OK&&a.count==counts[i]);
        for(unsigned j=0;j<a.count;++j)assert(a.value[j]==levels[i][j]);
    }
    assert(ndb_lookup(blob,sizeof(blob),"cx.mol",6,&e)==NDB_OK);
    assert(e.address==0&&e.owner_slave==3&&e.aux_length==2&&e.aux[0]==128&&e.aux[1]==0);
    assert(blob[144]=='c'&&blob[145]=='x'); /* debugfs wrong-bank bytes differ */
    assert(ndb_decode_arc(&e,&a)==NDB_NOT_ARC);
    unchanged(NDB_LENGTH,143,"cx.lvl",6);
    unchanged(NDB_LENGTH,NDB_MAX_BYTES+1,"cx.lvl",6);
    unchanged(NDB_ARGUMENT,sizeof(blob),"cx.lvl",0);
    unchanged(NDB_ARGUMENT,sizeof(blob),"123456789",9);
    unchanged(NDB_ARGUMENT,sizeof(blob),"cx\0lvl",6);
    unchanged(NDB_NOT_FOUND,sizeof(blob),"none.lvl",8);
    blob[4]^=1;unchanged(NDB_FORMAT,sizeof(blob),"cx.lvl",6);init();
    p32(blob,2);unchanged(NDB_UNSUPPORTED,sizeof(blob),"cx.lvl",6);init();
    p32(blob+140,1);unchanged(NDB_UNSUPPORTED,sizeof(blob),"cx.lvl",6);init();
    p16(blob+8,6);unchanged(NDB_UNSUPPORTED,sizeof(blob),"cx.lvl",6);init();
    p16(blob+10,65535);unchanged(NDB_LENGTH,sizeof(blob),"cx.lvl",6);init();
    p16(blob+14,65535);unchanged(NDB_CAPACITY,sizeof(blob),"cx.lvl",6);init();
    p16(blob+12,65535);unchanged(NDB_LENGTH,sizeof(blob),"cx.lvl",6);init();
    p16(blob+144+20,65535);unchanged(NDB_LENGTH,sizeof(blob),"cx.lvl",6);init();
    p16(blob+144+22,65535);unchanged(NDB_LENGTH,sizeof(blob),"cx.lvl",6);init();
    p16(blob+144+20,33);unchanged(NDB_CAPACITY,sizeof(blob),"cx.lvl",6);init();
    /* Bad unrelated entry is still rejected before publishing partial output. */
    p16(blob+144+4*24+22,65535);unchanged(NDB_LENGTH,sizeof(blob),"cx.lvl",6);init();
    /* Identical requested keys in another bank are ambiguous even if their
     * values match; aliases with different keys are not rejected wholesale. */
    p16(blob+24,4);p16(blob+26,128);p16(blob+28,256);p16(blob+30,1);
    memcpy(blob+144+128,blob+144,24);
    unchanged(NDB_AMBIGUOUS,sizeof(blob),"cx.lvl",6);init();
    assert(ndb_lookup(blob,sizeof(blob),"cx.lvl",6,&e)==NDB_OK);
    for(unsigned bad=0;bad<8;++bad) {
        struct ndb_entry changed=e;struct ndb_arc_levels before;
        memset(&a,0xa5,sizeof(a));memcpy(&before,&a,sizeof(a));
        switch(bad) {
        case 0:changed.address=0;break;
        case 1:changed.owner_slave=4;break;
        case 2:changed.address=0x40000;break;
        case 3:changed.address++;break;
        case 4:changed.aux_length=31;break;
        case 5:changed.aux_length=34;break;
        case 6:p16(changed.aux+4,16);break; /* duplicate level */
        case 7:p16(changed.aux+2,0);break; /* gap before nonzero */
        }
        assert(ndb_decode_arc(&changed,&a)!=NDB_OK);
        assert(!memcmp(&before,&a,sizeof(a)));
    }
    e.aux_length=4;p16(e.aux,16);p16(e.aux+2,64);
    assert(ndb_decode_arc(&e,&a)==NDB_OK&&a.count==2&&a.value[0]==16); /* native no-OFF resource */
    uint32_t seed=1;
    for(unsigned i=0;i<5000;++i) {
        init();seed=seed*1664525+1013904223;size_t at=seed%sizeof(blob);
        blob[at]^=(uint8_t)(seed>>24);size_t n=(seed>>13)%(sizeof(blob)+1);
        struct ndb_entry before;memset(&e,0xa5,sizeof(e));memcpy(&before,&e,sizeof(e));
        enum ndb_result rc=ndb_lookup(blob,n,"cx.lvl",6,&e);
        if(rc!=NDB_OK)assert(!memcmp(&before,&e,sizeof(e)));
    }
    puts("PASS: actual bounded binary parser; synthetic multi-bank/zero-address model, ARC tables, malformed ranges/duplicates/padding,5000 bounded mutations; no hardware snapshot or vote");
}
