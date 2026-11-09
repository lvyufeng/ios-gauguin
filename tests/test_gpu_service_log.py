#!/usr/bin/env python3
"""Reject incomplete/corrupt sampled evidence without inventing omitted jobs."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'tools'))
from gpu_service_log import CP_DONE, ONLINE, STOP, qualify_service_log


def trace(total=253):
    """Synthetic records for parser testing, never a physical acceptance result."""
    lines = [CP_DONE,
             'SWEET GPU WDT: pre-ZAP checkpoint seq=1 before=418515 after=0; '
             'CP idle/EOP/fault/routes/power verified',
             'SWEET GPU ZAP: before phase=2 token=fixture', ONLINE,
             'SWEET GPU SERVICE: renew=2 before=32766 after=0 submitted=0 '
             'completed=0 shadow=20; health/idle/routes/power verified']
    shadow = 20
    for job in range(1, total + 1):
        ibs = (job * 31) % 128 + 1
        shadow = (shadow + ibs * 4 + 8) % 8192
        if job <= 16 or job % 120 == 0:
            lines.append(f'SWEET GPU USER: submit rc=0 ibs={ibs} submitted={job} '
                         f'completed={job} shadow={shadow} polls=2')
    for renewal in range(30, 597, 30):
        lines.append(f'SWEET GPU SERVICE: renew={renewal} before=32766 after=0 '
                     f'submitted={total} completed={total} shadow={shadow}; '
                     'health/idle/routes/power verified')
    lines.extend([f'SWEET GPU SERVICE: final renewals=596 submitted={total} '
                  f'completed={total} shadow={shadow}; quarantined, no further refresh', STOP])
    return '\n'.join(lines) + '\n'


class ServiceEvidence(unittest.TestCase):
    def test_sampling_boundaries_and_unknown_evidence(self):
        for total in (9, 15, 16, 17, 119, 120, 121, 239, 240, 241, 253, 10003):
            with self.subTest(total=total):
                result = qualify_service_log(trace(total))
                self.assertEqual(result['native_submissions'], total)
                self.assertEqual(result['recorded_submissions'], min(16, total) + total // 120)
                self.assertEqual(result['unrecorded_successes'], total - result['recorded_submissions'])
                self.assertEqual(result['per_submit_ring_proven_through'], min(16, total))
                self.assertEqual(result['exact_later_IB_sequence_proven'], total <= 16)
                self.assertEqual(result['runtime_renewals'], 595)
                self.assertFalse(result['pixels_qualified'])
                self.assertFalse(result['desktop_qualified'])
                self.assertFalse(result['Metal_qualified'])

    def test_crlf_records(self):
        self.assertEqual(qualify_service_log(trace().replace('\n', '\r\n'))['native_submissions'], 253)

    def test_corrupt_or_missing_records(self):
        original = trace()
        lines = original.splitlines(keepends=True)
        first = next(line for line in lines if line.startswith('SWEET GPU USER: submit '))
        last_sample = next(line for line in lines if ' submitted=240 completed=240 ' in line)
        final = next(line for line in lines if line.startswith('SWEET GPU SERVICE: final '))
        heartbeat = next(line for line in lines if 'renew=30 ' in line)
        mutations = {
            'lost startup record': original.replace(first, ''),
            'lost streaming sample': original.replace(last_sample, ''),
            'duplicate sample': original.replace(last_sample, last_sample * 2),
            'submission error': original.replace(first, first.replace('rc=0 ', 'rc=4 ')),
            'invalid IB count': original.replace(first, first.replace('ibs=32 ', 'ibs=0 ')),
            'no polling evidence': original.replace(first, first.replace('polls=2', 'polls=0')),
            'ring increment wrong': original.replace(first, first.replace('shadow=156 ', 'shadow=160 ')),
            'interleaved prefix': original.replace(first, 'unrelated ' + first),
            'truncated record': original.replace(first, first[:40] + '\n'),
            'negative error': original.replace(first, first.replace('rc=0 ', 'rc=-1 ')),
            'overflowing field': original.replace(first, first.replace('polls=2', 'polls=4294967296')),
            'lost heartbeat': original.replace(heartbeat, ''),
            'duplicate heartbeat': original.replace(heartbeat, heartbeat * 2),
            'bad renewal readback': original.replace(heartbeat, heartbeat.replace('after=0 ', 'after=32766 ')),
            'heartbeat incomplete fence': original.replace(heartbeat, heartbeat.replace('completed=253 ', 'completed=252 ')),
            'missing final': original.replace(final, ''),
            'duplicate final': original.replace(final, final * 2),
            'incomplete final fence': original.replace(final, final.replace('completed=253 ', 'completed=252 ')),
            'final count behind records': original.replace(final, final.replace('submitted=253 completed=253', 'submitted=120 completed=120')),
            'final impossible counter': original.replace(final, final.replace('submitted=253 completed=253', 'submitted=4294967295 completed=4294967295')),
            'unaligned final pointer': original.replace(final, final.replace('shadow=', 'shadow=1')),
            'lost quarantine': original.replace(STOP, ''),
            'wrong boot sequence': original.replace('checkpoint seq=1 ', 'checkpoint seq=2 '),
            'missing CP boundary': original.replace(CP_DONE, ''),
            'health failure': original + 'SWEET GPU SERVICE: health/owner failure\n',
            'panic': original + 'SWEET PANIC ENTRY\n',
        }
        for name, changed in mutations.items():
            with self.subTest(name=name):
                self.assertNotEqual(changed, original)
                with self.assertRaises(ValueError):
                    qualify_service_log(changed)

    def test_future_completion_cannot_precede_its_record(self):
        original = trace()
        lines = original.splitlines(keepends=True)
        heartbeat = next(line for line in lines if 'renew=30 ' in line)
        lines.remove(heartbeat)
        first = next(i for i, line in enumerate(lines) if line.startswith('SWEET GPU USER: submit '))
        lines.insert(first, heartbeat)
        with self.assertRaises(ValueError):
            qualify_service_log(''.join(lines))

    def test_same_fence_pointer_must_be_consistent(self):
        original = trace()
        lines = original.splitlines(keepends=True)
        heartbeat = next(line for line in lines if 'renew=30 ' in line)
        # A different aligned pointer at the same completed fence is inconsistent.
        import re
        pointer = int(re.search(r'shadow=(\d+)', heartbeat)[1])
        changed = heartbeat.replace(f'shadow={pointer}', f'shadow={(pointer + 4) % 8192}')
        with self.assertRaises(ValueError):
            qualify_service_log(original.replace(heartbeat, changed))


if __name__ == '__main__':
    unittest.main(verbosity=2)
