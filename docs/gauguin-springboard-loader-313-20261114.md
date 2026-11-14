# 0313 candidate: make SpringBoard observation load and startup explicit

0312 proved that backboardd consumed synthetic HID queue data, while C4 still
had fifteen 4.9–5.3 second creation gaps. Its SpringBoard observer never emitted
an activation marker. The exact executable passed the dyld PATH-mask policy;
the library and launch plists matched their installed hashes after boot.
Loading and early constructor initialization remain unproven. All four files
and misc were independently restored; 0312 consent is consumed.

The project previously measured a missing DYLD_INSERT_LIBRARIES variable at
the actual backboardd exec boundary even though an unrelated custom job
variable arrived. That is historical evidence for a possible loading problem,
not proof that SpringBoard follows the same failing path. HakiOS also uses a
kernel insertion path for its
[SpringBoard library](https://github.com/oosexgang/hakios-xnu-kernel/blob/63fc2b4633bac3af8e57dadab9f5a8d4cb940438/userland/src/inject_sb.c#L2118).

## Candidate behavior

Patch 0235 appends the single existing-slot observer path at the actual
SpringBoard exec boundary when `sbp=1` and the existing C4 desktop mode is
selected. Default behavior is unchanged. It requires mobile UID/RUID 501,
the protected exact SpringBoard vnode, a protected root-owned nonwritable
library vnode, the matching exec thread/process and matching identity for an
exec shadow. It uses the existing checked argument-copy and alignment path.

An exact existing insertion is accepted without appending another entry.
Conflicting or duplicated DYLD insertion keys, insufficient argument space,
identity/ownership/ACL failures and copy failures preserve the original exec
arguments. It does not grant GPU access or broaden the existing AMFI policy.
The kernel reports incoming insertion counts, result, reason and added count;
it does not dump environment contents.

The library writes a fixed constructor-entry marker and an explicit refusal
reason for process, boot-argument, trace-flag, timebase or thread-creation
failure. The existing touch forwarding, CA request observation and main-loop
milestones are otherwise unchanged. These diagnostics do not fix the five-second
gap or establish 60fps by themselves.

## Offline checks

- Exact patch replay and reverse dry-run passed.
- Actual exec extraction/copy/insertion under ASAN/UBSAN: 104 cases passed,
  including 37 SpringBoard cases, shadow identity, conflicting environments,
  mobile-only admission, exact-fit/one-byte-short and partial-copy rollback.
  A fixture's 32-bit alignment assumption was corrected; production alignment
  code was unchanged. The original backboardd tests also passed.
- Native ARM64 `kern_exec.c` compilation passed against 2,133 pinned generated
  header/configuration inputs, without changing reference inputs.
- Actual ObjC wrappers/runtime tests: 117 checks passed with the added startup
  logs. Native iOS library build and strict signature verification passed.
  Library SHA256:
  `b0b49caf5ecf11619d6223455017f6668203ce61e0816dd70f599a6de9b800a4`.

Source commit: `2150dfe`. Private work is `research/tmp/sb-loader-313/`.
This candidate has not booted and has no write approval or prepared trial yet.
Next finish linking/image review and prepare fresh preimages, models and
restoration against root header
`7faaeed238ab8ad51846767eb8e6f98ecfd1d8a6243196f998bfd514892c522d`.

## Storage

A 60 MB offline batch was admitted before the sparse checkout and tests.
105 obsolete outputs were retired after verification: 189,791,771 logical bytes
of duplicate static capture blobs and two derived unstripped kernels. Each
duplicate has a retained identical counterpart; stripping each retired raw
kernel reproduced its retained kernel exactly. Original backups, all restored
captures, logs, ready-pinned inputs, stripped kernels, boot images, objects and
the baseline relink reproduction remain intact. Cleanup manifest SHA256:
`1e499fe4b55a0246453f4ad0d5eeb268f33ecd25f80e40e75a6286a029894fa7`.
The 620 MB link/image/preparation/trial batch was admitted at 499,363,512,320
accounted bytes, including a future 512 MiB trial reserve.
