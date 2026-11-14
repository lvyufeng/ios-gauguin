# 0314 candidate: admit the protected SpringBoard spawn child

0313 logged `SWEET SB INJECT` outcome 6, reason 9, before inspecting
credentials. No incoming insertion key was present. The observer consequently
had no constructor or activation record. Later dyld policy checks saw mobile
UID/RUID 501. The earlier UID value 4294967295 was an uninitialized diagnostic
sentinel, not the process identity. All four temporary files and misc were
independently restored after the trial.

The existing guard admitted the current process and a matching exec shadow,
but omitted the direct launchd spawn-child path. The actual `posix_spawn`
implementation sets the VFS context credential before adopting requested child
credentials, so that context can also retain the parent's old credential.
0313 did not log its caller or image flags; the source establishes a missing
case, not a complete runtime attribution.

Patch 0236 admits a distinct non-shadow child only when the caller is init,
the image is SPAWN without EXEC, the original parent is that caller, and the
image thread belongs to the target process. It obtains a reference to the
target's current credential, requires effective and real UID 501, and uses a
stack VFS context with that same held credential for vnode authorization.
Every exit after acquisition releases it. The original context stays intact.
The existing exact protected SpringBoard/library checks and environment-copy
bounds remain in force. The shadow path now also rejects mixed SPAWN/EXEC.
Caller PID, flags, init/shadow state and original parent are logged.

This changes the observation loader only. It reuses 0313's signed library,
C4 binary, GPU policy, automatic wake and 13-stroke input script. The library's
313 constructor marker denotes its version, not the new kernel's trial ID.
No 60fps claim follows from these changes.

## Validation

- 118 actual exec extraction/insertion cases passed under ASAN/UBSAN, including
  51 SpringBoard cases. New cases cover launchd spawn, stale parent credentials,
  fresh child identity, invalid parent/thread/shadow combinations and balanced
  credential references. Existing backboardd behavior also passed.
- Native ARM64 `kern_exec.c` compiled against 2,133 pinned generated header and
  configuration inputs. Reference files were unchanged.
- Patch replay reproduced the candidate exactly; reverse dry-run passed.
- The library is unchanged from the 0313 native/signature and 117-check ObjC
  validation; those results are reused with their exact input hashes.

Source commit is `2783cc4`; private artifacts are in `research/tmp/sb-spawn-314/`.
Local incremental linking, packaging and independent image review passed.
The image is 20,054,016 bytes, SHA256
`1e78df251263cdb2c524631d3c27f9db93391fd0134a7ef9e01e4e7d4dd19428`, identity
`xnu-local314-89f1cb48b219472180eaa18439a10abb`. There was no new CI run.

Fresh four-file preimages were read from the restored phone. Eight-range
installation and restoration models passed partial-write rollback, rollback
failure reporting and final HFSX verification; all writes stayed in RAM.
The missing-approval gate stopped before device commands or an execution claim.
Wake-log validation passed two positive and twelve negative cases.
The [0314 one-shot plan](gauguin-springboard-spawn-314-trial-20261114.md) is ready
with 65 fixed inputs and a fresh 512 MiB storage admission at 499,417,346,048
accounted bytes. No 0314 phone write or boot is authorized by consumed 0313
permission.
