#!/usr/bin/env python3
"""Conservative lossless console framing; event validation remains mandatory."""
from pathlib import Path
import hashlib
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from console_framing import FramingError, recover_records

PREFIX = (b'IOK backboardd: IOServiceFirstMatch <dict ID="0"><key>IOProviderClass</key>'
          b'<string ID="1">IOHIDDevice</string><key>IOServiceNot')
EVENT = b'SWEET WDT LEASE: one arm requested by bus coordinator; no automatic re-arm or PET'


class ConsoleFramingTests(unittest.TestCase):
    def test_plain_records_unchanged(self):
        self.assertEqual(recover_records(b'a\r\n' + EVENT + b'\n'),
                         (['a', EVENT.decode(), ''], []))

    def test_recovery_keeps_source_substring_hashes(self):
        raw = b'before\n' + PREFIX + EVENT + b'\nafter\n'
        frozen = bytes(raw)
        lines, records = recover_records(raw)
        self.assertEqual(lines, ['before', PREFIX.decode(), EVENT.decode(), 'after', ''])
        self.assertEqual(records, [{
            'raw_line': 2, 'ascii_event_column': len(PREFIX) + 1,
            'prefix_sha256': hashlib.sha256(PREFIX).hexdigest(),
            'event_sha256': hashlib.sha256(EVENT).hexdigest(),
        }])
        self.assertEqual(raw, frozen)

    def test_failure_and_malformed_event_contents_are_visible_not_repaired(self):
        for event in [b'SWEET WDT PET: unexpected', b'SWEET GPU CP: partial phase=7 rc=8',
                      b'SWEET GMU BOARD: stopped rc=12', b'SWEET GPU CP: malformed']:
            with self.subTest(event=event):
                lines, records = recover_records(PREFIX + event + b'\n')
                self.assertEqual(lines[1], event.decode())
                self.assertEqual(len(records), 1)

    def test_arbitrary_prefix_does_not_supply_a_record(self):
        raw = b'arbitrary ' + EVENT + b'\n'
        self.assertEqual(recover_records(raw), ([raw[:-1].decode(), ''], []))

    def test_invalid_or_ambiguous_iokit_prefixes_rejected(self):
        for prefix in [
            b'IOK fake: other <dict><key>IOServiceNot',
            b'IOK fake: IOServiceFirstMatch <dict><string>value',
            b'IOK fake: IOServiceFirstMatch <dict><key>&incomplete',
            b'IOK fake: IOServiceFirstMatch <dict></dict><key>IOServiceNot',
            b'IOK fake: IOServiceFirstMatch <dict><key attr="unterminated',
            b'IOK fake: IOServiceFirstMatch <dict><key>x\r',
            b'IOK fake: IOServiceFirstMatch <dict><key>' + b'x' * 16384,
        ]:
            with self.subTest(prefix=prefix[:80]), self.assertRaises(FramingError):
                recover_records(prefix + EVENT + b'\n')
        with self.assertRaises(FramingError):
            recover_records(PREFIX + EVENT + b'SWEET GPU CP: partial\n')
        with self.assertRaises(FramingError):
            recover_records(PREFIX + EVENT)

    def test_duplicate_event_is_not_deduplicated(self):
        lines, records = recover_records(PREFIX + EVENT + b'\n' + EVENT + b'\n')
        self.assertEqual(lines.count(EVENT.decode()), 2)
        self.assertEqual(len(records), 1)


if __name__ == '__main__':
    unittest.main()
