#include <atomic>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <functional>
#include <mutex>
#include <thread>
#include <vector>

using IOOptionBits=unsigned;using IOReturn=int;
#define OSDeclareDefaultStructors(...)
#ifndef __unused
#define __unused __attribute__((unused))
#endif
#define super IOService
static std::atomic<unsigned> live_objects{0},live_arrays{0},array_attempts{0},set_attempts{0};
static std::atomic<bool> fail_array{false},fail_record{false};
static std::atomic<unsigned> fail_set{0};
static thread_local unsigned client_lock_depth;
using IOLock=std::mutex;
static void IOLockLock(IOLock *l){l->lock();++client_lock_depth;}
static void IOLockUnlock(IOLock *l){assert(client_lock_depth);--client_lock_depth;l->unlock();}
template<typename... Args>static void log_ignore(const char *,Args...){ }
#define IOLog(...) log_ignore(__VA_ARGS__)
struct OSObject {
 std::atomic<unsigned> references{1};
 OSObject(){++live_objects;}
 virtual ~OSObject(){--live_objects;}
 bool init(){return true;}
 virtual void retain(){assert(references.fetch_add(1)>0);}
 virtual void release(){unsigned old=references.fetch_sub(1);assert(old);if(old==1)delete this;}
};
template<typename T>static T *allocate_record(){return fail_record?nullptr:new T;}
#define OSTypeAlloc(T) allocate_record<T>()
#define OSDynamicCast(T,p) dynamic_cast<T *>(p)
#define OSSafeReleaseNULL(p) do {if(p){(p)->release();(p)=nullptr;}}while(0)
struct OSArray:OSObject {
 std::vector<OSObject *> objects;
 OSArray(){++live_arrays;}
 ~OSArray()override{for(auto *o:objects)o->release();--live_arrays;}
 static OSArray *withCapacity(unsigned){++array_attempts;return fail_array?nullptr:new OSArray;}
 static OSArray *withArray(const OSArray *source,unsigned cap){
  auto *a=withCapacity(cap);if(!a)return nullptr;
  for(auto *o:source->objects)if(!a->setObject(o)){a->release();return nullptr;}return a;
 }
 bool setObject(OSObject *o){unsigned attempt=++set_attempts;if(fail_set && attempt==fail_set)return false;o->retain();objects.push_back(o);return true;}
 unsigned getCount()const{return (unsigned)objects.size();}
 OSObject *getObject(unsigned i)const{return objects.at(i);}
};
struct IOService:OSObject {
 std::mutex arbitration;
 const char *getName()const{return "fixture";}
 uint64_t getRegistryEntryID()const{return 77;}
 virtual bool handleOpen(IOService *,IOOptionBits,void *){return false;}
 virtual void handleClose(IOService *,IOOptionBits){}
 virtual bool handleIsOpen(const IOService *)const{return false;}
 virtual bool open(IOService *c,IOOptionBits o,void *a){std::lock_guard<std::mutex> guard(arbitration);return handleOpen(c,o,a);}
 virtual void close(IOService *c,IOOptionBits o=0){std::lock_guard<std::mutex> guard(arbitration);if(handleIsOpen(c))handleClose(c,o);}
};
struct IOHIDEvent:OSObject {uint64_t sender=0;void setSenderID(uint64_t id){sender=id;}};
struct IOHIDEventService:IOService {
 using IOService::open;
 using Action=void(*)(OSObject *,OSObject *,void *,OSObject *,IOOptionBits);
 mutable IOLock lock;IOLock *_clientLock=&lock;OSArray *_clients=OSArray::withCapacity(2);
 ~IOHIDEventService()override{assert(_clients);_clients->release();}
 bool open(IOService *,IOOptionBits,void *,Action);
 void close(IOService *,IOOptionBits=0)override;
 bool handleOpen(IOService *,IOOptionBits,void *)override;
 void handleClose(IOService *,IOOptionBits)override;
 bool handleIsOpenLocked(const IOService *)const;
 bool handleIsOpen(const IOService *)const override;
 void dispatchEvent(IOHIDEvent *,IOOptionBits=0);
};
@RECORD@
@METHODS@

struct Client:IOService {
 std::atomic<unsigned> *destroyed;std::atomic<unsigned> calls{0};std::function<void()> body;
 explicit Client(std::atomic<unsigned> &d):destroyed(&d){}
 ~Client()override{assert(!client_lock_depth);++*destroyed;}
};
static void callback(OSObject *target,OSObject *,void *ctx,OSObject *event,IOOptionBits)
{
 assert(!client_lock_depth && ctx==nullptr && static_cast<IOHIDEvent *>(event)->sender==77);
 auto *c=static_cast<Client *>(target);++c->calls;if(c->body)c->body();
}
static void reset_failures(){fail_array=false;fail_record=false;fail_set=0;set_attempts=0;}
static void close_oom_and_no_cycle()
{
 reset_failures();std::atomic<unsigned> destroyed{0};
 auto *owner=new IOHIDEventService;auto *a=new Client(destroyed);auto *b=new Client(destroyed);
 assert(owner->open(a,0,nullptr,callback) && owner->open(b,0,nullptr,callback));
 assert(a->references==1 && b->references==1); /* No open-lifetime retain cycle. */
 auto *unchanged=owner->_clients;unsigned allocations=array_attempts;
 fail_array=true;fail_record=true;fail_set=1;
 owner->close(a);owner->close(a);assert(owner->_clients==unchanged && array_attempts==allocations);
 assert(!owner->handleIsOpen(a) && owner->handleIsOpen(b) && owner->handleIsOpen(nullptr));
 a->release();assert(destroyed==1);
 IOHIDEvent event;owner->dispatchEvent(&event);assert(b->calls==1);
 owner->close(b);assert(!owner->handleIsOpen(nullptr) && array_attempts==allocations);
 b->release();assert(destroyed==2);owner->dispatchEvent(&event);
 reset_failures();owner->release();
}
static void snapshot_close_and_compaction()
{
 reset_failures();std::atomic<unsigned> destroyed{0};
 auto *owner=new IOHIDEventService;auto *a=new Client(destroyed);auto *b=new Client(destroyed);
 auto *later=new Client(destroyed);assert(owner->open(a,0,nullptr,callback));assert(owner->open(b,0,nullptr,callback));
 a->body=[&]{
  owner->close(b);b->release();b=nullptr;assert(destroyed==1);
  assert(owner->open(later,0,nullptr,callback));
  assert(owner->_clients->getCount()==2); /* Old array remains held by dispatcher. */
 };
 IOHIDEvent event;owner->dispatchEvent(&event);assert(a->calls==1 && later->calls==0);
 a->body={};owner->dispatchEvent(&event);assert(a->calls==2 && later->calls==1);
 owner->close(a);owner->close(later);a->release();later->release();owner->release();assert(destroyed==3);
}
static void open_failures_preserve_table()
{
 for(unsigned failure=0;failure<4;++failure){
  reset_failures();std::atomic<unsigned> destroyed{0};
  auto *owner=new IOHIDEventService;auto *a=new Client(destroyed);auto *b=new Client(destroyed);
  assert(owner->open(a,0,nullptr,callback));auto *before=owner->_clients;
  set_attempts=0;if(failure==0)fail_record=true;if(failure==1)fail_array=true;
  if(failure==2)fail_set=1;if(failure==3)fail_set=2;
  assert(!owner->open(b,0,nullptr,callback));assert(owner->_clients==before);
  assert(owner->handleIsOpen(a) && !owner->handleIsOpen(b));
  IOHIDEvent event;owner->dispatchEvent(&event);assert(a->calls==1 && b->calls==0);
  owner->close(a);a->release();b->release();owner->release();assert(destroyed==2);
 }
 reset_failures();
}
static void retained_callback_survives_close()
{
 reset_failures();std::atomic<unsigned> destroyed{0};
 auto *owner=new IOHIDEventService;auto *a=new Client(destroyed);
 std::atomic<bool> entered{false},allow{false};
 a->body=[&]{entered=true;while(!allow.load())std::this_thread::yield();assert(destroyed==0);};
 assert(owner->open(a,0,nullptr,callback));IOHIDEvent event;
 std::thread dispatcher([&]{owner->dispatchEvent(&event);});
 while(!entered.load())std::this_thread::yield();
 assert(a->references==2);fail_array=true;
 owner->close(a);assert(!owner->handleIsOpen(a));a->release();assert(destroyed==0);
 allow=true;dispatcher.join();assert(destroyed==1);
 owner->dispatchEvent(&event);reset_failures();owner->release();
}
static void self_close_and_repeated_open()
{
 reset_failures();std::atomic<unsigned> destroyed{0};auto *owner=new IOHIDEventService;
 for(unsigned i=0;i<40;++i){
  auto *a=new Client(destroyed);assert(owner->open(a,0,nullptr,callback));assert(owner->_clients->getCount()==1);
  a->body=[&]{owner->close(a);a->release();assert(a->references==1);};
  IOHIDEvent event;owner->dispatchEvent(&event);assert(destroyed==i+1 && !owner->handleIsOpen(nullptr));
 }
 owner->release();
}
int main()
{
 close_oom_and_no_cycle();assert(!live_objects && !live_arrays);
 snapshot_close_and_compaction();assert(!live_objects && !live_arrays);
 open_failures_preserve_table();assert(!live_objects && !live_arrays);
 retained_callback_survives_close();assert(!live_objects && !live_arrays);
 self_close_and_repeated_open();assert(!live_objects && !live_arrays);
 std::puts("PASS: actual close without allocation, immutable snapshots, target retention, concurrent/reentrant close and OOM open rollback");
}
