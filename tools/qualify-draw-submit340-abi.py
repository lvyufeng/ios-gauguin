#!/usr/bin/env python3
"""Resolve candidate frontend imports against actual20H392 and owned core."""
from pathlib import Path
import argparse
import ast
import bisect
import hashlib
import json
import plistlib
import struct
import sys

MAIN=Path('/Users/baai/Project/ios-gauguin')
WORK=Path(__file__).resolve().parents[1]
BASE=WORK/'research/tmp/draw-submit-340'


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def load(p):return json.loads(Path(p).read_text())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve();assert out.is_relative_to(BASE) and not out.exists()
    sb=MAIN/'research/tmp/gauguin-sb-stack-worktree-20261114/research/tmp/sb-stack-315'
    original=sb/'qualify_stack_abi.py';old=load(sb/'abi-v3/result.json')
    assert sha(original)==old['script_sha256']
    backup=load(MAIN/'research/tmp/metal-hardware-20261112/backup/result.json')
    image=Path(backup['backup']);assert sha(image)==backup['backup_sha256']
    native=load(BASE/'native-v2/result.json');frontend=load(BASE/'frontend-native-v1/result.json')
    core=Path(native['products']['candidate']['binary']);probe=Path(frontend['products']['candidate']['binary'])
    assert sha(core)==native['products']['candidate']['sha256'] and sha(probe)==frontend['products']['candidate']['sha256']
    sys.path.insert(0,str(MAIN/'research/tmp/dsh-0175'))
    from local_hfs175v3 import HFS
    h=HFS(image)
    try:
        assert plistlib.loads(h.content('/System/Library/CoreServices/SystemVersion.plist'))['ProductBuildVersion']=='20H392'
        inventory=load(MAIN/'research/tmp/dsh-gles-ui-0183/offline-resolved-cache-inventory.json')
        s=original.read_text();fragment=s[s.index('def forkread'):s.index('probe=Path')]
        # Pinned established read-only HFS cache mapper and export-trie resolver;
        # omit the old script's top-level output creation and observer probe.
        namespace=dict(h=h,inventory=inventory,struct=struct,bisect=bisect,hashlib=hashlib)
        exec(compile(ast.parse(fragment),str(original),'exec'),namespace)
        data=core.read_bytes();size=struct.unpack_from('<I',data,20)[0]
        commands=namespace['commands'](data[:32],data[32:32+size])
        at,n=namespace['export_span'](commands);trie=data[at:at+n];assert len(trie)==n
        parsed=namespace['native'](probe);rows=[];missing=[]
        for item in parsed['imports']:
            if item['provider']=='@rpath/libGauguinMetalCore.dylib':
                found=namespace['lookup'](trie,item['symbol'])
                answer=dict(provider=item['provider'],symbol=item['symbol'],export=found) if found else None
            elif item['provider']=='disabled-optional-M2V-hook':
                assert item['weak'];answer=dict(disabled_weak_hook=True)
            else:answer=namespace['resolve'](item['provider'],item['symbol'])
            row=dict(**item,resolved=bool(answer),resolution=answer);rows.append(row)
            if not answer:missing.append(row)
        assert not missing,missing
        paths=[Path(__file__),original,sb/'abi-v3/result.json',image,core,probe,
               BASE/'native-v2/result.json',BASE/'frontend-native-v1/result.json',
               MAIN/'research/tmp/dsh-gles-ui-0183/offline-resolved-cache-inventory.json']
        result=dict(state='0340-all-frontend-imports-resolved-actual20H392-and-owned-core',
            OS_build='20H392',cache_images=len(namespace['images']),cache_shards=namespace['shards'],
            checked_imports=len(rows),missing_imports=[],imports=rows,core_imports_unchanged=True,
            optional_hooks_remain_disabled=True,input_pins={str(p):sha(p) for p in paths},
            device_commands=0,runtime_behavior_qualified=False,physical_FPS_qualified=False)
        out.mkdir()
        with (out/'result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        print(json.dumps({k:v for k,v in result.items() if k not in ('input_pins','cache_shards','imports')},indent=2))
    finally:h.close()


if __name__=='__main__':main()
