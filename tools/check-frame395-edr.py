#!/usr/bin/env python3
"""Verify the signed ARM64 boot-argument comparison independently of C strings."""

import json
from pathlib import Path
import re
import subprocess

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-395'
P392 = MAIN/'research/tmp/gauguin-frame392-native-stock-worktree-20261123/research/tmp/frame-392'


def native_words(path):
    output = subprocess.check_output(['xcrun','otool','-t',str(path)],text=True,timeout=30)
    result = {}
    for line in output.splitlines():
        if not re.fullmatch(r'[0-9a-f]{16}(?: [0-9a-f]{8})+ ?',line): continue
        address,*words = line.split()
        first = int(address,16)
        for i,word in enumerate(words): result[first+4*i] = int(word,16)
    require(len(result)==1705,'native helper text size differs')
    return result


def check():
    exe = BASE/'edr-native/result.json'
    result = load(exe)
    old = load(P392/'edr-native/result.json')
    built,control,broken = (Path(p) for p in (result['binary'],result['profile_control'],old['binary']))
    require(sha(built)==result['binary_sha256'] and sha(control)==result['profile_control_sha256'] and
            sha(broken)==old['binary_sha256'] and result['profile_source_compiled'] and
            result['binary_bytes']==old['binary_bytes']==53520 and result['scope_checks']==2145,
            'native scope test inputs differ')
    subprocess.run(['codesign','--verify','--strict',str(built)],check=True,timeout=30)
    before,wanted,wrong = map(native_words,(control,built,broken))
    require(wanted.keys()==before.keys()==wrong.keys() and all(
        before[addr]==wrong[addr] for addr in range(0x4bb0,0x4d70,4)),
        'old ARM64 argument checking code does not match 0392')
    changes = {addr:(before[addr],word) for addr,word in wanted.items() if word!=before[addr]}
    require(changes=={0x4be0:(0x52800684,0x528006a4)} and
        all(wanted[addr]==word for addr,word in {
            0x4c14:0xb9400233, # ldr w19, [x17]
            0x4c18:0x39401235, # ldrb w21, [x17, #4]
            0x4c1c:0x6b00027f, # cmp w19, w0
            0x4c20:0x7a4402a0, # ccmp w21, w4, #0, eq
        }.items()),'native helper does not compare the fifth byte against ASCII 5')
    return dict(state='0395-signed-native-gpf5-scope-verified',scope_checks=2145,
                original_argument_check_reproduced=True,reviewed_machine_instruction_changes=1,
                otherSDK_word_differences=sum(before[addr]!=wrong[addr] for addr in before),
                compare_byte_offset=4,before=52,after=53,device_commands=0,
                input_pins={str(p):sha(p) for p in (exe,built,control,broken)})


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
