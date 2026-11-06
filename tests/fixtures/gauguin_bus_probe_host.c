/* Actual worker host fixture. Only platform calls, aligned MMIO-load/barrier,
 * and native SHA are seamed; real parser and planner are linked unchanged.
 * No hardware access, assembly, executable rewriting, or home-grown crypto.
 * Python supplies the real SHA of the immutable positive synthetic DB. */
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include "cmd_db_snapshot.h"
#include "gauguin_bcm_plan.h"

#define GAUGUIN 1
#define KERN_SUCCESS 0
#define PAGE_SHIFT 14
#define PAGE_SIZE ((vm_size_t)1 << PAGE_SHIFT)
#define VM_PROT_READ 1
#define SHA256_DIGEST_LENGTH 32
#define SHA256_DIGEST_STRING_LENGTH 65
typedef uintptr_t vm_offset_t;
typedef size_t vm_size_t;
typedef int kern_return_t;
typedef int wait_result_t;
typedef uint32_t ppnum_t;
typedef int boolean_t;
typedef uint32_t vm_prot_t;
typedef void *thread_t;
typedef void (*thread_continue_t)(void *, wait_result_t);
typedef struct { uint8_t digest[32]; unsigned updates; } SHA256_CTX;
#define CHECK(c, why) do { if (!(c)) { \
    fprintf(stderr, "FAIL line %d [%s]: %s\n", __LINE__, case_name, why); \
    exit(1); } } while (0)
#define DB_BYTES 131072u
#define DB_PA UINT32_C(0x80860000)
#define RSC_PA UINT32_C(0x18220000)
#define RSC_BYTES 0x4000u
#define FAKE_BASE UINT64_C(0x100000000)
#define LOG_LINES 4096u
#define READS_MAX 1200u
static const char *case_name = "setup";
static unsigned cases;
static uint8_t positive_db[DB_BYTES], db[2][DB_BYTES], positive_digest[32];
static uint32_t rsc[2][RSC_BYTES / 4];
struct expected_read { uint32_t offset, value; };
static struct {
    int enabled, touchmode, thread_error, context, delayed_context;
    unsigned starts, deallocations, terminations, sleeps, allocations;
    unsigned allocation_failure, map_failure, map_count, translate_failure;
    unsigned translations[2];
    unsigned managed_page, wrong_attr_page, pmap_checks[9];
    unsigned db_loads, rsc_loads, shas, positive_sha;
    unsigned markers, flushes, lines;
    char log[LOG_LINES][224];
    void *allocation;
    size_t allocation_size;
    thread_continue_t worker;
    uint32_t initial_config;
    struct expected_read expected[READS_MAX];
    unsigned expected_count;
} mock;

static void put16(uint8_t *p, unsigned v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v)
{ for (unsigned i=0;i<4;++i) p[i]=(uint8_t)(v>>(8*i)); }
static uint32_t get32(const uint8_t *p)
{ return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void entry(uint8_t *p, const char *name, uint32_t addr, unsigned len, unsigned off)
{
    CHECK(strlen(name)<=8,"entry name fits");
    memcpy(p,name,strlen(name)); put32(p+16,addr); put16(p+20,len); put16(p+22,off);
}
static void make_positive_db(void)
{
    static const char *const arc_names[]={"cx.lvl","mx.lvl","gfx.lvl","xo.lvl"};
    static const uint32_t arc_addr[]={0x30000,0x30010,0x30050,0x300a0};
    static const uint16_t levels[4][8]={
        {0,16,64,128,192,256,384,0}, {0,16,64,128,192,256,320,384},
        {0,64,128,192,256,320,384,416}, {0,32,80,128,0,0,0,0}};
    /* Independent board constants: do not construct fixtures from planner tables. */
    static const char *const names[]={"MC0","SH0","SN0","SN6","CE0","ACV"};
    static const uint32_t addr[]={0x50000,0x50004,0x5002c,0x50044,0x5006c,0x50080};
    static const uint32_t unit[]={2050000,3650000,530000,530000,7935,1};
    static const uint16_t width[]={16,32,16,16,8,0};
    static const uint8_t vcd[]={0,1,3,3,6,11};
    memset(positive_db,0,sizeof(positive_db));
    put32(positive_db,1); put32(positive_db+4,0x0c0330db);
    put16(positive_db+8,3); put16(positive_db+10,0); put16(positive_db+12,240);
    put16(positive_db+14,4); put16(positive_db+16,0x100);
    put16(positive_db+24,5); put16(positive_db+26,96); put16(positive_db+28,304);
    put16(positive_db+30,6); put16(positive_db+32,0x200);
    for (unsigned i=0;i<4;++i) {
        entry(positive_db+144+24*i,arc_names[i],arc_addr[i],16,16*i);
        for (unsigned j=0;j<8;++j) put16(positive_db+384+16*i+2*j,levels[i][j]);
    }
    for (unsigned i=0;i<6;++i) {
        entry(positive_db+240+24*i,names[i],addr[i],8,8*i);
        put32(positive_db+448+8*i,unit[i]); put16(positive_db+452+8*i,width[i]);
        positive_db[454+8*i]=vcd[i];
    }
}
static unsigned page_index(ppnum_t pn)
{
    if (pn >= (DB_PA>>PAGE_SHIFT) && pn < (DB_PA>>PAGE_SHIFT)+8)
        return pn-(DB_PA>>PAGE_SHIFT);
    CHECK(pn==(RSC_PA>>PAGE_SHIFT),"only nine known physical pages checked");
    return 8;
}
static int test_printf(const char *fmt,...)
{
    va_list ap; int n;
    CHECK(mock.lines<LOG_LINES,"bounded log");
    va_start(ap,fmt); n=vsnprintf(mock.log[mock.lines],sizeof(mock.log[0]),fmt,ap); va_end(ap);
    CHECK(n>0 && (size_t)n<sizeof(mock.log[0]),"one bounded record");
    CHECK(mock.log[mock.lines][n-1]=='\n',"newline record");
    ++mock.lines; return n;
}
bool PE_parse_boot_argn(const char *key,void *value,size_t len)
{
    CHECK(len==sizeof(int),"boot argument integer");
    if (!strcmp(key,"sweetbusprobe")) *(int*)value=mock.enabled;
    else { CHECK(!strcmp(key,"sweettouchmode"),"known boot arg"); *(int*)value=mock.touchmode; }
    return true;
}
kern_return_t kernel_thread_start(thread_continue_t fn,void *arg,thread_t *thread)
{
    CHECK(!arg,"null worker argument"); ++mock.starts;
    if (mock.thread_error) return mock.thread_error;
    mock.worker=fn; *thread=(thread_t)(uintptr_t)1; return KERN_SUCCESS;
}
void thread_deallocate(thread_t thread)
{ CHECK(thread==(thread_t)(uintptr_t)1,"known worker thread"); ++mock.deallocations; }
void thread_terminate_self(void) { ++mock.terminations; }
int ml_get_interrupts_enabled(void) { return mock.context!=1; }
int ml_at_interrupt_context(void) { return mock.context==2; }
int get_preemption_level(void) { return mock.context==3 ? 1:0; }
void IOSleep(unsigned ms)
{
    CHECK(ms==1000 && mock.sleeps<45,"45 one-second sleeps");
    CHECK(!mock.allocations && !mock.map_count && !mock.db_loads,"delay before allocation or mapping");
    CHECK(mock.markers==1 && mock.flushes==1,"delay marker persisted");
    if (++mock.sleeps==45) mock.context=mock.delayed_context;
}
void *IOMalloc(size_t size)
{
    CHECK(mock.sleeps==45 && !mock.allocations && !mock.map_count,"one allocation after delay");
    CHECK(size>2*DB_BYTES && size<2*DB_BYTES+16384,"bounded value storage");
    ++mock.allocations;
    if (mock.allocation_failure) return NULL;
    mock.allocation=calloc(1,size); mock.allocation_size=size;
    CHECK(mock.allocation,"host allocation"); return mock.allocation;
}
void sweet_log_mark_sync(const char *s)
{
    CHECK(!strncmp(s,"SWEET BUS: ",11) || !strncmp(s,"SWEET CMDB ",11),"marker namespace");
    CHECK(mock.lines && strlen(s)+1==strlen(mock.log[mock.lines-1]) &&
        !strncmp(s,mock.log[mock.lines-1],strlen(s)),"marker matches console record");
    CHECK(mock.markers==mock.flushes,"previous marker flushed"); ++mock.markers;
}
void sweet_log_flush_now(void)
{ CHECK(mock.markers==mock.flushes+1,"one flush per marker"); ++mock.flushes; }
boolean_t pmap_valid_page(ppnum_t pn)
{ unsigned i=page_index(pn); ++mock.pmap_checks[i]; return mock.managed_page==i+1; }
unsigned int pmap_cache_attributes(ppnum_t pn)
{ unsigned i=page_index(pn); return mock.wrong_attr_page==i+1 ? 6:0xd0000007u; }
vm_offset_t ml_io_map_with_prot(vm_offset_t pa,vm_size_t bytes,vm_prot_t prot)
{
    unsigned id=pa==DB_PA ? 0:1;
    CHECK(pa==DB_PA || pa==RSC_PA,"fixed physical map only");
    CHECK(bytes==(id ? RSC_BYTES:DB_BYTES) && prot==VM_PROT_READ,"exact extent read only");
    CHECK(mock.allocations==1 && mock.allocation,"storage before map");
    CHECK(mock.markers==mock.flushes && mock.markers>0,"map marker flushed");
    CHECK(mock.map_count==id,"CMDDB map then RSC, no retries");
    for (unsigned i=id ? 8:0;i<(id ? 9:8);++i)
        CHECK(mock.pmap_checks[i]==1,"pmap precheck before map");
    if (id) CHECK(mock.db_loads==65536,"RSC only after both complete copies");
    ++mock.map_count;
    return mock.map_failure==id+1 ? 0:(vm_offset_t)(FAKE_BASE+pa);
}
vm_offset_t ml_vtophys(vm_offset_t va)
{
    uint64_t pa=va-FAKE_BASE;
    unsigned id=(pa==DB_PA || pa==DB_PA+DB_BYTES-1) ? 0:1;
    CHECK(pa==DB_PA || pa==DB_PA+DB_BYTES-1 || pa==RSC_PA || pa==RSC_PA+RSC_BYTES-1,
        "only exact first/last byte translations");
    unsigned which=mock.translations[id]++;
    CHECK(which<2 && pa==(id ? RSC_PA:DB_PA)+(which ? (id ? RSC_BYTES:DB_BYTES)-1:0),
        "first and final byte in order");
    return (vm_offset_t)pa+(mock.translate_failure==id*2+which+1 ? 1:0);
}
static uint32_t fake_bus_read32(vm_offset_t base,uint32_t off)
{
    CHECK((off&3)==0,"aligned 32-bit read");
    CHECK(mock.markers==mock.flushes,"marker persisted before reads");
    if (base==FAKE_BASE+DB_PA) {
        unsigned k=mock.db_loads++;
        CHECK(k<65536 && off==4*(k%32768),"all 65536 words ascending, including zero words");
        CHECK(mock.translations[0]==2 && !mock.rsc_loads,"CMDDB translation and ordering");
        return get32(db[k/32768]+off);
    }
    CHECK(base==FAKE_BASE+RSC_PA && off+4<=RSC_BYTES,"bounded RSC frame");
    CHECK(mock.translations[1]==2 && mock.db_loads==65536,"RSC translations before read");
    CHECK(mock.rsc_loads<mock.expected_count,"no extra RSC reads");
    const struct expected_read *e=&mock.expected[mock.rsc_loads++];
    if (off!=e->offset) {
        fprintf(stderr,"RSC read %u got %04x want %04x\n",mock.rsc_loads-1,off,e->offset);
        CHECK(false,"exact independent RSC whitelist and order");
    }
    return e->value;
}
static void sha_init(SHA256_CTX *ctx) { memset(ctx,0,sizeof(*ctx)); }
static void sha_update(SHA256_CTX *ctx,const void *data,size_t len)
{
    CHECK(mock.allocation && data==mock.allocation && len==DB_BYTES,"SHA only work.raw[0] in normal memory");
    CHECK(mock.allocation_size>=len && mock.db_loads==65536 && !mock.shas && !ctx->updates,
        "one SHA after two stable copies");
    CHECK(data!=db[0] && data!=db[1] && data!=positive_db,"never hash fixture or MMIO pointer");
    mock.positive_sha=!memcmp(data,positive_db,DB_BYTES);
    if (mock.positive_sha) memcpy(ctx->digest,positive_digest,32);
    else memset(ctx->digest,0xa5,32);
    ++ctx->updates;
}
static void sha_final(uint8_t out[32],SHA256_CTX *ctx)
{ CHECK(ctx->updates==1,"one SHA update"); memcpy(out,ctx->digest,32); ++mock.shas; }
#define printf test_printf
#define SHA256_Init sha_init
#define SHA256_Update sha_update
#define SHA256_Final sha_final
@WORKER@
#undef printf
#undef SHA256_Init
#undef SHA256_Update
#undef SHA256_Final

static void add_read(unsigned offset,uint32_t value)
{
    CHECK(mock.expected_count<READS_MAX && offset%4==0 && offset+4<=RSC_BYTES,"oracle bounds");
    mock.expected[mock.expected_count++]=(struct expected_read){offset,value};
}
static void prepare_reads(void)
{
    mock.expected_count=0;
    add_read(0xc,mock.initial_config);
    unsigned initial_ncpt=(mock.initial_config>>27)&31;
    if (((mock.initial_config>>12)&63)<8 || !initial_ncpt || initial_ncpt>16) return;
    for (unsigned pass=0;pass<2;++pass) {
        uint32_t *regs=rsc[pass]; unsigned ncpt=(regs[3]>>27)&31;
        add_read(0xc,regs[3]);
        if (regs[3]!=mock.initial_config) return;
        add_read(0xd00,regs[0xd00/4]); add_read(0xd04,regs[0xd04/4]);
        for (unsigned t=0;t<8;++t) {
            unsigned b=0xd00+t*0x2a0;
            for (unsigned f=0;f<4;++f) add_read(b+0x10+4*f,regs[(b+0x10+4*f)/4]);
            if (regs[(b+0x1c)/4]>>ncpt) return;
        }
        for (unsigned t=0;t<8;++t) {
            unsigned b=0xd00+t*0x2a0;
            for (unsigned c=0;c<ncpt;++c) if (regs[(b+0x1c)/4]&(1u<<c))
                for (unsigned f=0;f<4;++f) add_read(b+0x30+0x14*c+4*f,regs[(b+0x30+0x14*c+4*f)/4]);
        }
    }
}
static void set_both(unsigned offset,uint32_t value)
{ CHECK(offset%4==0 && offset<RSC_BYTES,"set fixture register"); rsc[0][offset/4]=rsc[1][offset/4]=value; }
static unsigned tcs(unsigned t,unsigned off) { return 0xd00+t*0x2a0+off; }
static void reset(const char *name)
{
    free(mock.allocation); memset(&mock,0,sizeof(mock)); bus_work=NULL; bus_started=0;
    case_name=name; ++cases; mock.enabled=1;
    memcpy(db[0],positive_db,DB_BYTES); memcpy(db[1],positive_db,DB_BYTES);
    memset(rsc,0,sizeof(rsc)); mock.initial_config=(8u<<12)|(8u<<27);
    set_both(0xc,mock.initial_config);
    set_both(0xd00,0xff); /* IRQ enable is observed; IRQ status stays clear. */
    for (unsigned t=0;t<8;++t) {
        set_both(tcs(t,0x18),1); /* idle status is nonzero and not all ones */
        for (unsigned c=0;c<16;++c) {
            set_both(tcs(t,0x30+0x14*c),0x10000000u+(t<<4)+c);
            set_both(tcs(t,0x34+0x14*c),0x50000+4*c);
            set_both(tcs(t,0x38+0x14*c),0x60000000);
            set_both(tcs(t,0x3c+0x14*c),0x10100);
        }
    }
    set_both(tcs(4,0x1c),1u<<2); /* one non-ACTIVE command to observe */
}
static void run_worker(void)
{
    prepare_reads(); sweet_bus_probe_init();
    CHECK(mock.starts==1 && mock.worker && mock.deallocations==1,"one worker scheduled");
    CHECK(!mock.allocations && !mock.sleeps && !mock.map_count,"not inline");
    mock.worker(NULL,0); CHECK(mock.terminations==1,"worker terminated once");
}
static unsigned count_line(const char *needle)
{
    unsigned n=0; for(unsigned i=0;i<mock.lines;++i) if(strstr(mock.log[i],needle)) ++n; return n;
}
static void has(const char *needle) { CHECK(count_line(needle)>0,needle); }
static void absent(const char *needle) { CHECK(!count_line(needle),needle); }
static void all_reads(void)
{ CHECK(mock.rsc_loads==mock.expected_count,"complete exact expected reads"); }
static void complete(void)
{
    CHECK(mock.db_loads==65536 && mock.map_count==2,"full read-only capture");
    CHECK(mock.shas==1 && mock.positive_sha,"positive normal-copy digest"); all_reads();
    CHECK(count_line("SWEET CMDB RAW: ")==2048,"2048 raw chunks");
    CHECK(count_line("SWEET CMDB BEGIN: ")==1 && count_line("SWEET CMDB END: ")==1,"one complete RAW block");
    CHECK(mock.markers<100 && mock.flushes==mock.markers,"bounded flushes, never per raw chunk");
    CHECK(bus_work && bus_work==mock.allocation && bus_started==1,"retained value storage and one-shot");
    static const uint32_t want[]={0x6fffffff,0x6fffffff,0x2fffffff,0x6fffffff,0x6fffffff,0x60000008};
    static const uint32_t addr[]={0x50000,0x50004,0x5002c,0x50044,0x5006c,0x50080};
    CHECK(bus_work->plan.wait_mask==0x3b,"plan stored, wait mask");
    for(unsigned i=0;i<6;++i) {
        CHECK(bus_work->plan.cmd[i].address==addr[i] && bus_work->plan.cmd[i].data==want[i] &&
            bus_work->plan.cmd[i].wait==((0x3bu>>i)&1),"stored exact plan");
        char line[128]; snprintf(line,sizeof(line),"PLAN ONLY cmd%u addr=%05x data=%08x",i,addr[i],want[i]); has(line);
    }
    has("RSC stable captures=2"); has("PLAN ONLY; no bandwidth submitted, no GPU execution; observation only");
}
static void no_rsc(void)
{ CHECK(mock.db_loads==65536 && mock.map_count==1 && !mock.rsc_loads,"failure stops before RSC map"); absent("RSC stable captures=2"); }
static void export_positive(const char *path)
{
    FILE *f=fopen(path,"wb"); CHECK(f,"open positive log");
    for(unsigned i=0;i<mock.lines;++i) CHECK(fputs(mock.log[i],f)>=0,"write positive log");
    CHECK(!fclose(f),"close positive log");
}
static void parse_digest(const char *hex)
{
    CHECK(strlen(hex)==64,"digest length");
    for(unsigned i=0;i<32;++i) {
        char part[3]={hex[2*i],hex[2*i+1],0}; char *end;
        CHECK(strspn(part,"0123456789abcdef")==2,"lowercase hex digest");
        positive_digest[i]=(uint8_t)strtoul(part,&end,16); CHECK(!*end,"digest decode");
    }
}
int main(int argc,char **argv)
{
    make_positive_db();
    if(argc==3 && !strcmp(argv[1],"--emit-db")) {
        FILE *f=fopen(argv[2],"wb"); CHECK(f,"open positive DB");
        CHECK(fwrite(positive_db,1,DB_BYTES,f)==DB_BYTES && !fclose(f),"emit positive DB"); return 0;
    }
    CHECK(argc==5 && !strcmp(argv[1],"--digest") && !strcmp(argv[3],"--log"),"usage --digest HEX --log PATH");
    parse_digest(argv[2]);
    const int disabled[]={0,2,-1,9};
    for(unsigned i=0;i<sizeof(disabled)/sizeof(disabled[0]);++i) {
        reset("default off"); mock.enabled=disabled[i]; sweet_bus_probe_init(); sweet_bus_probe_init();
        CHECK(!mock.starts && !mock.allocations && !mock.map_count && !mock.lines,"disabled no effects");
    }
    reset("one start, positive"); run_worker(); complete();
    CHECK(mock.rsc_loads==79,"one preliminary + twice 39 RSC reads");
    has("config=40008000 ncpt=8 end=202c"); has("candidate_active_idle=2;");
    sweet_bus_probe_init(); CHECK(mock.starts==1,"atomic one shot"); export_positive(argv[4]);
    reset("thread failure"); mock.thread_error=5; sweet_bus_probe_init(); sweet_bus_probe_init();
    CHECK(mock.starts==1 && !mock.worker && !mock.allocations,"no inline fallback or retry"); has("worker creation failed=5");
    for(int bad=1;bad<=3;++bad) {
        reset("early context"); mock.context=bad; run_worker(); CHECK(!mock.sleeps && !mock.allocations && !mock.map_count,"early context stops");
        reset("late context"); mock.delayed_context=bad; run_worker(); CHECK(mock.sleeps==45 && !mock.allocations && !mock.map_count,"late context stops");
    }
    for(int mode=-1;mode<=9;++mode) if(mode) {
        reset("legacy writer conflict"); mock.touchmode=mode; run_worker(); CHECK(!mock.sleeps && !mock.allocations && !mock.map_count,"conflict stops before allocation");
    }
    reset("allocation failure"); mock.allocation_failure=1; run_worker(); CHECK(mock.allocations==1 && !mock.map_count,"allocation failure stops");
    for(unsigned i=0;i<9;++i) {
        reset("managed physical page"); mock.managed_page=i+1; run_worker();
        CHECK(mock.map_count==(i==8 ? 1u:0u) && mock.db_loads==(i==8 ? 65536u:0u) && !mock.rsc_loads,"managed stops before affected mapping");
        reset("wrong page cache type"); mock.wrong_attr_page=i+1; run_worker();
        CHECK(mock.map_count==(i==8 ? 1u:0u) && mock.db_loads==(i==8 ? 65536u:0u) && !mock.rsc_loads,"wrong cache type stops before affected mapping");
    }
    for(unsigned i=1;i<=2;++i) {
        reset("map failure"); mock.map_failure=i; run_worker();
        CHECK(mock.map_count==i && mock.db_loads==(i==2 ? 65536u:0u) && !mock.rsc_loads,"map failure no reads of failed map");
    }
    for(unsigned i=1;i<=4;++i) {
        reset("first or last translation failure"); mock.translate_failure=i; run_worker();
        CHECK(mock.db_loads==(i>2 ? 65536u:0u) && !mock.rsc_loads,"translation failure no affected read"); has("translation mismatch");
    }
    reset("changing CMDDB"); db[1][DB_BYTES-1]^=1; run_worker(); no_rsc();
    CHECK(!mock.shas,"no hash on differing copies"); absent("SWEET CMDB BEGIN:"); has("CMDDB copies differ");
    reset("missing BCM metadata"); memcpy(db[0]+240,"MC1",3); memcpy(db[1],db[0],DB_BYTES); run_worker(); no_rsc();
    CHECK(mock.shas==1 && !mock.positive_sha,"mutated bytes use sentinel digest"); has("CMDDB metadata MC0 invalid");
    reset("bad BCM aux"); db[0][460]^=1; memcpy(db[1],db[0],DB_BYTES); run_worker(); no_rsc(); has("CMDDB board plan invalid");
    reset("bad ARC levels"); put16(db[0]+384+4,1); memcpy(db[1],db[0],DB_BYTES); run_worker(); no_rsc(); has("ARC cx.lvl invalid");
    reset("bad bank bounds"); put16(db[0]+26,0xfff0); put16(db[0]+30,1024); memcpy(db[1],db[0],DB_BYTES); run_worker(); no_rsc();
    const uint32_t bad_configs[]={(7u<<12)|(8u<<27),(8u<<12),(8u<<12)|(17u<<27)};
    for(unsigned i=0;i<sizeof(bad_configs)/sizeof(bad_configs[0]);++i) {
        reset("bad initial geometry"); mock.initial_config=bad_configs[i]; set_both(0xc,mock.initial_config); run_worker();
        CHECK(mock.rsc_loads==1,"invalid geometry reads only preliminary config"); has("RSC geometry config="); absent("RSC stable captures=2");
    }
    for(unsigned pass=0;pass<2;++pass) {
        reset("configuration changes before capture"); rsc[pass][3]=(8u<<12); run_worker(); all_reads();
        CHECK(mock.rsc_loads==(pass ? 41u:2u),"changed config stops before capture IRQ/TCS"); has("RSC configuration changed"); absent("RSC stable captures=2");
    }
    reset("enable beyond ncpt"); set_both(tcs(3,0x1c),1u<<8); run_worker(); all_reads();
    CHECK(mock.rsc_loads==20,"config+IRQ and four TCS headers only"); has("TCS3 enable 00000100 beyond ncpt=8");
    reset("sparse command indexes 7 and 15"); mock.initial_config=(8u<<12)|(16u<<27); set_both(0xc,mock.initial_config);
    set_both(tcs(4,0x1c),(1u<<7)|(1u<<15)); run_worker(); complete();
    CHECK(mock.rsc_loads==87,"two sparse commands each capture"); has("end=20cc");
    has("RSC TCS4 cmd7 msgid=10000047 addr=0005001c"); has("RSC TCS4 cmd15 msgid=1000004f addr=0005003c");
    absent("RSC TCS4 cmd0 "); absent("RSC TCS4 cmd1 ");
    reset("changed RSC register"); rsc[1][tcs(2,0x18)/4]^=2; run_worker(); all_reads(); has("RSC snapshots differ"); absent("RSC stable captures=2");
    reset("changed enabled command set"); rsc[1][tcs(4,0x1c)/4]=1u<<3; run_worker(); all_reads(); has("RSC snapshots differ"); absent("RSC stable captures=2");
    reset("five slots not enough for plan"); mock.initial_config=(8u<<12)|(5u<<27); set_both(0xc,mock.initial_config); run_worker(); complete();
    has("ncpt=5 candidate_active_idle=2;"); has("not ready for 6-command transport");
    /* Each negative targets an otherwise-idle ACTIVE0, while ACTIVE1 is busy. */
    for(unsigned reason=0;reason<6;++reason) {
        reset("idle candidate exclusions"); set_both(tcs(1,0x14),1);
        if(reason==0) set_both(tcs(0,0x18),0);
        if(reason==1) set_both(tcs(0,0x18),0xffffffffu);
        if(reason==2) set_both(0xd04,1);
        if(reason==3) set_both(tcs(0,0x10),1);
        if(reason==4) set_both(tcs(0,0x14),1);
        if(reason==5) set_both(tcs(0,0x1c),1);
        run_worker(); complete(); has("candidate_active_idle=0;"); has("not ready for 6-command transport");
    }
    reset("only active1 candidate"); set_both(0xd04,1); run_worker(); complete(); has("candidate_active_idle=1;"); absent("not ready for 6-command transport");
    reset("ncpt16 but no candidate"); mock.initial_config=(8u<<12)|(16u<<27); set_both(0xc,mock.initial_config);
    set_both(tcs(0,0x14),1); set_both(tcs(1,0x14),1); run_worker(); complete(); has("ncpt=16 candidate_active_idle=0;"); has("not ready for 6-command transport");
    free(mock.allocation); mock.allocation=NULL; bus_work=NULL;
    printf("PASS: %u worker cases; ASan/UBSan; read-only mappings, exact MMIO whitelist, actual RAW log exported; SHA itself is a seam\n",cases);
    return 0;
}
