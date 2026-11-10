#!/usr/bin/env python3
"""Run extracted display ownership code; old raw-ID handoff must fail functionally."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
TREE=Path(os.environ['XNU_SOURCE'])
REFERENCE=Path(os.environ['PRESENT_REFERENCE'])
FIXTURE=ROOT/'tests/fixtures/present_lifetime_host.cpp'

def method(source,signature):
 start=source.index(signature)
 return source[start:source.index('\n}\n',start)+3]

def unit(tree):
 surface=(tree/'iokit/Kernel/arm/SweetSurface.cpp').read_text()
 fb=(tree/'iokit/Kernel/arm/SweetFramebuffer.cpp').read_text()
 held='sweet_surface_hold(uint32_t id)'in surface
 surface_methods=[method(surface,n)for n in ['static void\nsweet_surface_put(','SweetSurface *\nsweet_surface_copy(']]
 if held:surface_methods += [method(surface,n)for n in ['SweetSurface *\nsweet_surface_hold(','void\nsweet_surface_drop(']]
 frame_type=frame_methods=''
 if held:
  start=fb.index('struct sweet_fb_frame {');frame_type=fb[start:fb.index('\n};',start)+4]
  frame_methods='\n'.join(method(fb,n)for n in ['static void\nsweet_fb_frame_release(',
   'static void\nsweet_fb_frame_move(','static bool\nsweet_fb_frame_prepare(',
   'static SweetSurface *\nsweet_fb_present_surface(','bool\nAppleCLCD::takeHeldFrameLocked(',
   'void\nAppleCLCD::cancelHeldFrameLocked(','void\nAppleCLCD::finishHeldFrame(','void\nAppleCLCD::removeClient('])
  # Bind the tested helpers to the actual timer, close and guarded copy entry.
  timer=method(fb,'void\nAppleCLCD::vsyncFired(')
  assert 'fb->cancelHeldFrameLocked(&canceled, NULL)'in timer
  assert timer.index('fb->takeHeldFrameLocked(&frame)')<timer.index('fb->present(rec, fb->fHoldPresent ? frame.surfaces : NULL)')<timer.index('fb->finishHeldFrame(&frame)')
  present=method(fb,'void\nAppleCLCD::present(')
  assert present.index('sweet_fb_present_surface(rec, held, layer)')<present.index('SweetSurfaceGPURead gpuRead(s)')<present.index('memcpy((void *)(fPixels')
  assert 'if(!gpuRead.valid()){s->release();continue;}'in present
  assert 'if (!fFB->swap(rec, this)) return kIOReturnNotReady;'in fb
  assert 'fFB->removeClient(this);'in method(fb,'IOReturn\nIOMobileFramebufferUserClient::clientClose(')
 text=FIXTURE.read_text()
 for key,value in {'@SURFACE_METHODS@':'\n'.join(surface_methods),'@FRAME_TYPE@':frame_type,
                   '@GET32@':method(fb,'static uint32_t\nget32('),'@FRAME_METHODS@':frame_methods,
                   '@SWAP_METHOD@':method(fb,('bool'if held else'void')+'\nAppleCLCD::swap(')}.items():
  assert text.count(key)==1;text=text.replace(key,value)
 return '#define HAS_HELD '+str(int(held))+'\n'+text

def main():
 sources=[('baseline',REFERENCE),('candidate',TREE)]
 paths=[Path(__file__),FIXTURE]+[tree/'iokit/Kernel/arm'/name for _,tree in sources for name in ['SweetSurface.cpp','SweetFramebuffer.cpp']]
 pins={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in paths}
 env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='present-lifetime-')as d:
  directory=Path(d)
  for name,tree in sources:
   cpp=directory/(name+'.cpp');cpp.write_text(unit(tree));exe=directory/name
   subprocess.run(['clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable',
                   '-pedantic','-fsanitize=address,undefined','-fno-omit-frame-pointer',str(cpp),'-pthread','-o',str(exe)],env=env,check=True)
   result=subprocess.run([str(exe)],env=env,capture_output=True,text=True,timeout=30)
   if name=='baseline':
    assert result.returncode==42 and result.stderr=='FAIL pending display ID resolved a replacement surface after creator close\n',(result.returncode,result.stdout,result.stderr)
    print('Baseline functional RED: pending ID displays a replacement allocation after creator close')
   else:
    assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
    print(result.stdout,end='')
 assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in pins}
if __name__=='__main__':main()
