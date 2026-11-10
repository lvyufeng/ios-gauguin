/* A failed diagnostic gate must never silently activate a different renderer. MIT. */
#include "../userland/metal/probe_boot.h"
#include <stdio.h>
int main(void)
{
    const struct { const char *args; enum gauguin_probe_route route; } cases[] = {
        {NULL,0},{"",0},{"sweeteagl=1 gmt=1",1},{"gmt=1\tsweeteagl=1",1},
        {"sweeteagl=2",2},{"debug=1 sweeteagl=2 other=3",2},
        {"sweeteagl=1",0},{"sweeteagl=2 gmt=1",0},{"sweeteagl=2 gmt=0",0},
        {"sweeteagl=1 gmt=0",0},{"sweeteagl=2 sweeteagl=2",0},
        {"sweeteagl=1 sweeteagl=2 gmt=1",0},{"sweeteagl=2 sweeteagl=1",0},
        {"sweeteagl=20",0},{"sweeteagl=2suffix",0},{"xsweeteagl=2",0},
        {"foo=sweeteagl=2",0},{"sweeteagl=1 gmt=10",0},
        {"sweeteagl=1 gmt=1 gmt=1",0},{"sweeteagl=2 gmt=",0},
    };
    unsigned checks=0;
    for (size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++,checks++)
        if (gauguin_probe_boot_route(cases[i].args)!=cases[i].route) return 1;
    struct stat valid={0};valid.st_mode=S_IFREG|0755;valid.st_nlink=1;valid.st_size=GAUGUIN_LEGACY_PROBE_BYTES;
    if (!gauguin_legacy_probe_metadata_ok(&valid)) return 2;
    checks++;
    for (unsigned i=0;i<8;i++,checks++) {
        struct stat bad=valid;
        switch(i) {
        case 0:bad.st_uid=501;break;case 1:bad.st_gid=501;break;
        case 2:bad.st_mode|=0020;break;case 3:bad.st_mode|=04000;break;
        case 4:bad.st_mode=S_IFLNK|0755;break;case 5:bad.st_nlink=2;break;
        case 6:bad.st_size--;break;case 7:bad.st_mode=0;break;
        }
        if (gauguin_legacy_probe_metadata_ok(&bad)) return 3;
    }
    printf("%u boot route and retained executable metadata checks passed\n",checks);
    return 0;
}
