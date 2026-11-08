/* Execute the complete production admission function with typed OS boundaries.
 * Objective-C method metadata/implementations use the host's real runtime.
 */
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <mach/mach.h>
#include <objc/runtime.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FIXTURE FAIL line=%d: %s\n",__LINE__,#x); exit(1); } } while (0)
extern int gauguin_eagl_admit(void);
static const char *scenario;
static unsigned get8_calls,vm_calls,version_calls,matching_calls,service_calls,releases;
static int is(const char *s) { return strcmp(scenario,s)==0; }
const char *test_getprogname(void) { return is("wrong-program") ? "SpringBoard" : "backboardd"; }
uid_t test_getuid(void) { return is("wrong-uid") ? 0 : 501; }
uid_t test_geteuid(void) { return is("wrong-euid") ? 0 : 501; }
pid_t test_getpid(void) { return 186; }
char *test_getenv(const char *name)
{
    CHECK(strcmp(name,"GAUGUIN_EAGL_MODE")==0);
    return is("mode-render") ? "render" : is("mode-absent") ? NULL : "admission";
}
int test_sysctlbyname(const char *name,void *old,size_t *size,void *newp,size_t newsize)
{
    version_calls++;CHECK(strcmp(name,"kern.osversion")==0 && !newp && !newsize);
    if(is("version-failure")) { errno=ENOENT;return -1; }
    CHECK(*size>=8);memcpy(old,"20H392",7);*size=7;return 0;
}
struct limits { int32_t active;uint32_t aa;int32_t inactive;uint32_t ia; };
int memorystatus_control(uint32_t command,int32_t pid,uint32_t flags,void *buffer,size_t size)
{
    get8_calls++;CHECK(command==8 && pid==186 && !flags && size==16);
    if(is("get8-failure")) { errno=EPERM;return -1; }
    struct limits value={128,1,128,1};memcpy(buffer,&value,sizeof(value));return 0;
}
kern_return_t test_task_info(task_name_t task,task_flavor_t flavor,task_info_t info,mach_msg_type_number_t *count)
{
    vm_calls++;CHECK(task==mach_task_self() && flavor==TASK_VM_INFO && *count==TASK_VM_INFO_REV1_COUNT);
    if(is("vm-failure"))return KERN_FAILURE;
    ((task_vm_info_data_t *)info)->phys_footprint=32128;
    if(is("vm-short"))*count=0;
    return KERN_SUCCESS;
}
CFMutableDictionaryRef test_IOServiceMatching(const char *name)
{
    matching_calls++;CHECK(strcmp(name,"HakiosGPU")==0);
    return CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
}
io_service_t test_IOServiceGetMatchingService(mach_port_t port,CFDictionaryRef dictionary)
{
    service_calls++;CHECK(port==kIOMainPortDefault && dictionary);CFRelease(dictionary);
    return is("service-absent") ? 0 : 186;
}
kern_return_t test_IOObjectRelease(io_object_t object)
{
    releases++;CHECK(object==186);return KERN_SUCCESS;
}
static void untouched(id self,SEL selector) { (void)self;(void)selector; }
int main(int argc,char **argv)
{
    CHECK(argc==2);scenario=argv[1];
    const char *names[]={"initWithAPI:properties:","API","sharegroup","setParameter:to:","getMacroContextPrivate",
        "texImageIOSurface:target:internalFormat:width:height:format:type:plane:invert:","attachImage:toCoreSurface:invertedRender:","dealloc"};
    const char *types[]={"@32@0:8Q16@24","Q16@0:8","@16@0:8","Q28@0:8I16^i20","^{EAGLMacroContext=}16@0:8",
        "B72@0:8^{__IOSurface=}16Q24Q32I40I44Q48Q56I64B68","B36@0:8Q16^{__IOSurface=}24B32","v16@0:8"};
    Class cls=Nil;
    if(!is("class-absent")) {
        cls=objc_allocateClassPair(objc_getClass("NSObject"),"EAGLContext",0);CHECK(cls!=Nil);
        for(unsigned i=0;i<8;i++) {
            if(is("method-absent") && i==5)continue;
            const char *type=is("encoding-mismatch") && i==5 ? "B72@0:8^{__IOSurface=}16Q24Q32i40i44Q48Q56I64B68" : types[i];
            CHECK(class_addMethod(cls,sel_registerName(names[i]),(IMP)untouched,type));
        }
        objc_registerClassPair(cls);
    }
    CHECK(gauguin_eagl_admit()==0);
    unsigned rejected=is("wrong-program")||is("wrong-uid")||is("wrong-euid");
    CHECK(get8_calls==!rejected && vm_calls==!rejected && version_calls==!rejected);
    CHECK(matching_calls==!rejected && service_calls==!rejected);
    CHECK(releases==(!rejected && !is("service-absent")));
    if(cls)for(unsigned i=0;i<8;i++) {
        if(is("method-absent") && i==5)continue;
        CHECK(method_getImplementation(class_getInstanceMethod(cls,sel_registerName(names[i])))==(IMP)untouched);
    }
    printf("FIXTURE PASS case=%s all_original_IMPs_unchanged=1 admitted=0\n",scenario);
    if(cls)objc_disposeClassPair(cls);
    return 0;
}
