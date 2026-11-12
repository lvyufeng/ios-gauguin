#!/usr/bin/env python3
"""Build an isolated real-device ownership probe and exercise its host adapter.

No phone access. Requires an admitted complete trial batch, a qualified
ownership core and a current captured old router. Native loads only the new
private core path and hands off to the unchanged, hash-bound old router.
"""
from pathlib import Path
import argparse,concurrent.futures,hashlib,importlib.util,json,os,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for n in ['core-receipt','capture','boot-plan','budget','out']:ap.add_argument('--'+n,type=Path,required=True)
    a=ap.parse_args();repo=Path(__file__).resolve().parents[1];out=a.out.resolve()
    core=json.loads(a.core_receipt.read_text());source=Path(core['source']);lib=Path(core['library'])
    prepared=json.loads((source.parent/'result.json').read_text())
    assert prepared['profile']=='a619-ownership' and core['source_pins_unchanged']
    assert sha(lib)==core['sha256']=='c9da25aad0aacc6966071a78157f942189b379353eafdbb96e2a3854cc107674'
    assert all(sha(p)==h for p,h in core['input_pins'].items())
    cap=json.loads((a.capture/'result.json').read_text());row=cap['files']['/usr/libexec/gauguin-gpu-probe-router'];router=a.capture/row['output']
    assert sha(router)==row['sha256'] and router.stat().st_size==row['bytes']
    assert (row['uid'],row['gid'],row['mode'])==(0,0,0o100755)
    plan=json.loads(a.boot_plan.read_text());image=Path(plan['image'])
    assert sha(image)==plan['image_sha256']=='64596164315fc496ff30037bb1fdf982d1322069eee788e28554f38d6f43cc7e'
    budget=json.loads(a.budget.read_text());assert budget['admitted'] and budget['planned_batch_bytes']>=35433480192
    assert budget['current_accounted_bytes']+budget['planned_batch_bytes']<=500000000000
    unit=repo/'userland/metal/owned_probe.cpp'
    pins={str(p.resolve()):sha(p) for p in [Path(__file__),unit,a.core_receipt,a.capture/'result.json',router,a.boot_plan,a.budget]}
    pins.update(core['input_pins']);tag=hashlib.sha256(json.dumps(pins,sort_keys=True).encode()).hexdigest()[:24]
    out.mkdir(parents=True,exist_ok=False)
    header=out/'GauguinOwnedIdentity.h'
    header.write_text('\n'.join([
        'static const char kOwnedBuild[] = '+json.dumps(tag)+';',
        'static const char kOwnedCoreSha256[] = '+json.dumps(core['sha256'])+';',
        'static const size_t kOwnedCoreBytes = '+str(lib.stat().st_size)+';',
        'static const char kOwnedRouterSha256[] = '+json.dumps(row['sha256'])+';',
        'static const size_t kOwnedRouterBytes = '+str(row['bytes'])+';',
        'static const char kOwnedBootCommand[] = '+json.dumps(plan['boot_command'])+';'])+'\n')
    pins[str(header)]=sha(header)
    def run(argv,name,timeout=180):
        with (out/(name+'.log')).open('x')as log:
            p=subprocess.run([str(x) for x in argv],stdout=log,stderr=subprocess.STDOUT,timeout=timeout,
                env={**os.environ,'ASAN_OPTIONS':'abort_on_error=1:detect_leaks=0','UBSAN_OPTIONS':'halt_on_error=1'})
        assert p.returncode==0,(name,p.returncode)
    host=['clang++','-std=c++17','-O1','-g','-pthread','-fsanitize=address,undefined','-fno-sanitize-recover=all',
          '-DHAKIOS_METAL_TARGET_A619','-DGAUGUIN_OWNED_HOST','-Wall','-Wextra','-Werror','-Wno-unused-function','-I'+str(source/'include')]
    names=['pm4','gpu','command','compute','texture','render','link','compiler','metallib','c_api','fake_gpu','iokit_transport']
    def compile(n):run([*host,'-c',source/'src'/f'{n}.cpp','-o',out/f'{n}.o'],'host-compile-'+n)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:list(pool.map(compile,names))
    run([*host,unit,*[out/f'{n}.o' for n in names],'-framework','IOKit','-framework','CoreFoundation','-o',out/'host-owned-probe'],'host-link')
    run([out/'host-owned-probe','--owned300'],'host-run',timeout=45)
    hostlog=(out/'host-run.log').read_text()
    assert 'GAUGUIN OWNED HOST adapter=FakeGpu physical=0' in hostlog
    assert 'RESULT PASS jobs=8 callbacks=2 pixel_checks=20480 allocated=0 teardown_requested=1' in hostlog
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    pins[str(sdk/'SDKSettings.json')]=sha(sdk/'SDKSettings.json')
    binary=out/'gauguin-metal-owned-test'
    argv=['xcrun','--sdk','iphoneos','clang++','-target','arm64-apple-ios16.0','-isysroot',sdk,'-std=c++17','-O2',
          '-Wall','-Wextra','-Werror','-Wno-deprecated-declarations','-DHAKIOS_METAL_TARGET_A619',
          '-I'+str(source/'include'),'-I'+str(out),unit,lib,'-Wl,-rpath,/usr/local/lib/gauguin/owned','-o',binary]
    run(argv,'native-compile-link');run(['codesign','--force','--sign','-',binary],'sign');run(['codesign','--verify','--strict',binary],'verify')
    run(['otool','-L',binary],'loads');run(['nm','-m','-u',binary],'imports')
    spec=importlib.util.spec_from_file_location('build_core',repo/'tools/build-hakios-metal.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    platform=m.ios_version(binary);assert all(sha(p)==h for p,h in pins.items())
    result=dict(state='host-passed-native-owned-probe-awaiting-device',binary=str(binary),bytes=binary.stat().st_size,sha256=sha(binary),
       build=tag,core_sha256=sha(lib),core_path='/usr/local/lib/gauguin/owned/libGauguinMetalCore.dylib',
       router_sha256=row['sha256'],router_bytes=row['bytes'],platform=platform,expected_successful_jobs=8,
       expected_callbacks=2,expected_pixel_checks=20480,startup_seconds=180,work_alarm_seconds=30,
       input_pins=pins,inputs_unchanged=True,device_commands=0,installed=False,runtime_qualified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k!='input_pins'},indent=2))
if __name__=='__main__':main()
