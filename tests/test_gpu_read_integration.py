from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
S=Path(os.environ.get('XNU_SOURCE',R/'.deps-cache/p0-20261105/source209-codex'))

def extract(s,sig):
 a=s.index(sig);return s[a:s.index('\n}\n',a)+3]
EXTRA=r'''
static struct model *active_model;
static struct ggr_context *active_context;
#define ggrb_context (*active_context)
enum {GMB_READY=2};
static unsigned ggrb_started=1,last_access_checks;
static struct {unsigned reason;} ggrb_live_sample;
static uint64_t ggrb_end=UINT64_MAX,guard_duration,stamp_delay;
static bool gmb_thread(void){return true;}
static unsigned sweet_gmu_board_state(void){return GMB_READY;}
static uint64_t mach_absolute_time(void){return active_model->ns;}
static uint64_t ggrb_ns(void *p){(void)p;return active_model->ns;}
static void nanoseconds_to_absolutetime(uint64_t n,uint64_t *v){
 if(n==5000)active_model->ns+=stamp_delay;*v=n;
}
static bool ggrb_live_check(void *p){
 CHECK(p==active_model);bool ok=healthy(p);active_model->ns+=guard_duration;return ok;
}
@PERF@
@WRAPPER@
@HELPER@
static bool integrated_read_reg(void *p,uint32_t r,uint32_t *v){
 last_access_checks=((struct model *)p)->checks;return read_reg(p,r,v);
}
static bool integrated_read_memory(void *p,enum ggr_memory k,uint32_t o,uint32_t *v){
 last_access_checks=((struct model *)p)->checks;return read_memory(p,k,o,v);
}
static bool integrated_write(void *p,uint32_t r,uint32_t v){
 CHECK(((struct model *)p)->checks>=last_access_checks+2);
 last_access_checks=((struct model *)p)->checks;return write_reg(p,r,v);
}
static bool integrated_ring(void *p,uint32_t o,uint32_t v){
 CHECK(((struct model *)p)->checks>=last_access_checks+2);
 last_access_checks=((struct model *)p)->checks;return write_ring(p,o,v);
}
static bool integrated_barrier(void *p){
 CHECK(((struct model *)p)->checks>=last_access_checks+2);
 last_access_checks=((struct model *)p)->checks;return barrier(p);
}
static bool integrated_delay(void *p,uint32_t n){
 CHECK(((struct model *)p)->checks>=last_access_checks+2);
 last_access_checks=((struct model *)p)->checks;return delay_us(p,n);
}
static void setup(struct model *m,struct ggr_context *c,uint64_t duration,uint64_t late){
 init(m,c);m->checks=0;active_model=m;active_context=c;last_access_checks=0;
 guard_duration=duration;stamp_delay=late;ggrb_live_sample.reason=0;
 ggrb_read_head=ggrb_read_tail=ggrb_read_reuses=ggrb_read_max_gap=ggrb_read_max_age=0;
 ggrb_read_valid=false;ggrb_read_state=0;memset(&ggrb_perf,0,sizeof(ggrb_perf));
 c->ops.healthy=ggrb_live;c->ops.read_continuation=ggrb_read_continuation;
 c->ops.read_reg=integrated_read_reg;c->ops.read_memory=integrated_read_memory;
 c->ops.write_reg=integrated_write;c->ops.write_ring=integrated_ring;
 c->ops.barrier=integrated_barrier;c->ops.delay_us=integrated_delay;
}
int main(void){
 for(unsigned n=1;n<=128;n++){
  struct model old,m;struct ggr_context a,c;uint32_t fa=0,fc=0;
  init(&old,&a);old.checks=0;CHECK(submit(&a,n,&fa)==GGR_OK);
  setup(&m,&c,190000,0);CHECK(submit(&c,n,&fc)==GGR_OK);
  CHECK(fa==fc&&a.wptr==c.wptr&&a.completed==c.completed&&m.writes==old.writes);
  CHECK(!memcmp(m.ring,old.ring,sizeof(m.ring)));
  CHECK(ggrb_read_reuses>0&&m.checks<old.checks&&m.checks==ggrb_perf.checks);
  CHECK(ggrb_read_max_gap<=5000&&ggrb_read_max_age<=250000);
  for(unsigned mode=0;mode<2;mode++){
   setup(&m,&c,mode?190000:260000,mode?5001:0);fc=0;
   CHECK(submit(&c,n,&fc)==GGR_OK);CHECK(fc==fa&&m.writes==old.writes);
   CHECK(!ggrb_read_reuses&&m.checks==old.checks);
   CHECK(!memcmp(m.ring,old.ring,sizeof(m.ring)));
  }
 }
 struct model m;struct ggr_context c;
 setup(&m,&c,190000,0);CHECK(ggr_check_idle(&c)==GGR_OK);
 CHECK(ggrb_read_reuses==5&&m.checks==7);
 printf("Integrated actual core/full-clock-wrapper/board callback: %u assertions;190us guard reuse,260us/late-stamp full fallback, exact packets/fences and full write/barrier/delay gates; typed IO seams only\n",cases);
}
'''
def main():
 paths=[Path(__file__),R/'tests/fixtures/gpu-user/runtime_host.c',S/'bsd/dev/gauguin_gpu_runtime.c',S/'bsd/dev/gauguin_gpu_runtime.h',S/'bsd/dev/gauguin_gmu_board.c']
 pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 board=paths[-1].read_text();a=board.index('struct ggrb_perf_sample {');perf=board[a:board.index('static bool ggrb_micro_settle(',a)]
 helper=board[board.index('/* Read-only continuation of'):board.index('static bool ggrb_routes(')]
 wrapper=extract(board,'static bool ggrb_live(')
 base=paths[1].read_text();base=base[:base.index('int main(void)')]
 body=base+EXTRA.replace('@PERF@',perf).replace('@WRAPPER@',wrapper).replace('@HELPER@',helper)
 with tempfile.TemporaryDirectory(prefix='read-cont-integrated-') as d:
  d=Path(d);unit=d/'integration.c';unit.write_text(body);env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(S/'bsd/dev'),str(paths[2]),str(unit),'-o',str(d/'integration')],check=True,env=env)
  subprocess.run([str(d/'integration')],check=True,env=env,timeout=60)
 assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
if __name__=='__main__':main()
