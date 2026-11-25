#!/usr/bin/env python3
"""Run bounded CR341 codec contracts without constructing device IO."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys
import unittest

WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/program-io-341'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    out=args.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    sys.path[:0]=[str(WORK/'tests'),str(WORK/'tools')]
    suite=unittest.defaultTestLoader.discover(str(WORK/'tests'),pattern='test_core341_log.py')
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    assert result.wasSuccessful() and result.testsRun==9,log.getvalue()
    paths=[Path(__file__),WORK/'tests/test_core341_log.py',WORK/'tests/test_core_prof339_log.py',WORK/'tests/test_core340_log.py',WORK/'tools/core340_log.py',
        WORK/'tools/core341_log.py',WORK/'tools/core339_log.py',WORK/'tools/core338_log.py',
        BASE/'core-host-v3/program341-success.log']
    out.parent.mkdir(parents=True,exist_ok=True)
    value=dict(state='0341-strict-program-slab-and-IO-CPU-codec-contracts-passed',tests=9,
        contract_mutations=25+12+5+29+21+12+1,real_production_core_rows_format_checked=1,
        actual_FakeGpu_row_is_format_only_and_requires_actual_IO_for_device_gate=True,
        prior_0339_wire_refused=True,device_commands=0,device_writes=0,boot_attempts=0,
        input_pins={str(p):sha(p) for p in paths},test_log=log.getvalue())
    with out.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in value.items() if k not in ('input_pins','test_log')},indent=2))


if __name__=='__main__':main()
