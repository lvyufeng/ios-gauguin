#!/usr/bin/env python3
"""Test real candidate methods with host stand-ins for IOKit allocation/gate."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))


def main():
    source_path = SOURCE / 'iokit/Kernel/arm/hid/SweetHID.cpp'
    source = source_path.read_text()
    start = source.index('#define SWEET_TOUCH_FINGERS')
    end = source.index('\nOSDefineMetaClassAndStructors(SweetHIDTouch', start)
    cls = source[start:end]
    publish_start = source.index('static IOLock *gSweetTouchLock;')
    publish_end = source.index('bool\nSweetHIDButtons::start(', publish_start)
    publication = source[publish_start:publish_end]
    start = source.index('bool\nSweetHIDTouch::start(')
    end = source.index('\nvoid\nSweetHIDTouch::stop(', start)
    setup = source[start:end]
    start = end + 1
    end = source.index('\n/* key: 0 power', start)
    methods = source[start:end]
    capi = source[source.index('extern "C" void\nsweet_hid_touch('):]
    harness = (HERE / 'fixtures/test_hid_frame.cpp').read_text()
    for marker, text in (('@CLASS@', cls), ('@PUBLICATION@', publication), ('@START@', setup), ('@METHODS@', methods), ('@CAPI@', capi)):
        assert harness.count(marker) == 1
        harness = harness.replace(marker, text)
    with tempfile.TemporaryDirectory(prefix='gauguin-hid-frame-') as directory:
        path = Path(directory)
        (path / 'test.cpp').write_text(harness)
        trace_flags=(['-DGAUGUIN=1','-DTEST_UI_TRACE=1','-I'+str(SOURCE/'bsd/dev')]
                     if 'sweet_ui_trace_record' in source else [])
        subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-Wall', '-Wextra',
                        '-Werror', '-Wno-extra-semi', '-pedantic', '-fsanitize=address,undefined',
                        '-g', '-O1', '-pthread', *trace_flags, '-I', str(SOURCE / 'iokit'), str(path / 'test.cpp'),
                        '-o', str(path / 'test')], check=True)
        subprocess.run([str(path / 'test')], check=True)


if __name__ == '__main__':
    main()
