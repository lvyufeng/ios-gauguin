"""Read-only HFS helpers for 0342's bounded completed-journal/tail policy."""
from pathlib import Path
import hashlib
import importlib.util
import struct

BLOCK=4096
VOLUME=17179869184


def require(ok,why):
    if not ok:raise ValueError(why)


def sha(data):return hashlib.sha256(data).hexdigest()


def checksum(data):
    value=0
    for byte in data:value=((value<<8)^(value+byte))&0xffffffff
    return (~value)&0xffffffff


def inspect_journal(io,header,require_empty=False):
    require(header[1024:1028]==b'HX\x00\x05','HFSX version')
    jib=struct.unpack_from('>I',header,1036)[0]
    require(jib==3170646,'journal info moved')
    info=io.read(jib*BLOCK,BLOCK);flags=struct.unpack_from('>I',info)[0]
    offset,size=struct.unpack_from('>QQ',info,36)
    require(flags==1 and (offset,size)==(12978577408,8388608),'journal geometry changed')
    raw=io.read(offset,size)
    magic,endian,start,end,total,blsize,ck,hsize,sequence=struct.unpack_from('<IIQQQIIII',raw)
    require((magic,endian,total,blsize,hsize)==(0x4a4e4c78,0x12345678,size,94208,512),'journal layout')
    check=bytearray(raw[:44]);check[36:40]=bytes(4)
    require(checksum(check)==ck,'journal header checksum')
    require(all(hsize<=at<=size and at%hsize==0 for at in (start,end)),'journal pointer bounds')
    normalize=lambda at:hsize if at==size else at
    at,stop=normalize(start),normalize(end);sectors={};chunks=[];used_total=0;last=None
    require(not require_empty or at==stop,'pre-install journal is not empty')
    def read(position,length):
        require(hsize<=position<size and 0<length<size-hsize,'journal circular bounds')
        data=raw[position:min(position+length,size)]
        if len(data)<length:data+=raw[hsize:hsize+length-len(data)]
        require(len(data)==length,'journal short circular read');return data
    while at!=stop:
        body=read(at,blsize);maximum,count,used,want,flags=struct.unpack_from('<HHIII',body)
        check=bytearray(body[:32]);check[8:12]=bytes(4)
        seq=struct.unpack_from('<I',body,28)[0]
        require(checksum(check)==want,'journal transaction header checksum')
        require(flags in (1,3) and 1<count<=maximum and 16+16*maximum<=blsize and
                blsize<=used<size-hsize,'journal transaction shape')
        require(seq>0 and ((last is None and flags==3) or (last is not None and
                ((seq==last and flags==1) or (seq==last+1 and flags==3)))),'journal sequence/transaction boundary')
        position=at+blsize
        if position>=size:position=hsize+position-size
        consumed=blsize
        for i in range(1,count):
            number,length,expected=struct.unpack_from('<qiI',body,16+i*16)
            require(number>=-1 and length>0 and length%512==0,'journal block shape')
            payload=read(position,length)
            require(expected!=0 and checksum(payload)==expected,'journal payload checksum absent/invalid')
            if number!=-1:
                physical=number*512
                require(0<=physical<physical+length<=VOLUME and not
                        (physical<offset+size and offset<physical+length),'journal targets invalid/self range')
                for j in range(0,length,512):sectors[physical+j]=payload[j:j+512]
            position+=length
            if position>=size:position=hsize+position-size
            consumed+=length
        require(consumed==used,'journal bytes_used differs')
        chunks.append(dict(offset=at,sequence=seq,entries=count-1,bytes=used,flags=flags))
        at+=used
        if at>=size:at=hsize+at-size
        require(at==position,'journal circular boundary differs')
        used_total+=used;require(used_total<size-hsize,'journal cycle')
        last=seq
    if chunks:
        # Apple's replay also examines beyond declared end. Do not silently
        # omit a valid extra transaction; that requires a separate review.
        extra=bytearray(read(stop,32));want=struct.unpack_from('<I',extra,8)[0];extra[8:12]=bytes(4)
        require(checksum(extra)!=want,'valid extra transaction after declared journal end')
    homes={}
    for block in sorted({position//BLOCK for position in sectors}):
        current=io.read(block*BLOCK,BLOCK);homes[str(block)]=sha(current)
        for position in range(block*BLOCK,(block+1)*BLOCK,512):
            if position in sectors:
                begin=position-block*BLOCK
                require(current[begin:begin+512]==sectors[position],
                        'unapplied journal sector: replay is outside automatic0342 restore policy')
    target=bytearray(raw[:BLOCK]);struct.pack_into('<Q',target,8,end)
    target[36:40]=bytes(4);struct.pack_into('<I',target,36,checksum(target[:44]))
    result=dict(state='verified-empty-or-fully-applied-journal',info_block=jib,offset=offset,size=size,
        start=start,end=end,sequence=sequence,chunks=chunks,coalesced_sectors=len(sectors),home_block_sha256=homes,
        info_sha256=sha(info),journal_sha256=sha(raw),pending_home_sectors_all_match=True,
        physical_replay_writes=0,journal_header_change=bytes(target)!=raw[:BLOCK])
    return result,raw[:BLOCK],bytes(target),info,raw


def attribute_extents(raw):
    # Reuse the packed-format attribute leaf walker already independently
    # reviewed for0337. Importing the module has no device operation.
    path=Path(__file__).with_name('restore-queue337-trim.py')
    spec=importlib.util.spec_from_file_location('attribute_reader340',path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value.attribute_extents(raw)
