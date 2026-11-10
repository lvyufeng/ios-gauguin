#include <IOKit/SweetHIDTouchFrame.h>
#include <cassert>
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <functional>
#include <map>
#include <mutex>
#include <thread>
#include <vector>
#ifdef TEST_UI_TRACE
#include "gauguin_ui_trace.h"
struct trace_note {uint32_t kind;uint64_t id,event_time;};
static std::vector<trace_note> trace_notes;
extern "C" void sweet_ui_trace_record(uint32_t k,uint64_t id,uint32_t pid,uint32_t f,uint64_t a,uint64_t b,uint64_t c)
{assert(!pid&&!b&&!c);(void)f;trace_notes.push_back({k,id,a});}
#endif

using UInt32=uint32_t; using IOFixed=int32_t; using IOReturn=int;
constexpr int kIOReturnSuccess=0,kIOReturnBadArgument=-1,kIOReturnNotReady=-2,kIOReturnNoMemory=-3,kIOReturnBusy=-4;
constexpr int TRUE=1,kOSBooleanTrue=1,kHIDPage_Digitizer=13,kHIDUsage_Dig_TouchScreen=4;
constexpr int kIOHIDDigitizerTransducerTypeHand=1,kIOHIDDigitizerTransducerTypeFinger=2;
enum {kIOHIDEventFieldDigitizerCollection,kIOHIDEventFieldDigitizerIndex,kIOHIDEventFieldDigitizerIdentity,
 kIOHIDEventFieldDigitizerTouch,kIOHIDEventFieldDigitizerEventMask,kIOHIDEventFieldDigitizerX,
 kIOHIDEventFieldDigitizerY,kIOHIDEventFieldDigitizerRange,kIOHIDEventFieldDigitizerButtonMask};
constexpr uint32_t kIOHIDDigitizerEventFromEdgeTip=1,kIOHIDDigitizerEventTouch=2,kIOHIDDigitizerEventRange=4,
 kIOHIDDigitizerEventPosition=8,kIOHIDDigitizerEventIdentity=16;
#define OSDeclareDefaultStructors(...)
#define APPLE_KEXT_OVERRIDE override
#define IOLog(...) ((void)0)
static std::atomic<uint64_t> ticks{0};
static uint64_t mach_absolute_time(){return ++ticks;}
static bool native_geometry;
static bool PE_parse_boot_argn(const char *name,void *p,size_t n)
{assert(!strcmp(name,"sweetfb_native") && n==sizeof(int));*(int *)p=native_geometry;return true;}
struct OSObject {
 std::atomic<int> references{1};
 virtual ~OSObject(){assert(references==1);}
 void retain(){assert(references.fetch_add(1)>=1);}
 void release(){assert(references.fetch_sub(1)>1);}
};
using IOLock=std::mutex;
static IOLock *IOLockAlloc(){return new IOLock;}
static void IOLockFree(IOLock *lock){delete lock;}
static void IOLockLock(IOLock *lock){lock->lock();}
static void IOLockUnlock(IOLock *lock){lock->unlock();}
struct IOService:OSObject{};
struct IOCommandGate {
 using Action=IOReturn(*)(OSObject *,void *,void *,void *,void *);
 OSObject *owner;std::recursive_mutex mutex;
 explicit IOCommandGate(OSObject *o):owner(o){}
 IOReturn runAction(Action f,void *p=nullptr){std::lock_guard<std::recursive_mutex> guard(mutex);return f(owner,p,nullptr,nullptr,nullptr);}
};
struct OSArray {
 std::vector<OSObject *> values;
 unsigned getCount()const{return (unsigned)values.size();}
 OSObject *getObject(unsigned i)const{return values.at(i);}
};
static int live_events,allocations,fail_allocation,appends,fail_append;
struct IOHIDEvent:OSObject {
 int refs=1;uint64_t time;uint32_t transducer;std::map<int,int64_t> fields;OSArray children;
 IOHIDEvent(uint64_t t,uint32_t id):time(t),transducer(id){++live_events;}
 ~IOHIDEvent(){for(auto *p:children.values)((IOHIDEvent *)p)->release();--live_events;}
 static IOHIDEvent *digitizerEvent(uint64_t t,UInt32 id,int,bool range,UInt32 buttons,IOFixed x,IOFixed y){
  if(++allocations==fail_allocation)return nullptr;
  auto *e=new IOHIDEvent(t,id);e->fields[kIOHIDEventFieldDigitizerRange]=range;
  e->fields[kIOHIDEventFieldDigitizerButtonMask]=buttons;e->fields[kIOHIDEventFieldDigitizerX]=x;e->fields[kIOHIDEventFieldDigitizerY]=y;return e;
 }
 void retain(){++refs;}void release(){assert(refs>0);if(!--refs)delete this;}
 void setIntegerValue(int k,int64_t v){fields[k]=v;}void setFixedValue(int k,IOFixed v){fields[k]=v;}
 void appendChild(IOHIDEvent *e){if(++appends==fail_append)return;e->retain();children.values.push_back(e);}
 OSArray *getChildren(){return children.values.empty()?nullptr:&children;}
};
struct Recorded {
 uint64_t time;std::map<int,int64_t> fields;std::vector<Recorded> children;
 static Recorded copy(IOHIDEvent *e){Recorded r{e->time,e->fields,{}};for(auto *p:e->children.values)r.children.push_back(copy((IOHIDEvent *)p));return r;}
};
struct IOHIDEventService:IOService {
 IOCommandGate *_hidGate=nullptr;std::vector<Recorded> delivered;std::function<void()> callback;
 virtual bool start(IOService *){_hidGate=new IOCommandGate(this);return true;}
 virtual void stop(IOService *){}
 virtual UInt32 getPrimaryUsagePage(){return 0;}virtual UInt32 getPrimaryUsage(){return 0;}virtual UInt32 getProductID(){return 0;}
 template<typename... A>void setProperty(A...){ }void registerService(){}
 void dispatchEvent(IOHIDEvent *e){delivered.push_back(Recorded::copy(e));if(callback)callback();}
 ~IOHIDEventService(){delete _hidGate;}
};

@CLASS@
static SweetHIDTouch *gSweetTouch;
@PUBLICATION@
@START@
@METHODS@
@CAPI@
struct TestTouch:SweetHIDTouch {~TestTouch(){stop(nullptr);}};

static sweet_hid_touch_snapshot frame(uint32_t mask,int x=500,int y=1000)
{sweet_hid_touch_snapshot s{};s.active_mask=mask;for(int i=0;i<10;++i){s.x[i]=x;s.y[i]=y;}return s;}
static const Recorded &child(const Recorded &r,int index)
{for(const auto &c:r.children)if(c.fields.at(kIOHIDEventFieldDigitizerIndex)==index)return c;assert(false);return r;}
static bool flag(const Recorded &r,int bit){return (r.fields.at(kIOHIDEventFieldDigitizerEventMask)&bit)!=0;}
static void check_frame(const Recorded &r)
{assert(r.fields.at(kIOHIDEventFieldDigitizerCollection)==1);for(auto &c:r.children)assert(c.time==r.time);}
static void setup(SweetHIDTouch &h,bool native=false)
{native_geometry=native;assert(h.start(nullptr));assert(h.delivered.empty());allocations=appends=fail_allocation=fail_append=0;assert(live_events==0);}

static void replacement_and_legacy()
{
 TestTouch h;setup(h);auto empty=frame(0);auto a=frame(1,0,0);
 uint64_t before=ticks;assert(sweet_hid_touch_frame(&empty)==0 && ticks==before);
 assert(sweet_hid_touch_frame(&a)==0 && h.delivered.size()==1 && ticks==before+1);check_frame(h.delivered.back());
 const auto &first=child(h.delivered.back(),0);
 assert(first.fields.at(kIOHIDEventFieldDigitizerX)==1281 && first.fields.at(kIOHIDEventFieldDigitizerY)==484);
 assert(first.fields.at(kIOHIDEventFieldDigitizerIdentity)==2 && flag(first,kIOHIDDigitizerEventIdentity));
 assert(sweet_hid_touch_frame(&a)==0 && h.delivered.size()==1);
 auto b=frame(1u<<9,2000,3000);assert(sweet_hid_touch_frame(&b)==0 && h.delivered.size()==2);
 auto &r=h.delivered.back();check_frame(r);assert(r.children.size()==2 && r.fields.at(kIOHIDEventFieldDigitizerTouch)==1);
 assert(child(r,0).fields.at(kIOHIDEventFieldDigitizerTouch)==0 && flag(child(r,0),kIOHIDDigitizerEventRange));
 assert(child(r,9).fields.at(kIOHIDEventFieldDigitizerTouch)==1 && flag(child(r,9),kIOHIDDigitizerEventIdentity));
 assert(child(r,9).fields.at(kIOHIDEventFieldDigitizerX)==64137 && child(r,9).fields.at(kIOHIDEventFieldDigitizerY)==65024);
 h.touch(4,true,500,1000);assert(h.delivered.back().children.size()==2);
 assert(child(h.delivered.back(),9).fields.at(kIOHIDEventFieldDigitizerTouch)==1);
 h.touch(4,false,-100,-100);assert(child(h.delivered.back(),9).fields.at(kIOHIDEventFieldDigitizerTouch)==1);
 assert(sweet_hid_touch_frame(&empty)==0 && h.delivered.back().fields.at(kIOHIDEventFieldDigitizerTouch)==0);
 assert(h.delivered.back().children.size()==1 && child(h.delivered.back(),9).fields.at(kIOHIDEventFieldDigitizerX)==64137);
 assert(live_events==0);
}
static void masks_geometry_and_errors()
{
 TestTouch h;setup(h,true);auto s=frame(3,0,0);assert(sweet_hid_touch_frame(&s)==0);
 assert(child(h.delivered.back(),0).fields.at(kIOHIDEventFieldDigitizerX)==0);
 s.x[0]=400;s.y[0]=800;assert(sweet_hid_touch_frame(&s)==0);
 assert(flag(child(h.delivered.back(),0),kIOHIDDigitizerEventFromEdgeTip));
 assert(flag(child(h.delivered.back(),0),kIOHIDDigitizerEventPosition));
 assert(!flag(child(h.delivered.back(),0),kIOHIDDigitizerEventIdentity));
 auto empty=frame(0);assert(sweet_hid_touch_frame(&empty)==0);
 assert(flag(child(h.delivered.back(),0),kIOHIDDigitizerEventFromEdgeTip));
 s=frame(1);assert(sweet_hid_touch_frame(&s)==0);
 assert(!flag(child(h.delivered.back(),0),kIOHIDDigitizerEventFromEdgeTip));
 size_t count=h.delivered.size();s.active_mask=1u<<10;
 assert(sweet_hid_touch_frame(&s)==kIOReturnBadArgument && h.delivered.size()==count);
 assert(sweet_hid_touch_frame(nullptr)==kIOReturnBadArgument);
 h.touch(-1,true,0,0);h.touch(10,true,0,0);assert(h.delivered.size()==count);
 h.stop(nullptr);s.active_mask=1;assert(sweet_hid_touch_frame(&s)==kIOReturnNotReady);
}
static void stop_lifecycle()
{
 TestTouch h;setup(h);auto s=frame(1);
 auto *retained=sweetTouchCopyService();assert(retained==&h && h.references==3);
 h.stop(nullptr);assert(!gSweetTouch && h.references==2);
 assert(sweet_hid_touch_frame(&s)==kIOReturnNotReady);
 assert(retained->touchFrame(&s)==kIOReturnNotReady && h.delivered.empty());
 retained->release();assert(h.references==1);
 h.touch(0,true,1,1);sweet_hid_touch(0,1,1,1);assert(h.delivered.empty());
 TestTouch next;setup(next);assert(sweet_hid_touch_frame(&s)==0);
 assert(next.references==2 && h.references==1);
 /* A second published service is rejected without replacing the first. */
 TestTouch duplicate;assert(!duplicate.start(nullptr));assert(gSweetTouch==&next && duplicate.references==1);
 next.stop(nullptr);assert(!gSweetTouch && next.references==1);
}
static void concurrent_stop()
{
 TestTouch h;setup(h);auto s=frame(1);std::atomic<bool> entered{false},allow{false},stopped{false};
 h.callback=[&]{entered=true;while(!allow.load())std::this_thread::yield();};
 std::thread input([&]{assert(sweet_hid_touch_frame(&s)==0);});
 while(!entered.load())std::this_thread::yield();
 std::thread stopping([&]{h.stop(nullptr);stopped=true;});
 for(;;){auto *copy=sweetTouchCopyService();if(!copy)break;copy->release();std::this_thread::yield();}
 assert(!stopped.load() && sweet_hid_touch_frame(&s)==kIOReturnNotReady);
 allow=true;input.join();stopping.join();
 assert(stopped && h.references==1 && h.delivered.size()==1);
 assert(sweet_hid_touch_frame(&s)==kIOReturnNotReady);
}
static void allocation_rollback()
{
 for(int which=1;which<=5;++which){
  TestTouch h;setup(h);auto old=frame(1),next=frame(2|4);
  assert(sweet_hid_touch_frame(&old)==0);size_t count=h.delivered.size();allocations=appends=0;
  if(which<=3)fail_allocation=which;else fail_append=which-3;
  assert(sweet_hid_touch_frame(&next)==kIOReturnNoMemory && h.delivered.size()==count && live_events==0);
  fail_allocation=fail_append=0;allocations=appends=0;
  assert(sweet_hid_touch_frame(&next)==0 && h.delivered.size()==count+1);
  assert(child(h.delivered.back(),0).fields.at(kIOHIDEventFieldDigitizerTouch)==0);
  assert(flag(child(h.delivered.back(),1),kIOHIDDigitizerEventIdentity));
  assert(flag(child(h.delivered.back(),2),kIOHIDDigitizerEventIdentity));
  assert(live_events==0);
 }
}
static void reentry_and_ordering()
{
 TestTouch h;setup(h);auto one=frame(1),two=frame(2);int nested=0;
 h.callback=[&]{nested=sweet_hid_touch_frame(&two);};
 assert(sweet_hid_touch_frame(&one)==0 && nested==kIOReturnBusy && h.delivered.size()==1);
 h.callback={};assert(sweet_hid_touch_frame(&two)==0 && h.delivered.size()==2);
 assert(child(h.delivered.back(),0).fields.at(kIOHIDEventFieldDigitizerTouch)==0);
 auto empty=frame(0);assert(sweet_hid_touch_frame(&empty)==0);h.delivered.clear();
 std::thread a([&]{for(int i=0;i<30;++i)h.touch(0,true,100+i,100);});
 std::thread b([&]{for(int i=0;i<30;++i)h.touch(1,true,500+i,800);});
 a.join();b.join();assert(h.delivered.size()==60);
 uint64_t prior=0;for(auto &r:h.delivered){check_frame(r);assert(r.time>prior);prior=r.time;assert(r.fields.at(kIOHIDEventFieldDigitizerTouch)==1);}
 assert(sweet_hid_touch_frame(&empty)==0 && h.delivered.back().children.size()==2);
 assert(live_events==0);
}
#ifdef TEST_UI_TRACE
static void trace_identity()
{
 TestTouch h;setup(h);auto s=frame(1);trace_notes.clear();
 assert(sweet_hid_touch_frame_traced(&s,123)==0&&trace_notes.size()==2);
 assert(trace_notes[0].kind==GUT_HID_BEGIN&&trace_notes[1].kind==GUT_HID_END);
 assert(trace_notes[0].id==123&&trace_notes[1].id==123&&trace_notes[0].event_time==trace_notes[1].event_time);
 trace_notes.clear();assert(sweet_hid_touch_frame_traced(&s,124)==0&&trace_notes.empty());
 s.x[0]++;assert(sweet_hid_touch_frame(&s)==0&&trace_notes.empty());
 auto next=frame(2);h.callback=[&]{assert(sweet_hid_touch_frame_traced(&s,999)==kIOReturnBusy);};
 assert(sweet_hid_touch_frame_traced(&next,125)==0&&trace_notes.size()==2);
 assert(trace_notes[0].id==125&&trace_notes[1].id==125);h.callback={};
 trace_notes.clear();fail_allocation=1;allocations=0;
 assert(sweet_hid_touch_frame_traced(&s,126)==kIOReturnNoMemory&&trace_notes.empty());
 fail_allocation=0;allocations=0;
}
#endif
int main()
{
 replacement_and_legacy();stop_lifecycle();concurrent_stop();masks_geometry_and_errors();allocation_rollback();reentry_and_ordering();
#ifdef TEST_UI_TRACE
 trace_identity();
#endif
 puts("PASS: actual HID frame builder, geometry, identity/edge/up, allocation rollback, reentry, producer ordering and stop lifetime");
}
