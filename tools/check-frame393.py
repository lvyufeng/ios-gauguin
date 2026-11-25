#!/usr/bin/env python3
"""Exercise two exact CA transactions in the same annotated update."""

from importlib import import_module
import json
import os
import re
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from frame390_build import load_ca_port,replace_once
from frame393_build import BASE,PREVIOUS,load,stage,require,sha
from frame393_timeline import decode,measure


def host(source, root):
    fixture = import_module('check-frame385').FIXTURE
    fixture = replace_once(fixture,'else if (address >= UINT64_C(0x10000))',
        'else if (address == UINT64_C(0x1e1df7755) && n == 1) *(uint8_t *)out = 0;\n'
        '    else if (address >= UINT64_C(0x10000))')
    fixture = replace_once(fixture,'    now = 21000;', '''    uint8_t context2[0xc0] = {0}, node2[32] = {0};
    const uint64_t alternate = (uintptr_t)context2;
    word(context2, 0x10, 82);
    word(context2, 0xbc, 26);
    pointer(node2, 8, context2);
    word(node2, 0x18, 18);
    pointer(node, 0, node2);
    f385_record(1,F385_SOURCE,11100,201,24,82,0,0);
    f385_record(1,F385_SEND,13100,201,18,24,40003,0);
    f385_record(1,F385_ENCODED,14300,201,24,82,0,0);
    f385_record(1,F385_RECEIVE,14100,202,40,18,40003,0);
    f385_record(1,F385_COMMAND,15100,202,48,18,alternate,((uint64_t)82<<32)|17);
    f385_record(1,F385_APPLY,16100,202,48,18,alternate,((uint64_t)82<<32)|18);
    now = 21000;''')
    fixture = replace_once(fixture,'    for (unsigned i = 2; i <= 13;', '''    assert(f393_versions[0][0].count==2);
    now = 23000;
    debug(UINT64_C(0x1882d166c), 0x31ca0084, 72, 0, 42);
    assert(f393_versions[0][1].count==2);
    pointer(node2,0,node2);
    now = 25000;
    debug(UINT64_C(0x1882d166c), 0x31ca0084, 73, 0, 42);
    assert(f393_versions[0][2].count==0);
    sweet_ca385_swipe(2,40000000);
    for (unsigned i = 0; i <= F385_GESTURE_CAP; ++i)
        f385_record(2,F385_SOURCE,40000001+i,101,24,81,0,0);
    for (unsigned i = 3; i <= 13;''')
    support = root/'mach/arm/thread_status.h'
    support.parent.mkdir(parents=True)
    support.write_text('')
    probe = root/'fixture.c'
    binary = root/'fixture'
    probe.write_text(fixture)
    common = Path(load(PREVIOUS)['source'])/'bsd/dev'
    compile = subprocess.run(['xcrun','clang','-std=gnu17','-Wall','-Wextra','-Werror',
                               '-fsanitize=address,undefined','-I'+str(root),'-I'+str(source/'bsd/dev'),'-I'+str(common),
                               str(probe),'-o',str(binary)],capture_output=True,text=True,timeout=60)
    require(compile.returncode==0,'CA member fixture compile failed: '+compile.stderr[-2100:])
    return subprocess.check_output([str(binary)],text=True,timeout=25,
        env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1'))


def archived_first_swaps():
    archive = PREVIOUS.parents[1]/'execution'
    proof = load(archive/'result.json')
    path = archive/'scanout-comparison-0388-0390.json'
    require(proof['independent_restore_verified'] and sha(path)==
        '81d6b1e4f166b57ef5431c817bc0232340e9628aeaff9fd4bc79592b38ccdc8d','0390 restored reference differs')
    old = import_module('run-frame390-trial')
    plan = load(archive.parent/'trial-plan.json')
    scans,_ = old.audit.score_archive(archive,plan['kernel_banner'],expected_pairs=None,require_first=False)
    original = (archive/'kernel.log').read_text()
    require('SWEET F390 TX B ' not in original,'0390 unexpectedly contained a compact transaction')
    # The 0390 raw membership and scan chronology are retained. An empty
    # new-format transaction envelope exercises the host's independent join.
    raw = re.sub(r'^SWEET F390 TX Q (.+)$',r'SWEET F393 Q \1 0',original,flags=re.M)
    raw = raw.replace('SWEET F390 TX F ','SWEET F393 F ')
    rows,_,n,d = old.stage.staging.parse(raw)
    latches = old.stage.staging.verified_latches(rows,old.flip.latch_receipts(raw,rows)['accepted_by_scan'])
    output = measure(archive,raw,rows,n,d,latches,scans)
    require(len(output['strokes'])==13 and all(r['swap_membership']==2 and r['gate']==0 and not r['transactions']
        for r in output['strokes']),'0390 first swaps or closed-gate status did not reproduce')
    return dict(swaps=13,closed_gate=13,exact_transactions=0)


def test():
    load_ca_port()
    with TemporaryDirectory(prefix='0393-CA-host-',dir=BASE) as temporary:
        root = Path(temporary)
        source,patch = stage(root)
        raw = host(source,root)
        packets = [dict(serial=i,message_id=message,sender_thread=sender,receiver_thread=receiver,
                        send_tick=send,copyout_tick=arrive) for i,message,sender,receiver,send,arrive in (
            (17,40002,101,102,13000,13500),(18,40003,201,202,13100,13600))]
        stats,snapshots,by_swap = decode(raw,1000,500000000,packets)
        a,b,invalid = snapshots
        require(a.observed==b.observed==2 and invalid.observed==3 and invalid.key not in by_swap and
            len(by_swap[a.key])==len(by_swap[b.key])==2 and by_swap[a.key]==by_swap[b.key],
            'a native swap did not carry both exact versions or accepted incomplete read')
        first,second = by_swap[a.key]
        require((first['context'],first['version'],first['apply'],first['inclusion'])==(81,25,16000,(18000,19000)) and
            (second['context'],second['version'],second['apply'],second['inclusion'])==(82,18,16100,None) and
            first['first_membership']==second['first_membership']==a.key and stats['retention'][2]['lost']==1,
            'exact per-member apply, inclusion, or isolated stroke differs')
        alternate = [packets[0],dict(packets[1],receiver_thread=222)]
        bad,_,partial = decode(raw,1000,500000000,alternate)
        require(bad['missing_IPC']==1 and partial[a.key]==[first] and partial[b.key]==[first],
            'unrelated kernel IPC capsule completed a second context')
        return dict(state='0393-exact-two-member-swap-with-repeated-annotation-offline-verified',
            ASan_UBSan=True,exact_members=2,other_matches_refused=1,incomplete_snapshot_refused=True,
            isolated_overflow_stroke=2,stage_patch_sha256=sha(patch),
            independent_0390_snapshot_replay=archived_first_swaps(),device_commands=0)


if __name__=='__main__':
    print(json.dumps(test(),indent=2))
