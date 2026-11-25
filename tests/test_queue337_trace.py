#!/usr/bin/env python3
"""Exercise the production queue metadata log cap and worst-case row size."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess

def main():
    w=Path(__file__).resolve().parents[1]
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    out=ap.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=False)
    source=w/'tests/fixtures/queue337_trace_host.c';header=w/'graphics/gauguin-c4-queue/GauguinQueue337.h'
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    pins={str(p):sha(p)for p in (source,header,Path(__file__))}
    command=['clang','-std=c11','-Wall','-Wextra','-Werror','-pedantic','-O1','-g',
             '-fsanitize=address,undefined','-pthread','-I'+str(header.parent),str(source),'-o',str(out/'check')]
    with (out/'compile.log').open('x')as f:subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
    with (out/'trace.log').open('x')as f:r=subprocess.run([str(out/'check')],stdout=subprocess.PIPE,stderr=f,text=True,timeout=30)
    assert r.returncode==0
    rows=(out/'trace.log').read_text().splitlines(keepends=True);marker='GAUGUIN Q337: limit=32768 coverage=incomplete\n'
    assert len(rows)==32769 and rows.count(marker)==1 and max(len(r.encode())for r in rows)<=192
    pattern=r'GAUGUIN Q337: stage=[0-2] object=0x[0-9a-f]+ made_us=\d+ queue=\d+ ticket=\d+ retired=\d+ tick_us=\d+\n'
    assert all(row==marker or re.fullmatch(pattern,row)for row in rows)
    assert all(sha(Path(p))==h for p,h in pins.items())
    result=dict(state='Q337-production-logger-bounds-concurrent-cap-passed',input_pins=pins,
                max_line_bytes=max(map(len,rows)),rows=32768,markers=1,maximum_trace_bytes=32769*192,
                inputs_unchanged=True,device_commands=0,stdout=r.stdout.strip())
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(result['state'])
if __name__=='__main__':main()
