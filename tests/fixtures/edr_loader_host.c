#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static const char *test_name="backboardd",*test_mode="edr-default318";
static uid_t test_uid=501,test_euid=501;
static unsigned opens,clock_calls;
static int fail_open;
static const char *fake_name(void){return test_name;}
static const char *fake_env(const char *name){assert(!strcmp(name,"GAUGUIN_EAGL_MODE"));return test_mode;}
static uid_t fake_uid(void){return test_uid;}
static uid_t fake_euid(void){return test_euid;}
static double hm_now(void){return 100.0+(double)++clock_calls/1000;}
static void fake_reenter(void);
static void *fake_open(const char *path,int flags){
 assert(!strcmp(path,"/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib"));
 assert(flags==(RTLD_NOW|RTLD_LOCAL));++opens;fake_reenter();usleep(1000);
 return fail_open?NULL:(void *)0x12340;
}
static char *fake_error(void){return "test-loader-error";}
#define getprogname fake_name
#define getenv fake_env
#define getuid fake_uid
#define geteuid fake_euid
#define dlopen fake_open
#define dlerror fake_error
#include "../../graphics/gauguin-edr-loader/GauguinEDRLoader.h"
static void fake_reenter(void){gauguin_edr_load_after_completion();}
static void reset(void){gauguin_edr_loader_attempted=opens=clock_calls=0;fail_open=0;test_name="backboardd";test_mode="edr-default318";test_uid=test_euid=501;}
static void *worker(void *unused){(void)unused;for(int i=0;i<1000;i++)gauguin_edr_load_after_completion();return NULL;}
int main(void){
 unsigned cases=0;
 for(int i=0;i<7;i++){
  reset();
  if(i==0)test_name=NULL;if(i==1)test_name="SpringBoard";if(i==2)test_uid=0;
  if(i==3)test_euid=0;if(i==4)test_mode=NULL;if(i==5)test_mode="admission";if(i==6)test_mode="edr-default317";
  gauguin_edr_load_after_completion();assert(opens==0&&clock_calls==1);
  test_name="backboardd";test_mode="edr-default318";test_uid=test_euid=501;
  gauguin_edr_load_after_completion();assert(opens==0&&clock_calls==1);cases++;
 }
 reset();fail_open=1;gauguin_edr_load_after_completion();assert(opens==1&&clock_calls==2);
 fail_open=0;gauguin_edr_load_after_completion();assert(opens==1&&clock_calls==2);cases++;
 reset();pthread_t threads[16];for(int i=0;i<16;i++)assert(!pthread_create(&threads[i],NULL,worker,NULL));
 for(int i=0;i<16;i++)assert(!pthread_join(threads[i],NULL));assert(opens==1&&clock_calls==2);cases++;
 printf("{\"state\":\"passed-real-C4-loader-policy-and-one-attempt\",\"cases\":%u,\"concurrent_calls\":16000,\"reentrant_load_tested\":true,\"device_commands\":0}\n",cases);
 return 0;
}
