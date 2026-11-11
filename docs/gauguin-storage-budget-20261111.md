# Project storage cap

The user requires this project to remain within 500,000,000,000 bytes.
`python3 tools/storage-budget.py --planned-bytes TOTAL_BATCH_BYTES` checks the
whole planned batch before large image, clone or build allocation. It uses
conservative `du` accounting, which counts shared APFS clones repeatedly.
Reserve the full logical allocation for all clones in a batch.

The authorized cleanup retires 497 obsolete generated images, including old
working/edited/final images and superseded experimental HFS prefix snapshots.
Original phone partition backups, retained baselines, the current rollback
snapshot, current final image and active pinned dependencies are preserved.
The private deletion manifest records the exact paths and metadata.

DSH 31567 completes the cleanup in 59.262 seconds. Project accounting falls
from 1,996,059,840,512 to 391,252,217,856 bytes. Actual disk free space increases
by 319,118,360,576 bytes to 323,992,391,680 bytes. The larger accounted reduction
reflects repeated APFS clone accounting and is not physical disk space freed.
All 80 current readiness pins and 17 kernel package pins are rehashed after
deletion. No phone operation occurs during cleanup.

A later check after trial capture reports 391,356,162,048 accounted bytes
(391.4 GB), leaving 108.6 GB within the project cap. This is project artifact
accounting, rather than total usage by every application on the Mac.

Keep cleanup manifests and historical receipts. A retired image referenced by
an old completed trial is no longer available for a fresh verification; do not
describe it as currently present. Future work must budget capacity before
creating another full-root snapshot or temporary image batch.
