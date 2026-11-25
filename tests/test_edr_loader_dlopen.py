#!/usr/bin/env python3
"""Exercise the C4 loader through real Darwin dlopen on an owned worker fixture."""
from pathlib import Path
import argparse,hashlib,json,subprocess
WORK=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 out=a.out.resolve();assert out.is_relative_to(WORK/'research/tmp')and not out.exists();out.mkdir(parents=True)
 header=WORK/'graphics/gauguin-edr-loader/GauguinEDRLoader.h'
 pins={str(p):sha(p)for p in (header,Path(__file__).resolve())}
 (out/'fixture.m').write_text('''#import <Foundation/Foundation.h>
#include <pthread.h>
int fixture_init_count,fixture_init_on_worker,fixture_autoreleases_drained;
@interface GauguinLoaderObject:NSObject
@end
@implementation GauguinLoaderObject
- (void)dealloc {fixture_autoreleases_drained++;[super dealloc];}
@end
__attribute__((constructor))static void start(void){fixture_init_count++;fixture_init_on_worker=!pthread_main_np();(void)[[[GauguinLoaderObject alloc]init]autorelease];}
''')
 source=r'''
#import <Foundation/Foundation.h>
#include <assert.h>
#include <dlfcn.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static const char *fixture_path;
static void *loaded;
static unsigned calls;
static const char *fake_name(void){return "backboardd";}
static const char *fake_env(const char *key){assert(!strcmp(key,"GAUGUIN_EAGL_MODE"));return "edr-default318";}
static uid_t fake_uid(void){return 501;}
static double hm_now(void){struct timespec t;assert(!clock_gettime(CLOCK_MONOTONIC,&t));return t.tv_sec+t.tv_nsec/1e9;}
static void *bridge_open(const char *path,int flags){
 assert(!strcmp(path,"/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib"));
 assert(flags==(RTLD_NOW|RTLD_LOCAL));calls++;loaded=dlopen(fixture_path,flags);return loaded;
}
#define getprogname fake_name
#define getenv fake_env
#define getuid fake_uid
#define geteuid fake_uid
#define dlopen bridge_open
'''+f'#include "{header}"\n'+r'''
static void *work(void *unused){(void)unused;@autoreleasepool {gauguin_edr_load_after_completion();gauguin_edr_load_after_completion();}return NULL;}
int main(int argc,char **argv){
 assert(argc==2);fixture_path=argv[1];pthread_t t;assert(!pthread_create(&t,NULL,work,NULL));assert(!pthread_join(t,NULL));
 assert(calls==1&&loaded);int *count=dlsym(loaded,"fixture_init_count"),*worker=dlsym(loaded,"fixture_init_on_worker");
 int *drained=dlsym(loaded,"fixture_autoreleases_drained");assert(count&&*count==1&&worker&&*worker==1&&drained&&*drained==1);assert(!dlclose(loaded));
 puts("{\"state\":\"passed-Darwin-dlopen-ObjC-constructor-and-pool\",\"load_calls\":1,\"constructor_calls\":1,\"constructor_on_worker\":true,\"autoreleases_drained\":1,\"device_commands\":0}");return 0;
}
'''
 (out/'host.m').write_text(source)
 commands=[['xcrun','clang','-std=gnu11','-fno-objc-arc','-framework','Foundation','-O1','-Wall','-Wextra','-Werror','-dynamiclib',str(out/'fixture.m'),'-o',str(out/'fixture.dylib')],
           ['xcrun','clang','-std=gnu11','-fno-objc-arc','-framework','Foundation','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(out/'host.m'),'-o',str(out/'host')]]
 for i,argv in enumerate(commands):
  r=subprocess.run(argv,capture_output=True,text=True);(out/f'compile-{i}.log').write_text(r.stdout+r.stderr);assert r.returncode==0
 r=subprocess.run([str(out/'host'),str(out/'fixture.dylib')],capture_output=True,text=True,timeout=30)
 (out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr);assert r.returncode==0
 assert len(r.stderr.splitlines())==2 and 'identity=1 mode=1' in r.stderr and 'result=opened' in r.stderr
 result=json.loads(r.stdout);result.update(input_pins=pins,iOS_runtime_qualified=False,scope='Real Darwin dlopen/Objective-C constructor and drained autorelease pool on a worker. Fixed device pathname is checked then mapped to an owned local fixture; no iOS library is executed.')
 assert all(sha(Path(p))==v for p,v in pins.items())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
