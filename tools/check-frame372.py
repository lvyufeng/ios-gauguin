#!/usr/bin/env python3
"""Exercise the native compact wire format and pin exact CA code ranges."""

from hashlib import sha256
from importlib import import_module, util
from pathlib import Path
import re
import subprocess

from frame372_transport import BLOCK, CAP, MISSES, ROW, THREADS, decode, snapshot_handoff

scope = import_module('prepare-frame372')

DRIVER = r'''
#include <assert.h>
#include <inttypes.h>
#include <stdio.h>
#include "gauguin_frame372_wire.h"

static void emit(unsigned index, unsigned count, const uint8_t *data)
{
    char wire[4*((F372_BLOCK*F372_ROW+2)/3)+1];
    f372_base64(data,count*F372_ROW,wire);
    printf("SWEET F372 B %u %u %s\n", index, count, wire);
}

int main(void)
{
    uint8_t block[F372_BLOCK*F372_ROW];
    uint64_t base,send,post,done;
    unsigned serial,id,source,dest,count=0,position=0;
    assert(!f372_pack_pair(block,1,0,0,1,1,1,0,0));
    assert(!f372_pack_pair(block,1,1,0,1,3,2,0,0));
    assert(!f372_pack_pair(block,1,1,0,0,1,2,0,0));
    assert(!f372_pack_pair(block,1,1,0,1,1,UINT64_MAX,0,0));
    while (scanf("%" SCNu64 " %u %u %" SCNu64 " %" SCNu64 " %" SCNu64 " %u %u",
        &base,&serial,&id,&send,&post,&done,&source,&dest)==8) {
        assert(source<=255 && dest<=255 &&
            f372_pack_pair(block+count*F372_ROW,base,serial,id,send,post,done,source,dest));
        if (++count==F372_BLOCK) {
            emit(position,count,block);
            position+=count;
            count=0;
        }
    }
    if (count) emit(position,count,block);
    return 0;
}
'''


def emit(binary, rows, base, end, numer, denom):
    tids = sorted({thread for row in rows for thread in row[5:]})
    ids = {tid:i for i,tid in enumerate(tids)}
    data = ''.join(' '.join(map(str,(base,*row[:5],ids[row[5]],ids[row[6]])))+'\n' for row in rows)
    blocks = subprocess.check_output([str(binary)],input=data,text=True,timeout=30)
    count = len(rows)
    sent = max(row[0] for row in rows)
    header = (f'SWEET F344 H: count=1 reason=1 lost=0 start={base} end={end} numer={numer} denom={denom}\n'
        f'SWEET F372 H: count={count} cap={CAP} sent={sent} sent_cap=16384 copied={count} '
        f'missed=0 busy=0 evicted=0 failed=0 start={base}\n')
    dictionary = ''.join(f'SWEET F372 D: index={i} tid={tid}\n' for i,tid in enumerate(tids))
    wire = header+dictionary+blocks+f'SWEET F372 F: count={count} threads={len(tids)}\n'
    receipt = decode(wire,numer,denom)
    keys = ('serial','message_id','send_tick','post_tick','copyout_tick','sender_thread','receiver_thread')
    scope.require([tuple(row[k] for k in keys) for row in receipt['pairs']]==
        sorted(rows,key=lambda row:(row[4],row[0])), 'native compact receipt changed a tick, thread or serial')
    return wire


def ca_ranges(path):
    root = scope.MAIN/'research/tmp/gauguin-sb-stack-worktree-20261114/research/tmp/sb-stack-315'
    source = root/'symbolize_stack315_v2.py'
    spec = util.spec_from_file_location('local20H392',source)
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    resolver = mod.Resolver()
    names = (
        ('Render6Server13server_thread','CA server receive and dispatch'),
        ('Render7Decoder','CA decoder'),
        ('Render7Context13apply_streams','CA apply_streams'),
        ('Render7Context11will_commit','CA prepare commit'),
        ('Render7Context10did_commit','CA finish commit'),
        ('WindowServer6Server15context_changed','CA context_changed'),
        ('IOMFBServer15set_next_update','IOMFB set_next_update'),
        ('WindowServer6Server15set_next_update','CA next-update deadline'),
        ('IOMFBServer14vsync_callback','IOMFB vsync_callback'),
        ('WindowServer6Server15render_for_time','CA render_for_time'),
    )
    try:
        image = '/System/Library/Frameworks/QuartzCore.framework/QuartzCore'
        metadata = resolver.image(image)
        scope.require(metadata['uuid']=='9e40b2eb260c3af1ae45a1a551a8c1b9','QuartzCore cache UUID differs')
        result = {}
        ns = resolver.ns
        for address,offsets in metadata['symbols'].items():
            symbols = [ns['symbol_name'](offset) for offset in offsets]
            for key,stage in names:
                if not any(key in symbol for symbol in symbols):
                    continue
                mapped = resolver.instruction(metadata,address)
                if mapped['state']!='mapped-function' or int(mapped['function_start'],16)!=address:
                    continue
                end = int(mapped['function_end_exclusive'],16)
                result[address] = dict(start=address,end=end,stage=stage,
                    code_sha256=sha256(ns['vmread'](address,end-address)).hexdigest())
        scope.require(set(row['stage'] for row in result.values())=={stage for _,stage in names},
                'incomplete source code ranges for CA handoff')
        rows = [result[a] for a in sorted(result)]
        scope.require(all(a['end']<=b['start'] for a,b in zip(rows,rows[1:])), 'overlapping CA stages')
        scope.save(path,dict(image_uuid=metadata['uuid'],cache_build='20H392',ranges=rows,
            resolver_sha256=scope.sha(source),device_writes=0))
    finally:
        resolver.close()


def main():
    scope.check_budget()
    out = scope.HOST.parent
    out.mkdir()
    source = out/'compact-wire-projection.c'
    source.write_text(DRIVER)
    include = scope.BASE/'native-kernel/source/bsd/dev'
    binary = out/'compact-wire-projection'
    subprocess.run(['xcrun','clang','-std=c11','-g','-O1','-Wall','-Wextra','-Werror',
        '-fsanitize=address,undefined','-fno-sanitize-recover=all','-I',str(include),
        str(source),'-o',str(binary)],check=True,timeout=60)
    raw = (scope.REFERENCE/'kernel.log').read_text()
    base,end,n,d = map(int,re.search(r'^SWEET F344 H: .* start=(\d+) end=(\d+) numer=(\d+) denom=(\d+)$',
                                    raw,re.M).groups())
    fields = re.findall(r'^SWEET F371 E ([0-9a-f ]+)$',raw,re.M)
    rows = [tuple(int(x,16) for x in field.split()) for field in fields]
    scope.require(len(rows)==1536,'0371 captured prefix differs')
    wire = emit(binary,rows,base,end,n,d)
    dense = [(i,40002,base+i,base+i+5,base+i+9,1<<40,1<<41) for i in range(1,CAP+1)]
    whole = emit(binary,dense,base,end,n,d)
    for mutation in (wire.replace('F372 B 0 64','F372 B 1 64',1),
                     wire.replace('F372 D: index=0','F372 D: index=1',1),
                     wire.replace('F372 F: count=1536','F372 F: count=1535',1)):
        try:
            decode(mutation,n,d)
        except ValueError:
            continue
        raise ValueError('malformed compact receipt was accepted')
    receipt = decode(whole,n,d)
    scope.require(receipt['full_scope_observed'] and receipt['paired_exact_receipts']==CAP,
                  'dense capacity replay lost receipts')
    saturated = decode(whole.replace(f'copied={CAP}',f'copied={CAP+1}').replace(
        f'sent={CAP}',f'sent={CAP+1}'),n,d)
    scope.require(saturated['losses']['cap_saturation'] and not saturated['full_scope_observed'],
                  'transport saturation was silently accepted')
    receiver = 1<<41
    sample = (f'SMP backboardd[57] slide 0x100 mh 0x1000\n'
              f'SMP backboardd t0 tid {receiver} st 1 ev 0x0 wr 0 pc 0x1220 lr 0x1230 sp 0x8000\n'
              f'SWEET F372 S: tid={receiver} serial=1 epoch=1 read={base+20},{base+21}\n')
    stage = [dict(start=0x1100,end=0x1300,stage='test')]
    handoff = snapshot_handoff(sample,receipt,[dict(begin_thread=3)],stage)
    scope.require(handoff['register_samples'][0]['match'] and
        handoff['register_samples'][0]['pc_stage']=='test' and
        not handoff['continuous_transaction_identity_verified'],'sample receipt promoted to an exact swap cause')
    try:
        snapshot_handoff(sample.replace(f'{base+20},{base+21}',f'{base+5},{base+6}'),receipt,[],stage)
    except ValueError:
        pass
    else:
        raise ValueError('copyout after sample was accepted')
    text = out/'0371-roundtrip.log'
    text.write_text(wire)
    reference = scope.load(scope.REFERENCE/'kernel-IO-analysis.json')['ring']['total_bytes']
    prior_bytes = sum(len(row.encode())+len(b'\nSWEET F371 E \n') for row in fields)
    bound = (CAP//BLOCK)*(4*((BLOCK*ROW.size+2)//3)+64)+THREADS*64+MISSES*64+64*160+1024
    projected = reference-prior_bytes+bound
    scope.require(projected<4_194_304,'compact wire and stage evidence exceed measured console headroom')
    mapping = out/'20H392-ca-code-ranges.json'
    ca_ranges(mapping)
    files = (source,binary,text,mapping,include/'gauguin_frame372_wire.h')
    scope.save(scope.HOST,dict(state='0372-compact-transport-cross-compiled-and-modeled',
        patch_sha256=scope.sha(scope.PATCH),projection_passed=True,device_writes=0,device_boots=0,
        lossless_0371_records=len(rows),synthetic_capacity_pairs=CAP,record_bytes=ROW.size,
        reference_raw_bytes=reference,full_scope_export_bound=bound,projected_ring_bound=projected,
        input_pins={str(file):scope.sha(file) for file in files}))


if __name__=='__main__':
    main()
