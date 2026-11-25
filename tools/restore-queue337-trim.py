#!/usr/bin/env python3
"""Narrow recovery for the observed 0337 C4 tail trim. No boot/misc operations.

Prepare only reads the phone. Execute requires a NEW actual approval bound to
this exact plan and independently reviewed model. Frozen trial/restore inputs
are never changed. A nonempty journal is accepted only when every coalesced
pending payload already equals its home sectors, with a bad/stale next header.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import time

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
BASE = WORK/'research/tmp/queue-loss-337'
BLOCK = 4096
VOLUME = 17179869184
TAIL = list(range(3817892,3817896))
INSTALL_SHA = '69957de28f72973e05ad285aca0a795f84c3727798b1b58c202426d2900ab051'
HEADER_SHA = '23ff2a8dfd4a3c035cc14faa45bd0074bb9014f58bd4b59ec4171b4973044cc3'
MISC_SHA = 'ad7facb2586fc6e966c004d7d1d16b024f5805ff7cb47c7a85dabd8b48892ca7'
WRITE_BYTES = 10313728
FLAGS = ('allow_exact_six_file_restore','allow_reclaim_four_original_C4_blocks',
         'allow_allocation_bitmap_update','allow_primary_free_count_update',
         'allow_complete_already_applied_journal','allow_verified_preimage_rollback')


class Refused(RuntimeError):
    pass


def need(ok, message):
    if not ok:
        raise Refused(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load(path):
    return json.loads(path.read_text())


def canonical():
    sys.path[:0] = [str(MAIN/'research/tmp/dsh-0175'),
                   str(MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112'),
                   str(MAIN/'tools')]
    from write_root_delta175v2 import RecoveryIO
    from local_hfs175v3 import HFS
    from metal_ca_c5_delta import Remote
    from recovery_marker import READ
    return RecoveryIO,HFS,Remote,READ


def source_pins():
    paths = [Path(__file__),MAIN/'research/tmp/dsh-0175/write_root_delta175v2.py',
             MAIN/'research/tmp/dsh-0175/local_hfs175v3.py',
             MAIN/'research/tmp/gauguin-causal-trace-worktree-20261112/research/tmp/gpu-causal-trace-20261112/metal_ca_c5_delta.py',
             MAIN/'tools/recovery_marker.py',MAIN/'deps/mirror/hfs/core/hfs_journal.c',
             MAIN/'deps/mirror/hfs/core/hfs_journal.h',MAIN/'deps/mirror/hfs/core/hfs_format.h']
    return {str(p):sha(p.read_bytes()) for p in paths}


def identity_gate(io):
    i = io.identity()
    need(i['state']=='recovery' and i['product']=='gauguin' and
         i['partition_bytes']==114919714816 and i['unmounted'] and i['no_holders'],
         'one gauguin recovery/unmounted/no-holder device required')


def checksum(data):
    value = 0
    for byte in data:
        value = ((value << 8) ^ (value+byte)) & 0xffffffff
    return (~value) & 0xffffffff


def journal(raw, info):
    """Strict subset of Apple's replay_journal; refuses unsupported cases.

    block_info bnum uses DEV_BSIZE=512. Latest 512-byte sectors coalesce all
    overlaps. Reject killed entries, missing/zero payload checksums and extra
    valid transactions after end; none occur in the fixed 0337 observation.
    """
    need(struct.unpack_from('>I',info)[0]==1,'only internal initialized journal')
    offset,size = struct.unpack_from('>QQ',info,36)
    need(size==len(raw)==8388608 and offset==12978577408,'journal geometry changed')
    magic,endian,start,end,n,blsize,ck,hsize,sequence = struct.unpack_from('<IIQQQIIII',raw)
    need((magic,endian,n,blsize,hsize)==(0x4a4e4c78,0x12345678,size,94208,512),
         'unsupported journal layout')
    header = bytearray(raw[:44]);header[36:40]=bytes(4)
    need(checksum(header)==ck,'journal header checksum')
    need((start,end,sequence)==(4910592,8338944,12618806),'0337 journal pointers changed')

    def read(at,length):
        need(hsize<=at<size and 0<length<size-hsize,'journal circular read bounds')
        b = raw[at:min(at+length,size)]
        if len(b)<length:
            b += raw[hsize:hsize+length-len(b)]
        need(len(b)==length,'journal circular short read')
        return b

    sectors = {}; transactions = [];at = start;last = None;used_total = 0
    while at != end:
        b = read(at,blsize)
        maximum,count,used,expected,flags = struct.unpack_from('<HHIII',b)
        z = bytearray(b[:32]);z[8:12]=bytes(4)
        seq = struct.unpack_from('<I',b,28)[0]
        need(checksum(z)==expected,'transaction header checksum')
        need(flags==3 and 1<count<=maximum and 16+16*maximum<=blsize,
             'only independently complete checked transaction supported')
        need(last is None or seq==last+1,'transaction sequence order')
        need(blsize<=used<size-hsize,'transaction size')
        pos=at+blsize
        if pos>=size:pos=hsize+pos-size
        total=blsize
        for i in range(1,count):
            number,length,want = struct.unpack_from('<qiI',b,16+i*16)
            need(number>=0 and length>0 and length%512==0 and
                 number*512+length<=VOLUME,'unsupported/killed/outside journal entry')
            payload=read(pos,length)
            need(want!=0 and checksum(payload)==want,'payload checksum missing/invalid')
            need(not (number*512<offset+size and offset<number*512+length),
                 'journal cannot target itself')
            for delta in range(0,length,512):
                sectors[number*512+delta]=payload[delta:delta+512]
            pos+=length
            if pos>=size:pos=hsize+pos-size
            total+=length
        need(total==used,'transaction bytes_used does not match all entries')
        transactions.append(dict(offset=at,sequence=seq,entries=count-1,bytes=used))
        at+=used
        if at>=size:at=hsize+at-size
        need(at==pos,'transaction circular boundary')
        used_total+=used;need(used_total<size-hsize,'transaction cycle')
        last=seq
    # Apple's replay inspects beyond end. Refuse rather than omit valid extra
    # transactions; the fixed snapshot stops here on invalid header checksum.
    extra=bytearray(read(end,32));extra_ck=struct.unpack_from('<I',extra,8)[0]
    extra[8:12]=bytes(4)
    need(checksum(extra)!=extra_ck,'valid extra transaction: new review required')
    need(len(transactions)==17 and sum(t['entries'] for t in transactions)==277 and
         len(sectors)==1048 and last==sequence,'0337 pending transaction set changed')
    target=bytearray(raw[:BLOCK]);struct.pack_into('<Q',target,8,end)
    target[36:40]=bytes(4);struct.pack_into('<I',target,36,checksum(target[:44]))
    need(struct.unpack_from('<QQ',target,8)==(end,end),'journal target not empty')
    return sectors,bytes(target),dict(start=start,end=end,sequence=sequence,
        transactions=transactions,coalesced_sectors=len(sectors),payload_entries=277,
        all_payload_checksums_verified=True,valid_extra_transactions=False)


def attribute_extents(raw):
    """Walk every attribute leaf, including extent-backed attribute records."""
    if not raw:return [],{}
    size=struct.unpack_from('>H',raw,32)[0];at=struct.unpack_from('>I',raw,24)[0]
    need(size in (4096,8192,16384,32768) and len(raw)%size==0,'attribute node geometry')
    seen=set();previous=0;extents=[];counts={}
    while at:
        need(at not in seen and (at+1)*size<=len(raw),'attribute leaf cycle/bounds')
        seen.add(at);b=raw[at*size:(at+1)*size]
        nxt,back,kind,height,count=struct.unpack_from('>IIbBH',b)
        need(kind==-1 and height==1 and back==previous and count<size//4,'attribute leaf')
        for i in range(count):
            lo=struct.unpack_from('>H',b,size-2*(i+1))[0]
            hi=struct.unpack_from('>H',b,size-2*(i+2))[0]
            need(14<=lo<hi<=size-2*(count+1),'attribute record bounds')
            keysize=struct.unpack_from('>H',b,lo)[0];data=lo+2+keysize
            need(keysize>=12 and data+4<=hi,'attribute key bounds')
            typ=struct.unpack_from('>I',b,data)[0];counts[str(typ)]=counts.get(str(typ),0)+1
            need(typ in (0x10,0x20,0x30),'unknown attribute record')
            if typ in (0x20,0x30):
                begin=data+(24 if typ==0x20 else 8)
                need(begin+64<=hi,'attribute extent record bounds')
                for j in range(8):
                    start,n=struct.unpack_from('>II',b,begin+j*8)
                    if n:extents.append((start,n))
                    else:need(start==0,'empty attribute extent start')
        previous=at;at=nxt
    return extents,counts


def make_recipe(io):
    """Derive all preimages/targets afresh; no write operation is called."""
    _,HFS,Remote,READ=canonical();identity_gate(io)
    install_raw=(BASE/'slot-delta/install-plan.json').read_bytes()
    need(sha(install_raw)==INSTALL_SHA,'frozen install plan changed')
    install=json.loads(install_raw);capture=BASE/'slot-capture'
    need(sha((capture/'result.json').read_bytes())==install['capture_sha256'],'original capture changed')
    header=io.read(0,BLOCK);need(sha(header)==HEADER_SHA,'postboot header changed')
    alternate=io.read(VOLUME-BLOCK,BLOCK)
    jib_block=struct.unpack_from('>I',header,1036)[0]
    info=io.read(jib_block*BLOCK,BLOCK)
    offset,size=struct.unpack_from('>QQ',info,36)
    need(offset==12978577408 and size==8388608,'journal bounds changed')
    raw=io.read(offset,size)
    sectors,empty_journal,journal_receipt=journal(raw,info)
    home={}
    for block in sorted({at//BLOCK for at in sectors}):
        b=io.read(block*BLOCK,BLOCK);home[str(block)]=sha(b)
        for at in range(block*BLOCK,(block+1)*BLOCK,512):
            if at in sectors:
                need(b[at-block*BLOCK:at-block*BLOCK+512]==sectors[at],
                     'pending payload not yet at home: replay outside rescue scope')
    journal_receipt['all_131_home_blocks_match']=len(home)==131
    need(len(home)==131,'pending home block set changed')
    h=HFS(stream=Remote(io),size=VOLUME)
    images={};ranges=[];catalog={};file_checks={}

    def add(name,kind,block,current,target,fields=None):
        need(len(current)==len(target)>0 and len(current)%BLOCK==0 and current!=target,
             'empty/unchanged/misaligned rescue range')
        row=dict(name=name,kind=kind,block=block,bytes=len(target),
                 current_sha256=sha(current),target_sha256=sha(target))
        if fields is not None:row['fields']=fields
        ranges.append(row);images[name]=(current,target)

    try:
        bitmap=h.fork_read(h.special['allocation'])
        need(len(bitmap)==h.blocks//8,'allocation bitmap size')
        free=h.blocks-sum(byte.bit_count() for byte in bitmap)
        need(free==struct.unpack_from('>I',header,1072)[0]==404889,'free blocks do not match bitmap')
        need(all(not bitmap[n//8] & (1<<(7-n%8)) for n in TAIL),'original C4 tail reallocated')
        extents=[]
        for file in h.records.values():
            for forkname in ('data','resource'):
                extents+=file.get(forkname,{}).get('extents',[])
        for fork in h.special.values():extents+=fork['extents']
        for overflow in h.extent_records.values():extents+=overflow
        attrraw=h.fork_read(h.special['attributes'])
        attr_extents,attr_counts=attribute_extents(attrraw);extents+=attr_extents
        need(not any(start<=n<start+count for start,count in extents for n in TAIL),
             'C4 original tail has a catalog/resource/special/overflow/attribute owner')
        spans=list(h.spans(h.special['allocation'],TAIL[0]//8,1))
        need(len(spans)==1 and spans[0][1]==1,'bitmap location spans')
        bitblock,bitat=divmod(spans[0][0],BLOCK)
        need((bitblock,bitat)==(117,2100),'bitmap location changed')
        oldbit=io.read(bitblock*BLOCK,BLOCK);newbit=bytearray(oldbit)
        need(TAIL[0]//8==TAIL[-1]//8 and oldbit[bitat]&15==0,'four-bit bitmap geometry')
        newbit[bitat]|=15
        # Journal first: every pending transaction already exists at home.
        # Bitmap before catalog: interruption can leak four blocks, never
        # expose a 105-block fork whose tail is still marked free.
        add('journal-header','journal',offset//BLOCK,raw[:BLOCK],empty_journal)
        add('allocation-bitmap','bitmap',bitblock,oldbit,bytes(newbit),
            [dict(offset=bitat,mask=15,reclaimed_blocks=TAIL)])
        for name,row in install['rows'].items():
            file=h.paths[row['path']];fork=file['data']
            current_blocks=101 if name=='c4' else row['data_blocks']
            need(file['id']==row['cnid'] and file['type']==2 and not file['flags']&0x20 and
                 (file['uid'],file['gid'],file['mode'])==(0,0,row['mode']),'six-file identity changed')
            need(fork['logical']==row['new_logical'] and fork['blocks']==current_blocks and
                 fork['extents']==[[row['data_block'],current_blocks]],'unexpected six-file fork')
            need(sha(h.content(row['path']))==row['new_file_sha256'],'candidate contents changed')
            old=(capture/(name+'-old-data.bin')).read_bytes()
            need(len(old)==row['data_blocks']*BLOCK and sha(old)==row['old_data_sha256'] and
                 sha(old[:row['old_logical']])==row['old_file_sha256'],'original file preimage changed')
            current=io.read(row['data_block']*BLOCK,len(old))
            add(name+'-data','data',row['data_block'],current,old)
            span=list(h.spans(h.catalog,file['catalog_bsd_offset']+56,80))
            need(len(span)==1 and span[0][1]==80,'fork straddles catalog extent')
            catblock,at=divmod(span[0][0],BLOCK)
            need((catblock,at)==(row['catalog_block'],row['catalog_offset']) and at+80<=BLOCK,
                 'catalog fork location changed')
            group=catalog.setdefault(catblock,dict(current=io.read(catblock*BLOCK,BLOCK),fields=[]))
            group['fields'].append(dict(offset=at,bytes=8,value=row['old_logical'],file=name))
            if name=='c4':
                need(fork['clump']==0 and group['current'][at+24:at+80]==bytes(56),
                     'C4 has unexpected clump/extra extents')
                group['fields'] += [dict(offset=at+12,bytes=4,value=105,file=name),
                                    dict(offset=at+20,bytes=4,value=105,file=name)]
            file_checks[name]=dict(path=row['path'],cnid=file['id'],mode=file['mode'],
                current_fork=fork,original_logical=row['old_logical'],original_blocks=row['data_blocks'],
                original_file_sha256=row['old_file_sha256'],original_data_sha256=row['old_data_sha256'])
        for block,group in sorted(catalog.items()):
            current=group['current'];target=bytearray(current);allowed=set()
            for f in group['fields']:
                indexes=set(range(f['offset'],f['offset']+f['bytes']))
                need(not allowed & indexes,'overlapping catalog field edits');allowed|=indexes
                struct.pack_into('>Q' if f['bytes']==8 else '>I',target,f['offset'],f['value'])
            need({i for i,(a,b) in enumerate(zip(current,target)) if a!=b}<=allowed,
                 'unrelated catalog bytes changed')
            add('catalog-'+str(block),'catalog',block,current,bytes(target),group['fields'])
        primary=bytearray(header);struct.pack_into('>I',primary,1072,free-4)
        add('primary-header','primary',0,header,bytes(primary),[dict(offset=1072,bytes=4,value=free-4)])
        guard=dict(primary_sha256=sha(header),alternate_sha256=sha(alternate),
                   journal_info_sha256=sha(info),journal_sha256=sha(raw),home_block_sha256=home,
                   bitmap_sha256=sha(bitmap),catalog_sha256=sha(h.raw),
                   extents_sha256=sha(h.fork_read(h.special['extents'])),attributes_sha256=sha(attrraw),
                   attribute_record_types=attr_counts)
    finally:
        h.close()
    misc=io.run(io.adb+['exec-out',READ]).stdout
    need(len(misc)==BLOCK and sha(misc)==MISC_SHA,'misc is not original: no rescue writes')
    need(io.read(0,BLOCK)==header and io.read(offset,BLOCK)==raw[:BLOCK],
         'metadata changed during read-only preparation')
    intervals=sorted((r['block']*BLOCK,r['block']*BLOCK+r['bytes']) for r in ranges)
    need(all(a[1]<=b[0] for a,b in zip(intervals,intervals[1:])),'overlapping rescue writes')
    need(len(ranges)==14 and sum(r['bytes'] for r in ranges)==WRITE_BYTES,
         'rescue range/byte bound changed')
    result=dict(state='prepared-exact-0337-trim-rescue',install_plan_sha256=INSTALL_SHA,
        original_capture_sha256=install['capture_sha256'],source_pins=source_pins(),
        guard=guard,journal=journal_receipt,files=file_checks,ranges=ranges,
        reclaimed_blocks=TAIL,free_blocks_before=404889,free_blocks_after=404885,
        forward_write_bytes=WRITE_BYTES,including_failure_rollback_max_bytes=WRITE_BYTES*2,
        write_ranges=14,device_writes=0,device_boots=0,misc_original=True,
        alternate_header_unchanged=True,primary_attributes_unchanged=True,
        no_replay_writes_needed=True,no_retry=True)
    return result,images


def read_plan(folder):
    need(folder.resolve().is_relative_to(BASE),'rescue plan outside private state')
    raw=(folder/'rescue-plan.json').read_bytes();plan=json.loads(raw)
    need(plan['state']=='prepared-exact-0337-trim-rescue' and plan['source_pins']==source_pins(),
         'wrong rescue plan/source')
    images={}
    for row in plan['ranges']:
        name=row['name'];need('/' not in name and '..' not in name,'range filename')
        current=(folder/(name+'-current.bin')).read_bytes()
        target=(folder/(name+'-target.bin')).read_bytes()
        need(len(current)==len(target)==row['bytes'] and sha(current)==row['current_sha256'] and
             sha(target)==row['target_sha256'],'rescue local images changed')
        images[name]=(current,target)
    need(len(images)==len(plan['ranges'])==14 and
         sum(r['bytes'] for r in plan['ranges'])==WRITE_BYTES,'rescue limits')
    return raw,plan,images


def approval_gate(approval,plan_sha,review_sha):
    need(approval.get('approved') is True and approval.get('plan_sha256')==plan_sha and
         approval.get('review_sha256')==review_sha and approval.get('source')=='actual-user-q337-trim-rescue-reply' and
         approval.get('provenance')=='async-question-reply' and
         approval.get('question_item_id') and approval.get('exact_answer') and
         approval.get('answer_sha256')==sha(approval['exact_answer'].encode()) and
         all(approval.get(k) is True for k in FLAGS) and
         not approval.get('fixture_only',False),'new exact actual rescue approval required')


def apply_ranges(plan,images,io,report,verify):
    """Includes partially written range in rollback; never retries a forward run.

    If any other rollback fails, leave the already-empty journal in place and
    report it. Never re-enable a stale replay over a partially rolled back FS.
    """
    touched=[];failures=[];forward=rollback=0
    try:
        for row in plan['ranges']:
            current,target=images[row['name']]
            need(io.read(row['block']*BLOCK,row['bytes'])==current,'range changed immediately before write')
            touched.append(row);forward+=row['bytes']
            io.write(row['block']*BLOCK,target);io.sync()
            need(io.read(row['block']*BLOCK,row['bytes'])==target,'target readback differs')
            report(dict(state='rescue-applying',completed_ranges=len(touched),last=row['name'],forward_bytes=forward))
        verify()
        result=dict(state='0337-six-files-and-original-C4-allocation-restored',
                    forward_bytes=forward,rollback_bytes=0,verified_ranges=len(touched),reboot_permitted=False)
        report(result)
        return result
    except (Exception,KeyboardInterrupt) as error:
        for row in reversed(touched):
            if row['kind']=='journal' and failures:
                failures.append(dict(name=row['name'],error='kept empty because other rollback failed'))
                continue
            current,_target=images[row['name']]
            try:
                rollback+=row['bytes'];io.write(row['block']*BLOCK,current);io.sync()
                need(io.read(row['block']*BLOCK,row['bytes'])==current,'rollback readback differs')
            except (Exception,KeyboardInterrupt) as problem:
                failures.append(dict(name=row['name'],error=repr(problem)))
        result=dict(state='rescue-failed-preimages-restored' if not failures else 'rescue-failed-rollback-incomplete',
                    error=repr(error),forward_bytes=forward,rollback_bytes=rollback,
                    rollback_failures=failures,reboot_permitted=False)
        try:report(result)
        except Exception as problem:result['report_error']=repr(problem)
        return result


def verify_restored(plan,images,io):
    _,HFS,Remote,READ=canonical();identity_gate(io)
    for row in plan['ranges']:
        need(io.read(row['block']*BLOCK,row['bytes'])==images[row['name']][1],'final range mismatch')
    need(sha(io.read(VOLUME-BLOCK,BLOCK))==plan['guard']['alternate_sha256'],'alternate header changed')
    h=HFS(stream=Remote(io),size=VOLUME)
    try:
        install=load(BASE/'slot-delta/install-plan.json')
        for row in install['rows'].values():
            f=h.paths[row['path']];d=f['data']
            need(f['id']==row['cnid'] and f['type']==2 and not f['flags']&0x20 and
                 (f['uid'],f['gid'],f['mode'])==(0,0,row['mode']),'restored six-file identity')
            need(d['logical']==row['old_logical'] and d['blocks']==row['data_blocks'] and
                 d['extents']==[[row['data_block'],row['data_blocks']]],'restored original fork')
            need(sha(h.content(row['path']))==row['old_file_sha256'] and
                 sha(io.read(row['data_block']*BLOCK,row['data_blocks']*BLOCK))==row['old_data_sha256'],
                 'restored original logical/allocated contents')
        bitmap=h.fork_read(h.special['allocation'])
        need(h.blocks-sum(b.bit_count() for b in bitmap)==struct.unpack_from('>I',h.header,48)[0]==404885,
             'restored free count')
        need(all(bitmap[n//8] & (1<<(7-n%8)) for n in TAIL),'restored C4 tail allocation')
    finally:h.close()
    misc=io.run(io.adb+['exec-out',READ]).stdout
    need(len(misc)==BLOCK and sha(misc)==MISC_SHA,'misc changed during rescue')


def save(path,value):
    with path.open('x') as f:
        json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())


def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('execute');p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--approval',type=Path,required=True);p.add_argument('--review',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    need(args.out.resolve().is_relative_to(BASE) and not args.out.exists(),'new private output required')
    if args.command=='prepare':
        RecoveryIO,*_=canonical();plan,images=make_recipe(RecoveryIO())
        args.out.mkdir()
        for name,pair in images.items():
            for suffix,data in zip(('current','target'),pair):
                with (args.out/(name+'-'+suffix+'.bin')).open('xb') as f:f.write(data)
        save(args.out/'rescue-plan.json',plan)
        print(json.dumps({k:v for k,v in plan.items() if k not in ('source_pins','guard','files','ranges','journal')},indent=2))
        return
    # All authorization and local review checks precede any ADB or claim.
    raw,plan,images=read_plan(args.plan)
    review_raw=args.review.read_bytes();review=json.loads(review_raw)
    need(review['state']=='reviewed-0337-trim-rescue' and review['plan_sha256']==sha(raw) and
         review['model_passed'] and review['independent_metadata_review_passed'],'rescue review missing')
    need(all(sha(Path(p).read_bytes())==expected for p,expected in review['input_pins'].items()),
         'independent review inputs changed')
    approval_raw=args.approval.read_bytes();approval=json.loads(approval_raw)
    approval_gate(approval,sha(raw),sha(review_raw))
    claim=args.plan/'execute-claim.json'
    save(claim,dict(pid=os.getpid(),time=time.time(),plan_sha256=sha(raw),approval_sha256=sha(approval_raw)))
    args.out.mkdir()
    try:
        RecoveryIO,*_=canonical();io=RecoveryIO()
        # Full deterministic re-derivation catches a changed journal, owner,
        # bitmap, catalog, file or range before the FIRST mutation.
        fresh,fresh_images=make_recipe(io)
        need(fresh==plan and fresh_images==images,'device/preimages changed since frozen rescue')
    except (Exception,KeyboardInterrupt) as error:
        result=dict(state='rescue-refused-before-write',error=repr(error),device_writes=0,
                    device_boots=0,plan_sha256=sha(raw),reboot_permitted=False)
        save(args.out/'result.json',result)
        print(json.dumps(result,indent=2));raise SystemExit(1)
    def report(value):
        with (args.out/'progress.jsonl').open('a') as f:
            f.write(json.dumps(value)+'\n');f.flush();os.fsync(f.fileno())
    result=apply_ranges(plan,images,io,report,lambda:verify_restored(plan,images,io))
    result.update(plan_sha256=sha(raw),approval_sha256=sha(approval_raw),review_sha256=sha(review_raw),
                  device_boots=0,misc_writes=0,alternate_writes=0)
    save(args.out/'result.json',result)
    print(json.dumps(result,indent=2))
    if result['state']!='0337-six-files-and-original-C4-allocation-restored':raise SystemExit(1)


if __name__=='__main__':main()
