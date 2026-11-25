/* Appended to runtime_host.c after renaming its main. The three functions
 * under test are inserted verbatim from the candidate board C translation
 * unit. This fixture only models their external board predicates. */
static struct ggr_context ggrb_context;
static uint64_t ggrb_root;
static unsigned ggrb_started, routes_called, route_fail_call, delays;
static bool live_ok, routes_ok, delay_ok;

static bool ggrb_live(void *cookie)
{(void)cookie;return live_ok;}
static bool ggrb_routes(void)
{
    ++routes_called;
    return routes_ok && routes_called!=route_fail_call;
}
bool sweet_gpu_runtime_ready(void)
{
    if(ggrb_context.state!=GGR_READY)return false;
    if(ggrb_live(NULL)&&ggrb_routes())return true;
    ggr_fail(&ggrb_context,GGR_UNAVAILABLE);return false;
}
static bool ggrb_delay(void *cookie,unsigned us)
{(void)cookie;++delays;return delay_ok&&us==10;}

/* INSERT_REAL_BOARD_FUNCTIONS */

static void board_init(struct model *m)
{
    init_span(m,&ggrb_context);
    ggrb_root=1;ggrb_started=1;routes_called=route_fail_call=delays=0;
    live_ok=routes_ok=delay_ok=true;
}

int main(void)
{
    CHECK(baseline_main()==0);
    unsigned prior=cases;
    struct model m;
    uint64_t address=GGR_VA_START+65536;
    uint32_t words=16, fence=0;

    board_init(&m);
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,NULL)==GGR_ARGUMENT);
    CHECK(m.writes==0&&!m.quarantines);
    m.no_eop=true;
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_OK);
    CHECK(fence==1&&ggrb_context.state==GGR_BUSY&&ggrb_context.completed==0);
    unsigned writes=m.writes;
    fence=0xdeadbeef;
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_UNAVAILABLE);
    CHECK(fence==0&&m.writes==writes&&!m.quarantines);
    CHECK(sweet_gpu_runtime_poll(1)==GGR_PENDING);
    m.eop=1;
    CHECK(sweet_gpu_runtime_poll(1)==GGR_OK&&ggrb_context.completed==1);
    CHECK(sweet_gpu_runtime_wait(1)==GGR_OK&&!m.quarantines);

    m.no_eop=true;fence=0;
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_OK&&fence==2);
    CHECK(sweet_gpu_runtime_poll(1)==GGR_OK&&ggrb_context.state==GGR_BUSY);
    CHECK(sweet_gpu_runtime_poll(2)==GGR_PENDING);
    m.eop=2;
    CHECK(sweet_gpu_runtime_wait(2)==GGR_OK&&ggrb_context.completed==2);

    board_init(&m);m.no_eop=true;fence=0;
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_OK);
    routes_ok=false;
    CHECK(sweet_gpu_runtime_poll(1)==GGR_IO);
    CHECK(ggrb_context.state==GGR_FAILED&&m.quarantines==1);

    board_init(&m);m.no_eop=true;fence=0;
    route_fail_call=2; /* ready preflight passes; post-doorbell proof fails */
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_IO);
    CHECK(fence==0&&ggrb_context.submitted==1&&ggrb_context.completed==0);
    CHECK(ggrb_context.state==GGR_FAILED&&m.quarantines==1);

    board_init(&m);m.no_eop=true;fence=0;
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_OK);
    m.ns+=UINT64_C(3000000000);
    CHECK(sweet_gpu_runtime_wait(1)==GGR_TIMEOUT);
    CHECK(ggrb_context.state==GGR_FAILED&&m.quarantines==1);

    board_init(&m);m.no_eop=true;fence=0;
    CHECK(sweet_gpu_runtime_issue(&address,&words,1,&fence)==GGR_OK);
    delay_ok=false;
    CHECK(sweet_gpu_runtime_wait(1)==GGR_TIMEOUT);
    CHECK(ggrb_context.state==GGR_FAILED&&m.quarantines==1&&delays==1);

    printf("PASS: %u board issue/poll/wait/route/quarantine assertions; real wrappers, CPU model only\n",cases-prior);
    return 0;
}
