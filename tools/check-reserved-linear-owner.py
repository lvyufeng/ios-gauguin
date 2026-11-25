#!/usr/bin/env python3
"""Exercise the compiled low framebuffer extent checks without device writes."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK, load, require, sha

layout = import_module('check-gauguin-reserved-linear')


def check(manifest):
    stamp = load(manifest)
    source = Path(stamp['source'])/layout.BOARD
    fixture = WORK/'tests/fixtures/gauguin_reserved_scanout_host.c'
    recorded = source.read_text()
    require('two-private-reserved-linear-slots' in recorded and 'sweet_fb411_buffers' not in recorded,
            'wrong backing qualification code')
    start = recorded.index('static bool scan382_prepare(const struct scan381_state *s)\n{')
    end = recorded.index('bool sweet_frame382_active(',start)
    sdk = subprocess.check_output(['xcrun','--sdk','macosx','--show-sdk-path'],text=True).strip()
    with TemporaryDirectory(prefix='reserved-linear-owner-',dir=layout.BASE) as temp:
        directory = Path(temp)
        (directory/'gauguin_reserved_prepare.inc').write_text(recorded[start:end])
        executable = directory/'owner'
        subprocess.run([str(layout.layout.COMPILER/'clang'),'-isysroot',sdk,'-std=c11','-Wall','-Wextra','-Werror',
            '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I'+str(directory),
            '-I'+str(source.parent),str(fixture),'-o',str(executable)],check=True,timeout=60)
        subprocess.run([str(executable)],check=True,stdout=subprocess.DEVNULL,timeout=20)
    return dict(state='reserved-linear-backing-checked',cases=8,device_commands=0,
                input_pins={str(path):sha(path) for path in (manifest,source,fixture)})


if __name__=='__main__':
    import argparse
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('manifest',type=Path)
    print(json.dumps(check(cli.parse_args().manifest.resolve()),indent=2))
