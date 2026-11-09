/* Each owned EAGL context keeps its own CA effect uniforms. No Apple pointers
 * are dereferenced directly; ca_observer.inc validates their live association. */
#ifndef GAUGUIN_CA_EFFECTS_H
#define GAUGUIN_CA_EFFECTS_H
struct gauguin_ca_effects {
    uintptr_t context;
    float values[90][20];
    uint8_t given[90], said[90];
};
#endif
