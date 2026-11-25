#!/usr/bin/env python3
"""Bind the fresh recovery FDT/OPP curve to the fixed native565/BW9 request."""
from pathlib import Path
import hashlib,json,struct
MAIN=Path('/Users/baai/Project/ios-gauguin');WORK=Path(__file__).resolve().parents[1]
STATE=WORK/'research/tmp/key-perf565-331';BASE=MAIN/'research/tmp/gauguin-direct-load-worktree-20261116/research/tmp/direct-load-330'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 report=BASE/'gpu-policy-readback/result.json';r=json.loads(report.read_text());data={};pins={str(report):sha(report),str(Path(__file__)):sha(__file__)}
 assert r['state']=='readonly-current-native-GPU-policy-matches-retained-DT'
 for row in r['records']:
  p=Path(row['output']);assert sha(p)==row['sha256'] and p.stat().st_size==row['bytes'];data[row['path']]=p.read_bytes();pins[str(p)]=sha(p)
 decoder=MAIN/'research/tmp/dsh-0139/audit_policy.py';raw=decoder.read_text();a=raw.index("b=data['/sys/firmware/fdt']");z=raw.index('def u32(x):',a)
 env={'data':data,'struct':struct};exec(raw[a:z],env);nodes=env['nodes'];pins[str(decoder)]=sha(decoder)
 def u32(raw):assert len(raw)==4;return struct.unpack('>I',raw)[0]
 gpu='/soc/qcom,kgsl-3d0@3d00000';assert u32(nodes[gpu]['qcom,chipid'])==0x06010900 and nodes[gpu]['qcom,gpu-quirk-hfi-use-reg']==b''
 base='/sys/class/kgsl/kgsl-3d0/';freqs=list(map(int,data[base+'gpu_available_frequencies'].split()))
 assert freqs==[800000000,650000000,565000000,430000000,355000000,253000000]
 matches=[];prefix=gpu+'/qcom,gpu-pwrlevel-bins/'
 for path,props in nodes.items():
  if not path.startswith(prefix) or path[len(prefix):].count('/') or 'qcom,speed-bin' not in props:continue
  rows=sorted((u32(p['reg']),u32(p['qcom,gpu-freq'])) for n,p in nodes.items() if n.startswith(path+'/') and n[len(path)+1:].count('/')==0)
  if [n for n,f in rows]==list(range(7)) and [f for n,f in rows]==freqs+[0]:matches.append((path,u32(props['qcom,speed-bin'])))
 assert len(matches)==1 and matches[0][1]==169
 opp={}
 for path,props in nodes.items():
  if path.startswith('/soc/gpu-opp-table/') and 'opp-hz' in props:
   assert len(props['opp-hz'])==8;hz=struct.unpack('>Q',props['opp-hz'])[0];assert hz not in opp;opp[hz]=u32(props['opp-microvolt'])
 curve=[(0,0)]+[(hz,opp[hz]) for hz in reversed(freqs)]
 retained=MAIN/'research/tmp/dsh-0139/policy-audit.json';prior=json.loads(retained.read_text());pins[str(retained)]=sha(retained)
 assert [list(row) for row in curve]==prior['off_inclusive_ascending_hz_arc_vlvl']
 assert curve[1:5]==[(253000000,64),(355000000,128),(430000000,192),(565000000,256)]
 selected=r['active_rows'][2]['properties'];assert selected['reg']==[2] and selected['qcom,gpu-freq']==[565000000]
 assert selected['qcom,bus-freq']==[9] and selected['qcom,bus-min']==[8] and selected['qcom,bus-max']==[11]
 result=dict(state='PERF331-fresh-FDT-native-frequency-bandwidth-OPP-bound',chipid=0x06010900,active_bin=matches[0][0],matching_bin_property=169,off_inclusive_hz_ARC_virtual_levels=curve,
  profile={'linux_powerlevel':2,'perf_index':4,'frequency_hz':565000000,'bw_index':9,'bw_min':8,'bw_max':11,'ARC_virtual_level':256},
  context='Recovery observations and native policy; OPP field is ARC virtual level, not measured microvolts. Same-boot CMDDB is revalidated by unchanged production builders.',
  frequency_measured=False,voltage_measured=False,fuse_speed_bin_read=False,device_commands=0,input_pins=pins)
 for p,d in pins.items():assert sha(p)==d,p
 with (STATE/'policy-review.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
 print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))
if __name__=='__main__':main()
