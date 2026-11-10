# Graphics storage-image candidate

The actual 20H392 `std_vert1_lph` / `inplace_copy_lph` pair was refused because
the fragment function writes texture 3 through an image descriptor. Compute
images already had a descriptor path; graphics accepted only SSBOs in its shared
3D IBO table. This candidate implements that missing graphics path.

Preparation defaults to `a619-baseline`, whose 228 source files remain identical
to the qualified baseline. The candidate requires the explicit
`--profile a619-graphics-images` option. Its code and native library are software
qualifications only, and have not replaced the installed core.

The patch changes the full resource path:

- Reserve the vertex stage's entire IBO extent before compiling the fragment
  stage. Reserve it even when the fragment function originally has zero SSBOs.
- Build storage descriptors for 2D, 2D-array and 3D images, checking shape,
  element class and shader read/write usage. The shared table has 48 slots;
  out-of-range extents and conflicting descriptors refuse before emission.
- Include images in both stage NIBO register fields, and retain and submit their
  backing buffers with the correct write permission.
- Isolate image draws into sysmem passes with complete cache synchronization.
  GMEM replay, disabled synchronization, and aliases with render/depth/stencil
  attachments remain explicit refusals. Image atomics remain unsupported.

Software evidence includes an iOS16 A619 native build, 44 ASAN/UBSAN encoder and
refusal assertions, and linkage of the formerly refused actual CA pair at five
formats. A separate real AIR compiler test verifies that an image-only fragment
function preserves reserved bases 1, 4 and 31. These checks exercise descriptors
and compilation; the fake allocator does not execute shaders or rasterize.
The full actual CA catalog was rerun: all 469 distinct stage pairs link at all
five selected formats, covering the same 1,079 catalog entries. Full pipeline
state, other MRT formats and GPU pixels remain separate qualifications.

Before installing this core, verify its native imports against the actual iOS
cache and run real GPU image-write/readback cases, including both stages,
cross-draw sampling, CPU visibility and resource cleanup. Integrating the exact
CA frontend, global Metal publication, desktop rendering, latency and high
refresh still require physical acceptance. The already prepared 0230 userdata
delta keeps the earlier core and is a separate, unchanged consent request.
