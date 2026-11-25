// Actual queue enqueue, notification, observation and client enqueue bodies.
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
#include "gauguin_ui_trace.h"
#define GAUGUIN 1
#define super HostSharedQueue
#define ALIGNED_DATA_SIZE(value,alignment) (((value)+(alignment)-1)&~((alignment)-1))
#define DATA_QUEUE_ENTRY_HEADER_SIZE offsetof(IODataQueueEntry,data)
#define os_add_overflow(a,b,out) __builtin_add_overflow((a),(b),(out))
#define IOHID_DEBUG(...) ((void)0)
#define HIDLogError(...) ((void)0)
using UInt8=uint8_t;using UInt32=uint32_t;using UInt64=uint64_t;
using IOByteCount=uint64_t;using Boolean=bool;
enum {kIOHIDEventTypeDigitizer=11,kIOHIDEventTimestampTypeAbsolute=0,
      kIOHIDEventOptionContinuousTime=1,kIOHIDDebugCode_HIDEventServiceEnqueueFail=1,
      kHIDDispatchOptionDeliveryNotificationSuppress=2,kHIDDispatchOptionDeliveryNotificationForce=4,
      kIOHIDEventServiceQueueOptionNotificationForce=1,kIOHIDEventServiceQueueOptionNoFullNotification=2};
struct IODataQueueEntry {UInt32 size;UInt8 data[1];};
struct QueueMemory {UInt32 queueSize,head,tail;IODataQueueEntry queue[512];};
struct IOHIDEvent {
    UInt64 stamp=100,size=32;UInt32 type=kIOHIDEventTypeDigitizer,options=0;
    UInt64 getLength(){return size;}
    UInt32 getType(){return type;}
    UInt32 getOptions(){return options;}
    UInt64 getTimeStampOfType(int){return stamp;}
    void readBytes(void *out,UInt64 length){assert(length==size&&length<=4096);memset(out,0x5a,(size_t)length);}
};
struct HostSharedQueue {
    QueueMemory storage={};QueueMemory *dataQueue=&storage;unsigned notificationAttempts=0;
    UInt32 getQueueSize(){return dataQueue->queueSize;}
    void sendDataAvailableNotification(){++notificationAttempts;}
};
struct IOHIDEventServiceQueue:HostSharedQueue {
    UInt32 _options=0;UInt64 _notificationCount=0;void *_owner=nullptr;
    Boolean enqueueEvent(IOHIDEvent *);
    void sendDataAvailableNotification();
    bool copyTraceState(UInt32 *,UInt32 *,UInt32 *,UInt64 *);
};
struct IOHIDEventServiceUserClient {
    IOHIDEventServiceQueue *_queue=nullptr;void *_queuePort=nullptr;
    UInt32 _tracePID=57,_lastEventType=0,_droppedEventCount=0;
    UInt64 _eventCount=0,_lastEventTime=0,_lastDroppedEventTime=0;
    UInt64 getRegistryEntryID(){return 0x100001234ULL;}
    void enqueueEventGated(IOHIDEvent *);
};
static UInt64 clockTicks;
static UInt64 mach_continuous_time(){return ++clockTicks;}
static std::vector<gut_event> observed;
extern "C" void sweet_ui_trace_record(UInt32 kind,UInt64 id,UInt32 pid,UInt32 flags,UInt64 a,UInt64 b,UInt64 c)
{observed.push_back({observed.size()+1,++clockTicks,id,kind,pid,flags,0,a,b,c});}
@QUEUE_METHODS@
@CLIENT_METHOD@
static unsigned checks;
static void check(bool ok){++checks;assert(ok);}
int main(){
    IOHIDEventServiceQueue queue;queue.storage.queueSize=256;
    IOHIDEventServiceUserClient client;client._queue=&queue;client._queuePort=(void *)1;
    IOHIDEvent event;
    client.enqueueEventGated(&event);
    check(client._eventCount==1&&client._droppedEventCount==0&&observed.size()==2);
    check(queue.storage.head==0&&queue.storage.tail==36&&queue.notificationAttempts==1);
    auto old=observed[0],sample=observed[1];
    check(old.kind==GUT_HID_ENQUEUE&&old.flags==1&&old.a==1&&old.b==0&&old.c==0);
    check(sample.kind==GUT_HID_QUEUE_STATE&&sample.id==client.getRegistryEntryID()&&sample.pid==57&&sample.flags==3&&sample.a==36&&sample.b==256&&sample.c==1);
    UInt32 head=999,tail=999,capacity=999;UInt64 attempts=999;
    auto before=queue.storage;check(queue.copyTraceState(&head,&tail,&capacity,&attempts));
    check(head==0&&tail==36&&capacity==256&&attempts==1);
    check(!memcmp(&before,&queue.storage,sizeof(before))&&queue.notificationAttempts==1);

    // Simulate the consumer advancing head. Observation itself never advances it.
    queue.storage.head=36;observed.clear();event.stamp=200;client.enqueueEventGated(&event);
    check(observed.size()==2&&observed[1].a==((UInt64)36<<32|72));
    check(observed[1].c==2&&queue.notificationAttempts==2&&queue.storage.head==36);

    // A nonnull registration is separate from a notification attempt/result.
    client._queuePort=nullptr;observed.clear();client.enqueueEventGated(&event);
    check(observed.size()==2&&observed[1].flags==1&&observed[1].c==2);

    // Full and invalid-index paths retain the original result and counters.
    queue.storage.head=0;queue.storage.tail=252;observed.clear();client._queuePort=(void *)1;
    client.enqueueEventGated(&event);
    check(client._droppedEventCount==1&&observed.size()==2&&observed[0].flags==0&&observed[1].flags==2);
    check(queue.storage.head==0&&queue.storage.tail==252&&observed[1].c==3);
    queue.storage.head=257;observed.clear();client.enqueueEventGated(&event);
    check(client._droppedEventCount==2&&observed[1].a==((UInt64)257<<32|252)&&observed[1].c==3);
    queue.storage.head=100;queue.storage.tail=252;observed.clear();client.enqueueEventGated(&event);
    check(client._droppedEventCount==2&&queue.storage.tail==36&&observed[1].a==((UInt64)100<<32|36)&&observed[1].c==3);

    // Non-digitizer events and an absent queue generate no extra UI evidence.
    queue.storage.head=queue.storage.tail=0;observed.clear();event.type=2;
    client.enqueueEventGated(&event);check(observed.empty()&&queue.storage.tail==36);
    client._queue=nullptr;UInt64 count=client._eventCount;client.enqueueEventGated(&event);
    check(client._eventCount==count&&observed.empty());

    // Getter refusal changes neither output sentinels nor the queue.
    head=tail=capacity=999;attempts=999;
    check(!queue.copyTraceState(nullptr,&tail,&capacity,&attempts));
    check(head==999&&tail==999&&capacity==999&&attempts==999);
    queue.dataQueue=nullptr;check(!queue.copyTraceState(&head,&tail,&capacity,&attempts));
    check(head==999&&tail==999&&capacity==999&&attempts==999);
    printf("PASS actual HID queue observation checks=%u; no new dequeue or notification, host only\n",checks);
}
