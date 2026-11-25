#!/usr/bin/env python3
"""Host tests for tools/extract_cmd_db_snapshot.py (synthetic only).

Fixtures are generated in a TemporaryDirectory: a synthetic 131072-byte block,
a synthetic boot image and a kernel log with complete Darwin banners, one
boot-args line and the full RAW protocol. The extractor itself is imported;
the repo tools directory is put on sys.path for kernel_banner, exactly like the
CLI's PYTHONPATH. No real device dumps are used.

Line positions are never hard-coded: every fixture line is located by prefix.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / 'tools/kernel_banner.py').is_file())
TOOLS = ROOT / 'tools'
sys.path[:0] = [str(TOOLS), str(ROOT / 'tools')]

import extract_cmd_db_snapshot as extractor  # noqa: E402

TRIAL = 'a1b2c3'
BANNER = (b'Darwin Kernel Version 22.0.0: Thu Jan  1 00:00:00 PST 2026; '
          b'root:xnu-candidate/RELEASE_ARM64_TARGET')
OTHER_BANNER = (b'Darwin Kernel Version 21.6.0: Mon Jan  1 00:00:00 PST 2024; '
                b'root:xnu-other/RELEASE_ARM64_TARGET')
BLOCK = bytes((i * 7 + (i >> 8)) & 0xff for i in range(extractor.BLOCK_BYTES))
DIGEST = hashlib.sha256(BLOCK).hexdigest()

BEGIN_PREFIX = b'SWEET CMDB BEGIN:'
END_PREFIX = b'SWEET CMDB END:'
RAW_PREFIX = b'SWEET CMDB RAW:'
# Real verified log shape: label, ': ', then boot-args with spaces around '='.
BOOT_ARGS_LABEL = b'<Notice>: boot-args = '
BOOT_ARGS_PREFIX = BOOT_ARGS_LABEL


def make_image(banner=BANNER):
    # A real image carries the banner twice as identical copies.
    return b'IMG\x00' + banner + b'\x00' + b'\x00' * 64 + banner + b'\x00TAIL'


def raw_lines(block=BLOCK):
    return [f'SWEET CMDB RAW: offset={offset:05x} data={block[offset:offset + 64].hex()}'
            for offset in range(0, len(block), 64)]


def marker(trial=TRIAL):
    return b'sweettrial=' + trial.encode()


def make_lines(block=BLOCK, boot_args=None, trial=TRIAL, noise=False):
    sha = hashlib.sha256(block).hexdigest()
    if boot_args is None:
        # Real verified shape: the trial token is followed by further options,
        # so it is complete only when delimited on both sides by whitespace.
        boot_args = (b'debug=0x8 KeepSymbols=0x1 serial=3 '
                     + marker(trial) + b' sweettrial-coordinator=0')
    lines = [
        b'[0] Sweet kernel starting',
        b'Booting: ' + BANNER + b'\r\r',
        BOOT_ARGS_PREFIX + boot_args,
        b'[1] SWEET BUS PROBE: CMDDB snapshot begin',
        f'SWEET CMDB BEGIN: bytes=131072 sha256={sha}'.encode(),
    ]
    for index, line in enumerate(raw_lines(block)):
        if noise and index % 256 == 100:
            lines.append(f'[3] unrelated kernel message #{index}'.encode())
        lines.append(line.encode())
    lines += [
        f'SWEET CMDB END: bytes=131072 sha256={sha}'.encode(),
        b'[1] SWEET BUS PROBE: complete PLAN ONLY',
    ]
    return lines


def index_of(lines, prefix, start=0):
    """Index of the first line at/after start that starts with prefix."""
    for i in range(start, len(lines)):
        if lines[i].startswith(prefix):
            return i
    raise AssertionError(f'no line with prefix {prefix!r} from {start}')


def flip(byte):
    """Change a hex digit while keeping the replacement in [0-9a-f]."""
    return ord('1') if byte == ord('0') else ord('0')


def nasty(_ascii_byte):
    """Always replace the original byte with a non-hex byte."""
    return ord('!')


def raw_index(lines, chunk):
    """Locate the chunk-th RAW record, ignoring interleaved kernel lines."""
    if chunk < 0:
        raise AssertionError(f'negative RAW chunk {chunk}')
    found = index_of(lines, RAW_PREFIX, index_of(lines, BEGIN_PREFIX) + 1)
    for _ in range(chunk):
        found = index_of(lines, RAW_PREFIX, found + 1)
    return found


def raw_line(lines, chunk):
    """The chunk-th RAW line of an unmutated fixture built by make_lines."""
    return lines[raw_index(lines, chunk)]


def replace_raw(lines, chunk, line):
    lines[raw_index(lines, chunk)] = line


def insert_noise(lines, at_chunk):
    """Insert two unrelated kernel lines immediately before a RAW chunk."""
    at = raw_index(lines, at_chunk)
    return (lines[:at] +
            [b'[5] unrelated kernel message', b'[6] another unrelated message'] +
            lines[at:])


def last_index_of(lines, prefix):
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].startswith(prefix):
            return i
    raise AssertionError(f'no line with prefix {prefix!r}')


class Fixture:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.image = self.directory / 'boot.img'
        self.log = self.directory / 'log.txt'
        self.out = self.directory / 'cmd_db.bin'
        self.image.write_bytes(make_image())
        self.write_lines()

    def write_lines(self, lines=None):
        self.lines = make_lines() if lines is None else list(lines)
        self.log.write_bytes(b'\n'.join(self.lines) + b'\n')

    def set_boot_args(self, remainder):
        """Replace the whole boot-args line: remainder follows 'boot-args = '."""
        lines = list(self.lines)
        lines[self.boot_args()] = BOOT_ARGS_LABEL + remainder
        self.write_lines(lines)

    def boot_args(self):
        return index_of(self.lines, b'<Notice>: boot-args')

    def begin(self):
        return index_of(self.lines, BEGIN_PREFIX)

    def end(self):
        return last_index_of(self.lines, END_PREFIX)

    def raw(self, chunk=0):
        return raw_index(self.lines, chunk)

    def extract(self, trial=TRIAL):
        return extractor.extract(self.image, self.log, trial, self.out)

    def assert_untouched(self, case, prior=None):
        if prior is None:
            case.assertFalse(self.out.exists())
        else:
            case.assertTrue(self.out.exists())
            case.assertEqual(self.out.read_bytes(), prior)


class ExtractCase(unittest.TestCase):
    def setUp(self):
        self._temporary = tempfile.TemporaryDirectory()
        self.fixture = Fixture(self._temporary.name)

    def tearDown(self):
        self._temporary.cleanup()

    def mutate(self, index, old=None, new=None, remove=False):
        """Replace `old` with `new`; with old=None, overwrite the whole line."""
        lines = list(self.fixture.lines)
        if remove:
            del lines[index]
        elif old is None:
            lines[index] = new
        else:
            self.assertIn(old, lines[index])
            lines[index] = lines[index].replace(old, new)
        self.fixture.write_lines(lines)

    def assert_rejected(self, fragment, trial=TRIAL):
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract(trial)
        self.assertIn(fragment, str(context.exception))
        self.fixture.assert_untouched(self)


class PositiveTests(ExtractCase):
    def test_fixture_control_layout(self):
        # The control log is the exact shape the worker will print.
        self.assertEqual(self.fixture.lines[self.fixture.begin() + 1], self.fixture.lines[self.fixture.raw()])
        self.assertGreater(self.fixture.end(), self.fixture.raw(2047))
        self.assertGreater(self.fixture.raw(0), self.fixture.boot_args())
        self.assertEqual(self.fixture.lines[self.fixture.boot_args()],
                         BOOT_ARGS_LABEL + b'debug=0x8 KeepSymbols=0x1 serial=3 '
                         b'sweettrial=a1b2c3 sweettrial-coordinator=0')

    def test_exact_block_and_digest(self):
        self.assertEqual(self.fixture.extract(), DIGEST)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)
        self.assertEqual(len(self.fixture.out.read_bytes()), 131072)

    def test_actual_0112_shaped_boot_args(self):
        # Real verified shape: '<Notice>: boot-args = debug=0x8 serial=3 ...
        # sweettrial=passtage-0112-20261106-dsh-a1 ...' (trial near the end).
        value = 'passtage-0112-20261106-dsh-a1'
        self.fixture.set_boot_args(
            b'debug=0x8 KeepSymbols=0x1 serial=3 cpus=8 wdt=1 ' + marker(value) +
            b' sweettrial-coordinator=0')
        self.assertEqual(self.fixture.extract(trial=value), DIGEST)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_compact_boot_args(self):
        # 'boot-args=sweettrial=x ...': '=' directly before the marker is a
        # delimiter, so the compact form is a complete marker.
        lines = make_lines()
        lines[self.fixture.boot_args()] = (
            b'<Notice>: boot-args=' + marker() + b' debug=0x8 sweettrial-coordinator=0')
        self.fixture.write_lines(lines)
        self.assertEqual(self.fixture.extract(), DIGEST)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_compact_bare_trial_only(self):
        self.fixture.set_boot_args(marker())
        self.assertEqual(self.fixture.extract(), DIGEST)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_compact_form_with_spaces_around_equals(self):
        # Optional spaces around '=' are part of the label; the captured
        # remainder begins at the first non-space option.
        labels = (b'<Notice>: boot-args=sweettrial=' + TRIAL.encode() +
                  b' debug=0x8 sweettrial-coordinator=0',
                  b'<Notice>: boot-args =  debug=0x8 ' + marker() +
                  b' sweettrial-coordinator=0',
                  b'<Notice>: boot-args=  ' + marker() + b'   debug=0x8')
        for case, label in enumerate(labels):
            with self.subTest(label=label[:40]):
                directory = self.fixture.directory / f'compact-{case}'
                directory.mkdir()
                fixture = Fixture(directory)
                lines = make_lines()
                lines[index_of(lines, BOOT_ARGS_PREFIX)] = label
                fixture.write_lines(lines)
                self.assertEqual(fixture.extract(), DIGEST)
                self.assertEqual(fixture.out.read_bytes(), BLOCK)

    def test_compact_boot_args_and_crlf(self):
        # CRLF endings must retain both the banner line and the boot-args
        # identity: the banner still terminates, the marker is whole, and
        # every RAW line still fullmatches with its '\r'.
        lines = make_lines(noise=True)
        out = [line + b'\r' for line in lines]
        out[index_of(out, BOOT_ARGS_PREFIX)] = (
            b'<Notice>: boot-args=' + marker() + b' debug=0x8\r')
        self.fixture.log.write_bytes(b'\n'.join(out) + b'\r\n[2] more output\r\n')
        self.assertIn(BANNER, self.fixture.log.read_bytes())
        self.assertIn(marker(), self.fixture.log.read_bytes())
        self.assertEqual(self.fixture.extract(), DIGEST)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_crlf_spaced_identity_trial_last(self):
        # Spaced label, trial as the last option, trial followed by '\r':
        # still exactly one complete marker.
        lines = make_lines(noise=True)
        out = [line + b'\r' for line in lines]
        out[index_of(out, BOOT_ARGS_PREFIX)] = BOOT_ARGS_LABEL + b'debug=0x8 ' + marker() + b'\r'
        self.fixture.log.write_bytes(b'\n'.join(out) + b'\n')
        self.assertEqual(self.fixture.extract(), DIGEST)

    def test_interleaved_noise(self):
        lines = make_lines(noise=True)
        # Unrelated lines between BEGIN, some RAW chunks and END (8 CPUs).
        self.fixture.write_lines(lines)
        self.assertGreater(len(lines), 2048 + 5)
        noise = index_of(lines, b'[3] unrelated')
        self.assertLess(self.fixture.begin(), noise)
        self.assertLess(self.fixture.raw(99), noise)
        self.assertLess(noise, self.fixture.raw(100))
        self.assertLess(noise, self.fixture.end())
        self.assertEqual(self.fixture.extract(), DIGEST)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_identity_line_after_block(self):
        # Legitimate identity outside the block: the boot-args line after END.
        lines = [line for line in make_lines() if not line.startswith(BOOT_ARGS_PREFIX)]
        lines.append(BOOT_ARGS_LABEL + b'serial=3 ' + marker())
        self.fixture.write_lines(lines)
        self.assertGreater(self.fixture.boot_args(), self.fixture.end())
        self.assertEqual(self.fixture.extract(), DIGEST)


class ProtocolRejectionTests(ExtractCase):
    def test_missing_begin(self):
        self.mutate(self.fixture.begin(), BEGIN_PREFIX, b'SWEET CMDB BEGIN =')
        self.assert_rejected('BEGIN line')

    def test_duplicate_begin(self):
        lines = list(self.fixture.lines)
        lines.append(lines[self.fixture.begin()])
        self.fixture.write_lines(lines)
        self.assert_rejected('BEGIN line')

    def test_truncated_begin_count(self):
        self.mutate(self.fixture.begin(), b'bytes=131072', b'bytes=13107')
        self.assert_rejected('BEGIN line')

    def test_missing_end(self):
        self.mutate(self.fixture.end(), remove=True)
        self.assert_rejected('END line')

    def test_duplicate_end(self):
        lines = list(self.fixture.lines)
        lines.append(lines[self.fixture.end()])
        self.fixture.write_lines(lines)
        self.assert_rejected('END line')

    def test_end_before_begin(self):
        lines = list(self.fixture.lines)
        begin, end = self.fixture.begin(), self.fixture.end()
        lines[begin], lines[end] = lines[end], lines[begin]
        self.fixture.write_lines(lines)
        self.assert_rejected('END precedes BEGIN')

    def test_out_of_order_chunks(self):
        i = self.fixture.raw(10)
        self.fixture.write_lines(self.fixture.lines[:i] +
                                 [self.fixture.lines[i + 1], self.fixture.lines[i]] +
                                 self.fixture.lines[i + 2:])
        self.assert_rejected('offset 002c0')

    def test_duplicate_chunk(self):
        lines = list(self.fixture.lines)
        lines[self.fixture.raw(3)] = lines[self.fixture.raw(2)]
        self.fixture.write_lines(lines)
        self.assert_rejected('offset 00080')

    def test_chunk_corruption(self):
        line = bytearray(self.fixture.lines[self.fixture.raw(77)])
        line[-1] = ord('0') if line[-1] != ord('0') else ord('1')
        self.fixture.write_lines(self.fixture.lines[:self.fixture.raw(77)] + [bytes(line)] +
                                 self.fixture.lines[self.fixture.raw(77) + 1:])
        self.assert_rejected('sha256 does not match')

    def test_corruption_before_namespace_followed_by_raw(self):
        # Corrupting the 'SWEET' prefix turns that RAW line into a stray
        # non-CMDB log line; only 2047 RAW lines remain, so even the 'block'
        # is a complete 131008-byte prefix: rejected as an incomplete block,
        # never silently accepted (and never as a SHA failure).
        for position in (0, 4):
            with self.subTest(position=position):
                lines = insert_noise(make_lines(), 59)
                broken = bytearray(raw_line(lines, 50))
                broken[position] = nasty(broken[position])
                replace_raw(lines, 50, bytes(broken))
                self.fixture.write_lines(lines)
                self.assert_rejected('RAW lines')

    def test_corruption_inside_namespace(self):
        # 'SWEET CMDB RAw: ...' is an unknown CMDB namespace line: malformed.
        self.mutate(self.fixture.raw(50), b'SWEET CMDB RAW: ', b'SWEET CMDB RAw: ')
        self.assert_rejected('malformed or unknown CMDB line')

    def test_corruption_of_offset(self):
        # Each offset digit remains valid hex, so the record has a wrong
        # offset and must be rejected before the digest comparison.
        for digit in range(5):
            with self.subTest(digit=digit):
                lines = insert_noise(make_lines(), 45)
                broken = bytearray(raw_line(lines, 50))
                field_at = broken.index(b'offset=') + len(b'offset=')
                position = field_at + digit
                broken[position] = flip(broken[position])
                wrong_offset = broken[field_at:field_at + 5].decode('ascii')
                replace_raw(lines, 50, bytes(broken))
                self.fixture.write_lines(lines)
                self.assert_rejected(f'RAW chunk 50 has offset {wrong_offset}')

    def test_non_hex_offset_digit_is_malformed_not_sha(self):
        # A non-hex digit cannot be a record at all: the record is malformed,
        # never silently dropped and never reported as a digest failure.
        for digit in range(5):
            with self.subTest(digit=digit):
                lines = make_lines()
                broken = bytearray(raw_line(lines, 10))
                position = broken.index(b'offset=') + len(b'offset=') + digit
                broken[position] = nasty(broken[position])
                replace_raw(lines, 10, bytes(broken))
                self.fixture.write_lines(lines)
                self.assert_rejected('malformed or unknown CMDB line')

    def test_corruption_in_data_field(self):
        # Change the first, middle and last of the 128 data hex digits: still
        # 2048 ordered 64-byte chunks, so only SHA may reject them. Index 101
        # also follows an interleaved-noise line, so noise does not hide it.
        for index in (0, 50, 101, 2047):
            for digit in (0, 64, 127):
                with self.subTest(index=index, digit=digit):
                    lines = make_lines(noise=index >= 100)
                    broken = bytearray(raw_line(lines, index))
                    position = broken.index(b'data=') + len(b'data=') + digit
                    broken[position] = flip(broken[position])
                    replace_raw(lines, index, bytes(broken))
                    self.fixture.write_lines(lines)
                    self.assert_rejected('sha256 does not match')

    def test_bad_begin_hash(self):
        self.mutate(self.fixture.begin(), DIGEST.encode(), b'0' * 64)
        self.assert_rejected('BEGIN sha256 does not match')

    def test_bad_end_hash(self):
        self.mutate(self.fixture.end(), DIGEST.encode(), b'0' * 64)
        self.assert_rejected('END sha256 does not match')

    def test_bad_byte_count(self):
        self.mutate(self.fixture.end(), b'bytes=131072', b'bytes=131073')
        self.assert_rejected('END line')

    def test_malformed_raw_prefix(self):
        self.mutate(self.fixture.raw(9), RAW_PREFIX, b'SWEET CMDB RA:')
        self.assert_rejected('malformed')

    def test_unknown_namespace(self):
        self.mutate(self.fixture.raw(9), RAW_PREFIX, b'SWEET CMDB CHUNK:')
        self.assert_rejected('malformed or unknown CMDB line')

    def test_truncated_raw_line(self):
        lines = list(self.fixture.lines)
        i = self.fixture.raw(9)
        lines[i] = lines[i][:-2]
        self.fixture.write_lines(lines)
        self.assert_rejected('malformed or unknown CMDB line')

    def test_extra_raw_before_block(self):
        lines = list(self.fixture.lines)
        lines.insert(self.fixture.begin() - 1, lines[self.fixture.raw()])
        self.fixture.write_lines(lines)
        self.assert_rejected('outside')

    def test_extra_raw_after_block(self):
        lines = list(self.fixture.lines)
        lines.append(b'SWEET CMDB RAW: offset=1ffc0 data=' + b'00' * 64)
        self.fixture.write_lines(lines)
        self.assert_rejected('outside')

    def test_missing_chunk(self):
        self.mutate(self.fixture.raw(100), remove=True)
        self.assert_rejected('RAW lines')

    def test_missing_chunk_with_noise(self):
        self.fixture.write_lines(make_lines(noise=True))
        self.mutate(self.fixture.raw(1000), remove=True)
        self.assert_rejected('RAW lines')


class IdentityRejectionTests(ExtractCase):
    def test_other_kernel_same_digest(self):
        self.fixture.image.write_bytes(make_image(OTHER_BANNER))
        self.assert_rejected('BANNER MISMATCH')

    def test_log_banner_differs(self):
        self.mutate(index_of(self.fixture.lines, b'Booting: '), BANNER, OTHER_BANNER)
        self.assert_rejected('BANNER MISMATCH')

    def test_log_banner_truncated(self):
        # The shortened payload still has a line terminator, but differs
        # from the complete banner embedded in the image.
        self.mutate(index_of(self.fixture.lines, b'Booting: '), BANNER, BANNER[:-8])
        self.assert_rejected('BANNER MISMATCH')

    def test_log_with_two_banners(self):
        lines = list(make_lines())
        lines.insert(3, b'Other: ' + OTHER_BANNER)
        self.fixture.write_lines(lines)
        self.assert_rejected('banner')

    def test_wrong_trial_same_digest(self):
        # Same cmd-db bytes and digest, one complete but different marker.
        self.assert_rejected('found', trial='a1b2c4')
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract('a1b2c4')
        self.assertIn("'sweettrial=a1b2c3'", str(context.exception))

    def test_shorter_expected_trial_is_not_a_prefix_match(self):
        # The log's marker is 'sweettrial=a1b2c3'; expecting 'a1b2' must fail
        # because the complete marker is a different token, not by prefix.
        self.assert_rejected("'sweettrial=a1b2c3'", trial='a1b2')

    def test_longer_expected_trial_embedded_in_marker(self):
        # 'sweettrial=a1b2c3x' in the log is not the complete marker.
        self.fixture.set_boot_args(b'debug=0x8 ' + marker('a1b2c3x') + b' serial=3')
        self.assert_rejected("'sweettrial=a1b2c3x'", trial='a1b2c3')

    def test_expected_trial_is_embedded_prefix_of_marker(self):
        # Expecting 'a1b2c3' while the log carries 'sweettrial=a1b2c3x': the
        # substring is present but not a complete token.
        self.fixture.set_boot_args(marker('a1b2c3x'))
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract('a1b2c3')
        self.assertIn('complete', str(context.exception))
        self.fixture.assert_untouched(self)

    def test_extra_different_trial_option(self):
        # Two different complete trial options in one boot-args line: the
        # expected one is present, but membership is not enough.
        self.fixture.set_boot_args(b'debug=0x8 ' + marker() + b' ' + marker('a1b2c4'))
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract()
        message = str(context.exception)
        self.assertIn('complete', message)
        self.assertIn("'sweettrial=a1b2c4'", message)
        self.fixture.assert_untouched(self)

    def test_extra_trial_option_before_expected(self):
        # Order must not matter: the different option first still rejects.
        self.fixture.set_boot_args(marker('a1b2c4') + b' ' + marker() + b' debug=0x8')
        self.assert_rejected('found')

    def test_repeated_same_trial_option(self):
        # The expected marker twice is not "exactly one" complete marker.
        self.fixture.set_boot_args(b'debug=0x8 ' + marker() + b' ' + marker())
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract()
        self.assertIn('complete', str(context.exception))
        self.fixture.assert_untouched(self)

    def test_different_trial_option_only(self):
        # boot-args carries only a different trial option.
        self.fixture.set_boot_args(b'debug=0x8 ' + marker('a1b2c4'))
        self.assert_rejected('found')
        self.fixture.assert_untouched(self)

    def test_identity_after_noise_boot_args_spaced_trial_last(self):
        # Control for the rejection cases: the spaced form with the trial as
        # the last option, surrounded by interleaved noise, is accepted.
        self.fixture.write_lines(make_lines(noise=True))
        self.fixture.set_boot_args(b'debug=0x8 serial=3 ' + marker())
        self.assertEqual(self.fixture.extract(), DIGEST)

    def test_missing_boot_args(self):
        self.mutate(self.fixture.boot_args(), BOOT_ARGS_PREFIX, b'<Notice>: boot-time = ')
        self.assert_rejected('boot-args')

    def test_duplicate_boot_args_lines(self):
        lines = list(make_lines())
        # Keep exactly one global trial marker so duplicate boot-args lines
        # are the sole identity violation under test.
        lines.append(BOOT_ARGS_LABEL + b'debug=0x8 serial=3')
        self.fixture.write_lines(lines)
        self.assert_rejected('boot-args')

    def test_trial_embedded_in_other_option(self):
        self.mutate(self.fixture.boot_args(), b'sweettrial=' + TRIAL.encode() + b' ',
                    b'debug=' + TRIAL.encode() + b' ')
        self.assert_rejected('sweettrial')

    def test_trial_as_other_sweettrial_value(self):
        # The marker must not be a prefix of another sweettrial= option.
        self.mutate(self.fixture.boot_args(), b'sweettrial=' + TRIAL.encode() + b' ',
                    b'sweettrial=' + TRIAL.encode() + b'0 ')
        self.assert_rejected('sweettrial')

    def test_complete_marker_outside_boot_args(self):
        # A second complete marker elsewhere in the log (after BEGIN) is not
        # allowed even though live logs do echo the trial argument: exactly
        # one complete marker may exist.
        lines = list(make_lines())
        lines.append(b'[4] boot-args echo: ' + marker())
        self.fixture.write_lines(lines)
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract()
        self.assertIn('complete', str(context.exception))
        self.fixture.assert_untouched(self)

    def test_marker_echo_inside_block(self):
        # Same, but the echo sits among the RAW lines: still not allowed, and
        # it is not mistaken for noise just because it is inside the block.
        lines = insert_noise(make_lines(), 2047)
        lines.insert(index_of(lines, END_PREFIX) - 1, b'[7] echo ' + marker() + b' done')
        self.fixture.write_lines(lines)
        self.assert_rejected('complete')

    def test_identity_marker_option_with_coordinator_prefix(self):
        # 'sweettrial-coordinator=0' is a different option name, not a marker.
        self.fixture.set_boot_args(b'debug=0x8 ' + marker() +
                                   b' sweettrial-coordinator=' + TRIAL.encode())
        self.assertEqual(self.fixture.extract(), DIGEST)

    def test_bare_trial_value_is_not_uniqueness_rule(self):
        # A bare trial value elsewhere in the log is not a marker and is fine.
        lines = list(make_lines())
        lines.append(b'[4] trial id ' + TRIAL.encode() + b' under evaluation')
        self.fixture.write_lines(lines)
        self.assertEqual(self.fixture.extract(), DIGEST)

    def test_existing_output_preserved_identity(self):
        self.fixture.out.write_bytes(b'prior output')
        with self.assertRaises(extractor.Rejected):
            self.fixture.extract(trial='zz')
        self.fixture.assert_untouched(self, prior=b'prior output')

    def test_existing_output_preserved_protocol(self):
        self.fixture.out.write_bytes(b'prior output')
        lines = make_lines()
        broken = bytearray(raw_line(lines, 0))
        broken[-1] = flip(broken[-1])
        replace_raw(lines, 0, bytes(broken))
        self.fixture.write_lines(lines)
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract()
        self.assertIn('sha256 does not match', str(context.exception))
        self.fixture.assert_untouched(self, prior=b'prior output')

    def test_existing_output_preserved_verified_input(self):
        # Even a fully valid log never overwrites an existing output.
        self.fixture.out.write_bytes(b'prior output')
        with self.assertRaises(extractor.Rejected) as context:
            self.fixture.extract()
        self.assertIn('refusing to overwrite', str(context.exception))
        self.fixture.assert_untouched(self, prior=b'prior output')

    def test_invalid_trial_argument(self):
        for value in ('', 'a b', 'a=b', 'a\tb'):
            with self.subTest(value=value):
                self.assert_rejected('invalid --trial', trial=value)


class CliTests(ExtractCase):
    def cli(self, *extra, image=None, trial=TRIAL):
        command = [sys.executable, str(TOOLS / 'extract_cmd_db_snapshot.py'),
                   '--image', str(image or self.fixture.image), '--trial', trial,
                   '--log', str(self.fixture.log), '--out', str(self.fixture.out), *extra]
        return subprocess.run(command, capture_output=True, text=True,
                              env=dict(os.environ, PYTHONPATH=str(ROOT / 'tools')))

    def test_writes_once_and_never_overwrites(self):
        first = self.cli()
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)
        self.assertIn(f'sha256={DIGEST}', first.stdout)
        again = self.cli()
        self.assertNotEqual(again.returncode, 0)
        self.assertIn('refusing to overwrite', again.stderr)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_error_is_nonzero_no_output(self):
        self.mutate(self.fixture.end(), DIGEST.encode(), b'1' * 64)
        result = self.cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('REJECTED', result.stderr)
        self.assertFalse(self.fixture.out.exists())

    def test_interleaved_noise_via_cli(self):
        self.fixture.write_lines(make_lines(noise=True))
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_identity_error_reports_banner(self):
        self.fixture.image.write_bytes(make_image(OTHER_BANNER))
        result = self.cli()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('BANNER MISMATCH', result.stderr)
        self.assertFalse(self.fixture.out.exists())

    def test_compact_identity_via_cli(self):
        lines = make_lines()
        lines[self.fixture.boot_args()] = (
            b'<Notice>: boot-args=' + marker() + b' debug=0x8')
        self.fixture.write_lines(lines)
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.fixture.out.read_bytes(), BLOCK)

    def test_wrong_trial_same_digest_via_cli(self):
        result = self.cli(trial='a1b2c4')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('REJECTED', result.stderr)
        self.assertFalse(self.fixture.out.exists())

    def test_missing_arguments(self):
        result = subprocess.run([sys.executable, str(TOOLS / 'extract_cmd_db_snapshot.py')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.fixture.out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
