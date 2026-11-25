# Native A619 varying references

These are unchanged Mesa24.3.4 NIR/IR3/program/draw/sysmem/flush outputs for
smooth RG, smooth GR and first-provoking-vertex flat RG. The authored input is
`../gpu-draw/native_nir_varyings173.h`, captured under the same filename.
A separate legacy green capture reproduces the accepted171/172 reference.

The three window vertices are `(0,0)`, `(32,0)` and `(0,32)`, with equal clip W.
A pixel center `(x+1/2,y+1/2)` in the16x16 target interpolates RG to
`((2*x+1)/32,(2*y+1)/32)`. GR exchanges the two channels. Flat RG uses the first
vertex's zero pair. Blue is1/4 and alpha1. All256 centers are strictly inside.

The RGBA8_UNORM declaration is fixed before device testing: clamp each channel,
multiply255, and accept only floor or ceil per component. Alpha1 is exactly255;
blue1/4 allows63or64. The provenance includes all source-derived per-pixel
bounds and preferred nearest values. Between jobs the exact previous observed
pixels must be retained, including each prior legal rounding choice.
This follows [OpenGL4.6](https://registry.khronos.org/OpenGL/specs/gl/glspec46.core.pdf)
sections14.6.1 and2.3.5.2. It is a semantic declaration, not measured GPU precision.

Every profile contains27slots/26nonempty views,1158native payload words and
1632words with deterministic128-byte padding in the existing32KiB RO ring.
All shaders are128bytes, have no private memory or texture/UBO/SSBO resource
reads, and use actual native varying linkage. Smooth shaders contain `bary.f`;
the flat shader contains `flat.b`. Event values6/22/38 come from original native
context seqno inputs0/16/32. Packets and shader ISA are never patched afterward.

C materialization reproduces all three complete native ring images and compiles
as freestanding ARM64. This source evidence does not qualify physical varying
interpolation, a general submission API, textures, UI acceleration or Metal.
