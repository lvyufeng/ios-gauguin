# A619 offscreen clear and event sources

The169 temporary trial reached the clear stage but did not complete it. The
device shadow stayed20 instead of27, and the existing two-second WAIT guard
quarantined the transaction. No post-completion pixel readback was reached.
Consequently, this trial establishes neither clear execution nor acceleration.

Its cached control value was`0x0cf49802`, whereas the clear command waited for
sequence6 and then7. The sampled GPU counter was`0x0cf57bed`, only58347 ticks
later at19.2MHz. This suggests a timestamp was written where a sequence value
was expected. It does not identify the exact stalled packet or prove the final
cause of the failure.

The pinned Mesa24.3.4 source is commit
`769e51468b49b2a42f0a0eaf71cf9eed5ff4e5de`. Its Gallium`fd6_emit.h` requests
USER_32B for sequence events and ALWAYSON for timestamp queries, but its A6XX
branch sets bit30 for every addressed event, regardless of the requested
source. The same release's`adreno_pm4.xml` describes bit30 as selecting a
timestamp instead of the packet value. Its computerator A6xx sequence emitter
omits that bit; that transport produced actual shader/EOP results in168.
[Historical Gallium also emits sequence payloads without bit30](https://chromium.googlesource.com/chromiumos/third_party/mesa/+/9fc5ee58de44223e9f92064ad0f547302d1db55f/src/gallium/drivers/freedreno/a6xx/fd6_emit.h).
The historical mirror is supporting evidence, not a claim about current
upstream behavior or every A6xx firmware configuration.

The explicit port profile in
`tests/fixtures/gpu-clear/a619_event_source_profile.h` specializes native
`__event_write<A6XX>` before template instantiation. USER_32B emits packet
values without bit30; RB_DONE/ALWAYSON retains timestamp behavior. Unsupported
sources, destinations and event indices abort before even a packet header is
emitted. This is source-level transport selection, with no modification of the
primary Mesa tree or editing of captured packets after generation.

Native host controls select the original implementation with profile0 and
the port implementation with profile1. Both rebuild whole original emit and
barrier translation units using the evaluated original driver C++ flags.
The original control matches169 byte for byte. In both solid and two-color
captures, only the seven addressed event headers differ; restore194 words,
preamble205 words, target geometry and the separate semantic pixel oracle
remain identical. Each profile passes432 USER_32B cases and preserves the
native ALWAYSON query packet. Eighteen unsupported combinations abort with a
read-only ring, verifying rejection before the first packet write.

The accepted native report and independent review are in
`research/tmp/dsh-0170/`. Their source snapshot covers10642 files with SHA256
`598f1abe0af15e1ebf584c9dfb04acd14d41644d8a8597c120184da11767187d`.
The independent profile review SHA256 is
`275b73a58ebd32f05f53f7a339e7ca362a93c93979174a10954f501bf5d0b425`.
These are host/source checks, without GPU emulation or hardware qualification.

Patch170 carries those source-generated headers into the kernel. Its only
functional change is the seven event-source words. The clear engine's other
logic, header geometry and board code are unchanged apart from comments and
one diagnostic renamed FENCE with the USER32 source stated explicitly.
Pristine replay of164 patches produces5314 files with SHA256
`ef39ff64161d325d7e5a61f80e71af76704aaef139f2950f1b04dabb6641fbf3`.
All83 host test files, the actual signed/GGU/clear board model and two changed
ARM64 translation units pass. The clear model includes14875 cases, including
rejection of the observed169 control/shadow values and incorrect final
sequences. These checks still provide no physical clear result.

The kernel retains the full-page pixel checks, exact EOP7 comparison,
zero high neighbor, guards, permissions, ownership quarantine and current
timeouts. The failed169 image, packets, raw records and verifier results remain
preserved. A new temporary trial is required to determine whether this source
selection fixes the device stall. It will not establish general rendering,
Metal, UI performance or high-refresh support by itself.
