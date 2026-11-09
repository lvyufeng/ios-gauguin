# HakiOS direct Metal transport: gauguin compatibility audit

This offline audit prepares the next frontend integration while the separate
0217 IOSurface trial runs. It does not load a Metal runtime or execute GPU work.

DSH audit-v2 compiled the actual gauguin `ggr_request_size` implementation with
the pinned HakiOS `gpu.hpp` definitions. Thirteen structure sizes/alignments and
61 field offsets match. Eleven request sizes, including queue close, were
checked against the real dispatcher-size function. The same layout checks
compile as an arm64 iOS 16 object. BO read-only and write-combined flags match.

| Boundary | Result | Required integration |
| --- | --- | --- |
| Wire structures and request sizes | Compatible in this audit | Preserve exact sizes/offsets and validate returned data. |
| IOService matching | Already compatible: the local provider class and registry name are both `HakiosGPU` | Keep that matching string; `GauguinGPU.cpp` is a filename, not the provider class name. |
| Query pipe and submit flags | HakiOS direct library uses 1; gauguin requires `0x10` in both places | Adapt both query and submission; do not relax the kernel's existing validation. |
| Shader/device target | Upstream constants select `0x06030500`, two SP cores and LPAC; observed gauguin chip is `0x06010900` / GPU 619 | Derive the complete A619 profile from the matching Mesa device data and verify every consumed encoder/compiler capability. |
| Surface backing | Shared request layout is 40 bytes; backing/offset semantics remain platform-specific | Retain SweetSurface's separate state/pixel descriptors, exact offsets, ownership and fence-before-read behavior. |
| Runtime behavior | Current kernel is a finite, admitted, single-owner prototype with synchronous completed submissions | Do not infer asynchronous scheduling, multiple ordinary clients, recovery or daily use from header compatibility. |
| Metal discovery and CA | Outside this audit | Implement the matching accelerator/plugin publication, iOS 20H392 frontend ABI, shader library, pipeline variants, textures and presentation. |

The first audit attempt failed because the C function `ggr_submit` hides its
struct tag in C++; new v2 fixture/script/output files use explicit struct tags.
The failed attempt is preserved. No production source was changed for the audit.

The v2 report also contained a mistaken metadata literal proposing a service
rename to GauguinGPU. Source review corrected this in a separate v3 interpretation
without rerunning or overwriting either result. The measured wire/offset/request
checks remain valid; no service rename is needed.

Private evidence: `research/tmp/dsh-metal-0218-abi/`, authoritative structural
stage `audit-stage-v2/result.json` (exit 0, input pins unchanged), interpreted by
`review-corrected-service-metadata-v3.json`. The iOS object SHA-256 is
`04b1bffc9bf1c0923a8200fef313875cb7b8ee688292cdadb71af78c65191a38`.
Headers were Git-blob-verified at HakiOS
`63fc2b4633bac3af8e57dadab9f5a8d4cb940438`.
