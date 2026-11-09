# Actual iOS16 Metal frontend metadata inventory

After the A619 offscreen core passes, the next boundary is the Metal device and
CoreAnimation frontend. This offline inventory reads actual **20H392** framework
metadata from the verified local HFS backup. It does not load a plug-in or execute
any framework method, and does not qualify runtime ABI behavior.

The source cache remains outside git. It contains Metal UUID
`0f0b7b9690bf3a07b7e185e2fb6160e6`, IOGPU UUID
`8eb7ed27e1af3c82825b130c091d7070` and libobjc UUID
`ed021f8f14a13308913023e1a30aaf4a`. The current root delta changes only the declared
probe/core/job/cache and HFS metadata; it does not replace these frameworks.

## Actual recorded boundaries

The thirteen selected classes contain 990 decoded base-list instance methods
and 210 ivars. This is not a complete inventory of inherited methods, metaclass
methods or protocol requirements; category merging was not audited. Source-level
comments about another iOS build are not substitutes for this image's layout.

| Class | Recorded instance size | Selected selector and exact encoding |
| --- | ---: | --- |
| `_MTLDevice` | 528 | `targetDeviceInfo`: `r^{MTLTargetDeviceArch=QI*}16@0:8` |
| `_MTLCommandQueue` | 345 | `initWithDevice:descriptor:`: `@32@0:8@16@24` |
| `_MTLCommandBuffer` | 488 | `initWithQueue:retainedReferences:synchronousDebugMode:`: `@32@0:8@16B24B28` |
| `_MTLCommandBuffer` | 488 | `commitWithDeadline:`: `v24@0:8Q16` |
| `_MTLCommandEncoder` | 88 | `initWithCommandBuffer:`: `@24@0:8@16` |
| `_MTLCommandEncoder` | 88 | `setThreadgroupPackingDisabled:`: `v20@0:8B16` |
| `_MTLRenderPipelineState` | 160 | `initWithDevice:pipelineStateDescriptor:`: `@32@0:8@16@24` |
| `_MTLComputePipelineState` | 64 | `initWithDevice:pipelineStateDescriptor:`: `@32@0:8@16@24` |
| `_MTLSamplerState` | 48 | `initWithDevice:samplerDescriptor:`: `@32@0:8@16@24` |
| `_MTLFunction` | 200 | `bitcodeData`: `@16@0:8` |

Instance sizes are metadata values, not allocator rounding or a layout that the
new subclass should redeclare. HakiOS uses runtime ivar lookup by name; preserve
that behavior. In this image `_MTLCommandQueue._commandBufferSemaphore` is at
208 and `_MTLCommandBuffer._needsCommandBufferSemaphoreSignal` at 384. The latter
is a one-byte `B`. These values help audit the named lookup and semaphore
lifetime; they are not a reason to hardcode offsets into the frontend.

`targetDeviceInfo` returns a pointer to the recorded const struct, rather than
the struct by value. This agrees with the relevant HakiOS declaration. The
presence of an initializer or compiler selector does not prove that it accepts
our objects, initializes every driver field, or returns a non-null compiler.
The source must still handle validation failures, abstract/nil-stub methods,
command-buffer semaphore repayment and encoder/owner lifetime correctly.

## Decoder evidence and preserved failure

DSH `inventory-stage-v1` failed strict UTF-8 decoding because the initial parser
treated a cached direct selector offset as relative to its individual field.
The original source/result remain intact. The open-source runtime describes
the global relative-method selector base in
[objc-runtime-new.h](https://github.com/apple-oss-distributions/objc4/blob/fb265098298302243cd7eeaa1f63f0ba7786dd9a/runtime/objc-runtime-new.h)
and defines it using the interned selector in
[objc-magicsel.m](https://github.com/apple-oss-distributions/objc4/blob/fb265098298302243cd7eeaa1f63f0ba7786dd9a/runtime/objc-magicsel.m).
Those are format references, not a claim that runtime revision 951.1 is the
runtime shipped in 20H392.

Fresh v2 obtains the unique exact selector reference from this actual cached
libobjc image, then interprets the offsets from that address. It preserves
strict bounds, slide-v2 decoding, entry-size checks, UTF-8 and unique names.
`inventory-stage-v2/result.json` exits 0 with unchanged inputs; no lossy string
repair, guessed 20F66 address, phone command, binary patch or injection occurs.
Private evidence is under the isolated 0223 worktree's
`research/tmp/dsh-metal-0224-ios16-frontend-abi/`.

## Next implementation

Build the complete pinned HakiOS CA frontend against the qualified A619 core,
then check actual MTLDevice discovery, device capabilities and protocol/return
ABI on 20H392. Inventory its own pipeline libraries and exact variant labels;
preserve paired vertex/fragment selection and function constants. Qualify BGRA/
sRGB and IOSurface views, offsets, read-only pages and owner lifetime before
claiming correct icons/widgets or presentation. The current kernel admits one
GPU owner, so replacing GLES requires coordinated admission/worker/device
publication rather than a second competing connection. The physical 0223 result
qualifies the core's eight offscreen cases, not these remaining frontend steps.
