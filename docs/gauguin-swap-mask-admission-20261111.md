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
rewritten. These source tests alone prove no desktop pixels, physical FPS, high refresh
rate or daily-use qualification. Full build and trial evidence are recorded
below.

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
replay and keeps pixel/FPS/daily-use qualification false. Those were preparation-only results; the authorized trial status is below. The project accounts for about 432.9 GB, with 128 MiB reserved
for the next trial and capture, within the 500 GB cap.

## Completed 0293 trial

The authorized marker and single temporary boot succeeded, followed by automatic
recovery after 746 seconds. The user reports normal desktop icons, widgets and
Settings, with touch response and animation still as slow as before.

The complete capture passed its file and log-prefix checks. The strict GPU trace
gate failed because submission 12 was interleaved with SpringBoard IOK XML.
That raw trace and failed report remain unchanged. An independent scoped audit
verified all eight initial offscreen pixel phases and the root-owner handoff.
Before planned shutdown the held queue submitted 43, consumed and retired 42,
canceled one and rejected zero; these are queue counters, not pixel or scanout
measurements. Native final totals were 56 submitted and 56 completed. Two buffer
failures occurred only after the planned service stop.

The submission API averaged 17.26 ms, with a 50.71 ms maximum and 8.281 microseconds
of total lock-queue wait across 56 calls. These times include validation and
waiting and do not isolate GPU execution. The next diagnostic will enable the
installed frontend's hardware pass timestamps and improve submission-log framing
while preserving strict parsing. Physical FPS, high refresh and daily usability
remain unqualified. The user feedback establishes a display fix, without a
performance improvement.
