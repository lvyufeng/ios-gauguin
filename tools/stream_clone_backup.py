"""Read every incoming byte; update a distinct local clone and hash the stream.

No device, process, path, permission or image-format operations live here.
The caller must verify the source clone, stream exit status and final file hash.
"""
import hashlib

def copy_verified_stream(stream, target, expected_bytes, chunk_bytes=1048576):
    if type(expected_bytes) is not int or expected_bytes <= 0 or type(chunk_bytes) is not int or chunk_bytes <= 0:
        raise ValueError('positive integer geometry required')
    if target.seek(0, 2) != expected_bytes:
        raise ValueError('clone length differs')
    digest = hashlib.sha256();changed = 0;offset = 0
    while offset < expected_bytes:
        length = min(chunk_bytes, expected_bytes-offset)
        data = stream.read(length)
        if len(data) != length:
            raise ValueError('short fresh backup stream')
        target.seek(offset);old = target.read(length)
        if len(old) != length:
            raise ValueError('short clone read')
        digest.update(data)
        if old != data:
            target.seek(offset)
            if target.write(data) != length:
                raise ValueError('short clone write')
            changed += 1
        offset += length
    if stream.read(1) != b'':
        raise ValueError('extra fresh backup bytes')
    target.flush()
    return dict(fresh_bytes=offset,sha256=digest.hexdigest(),changed_chunks=changed,chunk_bytes=chunk_bytes)
