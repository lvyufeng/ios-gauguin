"""Build the same draw-state key on the stack; reuse its per-pass storage."""
OLD = '''    std::vector<uint8_t> staticKey;
    if (options.dedupRegs) {
        const void* ptrs[2] = {program.vs.k.words, program.fs.k.words};
        const uint32_t sizes[3] = {program.vs.k.numWords, program.fs.k.numWords, program.samples};
        auto add = [&](const void* p, size_t n) { staticKey.insert(staticKey.end(), static_cast<const uint8_t*>(p), static_cast<const uint8_t*>(p) + n); };
'''
NEW = '''    const void* ptrs[2] = {program.vs.k.words, program.fs.k.words};
    const uint32_t sizes[3] = {program.vs.k.numWords, program.fs.k.numWords, program.samples};
    constexpr size_t keyBytes = sizeof(ptrs) + sizeof(sizes) + sizeof(program.blend) + sizeof(program.moreBlend) + sizeof(encodeOptions);
    static_assert(keyBytes <= 1024, "bounded draw-state key");
    std::array<uint8_t, keyBytes> staticKey{};
    if (options.dedupRegs) {
        size_t keyAt = 0;
        auto add = [&](const void* p, size_t n) { memcpy(staticKey.data() + keyAt, p, n); keyAt += n; };
'''
EQUAL_OLD = '        if (joins && !open_->staticKey.empty() && open_->staticKey == staticKey) {\n'
EQUAL_NEW = '''        if (joins && open_->staticKey.size() == staticKey.size() &&
            std::equal(staticKey.begin(), staticKey.end(), open_->staticKey.begin())) {
'''
SAVE_OLD = '        open_->staticKey = forgot ? std::vector<uint8_t>() : std::move(staticKey);\n'
SAVE_NEW = '''        if (forgot) open_->staticKey.clear();
        else open_->staticKey.assign(staticKey.begin(), staticKey.end());
'''


def instrument(source):
    assert source.count(OLD) == source.count(EQUAL_OLD) == source.count(SAVE_OLD) == 1
    assert source.count('#include <algorithm>\n') == 1 and '#include <array>' not in source
    return source.replace('#include <algorithm>\n', '#include <algorithm>\n#include <array>\n').replace(OLD,NEW).replace(EQUAL_OLD,EQUAL_NEW).replace(SAVE_OLD,SAVE_NEW)
