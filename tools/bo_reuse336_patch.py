"""Adapt the bounded completed-BO cache to new sizes without growing it.

Only retire335 changes policy: at a capacity refusal, rotate out at most one
completed cached mapping which frees enough space. The original new-buffer
release remains the fallback. Never flush multiple mappings for one return.
"""

OLD_RETIRE = '''    if(eligible&&memory->getRetainCount()==1&&fCachedCount<kCache335Slots&&
       b->mappingSize<=kCache335Bytes-fCachedBytes) {
        b->handle=0;b->closePending=false;b->cached=true;
        ++fCachedCount;fCachedBytes+=b->mappingSize;
        cache335_count(&gCache335.stores);cacheState335();return true;
    }
'''

NEW_RETIRE = '''    if(eligible&&memory->getRetainCount()==1) {
        if(fCachedCount>=kCache335Slots||b->mappingSize>kCache335Bytes-fCachedBytes) {
            const uint64_t available=kCache335Bytes-fCachedBytes;
            const uint64_t required=b->mappingSize>available?b->mappingSize-available:0;
            gpu_buffer *victim=nullptr;uint32_t next=fCacheCursor336;
            // One rotating victim only. A larger new class which would need
            // multiple SMMU removals keeps the original release-new fallback.
            for(uint32_t step=0;step<GGR_MAX_CLIENT_BUFFERS;step++) {
                uint32_t index=(fCacheCursor336+step)%GGR_MAX_CLIENT_BUFFERS;
                gpu_buffer *old=fBuffers+index;
                if(old->cached&&old->memory&&old->installed&&!old->pending&&
                   !old->closePending&&old->mappingSize>=required) {
                    victim=old;next=(index+1)%GGR_MAX_CLIENT_BUFFERS;break;
                }
            }
            if(victim) {
                if(!drop(victim))return false; // retain original DMA escrow on failure
                fCacheCursor336=next;
            }
        }
        if(fCachedCount<kCache335Slots&&b->mappingSize<=kCache335Bytes-fCachedBytes) {
            b->handle=0;b->closePending=false;b->cached=true;
            ++fCachedCount;fCachedBytes+=b->mappingSize;
            cache335_count(&gCache335.stores);cacheState335();return true;
        }
    }
'''

CHANGES = (
    ('    uint32_t fCachedCount;\n', '    uint32_t fCachedCount,fCacheCursor336;\n'),
    ('    fCachedBytes=0;fCachedCount=0;fCacheEnabled=false;\n',
     '    fCachedBytes=0;fCachedCount=0;fCacheCursor336=0;fCacheEnabled=false;\n'),
    (OLD_RETIRE, NEW_RETIRE),
)


def transform(text, reverse=False):
    for old, new in reversed(CHANGES) if reverse else CHANGES:
        before, after = (new, old) if reverse else (old, new)
        assert text.count(before) == 1, before[:100]
        text = text.replace(before, after)
    return text
