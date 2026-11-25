"""Allow only an Apple code-signature reservation difference in a rebuilt core.

This check does not establish signature validity. The caller must also run
codesign --verify --strict on both binaries and require byte-identical results
after the same remove/re-sign operation on disposable local copies.
"""
import struct


def signature_reservation(data):
    if len(data) < 32 or struct.unpack_from('<I', data)[0] != 0xfeedfacf:
        raise ValueError('expected a thin 64-bit Mach-O')
    count, size = struct.unpack_from('<II', data, 16)
    end = 32 + size
    if end > len(data):
        raise ValueError('truncated load commands')
    at = 32
    linkedit = signature = None
    for _ in range(count):
        if at + 8 > end:
            raise ValueError('truncated command header')
        command, length = struct.unpack_from('<II', data, at)
        if length < 8 or length % 8 or at + length > end:
            raise ValueError('invalid command length')
        if command == 0x19 and data[at + 8:at + 24].rstrip(b'\0') == b'__LINKEDIT':
            if linkedit is not None or length != 72:
                raise ValueError('unexpected LINKEDIT layout')
            vm_size, file_offset, file_size = struct.unpack_from('<QQQ', data, at + 32)
            linkedit = (at, vm_size, file_offset, file_size)
        if command == 0x1d:
            if signature is not None or length != 16:
                raise ValueError('unexpected signature command')
            signature = (at, *struct.unpack_from('<II', data, at + 8))
        at += length
    if at != end or linkedit is None or signature is None:
        raise ValueError('missing or inconsistent signature layout')
    segment_at, vm_size, file_offset, file_size = linkedit
    signature_at, offset, reserved = signature
    if not end <= file_offset <= offset or offset + reserved != len(data):
        raise ValueError('signature is not the final file region')
    if file_size != len(data) - file_offset or vm_size != (file_size + 16383) & ~16383:
        raise ValueError('unexpected LINKEDIT extent')
    if reserved < 12:
        raise ValueError('missing signature superblob')
    magic, payload, blobs = struct.unpack_from('>III', data, offset)
    if magic != 0xfade0cc0 or not 12 + 8 * blobs <= payload <= reserved:
        raise ValueError('invalid signature superblob')
    if any(data[offset + payload:]):
        raise ValueError('nonzero signature reservation padding')
    # Every byte outside these three allocation fields and the verified
    # signature must match, including UUID, instructions, data and symbols.
    prefix = bytearray(data[:offset])
    fields = [(segment_at + 32, 8), (segment_at + 48, 8), (signature_at + 12, 4)]
    for start, length in fields:
        prefix[start:start + length] = bytes(length)
    return bytes(prefix), dict(signature_offset=offset, reserved_bytes=reserved,
                              payload_bytes=payload, linkedit_file_bytes=file_size,
                              linkedit_vm_bytes=vm_size, allocation_fields=fields)


def compare_signature_reservations(original, rebuilt):
    original_bytes, original_layout = signature_reservation(original)
    rebuilt_bytes, rebuilt_layout = signature_reservation(rebuilt)
    if original_bytes != rebuilt_bytes:
        raise ValueError('rebuilt core differs outside signature allocation')
    return dict(original=original_layout, rebuilt=rebuilt_layout,
                all_other_presignature_bytes_identical=True)
