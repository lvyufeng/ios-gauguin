/* Actual digitizer factory and appendChild bodies are inserted by runner. */
#include <cassert>
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <vector>
using UInt64=uint64_t;using UInt32=uint32_t;using IOFixed=int32_t;
using IOOptionBits=uint32_t;using IOHIDDigitizerTransducerType=int;
constexpr int kIOHIDEventTypeDigitizer=1,kIOHIDEventOptionIsAbsolute=2,kIOHIDEventOptionIsCollection=4;
constexpr int kIOHIDDigitizerTransducerTypeFinger=2,kIOHIDDigitizerOrientationTypeQuality=1;
struct Options {unsigned range=0;unsigned raw=0;Options &operator|=(unsigned v){raw|=v;return *this;}};
struct IOHIDDigitizerEventData {
 Options options;UInt32 eventMask=0,transducerIndex=0,transducerType=0,buttonMask=0;
 struct {IOFixed x=0,y=0,z=0;} position;
 IOFixed pressure=0,auxPressure=0,twist=0;
 unsigned identity=0,orientationType=0;
 struct {struct {IOFixed majorRadius=0,minorRadius=0;}quality,polar;}orientation;
};
static bool fail_object,fail_init,fail_array,fail_growth;
static unsigned live,initializations;
struct OSObject {virtual void retain()=0;virtual void release()=0;virtual ~OSObject()=default;};
struct OSArray {
 std::vector<OSObject *> objects;
 static OSArray *withObjects(const OSObject **objects,unsigned count){
  if(fail_array)return nullptr;
  auto *a=new OSArray;for(unsigned i=0;i<count;++i){auto *o=const_cast<OSObject *>(objects[i]);o->retain();a->objects.push_back(o);}return a;
 }
 bool setObject(OSObject *o){if(fail_growth)return false;o->retain();objects.push_back(o);return true;}
 unsigned getCount()const{return (unsigned)objects.size();}
 ~OSArray(){for(auto *o:objects)o->release();}
};
struct IOHIDEvent:OSObject {
 unsigned refs=1;IOHIDDigitizerEventData storage;IOHIDDigitizerEventData *_data=nullptr;OSArray *_children=nullptr;
 static void *operator new(size_t bytes)noexcept {return fail_object?nullptr:std::malloc(bytes);}
 static void operator delete(void *p)noexcept {std::free(p);}
 IOHIDEvent(){++live;}
 ~IOHIDEvent()override{delete _children;--live;}
 void retain()override{++refs;}void release()override{assert(refs);if(!--refs)delete this;}
 bool initWithTypeTimeStamp(int type,UInt64,IOOptionBits options){
  ++initializations;assert(type==kIOHIDEventTypeDigitizer && (options&kIOHIDEventOptionIsAbsolute));
  if(fail_init)return false;_data=&storage;return true;
 }
 static IOHIDEvent *digitizerEvent(UInt64,UInt32,IOHIDDigitizerTransducerType,bool,UInt32,IOFixed,IOFixed,
                                  IOFixed=0,IOFixed=0,IOFixed=0,IOFixed=0,IOOptionBits=0);
 void appendChild(IOHIDEvent *);
};
@FACTORY@
@APPEND@
static IOHIDEvent *event(unsigned id=2){return IOHIDEvent::digitizerEvent(42,id,2,true,1,100,200);}
int main()
{
 fail_object=true;assert(event()==nullptr && !live && !initializations);fail_object=false;
 fail_init=true;assert(event()==nullptr && !live && initializations==1);fail_init=false;
 auto *parent=event(0);auto *first=event();assert(parent && first && live==2);
 assert(first->_data->options.range==1 && first->_data->position.x==100 && first->_data->position.y==200);
 assert(first->_data->transducerIndex==2 && first->_data->identity==2 && first->_data->eventMask==0);
 fail_array=true;parent->appendChild(first);assert(!parent->_children && first->refs==1);fail_array=false;
 parent->appendChild(first);assert(parent->_children->getCount()==1 && first->refs==2);
 auto *second=event(3);fail_growth=true;parent->appendChild(second);
 assert(parent->_children->getCount()==1 && second->refs==1);fail_growth=false;
 parent->appendChild(second);assert(parent->_children->getCount()==2 && second->refs==2);
 first->release();second->release();assert(live==3);parent->release();assert(!live);
 std::puts("PASS: actual digitizer factory null/init failure and actual appendChild array/growth retention semantics");
}
