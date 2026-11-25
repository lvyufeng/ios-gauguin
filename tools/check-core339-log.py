#!/usr/bin/env python3
"""Record strict codec regressions and actual production formatter compatibility."""
import argparse
import importlib.util
import io
import json
from pathlib import Path
import unittest
from core339_scope import BASE,WORK,PRIOR,PARENT,sha
import core339_log as CORE


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    test=WORK/'tests/test_core_prof339_log.py'
    spec=importlib.util.spec_from_file_location('codec339_tests',test);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    stream=io.StringIO();r=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
    assert r.wasSuccessful(),stream.getvalue()
    log=BASE/'core-host-v3/prof339-success.log';rows=[s for s in log.read_text().splitlines() if s.startswith(CORE.PREFIX+'object=')]
    assert len(rows)==1
    common,extra=rows[0].split(' counts=',1)
    m=CORE.OLD.CR.fullmatch(common.replace(CORE.PREFIX,CORE.OLD.CR_PREFIX));x=CORE.EXTRA.fullmatch(' counts='+extra)
    assert m and x and len(rows[0].encode())+1<=2048 and x[15]=='0'
    counts=list(map(int,x[1].split(',')));execution=list(map(int,x[2].split(',')))
    assert sum(counts)==int(m[10]) and sum(execution)==int(m[11])
    paths=[Path(__file__),test,WORK/'tools/core339_log.py',log,
        PRIOR/'execution/backboardd.log.current',PARENT/'execution/backboardd.log.current']
    result=dict(state='0339-strict-codec-and-production-formatter-passed',tests=r.testsRun,
        contract_mutations=34,includes_whole_completion_before_notice=True,
        real_production_core_rows_format_checked=1,mixed_wait_categories_and_recording_worst_job_tested=True,
        prior337_and338_collections_rejected=True,physical_FPS_qualified=False,device_commands=0,
        input_pins={str(p):sha(p) for p in paths},test_log=stream.getvalue())
    with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','test_log')},indent=2))


if __name__=='__main__':main()
