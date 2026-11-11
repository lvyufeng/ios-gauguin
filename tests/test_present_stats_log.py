#!/usr/bin/env python3
"""Behavior tests for the strict 0221 SWEET FB present-statistics log parser.

The expected lines come from the IOLog calls in
xnu/patches/0221-gauguin-present-copy-stats.patch, not from the parser's
regular expressions.  A log is parsed as complete snapshots only: a summary
followed by its guard histogram and its copy histogram, in that order.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from present_stats_log import parse_present_stats  # noqa: E402

MAX_U64 = (1 << 64) - 1
ENABLED = 'SWEET FB STATS: enabled; CPU timing only, panel unqualified'
HIST_SUFFIX = '; ns upper bounds 500k,1m,2m,4m,8m,16m,33333333,inf'


def bucket(lower, upper):
    return {'lower_inclusive_ns': lower, 'upper_exclusive_ns': upper}


def main_line(attempts=5, copied=4, zero=1, invalid=0, bytes_=64, layers=4,
              guards=6, refused=1):
    return (f'SWEET FB STATS: attempts={attempts} copied={copied} zero={zero} '
            f'invalid={invalid} bytes={bytes_} layers={layers} '
            f'guards={guards} refused={refused}; CPU, not scanout')


def hist_line(kind, samples, bins):
    return (f'SWEET FB STATS {kind}: samples={samples} '
            f'bins={",".join(str(value) for value in bins)}{HIST_SUFFIX}')


def snapshot(attempts=5, copied=4, zero=1, invalid=0, bytes_=64, layers=4,
             guards=6, refused=1, guard_samples=4, guard_bins=None,
             copy_samples=4, copy_bins=None):
    """Build the three telemetry lines for one complete snapshot."""
    if guard_bins is None:
        guard_bins = [guard_samples, 0, 0, 0, 0, 0, 0, 0]
    if copy_bins is None:
        copy_bins = [copy_samples, 0, 0, 0, 0, 0, 0, 0]
    return [
        main_line(attempts, copied, zero, invalid, bytes_, layers, guards, refused),
        hist_line('GUARD', guard_samples, guard_bins),
        hist_line('COPY', copy_samples, copy_bins),
    ]


def parse(lines):
    return parse_present_stats('\n'.join(lines))


def without(**overrides):
    """Return a valid snapshot with individual fields replaced."""
    values = dict(attempts=5, copied=4, zero=1, invalid=0, bytes_=64, layers=4,
                  guards=6, refused=1, guard_samples=4, guard_bins=None,
                  copy_samples=4, copy_bins=None)
    values.update(overrides)
    return snapshot(**values)


class PresentStatsParserTests(unittest.TestCase):
    def test_complete_multi_snapshot_stream_keeps_every_snapshot(self):
        first = snapshot(attempts=2, copied=1, zero=1, bytes_=8, layers=1,
                         guards=1, refused=0, guard_samples=1,
                         copy_samples=1)
        second = snapshot(attempts=4, copied=3, zero=1, invalid=1, bytes_=24,
                          layers=3, guards=4, refused=1, guard_samples=2,
                          guard_bins=[1, 1, 0, 0, 0, 0, 0, 0],
                          copy_samples=2,
                          copy_bins=[1, 1, 0, 0, 0, 0, 0, 0])
        third = snapshot(attempts=8, copied=6, zero=2, invalid=2, bytes_=96,
                         layers=6, guards=9, refused=2, guard_samples=5,
                         guard_bins=[2, 2, 1, 0, 0, 0, 0, 0],
                         copy_samples=4,
                         copy_bins=[1, 2, 1, 0, 0, 0, 0, 0])
        result = parse(first + second + third)

        self.assertEqual(len(result['snapshots']), 3)
        self.assertEqual([row['counts']['attempts'] for row in result['snapshots']],
                         [2, 4, 8])
        self.assertEqual(result['snapshots'][1]['counts'], {
            'attempts': 4, 'copied': 3, 'zero': 1, 'invalid': 1,
            'bytes': 24, 'layers': 3, 'guards': 4, 'refused': 1,
        })
        self.assertEqual(result['snapshots'][2]['guard']['bins'],
                         [2, 2, 1, 0, 0, 0, 0, 0])
        self.assertEqual(result['snapshots'][2]['copy']['bins'],
                         [1, 2, 1, 0, 0, 0, 0, 0])
        self.assertEqual(result['snapshots'][1]['guard']['p95_bucket_ns'],
                         bucket(500000, 1000000))
        self.assertEqual(result['snapshots'][2]['copy']['p99_bucket_ns'],
                         bucket(1000000, 2000000))

    def test_exact_enabled_announcement_is_accepted(self):
        result = parse([ENABLED] + without())
        self.assertEqual(len(result['snapshots']), 1)
        self.assertEqual(result['snapshots'][0]['counts']['attempts'], 5)

    def test_enabled_announcement_cannot_claim_panel_or_gpu_qualification(self):
        variants = [
            ENABLED.replace('panel unqualified', 'panel qualified'),
            ENABLED.replace('CPU timing only', 'GPU timing only'),
            ENABLED + '; qualified',
            ' ' + ENABLED,
        ]
        for text in variants:
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse([text] + without())

    def test_no_timing_samples_yields_no_percentile_buckets(self):
        result = parse(without(attempts=3, copied=2, zero=1, invalid=3,
                               bytes_=32, layers=2, guards=4, refused=0,
                               guard_samples=0,
                               copy_samples=0))
        row = result['snapshots'][0]
        self.assertEqual(row['guard']['samples'], 0)
        self.assertEqual(row['copy']['samples'], 0)
        self.assertIsNone(row['guard']['p95_bucket_ns'])
        self.assertIsNone(row['guard']['p99_bucket_ns'])
        self.assertIsNone(row['copy']['p95_bucket_ns'])
        self.assertIsNone(row['copy']['p99_bucket_ns'])

    def test_zero_work_snapshot_can_still_record_guard_wait_samples(self):
        result = parse(without(attempts=1, copied=0, zero=1, invalid=0,
                               bytes_=0, layers=0, guards=2, refused=0,
                               guard_samples=1, copy_samples=0))
        row = result['snapshots'][0]
        self.assertEqual(row['counts']['zero'], 1)
        self.assertEqual(row['guard']['samples'], 1)
        self.assertEqual(row['copy']['samples'], 0)
        self.assertEqual(row['guard']['p95_bucket_ns'], bucket(0, 500000))
        self.assertIsNone(row['copy']['p95_bucket_ns'])

    def test_guard_and_copy_populations_are_independent(self):
        result = parse(without(attempts=6, copied=4, zero=2, bytes_=64,
                               layers=4, guards=7, refused=1,
                               guard_samples=5,
                               guard_bins=[2, 2, 1, 0, 0, 0, 0, 0],
                               copy_samples=3,
                               copy_bins=[0, 0, 0, 2, 1, 0, 0, 0]))
        row = result['snapshots'][0]
        self.assertEqual(row['guard']['samples'], 5)
        self.assertEqual(row['copy']['samples'], 3)
        self.assertEqual(row['guard']['p95_bucket_ns'], bucket(1000000, 2000000))
        self.assertEqual(row['guard']['p99_bucket_ns'], bucket(1000000, 2000000))
        self.assertEqual(row['copy']['p95_bucket_ns'], bucket(4000000, 8000000))
        self.assertEqual(row['copy']['p99_bucket_ns'], bucket(4000000, 8000000))

    def test_histogram_edges_are_lower_inclusive_upper_exclusive(self):
        result = parse(without(attempts=2, copied=1, zero=1, bytes_=8,
                               layers=1, guards=2, refused=0,
                               guard_samples=2,
                               guard_bins=[1, 0, 0, 0, 0, 0, 0, 1],
                               copy_samples=1,
                               copy_bins=[1, 0, 0, 0, 0, 0, 0, 0]))
        row = result['snapshots'][0]
        self.assertEqual(row['guard']['p95_bucket_ns'],
                         bucket(33333333, None))
        self.assertEqual(row['copy']['p95_bucket_ns'],
                         bucket(0, 500000))
        self.assertEqual(result['histogram_bounds'],
                         'lower inclusive, upper exclusive; final upper bound unbounded')

    def test_every_histogram_bin_maps_to_its_upper_exclusive_edge(self):
        expected = [
            (0, 500000),
            (500000, 1000000),
            (1000000, 2000000),
            (2000000, 4000000),
            (4000000, 8000000),
            (8000000, 16000000),
            (16000000, 33333333),
            (33333333, None),
        ]
        for index, edges in enumerate(expected):
            with self.subTest(bin=index):
                bins = [0] * 8
                bins[index] = 1
                result = parse(snapshot(attempts=1, copied=1, zero=0,
                                        bytes_=4, layers=1, guards=1,
                                        refused=0, guard_samples=1,
                                        guard_bins=bins, copy_samples=1,
                                        copy_bins=bins))
                row = result['snapshots'][0]
                self.assertEqual(row['guard']['p95_bucket_ns'], bucket(*edges))
                self.assertEqual(row['copy']['p99_bucket_ns'], bucket(*edges))

    def test_p95_and_p99_use_nearest_rank_with_integer_buckets(self):
        rank_ceiling = snapshot(attempts=3, copied=3, zero=0, bytes_=12,
                                layers=3, guards=3, refused=0,
                                guard_samples=3,
                                guard_bins=[2, 1, 0, 0, 0, 0, 0, 0],
                                copy_samples=3,
                                copy_bins=[2, 1, 0, 0, 0, 0, 0, 0])
        exact_rank = snapshot(attempts=100, copied=100, zero=0, bytes_=400,
                              layers=100, guards=100, refused=0,
                              guard_samples=100,
                              guard_bins=[95, 5, 0, 0, 0, 0, 0, 0],
                              copy_samples=100,
                              copy_bins=[95, 5, 0, 0, 0, 0, 0, 0])
        rounded_rank = snapshot(attempts=101, copied=101, zero=0, bytes_=404,
                                layers=101, guards=101, refused=0,
                                guard_samples=101,
                                guard_bins=[95, 6, 0, 0, 0, 0, 0, 0],
                                copy_samples=101,
                                copy_bins=[95, 6, 0, 0, 0, 0, 0, 0])
        result = parse(rank_ceiling + exact_rank + rounded_rank)
        rows = result['snapshots']

        self.assertEqual(rows[0]['guard']['p95_bucket_ns'],
                         bucket(500000, 1000000))
        self.assertEqual(rows[0]['guard']['p99_bucket_ns'],
                         bucket(500000, 1000000))
        self.assertEqual(rows[1]['guard']['p95_bucket_ns'],
                         bucket(0, 500000))
        self.assertEqual(rows[1]['guard']['p99_bucket_ns'],
                         bucket(500000, 1000000))
        self.assertEqual(rows[2]['guard']['p95_bucket_ns'],
                         bucket(500000, 1000000))
        self.assertEqual(rows[2]['guard']['p99_bucket_ns'],
                         bucket(500000, 1000000))
        self.assertEqual(rows[2]['copy']['p99_bucket_ns'],
                         bucket(500000, 1000000))

    def test_zero_snapshot_is_complete(self):
        result = parse(snapshot(attempts=0, copied=0, zero=0, invalid=0,
                                bytes_=0, layers=0, guards=0, refused=0,
                                guard_samples=0, copy_samples=0))
        row = result['snapshots'][0]
        self.assertEqual(row['counts'], {
            'attempts': 0, 'copied': 0, 'zero': 0, 'invalid': 0,
            'bytes': 0, 'layers': 0, 'guards': 0, 'refused': 0,
        })
        self.assertEqual(row['guard']['bins'], [0] * 8)
        self.assertIsNone(row['guard']['p95_bucket_ns'])

    def test_empty_or_no_telemetry_input_fails_closed(self):
        for text in ('', '   \n\t\n', 'unrelated console noise\n', ENABLED + '\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_present_stats(text)
        with self.assertRaises(ValueError):
            parse_present_stats(None)

    def test_uint64_saturation_is_accepted_and_unbounded_percentiles_are_none(self):
        result = parse(without(attempts=MAX_U64, copied=MAX_U64, zero=MAX_U64,
                               bytes_=MAX_U64, layers=MAX_U64,
                               guards=MAX_U64, refused=0,
                               guard_samples=MAX_U64,
                               guard_bins=[MAX_U64, 0, 0, 0, 0, 0, 0, 0],
                               copy_samples=MAX_U64,
                               copy_bins=[MAX_U64, 0, 0, 0, 0, 0, 0, 0]))
        row = result['snapshots'][0]
        self.assertEqual(row['counts']['attempts'], MAX_U64)
        self.assertEqual(row['guard']['bins'][0], MAX_U64)
        self.assertIsNone(row['guard']['p95_bucket_ns'])
        self.assertIsNone(row['copy']['p99_bucket_ns'])

    def test_saturated_histogram_sum_caps_at_uint64(self):
        result = parse(without(attempts=MAX_U64, copied=MAX_U64, zero=0,
                               bytes_=MAX_U64, layers=MAX_U64,
                               guards=MAX_U64, refused=0,
                               guard_samples=MAX_U64,
                               guard_bins=[MAX_U64, MAX_U64, 0, 0, 0, 0, 0, 0],
                               copy_samples=MAX_U64,
                               copy_bins=[MAX_U64, 0, 0, 0, 0, 0, 0, 0]))
        self.assertEqual(result['snapshots'][0]['guard']['samples'], MAX_U64)

    def test_values_above_uint64_are_rejected_everywhere(self):
        main_fields = ('attempts', 'copied', 'zero', 'invalid', 'bytes_',
                       'layers', 'guards', 'refused')
        for field in main_fields:
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'uint64'):
                parse(without(**{field: MAX_U64 + 1}))

        for kind in ('guard', 'copy'):
            with self.subTest(kind=kind, field='samples'), \
                    self.assertRaisesRegex(ValueError, 'uint64'):
                lines = without()
                index = 1 if kind == 'guard' else 2
                lines[index] = hist_line(kind.upper(), MAX_U64 + 1,
                                         [0, 0, 0, 0, 0, 0, 0, 0])
                parse(lines)
            with self.subTest(kind=kind, field='bin'), \
                    self.assertRaisesRegex(ValueError, 'uint64'):
                lines = without()
                index = 1 if kind == 'guard' else 2
                bins = [0, 0, 0, 0, 0, 0, 0, MAX_U64 + 1]
                lines[index] = hist_line(kind.upper(), MAX_U64 + 1, bins)
                parse(lines)

    def test_truncated_streams_are_rejected(self):
        complete = without()
        cases = [
            [complete[0]],
            complete[:2],
            complete + [complete[0]],
            ['prefix', complete[0]],
            [complete[1]],
            [complete[2]],
        ]
        for lines in cases:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse(lines)

    def test_duplicate_and_out_of_order_telemetry_is_rejected(self):
        main, guard, copy = without()
        second = without(attempts=6, copied=5, zero=1)
        cases = [
            [main, main, guard, copy],
            [main, guard, guard, copy],
            [main, guard, copy, copy],
            [main, guard, second[0], copy, second[1], second[2]],
            [guard, main, copy],
            [main, copy, guard],
            [main, copy],
        ]
        for lines in cases:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse(lines)

    def test_noise_between_telemetry_lines_is_allowed(self):
        main, guard, copy = without()
        lines = [
            'kernel[0]: unrelated boot chatter',
            main,
            'SWEET FB: swap 1 by backboardd layer 0 surface 2 100x100',
            guard,
            ENABLED,
            'kernel[0]: tail noise',
            copy,
            'kernel[0]: after math',
        ]
        result = parse(lines)
        self.assertEqual(len(result['snapshots']), 1)

    def test_noise_that_looks_like_telemetry_is_not_silently_skipped(self):
        main, guard, copy = without()
        cases = [
            [main, 'kernel[0]: ' + guard, copy],
            ['kernel[0]: ' + main, guard, copy],
            [main, guard, 'kernel[0]: ' + copy],
            ['SWEET FB STATS GUARD: samples=4 bins=4,0,0,0,0,0,0,0' + HIST_SUFFIX,
             main, guard, copy],
        ]
        for lines in cases:
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse(lines)

    def test_wrong_histogram_sums_are_rejected(self):
        cases = [
            ('guard', 1, [1, 1, 1, 0, 0, 0, 0, 0]),
            ('copy', 2, [2, 1, 1, 1, 0, 0, 0, 0]),
        ]
        for kind, index, bins in cases:
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'histogram'):
                lines = without()
                lines[index] = hist_line(kind.upper(), 4, bins)
                parse(lines)

    def test_invalid_refused_copy_and_guard_relationships_are_rejected(self):
        cases = [
            dict(attempts=6),
            dict(invalid=6),
            dict(refused=7),
            dict(layers=3),
            dict(bytes_=3),
            dict(guard_samples=7, guard_bins=[7, 0, 0, 0, 0, 0, 0, 0]),
            dict(copy_samples=5, copy_bins=[5, 0, 0, 0, 0, 0, 0, 0]),
            dict(attempts=5, invalid=1, guard_samples=5,
                 guard_bins=[5, 0, 0, 0, 0, 0, 0, 0]),
            dict(attempts=5, copied=5, zero=0, invalid=1, bytes_=20,
                 layers=5, guards=5, guard_samples=4,
                 copy_samples=5, copy_bins=[5, 0, 0, 0, 0, 0, 0, 0]),
        ]
        for index, overrides in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ValueError):
                parse(without(**overrides))

    def test_copied_bytes_cover_at_least_one_pixel_per_copied_frame(self):
        # Each copied layer adds w*h*4 bytes with positive w and h.  Unsaturated
        # totals therefore cannot be smaller than four bytes per copied frame.
        with self.assertRaises(ValueError):
            parse(without(attempts=2, copied=2, zero=0, bytes_=5, layers=2,
                          guards=2, refused=0, guard_samples=2,
                          guard_bins=[2, 0, 0, 0, 0, 0, 0, 0],
                          copy_samples=2,
                          copy_bins=[2, 0, 0, 0, 0, 0, 0, 0]))

    def test_regressed_main_counters_are_rejected(self):
        previous = dict(attempts=100, copied=10, zero=90, bytes_=1000,
                        layers=20, guards=200, refused=5,
                        guard_samples=90,
                        guard_bins=[50, 40, 0, 0, 0, 0, 0, 0])
        replacements = [
            dict(attempts=99, copied=10, zero=89),
            dict(copied=9, zero=91, copy_samples=9,
                 copy_bins=[9, 0, 0, 0, 0, 0, 0, 0]),
            dict(copied=12, zero=88, bytes_=1200),
            dict(bytes_=999),
            dict(layers=19),
            dict(guards=199),
            dict(refused=4),
        ]
        for overrides in replacements:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, 'regress'):
                parse(snapshot(**previous) +
                      snapshot(**dict(previous, **overrides)))

    def test_invalid_time_counter_regression_is_rejected(self):
        previous = dict(attempts=100, copied=10, zero=90, invalid=2,
                        bytes_=1000, layers=20, guards=200, refused=5,
                        guard_samples=90,
                        guard_bins=[50, 40, 0, 0, 0, 0, 0, 0])
        following = dict(previous, invalid=1)
        with self.assertRaisesRegex(ValueError, 'regress'):
            parse(snapshot(**previous) + snapshot(**following))

    def test_regressed_histogram_samples_and_bins_are_rejected(self):
        previous = dict(attempts=100, copied=10, zero=90, bytes_=1000,
                        layers=20, guards=200, refused=5,
                        guard_samples=90,
                        guard_bins=[50, 40, 0, 0, 0, 0, 0, 0],
                        copy_samples=10,
                        copy_bins=[10, 0, 0, 0, 0, 0, 0, 0])
        replacements = [
            dict(guard_samples=89, guard_bins=[49, 40, 0, 0, 0, 0, 0, 0]),
            dict(guard_samples=90, guard_bins=[49, 41, 0, 0, 0, 0, 0, 0]),
            dict(copy_samples=9, copy_bins=[9, 0, 0, 0, 0, 0, 0, 0]),
            dict(copy_samples=10, copy_bins=[9, 1, 0, 0, 0, 0, 0, 0]),
        ]
        for overrides in replacements:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(ValueError, 'regress'):
                parse(snapshot(**previous) +
                      snapshot(**dict(previous, **overrides)))

    def test_malformed_telemetry_is_never_repaired(self):
        main, guard, copy = without()
        bad_main = [
            main.replace('; CPU, not scanout', '; GPU, not scanout'),
            main.replace('attempts=', 'attempts ='),
            main.replace(' copied=4', ''),
            main + ' extra',
            main.replace('attempts=5', 'attempts=5.0'),
            main.replace('attempts=5', 'attempts=-1'),
        ]
        for text in bad_main:
            with self.subTest(kind='main', text=text), self.assertRaises(ValueError):
                parse([text, guard, copy])

        bad_guard = [
            'SWEET FB STATS GUARD: samples=4 bins=4,0,0,0,0,0,0' + HIST_SUFFIX,
            'SWEET FB STATS GUARD: samples=4 bins=4,0,0,0,0,0,0,0,0' + HIST_SUFFIX,
            guard.replace('; ns upper bounds', '; ns upper bound'),
            guard.replace('samples=4 ', ''),
            guard.replace('bins=4', 'bins=4.0'),
            guard.replace('33333333,inf', '33333333'),
            guard + ';',
        ]
        for text in bad_guard:
            with self.subTest(kind='guard', text=text), self.assertRaises(ValueError):
                parse([main, text, copy])

        for text in (copy.replace('samples=4', 'samples=four'),
                     copy.replace(HIST_SUFFIX, '')):
            with self.subTest(kind='copy', text=text), self.assertRaises(ValueError):
                parse([main, guard, text])

    def test_parser_makes_no_hardware_or_fps_claims(self):
        result = parse(without(attempts=1, copied=1, zero=0, bytes_=4,
                               layers=1, guards=1, refused=0,
                               guard_samples=1,
                               guard_bins=[1, 0, 0, 0, 0, 0, 0, 0],
                               copy_samples=1,
                               copy_bins=[1, 0, 0, 0, 0, 0, 0, 0]))
        self.assertIs(result['disabled_trace_overhead_qualified'], False)
        self.assertIs(result['panel_scanout_qualified'], False)
        self.assertIs(result['physical_FPS_qualified'], False)
        self.assertIs(result['input_latency_qualified'], False)
        self.assertIs(result['desktop_correctness_qualified'], False)
        self.assertEqual(result['scope'],
                         'CPU guard-acquisition and copied-byte wall intervals')

    def test_copy_samples_require_a_guard_sample(self):
        # Every copied layer follows a successful GPU read guard in the same
        # present, so a copy timing sample implies a guard timing sample.
        with self.assertRaises(ValueError):
            parse(without(attempts=5, copied=4, zero=1, guards=6, refused=0,
                          guard_samples=2, guard_bins=[2, 0, 0, 0, 0, 0, 0, 0],
                          copy_samples=4, copy_bins=[4, 0, 0, 0, 0, 0, 0, 0]))

    def test_copied_frames_require_successful_guards(self):
        # copied counts presents that copied bytes; guards counts GPU read
        # acquisitions.  At least one successful guard precedes each copy.
        with self.assertRaises(ValueError):
            parse(without(attempts=5, copied=5, zero=0, bytes_=20, layers=5,
                          guards=4, refused=0, guard_samples=4,
                          guard_bins=[4, 0, 0, 0, 0, 0, 0, 0],
                          copy_samples=4, copy_bins=[4, 0, 0, 0, 0, 0, 0, 0]))

    def test_duplicate_complete_snapshot_is_rejected(self):
        # attempts increments once per present, so below saturation a second
        # identical snapshot can only be a duplicated record.
        complete = without()
        with self.assertRaises(ValueError):
            parse(complete + complete)


if __name__ == '__main__':
    unittest.main()
