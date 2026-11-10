"""Synthetic acceptance fixtures are not hardware results. MIT."""
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'tools'))
from metal_shader_log import P,shader_hashes,qualify_shader_log
from test_metal_frontend_log import fixture as objects_fixture,BUILD
from test_gpu_service_log import trace
LIBRARY='a'*64
LIBRARY_BYTES=1024

def fixture():
    original,stderr,_=objects_fixture();lines=original.splitlines()[:-3]
    lines=[line.replace('GAUGUIN METAL226 ',P).replace('scope=root-offscreen-objects-not-CA','scope=root-offscreen-shader-pipelines-not-CA') for line in lines]
    seed=0x12345678;render,compute,half=shader_hashes(seed)
    lines.extend([P+f'library bytes={LIBRARY_BYTES} sha256={LIBRARY}',
                  P+'memory phase=shader-compute-compiled active=128 inactive=128 hard=1 footprint=33554432',
                  P+'pipelines functions=5 compute=1'])
    for phase,digest in compute.items():lines.append(P+f'values phase={phase} words=256 hash={digest} PASS')
    for phase,digest in render.items():
        if phase=='gamma-RGBA':lines.append(P+f'half_pixels phase=premul-half pixels=4096 hash={half} PASS')
        lines.append(P+f'pixels phase={phase} words=4096 hash={digest} PASS')
    lines.extend([P+'memory phase=shader-render-completed active=128 inactive=128 hard=1 footprint=33554432',
                  P+'pipelines render_states=7 render_jobs=8 jobs=10 pixel_checks=32768 compute_words=512 PASS',
                  P+'memory phase=after-resource-release active=128 inactive=128 hard=1 footprint=8388608',
                  P+'ownership reacquired=1 closed=1 PASS',
                  P+f'RESULT PASS build={BUILD} seed={seed} jobs=93 pixel_checks=372736 compute_words=512 half_pixels=4096 abandoned=80 teardown-requested=1 discovery=0 shader-pipelines=1 UI=0'])
    return '\n'.join(lines)+'\n',stderr,trace(93)

def qualify(out,err,native,**extra):
    params=dict(build=BUILD,library_sha256=LIBRARY,library_bytes=LIBRARY_BYTES);params.update(extra)
    return qualify_shader_log(out,err,native,**params)

class ShaderEvidence(unittest.TestCase):
    def test_complete_fixture_claim_is_bounded(self):
        r=qualify(*fixture());self.assertEqual((r['jobs'],r['pixel_checks'],r['compute_words']),(93,372736,512))
        self.assertEqual(r['finite_service']['unrecorded_successes'],77)
        self.assertTrue(r['shader_subset_qualified'])
        for key in ('device_discovery_qualified','desktop_qualified','high_refresh_qualified'):self.assertFalse(r[key])

    def test_reject_missing_stale_and_corrupted_shader_records(self):
        out,err,native=fixture();lines=out.splitlines(keepends=True)
        library=next(x for x in lines if x.startswith(P+'library '))
        compute=next(x for x in lines if x.startswith(P+'values phase=compute-B'))
        half=next(x for x in lines if x.startswith(P+'half_pixels '))
        gamma=next(x for x in lines if x.startswith(P+'pixels phase=gamma-BGRA '))
        texture_a=next(x for x in lines if x.startswith(P+'pixels phase=textured-A '))
        texture_b=next(x for x in lines if x.startswith(P+'pixels phase=textured-B '))
        mutations=[out.replace(library,''),out.replace(library,library*2),out.replace(library,'interleaved '+library),
                   out.replace('library bytes=1024','library bytes=1025'),out.replace(LIBRARY,'b'*64),
                   out.replace(compute,''),out.replace(compute,compute*2),
                   out.replace(compute,compute.replace('hash=','hash=0')),
                   out.replace(texture_b,texture_b.replace(texture_b.split('hash=')[1][:16],texture_a.split('hash=')[1][:16])),
                   out.replace(half,''),out.replace(half,half.replace('pixels=4096','pixels=4095')),
                   out.replace(gamma,''),out.replace('render_states=7','render_states=6'),
                   out.replace('functions=5 compute=1','functions=5 compute=0'),
                   out.replace('footprint=33554432','footprint=134217729',1),
                   out.replace('jobs=93','jobs=83'),out.replace('shader-pipelines=1','shader-pipelines=0'),
                   out.replace('ownership reacquired=1','ownership reacquired=0'),
                   out.replace('scope=root-offscreen-shader-pipelines-not-CA','scope=root-offscreen-objects-not-CA'),
                   out+P+'unexpected marker\n',out+'GAUGUIN METAL223 stale run\n']
        for changed in mutations:
            self.assertNotEqual(changed,out)
            with self.subTest(tail=changed[-100:]),self.assertRaises(ValueError):qualify(changed,err,native)

    def test_reject_wrong_expected_artifact_and_native_scope(self):
        for params in [dict(build='f'*24),dict(library_sha256='f'*64),dict(library_bytes=1025)]:
            with self.assertRaises(ValueError):qualify(*fixture(),**params)
        out,err,native=fixture()
        for changed in [trace(83),native+'SWEET GPU AUTH: compositor opened pid=57 root_fence=93\n',
                        native+'SWEET GPU USER: client closed after fault; fixture\n']:
            with self.assertRaises(ValueError):qualify(out,err,changed)

    def test_reject_unadmitted_or_refused_runtime(self):
        out,err,native=fixture()
        for changed in [err.replace('methods=12','methods=11'),err+'HakiosMetal: refused: fragment pipeline\n']:
            with self.assertRaises(ValueError):qualify(out,changed,native)

if __name__=='__main__':unittest.main(verbosity=2)
