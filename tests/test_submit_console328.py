#!/usr/bin/env python3
"""Run actual old/new rejection loggers through the actual XNU console buffer."""
from pathlib import Path
import hashlib
import json
import os
import subprocess

W = Path(__file__).resolve().parents[1]
B = W/'research/tmp/gesture-sample-328'
P = Path('/Users/baai/Project/ios-gauguin/research/tmp/gauguin-submit-reject-worktree-20261115/research/tmp/submit-reject-327')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    out = B/'console-host-v1'
    out.mkdir(exist_ok=False)
    manifest = json.loads((P/'local-link/build-manifest.json').read_text())
    base = Path(manifest['source_union']['base'])
    header = base/'osfmk/console/serial_protos.h'
    serial = base/'osfmk/console/serial_general.c'
    old = P/'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp'
    new = B/'kernel-source/iokit/Kernel/arm/GauguinGPU.cpp'
    paths = [Path(__file__),P/'local-link/build-manifest.json',header,serial,old,new,
             B/'kernel-source/bsd/dev/gauguin_gpu_runtime.h']
    pins = {str(path):sha(path) for path in paths}
    for path in (header,serial):
        assert sha(path) == manifest['input_pins'][str(path)]['sha256']
    raw = serial.read_text()
    functions = ''
    for name in ('console_printbuf_state_init','console_printbuf_putc','console_printbuf_clear'):
        start = raw.index('void\n'+name+'(')
        end = raw.index('\n}\n',start)+3
        functions += raw[start:end]+'\n'
    raw = header.read_text()
    struct = raw[raw.index('#define SERIAL_CONS_BUF_SIZE'):raw.index('extern int console_printbuf_drain_initialized;')]
    assert '#define SERIALMODE_SYNCDRAIN 0x04' in raw
    prelude = r'''
#include <cassert>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include "gauguin_gpu_runtime.h"
using IOReturn=int;
constexpr int kIOReturnSuccess=0;
static int serialmode;
#define SERIALMODE_SYNCDRAIN 0x04
static std::string wire;
static void console_write(char *text,int size){assert(size>=0);wire.append(text,size);}
'''
    log = r'''
static unsigned calls,clock_reads;
static int last_formatted_bytes;
static uint64_t clock_tick=5000000000ULL;
static uint64_t mach_absolute_time(){++clock_reads;return clock_tick;}
static void IOLog(const char *format,...){
 char raw[2048];va_list args;va_start(args,format);
 int n=vsnprintf(raw,sizeof(raw),format,args);va_end(args);
 assert(n>0&&n<(int)sizeof(raw));++calls;last_formatted_bytes=n;
 console_printbuf_state state;console_printbuf_state_init(&state,1,1);
 for(int i=0;i<n;i++)console_printbuf_putc(raw[i],&state);
 console_printbuf_clear(&state);
}
'''
    cases = r'''
static unsigned checks;
#define CHECK(x) do{++checks;assert(x);}while(0)
static void reset(){wire.clear();calls=clock_reads=0;gsub_diag327_count=0;}
int main(){
 struct ggr_submit r={};gsub_diag327 d={10,UINT32_MAX,0,0,0,0,0,0,0,0};
 r.flags=0x10;r.nr_bos=12;r.nr_cmds=1;r.queueid=1;
 reset();
 gsub_diag327_log(&d,&r,0,true,true,7,0,839,91340800);
 gsub_diag327_log(&d,&r,1,false,true,7,0,839,91340800);
 gsub_diag327_log(&d,&r,1,true,false,7,0,839,91340800);
 CHECK(wire.empty()&&calls==0&&clock_reads==0&&gsub_diag327_count==0);
 gsub_diag327_log(&d,&r,1,true,true,7,0,839,91340800);
#ifdef CONSOLE328
 CHECK(wire.size()==235&&wire.back()=='\n'&&last_formatted_bytes==235);
#else
 CHECK(wire.size()==255&&wire.back()!='\n'&&last_formatted_bytes>255);
#endif
 reset();clock_tick=UINT64_MAX;
 d={10,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX,UINT32_MAX};
 std::memset(&r,0xff,sizeof(r));
 gsub_diag327_log(&d,&r,INT32_MIN,true,true,UINT64_MAX,UINT32_MAX,UINT32_MAX,UINT64_MAX);
#ifdef CONSOLE328
 CHECK(wire.size()==235&&wire.back()=='\n'&&last_formatted_bytes==235);
 CHECK(wire.find("ffffffffffffffff")!=std::string::npos);
#else
 CHECK(wire.size()==255&&wire.back()!='\n'&&last_formatted_bytes>255);
#endif
 reset();
 for(unsigned i=0;i<80;i++){clock_tick=5000000000ULL+i;gsub_diag327_log(&d,&r,1,true,true,i+1,0,0,0);}
 CHECK(calls==65&&clock_reads==64&&gsub_diag327_count==65);
#ifdef CONSOLE328
 CHECK(wire.size()==64*235+strlen("SWEET GS328: limit=64 coverage=incomplete\n"));
 unsigned newlines=0;for(char c:wire)if(c=='\n')++newlines;CHECK(newlines==65);
#else
 CHECK(wire.size()==64*255+strlen("SWEET GPU SUBMIT327: limit=64 coverage=incomplete\n"));
#endif
 size_t before=wire.size();gsub_diag327_count=UINT32_MAX;
 gsub_diag327_log(&d,&r,1,true,true,7,0,0,0);CHECK(wire.size()==before&&calls==65);
 // The actual transport boundary is255 bytes including newline. Test exact
 // boundary, overflow and synchronous-drain behavior independently of logger.
 for(unsigned n=254;n<=256;n++){
  wire.clear();std::string row(n-1,'x');row+='\n';IOLog("%s",row.c_str());
  CHECK(wire.size()==(n<=255?n:255));CHECK((wire.back()=='\n')==(n<=255));
 }
 serialmode=SERIALMODE_SYNCDRAIN;wire.clear();std::string longrow(600,'x');longrow+='\n';IOLog("%s",longrow.c_str());CHECK(wire==longrow);
 printf("{\"checks\":%u,\"old_truncation_reproduced\":%s,\"candidate_full_rows\":%s}\n",checks,
#ifdef CONSOLE328
 "false","true"
#else
 "true","false"
#endif
 );
}
'''
    env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1')
    results={}
    for variant,path in (('baseline',old),('candidate',new)):
        text=path.read_text()
        a=text.index('/* SUBMIT327:' if variant=='baseline' else '/* SUBMIT328:')
        z=text.index('class GauguinGPUUserClient',a)
        unit=out/(variant+'.cpp')
        unit.write_text(prelude+struct+functions+log+text[a:z]+cases)
        command=['clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(B/'kernel-source/bsd/dev')]
        if variant=='candidate':command+=['-DCONSOLE328=1']
        command += [str(unit),'-o',str(out/variant)]
        with (out/(variant+'-compile.log')).open('x') as stream:
            compiled=subprocess.run(command,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
        assert compiled.returncode==0,variant
        run=subprocess.run([str(out/variant)],env=env,capture_output=True,text=True,timeout=60)
        (out/(variant+'-run.log')).write_text(run.stdout+run.stderr)
        assert run.returncode==0 and not run.stderr,variant
        results[variant]=json.loads(run.stdout)
    # Outside the log block only the format's comment changed. All submission,
    # dispatch, ownership and GPU operations remain byte-identical to327.
    def without_diagnostic(path,label):
        text=path.read_text();a=text.index(label);z=text.index('class GauguinGPUUserClient',a)
        return text[:a]+text[z:]
    assert without_diagnostic(old,'/* SUBMIT327:')==without_diagnostic(new,'/* SUBMIT328:')
    assert all(sha(path)==digest for path,digest in pins.items())
    result=dict(state='GESTURE328-actual-XNU-console-truncation-reproduced-and-fixed',
        results=results,actual_console_functions=3,serial_buffer_bytes=256,serial_payload_bytes=255,
        candidate_record_bytes=235,all_64_rows_and_limit_marker_complete=True,scope_and_rate_bound_preserved=True,
        submission_and_dispatch_bodies_identical=True,sanitizers='ASan+UBSan',input_pins=pins,inputs_unchanged=True,device_commands=0)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__=='__main__':
    main()
