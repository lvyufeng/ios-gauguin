#!/usr/bin/env python3
"""Exercise real factory/appendChild code using host allocation fault injection."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))


def main():
    source = (SOURCE / 'iokit/Kernel/arm/hid/IOHIDEvent.cpp').read_text()
    def extract(signature):
        start = source.index(signature)
        return source[start:source.index('\n}\n', start) + 3]
    fixture = (HERE / 'fixtures/test_event_factory.cpp').read_text()
    fixture = fixture.replace('@FACTORY@', extract('IOHIDEvent * IOHIDEvent::digitizerEvent('))
    fixture = fixture.replace('@APPEND@', extract('void IOHIDEvent::appendChild('))
    with tempfile.TemporaryDirectory(prefix='hid-event-factory-') as temporary:
        directory = Path(temporary)
        (directory / 'test.cpp').write_text(fixture)
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra', '-Werror',
                        '-pedantic', '-fsanitize=address,undefined', '-O1', '-g',
                        str(directory / 'test.cpp'), '-o', str(directory / 'test')], check=True)
        subprocess.run([str(directory / 'test')], check=True)


if __name__ == '__main__':
    main()
