# Root launch router and local desktop task candidate, 0247

Source c41838b5c4595779260b952fd3df3a4f1dda650e on
codex/gauguin-metal-launch-router-20261111 completes the source-side launch
routing planned after 0246. This is a signed executable and three local plist
candidates. Nothing has been installed or staged into an HFS volume.

## Routing and memory policy

The root job keeps its existing label, org.gauguin.gpu-probe. A small router
selects the retained frontend for the existing diagnostic/legacy modes and the
0245 bootstrap only for exact dyld1/sweeteagl2/gmt2. Unknown or conflicting
profiles fail. It verifies root identity, OS 20H392, target metadata and SHA256,
then uses POSIX_SPAWN_SETEXEC to replace its process image. It loads no GPU
library itself. Same-process replacement is modeled in host tests and remains
unverified on the phone.

The router requires its existing active/inactive 128 MiB fatal limits and
preserves that policy with explicit spawn attributes. Captured D22 and D221
policies already contain the label-specific soft-limit override and hard
limits. No additional policy row or policy-file modification is needed; the
earlier suggestion to add executable-name policy entries is superseded.

The retained target is specifically the pending 0240 probe, SHA256
26d09095687544b44af83232fd850c8d8c0d2149a7c17b87b7a0500b697bca3b,
not the currently installed 0237 binary. The bootstrap is the 0245 executable,
SHA256 2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c.
Installation of 0240 and its paired physical trial must precede any future
router installation.

## Scoped local launch transformation

Only the root job's argument array and backboardd's explicit
DYLD_INSERT_LIBRARIES are changed, in both job files and the launch cache.
GAUGUIN_EAGL_MODE=admission stays: old modes need that marker for the kernel's
automatic insertion; 0246 suppresses insertion in the new desktop mode.

The actual cached backboardd environment contains two extra logging settings
absent from the standalone job: CFLOG_FORCE_STDERR and OS_ACTIVITY_DT_MODE.
The transformer preserves each representation independently. It retains all
531 labels, 529 unrelated jobs, all other cache sections, and both policy files.
Its three binary-plist outputs are:

| Candidate | Bytes | SHA256 |
| --- | ---: | --- |
| root job | 487 | b9909fd6d3c816b8321ec1fb818f2ae76f06299fd5c7c50f04d936e4b6fb7a58 |
| backboardd job | 1,133 | efdef6cfedd44e28e7379cc35feaf744d7450794bd636fd829ebd6be480c84dd |
| launch cache | 795,842 | 140a1df1cb3743c955a8319e0ea7a83c604c485842a21dab4a981ed35da83736 |

These outputs are not a root-volume delta. A future volume proposal must use
a fresh capture after 0240, include the complete reviewed desktop package,
and obtain the required individual write consent.

## Software evidence and limits

DSH stage v1, PID 96572, exits 1 after all 29 router cases and the native build
pass: the initial transformer incorrectly requires the full job and cached
environments to be equal. The correction preserves cache-only entries.
Only the transformer and its tests change after that terminal failure; both
original stage and its logs remain.

DSH stage v2, PID 97190, exits 0 with 26 unchanged pins. It reuses the passed
router build and finishes the local launch checks, including 14 corrupted-input
controls, 531 labels, 529 unchanged jobs and binary-plist round trips. Router
tests exercise actual file/hash/attribute logic under ASAN/UBSAN; credentials,
system calls and successful SETEXEC are typed host seams.

The signed ARM64 iOS 16 router is 69,536 bytes, SHA256
a32f77cbbac5583fb681c037ab77cb2f16e304dc85006e5762bf3da1ab96c101.
Compilation and signature verification logs are empty. ABI stage v1, PID 97710,
exits 0 with 32 unchanged pins: all 32 imports resolve against the verified
20H392 backup, using 28 export images. No unresolved strong or weak import
remains. This establishes neither runtime routing nor a working desktop.

Codex rehashed final stage inputs/logs, native inputs/binary and all local plist
inputs/products. Evidence is private under the 0247 worktree at
research/tmp/dsh-launch-0247-router. Review SHA256:
3ed4442c6866608d22906335ebad56cc8148c7505ca6de6b92c84f870646cade.

No device command, userdata write, reboot, CI build or push occurred.
The pending 0240 plan and paired 0239 image remain unchanged.
