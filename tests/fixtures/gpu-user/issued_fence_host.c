/* Appended to runtime_host.c after renaming its main to baseline_main. */
int main(void)
{
    CHECK(baseline_main()==0);
    unsigned prior=cases;
    struct model m;struct ggr_context c;
    uint64_t address=GGR_VA_START+65536;uint32_t words=16,fence=0;

    init(&m,&c);m.no_eop=true;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    CHECK(fence==1&&c.state==GGR_BUSY&&c.submitted==1&&c.completed==0);
    CHECK(c.pending_deadline_ns>0&&c.pending_wptr==m.wptr&&m.eop==0);
    unsigned writes=m.writes;uint32_t other=0xfeedbeef;
    CHECK(ggr_issue(&c,&address,&words,1,&other)==GGR_UNAVAILABLE);
    CHECK(other==0xfeedbeef&&m.writes==writes&&!m.quarantines);
    CHECK(ggr_poll(&c)==GGR_PENDING&&c.completed==0);
    m.eop=1;
    CHECK(ggr_poll(&c)==GGR_OK&&c.completed==1&&c.state==GGR_READY);
    CHECK(c.pending_deadline_ns==0&&c.wptr==m.shadow);
    CHECK(ggr_wait(&c,1)==GGR_OK&&ggr_poll(&c)==GGR_UNAVAILABLE);

    /* Completion found after a long gap is still real, even if the caller
     * did not poll inside the original two-second pending deadline. */
    init(&m,&c);fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK&&m.eop==1);
    m.ns+=UINT64_C(3000000000);
    CHECK(ggr_poll(&c)==GGR_OK&&c.completed==1&&!m.quarantines);

    init(&m,&c);m.no_eop=true;fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    m.ns+=UINT64_C(3000000000);
    CHECK(ggr_poll(&c)==GGR_TIMEOUT&&c.state==GGR_FAILED&&m.quarantines==1);
    writes=m.writes;
    CHECK(ggr_poll(&c)==GGR_UNAVAILABLE&&m.writes==writes);

    init(&m,&c);m.no_shadow=true;fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    CHECK(ggr_poll(&c)==GGR_PENDING&&c.completed==0);
    m.shadow=c.pending_wptr;
    CHECK(ggr_poll(&c)==GGR_OK&&c.completed==1);

    init(&m,&c);fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    m.eop=2;
    CHECK(ggr_poll(&c)==GGR_IO&&c.state==GGR_FAILED&&m.quarantines==1);

    init(&m,&c);m.defer_eop_reads=4;fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    CHECK(ggr_wait(&c,fence)==GGR_OK&&c.polls>=4&&c.completed==fence);

    /* A ring wrap is safe while the previous command has completed. */
    init(&m,&c);c.wptr=m.wptr=m.shadow=m.old_wptr=8188;fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    CHECK(c.pending_wptr==8&&c.wptr==8188);
    CHECK(ggr_poll(&c)==GGR_OK&&c.wptr==8&&m.wptr==8);

    init(&m,&c);c.wptr=m.wptr=m.shadow=m.old_wptr=8180;fence=0;
    CHECK(ggr_issue(&c,&address,&words,1,&fence)==GGR_OK);
    CHECK(c.pending_wptr==0&&c.state==GGR_BUSY);
    CHECK(ggr_poll(&c)==GGR_OK&&c.wptr==0&&c.completed==1);

    init(&m,&c);other=0xfeedbeef;writes=m.writes;
    CHECK(ggr_issue(&c,&address,&words,0,&other)==GGR_ARGUMENT);
    CHECK(other==0xfeedbeef&&m.writes==writes);
    CHECK(ggr_submit(&c,&address,&words,1,NULL)==GGR_ARGUMENT&&m.writes==writes);
    printf("PASS: %u issued/pending/completed/deadline/wrap assertions; typed ring, no GPU emulation\n",cases-prior);
    return 0;
}
