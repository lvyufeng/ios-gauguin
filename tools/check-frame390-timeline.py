#!/usr/bin/env python3
"""Verify the compact CA observer with sanitizers and restored 0386 identities."""

from collections import defaultdict
from importlib import import_module
import json
from pathlib import Path
from struct import Struct
import subprocess
from tempfile import TemporaryDirectory

from frame390_build import BASE, CAP, load_ca_port, require, sha, stage
from frame390_timeline import decode

ARCHIVE_PROGRAM = r"""
static int replay(void)
{
    static struct f385_row rows[F385_GESTURE_CAP];
    uint32_t count;
    while (fread(&count, sizeof(count), 1, stdin) == 1) {
        struct f390_snapshot snap;
        assert(count <= F385_GESTURE_CAP && fread(rows, sizeof(rows[0]), count, stdin) == count &&
               fread(&snap, sizeof(snap), 1, stdin) == 1);
        struct f390_commit_receipt r;
        if (f390_commit_for_snapshot(rows, count, &snap, &r)) {
            const uint64_t values[] = {r.commit->tick, r.encoded->tick, r.send->tick, r.receive->tick,
                                      r.command->tick, r.apply->tick};
            assert(fwrite(values, sizeof(values), 1, stdout) == 1);
        } else {
            const uint64_t empty[6] = {0};
            assert(fwrite(empty, sizeof(empty), 1, stdout) == 1);
        }
    }
    assert(feof(stdin));
    return 0;
}
"""


def build_fixture(folder, source):
    prior = import_module('check-frame385')
    code = prior.FIXTURE.replace(
        'else if (address >= UINT64_C(0x10000))',
        'else if (address == UINT64_C(0x1e1df7755) && n == 1) *(uint8_t *)out = 0;\n'
        '    else if (address >= UINT64_C(0x10000))')
    code = code.replace('int main(void)\n{',ARCHIVE_PROGRAM+'''
int main(int argc, char **argv)
{
    (void)argv;
    if (argc > 1) return replay();
''')
    code = code.replace('    for (unsigned i = 2; i <= 13;', '''    sweet_ca385_swipe(2, 40000000);
    for (unsigned i = 0; i <= F385_GESTURE_CAP; ++i)
        f385_record(2, F385_SOURCE, 40000001+i, 101, 24, 81, 0, 0);
    for (unsigned i = 3; i <= 13;''')
    stub = folder/'mach/arm/thread_status.h'
    stub.parent.mkdir(parents=True)
    stub.write_text('')
    path,binary = folder/'fixture.c',folder/'fixture'
    path.write_text(code)
    p = subprocess.run(['xcrun','clang','-std=gnu17','-Wall','-Wextra','-Werror',
                       '-fsanitize=address,undefined','-I',str(folder),'-I',str(source/'bsd/dev'),str(path),
                       '-o',str(binary)],text=True,capture_output=True,timeout=60)
    require(p.returncode==0,'CA timeline fixture compile failed: '+p.stderr[-2500:])
    return binary


def restored_fixture(binary):
    prior = import_module('audit-frame386-ca-prefix')
    reader = import_module('frame385_transactions')
    execution = prior.BASE/'execution'
    require(all(sha(execution/name)==digest for name,digest in prior.PINNED.items()),'0386 retained inputs differ')
    raw = (execution/'kernel.log').read_text()
    start,end,n,d = prior.envelope(raw)
    _,events = prior.read_prefix(raw,start,end)
    by_stroke, by_kind = defaultdict(list),defaultdict(list)
    for e in events:
        by_stroke[e.stroke].append(e)
        by_kind[e.kind].append(e)
    applies = reader.match_applies(by_kind,prior.packet_lane(raw,n,d)['pairs'])
    row = Struct('<6QHH4x')
    snap = Struct('<4Q4I2B6x')
    count = Struct('<I')
    output = Struct('<6Q')
    payload, expected = bytearray(), []
    for (context,version),matches in applies.items():
        for chain in matches:
            apply = chain[-1]
            rows = by_stroke[apply.stroke]
            # These snapshots are synthetic. The source/transport/apply
            # identities and their timing come from the validated archive.
            for state,cid,seed in ((1,version>>32,version&0xffffffff),(2,version>>32,version&0xffffffff)):
                payload.extend(count.pack(len(rows)))
                for e in rows:
                    payload.extend(row.pack(e.tick,e.thread,e.a,e.b,e.c,e.d,e.kind,e.stroke))
                payload.extend(snap.pack(max(e.tick for e in chain)+1,0,context,0,1,1,cid,seed,state,0))
                expected.append(tuple(e.tick for e in chain) if state==1 else (0,)*6)
    replay = subprocess.run([str(binary),'archive'],input=payload,capture_output=True,timeout=60)
    require(replay.returncode==0,'CA restored fixture failed: '+replay.stderr.decode(errors='replace')[-1500:])
    actual = list(output.iter_unpack(replay.stdout))
    require(len(expected)==304 and actual==expected,'CA compact identities differ from the retained 0386 joins')
    return dict(matching_retained_apply_chains=152,rejected_ambiguous_snapshots=152,
        source_pins={str(execution/name):digest for name,digest in prior.PINNED.items()})


def check():
    port = load_ca_port()
    static = port.observer.static()
    with TemporaryDirectory(prefix='0390-wire-test-',dir=BASE) as folder:
        root = Path(folder)
        source,patch,pins = stage(root)
        binary = build_fixture(root,source)
        raw = subprocess.check_output([str(binary)],text=True,timeout=25)
        packet = dict(serial=17,message_id=40002,sender_thread=101,receiver_thread=102,send_tick=13000,copyout_tick=13500)
        stats,snapshots,joined = decode(raw,1000,500000000,[packet])
        receipt, = (r for r in joined.values() if r is not None)
        require(stats['retention'][2]==dict(retained=CAP,lost=1,receipts=0) and
                receipt['commit']==11000 and receipt['apply']==16000 and receipt['inclusion']==[18000,19000] and
                receipt['snapshot'].key==snapshots[0].key,'CA compact fixture chronology or lane isolation differs')
        broken = dict(packet,copyout_tick=15000)
        reject,_,partial = decode(raw,1000,500000000,[broken])
        require(reject['missing_IPC']==1 and list(partial.values())==[None],
                'an unrelated kernel packet completed the CA chain')
        archive = restored_fixture(binary)
        return dict(state='0390-compact-CA-timeline-offline-verified',ASan_UBSan=True,device_commands=0,
            static=static,fixture_swipes=len(stats['retention']),scope_overflow_rejected=True,archive=archive,
            staged_patch_sha256=sha(patch),input_pins=pins)


if __name__=='__main__':
    print(json.dumps(check(),indent=2))
