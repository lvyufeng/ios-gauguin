#!/usr/bin/env python3
"""Strict codec/identity contracts and the actual worst-case C++ formatter."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest

WORK=Path(__file__).resolve().parents[1];BASE=WORK/'research/tmp/io-path-342'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    folder=out.with_suffix('');assert not folder.exists();folder.mkdir()
    sys.path[:0]=[str(WORK/'tests'),str(WORK/'tools')]
    import core342_log as codec
    source=Path(json.loads((BASE/'prepared-v3/result.json').read_text())['sources']['candidate'])
    paths=[Path(__file__),WORK/'tests/fixtures/format342.cpp',WORK/'tests/test_core342_log.py',
        WORK/'tests/test_core341_log.py',WORK/'tests/test_core340_log.py',WORK/'tests/test_core_prof339_log.py',
        BASE/'core-host-v2/program342-success.log']
    paths.extend(WORK/'tools'/name for name in ('phase342_log.py','kernel342_log.py','core342_log.py','core341_log.py','core340_log.py','core339_log.py','core338_log.py'))
    paths.extend(source/'src'/name for name in ('Recording342.hpp','Recording338.hpp','Profiling342.hpp','Reuse342.hpp','Allocation342.hpp','Phase342.hpp'))
    pins={str(p):sha(p) for p in paths}
    argv=['clang++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
        '-DHAKIOS_METAL_TARGET_A619','-I'+str(source/'include'),'-I'+str(source/'src'),str(WORK/'tests/fixtures/format342.cpp'),'-o',str(folder/'formatter')]
    p=subprocess.run(argv,capture_output=True,timeout=90);(folder/'compile.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0,p.stderr
    p=subprocess.run([str(folder/'formatter')],capture_output=True,timeout=30);(folder/'worst-row.log').write_bytes(p.stderr)
    lines=p.stderr.decode().splitlines();assert p.returncode==0 and len(lines)==1 and codec.parse_extra(lines[0]) is not None
    assert len(lines[0].encode())+1<=8192
    suite=unittest.defaultTestLoader.discover(str(WORK/'tests'),pattern='test_core342_log.py')
    log=io.StringIO();tests=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert tests.wasSuccessful() and tests.testsRun>=8,log.getvalue()
    assert all(sha(p)==h for p,h in pins.items())
    result=dict(state='0342-strict-user-kernel-CPU-identity-codec-contracts-passed',tests=tests.testsRun,
        real_production_core_rows_format_checked=1,worst_case_all_integer_widths_formatter_bytes=len(lines[0].encode())+1,
        real_FakeGpu_row_is_format_only=True,prior_wires_refused=True,
        loss_overflow_pending_duplicates_gaps_and_identity_mismatch_refused=True,
        input_pins=pins,test_log=log.getvalue(),device_commands=0,device_writes=0,boot_attempts=0)
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','test_log')},indent=2))


if __name__=='__main__':main()
