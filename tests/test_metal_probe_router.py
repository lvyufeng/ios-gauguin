#!/usr/bin/env python3
"""Execute production routing/hash/SETEXEC code using typed privilege/spawn seams."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    r=Path(__file__).resolve().parents[1];out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    payloads=[b'qualified retained probe fixture 247\n',b'qualified bootstrap fixture 247\n']
    paths=[out/'retained-executable',out/'bootstrap-executable']
    header=['#include <stdint.h>','struct gauguin_router_target {const char *path,*argument;uint64_t bytes;unsigned char sha256[32];};']
    for kind,path,payload,arg in zip(['retained','bootstrap'],paths,payloads,['--metal230','--bootstrap245']):
        digest=hashlib.sha256(payload).digest();values=','.join(str(b)for b in digest)
        header.append('static const struct gauguin_router_target gauguin_router_'+kind+'={'+json.dumps(str(path))+','+json.dumps(arg)+','+str(len(payload))+',{'+values+'}};')
    (out/'GauguinProbeRouterTargets.h').write_text('\n'.join(header)+'\n')
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1')
    common=['xcrun','clang','-std=gnu11','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
            '-I'+str(out),'-I'+str(r/'graphics/hakios-metal-ca/overlay/userland/src'),'-I'+str(r/'graphics/hakios-metal-ca/desktop-overlay/userland/src')]
    aliases=['main=gauguin_router_main','getuid=router_getuid','geteuid=router_geteuid','getprogname=router_getprogname',
             'sysctlbyname=router_sysctl','fstat=router_fstat','memorystatus_control=router_mem','posix_spawn=router_spawn','posix_spawnattr_setjetsam_ext=router_jetsam']
    def run(args,name):
        with(out/(name+'.log')).open('x')as f:subprocess.run(list(map(str,args)),env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    run(common+['-D'+x for x in aliases]+['-DGAUGUIN_ROUTER_BUILD="host-model"','-c',r/'userland/metal/probe_router.c','-o',out/'router.o'],'compile-router')
    undefined=subprocess.check_output(['xcrun','nm','-u',str(out/'router.o')],text=True)
    assert '_router_spawn'in undefined and not any(line.split()[-1]=='_posix_spawn'for line in undefined.splitlines())
    run(common+[out/'router.o',r/'tests/fixtures/metal_probe_router_host.c','-o',out/'router-host'],'link-host')
    cases=['diag','legacy','desktop','mode-prefix','mode-duplicate','mode-conflict','mode-one-two','mode-empty',
           'uid','euid','program','version','arguments','target-owner','target-group','target-mode','target-link','target-size',
           'target-hash','target-symlink','target-changed','memory-active','memory-inactive','memory-fatal','priority','priority-pid',
           'spawn-jetsam','spawn-error','spawn-return']
    for case in cases:
        for path,payload in zip(paths,payloads):
            if path.is_symlink():path.unlink()
            path.write_bytes(payload);path.chmod(0o755)
        run([out/'router-host',case],case)
    print(f'{len(cases)} actual router/file/hash/attribute cases passed; modeled credentials and SETEXEC; no process replaced')
if __name__=='__main__':main()
