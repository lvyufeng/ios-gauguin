from pathlib import Path
import hashlib,os,subprocess,tempfile
R=Path(__file__).resolve().parent.parent
S=Path(os.environ.get('XNU_SOURCE',R/'.deps-cache/p0-20261105/source209-codex'))
P=Path(os.environ.get('XNU_REFERENCE',R/'.deps-cache/p0-20261105/source208-codex'))

def extract(s,sig):
 a=s.index(sig);return s[a:s.index('\n}\n',a)+3]
EXTRA=r'''
static unsigned stamps,attempts,reuses,tracked_reads,tracked_writes;
static bool allow_reuse,allow_stamp,cached_read,full_ok,stamp_valid;
static uint64_t stamp_ns;
static bool tracked_healthy(void *p){cached_read=false;full_ok=healthy(p);return full_ok;}
static bool continuation(void *p,bool stamp){
 struct model *m=p;
 if(stamp){CHECK(full_ok);++stamps;stamp_ns=m->ns;stamp_valid=allow_stamp;return stamp_valid;}
 ++attempts;bool valid=stamp_valid;stamp_valid=false;
 if(!valid||!allow_reuse||m->ns<stamp_ns||m->ns-stamp_ns>5000)return false;
 cached_read=true;++reuses;return true;
}
static bool tracked_reg(void *p,uint32_t r,uint32_t *v){
 CHECK(cached_read||full_ok);++tracked_reads;return read_reg(p,r,v);
}
static bool tracked_memory(void *p,enum ggr_memory k,uint32_t o,uint32_t *v){
 CHECK(cached_read||full_ok);++tracked_reads;return read_memory(p,k,o,v);
}
static bool tracked_write(void *p,uint32_t r,uint32_t v){
 CHECK(!cached_read&&full_ok);++tracked_writes;return write_reg(p,r,v);
}
static bool tracked_ring(void *p,uint32_t o,uint32_t v){
 CHECK(!cached_read&&full_ok);++tracked_writes;return write_ring(p,o,v);
}
static bool tracked_barrier(void *p){CHECK(!cached_read&&full_ok);return barrier(p);}
static bool tracked_delay(void *p,uint32_t n){CHECK(!cached_read&&full_ok);return delay_us(p,n);}
static void setup_tracked(struct model *m,struct ggr_context *c,bool reuse,bool record){
 init(m,c);m->checks=0;stamps=attempts=reuses=tracked_reads=tracked_writes=0;
 allow_reuse=reuse;allow_stamp=record;cached_read=full_ok=stamp_valid=false;stamp_ns=0;
 c->ops.healthy=tracked_healthy;c->ops.read_continuation=continuation;
 c->ops.read_reg=tracked_reg;c->ops.read_memory=tracked_memory;
 c->ops.write_reg=tracked_write;c->ops.write_ring=tracked_ring;
 c->ops.barrier=tracked_barrier;c->ops.delay_us=tracked_delay;
}
int main(void){
 baseline_main();
 for(unsigned n=1;n<=GGR_MAX_COMMANDS;n++){
  struct model reference,fast;struct ggr_context a,b;uint32_t fa=0,fb=0;
  init(&reference,&a);reference.checks=0;
  CHECK(submit(&a,n,&fa)==GGR_OK);
  setup_tracked(&fast,&b,true,true);b.read_checked=true;stamp_valid=true;stamp_ns=fast.ns;
  CHECK(submit(&b,n,&fb)==GGR_OK);CHECK(fa==fb&&a.wptr==b.wptr&&a.completed==b.completed);
  CHECK(!memcmp(reference.ring,fast.ring,sizeof(reference.ring)));
  CHECK(reference.writes==fast.writes&&reference.decoded_ibs==fast.decoded_ibs);
  CHECK(reference.eop==fast.eop&&reference.shadow==fast.shadow);
  CHECK(reuses>0&&fast.checks<reference.checks&&stamps>reuses);
  CHECK(tracked_reads>reuses&&tracked_writes==reference.writes);
  setup_tracked(&fast,&b,false,true);fb=0;CHECK(submit(&b,n,&fb)==GGR_OK);
  CHECK(!reuses&&fast.checks==reference.checks&&fast.writes==reference.writes&&fb==fa);
  setup_tracked(&fast,&b,true,false);fb=0;CHECK(submit(&b,n,&fb)==GGR_OK);
  CHECK(!attempts&&!reuses&&fast.checks==reference.checks&&fb==fa);
 }
 struct model m;struct ggr_context c;uint32_t fence=0;
 setup_tracked(&m,&c,true,true);CHECK(submit(&c,4,&fence)==GGR_OK);unsigned checks=m.checks;
 for(unsigned failure=1;failure<=checks;failure++){
  setup_tracked(&m,&c,true,true);m.fail_at=failure;fence=0;
  CHECK(submit(&c,4,&fence)!=GGR_OK);CHECK(c.state==GGR_FAILED&&!c.read_checked);
  CHECK(m.stopped&&m.quarantines==1&&!fence);
  uint32_t writes=m.writes;CHECK(submit(&c,4,&fence)==GGR_UNAVAILABLE);
  CHECK(m.writes==writes&&m.quarantines==1);
 }
 setup_tracked(&m,&c,true,true);c.read_checked=true;stamp_valid=true;stamp_ns=m.ns;
 CHECK(ggr_check_idle(&c)==GGR_OK);CHECK(reuses>0&&tracked_writes==0);
 ggr_fail(&c,GGR_IO);CHECK(!c.read_checked&&m.stopped&&m.quarantines==1);
 printf("Read continuation runtime: %u assertions; original baseline plus exact ring/fences, optional fallback and every full-guard failure; all writes fully gated\n",cases);
 return 0;
}
'''
BOARD=r'''
#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do{++checks;assert(x);}while(0)
enum{GGR_READY=1,GGR_BUSY=2,GGR_FAILED=3,GMB_READY=2};
static unsigned ggrb_started,board,thread,clock_reads,advance_at;
static struct {uint32_t state;uint64_t operation_end_ns;} ggrb_context;
static struct {uint32_t reason;} ggrb_live_sample;
static uint64_t now,ggrb_end,guard_cost,advance_ticks;static bool zero_limit,full_ok;
static uint64_t mach_absolute_time(void){if(++clock_reads==advance_at)now+=advance_ticks;return now;}
static uint64_t ggrb_ns(void *p){assert(!p);return now;}
static bool gmb_thread(void){return thread;}
static unsigned sweet_gmu_board_state(void){return board;}
static void nanoseconds_to_absolutetime(uint64_t n,uint64_t *p){*p=zero_limit?0:n;}
static bool ggrb_live_check(void *p){assert(!p);now+=guard_cost;return full_ok;}
@PERF@
@WRAPPER@
@HELPER@
static void reset(void){
 now=1000;ggrb_end=ggrb_context.operation_end_ns=2000000000;
 ggrb_context.state=GGR_BUSY;ggrb_live_sample.reason=0;
 ggrb_started=thread=1;board=GMB_READY;
 ggrb_read_head=ggrb_read_tail=ggrb_read_reuses=ggrb_read_max_gap=ggrb_read_max_age=0;
 ggrb_read_state=0;ggrb_read_valid=zero_limit=false;
 memset(&ggrb_perf,0,sizeof(ggrb_perf));ggrb_perf.last_live_begin=100;ggrb_perf.last_live_end=now;ggrb_perf.last_live_valid=true;
 guard_cost=advance_ticks=advance_at=clock_reads=0;full_ok=true;
}
int main(void){
 reset();CHECK(!ggrb_read_continuation(NULL,false));
 CHECK(ggrb_read_continuation(NULL,true));now+=5000;
 CHECK(ggrb_read_continuation(NULL,false));CHECK(ggrb_read_reuses==1&&ggrb_read_max_gap==5000&&ggrb_read_max_age==5900);
 CHECK(!ggrb_read_continuation(NULL,false));CHECK(ggrb_read_reuses==1&&!ggrb_read_valid);
 for(unsigned condition=0;condition<15;condition++){
  reset();CHECK(ggrb_read_continuation(NULL,true));
  switch(condition){case 0:now+=5001;break;case 1:now=999;break;
   case 2:ggrb_context.state=GGR_READY;break;case 3:ggrb_context.state=GGR_FAILED;break;
   case 4:ggrb_started=0;break;case 5:thread=0;break;case 6:board=0;break;
   case 7:ggrb_live_sample.reason=13;break;case 8:ggrb_end=now;break;
   case 9:ggrb_context.operation_end_ns=now;break;case 10:zero_limit=true;break;
   case 11:ggrb_read_reuses=UINT64_MAX;break;case 12:ggrb_read_head=0;now=ggrb_read_tail=250001;break;
   case 13:ggrb_read_head=ggrb_read_tail+1;break;case 14:ggrb_read_tail=now+1;break;}
  CHECK(!ggrb_read_continuation(NULL,false));CHECK(!ggrb_read_valid&&!ggrb_read_max_gap&&!ggrb_read_max_age);
  uint64_t reuses=ggrb_read_reuses;CHECK(!ggrb_read_continuation(NULL,false));CHECK(ggrb_read_reuses==reuses);
 }
 for(unsigned condition=0;condition<11;condition++){
  reset();switch(condition){case 0:ggrb_started=0;break;case 1:thread=0;break;
   case 2:board=0;break;case 3:ggrb_context.state=GGR_FAILED;break;
   case 4:ggrb_live_sample.reason=1;break;case 5:ggrb_end=now;break;
   case 6:ggrb_context.operation_end_ns=now;break;case 7:ggrb_perf.last_live_valid=false;break;
   case 8:ggrb_perf.last_live_begin=ggrb_perf.last_live_end+1;break;
   case 9:now+=5001;break;case 10:ggrb_perf.last_live_begin=0;ggrb_perf.last_live_end=now=250001;break;}
  CHECK(!ggrb_read_continuation(NULL,true));CHECK(!ggrb_read_valid);
 }
 reset();ggrb_context.state=GGR_READY;CHECK(ggrb_read_continuation(NULL,true));
 now++;CHECK(ggrb_read_continuation(NULL,false));CHECK(ggrb_read_max_gap==1);
 /* Actual full-guard wrapper timestamps cannot be rebased by a late stamp. */
 reset();guard_cost=200000;CHECK(ggrb_live(NULL));
 CHECK(ggrb_perf.last_live_begin==1000&&ggrb_perf.last_live_end==201000&&ggrb_perf.last_live_valid);
 CHECK(ggrb_read_continuation(NULL,true));now+=5000;CHECK(ggrb_read_continuation(NULL,false));
 CHECK(ggrb_read_max_gap==5000&&ggrb_read_max_age==205000);
 reset();guard_cost=200000;CHECK(ggrb_live(NULL));now+=5001;
 CHECK(!ggrb_read_continuation(NULL,true)&&!ggrb_read_valid);
 reset();advance_at=2;advance_ticks=300000;CHECK(ggrb_live(NULL));
 CHECK(ggrb_perf.last_live_end-ggrb_perf.last_live_begin==300000);
 CHECK(!ggrb_read_continuation(NULL,true)&&!ggrb_read_valid);
 reset();guard_cost=250000;CHECK(ggrb_live(NULL));CHECK(ggrb_read_continuation(NULL,true));
 now++;CHECK(!ggrb_read_continuation(NULL,false)&&!ggrb_read_valid);
 reset();full_ok=false;CHECK(!ggrb_live(NULL));CHECK(!ggrb_perf.last_live_valid);
 CHECK(!ggrb_read_continuation(NULL,true));
 printf("Actual board continuation/wrapper: %u assertions;5us end/250us start bounds, no late-stamp rebase, one-use/context/deadline/overflow/preemption seams; CPU clocks only\n",checks);
}
'''

def main():
 names=['bsd/dev/gauguin_gpu_runtime.c','bsd/dev/gauguin_gpu_runtime.h','bsd/dev/gauguin_gmu_board.c','iokit/Kernel/arm/GauguinGPU.cpp']
 paths=[Path(__file__),R/'tests/fixtures/gpu-user/runtime_host.c']+[S/n for n in names]+[P/n for n in names]
 pins={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 board=(S/names[2]).read_text();old=(P/names[2]).read_text()
 for sig in ['static bool gfw_faults(','static bool ggrb_live_check(']:assert extract(board,sig)==extract(old,sig)
 wrapper=extract(board,'static bool ggrb_live(')
 assert wrapper.replace('    ggrb_perf.last_live_begin=begin;ggrb_perf.last_live_end=end;\n','').replace('    ggrb_perf.last_live_valid=ok&&end>=begin;\n','')==extract(old,'static bool ggrb_live(')
 assert (S/names[3]).read_bytes()==(P/names[3]).read_bytes()
 a=(S/names[1]).read_text();b=(P/names[1]).read_text();assert a[:a.index('enum ggr_state')]==b[:b.index('enum ggr_state')]
 core=(S/names[0]).read_text()
 for sig in ['static bool wr(','static bool barrier(','static bool delay(']:
  body=extract(core,sig) if '\n{\n' in core[core.index(sig):core.index(sig)+150] else core[core.index(sig):core.index('\n',core.index('\n',core.index(sig))+1)]
  assert 'return alive(c)&&' in body and 'before_read(' not in body
 helper=board[board.index('/* Read-only continuation of'):board.index('static bool ggrb_routes(')]
 perf=board[board.index('struct ggrb_perf_sample {'):board.index('static bool ggrb_micro_settle(',board.index('struct ggrb_perf_sample {'))]
 assert 'gfw_' not in helper and 'gmb_read' not in helper and 'gmb_write' not in helper
 baseline=paths[1].read_text().replace('int main(void)','static int baseline_main(void)',1)
 runtime=baseline+EXTRA
 with tempfile.TemporaryDirectory(prefix='read-cont209-') as d:
  d=Path(d);env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
  for name,body,production in [('runtime',runtime,True),('board',BOARD.replace('@HELPER@',helper).replace('@PERF@',perf).replace('@WRAPPER@',wrapper),False)]:
   unit=d/(name+'.c');unit.write_text(body);cmd=['clang','-std=c11','-Wall','-Wextra','-Werror','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(S/'bsd/dev')]
   if production:cmd.append(str(S/names[0]))
   subprocess.run(cmd+[str(unit),'-o',str(d/name)],check=True,env=env)
   subprocess.run([str(d/name)],check=True,env=env,timeout=60)
 assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
 print('Original full live/clock/SMMU masks and API/BO/PTE/cache code byte-identical; read-side sampling frequency explicitly changes; full write/barrier/delay gates retained')
if __name__=='__main__':main()
