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

Physical execution must check GEM write permissions, shader resource usage, GPU fences,
CPU visibility, image-to-sampled-texture ordering, buffer/texture isolation and
cleanup while retaining the 128 MiB fatal process limits. Physical image results,
Metal desktop publication, frame rate and daily use remain unqualified. This
preparation does not alter the separately approved 0230 image or userdata plan.

The bounded `image_probe.cpp` executable now builds and signs for iOS16 against
the explicit graphics-image core. Its nine planned submissions each contain
store, read/write and sample draws without an intervening CPU read. It varies
attribute, vertex-texture and vertex-buffer sources, tests scissored preservation,
checks actual submission WRITE flags and fences, and compares image, sampled and
coverage pixels. Raw image/sample rows allow a separate reader to check results.
The probe retains root-only mode1/gmt1 admission,90-second delay,128MiB hard limits
and a210-second alarm. Physical execution remains pending.
No core, probe or userdata was installed by this independent build.

`metal_image_log.py` independently recomputes all 73,728 raw image and sampled
pixels across nine jobs. It checks scissor preservation, all three vertex input
modes, exact artifact identities, row order and hashes, phase parameters, nine
distinct completed fences, memory limits and connection release. Correcting a
hash after corrupting a pixel does not bypass the expected-pixel comparison.
Its four synthetic protocol tests cover four input seeds and malformed/error
controls. A log alone does not prove native GPU execution; kernel service,
ownership, faults and submission correlation are still required separately.

The native probe reports 110,592 internal comparisons, but emits raw rows for
only the image and sampled target. Its 36,864 coverage checks therefore remain
internal assertions and are explicitly excluded from the independent raw count.

`run-metal-image-oracle.py` runs the same project-owned shaders through public
macOS Metal. Store, read/write update and sampling use one command buffer per
job, with no intervening CPU read. It captures image, sampled and coverage rows.
Four seeds passed independent Python checks of all 442,368 actual Mac GPU pixels;
32 corrupted versions of these actual logs were rejected. This validates the
MSL patterns and pixel expectations on the Mac, without qualifying A619 code
generation, resource descriptors or native phone execution.

The exact candidate core and native executable also passed a fresh 20H392
dyld-cache export audit: 211 core imports plus 85 executable imports resolved,
including executable-to-core bindings. No missing imports remained. The library
and probe remain hardware-unqualified and have not been installed. This work
does not modify the separately approved 0235 FP16/CoreAnimation phone trial.
