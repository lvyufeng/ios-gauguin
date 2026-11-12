#!/usr/bin/env python3
"""An absent individual approval must stop before ADB, fastboot or a claim."""

import os
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path


WORK = Path(__file__).resolve().parents[1]
STATE = WORK/'research/tmp/sb-rate-20261112'
RUNNER = WORK/'tools/run-sb-rate-trial.py'


def main():
    assert (STATE/'ready.json').is_file()
    assert not (STATE/'approval.json').exists()
    assert not (STATE/'execution').exists()
    with tempfile.TemporaryDirectory(prefix='sb-trial-gate-') as temporary:
        root=Path(temporary)
        marker=root/'device-command-called'
        for command in ('adb','fastboot'):
            path=root/command
            path.write_text('#!/bin/sh\n: > '+str(marker)+'\nexit 97\n')
            path.chmod(0o700)
        env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ['PATH'])
        result=subprocess.run([sys.executable,str(RUNNER)],env=env,
                              capture_output=True,text=True,timeout=10)
        assert result.returncode != 0
        assert 'no individual SpringBoard trial approval; zero device IO' in result.stderr
        assert not marker.exists() and not (STATE/'execution').exists()
    spec=importlib.util.spec_from_file_location('sb_trial',RUNNER)
    runner=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert runner.classify_observer({'observer_seen':True,'records_in_window':1},False) == \
        'SpringBoard-log-tail-ambiguous-root-restored'
    assert runner.classify_observer({'observer_seen':False,'records_in_window':0},True) == \
        'SpringBoard-observer-not-seen-root-restored'
    assert runner.classify_observer({'observer_seen':True,'records_in_window':0},True) == \
        'SpringBoard-observer-active-no-samples-root-restored'
    assert runner.classify_observer({'observer_seen':True,'records_in_window':1},True) == \
        'SpringBoard-rate-observed-root-restored'
    print('SpringBoard trial gate refused before any device command')


if __name__=='__main__':
    main()
