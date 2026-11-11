# Background-update admission repair

The actual 0291 temporary boot completed all 14 native GPU jobs, including the
eight root pixel stages and owner handoff. Its held display queue accepted zero
frames. All first-eight diagnostic records contain a registered owner, two
clients and `0x80000007`; all 15 classified rejections at the last pre-stop
snapshot are mask rejections. The old guard treats every bit outside four layer
bits as invalid, before attempting surface retention.

The [HakiOS implementation](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/xnu/files/iokit/Kernel/MiniIOMobileFramebuffer.cpp)
retains the complete request and processes four layers without rejecting this
high bit. An independent [iOS 16.7 instruction analysis](https://github.com/shenli99/ios-mh2lm/blob/d6448669b3b433a069c0bd9eae010c31360cb13d/docs/FRAMEBUFFER-USERLAND-ABI.md)
identifies bit31 as a background-color update and explains the legitimate
`0x80000007` clear-layers request. That analysis has not been bound to the
exact cache bytes on this phone.

Patch 0217 admits only `0x80000000 | 0x0f`, keeps unknown bits 4–30 rejected,
and uses only the low four bits to select surface holds. It preserves the
complete raw request and existing owner, lifetime, unwind and pending-frame
checks. It does not implement background filling, disable/persistent-layer
state or SwapWait semantics; those remain separate correctness requirements.

The sanitizer harness compiles and executes the actual old and new production
methods. The old guard fails functionally on the observed bit31 input. The
candidate passes 32 legitimate flag/layer combinations, 54 single unknown-bit
combinations, raw-record preservation, partial unwind and owner/retirement
checks. The native ARM64 framebuffer translation unit also compiles.

The parser now takes an explicit kernel contract: default `0x0f` for 0291,
`0x8000000f` for 0217. Tests preserve the actual 0291 diagnosis and reject
silently interpreting its old reason2 under the new policy. No old report is
rewritten. A new whole-kernel build, package and independently authorized
physical trial are still required. This source change proves no desktop
pixels, physical FPS, high refresh rate or daily-use qualification.

## Complete offline image and current device binding

The source was pushed as `246f17a54e6341a881b30647bac4e69a8d0d97e3`. A complete
local native build with fresh objects passed all retained provenance and symbol
checks in 209.814 seconds. The 20,021,248-byte temporary image SHA-256 is
`cc112dd62f3d700ce29cb90a1420fe9c51430469087ca6f5e4411f2dca8fee22`.
The command, managed-memory description, firmware assets, shim and DTB match
the baseline; the image declares the explicit `0x8000000f` update-bit contract.

Fresh read-only recovery checks match all 27 files and four directory tuples
against the actual post-0291 capture. The router and both target bindings pass.
The recovery marker preimage is backed up. The concrete trial plan SHA-256 is
`87c09972ff9edd39a3fcb52c4cafaa04b73b1ae06c579e798d9ec3ef7e4102e0`.
It proposes one 13-byte recovery marker and one temporary 0293 boot, with only
those marker bytes restored if marker writing or readback fails.

The booter and process-group wrapper reject absent real consent before device
IO or launch. The version-bound postprocessor also passes a complete capture
replay and keeps pixel/FPS/daily-use qualification false. No new 0293 write or
boot has occurred. The project accounts for about 432.9 GB, with 128 MiB reserved
for the next trial and capture, within the 500 GB cap.
