# Router target binding after the 0282 startup failure

Trial 0282 never executes the updated GPU bootstrap. The installed router still
requires the old 115,968-byte executable with SHA256 `2e41724459e53107b7e34fc932600507f6c1e5644917f7cc6c7029101bb1450c`.
The installed bootstrap is 116,048 bytes with SHA256 `7b922e66fbeb862504ea8ac01fd73681382e4718b7b1325e405fbecc25f6b6e0`.
Its target verification fails before SETEXEC. Increasing the readiness timeout
again would not address that failure.

The build recipe now binds the router to that installed bootstrap and requires
its 180-second readiness budget and separate 30-second work alarm. Runtime C,
profile admission, credentials, memory policy and SETEXEC remain unchanged.
The two retained target paths and arguments are unchanged.

`tools/metal_router_targets.py` compares the router and both embedded targets
against actual captured bytes, sizes, hashes and HFS ownership/modes. A future
volume proposal must run this check on its final image. It does not claim to
replace the router's runtime inode, link-count or concurrent-change checks.

DSH 39675 builds and signs the replacement and completes the focused checks in
5.250 seconds with 89 unchanged stage pins. The original 29 production router
cases pass under ASAN/UBSAN. A new test uses the real installed 0282 binaries
with production router code: the old target tuple refuses before memory-policy
or spawn calls, while the new tuple passes to modeled SETEXEC with the same
PID. Four corrupted package captures are rejected. Credentials and SETEXEC
are typed host seams; no real process replacement or phone command occurs.

The signed iOS 16 router is 69,536 bytes, SHA256
`7834e091f35dfca68ad8f6f0673e57d88ddfa3664b01b137d0ca3b01890e5cd2`,
build `75fd7501e15a2ec6083233d4`. Its import listing and load commands match
the previous router exactly, retaining the prior static 20H392 resolution
evidence. The binary was built from the pinned working source before the
subsequent source commit.

This is a source/build correction. It is not installed or hardware-qualified.
The 0250 kernel, frontend, bootstrap, core and shaders do not need replacement.
Full GPU desktop rendering, frame rate and daily usability remain unproven.
Before allocating the upcoming backup and final candidate, the entire 36 GiB
batch was admitted at 391.4 GB under the project's 500 GB storage cap.
