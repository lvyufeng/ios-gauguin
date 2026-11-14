"""Read the fixed31-file owned-core root set with bounded full log growth without mounting, writes or reboot."""
from pathlib import Path
import argparse,hashlib,json,re,sys
DIRECTORIES={'/private/var/mobile/Library/Caches/gauguin-metal244': {'target_uid': 501, 'target_gid': 501, 'target_mode': 16832}, '/private/var/mobile/Library/Caches/gauguin-metal244/pipelinelib': {'target_uid': 501, 'target_gid': 501, 'target_mode': 16832}, '/System/Library/Extensions/GauguinMetalDesktop.bundle': {'target_uid': 0, 'target_gid': 0, 'target_mode': 16877}, '/System/Library/Extensions/GauguinMetalDesktop.bundle/_CodeSignature': {'target_uid': 0, 'target_gid': 0, 'target_mode': 16877}}
MAIN=Path('/Users/baai/Project/ios-gauguin');W=Path(__file__).resolve().parent;R=MAIN
sys.path.insert(0,str(MAIN/'research/tmp/dsh-0175'))
from local_hfs175v3 import HFS
from write_root_delta175v2 import RecoveryIO,VOLUME,PARTITION_BYTES,require
PATHS={
 '/usr/local/lib/gauguin/pipeline_fixture.metallib',
 '/usr/libexec/gauguin-metal-frontend-probe',
 '/usr/local/lib/gauguin/GauguinMetal.bundle/GauguinMetal',
 '/usr/local/lib/gauguin/GauguinMetal.bundle/Info.plist',
 '/usr/local/lib/gauguin/GauguinMetal.bundle/_CodeSignature/CodeResources',
 '/usr/libexec/gauguin-gpu-probe','/usr/libexec/gauguin-gles-probe',
 '/usr/libexec/gauguin-metal-probe','/usr/local/lib/gauguin/libGauguinMetalCore.dylib',
 '/usr/local/lib/gauguin/libGauguinOSMesa.8.dylib',
 '/System/Library/LaunchDaemons/org.gauguin.gpu-probe.plist','/System/Library/xpc/launchd.plist',
 '/private/var/tmp/gauguin-gles180.log','/private/var/tmp/gauguin-gles180.stderr.log',
 '/System/Library/LaunchDaemons/com.apple.jetsamproperties.D22.plist',
 '/System/Library/LaunchDaemons/com.apple.jetsamproperties.D221.plist',
 '/usr/local/lib/gauguin/libGauguinEAGLAdmission.dylib',
 '/System/Library/LaunchDaemons/com.apple.backboardd.plist','/private/var/log/backboardd.log',
 '/usr/local/lib/gauguin/libGauguinCompositorProbe.dylib','/usr/libexec/backboardd',
 '/usr/local/lib/gauguin/libGauguinEAGL.dylib',
 '/System/Library/Extensions/GauguinMetalDesktop.bundle/GauguinMetalDesktop',
 '/System/Library/Extensions/GauguinMetalDesktop.bundle/Info.plist',
 '/System/Library/Extensions/GauguinMetalDesktop.bundle/_CodeSignature/CodeResources',
 '/usr/libexec/gauguin-gpu-probe-router',
 '/usr/libexec/gauguin-metal-bootstrap',
}
FILE_LIMITS={
 '/private/var/tmp/gauguin-gles180.log':8388608,
 '/private/var/tmp/gauguin-gles180.stderr.log':8388608,
 '/usr/local/lib/gauguin/libGauguinOSMesa.8.dylib':16026608,
 '/usr/local/lib/gauguin/libGauguinMetalCore.dylib':8369632,
 '/usr/libexec/gauguin-metal-probe':115728,
 '/usr/libexec/backboardd':1184848,
 '/private/var/log/backboardd.log':8388608,
}
PATHS.update({'/usr/libexec/gauguin-metal-owned-test','/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib'})
FILE_LIMITS['/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib']=8407792
DIRECTORIES['/usr/local/lib/gauguin/owned']={'target_uid':0,'target_gid':0,'target_mode':16877}
PATHS.update({'/System/Library/LaunchDaemons/com.apple.SpringBoard.plist','/private/var/log/springboard.log'})
FILE_LIMITS['/System/Library/LaunchDaemons/com.apple.SpringBoard.plist']=4096
FILE_LIMITS['/private/var/log/springboard.log']=8388608
def capture(c,make_io=RecoveryIO):
 require(c['phase']in ['before-boot','after-boot','local-model'],'unexpected capture phase')
 require(type(c['files'])is dict and set(c['files'])==PATHS,'wrong capture file set')
 names=list(c['files'].values());require(all(type(n)is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',n)for n in names)and len(set(names))==31,'unsafe/duplicate output name')
 out=(R/c['out']).resolve();require(out.is_relative_to(R/'research/tmp'),'private output required')
 expected=c.get('expected_header_sha256');require(expected is None or re.fullmatch('[0-9a-f]{64}',expected),'invalid header pin')
 io=make_io();info=io.identity()
 require(info['state']=='recovery' and info['product']=='gauguin' and info['partition_bytes']==PARTITION_BYTES and info['unmounted']and info['no_holders'],'wrong recovery')
 header=io.read(0,4096);require(len(header)==4096,'short initial header')
 header_sha=hashlib.sha256(header).hexdigest();require(expected is None or expected==header_sha,'unexpected root header')
 out.mkdir(exist_ok=False)
 class Remote:
  def __init__(self):self.pos=0;self.bytes=0
  def seek(self,n):self.pos=n
  def read(self,n):
   require(type(n)is int and 0<=n<=268435456 and 0<=self.pos and self.pos+n<=VOLUME,'bad remote read')
   if not n:return b''
   lo=self.pos//4096*4096;end=(self.pos+n+4095)//4096*4096;raw=io.read(lo,end-lo)
   require(len(raw)==end-lo,'short remote read; never repair framing')
   self.bytes+=len(raw);data=raw[self.pos-lo:self.pos-lo+n];self.pos+=n;return data
  def close(self):pass
 remote=Remote();h=HFS(stream=remote,size=VOLUME);files={}
 try:
  for path,name in c['files'].items():
   row=h.paths.get(path)
   if not row:files[path]={'present':False};continue
   require(row['type']==2 and row['data']['logical']<=FILE_LIMITS.get(path,1048576)and not row['flags']&0x20,'unexpected probe/log fork: '+path)
   data=h.content(path);require(len(data)==row['data']['logical'],'short logical file')
   with (out/name).open('xb')as f:f.write(data)
   files[path]=dict(present=True,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),uid=row['uid'],gid=row['gid'],mode=row['mode'],fork=row['data'],output=name)
  directories={}
  for path,want in DIRECTORIES.items():
   row=h.paths[path]
   require(row['type']==1 and not row['flags']&0x68,'unexpected directory: '+path)
   require((row['uid'],row['gid'],row['mode'])==(want['target_uid'],want['target_gid'],want['target_mode']),'directory owner/mode differs: '+path)
   directories[path]={k:row[k] for k in ['type','uid','gid','mode']}
 finally:h.close()
 require(io.read(0,4096)==header,'root header changed during capture')
 result=dict(state='captured-readonly-owned-root-files',phase=c['phase'],files=files,directories=directories,root_header_sha256=header_sha,partition_read_bytes=remote.bytes+8192,device_writes=0,reboot_commands=0)
 with (out/'result.json').open('x')as f:f.write(json.dumps(result,indent=2)+'\n')
 return result
def main():
 ap=argparse.ArgumentParser();ap.add_argument('profile',type=Path);a=ap.parse_args();r=capture(json.loads(a.profile.read_text()))
 print(json.dumps({k:v for k,v in r.items()if k!='files'},indent=2))
if __name__=='__main__':main()
