#!/usr/bin/env python3
"""Execute the clock header and actual configure/tick/arm driver bodies with virtual time."""
from pathlib import Path
import hashlib,os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
TREE=Path(os.environ['XNU_SOURCE']);REFERENCE=Path(os.environ['PRESENT_REFERENCE'])
FIXTURE=ROOT/'tests/fixtures/present_clock_host.cpp'

def method(source,signature):
 start=source.index(signature);return source[start:source.index('\n}\n',start)+3]

def main():
 header=TREE/'iokit/Kernel/arm/SweetPresentClock.h';source=TREE/'iokit/Kernel/arm/SweetFramebuffer.cpp';old=REFERENCE/'iokit/Kernel/arm/SweetFramebuffer.cpp'
 files=[Path(__file__),FIXTURE,header,source,old];pins={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
 fb=source.read_text();before=old.read_text();timer=method(fb,'void\nAppleCLCD::vsyncFired(')
 assert 'sender->setTimeoutUS'not in timer and timer.count('fb->armVsync(sender);')==3
 assert timer.index('IOLockLock(fb->fLock)')<timer.index('now = mach_absolute_time(); /* include time waiting for fLock */')<timer.index('fb->presentClockTickLocked(')
 assert 'if (fb->fPhasePresent) flush = fb->fDirty && phaseCopy;'in timer
 assert timer.index('if (rec != NULL) fb->presentClockCopiedLocked();')<timer.index('fb->present(rec,')
 assert 'configurePresentClock();'in method(fb,'bool\nAppleCLCD::start(')
 old_timer=method(before,'void\nAppleCLCD::vsyncFired(')
 arm='sender->setTimeoutUS(SWEET_FB_VSYNC_US);';flush='bool flush = fb->fDirty && (count % fb->fFlushTicks) == 0;'
 assert arm in old_timer and flush in old_timer and old_timer.rindex(arm)>old_timer.index('fb->present(rec,')
 text=FIXTURE.read_text()
 methods='\n'.join(method(fb,n)for n in ['void\nAppleCLCD::configurePresentClock(',
  'bool\nAppleCLCD::presentClockTickLocked(','void\nAppleCLCD::presentClockCopiedLocked(','void\nAppleCLCD::armVsync('])
 for key,value in {'@CLOCK_HEADER@':header.read_text(),'@DRIVER_METHODS@':methods,'@LEGACY_ARM@':arm,'@LEGACY_FLUSH@':flush}.items():
  assert text.count(key)==1;text=text.replace(key,value)
 env=dict(os.environ,ASAN_OPTIONS='halt_on_error=1:detect_leaks=0',UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
 with tempfile.TemporaryDirectory(prefix='present-clock-')as d:
  p=Path(d);cpp=p/'clock.cpp';cpp.write_text(text);exe=p/'clock'
  subprocess.run(['clang++','-std=c++17','-O1','-g','-Wall','-Wextra','-Werror','-pedantic','-fsanitize=address,undefined',
                  '-fno-omit-frame-pointer',str(cpp),'-pthread','-o',str(exe)],env=env,check=True)
  old_run=subprocess.run([str(exe),'legacy-contract'],env=env,capture_output=True,text=True,timeout=30)
  assert old_run.returncode==42 and old_run.stderr=='FAIL relative rearm adds copy work to the next interval\n',(old_run.returncode,old_run.stdout,old_run.stderr)
  print('Baseline functional RED: actual relative rearm adds virtual copy work to every copy interval')
  good=subprocess.run([str(exe),'phase-contract'],env=env,capture_output=True,text=True,timeout=30)
  assert good.returncode==0,(good.returncode,good.stdout,good.stderr);print(good.stdout,end='')
 assert pins=={p:hashlib.sha256(p.read_bytes()).hexdigest()for p in files}
if __name__=='__main__':main()
