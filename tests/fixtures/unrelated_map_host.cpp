#include "gauguin_gpu_runtime.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <vector>

using UInt32=uint32_t;
using IOOptionBits=uint32_t;
using IOReturn=uint32_t;
constexpr IOReturn kIOReturnSuccess=0, kIOReturnBadArgument=1, kIOReturnNotReady=2, kIOReturnNotPrivileged=3;
struct IOMemoryDescriptor { virtual ~IOMemoryDescriptor()=default; unsigned retains=1; void retain(){++retains;} };
struct IOBufferMemoryDescriptor: IOMemoryDescriptor {};
struct Surface { bool readOnly=false; };
struct gpu_buffer { IOMemoryDescriptor* memory=nullptr; Surface* surface=nullptr; bool pending=false,closePending=false; };
struct gpu_queue { uint32_t id=1,issued=1,completed=0; };
#define OSDynamicCast(type, value) dynamic_cast<type*>(value)
struct FakeLock { int id; } requestLock{1}, gpuLock{2};
FakeLock *gRequests=&requestLock,*gLock=&gpuLock;
std::vector<int> locks;
void IOLockLock(FakeLock* l){assert(l);assert(locks.size()==size_t(l->id-1));locks.push_back(l->id);}
void IOLockUnlock(FakeLock* l){assert(!locks.empty()&&locks.back()==l->id);locks.pop_back();}
uint64_t currentTask=1;
uint64_t current_task(){return currentTask;}
uint64_t mach_absolute_time(){return 1000;}
bool gMapUnrelated=true,gapi_frozen=false;
struct {uint64_t calls,fast,waited,failures;bool overflow;} gMapStats;
unsigned enteredProfiles=0,endedProfiles=0,clockCalls=0,waitCalls=0,healthCalls=0;
bool failWait=false,failHealth=false;
uint64_t gapi_begin(uint32_t selector,uint64_t,uint64_t){assert(selector==0x100&&locks.size()==2);++enteredProfiles;return gapi_frozen?0:1;}
void gapi_end(uint64_t,IOReturn){assert(locks.size()==2);++endedProfiles;}
ggr_context ggrb_context{};
unsigned ggrb_started=1;
bool ggrb_service=true;
uint64_t ggrb_root=0x1003,ggrb_end=10000000000ull,now=1000;
struct {uint32_t reason;} ggrb_live_sample;
uint64_t clockRead(void*){++clockCalls;return now;}
// EXTRACT_PREDICATE
bool sweet_gpu_runtime_ready(){++healthCalls;return !failHealth&&ggrb_context.state==GGR_READY;}

class GauguinGPUUserClient {
public:
 bool fCompositor=true,fAsync=true,fClosed=false;
 uint64_t fTask=1;
 uint32_t fPendingCount=1,fPendingNativeFence=2,fPendingQueueFence=1;
 gpu_queue queue{};
 gpu_queue* fPendingQueue=&queue;
 gpu_buffer target{},other{};
 gpu_buffer* find(uint32_t type){return type==1?&target:nullptr;}
 IOReturn finishPending(bool wait,bool reap){
  assert(wait&&reap&&locks.size()==2);++waitCalls;
  if(failWait)return kIOReturnNotReady;
  fPendingCount=0;target.pending=false;other.pending=false;
  if(fPendingQueue)fPendingQueue->completed=fPendingQueue->issued;
  ggrb_context.state=GGR_READY;ggrb_context.completed=ggrb_context.submitted;
  ggrb_context.pending_deadline_ns=0;
  return kIOReturnSuccess;
 }
 IOReturn baseline(UInt32,IOOptionBits*,IOMemoryDescriptor**);
 IOReturn candidate(UInt32,IOOptionBits*,IOMemoryDescriptor**);
};
GauguinGPUUserClient* gOwner=nullptr;
// EXTRACT_BASELINE
// EXTRACT_CANDIDATE

IOBufferMemoryDescriptor owned,otherOwned;
IOMemoryDescriptor foreign;
Surface surface;
GauguinGPUUserClient client;
unsigned checks=0,cases=0;
void check(bool condition){++checks;assert(condition);}
void reset(){
 assert(locks.empty());client=GauguinGPUUserClient{};client.fPendingQueue=&client.queue;gOwner=&client;
 owned.retains=otherOwned.retains=foreign.retains=1;surface.readOnly=false;
 client.target.memory=&owned;client.other.memory=&otherOwned;client.other.pending=true;
 ggrb_context={};ggrb_context.state=GGR_BUSY;ggrb_context.submitted=2;ggrb_context.completed=1;
 ggrb_context.pending_wptr=30;ggrb_context.pending_deadline_ns=2000001000ull;
 ggrb_context.ops.nanoseconds=clockRead;
 ggrb_started=1;ggrb_service=true;ggrb_root=0x1003;ggrb_end=10000000000ull;now=1000;ggrb_live_sample.reason=0;
 gMapUnrelated=true;gapi_frozen=false;gMapStats={};currentTask=1;gLock=&gpuLock;
 enteredProfiles=endedProfiles=clockCalls=waitCalls=healthCalls=0;failWait=failHealth=false;
}
struct Observation {IOReturn result;bool outputChanged;unsigned ownedRefs,otherRefs,foreignRefs,waits,health;uint32_t pending,state;bool otherPending;};
Observation invoke(bool candidate,uint32_t type=1,bool nullOptions=false,bool nullMemory=false){
 IOMemoryDescriptor* output=nullptr;IOOptionBits options=999;
 auto result=candidate?client.candidate(type,nullOptions?nullptr:&options,nullMemory?nullptr:&output):client.baseline(type,nullOptions?nullptr:&options,nullMemory?nullptr:&output);
 check(locks.empty());check(enteredProfiles==endedProfiles);
 check(result==kIOReturnSuccess?(output==client.target.memory&&options==0):(output==nullptr&&options==999));
 return {result,output!=nullptr,owned.retains,otherOwned.retains,foreign.retains,waitCalls,healthCalls,client.fPendingCount,ggrb_context.state,client.other.pending};
}
void equivalent(const std::function<void()>& alter,uint32_t type=1,bool nullOptions=false,bool nullMemory=false){
 reset();alter();auto old=invoke(false,type,nullOptions,nullMemory);
 reset();alter();auto current=invoke(true,type,nullOptions,nullMemory);
 check(old.result==current.result&&old.outputChanged==current.outputChanged&&old.ownedRefs==current.ownedRefs&&old.otherRefs==current.otherRefs&&old.foreignRefs==current.foreignRefs);
 check(old.waits==current.waits&&old.health==current.health&&old.pending==current.pending&&old.state==current.state&&old.otherPending==current.otherPending);
 check(gMapStats.fast==0);++cases;
}
int main(){
 reset();auto old=invoke(false);check(old.waits==1&&old.health==1&&old.result==0);
 reset();auto context=ggrb_context;auto q=client.queue;auto current=invoke(true);
 check(current.result==0&&current.waits==0&&current.health==0&&clockCalls==1);
 check(current.pending==1&&current.otherPending&&otherOwned.retains==1&&owned.retains==2);
 check(std::memcmp(&context,&ggrb_context,sizeof(context))==0&&std::memcmp(&q,&client.queue,sizeof(q))==0);
 check(gMapStats.calls==1&&gMapStats.fast==1&&gMapStats.waited==0&&gMapStats.failures==0);++cases;
 equivalent([]{gMapUnrelated=false;});
 equivalent([]{client.fCompositor=false;});
 equivalent([]{client.fAsync=false;});
 equivalent([]{client.fClosed=true;});
 equivalent([]{gOwner=nullptr;});
 equivalent([]{currentTask=2;});
 equivalent([]{gLock=nullptr;});
 equivalent([]{},0);equivalent([]{},2);equivalent([]{},1,true);equivalent([]{},1,false,true);
 equivalent([]{client.target.pending=true;});
 equivalent([]{client.target.closePending=true;});
 equivalent([]{client.target.memory=&foreign;});
 equivalent([]{client.target.surface=&surface;});
 equivalent([]{client.target.surface=&surface;surface.readOnly=true;});
 equivalent([]{client.fPendingCount=0;ggrb_context.state=GGR_READY;});
 equivalent([]{client.fPendingCount=GGR_MAX_BUFFERS+1;});
 equivalent([]{client.fPendingQueue=nullptr;});
 equivalent([]{client.fPendingNativeFence=0;});
 equivalent([]{client.fPendingNativeFence=3;});
 equivalent([]{client.fPendingQueueFence=0;});
 equivalent([]{client.queue.issued=2;});
 equivalent([]{client.queue.completed=1;});
 equivalent([]{client.queue.completed=UINT32_MAX;});
 equivalent([]{client.queue.issued=client.fPendingQueueFence=3;client.queue.completed=0;});
 equivalent([]{ggrb_started=0;});equivalent([]{ggrb_service=false;});equivalent([]{ggrb_root=0;});
 equivalent([]{ggrb_live_sample.reason=1;failWait=true;});
 equivalent([]{ggrb_context.state=GGR_COLD;failWait=true;});
 equivalent([]{ggrb_context.state=GGR_READY;});
 equivalent([]{ggrb_context.state=GGR_FAILED;failWait=true;});
 equivalent([]{ggrb_context.last_error=GGR_IO;failWait=true;});
 equivalent([]{ggrb_context.completed=UINT32_MAX;failWait=true;});
 equivalent([]{ggrb_context.submitted=3;});
 equivalent([]{ggrb_context.completed=0;});
 equivalent([]{ggrb_context.pending_wptr=8192;});
 equivalent([]{ggrb_context.pending_deadline_ns=0;});
 equivalent([]{ggrb_context.ops.nanoseconds=nullptr;});
 equivalent([]{now=0;});equivalent([]{now=ggrb_context.pending_deadline_ns;});
 equivalent([]{now=ggrb_context.pending_deadline_ns+1;});equivalent([]{ggrb_end=now;});
 equivalent([]{client.target.pending=true;failWait=true;});
 equivalent([]{gMapUnrelated=false;failHealth=true;});
 // Wrap position zero is valid; this is not a completion or fence advance.
 reset();ggrb_context.pending_wptr=0;check(invoke(true).waits==0);++cases;
 // Counters cannot alter decisions, overflow or an already-frozen prefix.
 reset();gMapStats.calls=UINT64_MAX;check(invoke(true).waits==0);check(gMapStats.overflow&&gMapStats.calls==UINT64_MAX);++cases;
 reset();gapi_frozen=true;check(invoke(true).waits==0);check(gMapStats.calls==0);++cases;
 printf("{\"state\":\"MAP324-actual-method-and-predicate-host-passed\",\"cases\":%u,\"checks\":%u,\"baseline_waited_for_unrelated_job\":true,\"candidate_preserved_pending_ownership\":true,\"noneligible_behaviors_equal\":true,\"actual_GPU_calls\":0,\"device_commands\":0}\n",cases,checks);
}
