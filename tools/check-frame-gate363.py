#!/usr/bin/env python3
"""Reproduce the gate fault and exercise capture entry with the actual boot arguments."""

from importlib import import_module
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame362_scope import MAIN, WORK, load, require, sha

OLD = MAIN/'research/tmp/gauguin-sdk-control-worktree-20261121/research/tmp/frame-362'
OUT = WORK/'research/tmp/frame-gate-363'
FIXTURE = WORK/'tests/fixtures/frame-mode363.c'


def load_driver(directory, basename):
    return (directory/'native-kernel/source/bsd/dev'/basename).read_text()


def frame_init(raw, suffix):
    body = raw.split('static void frame_init(void)\n',1)[1].split('\nvoid sweet_frame344_prepare',1)[0]
    return 'static void frame_init_'+suffix+'(void)\n'+body


def check():
    touch = load_driver(OUT,'sweet_touch.c')
    before = load_driver(OLD,'gauguin_ui_trace_board.c')
    after = load_driver(OUT,'gauguin_ui_trace_board.c')
    image = load(OUT/'frame363-image.json')
    artifact = Path(image['image'])
    payload = import_module('package-frame344').parts(artifact.read_bytes())[2]
    command = payload[0x48:0x2a8].rstrip(b'\0').decode()
    require(touch==load_driver(OLD,'sweet_touch.c') and
            artifact.stat().st_size==image['image_bytes'] and sha(artifact)==image['image_sha256'] and
            command==image['command']==load(OLD/'trial-plan.json')['boot_command'] and
            {'swp=4','sweetfb_stats=9','sweetnvt=0','sweetfb_hz=60'} <= set(command.split()) and
            touch.count('sweet_frame344_prepare();')==1,
            'capture repair changed touch source or the frozen workload selector')
    dispatch = touch.split('\n\tint swipe = 0;',1)[1].split('\n\t/* Independent opt-in stage0',1)[0]
    prepared_body = after.split('\nvoid sweet_frame344_prepare(void)',1)[1].split('\nstatic void frame_drain',1)[0]
    functions = '\n'.join((frame_init(before,'before'),frame_init(after,'after'),
        'void sweet_frame344_prepare(void)'+prepared_body,
        'static void touch_init_mode(void) { int physical = physical_mode; int swipe = 0;'+dispatch+'\n}'))
    with TemporaryDirectory(prefix='0363-gate-check-',dir=OUT) as directory:
        work = Path(directory)
        source = work/'frame-mode.c'
        source.write_text(FIXTURE.read_text().replace('/* MODE_IMPLEMENTATIONS */',functions))
        binary = work/'frame-mode'
        subprocess.run(['clang','-Wall','-Wextra','-Werror','-O1','-fsanitize=address,undefined',str(source),
                        '-o',str(binary)],check=True,timeout=120)
        result = subprocess.check_output([str(binary)],text=True,timeout=20).strip()
    require(result=='480 gate and prepare combinations passed','mode coverage differs')
    inputs = (FIXTURE,OUT/'frame363-image.json',artifact,
              OUT/'native-kernel/source/bsd/dev/gauguin_ui_trace_board.c',
              OUT/'native-kernel/source/bsd/dev/sweet_touch.c')
    report = dict(state='0363-packed-boot-and-capture-prepare-passed',cases=480,boot_selector=4,
                  reproduced_0362_gate_failure=True,capture_transition_and_single_poll_start=True,
                  device_commands=0,input_pins={str(path):sha(path) for path in inputs})
    with (OUT/'gate-start-host.json').open('x') as stream:
        json.dump(report,stream,indent=2)
        stream.write('\n')
    return report


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
