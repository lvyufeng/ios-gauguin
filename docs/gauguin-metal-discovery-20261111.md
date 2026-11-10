# Metal discovery and first-open candidate, 0246

Source `ff6c07327b9e5d7a5132a5d30a606c89b7d30d6e` on
`codex/gauguin-metal-discovery-20261111` connects the 0245 ownership gate to
system plugin publication and a finite first-device wait. The candidate has
not been installed, linked into a complete kernel or run on the phone.

## Behavior added

Kernel patch 0213 defines one predicate for the new mode: exact integer values
`sweet_dyld_probe=1 sweeteagl=2 gmt=2`. Both the GPU bootstrap gate and the
accelerator publisher use that predicate. Other qualified modes retain their
existing branch.

For this new mode, `sweet_eagl_exec_inject` stops before appending an EAGL
library. It preserves the incoming environment byte for byte; it cannot remove
an explicit old library already supplied by launchd. Protected launchd proxy,
executable and compositor caller checks remain unchanged.

An atomic publisher claim allows only one accelerator instance to advertise
`MetalPluginName=GauguinMetalDesktop` and
`MetalPluginClassName=GauguinDesktopMetalDevice`. A partial property failure
removes both keys and releases the claim. Stop removes the keys before releasing
the claim. The generic accelerator user client retains its stub markers; the
real backend remains the separately qualified HakiosGPU transport.

The desktop-only seventh frontend patch replaces the single GPU open with the
production wait helper. It retries at 100 ms intervals for at most 35 seconds,
covering the root bootstrap's 30-second alarm. It returns immediately when the
kernel permits ownership. Backward/failed clocks, sleeping failure and a frozen
clock are finite failures; an independent 351-attempt limit prevents an endless
loop. A device acquired after the deadline, or immediately before a clock
failure, is closed before returning nil. Logs record the reason, attempts and
elapsed time. This addresses an early nil result becoming cached by Metal; the
actual framework behavior still requires a phone trial.

## Evidence

Pristine `1b191cb5` plus all 205 patches produces 5,332 files with source SHA256
`f002053dffd1b6f0a152a8bbb22e193cfb242b971c61d30e05402ca49e2a8b44`.
Exactly four files differ from 0245: `kern_exec.c`, the diagnostics header,
`GauguinGPU.cpp` and `SweetFramebuffer.cpp`.

DSH verifies actual source bodies with typed seams:

- 67 production exec/GET8/provenance scenarios, including all 64 mode-value
  combinations and unchanged incoming environments with and without the old
  explicit library.
- The 0245 ownership scenarios and existing GPU IOKit regressions, including
  readonly input, fault retention, queue ordering, BO limits, early VA release
  and the legacy six-fence pilot.
- 507 publication checks, including 1,600 concurrent service starts, rollback
  on either property failure, owner stop and subsequent publisher reuse.
- 2,888 first-open checks against an independent completion-time formula:
  immediate and delayed availability, exact deadline, timeout, late acquisition,
  device release on failure, bad/backward/frozen clocks and sleeping failure.
  Clocks and transport in these tests are modeled; no real registry or GPU runs.
- All six old frontend profiles generate byte-identical source files.

The initial stage, PID 91544, exits 1 after the exec and ownership checks pass:
the publication fixture omitted IOService's virtual destructor. The fixture is
corrected, and only unfinished checks resume. Final stage v2, PID 92418, exits
0 in 16.609258 seconds with 284 unchanged pins. The original failure is retained.

Three native ARM64 translation units compile using the successful 0242 recipe,
with 2,130 header/config checks and 5,334 recorded source/tool inputs:

| Unit | Object bytes | SHA256 |
| --- | ---: | --- |
| GauguinGPU | 355,784 | `68f46799116a06b9c96f5afc1676476575016714f4b53e36001b6ff51782418d` |
| SweetFramebuffer | 427,016 | `5f983a770d0ede5035259334ba2282205de2e15d35ce618cf983e40589599f44` |
| kern_exec | 356,688 | `95e9647f4190e2e20cf65e814bfe16b3109289d78973e958c5687f10342e9621` |

Existing compiler/header diagnostics remain in the raw logs. Native symbols
confirm one C definition of the shared mode predicate, consumed under the same
symbol name by both IOKit objects. Protected reference files remain unchanged.
This is not a complete kernel link or physical test.

The signed frontend is 428,480 bytes, SHA256
`09b39b36601dc432fe06dbcd6c6943fb954584260b8a9b05dabb87a4f517a96b`,
with principal class `GauguinDesktopMetalDevice` and unchanged core `8a826583...`.
DSH ABI stage v1, PID 93326, exits 0 in 10.069853 seconds with 292 unchanged
pins. All 555 core/frontend imports resolve against the verified 20H392 cache;
the sole added frontend import is `nanosleep`. Five optional M2V hooks remain
disabled. None of this establishes actual discovery or desktop pixels.

Codex independently rehashed final stage inputs/logs, the whole source,
prepared frontend/native input maps, all three native objects and their source
pins, and the signed bundle. Private evidence lives in the 0246 worktree at
`research/tmp/dsh-discovery-0246-integration`. `review246-v1.json` SHA256:
`33d52ccfaa4ebf3efd7fe846e4a8b840b9d5381c042ad8e2c73b6414829ae35d`.

## Next integration before any desktop boot

The actual captured launchd task still specifies the old EAGL library. A future
root overlay must remove only `DYLD_INSERT_LIBRARIES` from backboardd's task and
cache, while retaining `GAUGUIN_EAGL_MODE=admission`. The marker is harmless in
the new mode, where automatic injection is disabled, and lets old modes keep
their kernel insertion path. Removing both keys would break that compatibility.

The existing root job must also route by boot profile: retain the current
frontend diagnostic/legacy core path in old modes, and execute the new finite
bootstrap in the desktop mode. Use a small hash-checked SETEXEC dispatcher with
the proven 128 MiB hard spawn attributes, rather than racing two root jobs or
silently dropping the old diagnostic. Preserve the 531 task labels and
unrelated entries; prepare the corresponding memory-policy entries and cache
updates as one reviewable candidate.

The compositor's readonly task-input gate, real shared output, producer fence
and presentation still need integration and physical acceptance. The 0240
shared-output proposal remains pending. Do not repeat its question or boot a
new image and stale its delta; after the genuine reply, its exact paired 0239
image must run first. Only then qualify later kernel candidates and a complete
desktop package. Icons/widgets, transitions, stable input latency, sustained
usable 60 Hz, physical 90/120 Hz and daily phone functions remain unproven.

This milestone performs no device command, root write, reboot, CI build or push.
