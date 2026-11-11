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
