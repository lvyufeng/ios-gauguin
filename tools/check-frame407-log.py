#!/usr/bin/env python3
"""Verify lossless compact GPU request rows and stage only their formatter."""

import argparse
from difflib import unified_diff
from importlib import import_module
import json
from pathlib import Path
import re
import struct
import subprocess
from tempfile import TemporaryDirectory

from frame366_scope import WORK,load,require,sha
import kernel342_log as wire

hint = import_module('check-frame406-hint')
BASE = WORK/'research/tmp/frame-407'
PATCH = BASE/'407-compact-IO-rows.patch'
INPUT = WORK/'graphics/gauguin-io-path/Kernel342.hpp'
FIXTURE = WORK/'tests/fixtures/kernel_phase342.cpp'
HEADER = Path('iokit/Kernel/arm/Kernel342.hpp')
REFERENCE = hint.previous.CONTROL.parents[1]/'execution'
ROW = wire.PREFIX+'row '
TOKEN = '    uint64_t token()const noexcept{return row_.token;}\n'


def replay(reference):
    text = (reference/'kernel.log').read_text()
    raw = (reference/'kernel.log.bin').read_bytes()
    old = wire.parse(text,raw)
    require(old['coverage_qualified'] and old['header']['version']==1,'compact replay source differs')
    lines = []
    row_bytes = 0
    for line in text.splitlines(keepends=True):
        if line.startswith(ROW):
            fields = line[len(ROW):].split()
            line = ROW+' '.join(field.split('=',1)[1] for field in fields)+'\n'
            row_bytes += len(line.encode())+1
        lines.append(line)
    text = ''.join(lines).replace(wire.PREFIX+'begin version=1',wire.PREFIX+'begin version=2',1)
    replaced,n = re.subn(r'(^SWEET IO342: begin .*? row_bytes=)\d+',
        lambda match:match[1]+str(row_bytes),text,flags=re.M)
    require(n==1,'compact replay header is ambiguous')
    data = replaced.encode()
    ring = struct.pack('<8sIIQQ',b'SWEETLOG',1,4_194_304,len(data),old['ring']['flush_sequence']).ljust(4096,b'\0')
    ring += data.ljust(4_194_304,b'\0')
    compact = wire.parse(replaced,ring)
    require(compact['coverage_qualified'] and compact['rows']==old['rows'] and compact['footer']==old['footer'] and
            len(old['rows'])>2_500,'compact encoding changed a request or timing phase')
    row = next(line for line in replaced.splitlines() if line.startswith(ROW))
    bad = [row.replace('row 0 ','row 1 ',1),row.replace('row 0 ','row index=0 ',1),row+' 0']
    for wrong in bad:
        require(wrong!=row and not wire.parse(replaced.replace(row,wrong,1),ring)['coverage_qualified'],
                'malformed compact request unexpectedly qualified')
    return dict(rows=len(old['rows']),saved_bytes=old['header']['row_bytes']-row_bytes,
        identical_phase_rows=True)


def host(control):
    source = Path(load(control)['source'])
    original = (source/HEADER).read_text()
    canonical = subprocess.check_output(['git','show','b7e9b71:graphics/gauguin-io-path/Kernel342.hpp'],cwd=WORK,text=True)
    require(original.count(TOKEN)==1 and original.replace(TOKEN,'')==canonical,
            'compact encoder donor has additional runtime changes')
    compact = INPUT.read_text()
    anchor = '    uint32_t selector()const noexcept{return row_.selector;}\n'
    require(compact.count(anchor)==1, 'missing native request accessor')
    compact = compact.replace(anchor,anchor+TOKEN)
    PATCH.write_text(''.join(unified_diff(original.splitlines(keepends=True),compact.splitlines(keepends=True),
        'a/'+str(HEADER),'b/'+str(HEADER))))
    with TemporaryDirectory(prefix='407-io-',dir=BASE) as folder:
        binary = str(Path(folder)/'test')
        subprocess.run(['xcrun','clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-fno-sanitize-recover=all','-I'+str(INPUT.parent),str(FIXTURE),'-o',binary],check=True,timeout=45)
        for mode in ('enabled','disabled','foreign-thread','capacity','overflow','pending-dump','format','dump-byte-limit','clock-scale'):
            subprocess.run([binary,mode],check=True,timeout=15,capture_output=True)
    proof = replay(REFERENCE)
    require(proof['saved_bytes']>=300_000,'compact wire headroom insufficient')
    return dict(state='0407-lossless-GPU-request-wire-host-verified',ASan_UBSan=True,device_commands=0,
        compatible_archive_replay=proof,patch_sha256=sha(PATCH),input_pins={str(p):sha(p) for p in (
            control,source/HEADER,INPUT,FIXTURE,Path(wire.__file__),PATCH,REFERENCE/'kernel.log',REFERENCE/'kernel.log.bin')})


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('control',type=Path)
    print(json.dumps(host(parser.parse_args().control.resolve()),indent=2))
