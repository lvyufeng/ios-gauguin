#!/usr/bin/env python3
"""Run failure-boundary tests against the linked Adreno read-only mapping body."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, load, require, sha

candidate = import_module('check-gauguin-shared-scanout')


def check():
    manifest = load(candidate.KERNEL)
    root = Path(manifest['source'])
    source = root/candidate.GPU
    version = source.read_text()
    require(manifest['state']=='0414-native-ARM64-linked' and candidate.HELPER in version,
            'compiled GPU aperture body differs')
    control = Path(load(candidate.INPUT)['source'])/candidate.GPU
    section = 'static bool importedPhysicalPage('
    end = 'IOReturn GauguinGPUUserClient::add('
    before = control.read_text()
    require(before[before.index(section):before.index(end)]==version[version.index(section):version.index(end)],
            'generic GPU surface import differs')
    fixture = WORK/'tests/fixtures/gauguin_shared_scanout_gpu_host.cpp'
    sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    with TemporaryDirectory(prefix='shared-scanout-',dir=candidate.BASE) as temp:
        scratch = Path(temp)
        (scratch/'gauguin_gpu_probe414.inc').write_text(candidate.HELPER)
        executable = scratch/'probe'
        subprocess.run([str(candidate.COMPILER/'clang++'),'-isysroot',sdk,'-std=c++20','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(scratch),'-I'+str(root/'bsd/dev'),
            str(fixture),'-o',str(executable)],check=True,timeout=60)
        for failure in range(8):
            subprocess.run([str(executable),str(failure)],check=True,timeout=10)
    return dict(state='read-only-shared-scanout-aperture-offline-verified',cases=8,device_commands=0,
        input_pins={str(path):sha(path) for path in (candidate.KERNEL,control,source,fixture)})


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
