# Native sequence references

These are original Mesa 24.3.4 A619 command and shader outputs for three fixed
NIR inputs: a full green triangle, a full red triangle and an inset green
triangle over a blue clear. The authored NIR lives in
`../gpu-draw/native_nir_programs.h` and `../gpu-draw/native_nir_controls.h`.
The inset's exact window vertices are `(4.25,4.25)`, `(20.25,4.25)` and
`(4.25,20.25)`. Integer point sampling gives 116 green and 140 blue pixels;
no edge crosses a pixel center. These counts are expected values.

Each capture initializes the original native CPU context's `seqno` to 0, 16
or 32. Unmodified emitters produce final completion values 6, 22 and 38.
Commands and shader instructions are never patched after capture. Complete
payload arrays are shared only when their bytes are identical. Each profile
has the same 27 slots, 26 nonempty views, 1,158 payload words and 1,632 words
including deterministic 128-byte padding, in the existing 32 KiB RO ring.
The first profile is byte-exact to the fixed green reference in `gpu-draw`.

`native_provenance.json` records source and capture identities. Host C
materialization reproduces all three captured ring images byte for byte, and
the same reference compiles as freestanding ARM64. These files establish
source provenance; they do not establish physical execution of a sequence,
a submission API, UI acceleration or Metal support.
