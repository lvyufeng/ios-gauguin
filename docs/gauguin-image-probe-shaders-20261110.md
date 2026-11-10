# Graphics image probe inputs

`graphics_images.metal` provides six project-owned Metal 2.4 functions for a
future physical image-write/readback diagnostic. It covers attribute vertices,
vertex texture reads, read-only device-buffer vertices, fragment image stores,
read/write image updates and subsequent integer-texture reads.

The Metal 2.4 compiler used here rejects writable resources in a non-void vertex
function. The fixture therefore keeps its rasterizing vertex resources
read-only. Writable void vertex functions and rasterization-disabled pipelines
need separate qualification; the encoder's low-level VS descriptor tests do not
prove that public Metal contract.

The fixture builds separately for iOS16 and macOS13. All nine vertex/fragment
pairings have compiled and linked for five selected target formats with the
candidate A619 core. This is compile/link evidence, not GPU execution or a
completed image probe. The candidate core's 211 imports also resolve against
the actual 20H392 cache in the retained complete backup.

Before installation, finish the bounded root executable and independent pixel
oracles. It must check GEM write permissions, shader resource usage, GPU fences,
CPU visibility, image-to-sampled-texture ordering, buffer/texture isolation and
cleanup while retaining the 128 MiB fatal process limits. Physical image results,
Metal desktop publication, frame rate and daily use remain unqualified. This
preparation does not alter the separately approved 0230 image or userdata plan.
