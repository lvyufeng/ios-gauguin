#!/usr/bin/env python3
"""Validate finite GPU service records, including sampled success submissions.

This checks the evidence the kernel records. It cannot recover unsampled IBs,
prove pixels, identify a boot image, or establish desktop/Metal performance.
"""
import re

HZ = 32765
RING_WORDS = 8192
FIRST_RECORDS = 16
RECORD_INTERVAL = 120
CP_DONE = ('SWEET GPU CP BOOT: first native ME_INIT/WHERE_AM_I completed; '
           'GPU requests held; before signed ZAP; no unsecured/rendering/Metal')
ONLINE = ('SWEET GPU SERVICE: owner online test_seconds=600; watchdog remains '
          'enabled, failures retain DMA owners')
STOP = ('SWEET GPU SERVICE: test deadline reached; no more refresh, owners '
        'retained until hardware reset')


def need(ok, message):
    if not ok:
        raise ValueError(message)


def records(text, prefix, pattern):
    """Reject malformed/interleaved records instead of silently omitting them."""
    compiled = re.compile(pattern)
    rows = []
    offset = 0
    for raw in text.splitlines(keepends=True):
        line = raw.rstrip('\r\n')
        if prefix in line:
            match = compiled.fullmatch(line) if line.startswith(prefix) else None
            need(match is not None, 'malformed/interleaved ' + prefix)
            values = tuple(map(int, match.groups()))
            need(all(0 <= n < 2**32 for n in values), 'record integer overflow')
            rows.append((offset, offset + len(raw), values))
        offset += len(raw)
    return rows


def _one(rows, name):
    need(len(rows) == 1, 'missing/duplicate ' + name)
    return rows[0]


def _healthy(before, after):
    return 0 <= after <= HZ // 4 and after < before <= 753595 - 3 * HZ


def _ring_reachable(previous_count, previous_shadow, count, shadow):
    """Only bound omitted IBs; do not claim their exact ring increments."""
    if count == previous_count:
        return shadow == previous_shadow
    gap = count - previous_count
    if gap < 0 or not 0 <= shadow < RING_WORDS or shadow % 4:
        return False
    # Every successful submission adds 4*ibs+8 words, with 1 <= ibs <= 128.
    low, high = 12 * gap, 520 * gap
    residue = (shadow - previous_shadow) % RING_WORDS
    wraps = max(0, (low - residue + RING_WORDS - 1) // RING_WORDS)
    return residue + wraps * RING_WORDS <= high


def qualify_service_log(text):
    for bad in ('SWEET PANIC ENTRY', 'phystokv_range: illegal',
                'SWEET WDT SERVICE: failed', 'SWEET GPU SERVICE: health/owner failure',
                'SWEET GPU SERVICE: invalid coordinator context', 'client closed after fault'):
        need(bad not in text, bad)
    checkpoint = _one(records(
        text, 'SWEET GPU WDT: pre-ZAP checkpoint ',
        r'SWEET GPU WDT: pre-ZAP checkpoint seq=(\d+) before=(\d+) after=(\d+); '
        r'CP idle/EOP/fault/routes/power verified'), 'boot checkpoint')
    boot, before, after = checkpoint[2]
    need(boot == 1 and _healthy(before, after), 'invalid boot checkpoint')
    init = 'SWEET GPU ZAP: before phase=2 '
    need(text.count(CP_DONE) == text.count(init) == text.count(ONLINE) == text.count(STOP) == 1,
         'missing/duplicate boot or service boundary')
    need(text.index(CP_DONE) < checkpoint[0] < text.index(init) < text.index(ONLINE),
         'checkpoint or service boundary order differs')

    submissions = records(
        text, 'SWEET GPU USER: submit ',
        r'SWEET GPU USER: submit rc=(\d+) ibs=(\d+) submitted=(\d+) '
        r'completed=(\d+) shadow=(\d+) polls=(\d+)')
    renewals = records(
        text, 'SWEET GPU SERVICE: renew=',
        r'SWEET GPU SERVICE: renew=(\d+) before=(\d+) after=(\d+) submitted=(\d+) '
        r'completed=(\d+) shadow=(\d+); health/idle/routes/power verified')
    final = _one(records(
        text, 'SWEET GPU SERVICE: final ',
        r'SWEET GPU SERVICE: final renewals=(\d+) submitted=(\d+) completed=(\d+) '
        r'shadow=(\d+); quarantined, no further refresh'), 'final service record')
    count, total, completed, final_shadow = final[2]
    need(300 <= count <= 600 and 9 <= total == completed, 'finite service did not complete')
    need([row[2][0] for row in renewals] == [2, *range(30, count + 1, 30)],
         'missing/duplicate/reordered heartbeat sample')
    need(len(submissions) == min(FIRST_RECORDS, total) + total // RECORD_INTERVAL,
         'submission sample count differs from final counter')
    expected = [*range(1, min(FIRST_RECORDS, total) + 1),
                *range(RECORD_INTERVAL, total + 1, RECORD_INTERVAL)]
    need([row[2][2] for row in submissions] == expected,
         'missing/duplicate/reordered or unexpected submission sample')

    snapshots = []
    previous_shadow = 20
    for position, end, row in submissions:
        rc, ibs, submitted, completed, shadow, polls = row
        need(rc == 0 and 1 <= ibs <= 128 and submitted == completed and polls > 0,
             'submission did not complete successfully')
        need(0 <= shadow < RING_WORDS and shadow % 4 == 0, 'invalid submission ring pointer')
        if completed <= FIRST_RECORDS:
            need(shadow == (previous_shadow + 4 * ibs + 8) % RING_WORDS,
                 'startup ring increment differs')
        previous_shadow = shadow
        snapshots.append((position, end, submitted, shadow))
    for position, end, row in renewals:
        sequence, before, after, submitted, completed, shadow = row
        need(_healthy(before, after) and submitted == completed and submitted <= total,
             'unhealthy/incomplete heartbeat')
        snapshots.append((position, end, submitted, shadow))
    snapshots.append((final[0], final[1], total, final_shadow))
    snapshots.sort()
    previous_count, previous_shadow = 0, 20
    online = text.index(ONLINE)
    for position, end, submitted, shadow in snapshots:
        need(online < position <= final[0], 'GPU sample outside online service')
        need(_ring_reachable(previous_count, previous_shadow, submitted, shadow),
             'reported fence/ring snapshots are inconsistent')
        previous_count, previous_shadow = submitted, shadow
    # A heartbeat reporting fence N must follow all explicitly recorded fences <=N.
    for position, end, row in renewals:
        completed = row[4]
        need(all(job_end <= position for _, job_end, job in submissions if job[3] <= completed),
             'heartbeat precedes a recorded completion')
    need(all(end <= final[0] for _, end, _ in submissions + renewals) and
         final[1] <= text.index(STOP), 'finite stop order differs')
    return {
        'state': 'consistent-finite-sampled-GPU-service-records',
        'boot_checkpoint_sequence': boot,
        'boot_checkpoint_before': checkpoint[2][1],
        'boot_checkpoint_after': checkpoint[2][2],
        'verified_renewals': count, 'runtime_renewals': count - boot,
        'native_submissions': total, 'recorded_submissions': len(submissions),
        'unrecorded_successes': total - len(submissions),
        'recorded_fences': expected, 'native_final_shadow': final_shadow,
        'per_submit_ring_proven_through': min(FIRST_RECORDS, total),
        'exact_later_IB_sequence_proven': total <= FIRST_RECORDS,
        'pixels_qualified': False, 'desktop_qualified': False, 'Metal_qualified': False,
    }
