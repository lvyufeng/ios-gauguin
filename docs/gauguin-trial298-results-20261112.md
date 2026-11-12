# Trial 0298: CPU present statistics and the retained GPU baseline

2026-11-12 CST. The individually approved single temporary boot and read-only
post capture completed. This establishes finite diagnostic evidence. The phone
is back in recovery; full phone acceptance remains incomplete.

## Authorization, source and execution

The actual answer to questionItemId
`["request_user_input_async","call_df74f585b2ae42efaa1fa83f8850e829",0]` was
`允许本轮标记写入、临时启动及标记失败回滚`. It authorized only the existing
0298 plan: a 13-byte recovery marker at the start of misc, rollback of those
same bytes only on marker failure, one temporary boot without retry, a
600-second GPU service and up to 780 seconds of observation. Normal iOS runtime
log writes were allowed. No explicit userdata difference write was performed.

- Plan SHA: `6872d2d396e10bdd7209f34c0c7e9675688b440f06c0a10df3a8f18fafdb5184`
- Image: 20,021,248 bytes, SHA `64596164315fc496ff30037bb1fdf982d1322069eee788e28554f38d6f43cc7e`
- Source commit: `faed768516c106514d11681295de71639e06934a`
- Full source: 5,333 files, SHA `6ab302a69608be6dbe9a651e500891c715f990b0db553254322bdbbf0e0f0b3e`
- Exact observed kernel identity: `xnu-d32fdbfabacc428f9f74401f3b674cbd`, built Nov 12 00:55:21 CST
- DSH trial dispatcher 8284, isolated boot-helper process group 8784
- DSH read-only post dispatcher 17131

Fresh preflight verified 27 files and 4 directories before any marker write.
The original 4,096-byte misc preimage hash was
`ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7`.
The 13-byte write's full readback matched
`8698abf44b69b8040dd109feefc23706f070a26932c47f2b44a835efb2b9c801`;
no rollback was needed. Fastboot reported a successful temporary boot.
The observer detected recovery after 745 seconds and validated the exact
image/kernel banner. Observation elapsed 745.866639 seconds; the outer stage,
including preflight, elapsed 815.634817 seconds. It exited 0 with all 88 inputs
unchanged and no live child in the boot-helper process group. Boot attempts
were 1, retries 0. No CI run was performed.

The read-only post stage exited 0 in 16.549918 seconds with all 105 inputs
unchanged. It revalidated 24 static files, metadata for 4 directories, and the
complete old prefixes of 3 logs. The new tails were 3,007, 135 and 53,071 bytes.
All 12 preserved 0297 evidence pins match. The post-boot root header is
`fb998b9aafcf92f7a6f2d48358b6c245a634dcb775822d352cfe4677665d7858`;
the header and logs legitimately changed during the authorized runtime. New
trials need a new current baseline and fresh preflight rather than reusing the
old 0298 pre-boot header or log prefixes.

## CPU present evidence

The strict 0221 parser accepted five ordered cumulative snapshots. The latest
recorded prefix contains 16 attempts, 15 copied attempts, one zero-byte
attempt, zero invalid timings and zero refused guards. It records 155,520,000
copied bytes across 15 layers.

All 15 guard-acquisition samples are in `[0, 0.5 ms)`. All 15 copied-byte wall
intervals are in `[2, 4 ms)`. The reported p95 and p99 fall in those same bins;
these are bucket bounds, not exact percentiles. The earlier cumulative
snapshots must not be added together. Later activity after the last printed
prefix may be unreported. These counters measure CPU intervals, with tracing
enabled. They do not establish scanout, actual FPS, input latency, or disabled
tracing overhead.

## Finite GPU and userland evidence

The exact current native log passed the committed finite-service validator:
598 renewals, 27 submitted/completed jobs, 16 individually recorded successful
submissions and 11 further successes established only by sampled counters.
Exact per-submit ring increments are proven through submission 16. The
600-second service stopped deliberately; four later compositor buffer requests
failed after withdrawal. Those post-stop failures remain recorded separately
from service-window failures.

The current-only bootstrap tail contains eight ordered offscreen phases:
two clears, compute, triangle, two textures, additive blending and
premultiplied half float. Their compared counts and hashes match independently
computed CPU expectations; one queue's fences 1 through 8 match the initial
native completions. Native arming and clean close precede compositor ownership
with root fence 8. Printed build `9b9f99e2627808207562eee0` is present in the
captured installed bootstrap bytes, and its printed core hash matches the
captured installed library SHA
`8a8265838bfd3e4a9d627ef40f06e391a74fa3543d0f58b8dca3eec2f04ee1e1`.
These artifacts also match the immutable pre-boot pins.

The original legacy parser correctly rejected the new memory label. Its
byte-exact source and the rejected result remain preserved. The new distinct
`tools/metal_bootstrap_log.py:qualify_bootstrap_log` validates the unmodified
current logs and the complete startup/arming/clean-close/native-handoff
order. Validation passed 58 legacy checks using an independent C++ CPU
oracle, 160 synthetic bootstrap checks, 11 current-log checks and seven
finite-service unit tests. Codex review corrected three negative cases that
had supplied native text as stdout, bounded the serialized compositor/proxy
PIDs, and kept both earlier source/results and the demonstrated old acceptance
gap. No input log was relabeled. The 44.460868178-second startup value is
the userspace bootstrap recorded interval, not total boot wall time. The
strict result covers 28,928 compared output words and eight completed root
fences; broad Metal/desktop/FPS/daily-use qualification flags remain false.

The backboardd tail records ABI admission, a successful in-process first open,
pipeline linking and draw work. Its 17 frontend FPS summaries all report zero
presented. That frontend counter is not a physical panel measurement. No
`metal_defer` state is recorded in this tail. Neither activation nor
deactivation is inferred from that absence. Physical screen/input feedback was
not available when this report was finalized. Full Metal API compatibility,
system device discovery, correct desktop, total safe RAM, reliable storage,
peripherals, 90/120 Hz and daily use remain unqualified.

## Audit corrections and private evidence

Codex's first additional host audit rejected two pre-existing content-pinned
symlinks. The failed script and result remain preserved. The corrected audit
follows the original dispatcher's resolved-content hash contract and records
the current link targets; it does not claim the original profile pinned target
spellings. Captured root files remain required to be regular files. All 88
trial, 105 post and 51 review pins were checked. No device trial or capture was
repeated during that audit correction.

Private W is
`research/tmp/gauguin-present-trace-worktree-20261112/research/tmp/dsh-trial298-prep/`.
Its original `trial-stage-v1/`, `execution298-v1/`, `trial298-v1/`,
`post-stage-v1/`, `post298-capture-v1/`, `review298.json` and
`codex-trial298-audit.json` are terminal evidence; never relaunch them. Additional
host reports and source snapshots are under `research/tmp/resume-ios-20261112/`.
Raw device logs, identifiers and Apple artifacts stay outside git.

## Future command budget and next work

The separate native 0222 kernel remains unbooted. Its two proposed future
profiling commands can retain `sweetfb_hz=60`: remove exactly
` sweetpasmem=0` and append ` sweetgfprof=0` or ` sweetgfprof=1`. Each is 605
bytes within the 607-byte budget, differing in one final policy byte. All six
source consumers of `sweetpasmem` initialize the destination to zero and
discard the parser's presence result. The exact parser leaves that destination
untouched when absent. Source review therefore establishes the same feature
gating at those consumers, without claiming real-time equivalence. The private
`future-command-budget-review.json` pins all consumers and parser sources.
Omitting `sweetfb_hz=60` remains invalid for the intended comparison because
its default changes copy cadence. No future image or boot is authorized by
the consumed 0298 consent.

Preserve this installed baseline and finish the source ownership/admission
foundation before enabling a deferred/async Metal path. Prior host reports
establish lifetime defects in the opt-in path; they do not show those defects
occurred in this boot. The next source work must cover queued jobs and callback
leases, recorder and native queue/GPU lifetime, callback-safe teardown and
frontend commit/wait admission ordering. The original mock's completion-before-
callback ordering differs from actual core finish ordering; use the real core
with its FakeGpu endpoint for regression evidence. Any large new source/build
batch needs whole-batch admission under the 500,000,000,000-byte cap first.

Final pre-commit accounting was 450835124224 B of 500,000,000,000 B. The post capture had separately admitted its full
256 MiB batch. No large image, source clone or native build batch was
created in this trial/host-validator increment.

The original uncommitted `tools/mkadt.py` edit remains byte-identical. The full
phone objective remains active and incomplete.
