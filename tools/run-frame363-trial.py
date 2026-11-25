#!/usr/bin/env python3
"""Execute the approved F344 repair and score after fresh readback."""

import argparse
from functools import partial
from importlib import import_module

from frame363_scope import BASE, FLAGS, RESERVE, SUCCESS, expected_plan

EXEC = BASE/'execution'
after_restore = partial(import_module('run-frame362-trial').after_restore,trial='0363',success=SUCCESS)


def main(check_gate=False):
    run = import_module('run-core342-trial')
    try:
        plan,approval,budget = import_module('run-frame347-trial').authorization(
            run,base=BASE,trial='0363',expected=expected_plan,flags=FLAGS,reserve=RESERVE)
    except (Exception,KeyboardInterrupt) as error:
        print('0363 refused before device IO: '+repr(error),flush=True)
        return 2
    if check_gate:
        print('0363 exact authorization and frozen inputs accepted. Zero device IO.',flush=True)
        return 0
    return run.execute(plan,approval,budget,BASE,EXEC,trial='0363',after_restore=after_restore,success_state=SUCCESS)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-gate',action='store_true')
    raise SystemExit(main(parser.parse_args().check_gate))
