# Bind complete Gauguin DRM timings to the captured DTB

The 0272 verifier compared front porches and horizontal/vertical totals. A legal
change to `hsync_end` or `vsync_end` could change sync width and back porch while
passing those comparisons. The new contract checks every timing field of all
advertised modes and the active mode against the same captured DTB model.

```sh
python3 tools/gauguin-display-profile.py CAPTURE.dtb --drm-mode-log MODES.log
```

This CLI is on branch `codex/gauguin-mode-contract-20261111`, in the retained
`research/tmp/gauguin-mode295-worktree-20261111` checkout. The generic DRM reader
continues accepting legal catalogs; the optional contract verifies their identity.
Without the new flag, existing CLI output is unchanged.

The contract uses nominal rate and clock as keys, independent of catalog order.
It includes sync widths, back porches, skew, scan multiplier and full public
flags. Horizontal skew comes from the actual DTB. The supported vendor video
catalog uses public `VID_MODE_PANEL`; private DFPS transition flags are separate.
Mode `type`, including `PREFERRED`, is retained as selection metadata rather than
compared as a physical timing field. This follows the pinned
[vendor converter](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/techpack/display/msm/dsi/dsi_drm.c#L100)
and [public mode flags](https://github.com/MiCode/Xiaomi_Kernel_OpenSource/blob/e601e14af391539e0fd67fe0506bcbe55bfcd997/include/uapi/drm/drm_mode.h#L122).

DSH passed six test groups: twelve cached handset modes, 24 legal sync-end
mutations accepted by the old four-field policy, 30 timing-field/active mutations,
incomplete and ambiguous catalogs, reordered catalogs and selection metadata.
The actual vendor conversion function also produced matching complete timing
and flag tuples for all twelve normal advertised video cases under ASan/UBSan.
That oracle checks conversion mapping; it does not independently validate the
existing DFPS algorithm, clock generation or physical display.

This is offline evidence. No handset command, modeset or new kernel boot ran.
Physical 90/120 Hz, scanout latch and application cadence remain unqualified.
The existing 0294 diagnostic image and all 641 sealed inputs remain unchanged;
its one-boot trial still needs the previously requested individual authorization.
Raw device DTBs and captured logs remain private. Evidence is retained under
`research/tmp/dsh-mode-contract-0295`.
