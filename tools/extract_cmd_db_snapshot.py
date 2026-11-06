#!/usr/bin/env python3
"""Extract one verified 128KiB cmd-db RAW block from a bound kernel log.

Protocol (fixed, must match the future worker's printf lines):
  SWEET CMDB BEGIN: bytes=131072 sha256=<64 lower hex>
  SWEET CMDB RAW: offset=<5 lower hex> data=<128 lower hex>   (exactly 2048)
  SWEET CMDB END: bytes=131072 sha256=<same as BEGIN>
offsets 00000,00040,...,1ffc0; concatenated data must be exactly 131072 bytes
whose SHA-256 equals both header hashes.

Identity contract: the supplied --image (boot image) and --log must carry one
complete distinct kernel banner. The log must contain exactly one actual
boot-args line; "boot-args" may be followed by optional spaces, '=', and
optional spaces, and the complete rest of that line is split on whitespace.
That option list must be exactly [sweettrial=<value>]: the exact token must be
present at least once and every sweettrial= option in it must equal the
expected complete marker (an extra or different trial option is rejected).
Independently, the log as a whole must contain exactly one complete
sweettrial=<value> token: a marker starts at a sweettrial= that is not
immediately preceded by an identifier byte (so 'boot-args=sweettrial=x' is
allowed) and runs to the next whitespace/end of line or NUL (so
'sweettrial=<value>x' is not a complete marker). A different kernel or trial
is rejected even when the cmd-db bytes are identical. The identity is a normal
log line outside the CMDB block.

Unrelated (non-"SWEET CMDB") kernel log lines interleaved between BEGIN and
END, e.g. from concurrent printf on other CPUs, are accepted; only RAW lines
are collected, and they must be strictly ordered, unique, 64-byte chunks at
offsets 00000,00040,...,1ffc0 forming the complete 131072 bytes. Any other
"SWEET CMDB" line that is not a valid BEGIN/END/RAW record, and any RAW line
outside the BEGIN/END block, is rejected.

This validates the identity/completeness of the SUPPLIED log only. The caller
must still perform a fresh pull from the device for that unique trial. This
tool cannot prove wall-clock freshness and cannot detect an entirely copied
log that matches; the SHA alone does not prove freshness.

The output file is created exclusively (never overwritten); on any rejection
no output is created and an existing file is left intact. This module is meant
to live beside tools/kernel_banner.py: run it with that directory on PYTHONPATH.
"""
import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

from kernel_banner import compare as compare_banner

BLOCK_BYTES = 131072
CHUNK_BYTES = 64
CHUNKS = BLOCK_BYTES // CHUNK_BYTES
_HEX64 = rb'[0-9a-f]{64}'
BEGIN = re.compile(rb'SWEET CMDB BEGIN: bytes=131072 sha256=(' + _HEX64 + rb')\r?')
END = re.compile(rb'SWEET CMDB END: bytes=131072 sha256=(' + _HEX64 + rb')\r?')
RAW = re.compile(rb'SWEET CMDB RAW: offset=([0-9a-f]{5}) data=([0-9a-f]{128})\r?')
NAMESPACE = b'SWEET CMDB'
# One actual boot-args line; capture its complete remainder on that line.
BOOT_ARGS = re.compile(
    rb'(?<![A-Za-z0-9_-])boot-args[ \t]*=[ \t]*([^\r\n\x00]*)')
_TRIAL_FIELD = re.compile(rb'[^ \t\r\n\x00]+')
# A complete sweettrial=<non-whitespace> token: no identifier byte directly
# before 'sweettrial' (an '=' or whitespace is fine), token runs to whitespace.
_TRIAL_TOKEN = re.compile(
    rb'(?<![A-Za-z0-9_-])sweettrial=([^ \t\r\n\x00]+)')


class Rejected(Exception):
    """Validation failed; nothing was written."""


def _valid_trial(value):
    return bool(value) and not any(c in value for c in ' \t\r\n\x00=\\') and all(
        0x21 <= ord(c) <= 0x7e for c in value)


def _lines(data):
    return data.split(b'\n')


def _marker(trial_value):
    return b'sweettrial=' + trial_value


def _complete_markers(data):
    """Every complete sweettrial=<value> token anywhere in the log."""
    return [b'sweettrial=' + value for value in _TRIAL_TOKEN.findall(data)]


def _check_identity(data, begin_at, end_at, trial):
    """One actual boot-args line outside the block, one complete marker."""
    markers = _complete_markers(data)
    if markers != [_marker(trial.encode('ascii'))]:
        shown = [marker.decode('ascii', 'replace') for marker in markers]
        raise Rejected(f'the log must contain exactly one complete sweettrial='
                       f'{trial} token and no other sweettrial= token '
                       f'(found {shown})')
    matches = list(BOOT_ARGS.finditer(data))
    if len(matches) != 1:
        raise Rejected(f'expected exactly one boot-args line, found {len(matches)}')
    match = matches[0]
    line_at = data.count(b'\n', 0, match.start())
    if begin_at <= line_at <= end_at:
        raise Rejected('boot-args line lies inside the CMDB block')
    found = [option for option in _TRIAL_FIELD.findall(match.group(1))
             if option.startswith(b'sweettrial=')]
    if found != [_marker(trial.encode('ascii'))]:
        shown = [option.decode('ascii', 'replace') for option in found]
        raise Rejected(f'boot-args must contain exactly the one sweettrial={trial} '
                       f'option (found {shown})')


def _parse_block(data, trial):
    lines = _lines(data)
    begins = [(i, m) for i, line in enumerate(lines) for m in [BEGIN.fullmatch(line)] if m]
    ends = [(i, m) for i, line in enumerate(lines) for m in [END.fullmatch(line)] if m]
    if len(begins) != 1:
        raise Rejected(f'expected exactly one BEGIN line, found {len(begins)}')
    if len(ends) != 1:
        raise Rejected(f'expected exactly one END line, found {len(ends)}')
    begin_at, begin = begins[0]
    end_at, end = ends[0]
    if end_at < begin_at:
        raise Rejected('END precedes BEGIN')

    raws = []
    for i, line in enumerate(lines):
        if BEGIN.fullmatch(line) or END.fullmatch(line):
            continue
        match = RAW.fullmatch(line)
        if match:
            if not begin_at < i < end_at:
                raise Rejected(f'extra RAW line outside the BEGIN/END block, line {i + 1}')
            raws.append(match)
        elif NAMESPACE in line:
            raise Rejected(f'malformed or unknown CMDB line {i + 1}')

    if len(raws) != CHUNKS:
        raise Rejected(f'expected {CHUNKS} RAW lines, found {len(raws)}')
    block = bytearray()
    for index, match in enumerate(raws):
        offset = int(match.group(1), 16)
        expected = index * CHUNK_BYTES
        if offset != expected:
            raise Rejected(f'RAW chunk {index} has offset {offset:05x}, '
                           f'expected {expected:05x} (duplicate, out-of-order '
                           f'or corrupt offset)')
        block += bytes.fromhex(match.group(2).decode('ascii'))
    if len(block) != BLOCK_BYTES:
        raise Rejected(f'decoded {len(block)} bytes, expected {BLOCK_BYTES}')
    digest = hashlib.sha256(block).hexdigest()
    if begin.group(1).decode('ascii') != digest:
        raise Rejected('BEGIN sha256 does not match the decoded bytes')
    if end.group(1).decode('ascii') != digest:
        raise Rejected('END sha256 does not match the decoded bytes')
    _check_identity(data, begin_at, end_at, trial)
    return bytes(block), digest


def extract(image, log, trial, out):
    """Validate, then create out exclusively. Returns the block sha256 hex."""
    if not _valid_trial(trial):
        raise Rejected(f'invalid --trial {trial!r}: one non-empty printable token')
    try:
        compare_banner(Path(image), Path(log))
    except (OSError, ValueError) as error:
        raise Rejected(f'identity: {error}') from None
    try:
        data = Path(log).read_bytes()
    except OSError as error:
        raise Rejected(f'cannot read log: {error}') from None
    block, digest = _parse_block(data, trial)
    try:
        handle = open(out, 'xb')  # exclusive create: never overwrite
    except FileExistsError:
        raise Rejected(f'output exists, refusing to overwrite: {out}') from None
    except OSError as error:
        raise Rejected(f'cannot create output: {error}') from None
    try:
        with handle:
            handle.write(block)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as error:
        try:
            os.unlink(out)  # only the file this call just created
        except OSError:
            pass
        raise Rejected(f'write failed: {error}') from None
    return digest


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--image', type=Path, required=True,
                        help='boot image the log banner must match')
    parser.add_argument('--trial', required=True,
                        help='sweettrial value without the sweettrial= prefix')
    parser.add_argument('--log', type=Path, required=True,
                        help='pulled kernel log carrying the RAW block')
    parser.add_argument('--out', type=Path, required=True,
                        help='new binary file to create')
    args = parser.parse_args(argv)
    try:
        digest = extract(args.image, args.log, args.trial, args.out)
    except Rejected as error:
        print(f'REJECTED: {error}', file=sys.stderr)
        return 2
    print(f'OK: wrote {BLOCK_BYTES} bytes to {args.out} sha256={digest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
