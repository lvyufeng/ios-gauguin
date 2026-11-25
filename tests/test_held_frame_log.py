#!/usr/bin/env python3
"""Require complete, branch-consistent presentation diagnostics, not UI claims."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from gpu_service_log import STOP
from held_frame_log import ENABLED, parse_held_frames


def hold(rejected, submitted=0, replaced=0, consumed=0, retired=0, canceled=0, pending=0, active=0):
    return (f'SWEET FB HOLD: submitted={submitted} replaced={replaced} consumed={consumed} '
            f'retired={retired} canceled={canceled} rejected={rejected} pending={pending} active={active}\n')


def detail(n, reason=2, owner=1, registered=1, mask=0x101, ids=(120, 0, 0, 0)):
    return (f'SWEET FB REJECT: n={n} reason={reason} owner={owner} registered={registered} '
            f'clients=1 mask=0x{mask:x} ids={",".join(map(str, ids))}\n')


def counts(null=0, mask=0, surface0=0, surface1=0, surface2=0, surface3=0, unregistered=0):
    return (f'SWEET FB REJECT COUNTS: null={null} mask={mask} surface0={surface0} '
            f'surface1={surface1} surface2={surface2} surface3={surface3} unregistered={unregistered}\n')


def trace():
    return (ENABLED + '\n' + hold(0) + ''.join(detail(n) for n in range(1, 9)) +
            hold(200) + counts(mask=200) + STOP + '\n' + hold(211) + counts(mask=211))


class HeldFrameLogTests(unittest.TestCase):
    def test_separates_initial_failure_from_planned_stop(self):
        result = parse_held_frames(trace())
        self.assertEqual(result['last_before_planned_stop']['rejected'], 200)
        self.assertEqual(result['last_after_planned_stop']['rejected'], 211)
        self.assertEqual(result['reasons_before_planned_stop']['layer_mask'], 200)
        self.assertEqual(len(result['detailed_rejections']), 8)
        self.assertTrue(result['rejection_cause_observed'])
        for key in ['GPU_execution_qualified', 'desktop_pixels_qualified', 'FPS_qualified', 'high_refresh_qualified', 'daily_use_qualified']:
            self.assertFalse(result[key])

    def test_each_actual_prepare_reason_and_null_owner_short_circuit(self):
        details = [detail(1, 1, owner=0, mask=0)]
        details += [detail(2, 2)]
        details += [detail(layer + 3, layer + 3, mask=1 << layer,
                           ids=tuple(123 if i == layer else 0 for i in range(4))) for layer in range(4)]
        details += [detail(7, 7, owner=0, registered=0, mask=0),
                    detail(8, 7, owner=1, registered=0, mask=0)]
        text = ENABLED + '\n' + ''.join(details) + hold(8) + counts(1, 1, 1, 1, 1, 1, 2) + STOP + '\n'
        result = parse_held_frames(text)
        self.assertEqual([row['reason'] for row in result['detailed_rejections']], [1, 2, 3, 4, 5, 6, 7, 7])

    def test_old_counters_do_not_invent_reasons(self):
        old = ENABLED + '\n' + hold(200) + STOP + '\n' + hold(211)
        result = parse_held_frames(old, require_reasons=False)
        self.assertFalse(result['rejection_cause_observed'])
        self.assertIsNone(result['reasons_before_planned_stop'])
        with self.assertRaises(ValueError):
            parse_held_frames(old)

    def test_later_unsampled_rejections_can_have_different_causes(self):
        text = trace().replace(counts(mask=200), counts(mask=199, unregistered=1))
        text = text.replace(counts(mask=211), counts(mask=200, unregistered=11))
        result = parse_held_frames(text)
        self.assertEqual(result['reasons_before_planned_stop']['unregistered'], 1)
        self.assertEqual(result['reasons_after_planned_stop']['unregistered'], 11)

    def test_stop_between_hold_and_counts_keeps_the_same_snapshot_phase(self):
        text = trace().replace(counts(mask=200) + STOP + '\n', STOP + '\n' + counts(mask=200))
        result = parse_held_frames(text)
        self.assertEqual(result['reasons_before_planned_stop']['layer_mask'], 200)
        self.assertEqual(result['reasons_after_planned_stop']['layer_mask'], 211)
        first = result['reason_snapshot_positions'][0]
        self.assertLess(first['held'], text.index(STOP))
        self.assertGreater(first['counts'], text.index(STOP))

    def test_successful_ownership_accounting_is_scoped(self):
        text = ENABLED + '\n' + hold(0, submitted=5, replaced=1, consumed=3, retired=2, pending=1, active=1) + STOP + '\n'
        result = parse_held_frames(text)
        self.assertEqual(result['last_before_planned_stop']['consumed'], 3)
        self.assertFalse(result['rejection_cause_observed'])
        self.assertFalse(result['desktop_pixels_qualified'])

    def test_kernel_contract_keeps_old_diagnosis_and_new_metadata_distinct(self):
        old = trace().replace('mask=0x101', 'mask=0x80000007')
        self.assertTrue(parse_held_frames(old)['rejection_cause_observed'])
        with self.assertRaises(ValueError):
            parse_held_frames(old, allowed_mask=0x8000000f)
        new = (ENABLED + '\n' + hold(0) + detail(1, 3, mask=0x80000001, ids=(123, 0, 0, 0)) +
               hold(1) + counts(surface0=1) + STOP + '\n')
        result = parse_held_frames(new, allowed_mask=0x8000000f)
        self.assertEqual(result['allowed_update_bits'], '0x8000000f')
        self.assertEqual(result['reasons_before_planned_stop']['surface0'], 1)
        with self.assertRaises(ValueError):
            parse_held_frames(new)
        for invalid in [0xffffffff, 0x7fffffff, 0x1f, True]:
            with self.subTest(contract=invalid), self.assertRaises(ValueError):
                parse_held_frames(trace(), allowed_mask=invalid)

    def test_malformed_missing_duplicate_and_inconsistent_records_fail(self):
        good = trace()
        mutations = [
            good.replace(detail(1), 'IOKit: ' + detail(1)),
            good.replace(detail(1), detail(1).rstrip() + ' other log\n'),
            good.replace(detail(4), ''),
            good.replace(detail(8), detail(8) + detail(9)),
            good.replace(detail(3), detail(2)),
            good.replace(counts(mask=200), counts(mask=199)),
            good.replace(counts(mask=200), ''),
            good.replace(counts(mask=211), counts(mask=211) + counts(mask=211)),
            good.replace(counts(mask=200), 'IOKit: ' + counts(mask=200)),
            good.replace(hold(200), hold(200, submitted=1)),
            good.replace(hold(200), hold(200, consumed=1)),
            good.replace(hold(211), hold(199)),
            good.replace(detail(1), detail(1, mask=1)),
            good.replace(detail(1), detail(1, 3, mask=0, ids=(123, 0, 0, 0))),
            good.replace(detail(1), detail(1, 3, mask=1, ids=(0, 0, 0, 0))),
            good.replace(detail(1), detail(1, 7, registered=1)),
            good.replace(detail(1), detail(1, 1, owner=1, registered=1)),
            good.replace('ids=120,0,0,0', 'ids=4294967296,0,0,0', 1),
            good.replace('mask=0x101', 'mask=0x100000000', 1),
            good.replace(hold(211), hold(1 << 64)),
            good.replace(STOP, ''),
            good + STOP + '\n',
            good.replace(ENABLED, ENABLED + '\n' + ENABLED),
            good.replace(detail(1), detail(1).replace('clients=1', 'clients=0')),
            good.replace(detail(1), 'IOKit noise\v' + detail(1)),
            good.replace(detail(1), 'IOKit noise\f' + detail(1)),
            good.replace(detail(1), 'IOKit noise\u0085' + detail(1)),
            good.replace(hold(0), hold(8) + counts(mask=8)),
            good.replace(hold(200), hold(7)),
            ENABLED + '\n' + hold(200) + ''.join(detail(n) for n in range(1, 9)) + counts(mask=200) + STOP + '\n',
        ]
        # A reason counter can change only by increasing; the sum alone is insufficient.
        mutations.append(good.replace(counts(mask=211), counts(mask=199, unregistered=12)))
        for index, text in enumerate(mutations):
            with self.subTest(index=index), self.assertRaises(ValueError):
                parse_held_frames(text)


if __name__ == '__main__':
    unittest.main()
