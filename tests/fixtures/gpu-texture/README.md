# Native A619 fixed texture references

Original Mesa 24.3.4 (commit `769e51468b49b2a42f0a0eaf71cf9eed5ff4e5de`)
NIR/IR3 compiler and sampler/view/cache/program/draw/sysmem emitters generated
these bytes. No packet or ISA postprocessing. Captures are CPU source evidence;
GPU texture execution and a general graphics API remain unqualified.

The three profiles use the same full-screen smooth vertex UV and a single
normalized 2D nearest sampler at explicit LOD 0, with clamp-to-edge:

1. Sample `(u,v)`.
2. Sample `(v,u)`.
3. Sample `(u+1,v)` to exercise the upper U clamp.

The immutable 4×4 RGBA8 input has a 64-byte row pitch and a 4 KiB source extent.
For texel `(s,t)`, R/G are the low/high bits of s and B/A the low/high bits of t,
each mapped to 0 or 255. Alpha blending is disabled. On the 16×16 target,
`u=(x+1/2)/16` and `v=(y+1/2)/16`; expected source texels are `(x/4,y/4)`,
`(y/4,x/4)`, and `(3,y/4)` using integer division. This gives 16, 16 and 4
expected distinct colors. Endpoint components permit exact pixel checks.
These expectations are fixed before any phone test; no tolerance is fitted to
hardware output. See [OpenGL 4.6, §8.14.2/table 8.20](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf).

Each profile has 31 source views: 27 native ring objects (including raw sampler
and descriptor data), three 128-byte shaders, and the immutable texture input.
Thirty views are nonempty. The 2,221 payload words include texture data;
2,752 words include serialized padding. The texture lies at `0xfc00a000` in
the existing 32 KiB read-only RING mapping. The target remains the separate
4 KiB DATA mapping. The command IB is 203 words; the draw stream is 79 words.
Native USER32 EOP sequences are 6/22/38 with emitter seeds 0/16/32.

Raw sampler and descriptor payloads are data, not executable PM4 streams.
Only byte-identical complete payloads are deduplicated. CPU C materialization
reproduces all three complete 32 KiB reference images exactly; a freestanding
ARM64 reference also compiles. A separate green control matches the accepted
0173 reference byte for byte. Typed CPU resource attachment is a capture seam;
this does not qualify full Gallium resource lifecycle, Metal, UI or throughput.
