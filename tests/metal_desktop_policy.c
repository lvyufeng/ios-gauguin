/* Current-system compositor admission and upload boundaries. MIT. */
#include "../graphics/hakios-metal-ca/desktop-overlay/userland/src/GauguinMetalDesktopPolicy.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { count++; if (!(x)) { fprintf(stderr,"line %d failed\n",__LINE__); return 1; } } while (0)
int main(void)
{
    unsigned count=0;
    char args[256];
    CHECK(!gauguin_desktop_boot(NULL)); CHECK(!gauguin_desktop_boot(""));
    for (unsigned a=0;a<13;a++) for(unsigned b=0;b<13;b++) for(unsigned c=0;c<13;c++) {
        snprintf(args,sizeof(args),"sweeteagl=%u gmt=%u sweet_dyld_probe=%u",a,b,c);
        CHECK(gauguin_desktop_boot(args)==(a==2 && b==2 && c==1));
    }
    const char *bad[]={"xsweeteagl=2 gmt=2 sweet_dyld_probe=1", "sweeteagl=2 xgmt=2 sweet_dyld_probe=1",
        "sweeteagl=2 gmt=2 xsweet_dyld_probe=1", "sweeteagl=2\ngmt=2 sweet_dyld_probe=1",
        "sweeteagl=2 gmt=2 sweet_dyld_probe=1suffix", "sweeteagl=2 gmt=2 sweet_dyld_probe=1=1"};
    for(size_t i=0;i<sizeof(bad)/sizeof(*bad);i++) CHECK(!gauguin_desktop_boot(bad[i]));
    const char *extra[]={"sweeteagl=2","sweeteagl=1","gmt=2","gmt=1","sweet_dyld_probe=1",
        "sweet_dyld_probe=0","metal_m2v=1","x=metal_m2v=1"};
    for(size_t i=0;i<sizeof(extra)/sizeof(*extra);i++) {
        snprintf(args,sizeof(args),"sweeteagl=2 gmt=2 sweet_dyld_probe=1 %s",extra[i]);
        CHECK(!gauguin_desktop_boot(args));
    }
    CHECK(gauguin_desktop_boot("\tdebug=1 gmt=2\t sweet_dyld_probe=1 sweeteagl=2 "));
    CHECK(gauguin_desktop_identity(501,501,"backboardd","20H392"));
    const unsigned ids[]={0,1,500,501,502,UINT32_MAX};
    for(size_t a=0;a<6;a++) for(size_t b=0;b<6;b++)
        CHECK(gauguin_desktop_identity(ids[a],ids[b],"backboardd","20H392")== (a==3 && b==3));
    CHECK(!gauguin_desktop_identity(501,501,"SpringBoard","20H392"));
    CHECK(!gauguin_desktop_identity(501,501,"backboardd","20H391"));
    CHECK(!gauguin_desktop_identity(501,501,NULL,"20H392"));
    CHECK(!gauguin_desktop_identity(501,501,"backboardd",NULL));
    const char *path="/System/Library/Frameworks/QuartzCore.framework/QuartzCore";
    unsigned char uuid[]={0x9e,0x40,0xb2,0xeb,0x26,0x0c,0x3a,0xf1,0xae,0x45,0xa1,0xa5,0x51,0xa8,0xc1,0xb9};
    CHECK(gauguin_desktop_upload_site(path,uuid,0x200390));
    for(unsigned bit=0;bit<128;bit++) {
        uuid[bit/8]^=1U<<(bit%8);CHECK(!gauguin_desktop_upload_site(path,uuid,0x200390));uuid[bit/8]^=1U<<(bit%8);
    }
    for(int d=-64;d<=64;d++) CHECK(gauguin_desktop_upload_site(path,uuid,0x200390+d)==(d==0));
    CHECK(!gauguin_desktop_upload_site(NULL,uuid,0x200390));
    CHECK(!gauguin_desktop_upload_site(path,NULL,0x200390));
    CHECK(!gauguin_desktop_upload_site("/tmp/QuartzCore",uuid,0x200390));
    CHECK(gauguin_desktop_upload_bounds(0x4000,1,0));
    CHECK(gauguin_desktop_upload_bounds(0x4000,64ULL<<20,0));
    CHECK(!gauguin_desktop_upload_bounds(0x4000,(64ULL<<20)+1,0));
    CHECK(!gauguin_desktop_upload_bounds(0,1,0));CHECK(!gauguin_desktop_upload_bounds(1,0,0));
    CHECK(!gauguin_desktop_upload_bounds(UINTPTR_MAX-15,16,0));
    for(unsigned bit=0;bit<64;bit++) CHECK(!gauguin_desktop_upload_bounds(0x4000,16384,1ULL<<bit));
    printf("%u desktop policy boundary checks passed; host only\n",count);return 0;
}
