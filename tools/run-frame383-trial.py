#!/usr/bin/env python3
"""Score the same hardware flip only after the recoverable IOKit mapping fix verifies."""

from functools import partial
from importlib import import_module

scope = import_module('prepare-frame383')
parent = import_module('run-frame382-trial')

if __name__=='__main__':
    raise SystemExit(parent.parent.runner.main(scope,
        after_restore_fn=partial(parent.after_restore,trial_scope=scope)))
