#!/usr/bin/env python3
"""Qualify the next stock CPU interaction point with the intact old lease."""

from difflib import unified_diff
from importlib import import_module
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from frame366_scope import load,require,sha

wire = import_module('check-frame407-log')
prior = import_module('prepare-frame405')
BASE,CONTROL = wire.BASE,wire.hint.CONTROL
PATCH = BASE/'407-stock-1766400-interaction.patch'
HEADER = Path('bsd/dev/gauguin_cpufreq402.h')
TARGET_KHZ = 1_766_400
sys.path.append(str(prior.prior.P403_TOOLS))
stock = import_module('check-frame402')


def host():
    policy = stock.stock()
    require(policy['stock_khz'][7]==TARGET_KHZ and policy['performance_cpus']==[6,7] and
            policy['thermal_limit_millic']==65_000 and policy['finite_input_lease_ms']==35,
            'same-phone Android operating point or guard differs')
    source = Path(load(CONTROL)['source'])
    original = (source/HEADER).read_text()
    revised = wire.hint.replace(original,
        'CPU402_TARGET_L = 73, /* 1,401,600 kHz at the stock 19.2 MHz XO. */',
        'CPU402_TARGET_L = 92, /* 1,766,400 kHz at the stock 19.2 MHz XO. */')
    PATCH.write_text(''.join(unified_diff(original.splitlines(keepends=True),revised.splitlines(keepends=True),
        'a/'+str(HEADER),'b/'+str(HEADER))))
    fixture = prior.prior.P403_TOOLS.parent/'tests/fixtures/frame402_cpu_point.c'
    replay = fixture.read_text().replace('point.selected == 5','point.selected == 7')
    replay = replay.replace('CPU402_FREQ_LUT, 5,','CPU402_FREQ_LUT, 7,').replace('0x40010049','0x4001005c')
    replay = replay.replace('CPU402_VOLT_LUT, 5,','CPU402_VOLT_LUT, 7,')
    with TemporaryDirectory(prefix='407-cpu-',dir=BASE) as folder:
        folder = Path(folder)
        (folder/HEADER.name).write_text(revised)
        (folder/fixture.name).write_text(replay)
        binary = str(folder/'test')
        subprocess.run(['xcrun','clang','-std=c11','-Wall','-Wextra','-Werror','-DFRAME403_THERMAL_RETRY=1',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(folder),str(folder/fixture.name),
            '-o',binary],check=True,timeout=45)
        subprocess.run([binary],check=True,timeout=15,capture_output=True)
    return dict(state='0407-stock-CPU-point-host-verified',device_commands=0,ASan_UBSan=True,
        target_khz=TARGET_KHZ,target_table_index=7,policy=policy,patch_sha256=sha(PATCH),
        input_pins={str(p):sha(p) for p in (CONTROL,source/HEADER,fixture,PATCH,stock.ANDROID,stock.observe.placement.FDT)})


if __name__=='__main__':
    print(json.dumps(host(),indent=2))
