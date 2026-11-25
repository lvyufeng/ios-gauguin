"""Compile production once handling against the real host dispatch runtime."""
from pathlib import Path
import hashlib,json,re,subprocess
WORK=Path(__file__).resolve().parents[1]
out=WORK/'research/tmp/edr-once-320/once-host-v1';out.mkdir(exist_ok=False)
source=WORK/'tests/fixtures/edr_once_host.c'
args=['xcrun','clang','-std=gnu11','-O1','-g','-fblocks','-Wall','-Wextra','-Werror',
      '-fsanitize=address,undefined',str(source),'-o',str(out/'check')]
with(out/'compile.log').open('x')as f:subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,check=True)
run=subprocess.run([str(out/'check')],capture_output=True,text=True,timeout=30)
(out/'stdout.log').write_text(run.stdout);(out/'stderr.log').write_text(run.stderr)
assert run.returncode==0,run.stderr
lines=run.stderr.splitlines()
assert len(lines)==259 and sum('eligible=0'in line for line in lines)==1
assert all(re.fullmatch(r'GAUGUIN EDR320: once (?:before=0x[0-9a-f]{16} eligible=[01]|after=0x[0-9a-f]{16} complete=1)',line)for line in lines)
result=json.loads(run.stdout);assert result['generation_returns']>0 and result['occupied_initializer_refused']
files=[Path(__file__).resolve(),source,*sorted((WORK/'graphics/gauguin-edr-default').glob('*'))]
result.update(input_pins={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in files},
    production_log_rows=len(lines),sanitizer_errors=False,compiler_argv=args,iOS_runtime_qualified=False)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
