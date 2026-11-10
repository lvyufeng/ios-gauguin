"""Validate93-job MTL shader evidence; discovery/CA/FPS remain separate.

Caller binds exact installed artifacts, full old log prefixes and strict image
identity. These CPU expectations never derive from the GPU's reported hashes.
"""
import re
from metal_probe_log import fnv,need,records,single,binary_color
from metal_frontend_log import expected_hashes as object_hashes
from gpu_service_log import qualify_service_log
P='GAUGUIN METAL227 '

def shader_hashes(seed):
    need(type(seed) is int and 0<=seed<2**32,'invalid seed')
    out={}
    for bgra in (False,True):
        pixels=[]
        vertices=((0,0),(128,0),(0,126))
        for y in range(64):
            for x in range(64):
                a,b=2*x+1,2*y+1
                inside=all((dx-cx)*(b-cy)-(dy-cy)*(a-cx)>0 for (cx,cy),(dx,dy) in zip(vertices,vertices[1:]+vertices[:1]))
                red,blue=(0xffff0000,0xff0000ff) if bgra else (0xff0000ff,0xffff0000)
                pixels.append(red if inside else blue)
        out['triangle-BGRA' if bgra else 'triangle-RGBA']=fnv(pixels,4)
    for phase,current in [('textured-A',seed),('textured-B',seed^8)]:
        out[phase]=fnv([binary_color((current&7)^(7 if (x//8+y//8+(current>>3))&1 else 0))
                        for y in range(64) for x in range(64)],4)
    out['additive-RGBA']=fnv([0xff00ffff]*4096,4)
    out['gamma-RGBA']=out['gamma-BGRA']=fnv([0xffbcbcbc]*4096,4)
    compute={phase:fnv([((i*0x9e3779b1)+current)&0xffffffff for i in range(256)],4)
             for phase,current in [('compute-A',seed),('compute-B',seed^0xa5a5f00d)]}
    return out,compute,fnv([0x3c00000038003800]*4096,8)

def qualify_shader_log(stdout,stderr,native,*,build,library_sha256,library_bytes):
    need(re.fullmatch('[0-9a-f]{24}',build) is not None and re.fullmatch('[0-9a-f]{64}',library_sha256) is not None,'invalid pinned identities')
    need(type(library_bytes) is int and 88<library_bytes<1048576,'invalid pinned library length')
    need(P+'FAIL' not in stdout+'\n'+stderr and 'GAUGUIN METAL226 ABI rejected' not in stderr,'probe/ABI failure')
    need('GAUGUIN METAL223 ' not in stdout and 'GAUGUIN METAL226 ' not in stdout,'wrong probe mode')
    begin=single(records(stdout,P+'begin ',P+r'begin build=([0-9a-f]{24}) delay=90 scope=root-offscreen-shader-pipelines-not-CA'),'begin')
    need(begin[1]==(build,),'begin build differs')
    device=single(records(stdout,P+'device=',P+r'device=Adreno \(hakios-metal, chip 0x6010900\) seed=(\d+) maxBO=67108864 queueSlots=4'),'device')
    seed=int(device[1][0]);need(seed<2**32,'seed overflow')
    base=object_hashes(seed);render,compute,half_hash=shader_hashes(seed);expected={**base,**render}
    memory=records(stdout,P+'memory ',P+r'memory phase=(\S+) active=128 inactive=128 hard=1 footprint=(\d+)')
    need([x[1][0] for x in memory]==['before-delay','opened','shader-compute-compiled','shader-render-completed','after-resource-release'],'memory checkpoint set/order differs')
    need(all(0<int(x[1][1])<=128*1024*1024 for x in memory),'memory footprint bound differs')
    pixels=records(stdout,P+'pixels ',P+r'pixels phase=(\S+) words=4096 hash=([0-9a-f]{16}) PASS')
    need([x[1][0] for x in pixels]==list(expected) and all(digest==expected[phase] for _,(phase,digest) in pixels),'pixel phase/order/CPU-expected hash differs')
    positions={phase:at for at,(phase,_) in pixels}
    abandoned=single(records(stdout,P+'abandoned-slots ',P+r'abandoned-slots count=80 PASS'),'abandoned slots')
    surface=single(records(stdout,P+'surface ',P+r'surface id=(\d+) width=64 height=64 stride=256 format=BGRA cases=3 PASS'),'surface')
    need(0<int(surface[1][0])<2**32,'bad surface ID')
    library=single(records(stdout,P+'library ',P+r'library bytes=(\d+) sha256=([0-9a-f]{64})'),'library')
    need(library[1]==(str(library_bytes),library_sha256),'actual loaded library differs')
    first=single(records(stdout,P+'pipelines functions=',P+r'pipelines functions=5 compute=1'),'compute pipeline')
    last=single(records(stdout,P+'pipelines render_states=',P+r'pipelines render_states=7 render_jobs=8 jobs=10 pixel_checks=32768 compute_words=512 PASS'),'render pipelines')
    values=records(stdout,P+'values ',P+r'values phase=(\S+) words=256 hash=([0-9a-f]{16}) PASS')
    need([x[1][0] for x in values]==list(compute) and all(digest==compute[phase] for _,(phase,digest) in values),'compute updates or hashes differ')
    half=single(records(stdout,P+'half_pixels ',P+r'half_pixels phase=premul-half pixels=4096 hash=([0-9a-f]{16}) PASS'),'half blending')
    need(half[1]==(half_hash,),'RGBA16F premultiplied readback differs')
    owner=single(records(stdout,P+'ownership ',P+r'ownership reacquired=1 closed=1 PASS'),'owner return')
    result=single(records(stdout,P+'RESULT ',P+r'RESULT PASS build=([0-9a-f]{24}) seed=(\d+) jobs=93 pixel_checks=372736 compute_words=512 half_pixels=4096 abandoned=80 teardown-requested=1 discovery=0 shader-pipelines=1 UI=0'),'result')
    need(result[1]==(build,str(seed)),'result identity differs')
    need(begin[0]<memory[0][0]<device[0]<memory[1][0]<pixels[0][0]<pixels[7][0]<abandoned[0]<pixels[8][0],'startup/base order differs')
    need(positions['surface-CPU-to-GPU-B']<surface[0]<library[0]<memory[2][0]<first[0]<values[0][0]<values[1][0]<positions['triangle-RGBA'],'library/compute order differs')
    need(positions['additive-RGBA']<half[0]<positions['gamma-RGBA']<positions['gamma-BGRA']<memory[3][0]<last[0]<memory[4][0]<owner[0]<result[0],'render/lifetime order differs')
    known={r[0] for rows in ([begin],[device],memory,pixels,[abandoned],[surface],[library],[first],[last],values,[half],[owner],[result]) for r in rows}
    need({i for i,line in enumerate(stdout.splitlines()) if P in line}==known,'unknown/truncated/interleaved receipt')
    admitted=single(records(stderr,'GAUGUIN METAL226 admitted ',r'GAUGUIN METAL226 admitted OS=20H392 methods=12 ivars=2 root-only no-discovery'),'runtime ABI admission')
    need({i for i,line in enumerate(stderr.splitlines()) if 'GAUGUIN METAL226 ' in line}=={admitted[0]},'unexpected ABI output')
    refusals=[line for line in stderr.splitlines() if 'refused:' in line]
    need(len(refusals)==1 and refusals[0].endswith('refused: buffer length 67108865 outside 1..64MiB kernel cap'),'unexpected operation refusal')
    service=qualify_service_log(native,expected_seconds=600);need(service['native_submissions']==93,'93 native completed jobs required')
    need('SWEET GPU AUTH: compositor opened ' not in native and 'SWEET GPU USER: client closed after fault;' not in native,'competing/faulted GPU owner')
    return dict(state='qualified227-bounded-public-MTL-shaders-only',build=build,seed=seed,library_sha256=library_sha256,
                jobs=93,pixel_checks=372736,compute_words=512,half_pixels=4096,render_states=7,
                owner_reacquired=True,device_discovery_qualified=False,desktop_qualified=False,
                high_refresh_qualified=False,shader_subset_qualified=True,finite_service=service)
