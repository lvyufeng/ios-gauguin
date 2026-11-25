/* Admission must not silently switch rendering modes. MIT. */
#include "../graphics/hakios-metal-ca/overlay/userland/src/GauguinMetalProfile.h"
#include <stdio.h>

int main(void)
{
    const struct { const char *args; bool allowed; } cases[] = {
        {NULL, false}, {"", false}, {" \t ", false},
        {"sweeteagl=1 gmt=1", true},
        {"\tgmt=1\t sweeteagl=1 ", true},
        {"debug=1 sweeteagl=1 gmt=1 other=42", true},
        {"sweeteagl=2 gmt=1", false},
        {"sweeteagl=1 gmt=0", false},
        {"sweeteagl=1 gmt=10", false},
        {"sweeteagl=10 gmt=1", false},
        {"xsweeteagl=1 gmt=1", false},
        {"sweeteagl=1 xgmt=1", false},
        {"foo=sweeteagl=1 gmt=1", false},
        {"sweeteagl=1 foo=gmt=1", false},
        {"sweeteagl=1 gmt=1 sweeteagl=1", false},
        {"gmt=1 sweeteagl=1 gmt=1", false},
        {"sweeteagl=2 sweeteagl=1 gmt=1", false},
        {"sweeteagl=1 sweeteagl=2 gmt=1", false},
        {"gmt=0 gmt=1 sweeteagl=1", false},
        {"sweeteagl=1 gmt=1 gmt=0", false},
        {"sweeteagl=1\ngmt=1", false},
        {"sweeteagl=1 gmt=1suffix", false},
        {"sweeteagl=1 gmt=1=1", false},
        {"SWEETEAGL=1 gmt=1", false},
        {"sweeteagl=1 GMT=1", false},
        {"sweeteagl=1", false}, {"gmt=1", false},
    };
    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
        if (gauguin_metal_boot_profile(cases[i].args) != cases[i].allowed) {
            fprintf(stderr, "admission case %zu failed\n", i);
            return 1;
        }
    }
    puts("27 renderer admission cases passed");
    return 0;
}
