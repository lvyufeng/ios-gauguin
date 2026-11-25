#!/usr/bin/env python3
"""Run the production explicit loader with checked host entry points."""
from pathlib import Path
import argparse,hashlib,json,subprocess
WORK=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 out=a.out.resolve();assert out.is_relative_to(WORK/'research/tmp')and not out.exists();out.mkdir(parents=True)
 src=WORK/'tests/fixtures/edr_loader_host.c';header=WORK/'graphics/gauguin-edr-loader/GauguinEDRLoader.h'
 pins={str(p):sha(p)for p in (src,header,Path(__file__).resolve())}
 argv=['xcrun','clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(src),'-o',str(out/'check')]
 r=subprocess.run(argv,capture_output=True,text=True);(out/'compile.log').write_text(r.stdout+r.stderr);assert r.returncode==0
 r=subprocess.run([str(out/'check')],capture_output=True,text=True,timeout=30)
 (out/'stdout.log').write_text(r.stdout);(out/'stderr.log').write_text(r.stderr);assert r.returncode==0
 assert all(line.startswith('GAUGUIN EDR318 LOADER: ')for line in r.stderr.splitlines())
 assert r.stderr.count('result=opened')==1 and r.stderr.count('result=failed')==1 and r.stderr.count('refused=scope')==7
 result=json.loads(r.stdout);assert result['cases']==9 and result['concurrent_calls']==16000
 result.update(input_pins=pins,compiler_argv=argv,iOS_loader_qualified=False,expected_loader_log_lines=len(r.stderr.splitlines()))
 assert all(sha(Path(p))==v for p,v in pins.items())
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
