#!/usr/bin/env python3
"""Execute actual queue/client methods and verify the passive snapshot contract."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]


def method(text,signature):
    start=text.index(signature)
    return text[start:text.index('\n}',start)+2]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--receipt',type=Path)
    args=ap.parse_args();base=args.source.resolve();hid=base/'iokit/Kernel/arm/hid'
    fixture=ROOT/'tests/fixtures/hid_queue_observer_host.cpp'
    files=[Path(__file__),fixture,hid/'IOHIDEventServiceQueue.cpp',hid/'IOHIDEventServiceUserClient.cpp',base/'bsd/dev/gauguin_ui_trace.h']
    pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    queue=(hid/'IOHIDEventServiceQueue.cpp').read_text();client=(hid/'IOHIDEventServiceUserClient.cpp').read_text()
    bodies='\n'.join(method(queue,s) for s in [
        'Boolean IOHIDEventServiceQueue::enqueueEvent(',
        'void IOHIDEventServiceQueue::sendDataAvailableNotification(',
        'bool IOHIDEventServiceQueue::copyTraceState('])
    text=fixture.read_text().replace('@QUEUE_METHODS@',bodies).replace('@CLIENT_METHOD@',method(client,'void IOHIDEventServiceUserClient::enqueueEventGated('))
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
    with tempfile.TemporaryDirectory(prefix='hid-queue-observer-') as tmp:
        tmp=Path(tmp);unit=tmp/'test.cpp';unit.write_text(text);exe=tmp/'test'
        subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-O1','-g',
            '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(base/'bsd/dev'),str(unit),'-o',str(exe)],env=env,check=True)
        result=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
        assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
        print(result.stdout,end='')
    assert pins=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    if args.receipt:
        assert not args.receipt.exists()
        args.receipt.write_text(json.dumps({'state':'passed-actual-HID-queue-observation-host','input_pins':pins,
            'inputs_unchanged':True,'output':result.stdout,'sanitizers':'address,undefined','hardware_qualified':False},indent=2)+'\n')


if __name__=='__main__':main()
