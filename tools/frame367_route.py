"""Decode the bounded read-only SSPP and CTL snapshot."""

import re

PREFIX = 'SWEET F367 '
FB = re.compile(r'FB: base=([0-9a-f]{1,16}) width=(\d+) height=(\d+) stride=(\d+)')
DONE = re.compile(r'ROUTE: status=(stable|map-failed|unstable|stopped) attempts=(\d+) samples=(\d+) first=(\d+) last=(\d+)')
FIELDS = re.compile(r'(CTL|SSPP): index=([0-3]) fields=([0-9a-f]{8}(?:,[0-9a-f]{8})+)')
PIPE_BASES = (0x0ae05000, 0x0ae25000, 0x0ae27000, 0x0ae29000)
PIPE_NAMES = ('VIG0', 'DMA0', 'DMA1', 'DMA2')
FB_LENGTH = 10_368_000
MASK = (1 << 32) - 1


def require(condition, statement):
    if not condition:
        raise ValueError(statement)


def mixer_sources(words):
    """Decode Lagoon's primary and virtual stage fields for the four catalog pipes."""
    layer, ext, ext2, ext3 = words
    primary = (
        (layer & 7) or (ext & 1),
        (layer & (7 << 18)) or (ext & (1 << 16)),
        (layer & (7 << 21)) or (ext & (1 << 18)),
        ext2 & 15,
    )
    virtual = (ext3 & 15, ext2 & (15 << 8), ext2 & (15 << 12), ext2 & (15 << 16))
    return tuple(i for i,v in enumerate(primary) if v), tuple(i for i,v in enumerate(virtual) if v)


def match_route(framebuffer, controls, pipes):
    source = [i for i,p in pipes.items() if p[4]==framebuffer]
    control = [i for i,c in controls.items() if c[2] & 2]
    if len(source)!=1 or len(control)!=1:
        return None,'source-or-control-not-unique'
    pipe_index, = source
    control_index, = control
    p = pipes[pipe_index]
    top, flush, interface, *stages = controls[control_index]
    mixers = [mixer_sources(stages[i:i+4]) for i in (0,4)]
    if interface!=2 or [k for active,_ in mixers for k in active]!=source or any(v for _,v in mixers):
        return None,'source-not-uniquely-staged'
    size, xy, out_size, out_xy, addr, pitch, fmt, op, multirect = p
    geometry = (2400 << 16) | 1080
    unsupported_format = (3 << 30) | (1 << 22) | (3 << 19) | (1 << 11)
    unsupported_ops = (1 << 22) | (1 << 14) | (1 << 13) | 1
    if (size!=geometry or out_size!=geometry or xy or out_xy or pitch!=4320 or
            fmt & unsupported_format or ((fmt >> 9) & 3)!=3 or op & unsupported_ops or
            multirect or top & (1 << 17) or flush):
        return None,'unsupported-pixel-layout-or-pending-flush'
    return dict(pipe=PIPE_NAMES[pipe_index],source_base=PIPE_BASES[pipe_index],
        source_address_register=PIPE_BASES[pipe_index]+0x14,control_index=control_index,
        ctl_base=0x0ae02000+0x200*control_index,interface=1,framebuffer=addr),None


def decode(text):
    framebuffer = terminal = None
    controls, pipes = {}, {}
    for line in text.splitlines():
        _,tag,body = line.partition(PREFIX)
        if not tag:
            continue
        require(terminal is None,'F367 record after terminal receipt')
        if match := DONE.fullmatch(body):
            terminal = match.groups()
        elif match := FB.fullmatch(body):
            require(framebuffer is None,'duplicate inherited framebuffer receipt')
            base,width,height,stride = match.groups()
            framebuffer = (int(base,16),int(width),int(height),int(stride))
        else:
            match = FIELDS.fullmatch(body)
            require(match is not None,'malformed F367 register record')
            lane,index,packed = match.groups()
            target = controls if lane=='CTL' else pipes
            index = int(index)
            fields = tuple(int(word,16) for word in packed.split(','))
            require(index not in target and len(fields)==(11 if lane=='CTL' else 9),
                    'duplicate or partial F367 register record')
            target[index] = fields
    require(terminal is not None,'missing F367 terminal receipt')
    status,*values = terminal
    attempts, samples, first, last = map(int,values)
    require(0<=samples<=attempts<=8 and first<=MASK and last<=MASK,'F367 budget or frame counter differs')
    report = dict(snapshot_status=status,attempts=attempts,samples=samples,first_scan=first,last_scan=last,
        display_address_translation_qualified=False,hardware_latch_qualified=False)
    if status!='stable':
        require(samples<3 and framebuffer is None and not controls and not pipes,'partial accepted F367 snapshot')
        return report
    require(samples==3 and 2<=((last-first)&MASK)<0x80000000 and framebuffer and len(controls)==len(pipes)==4,
            'stable F367 snapshot incomplete')
    base,width,height,stride = framebuffer
    require(0<base<=(1 << 32)-FB_LENGTH and not base%16384 and (width,height,stride)==(1080,2400,4320),
            'F367 inherited framebuffer layout differs')
    route,reason = match_route(base,controls,pipes)
    return report | dict(inherited_framebuffer=base,frame_bytes=FB_LENGTH,pipe_words=pipes,control_words=controls,
        route=route,mismatch=reason)
