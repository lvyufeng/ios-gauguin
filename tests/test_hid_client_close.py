#!/usr/bin/env python3
"""Exercise real HID open/close/snapshot dispatch under OOM and concurrency."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))


def main():
    source = (SOURCE / 'iokit/Kernel/arm/hid/SweetHID.cpp').read_text()
    def extract(signature):
        begin = source.index(signature)
        return source[begin:source.index('\n}\n', begin) + 3]
    start = source.index('class IOHIDEventServiceClient :')
    end = source.index('OSDefineMetaClassAndStructors(IOHIDEventServiceClient', start)
    cls = source[start:end]
    methods = '\n'.join(extract(signature) for signature in (
        'bool\nIOHIDEventService::open(', 'void\nIOHIDEventService::close(',
        'bool\nIOHIDEventService::handleOpen(', 'void\nIOHIDEventService::handleClose(',
        'bool\nIOHIDEventService::handleIsOpenLocked(', 'bool\nIOHIDEventService::handleIsOpen(',
        'void\nIOHIDEventService::dispatchEvent('))
    fixture = (HERE / 'fixtures/hid_client_close_host.cpp').read_text()
    fixture = fixture.replace('@RECORD@', cls).replace('@METHODS@', methods)
    with tempfile.TemporaryDirectory(prefix='hid-client-close-') as temporary:
        directory = Path(temporary)
        (directory / 'test.cpp').write_text(fixture)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-pedantic', '-Wno-extra-semi', '-fsanitize=address,undefined',
                        '-pthread', '-O1', '-g', str(directory / 'test.cpp'), '-o', str(directory / 'test')], check=True)
        subprocess.run([str(directory / 'test')], check=True, timeout=30)


if __name__ == '__main__':
    main()
