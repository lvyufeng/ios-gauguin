#!/usr/bin/env python3
"""Execute the real pipeline-library method with private filesystem and Metal-cache seams."""
from pathlib import Path
import argparse,os,subprocess
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True);ap.add_argument('--expect-refusal',action='store_true')
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);repo=Path(__file__).resolve().parents[1]
    text=a.source.read_text();signature='- (id)newPipelineLibraryWithFilePath:(NSString *)path error:(NSError **)error\n{'
    begin=text.index(signature);method=text[begin:text.index('\n}\n',begin)+3]
    code=r'''
#import <Foundation/Foundation.h>
#import <objc/message.h>
#include <sys/stat.h>
#include <unistd.h>
#include <stdio.h>
#include "GauguinMetalDesktopPolicy.h"
static const char *productionCache=GAUGUIN_METAL_DESKTOP_CACHE_DIRECTORY;
static NSString *privateCache,*oldTemp,*originalPipeline;
static unsigned writes,lookups;static bool originalReady;
struct MTLTargetDeviceArch;
@interface FixtureCache:NSObject {NSString *path;}
- (id)initWithFilePath:(NSString *)p readOnly:(BOOL)ro deviceInfo:(const struct MTLTargetDeviceArch *)info;
- (void)write;
@end
@implementation FixtureCache
- (id)initWithFilePath:(NSString *)p readOnly:(BOOL)ro deviceInfo:(const struct MTLTargetDeviceArch *)info
{(void)info;if((self=[super init])){if(ro)abort();path=[p copy];}return self;}
- (void)write {writes++;[@"host-only-cache-format" writeToFile:path atomically:NO encoding:NSUTF8StringEncoding error:NULL];}
- (void)dealloc {[path release];[super dealloc];}
@end
static Class fixture_cache_class(NSString *name){if(![name isEqualToString:@"_MTLPipelineCache"])abort();return [FixtureCache class];}
@interface Base:NSObject
- (id)newPipelineLibraryWithFilePath:(NSString *)path error:(NSError **)error;
@end
@implementation Base
- (id)newPipelineLibraryWithFilePath:(NSString *)path error:(NSError **)error
{
    lookups++;if(path==nil)return nil;
    NSFileManager *fm=[NSFileManager defaultManager];
    NSString *marker=[path stringByAppendingPathComponent:@"pipelines.host"];
    if(([path isEqualToString:originalPipeline]&&originalReady)||
       (![path isEqualToString:originalPipeline]&&[fm fileExistsAtPath:marker]&&
        [fm fileExistsAtPath:[path stringByAppendingPathComponent:@"functions"]]&&
        [fm fileExistsAtPath:[[path stringByDeletingLastPathComponent]stringByAppendingPathComponent:@"default.metallib"]])){
        if(error)*error=nil;return [NSObject new];
    }
    if(error)*error=[NSError errorWithDomain:@"host-only" code:1 userInfo:@{NSLocalizedDescriptionKey:
        [@"Could not open pipeline cache file: "stringByAppendingString:marker]}];
    return nil;
}
@end
@interface Device:Base
- (const struct MTLTargetDeviceArch *)targetDeviceInfo;
@end
// Rebase only the two storage roots into a private test directory. The actual
// method performs directory creation, links, cache retry and original-result flow.
#undef GAUGUIN_METAL_DESKTOP_CACHE_DIRECTORY
#define GAUGUIN_METAL_DESKTOP_CACHE_DIRECTORY ([privateCache UTF8String])
#define NSTemporaryDirectory() oldTemp
#define NSClassFromString(name) fixture_cache_class(name)
#define hm_print(...) ((void)0)
@implementation Device
- (const struct MTLTargetDeviceArch *)targetDeviceInfo{return NULL;}
METHOD
@end
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"line%d failed\n",__LINE__);return 1;}}while(0)
int main(int argc,char **argv){@autoreleasepool{
    CHECK(argc==2&&geteuid()!=0);CHECK(!strcmp(productionCache,"/private/var/mobile/Library/Caches/gauguin-metal244"));
    NSString *base=[NSString stringWithUTF8String:argv[1]];NSFileManager *fm=[NSFileManager defaultManager];
    privateCache=[base stringByAppendingPathComponent:@"mobile-cache"];
    oldTemp=[base stringByAppendingPathComponent:@"old-root-temp"];
    NSString *old=[oldTemp stringByAppendingPathComponent:@"hakios-pipelinelib"];
    originalPipeline=[base stringByAppendingPathComponent:@"source/QuartzCore.framework/default.pipelinelib"];
    CHECK([fm createDirectoryAtPath:originalPipeline withIntermediateDirectories:YES attributes:nil error:NULL]);
    CHECK([fm createDirectoryAtPath:old withIntermediateDirectories:YES attributes:nil error:NULL]);
    CHECK([fm createDirectoryAtPath:privateCache withIntermediateDirectories:YES attributes:nil error:NULL]);
    for(NSString *name in @[@"pipelines.desc",@"functions"])
        CHECK([@"fixture" writeToFile:[originalPipeline stringByAppendingPathComponent:name]atomically:NO encoding:NSUTF8StringEncoding error:NULL]);
    CHECK([@"matched-library-fixture"writeToFile:[[originalPipeline stringByDeletingLastPathComponent]stringByAppendingPathComponent:@"default.metallib"]atomically:NO encoding:NSUTF8StringEncoding error:NULL]);
    NSString *sentinel=[old stringByAppendingPathComponent:@"untouched"];
    CHECK([@"root-diagnostic"writeToFile:sentinel atomically:NO encoding:NSUTF8StringEncoding error:NULL]);
    CHECK(chmod([old fileSystemRepresentation],0555)==0&&access([old fileSystemRepresentation],W_OK)!=0);
    CHECK(chmod([privateCache fileSystemRepresentation],0700)==0);
    Device *device=[Device new];NSError *error=nil;
    id library=[device newPipelineLibraryWithFilePath:originalPipeline error:&error];
    if(!library){CHECK(error!=nil&&access([old fileSystemRepresentation],W_OK)!=0);puts("old shared-root cache cannot be written: expected functional refusal");return 42;}
    CHECK(error==nil&&writes==1);[library release];
    CHECK([[NSString stringWithContentsOfFile:sentinel encoding:NSUTF8StringEncoding error:NULL]isEqualToString:@"root-diagnostic"]);
    CHECK([fm fileExistsAtPath:[privateCache stringByAppendingPathComponent:@"pipelinelib"]]);
    library=[device newPipelineLibraryWithFilePath:originalPipeline error:&error];
    CHECK(library!=nil&&error==nil&&writes==1);[library release];
    CHECK([fm removeItemAtPath:[privateCache stringByAppendingPathComponent:@"pipelinelib"]error:NULL]);
    CHECK(chmod([privateCache fileSystemRepresentation],0555)==0);
    library=[device newPipelineLibraryWithFilePath:originalPipeline error:&error];
    CHECK(library==nil&&error!=nil);CHECK(chmod([privateCache fileSystemRepresentation],0700)==0);
    originalReady=true;unsigned count=writes;
    library=[device newPipelineLibraryWithFilePath:originalPipeline error:&error];
    CHECK(library!=nil&&error==nil&&writes==count);[library release];
    CHECK([device newPipelineLibraryWithFilePath:nil error:NULL]==nil);
    CHECK([[NSString stringWithContentsOfFile:sentinel encoding:NSUTF8StringEncoding error:NULL]isEqualToString:@"root-diagnostic"]);
    CHECK(chmod([old fileSystemRepresentation],0755)==0);[device release];
    printf("PASS %u actual pipeline-method filesystem assertions; private/warm/unwritable/original/nil paths, modeled Metal cache format\n",checks);return 0;
}}
'''.replace('METHOD',method)
    unit=a.out/'pipeline.m';unit.write_text(code)
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    args=['xcrun','--sdk','macosx','clang','-O1','-g','-fno-objc-arc','-fsanitize=address,undefined',
          '-framework','Foundation','-I'+str(repo/'graphics/hakios-metal-ca/desktop-overlay/userland/src'),str(unit),'-o',str(a.out/'pipeline')]
    with(a.out/'compile.log').open('x')as stream:subprocess.run(args,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    with(a.out/'run.log').open('x')as stream:
        p=subprocess.run([str(a.out/'pipeline'),str(a.out/'filesystem')],env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=30)
    assert p.returncode==(42 if a.expect_refusal else 0),('actual pipeline method',p.returncode)
    print('actual pipeline-cache method passed its expected contract; filesystem/cache format seams, no GPU claim')
if __name__=='__main__':main()
