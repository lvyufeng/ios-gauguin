#!/usr/bin/env python3
"""Exercise malformed VM replies and confirm failure diagnostics skip hashing."""
import hashlib,json,subprocess
from pathlib import Path
WORK=Path(__file__).resolve().parents[1]
out=WORK/'research/tmp/edr-once-320/region-host-v1';out.mkdir(exist_ok=False)
source=WORK/'tests/fixtures/edr_region_bounds.c'
argv=['xcrun','clang','-std=gnu11','-O1','-g','-fblocks','-Wall','-Wextra','-Werror',
      '-fsanitize=address,undefined',str(source),'-o',str(out/'check')]
with(out/'compile.log').open('x')as f:subprocess.run(argv,stdout=f,stderr=subprocess.STDOUT,check=True)
run=subprocess.run([str(out/'check')],capture_output=True,text=True,timeout=30)
(out/'stdout.log').write_text(run.stdout);(out/'stderr.log').write_text(run.stderr)
assert run.returncode==0,run.stderr
assert run.stderr=='GAUGUIN EDR320: code-check name=initializer region=0 kr=0 count=12 depth=1 protection=5 hashed=0 hash=0 sha256='+64*'0'+'\n'
result=json.loads(run.stdout);assert result['checks']==20 and result['rpc_calls']==17
files=[Path(__file__).resolve(),source,*sorted((WORK/'graphics/gauguin-edr-default').glob('*'))]
result.update(input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files},
    invalid_mapping_never_hashed=True,compiler_argv=argv)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
