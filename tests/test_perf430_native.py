#!/usr/bin/env python3
"""Compare actual default/430 port stores with the pinned native driver functions."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/perf430-326';OLD=MAIN/'research/tmp/dsh-0143'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def function(s,name):
 m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:void|bool|int)\s+'+name+r'\(',s,re.M);assert m,name
 return s[m.start():s.index('\n}\n',m.start())+3]
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);out=ap.parse_args().out.resolve()
 assert out.is_relative_to(STATE) and not out.exists()
 proof=OLD/'native-oracle-v3/result.json';old=json.loads(proof.read_text())
 assert old['state']=='passed' and old['inputs_unchanged'] and old['compile_exit']==old['run_exit']==0
 pins={str(MAIN/n):d for n,d in old['input_pins'].items()}
 for n,d in pins.items():assert sha(n)==d,n
 native=(OLD/'native-oracle-v3/oracle.c').read_text()
 sources={'kgsl_gmu_core.c':['gmu_core_is_register_offset','gmu_core_regread','gmu_core_regwrite'],
          'adreno_a6xx_gmu.c':['a6xx_gmu_oob_set','a6xx_gmu_oob_clear','a6xx_gmu_dcvs_nohfi'],
          'kgsl_gmu.c':['gmu_dcvs_set']}
 for name,functions in sources.items():
  src=(OLD/'native'/name).read_text()
  for name in functions:assert function(native,name)==function(src,name),name
 target='setup(&d);assert(gmu_dcvs_set(&d,5,5)==0);';assert native.count(target)==1
 native=native.replace(target,'setup(&d);assert(gmu_dcvs_set(&d,3,8)==0);')
 native=native.replace('trace[1][1]==0x30000001&&trace[2][1]==0x00005005','trace[1][1]==0x30000003&&trace[2][1]==0x00008008')
 native=native.replace('selected253MHz/bus5 produces30000001/00005005','selected430MHz/bus8 produces30000003/00008008')
 fixture=WORK/'tests/fixtures/gmu-firmware/firmware_host.c';s=fixture.read_text()
 assert s.count('int main(void){')==1;s=s.replace('int main(void){','void original_main(void){')
 marker='static unsigned checks;';assert s.count(marker)==1;s=s.replace(marker,marker+'\nstatic uint32_t oracle_writes[6][3];static unsigned oracle_count;\n')
 marker='if(!tick(f))return false;++f->writes;';assert s.count(marker)==1
 s=s.replace(marker,marker+'''if(f->dcvs&&f->channel.test_valid){CHECK(oracle_count<6);oracle_writes[oracle_count][0]=(w==GMF_TCM?0x1b000u:0x1f000u)+off/4;oracle_writes[oracle_count][1]=value;oracle_writes[oracle_count][2]=0;++oracle_count;}''')
 s+='''\nint main(int argc,char **argv){assert(argc==3);for(unsigned mode=0;mode<2;mode++){profile430=mode;oracle_count=0;memset(oracle_writes,0,sizeof(oracle_writes));struct fake *f=fresh();f->dcvs=f->bw=f->perf=1;struct gmf_receipt out;CHECK(run(f,&out)==GMF_OK&&f->doorbells==5&&f->dcvs_writes==6&&oracle_count==6);FILE *o=fopen(argv[mode+1],"wb");CHECK(o&&fwrite(oracle_writes,1,sizeof(oracle_writes),o)==sizeof(oracle_writes)&&!fclose(o));free(f);}puts("PASS: actual port default253/BW5 and430/BW8 six-store sequences captured after five HFIs");}\n'''
 d=STATE/'kernel-source/bsd/dev';names=['gauguin_gmu_firmware','gauguin_gmu_hfi','gauguin_gmu_memory','cmd_db_snapshot','gauguin_bcm_plan']
 files=[Path(__file__),fixture,proof,OLD/'native-oracle-v3/oracle.c',OLD/'native-oracle-v3/native-writes.bin',*[d/(n+ext) for n in names for ext in ('.c','.h')]]
 pins.update({str(p):sha(p) for p in files});out.mkdir()
 (out/'native.c').write_text(native);(out/'port.c').write_text(s)
 env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 def run(cmd,label):
  with (out/(label+'.log')).open('x') as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
  assert r.returncode==0,label
 common=['clang','-std=gnu11','-Wall','-Wextra','-Werror','-g','-fsanitize=address,undefined']
 run(common+['-Wno-error=pointer-sign',str(out/'native.c'),'-o',str(out/'native')],'native-compile')
 run([str(out/'native'),str(out/'native430.bin')],'native-run')
 run(common+['-I'+str(d),*[str(d/(n+'.c')) for n in names],str(out/'port.c'),'-o',str(out/'port')],'port-compile')
 run([str(out/'port'),str(out/'port253.bin'),str(out/'port430.bin')],'port-run')
 oldwire=OLD/'native-oracle-v3/native-writes.bin'
 assert sha(oldwire)==old['native_writes_sha256']
 assert (out/'port253.bin').read_bytes()==oldwire.read_bytes()
 assert (out/'port430.bin').read_bytes()==(out/'native430.bin').read_bytes()
 assert all((out/n).stat().st_size==72 for n in ('port253.bin','port430.bin','native430.bin'))
 for n,digest in pins.items():assert sha(n)==digest,n
 result=dict(state='PERF326-actual-port-default-and430-match-primary-native',native_functions=7,native_legal_pairs=72,stores_per_profile=6,bytes_per_profile=72,
  default253_sha256=sha(out/'port253.bin'),native430_sha256=sha(out/'native430.bin'),port430_sha256=sha(out/'port430.bin'),default_store_stream_unchanged=True,
  sources_ref='19b63c8192b1c9b7c4d931d7d3be92024bc2d778',sanitizers='ASan+UBSan',input_pins=pins,inputs_unchanged=True,device_commands=0,hardware_frequency_measured=False)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
