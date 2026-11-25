#!/usr/bin/env python3
"""Validate the same-phone CPU frequency resources and build the read-only observer."""

import argparse
from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

placement = import_module('check-frame398')
P398 = MAIN/'research/tmp/gauguin-frame398-renderer-performance-core-worktree-20261123/research/tmp/frame-398'
BASE = WORK/'research/tmp/frame-399'
CONTROL = P398/'native-kernel/build-manifest.json'
PATCH = WORK/'graphics/gauguin-program-io/0399-observe-native-cpu-frequency-domains.patch'
FIXTURE = WORK/'tests/fixtures/frame399_cpu_frequency.cpp'
HEADER = Path('bsd/dev/gauguin_cpufreq399.h')
GPU = placement.GPU


def stock_resources():
    node = '/soc/qcom,cpufreq-hw'
    def dt(kind, path, prop):
        return subprocess.check_output(['fdtget','-t',kind,str(placement.FDT),path,prop],
                                       text=True,timeout=15).split()

    properties = subprocess.check_output(['fdtget','-p',str(placement.FDT),node],text=True,timeout=15).splitlines()
    addresses = [int(word,16) for word in dt('x',node,'reg')]
    require(addresses == [0x18323000,0x1000,0x18325800,0x1000] and
            dt('s',node,'compatible') == ['qcom,cpufreq-hw'] and
            dt('s',node,'reg-names') == ['freq-domain0','freq-domain1'] and
            dt('s',node,'clock-names') == ['xo','alternate'] and
            'qcom,no-accumulative-counter' in properties and
            {'qcom,lut-row-size','qcom,lut-max-entries','qcom,skip-enable-check'}.isdisjoint(properties),
            'same-phone standard CPUFreq-HW resources differ')
    return dict(domains=[addresses[:2],addresses[2:]], topology=placement.stock_topology(),
                counter_kind='one counter per frequency domain')


def host():
    resources = stock_resources()
    source = Path(load(CONTROL)['source'])/GPU
    with TemporaryDirectory(prefix='399-clock-host-',dir=BASE) as temporary:
        folder = Path(temporary)
        target = folder/GPU
        target.parent.mkdir(parents=True)
        (folder/HEADER).parent.mkdir(parents=True)
        target.write_bytes(source.read_bytes())
        subprocess.run(['patch','-p1','-F','0','-i',str(PATCH)],cwd=folder,check=True,capture_output=True,timeout=20)
        unit = target.read_text()
        driver = import_module('check-frame397').method
        mapper = driver(unit,'mapDisplayClocks399')
        issue = driver(unit,'GauguinGPUUserClient::submit')
        done = driver(unit,'GauguinGPUUserClient::finishPending')
        require(issue.index('if (ok && fAsync && sweet_frame344_clock())') <
                issue.index('sweet_frame344_record(F344_ISSUE,fence,0') <
                issue.index('if (fCompositor) sampleDisplayClockIssue399(fPendingDisplayTicket, fence);') and
                done.index('sweet_frame344_record(F344_READY,fence,0') <
                done.index('sampleDisplayClockCompletion399(fence);') and
                all(hex(domain[0]) in mapper for domain in resources['domains']) and
                'memory->map(kIOMapReadOnly | kIOMapInhibitCache)' in mapper and
                'mapDisplayClocks399();' in driver(unit,'GauguinGPUStart') and
                'discardDisplayClock399Maps();' in driver(unit,'GauguinGPUStop'),
                'clock observation is absent from the existing capture or read-only lifetime')
        test = folder/'clock-host'
        subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I'+str(folder/HEADER.parent),str(FIXTURE),'-o',str(test)],
            check=True,capture_output=True,timeout=45)
        subprocess.run([str(test)],check=True,timeout=15)
    return dict(state='0399-CPU-frequency-observer-host-verified',ASan_UBSan=True,cases=10,resources=resources,
                device_commands=0,patch_sha256=sha(PATCH),
                input_pins={str(path):sha(path) for path in (CONTROL,source,PATCH,FIXTURE,placement.FDT)})


def native():
    budget = load(BASE/'native-development-admission.json')
    offline = load(BASE/'offline.json')
    require(budget['admitted'] and budget['planned_batch_bytes'] >= 72_000_000 and
            budget['current_accounted_bytes']+budget['planned_batch_bytes'] <= budget['limit_bytes'] and
            offline == host(), '0399 native build exceeds budget or exact source proof differs')
    result = BASE/'native-kernel'
    import_module('build-frame347').link_scanout(CONTROL,result,parent_trial='0398',trial='0399',patches=(PATCH,),
        extra_units=(('GauguinGPU',CONTROL,'compile-GauguinGPU'),),recompile_scanout=False,
        compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    build = load(result/'build-manifest.json')
    require(build['inputs_unchanged'] and build['baseline_reproduced_except_uuid'] and
            {Path(path).stem for path in build['object_replacements'].values()} == {'GauguinGPU'},
            '0399 changed kernel components outside the GPU observer')
    return dict(kernel_sha256=build['kernel_sha256'],identity=build['identity'],device_commands=0)


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('step',choices=('host','native'))
    print(json.dumps(globals()[cli.parse_args().step](),indent=2))
