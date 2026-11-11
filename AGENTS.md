# Working on ios-sweet

- Read `NOTES.md` before starting; it contains the project goal, hardware facts,
  current blocker, local artifact locations and the next concrete action.
- The user switches agents frequently. Update the active handoff in `NOTES.md`
  after each milestone and before stopping. Record commits, CI run IDs, exact
  build/boot results and unfinished work. Distinguish observations from guesses.
- Commit completed changes. Use `gh` for GitHub Actions kernel builds and logs.
  Local single-file cross-compiles are useful before spending a CI run.
- Device bring-up uses temporary `fastboot boot` images. Preserve the Android
  installation and partition backups. The user approved (2026-10-15) using
  internal UFS for iOS and said Android may be deleted: the iOS root goes
  into the existing `userdata` partition (no GPT changes). Keep bootloaders,
  recovery, modem, persist and the backups intact, and confirm each
  destructive step with the user before running it.
- Keep device dumps, serial numbers and downloaded Apple artifacts out of git.
- The user set a 500 GB project storage cap on 2026-11-11 (500,000,000,000
  bytes). Before creating large images, clones or build batches, run
  `python3 tools/storage-budget.py --planned-bytes TOTAL_BATCH_BYTES` and
  proceed only if admitted. Count APFS clones conservatively. Retire obsolete
  generated temporary images when needed, recording the cleanup manifest.
  Preserve original phone partition backups, current rollback snapshots and
  all inputs pinned by the active trial. Keep enough space within the cap for
  the entire planned batch, rather than checking each clone separately.
