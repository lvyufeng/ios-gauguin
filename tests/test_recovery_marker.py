"""Exercise the fixed misc write scope and restoration after partial failures."""

import hashlib
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from recovery_marker import MARKER, READ, WRITE, RecoveryMarkerError, set_recovery_marker


class FakeRecovery:
    adb = ["adb", "-s", "fixture"]

    def __init__(self, data, failure=None):
        self.data = data
        self.failure = failure
        self.calls = []
        self.writes = 0

    def run(self, args, data=None):
        self.calls.append((args, data))
        if args == self.adb + ["exec-out", READ]:
            if self.writes == 1 and self.failure == "readback":
                return SimpleNamespace(stdout=self.data[:-1] + bytes([self.data[-1] ^ 1]))
            return SimpleNamespace(stdout=self.data)
        if args != self.adb + ["exec-in", WRITE] or len(data) != len(MARKER):
            raise AssertionError("operation escaped the fixed 13-byte scope")
        self.writes += 1
        if self.writes == 2 and self.failure == "rollback":
            raise OSError("restore failed")
        if self.writes == 1 and self.failure in ("partial", "rollback", "interrupt"):
            self.data = data[:4] + self.data[4:]
            if self.failure == "interrupt":
                raise KeyboardInterrupt()
            raise OSError("partial write")
        self.data = data + self.data[len(MARKER):]
        return SimpleNamespace(stdout=b"")


class RecoveryMarker(unittest.TestCase):
    def setUp(self):
        self.backup = bytes(i % 251 for i in range(4096))
        self.approval = {"misc_recovery_marker_approved": True, "allow_rollback": True,
                         "misc_backup_sha256": hashlib.sha256(self.backup).hexdigest()}

    def test_separate_approval_and_exact_backup_precede_device_access(self):
        cases = [{}, {"approved": True, "allow_rollback": True},
                 dict(self.approval, misc_recovery_marker_approved=False),
                 dict(self.approval, allow_rollback=False),
                 dict(self.approval, misc_backup_sha256="0" * 64)]
        for approval in cases:
            with self.subTest(approval=approval):
                io = FakeRecovery(self.backup)
                with self.assertRaises(RecoveryMarkerError):
                    set_recovery_marker(io, approval, self.backup)
                self.assertEqual(io.calls, [])

    def test_changed_device_preimage_stops_before_write(self):
        io = FakeRecovery(bytes(4096))
        with self.assertRaises(RecoveryMarkerError):
            set_recovery_marker(io, self.approval, self.backup)
        self.assertEqual(io.writes, 0)

    def test_success_changes_only_the_marker(self):
        io = FakeRecovery(self.backup)
        result = set_recovery_marker(io, self.approval, self.backup)
        self.assertEqual(result["state"], "misc-marker-readback-verified")
        self.assertEqual(io.writes, 1)
        self.assertEqual(io.data, MARKER + self.backup[len(MARKER):])

    def test_failed_write_readback_or_interrupt_restores_preimage(self):
        for failure in ("partial", "readback", "interrupt"):
            with self.subTest(failure=failure):
                io = FakeRecovery(self.backup, failure)
                with self.assertRaises(RecoveryMarkerError) as raised:
                    set_recovery_marker(io, self.approval, self.backup)
                self.assertIs(raised.exception.rollback_verified, True)
                self.assertEqual(io.writes, 2)
                self.assertEqual(io.data, self.backup)

    def test_failed_restoration_is_reported_unverified(self):
        io = FakeRecovery(self.backup, "rollback")
        with self.assertRaises(RecoveryMarkerError) as raised:
            set_recovery_marker(io, self.approval, self.backup)
        self.assertIs(raised.exception.rollback_verified, False)
        self.assertNotEqual(io.data, self.backup)


if __name__ == "__main__":
    unittest.main()
