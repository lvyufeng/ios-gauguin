"""Write direct constants once into the PM4 stream, without temporary vectors."""

DECL_OLD = '    void packet(uint32_t opcode, const uint32_t* words, uint32_t count);\n'
DECL_NEW = DECL_OLD + '''    // Non-aliasing prefix/payload followed by zero padding; one type-7 packet.
    // Reject malformed shapes before changing the stream. No allocation after reserve.
    void packet(uint32_t opcode, const uint32_t* prefix, uint32_t prefixCount,
                const uint32_t* data, uint32_t count, uint32_t zeroWords);
'''
IMPL_OLD = '''void Stream::packet(uint32_t opcode, const uint32_t* words, uint32_t count) {
    command(opcode, count);
    words_.insert(words_.end(), words, words + count);
}
'''
IMPL_NEW = IMPL_OLD + '''
void Stream::packet(uint32_t opcode, const uint32_t* prefix, uint32_t prefixCount,
                    const uint32_t* data, uint32_t count, uint32_t zeroWords) {
    const uint64_t total = uint64_t(prefixCount) + count + zeroWords;
    if (total > 0x3fff || (prefixCount && !prefix) || (count && !data))
        throw std::length_error("invalid segmented PM4 packet");
    if (words_.max_size() - words_.size() < total + 1)
        throw std::length_error("PM4 stream too large");
    const size_t needed = words_.size() + size_t(total) + 1;
    if (needed > words_.capacity()) {
        const size_t capacity = words_.capacity();
        const size_t grown = capacity > words_.max_size() / 2 ? words_.max_size() : capacity * 2;
        words_.reserve(std::max(needed, grown));
    }
    command(opcode, uint32_t(total));
    if (prefixCount) words_.insert(words_.end(), prefix, prefix + prefixCount);
    if (count) words_.insert(words_.end(), data, data + count);
    words_.insert(words_.end(), zeroWords, 0u);
}
'''
LOAD_OLD = '''void loadDirect(pm4::Stream& st, const Stage& s, a6xx_state_type type, uint32_t dstOff, uint32_t units, const uint32_t* data, uint32_t dwords) {
    std::vector<uint32_t> w;
    w.reserve(3 + dwords);
    w.push_back(loadState6_0(dstOff, type, SS6_DIRECT, shaderBlock(s), units));
    w.push_back(0);
    w.push_back(0);
    w.insert(w.end(), data, data + dwords);
    st.packet(loadOpcode(s), w.data(), uint32_t(w.size()));
}
'''
LOAD_NEW = '''void loadDirect(pm4::Stream& st, const Stage& s, a6xx_state_type type, uint32_t dstOff, uint32_t units, const uint32_t* data, uint32_t dwords,
                uint32_t zeroWords = 0) {
    const uint32_t prefix[3] = {loadState6_0(dstOff, type, SS6_DIRECT, shaderBlock(s), units), 0, 0};
    st.packet(loadOpcode(s), prefix, 3, data, dwords, zeroWords);
}
'''
IMM_OLD = '''            std::vector<uint32_t> imm(s.k.immediates, s.k.immediates + s.k.numImmediates);
            imm.resize((imm.size() + 3) & ~size_t(3), 0);
            loadDirect(stream, s, ST6_CONSTANTS, s.k.immediatesOffsetVec4, uint32_t(imm.size() / 4), imm.data(), uint32_t(imm.size()));
'''
IMM_NEW = '''            const uint32_t padding = (0u - s.k.numImmediates) & 3u;
            const uint32_t units = uint32_t((uint64_t(s.k.numImmediates) + padding) / 4);
            loadDirect(stream, s, ST6_CONSTANTS, s.k.immediatesOffsetVec4, units, s.k.immediates, s.k.numImmediates, padding);
'''


def instrument(header, pm4, render):
    assert header.count(DECL_OLD) == pm4.count(IMPL_OLD) == render.count(LOAD_OLD) == render.count(IMM_OLD) == 1
    header = header.replace(DECL_OLD, DECL_NEW)
    pm4 = '#include <algorithm>\n#include <stdexcept>\n' + pm4.replace(IMPL_OLD, IMPL_NEW)
    render = render.replace(LOAD_OLD, LOAD_NEW).replace(IMM_OLD, IMM_NEW)
    return header, pm4, render
