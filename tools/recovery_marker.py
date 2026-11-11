"""Write the fixed misc recovery marker using a separately approved preimage."""

import hashlib


MARKER = b"boot-recovery"
READ = "dd if=/dev/block/by-name/misc bs=4096 count=1 2>/dev/null"
WRITE = "dd of=/dev/block/by-name/misc bs=1 seek=0 conv=notrunc 2>/dev/null"


class RecoveryMarkerError(RuntimeError):
    def __init__(self, message, rollback_verified=None):
        super().__init__(message)
        self.rollback_verified = rollback_verified


def set_recovery_marker(io, approval, backup):
    if (approval.get("misc_recovery_marker_approved") is not True
            or approval.get("allow_rollback") is not True):
        raise RecoveryMarkerError("separate misc-marker approval required")
    if len(backup) != 4096 or approval.get("misc_backup_sha256") != hashlib.sha256(backup).hexdigest():
        raise RecoveryMarkerError("misc backup differs from the approved preimage")

    def read():
        result = io.run(io.adb + ["exec-out", READ]).stdout
        if len(result) != len(backup):
            raise RecoveryMarkerError("short misc read")
        return result

    def write(value):
        io.run(io.adb + ["exec-in", WRITE], data=value)

    if read() != backup:
        raise RecoveryMarkerError("misc changed since its approved backup")
    expected = MARKER + backup[len(MARKER):]
    try:
        write(MARKER)
        if read() != expected:
            raise RecoveryMarkerError("misc marker readback differs")
    except (Exception, KeyboardInterrupt) as error:
        restored = False
        try:
            write(backup[:len(MARKER)])
            restored = read() == backup
        except (Exception, KeyboardInterrupt):
            pass
        raise RecoveryMarkerError("misc marker failed; rollback " +
                                  ("verified" if restored else "unverified"), restored) from error
    return {"state": "misc-marker-readback-verified", "bytes": len(MARKER),
            "before_sha256": hashlib.sha256(backup).hexdigest(),
            "after_sha256": hashlib.sha256(expected).hexdigest()}
