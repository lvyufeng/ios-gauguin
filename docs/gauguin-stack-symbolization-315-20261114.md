# Actual 20H392 symbols for the 0315 stack probe

The 0315 one-shot transaction is fixed at `8ee8dab`; its separate permission
request has been sent and is awaiting the user's actual answer. No 0315 phone
write or boot has occurred. This offline analysis changes none of its 70 inputs.

The preserved 20H392 cache provides QuartzCore image base `0x188284000`, UUID
`9e40b2eb260c3af1ae45a1a551a8c1b9`. Its local symbols and `LC_FUNCTION_STARTS`
agree on the six ranges below. End offsets are exclusive. The private report
also records the SHA256 of each function's actual instruction bytes.

| Function | Image-relative range | Existing static evidence |
| --- | --- | --- |
| `CA::Render::Context::request_synchronize` | `[0xa41dc, 0xa44e8)` | Schedules a default five-second deadline/callback; this is not itself a blocking wait. |
| `CA::Render::Context::wait_for_synchronize` | `[0xb36ac, 0xb38ac)` | Receives a synchronization reply with a one-second Mach receive timeout. |
| `CA::Context::synchronize` | `[0x1b82d0, 0x1b8a20)` | Calls the request and receive paths. |
| `-[CAWindowServerDisplay freeze]` | `[0x2637dc, 0x26395c)` | Contains a five-second semaphore wait. |
| `CA::OGL::MetalContext::Pipeline::wait_for_completion` | `[0x201634, 0x20166c)` | Waits for a dispatch block with an infinite deadline. |
| `CA::Transaction::ensure_implicit` | `[0x430e4, 0x43264)` | Registers the transaction run-loop observer; registration is not a wait. |

Use the observer's `QuartzCore+offset` labels with this specific image. Preserve
the raw PC, LR and saved return addresses. PC identifies the current instruction;
LR and saved LR identify return locations. For an AArch64 return address, inspect
the preceding four-byte instruction as a separate callsite candidate and verify
the instruction. Do not silently replace the raw return address with that
candidate, map unknown or ambiguous image labels, or guess pointer-authentication
masks. Other frames need their own actual image's symbols and function boundaries.

These ranges are a shortlist, not a complete map of possible stalls. Repeated
samples aligned with the same long main-loop turn can identify a waiting path.
One sample, a nearby symbol or a literal timeout alone does not establish the
root cause. No runtime stacks or new frame-rate evidence exist at this checkpoint.

Private evidence is in `research/tmp/sb-stack-315/`:

- `prepare_stack_symbol_map.py`, SHA256
  `b824e196209a1d65de88b92dadb276a6f244a79110c4d5000e716ca297c1006d`.
- `stack-symbol-ranges.json`, SHA256
  `0ad9645851ea02f361534034fb4445ba494a83aeb3aba1ea94de9171e12b3393`.

The reader uses the already inspected offline cache parser, verifies the
preserved backup header and system version, and reads the backup without writing
to it. The helper completed with six matching symbols and bounded text ranges.
It issues no phone command and writes no large image or cache export.
