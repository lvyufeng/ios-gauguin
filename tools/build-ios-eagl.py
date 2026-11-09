#!/usr/bin/env python3
"""Build the EAGL diagnostics, disabled bridge, or compositor probe for iOS16.

Only local source preparation, cross-compilation and signing. The default
bridge stays disabled. The compositor bridge is an explicit build option.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,struct,subprocess

ACCEPTED_MESA='3a44752493fb204d62817934dcee10c48ed3be857908402f93e06cc77128a2ea'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def replace_once(s,a,b):
    assert s.count(a)==1,('primary source context differs',a[:100])
    return s.replace(a,b)
def adapt_eagl(s):
    s=replace_once(s,'#include "hakios.gl.h"','#include "hakios.gl.h"\n#include <limits.h>\nextern int gauguin_eagl_admit(void);')
    s=replace_once(s,'    GLsizei width, GLsizei height, unsigned long format, unsigned long type, uint32_t plane, BOOL invert)',
        '    uint32_t pixel_width, uint32_t pixel_height, unsigned long format, unsigned long type, uint32_t plane, BOOL invert)')
    start=s.index('my_texImageIOSurface(');end=s.index('\nstatic ',start)
    part=s[start:end]
    part=replace_once(part,'\t(void)selector;','\tif (pixel_width > INT_MAX || pixel_height > INT_MAX) return NO;\n\tGLsizei width = (GLsizei)pixel_width, height = (GLsizei)pixel_height;\n\t(void)selector;')
    s=s[:start]+part+s[end:]
    s=replace_once(s,'install(void)\n{','install(void)\n{\n\tif (!gauguin_eagl_admit()) return;')
    # A caller diagnostic must not chase arbitrary caller frame pointers.
    # Retain only the current frame's return address, which Clang supports.
    s=replace_once(s,'uintptr_t callers[5], slide;','uintptr_t callers[1], slide;')
    s=replace_once(s,'char line[5 * 20 + 1] = "";','char line[20 + 1] = "";')
    for depth in range(1,5):
        s=replace_once(s,'\tcallers[%d] = (uintptr_t)__builtin_return_address(%d);\n' % (depth,depth),'')
    s=replace_once(s,'size_t size = 1, extensions = 0;','size_t size = 1;')
    s=replace_once(s,'\t\textensions++;\n','')
    # Actual ARM64 method widths from this root's 20H392 metadata. This checks
    # the C hook types as well as the otherwise easy-to-miss unsigned dimensions.
    marker='/* Does the display\'s driver wait for the GPU'
    assertions='''typedef BOOL (*gauguin_tex_method)(id, SEL, IOSurfaceRef, unsigned long, unsigned long,
    uint32_t, uint32_t, unsigned long, unsigned long, uint32_t, BOOL);
_Static_assert(sizeof(unsigned long) == 8 && sizeof(GLsizei) == 4 && sizeof(BOOL) == 1, "actual arm64 EAGL widths");
_Static_assert(__builtin_types_compatible_p(__typeof__(&my_texImageIOSurface), gauguin_tex_method), "20H392 uint32 dimensions");

'''
    s=replace_once(s,marker,assertions+marker)
    return s

def adapt_render_eagl(source):
    source = replace_once(source, 'static struct eagl *contexts[8];',
                          'static struct eagl *contexts[8];\n'
                          'static pthread_mutex_t gauguin_context_lock = PTHREAD_RECURSIVE_MUTEX_INITIALIZER;')
    start = source.index('static struct eagl *\ncontext_of(id object)\n')
    end = source.index('\n/* ----', start)
    source = source[:start] + '''static struct eagl *
context_of(id object)
{
    struct eagl *found = NULL;
    pthread_mutex_lock(&gauguin_context_lock);
    for (unsigned i = 0; i < sizeof(contexts) / sizeof(contexts[0]); i++) {
        if (contexts[i] != NULL && contexts[i]->object == object) {
            found = contexts[i];
            break;
        }
    }
    pthread_mutex_unlock(&gauguin_context_lock);
    return found;
}
''' + source[end:]
    source = replace_once(
        source, '\t\tfree(e);\n\t\treturn nil;\n\t}\n\tcurrent = e;',
        '\t\tif (e->gl) hakios_gl_destroy(e->gl);\n'
        '\t\tfree(e);\n\t\treturn nil;\n\t}\n\tcurrent = e;')
    source = replace_once(source, "/* Does the display's driver wait for the GPU",
                          '#include "bridge.inc"\n\n'
                          "/* Does the display's driver wait for the GPU")
    source = replace_once(source,
                          '\tstatic const struct {\n\t\tconst char *name;\n\t\tIMP ours;\n\t} methods[] = {',
                          '\tstatic const struct gauguin_eagl_method methods[] = {')
    begin = source.index('\tfor (unsigned i = 0; i < sizeof(methods) / sizeof(methods[0]); i++) {')
    end = source.index('\n\tsay("hakios-gl: %u of %zu methods', begin)
    source = source[:begin] + (
        '\treplaced = gauguin_eagl_install_subclass(class, methods, sizeof(methods) / sizeof(methods[0]));\n'
    ) + source[end:]
    return source
def macho(p,kind):
    b=p.read_bytes();magic,cpu,sub,typ,n,size,flags,res=struct.unpack_from('<8I',b)
    assert magic==0xfeedfacf and cpu==0x100000c and typ==kind and n<256 and 32+size<=len(b)
    at=32;versions=[];loads=[];rpaths=[];identity=[]
    for _ in range(n):
        cmd,sz=struct.unpack_from('<II',b,at);assert sz>=8 and at+sz<=32+size
        if cmd==0x32:versions.append(struct.unpack_from('<4I',b,at+8))
        if cmd in (0xd,0xc,0x80000018,0x8000001f):
            o=struct.unpack_from('<I',b,at+8)[0];assert 24<=o<sz
            name=b[at+o:b.index(b'\0',at+o,at+sz)].decode()
            (identity if cmd==0xd else loads).append(name)
        if cmd==0x8000001c:
            o=struct.unpack_from('<I',b,at+8)[0];rpaths.append(b[at+o:b.index(b'\0',at+o,at+sz)].decode())
        at+=sz
    assert at==32+size and len(versions)==1 and versions[0][:2]==(2,0x100000)
    return {'bytes':len(b),'sha256':sha(p),'versions':versions,'loads':loads,'rpaths':rpaths,'install_names':identity}

def build_pilot(repo, mesa_build, out):
    receipt = mesa_build.resolve() / 'result.json'
    mesa = json.loads(receipt.read_text())
    assert mesa['state'] == 'passed-iOS16-A619-GLES-library-and-probe-build'
    lib = Path(mesa['products']['libGauguinOSMesa.8.dylib']['path'])
    assert sha(lib) == ACCEPTED_MESA
    includes = Path(mesa['source']) / 'include'
    sources = repo / 'userland/eagl'
    launcher_source = sources / 'pilot.c'
    admission_source = sources / 'admission.c'
    worker_source = sources / 'compositor_probe.c'
    sdk = Path(subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--show-sdk-path'], text=True).strip())
    clang = subprocess.check_output(['xcrun', '--sdk', 'iphoneos', '--find', 'clang'], text=True).strip()
    headers = ['GL/gl.h', 'GL/glext.h', 'GL/osmesa.h', 'GLES3/gl3.h',
               'GLES3/gl3platform.h', 'KHR/khrplatform.h']
    paths = [Path(__file__).resolve(), receipt, lib, sdk / 'SDKSettings.json',
             launcher_source, admission_source, worker_source, *(includes / h for h in headers)]
    pins = {str(path): sha(path) for path in paths}
    out = out.resolve()
    products = out / 'products'
    out.mkdir(parents=True, exist_ok=False)
    products.mkdir()
    install_dir = '/usr/local/lib/gauguin'
    admission = products / 'libGauguinEAGLAdmission.dylib'
    worker = products / 'libGauguinCompositorProbe.dylib'
    common = [clang, '-target', 'arm64-apple-ios16.0', '-isysroot', str(sdk),
              '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-dynamiclib',
              '-framework', 'CoreFoundation', '-framework', 'IOKit']
    commands = (
        (admission, common + ['-lobjc', '-DGAUGUIN_EAGL_ADMISSION_ONLY=1',
                              '-DGAUGUIN_EAGL_PILOT=1', str(admission_source), str(launcher_source)]),
        (worker, common + ['-fvisibility=hidden', '-I' + str(includes), '-framework', 'IOSurface',
                           str(worker_source), str(lib), '-Wl,-rpath,' + install_dir]),
    )
    artifacts = {}
    for product, argv in commands:
        install_name = install_dir + '/' + product.name
        with (out / (product.stem + '.log')).open('xb') as log:
            subprocess.run(argv + ['-install_name', install_name, '-o', str(product)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
            subprocess.run(['/usr/bin/codesign', '--force', '--sign', '-', str(product)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
            subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(product)],
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        artifact = macho(product, 6)
        assert artifact['install_names'] == [install_name]
        artifacts[product.name] = {'path': str(product), **artifact}
    loader = artifacts[admission.name]
    probe = artifacts[worker.name]
    assert not loader['rpaths'] and all('GauguinOSMesa' not in x for x in loader['loads'])
    assert probe['rpaths'] == [install_dir] and '@rpath/libGauguinOSMesa.8.dylib' in probe['loads']
    symbols = subprocess.check_output(['/usr/bin/nm', '-gUj', str(worker)], text=True).splitlines()
    assert symbols == ['_gauguin_compositor_gles_run']
    for product in (admission, worker):
        imports = subprocess.check_output(['/usr/bin/nm', '-uj', str(product)], text=True)
        assert not any(x in imports for x in ('method_setImplementation', 'class_addMethod',
                                               'method_exchangeImplementations'))
    assert all(sha(Path(path)) == pin for path, pin in pins.items())
    result = {'state': 'signed-iOS16-arm64-compositor-probe-and-late-loader',
              'products': artifacts, 'input_pins': pins, 'inputs_unchanged': True,
              'device_writes': 0, 'renderer_hooks': False, 'physical_qualified': False}
    (out / 'build-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['state'])

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--upstream-cache',type=Path);ap.add_argument('--mesa-build',type=Path,required=True)
    ap.add_argument('--registry',type=Path);ap.add_argument('--out',type=Path,required=True)
    choices=ap.add_mutually_exclusive_group()
    choices.add_argument('--compositor-pilot', action='store_true')
    choices.add_argument('--compositor-bridge', action='store_true');a=ap.parse_args()
    repo=Path(__file__).resolve().parent.parent
    if a.compositor_pilot:
        if a.upstream_cache or a.registry:
            ap.error('--compositor-pilot uses the accepted Mesa build without bridge inputs')
        return build_pilot(repo, a.mesa_build, a.out)
    if not a.upstream_cache or not a.registry:
        ap.error('--upstream-cache and --registry are required for the disabled bridge')
    e=repo/'userland/eagl';out=a.out.resolve();cache=a.upstream_cache.resolve()
    manifest=e/'upstream.json';m=json.loads(manifest.read_text());assert m['commit']=='63fc2b4633bac3af8e57dadab9f5a8d4cb940438'
    inputs={str(p):sha(p) for p in [Path(__file__).resolve(),manifest,e/'admission.c',e/'LICENSE.upstream',a.registry.resolve()]}
    if a.compositor_bridge:
        inputs.update({str(p):sha(p) for p in (e/'bridge.inc',e/'pilot.c')})
    for row in m['files']:
        p=cache/row['cache_name'];b=p.read_bytes();assert len(b)==row['bytes'] and sha(p)==row['sha256']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['git_blob'];inputs[str(p)]=sha(p)
    receipt=a.mesa_build.resolve()/'result.json';mesa=json.loads(receipt.read_text());lib=Path(mesa['products']['libGauguinOSMesa.8.dylib']['path'])
    assert mesa['state']=='passed-iOS16-A619-GLES-library-and-probe-build' and sha(lib)==ACCEPTED_MESA
    assert mesa['products']['libGauguinOSMesa.8.dylib']['sha256']==ACCEPTED_MESA
    assert a.registry.name=='gl.xml' and a.registry.stat().st_size>1000000
    inputs.update({str(receipt):sha(receipt),str(lib):sha(lib)})
    sdk=Path(subprocess.check_output(['xcrun','--sdk','iphoneos','--show-sdk-path'],text=True).strip())
    compiler=subprocess.check_output(['xcrun','--sdk','iphoneos','--find','clang'],text=True).strip();inputs[str(sdk/'SDKSettings.json')]=sha(sdk/'SDKSettings.json')
    out.mkdir(parents=True,exist_ok=False);source=out/'source';source.mkdir();product=out/'product';product.mkdir();logs=[]
    record={'state':'building-inert-EAGL-admission-and-disabled-bridge','input_pins':inputs,'results':logs,'device_commands':0,'UI_qualified':False,'rendering_enabled':False,'sdk':str(sdk)}
    def save():
        record['inputs_unchanged']=all(sha(Path(p))==pin for p,pin in inputs.items());(out/'result.json').write_text(json.dumps(record,indent=2)+'\n')
    def run(argv,name):
        with (out/(name+'.log')).open('xb') as f:p=subprocess.run(argv,cwd=repo,stdout=f,stderr=subprocess.STDOUT)
        logs.append({'name':name,'argv':argv,'exit':p.returncode});save();assert p.returncode==0,(name,p.returncode)
    try:
        for name in ('eagl.c','gl_osmesa.c','hakios.gl.h'):shutil.copyfile(cache/name,source/name)
        adapted=adapt_eagl((source/'eagl.c').read_text())
        if a.compositor_bridge:
            adapted=adapt_render_eagl(adapted)
            shutil.copyfile(e/'bridge.inc',source/'bridge.inc')
        (source/'eagl.c').write_text(adapted)
        shutil.copyfile(e/'LICENSE.upstream',source/'LICENSE.upstream')
        run(['/usr/bin/nm','-gU',str(lib)],'accepted-Mesa-exports')
        exported=sorted(set(re.findall(r'\b_(gl\w+)\s*$',(out/'accepted-Mesa-exports.log').read_text(),re.M)))
        assert len(exported)>500;exports=source/'exported-gl.txt';exports.write_text('\n'.join(exported)+'\n')
        # Keep stdout (generated C) separate from the generator's coverage report.
        with (source/'eagl_gen.h').open('xb') as f,(out/'generator-coverage.log').open('xb') as err:
            q=subprocess.run(['python3',str(cache/'mkeagl.py'),str(cache/'eagl_slots.txt'),str(a.registry.resolve()),str(exports),str(source/'eagl.c')],stdout=f,stderr=err)
        assert q.returncode==0
        coverage=(out/'generator-coverage.log').read_text();assert '409 entries:' in coverage and 'of those QuartzCore calls:' not in coverage
        common=[compiler,'-target','arm64-apple-ios16.0','-isysroot',str(sdk),'-std=gnu11','-O2','-Wall','-Wextra','-Werror','-dynamiclib','-framework','CoreFoundation','-framework','IOKit','-lobjc']
        admission=product/'libGauguinEAGLAdmission.dylib';bridge=product/'libGauguinEAGL.dylib'
        admission_flags=['-DGAUGUIN_EAGL_ADMISSION_ONLY=1']
        admission_sources=[str(e/'admission.c')]
        bridge_flags=[]
        if a.compositor_bridge:
            admission_flags+=['-DGAUGUIN_EAGL_PILOT=1','-DGAUGUIN_EAGL_BRIDGE_LOADER=1']
            admission_sources.append(str(e/'pilot.c'))
            bridge_flags=['-DGAUGUIN_EAGL_RENDER_PILOT=1']
        run(common+admission_flags+['-install_name','/usr/local/lib/gauguin/'+admission.name]+admission_sources+['-o',str(admission)],'admission-link')
        bridge_log='render-bridge-link' if a.compositor_bridge else 'disabled-bridge-link'
        run(common+bridge_flags+['-framework','IOSurface','-install_name','/usr/local/lib/gauguin/'+bridge.name,'-I'+str(source),str(source/'eagl.c'),str(source/'gl_osmesa.c'),str(e/'admission.c'),str(lib),'-Wl,-rpath,/usr/local/lib/gauguin','-o',str(bridge)],bridge_log)
        products={}
        for i,p in enumerate((admission,bridge)):
            run(['/usr/bin/codesign','--force','--sign','-',str(p)],f'sign-{i}');run(['/usr/bin/codesign','--verify','--strict',str(p)],f'verify-{i}')
            products[p.name]={'path':str(p),**macho(p,6)}
            run(['/usr/bin/nm','-u',str(p)],f'imports-{i}')
        imports=(out/'imports-0.log').read_text()
        forbidden=('IOConnectCall','OSMesa','method_setImplementation','class_addMethod','method_exchangeImplementations')
        if not a.compositor_bridge:
            forbidden+=('IOServiceOpen',)
        assert not any(x in imports for x in forbidden)
        assert not any('GauguinOSMesa' in x or 'OpenGLES' in x for x in products[admission.name]['loads'])
        assert '@rpath/libGauguinOSMesa.8.dylib' in products[bridge.name]['loads']
        record.update(state='passed-iOS16-inert-EAGL-admission-and-disabled-bridge-build',products=products,generator_coverage=coverage.strip(),scope='Cross-build and signing only. Admission has no renderer-changing imports or Mesa dependency. Both products disable method replacement. Runtime injection and compositor memory/ABI remain unqualified.')
        if a.compositor_bridge:
            run(['/usr/bin/nm','-gU',str(bridge)],'bridge-exports')
            assert '_gauguin_eagl_bridge_installed' in (out/'bridge-exports.log').read_text()
            assert 'method_setImplementation' in (out/'imports-1.log').read_text()
            record.update(state='passed-iOS16-scoped-EAGL-subclass-bridge-build',rendering_enabled=True,
                          scope='Signed build of an opt-in new-context EAGL subclass and late loader. Physical frame composition remains unqualified.')
        save();assert record['inputs_unchanged'];print(json.dumps({k:v for k,v in record.items() if k not in ('input_pins','results')},indent=2))
    except Exception as exc:record.update(state='failed-inert-EAGL-build',error=repr(exc));save();raise
if __name__=='__main__':main()
