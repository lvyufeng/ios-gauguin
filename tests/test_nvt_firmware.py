#!/usr/bin/env python3
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'fixtures'))
sys.path.insert(0, str(HERE.parent / 'bootstrap'))
import nvt_test_support as support

parser = argparse.ArgumentParser(description='Firmware parser format controls, synthetic by default')
support.add_arguments(parser)
args = parser.parse_args()
root = support.module_root(args, HERE)
with tempfile.TemporaryDirectory(prefix='nvt-firmware-test-') as directory:
    scratch = Path(directory)
    image, digest, label = support.input_image(args.firmware, scratch)
    print(label, flush=True)
    out = scratch / 'test'
    subprocess.run(['clang', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
        '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
        '-I' + str(root / 'firmware'), str(root / 'firmware/nvt_firmware.c'),
        str(support.fixture(HERE, 'test_nvt_firmware.c')), '-o', str(out)], check=True)
    subprocess.run([str(out), str(image)], check=True)
    support.unchanged(image, digest)
