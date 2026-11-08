#!/usr/bin/env python3
"""Cross-build the prepared actual Mesa freedreno GLES library for iOS16.
Uses only the installed iPhoneOS SDK and an existing Meson/Python environment.
Output is local software qualification; never installs or executes on a phone.
"""
from pathlib import Path
import argparse,hashlib,json,os,shutil,struct,subprocess

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def versions(data):
    header=struct.unpack_from('<8I',data);assert header[0]==0xfeedfacf and header[1]==0x100000c
    at=32;found=[]
    for _ in range(header[4]):
        cmd,size=struct.unpack_from('<II',data,at);assert size>=8 and at+size<=len(data)
        if cmd==0x32:found.append(struct.unpack_from('<4I',data,at+8))
        at+=size
    assert len(found)==1 and found[0][0]==2 and found[0][1]==0x100000,'wrong platform/deployment target'
    return found

def package(repo,source,build,product,compiler,sdk,run,logs):
    library=product/'libGauguinOSMesa.8.dylib';shutil.copyfile(build/'src/gallium/targets/osmesa/libOSMesa.8.dylib',library)
    run(['/usr/bin/install_name_tool','-id','@rpath/libGauguinOSMesa.8.dylib',str(library)],'install-name')
    # Mesa's Darwin meson builds libglapi.a even with shared-glapi enabled;
    # the actual linked OSMesa already owns its dispatch table and GL exports.
    binary=product/'gauguin-gles-probe'
    run([str(compiler),'-target','arm64-apple-ios16.0','-isysroot',str(sdk),'-std=c11','-O2','-Wall','-Wextra','-Werror','-I'+str(source/'include'),str(repo/'tools/gauguin-gles-probe.c'),str(library),'-Wl,-rpath,/usr/local/lib/gauguin','-framework','IOKit','-framework','IOSurface','-framework','CoreFoundation','-o',str(binary)],'probe-link')
    for i,p in enumerate([library,binary]):
        versions(p.read_bytes());run(['/usr/bin/codesign','--force','--sign','-',str(p)],f'sign-{i}');run(['/usr/bin/codesign','--verify','--strict',str(p)],f'verify-{i}')
    run(['/usr/bin/otool','-L',str(library)],'library-loads');run(['/usr/bin/otool','-L',str(binary)],'probe-loads')
    run(['/usr/bin/nm','-gU',str(library)],'library-exports')
    exports=(logs/'library-exports.log').read_text()
    assert all(name in exports for name in ['_OSMesaCreateContextAttribs','_OSMesaMakeCurrent','_OSMesaGetProcAddress','_glCreateShader','_glDrawArrays','_glReadPixels'])
    # This extension is obtained through GetProcAddress, not a public Mach-O
    # symbol. Its compiled dispatch name must still exist in the real library.
    assert b'EGLImageTargetTexture2DOES\0' in library.read_bytes()
    loads=(logs/'library-loads.log').read_text();assert 'libglapi' not in loads and 'libLLVM' not in loads
    return {p.name:{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p),'platform_versions':versions(p.read_bytes())} for p in [library,binary]}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepared',type=Path,required=True);ap.add_argument('--venv',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--jobs',type=int,default=8);a=ap.parse_args()
    assert 1<=a.jobs<=16
    repo=Path(__file__).resolve().parent.parent;receipt=a.prepared.resolve()/'result.json';prepared=json.loads(receipt.read_text())
    assert prepared['state']=='prepared-pinned-A619-Darwin-GLES-source'
    source=Path(prepared['source']);venv=a.venv.resolve();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    compiler=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--find','clang'],text=True).strip())
    cxx=compiler.with_name('clang++');ar=compiler.with_name('ar');strip=compiler.with_name('strip')
    inputs={str(p):sha(p) for p in [Path(__file__).resolve(),repo/'tools/gauguin-gles-probe.c',receipt,sdk/'SDKSettings.json']}
    inputs.update({str(source/p):pin for p,pin in prepared['changed_source_pins'].items()})
    assert all(sha(Path(p))==pin for p,pin in inputs.items()),'prepared source differs'
    env=os.environ.copy();env['PATH']=str(venv/'bin')+':/opt/homebrew/opt/bison/bin:/opt/homebrew/bin:'+env.get('PATH','')
    cross=out/'cross.ini';cross.write_text('''[binaries]
c = %s
cpp = %s
objc = %s
ar = %s
strip = %s
pkg-config = '/usr/bin/false'
[host_machine]
system = 'darwin'
subsystem = 'ios'
cpu_family = 'aarch64'
cpu = 'arm64'
endian = 'little'
[properties]
needs_exe_wrapper = true
'''%(repr([str(compiler),'-target','arm64-apple-ios16.0','-isysroot',str(sdk)]),repr([str(cxx),'-target','arm64-apple-ios16.0','-isysroot',str(sdk)]),repr([str(compiler),'-target','arm64-apple-ios16.0','-isysroot',str(sdk)]),repr(str(ar)),repr(str(strip))))
    build=out/'build';product=out/'product';product.mkdir();results=[]
    record={'state':'starting-ios-GLES-build','source':str(source),'sdk':str(sdk),'input_pins':inputs,'results':results,'physical_qualified':False,'device_commands':0}
    def save():
        record['inputs_unchanged']=all(sha(Path(p))==pin for p,pin in inputs.items());(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    def run(command,name):
        with (out/(name+'.log')).open('x') as f:p=subprocess.run(command,env=env,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
        results.append({'name':name,'argv':command,'exit':p.returncode});save();assert p.returncode==0,('command failed',name,p.returncode)
    try:
        run([str(venv/'bin/meson'),'setup',str(build),str(source),'--cross-file',str(cross),'--wrap-mode=nofallback','--prefix=/usr/local/lib/gauguin','--libdir=.', '--buildtype=release','-Db_ndebug=true',
            '-Dplatforms=','-Dgallium-drivers=freedreno','-Dfreedreno-kmds=msm','-Dvulkan-drivers=','-Dglx=disabled','-Degl=disabled','-Dgbm=disabled','-Dosmesa=true','-Dllvm=disabled','-Dshared-glapi=enabled','-Dgles1=disabled','-Dgles2=enabled','-Dopengl=true',
            '-Dzstd=disabled','-Dxmlconfig=disabled','-Dexpat=disabled','-Dshader-cache=disabled','-Dvalgrind=disabled','-Dlibunwind=disabled','-Dglvnd=disabled','-Dvideo-codecs=','-Dtools=','-Dgallium-vdpau=disabled','-Dgallium-va=disabled','-Dgallium-xa=disabled','-Dlmsensors=disabled','-Dbuild-tests=false'],'configure')
        run(['ninja','-C',str(build),'-j',str(a.jobs),'src/gallium/targets/osmesa/libOSMesa.8.dylib'],'compile-link')
        products=package(repo,source,build,product,compiler,sdk,run,out)
        record.update(state='passed-iOS16-A619-GLES-library-and-probe-build',products=products,renderer='actual Mesa freedreno only; no softpipe/llvmpipe linked',scope='LOCAL CROSS BUILD only; no physical API/rendering/Metal/UI performance proof')
        save();assert record['inputs_unchanged'];print(json.dumps({k:v for k,v in record.items() if k not in ['results','input_pins']},indent=2))
    except Exception as e:record.update(state='failed-ios-GLES-build',error=repr(e));save();raise
if __name__=='__main__':main()
