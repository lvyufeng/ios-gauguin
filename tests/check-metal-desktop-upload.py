#!/usr/bin/env python3
"""Exercise actual frontend snapshot/deallocator methods with a host allocation transport.

The admission shim here is deliberately modeled. UUID/site policy has its own
test; this test proves neither real QuartzCore invocation nor GPU execution.
"""
from pathlib import Path
import argparse, subprocess

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--expect-refusal',action='store_true')
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    source=a.source.read_text()
    begin=source.index('- (id)newBufferWithBytesNoCopy:')
    # The interface declaration precedes the implementation; locate the actual body.
    while ';' in source[begin:source.index('{',begin)]:
        begin=source.index('- (id)newBufferWithBytesNoCopy:',begin+1)
    end=source.index('\n/* the layout of a texture',begin)
    upload=source[begin:end]
    bb=source.index('@implementation HakiosMetalBuffer')
    begin=source.index('- (void)dealloc',bb)
    end=source.index('- (hakios_metal_buffer *)hakiosBuffer',begin)
    lifetime=source[begin:end]
    code=r'''
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
static bool permit=true, fail_allocation=false;
static unsigned allocations=0, frees=0, callbacks=0;
static bool saw_caller=false;
#define hm_print(...) ((void)0)
#define HM_ONCE(...) ((void)0)
static bool gauguin_metal_desktop_upload(const void *pc,const void *bytes,size_t n,uint64_t opts)
{ saw_caller=pc!=NULL;return permit && bytes && n && !opts; }
static void hakios_metal_buffer_free(void *p) { frees++;free(p); }
@interface HakiosMetalBuffer : NSObject {
@public void *_buffer; id _device; void (^_deallocator)(void *,NSUInteger);
void *_callerBytes; NSUInteger _callerLength;
}
- (void)hakiosSetDeallocator:(void (^)(void *,NSUInteger))d bytes:(void *)b length:(NSUInteger)n;
@end
@implementation HakiosMetalBuffer
LIFETIME
@end
@interface Harness : NSObject
- (id)newBufferWithBytes:(const void *)b length:(NSUInteger)n options:(MTLResourceOptions)o;
- (id)newBufferWithBytesNoCopy:(void *)b length:(NSUInteger)n options:(MTLResourceOptions)o
    deallocator:(void (^)(void *,NSUInteger))d;
@end
@implementation Harness
- (id)newBufferWithBytes:(const void *)bytes length:(NSUInteger)n options:(MTLResourceOptions)o
{
    (void)o;if(fail_allocation)return nil;
    HakiosMetalBuffer *b=[HakiosMetalBuffer new];b->_buffer=malloc(n);memcpy(b->_buffer,bytes,n);allocations++;return b;
}
UPLOAD
@end
static int check(bool value,int line) {if(!value){fprintf(stderr,"line%d failed\n",line);return 1;}return 0;}
#define CHECK(x) do{if(check((x),__LINE__))return 1;}while(0)
int main(void) { @autoreleasepool {
    Harness *h=[Harness new];unsigned char original[256],expected[256];
    for(unsigned i=0;i<256;i++)original[i]=expected[i]=(unsigned char)(i*17+3);
    void *original_address=original;
    void (^done)(void *,NSUInteger)=^(void *p,NSUInteger n){if(p!=original_address||n!=256)abort();callbacks++;};
    HakiosMetalBuffer *b=[h newBufferWithBytesNoCopy:original length:256 options:0 deallocator:done];
    if(EXPECT_REFUSAL) {CHECK(b==nil);CHECK(!allocations&&!frees&&!callbacks);[h release];puts("old diagnostic refuses this upload: expected baseline");return 0;}
    if(!b){fprintf(stderr,"named desktop upload remains refused\n");return 42;}
    CHECK(saw_caller && allocations==1 && callbacks==0);
    CHECK(!memcmp(b->_buffer,expected,256));
    memset(original,0xee,256);CHECK(!memcmp(b->_buffer,expected,256));
    /* Snapshot semantics are explicit: later changes are not shared. */
    [b retain];[b release];CHECK(callbacks==0);[b release];CHECK(callbacks==1 && frees==1);
    permit=false;b=[h newBufferWithBytesNoCopy:original length:256 options:0 deallocator:done];
    CHECK(!b && allocations==1 && callbacks==1);
    permit=true;fail_allocation=true;b=[h newBufferWithBytesNoCopy:original length:256 options:0 deallocator:done];
    CHECK(!b && allocations==1 && callbacks==1);
    fail_allocation=false;b=[h newBufferWithBytesNoCopy:original length:256 options:0 deallocator:nil];
    CHECK(b!=nil);[b release];CHECK(frees==2 && callbacks==1);
    [h release];puts("actual snapshot and deallocator methods passed; host transport; no GPU claim");return 0;
} }
'''.replace('LIFETIME',lifetime).replace('UPLOAD',upload).replace('EXPECT_REFUSAL','1'if a.expect_refusal else'0')
    fixture=a.out/'upload.m';fixture.write_text(code)
    command=['xcrun','--sdk','macosx','clang','-O1','-g','-fblocks','-fno-objc-arc',
             '-fsanitize=address,undefined','-framework','Foundation','-framework','Metal',str(fixture),'-o',str(a.out/'upload')]
    with (a.out/'compile.log').open('x')as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(a.out/'upload')],check=True)

if __name__=='__main__':main()
