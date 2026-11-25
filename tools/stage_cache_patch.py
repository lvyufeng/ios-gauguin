"""Exact, reversible cache-lock-only edits to the qualified compiler source."""


def instrument(raw):
    original, edits = raw, []

    def edit(before, after):
        nonlocal raw
        assert raw.count(before) == 1, before
        raw = raw.replace(before, after)
        edits.append((before, after))

    edit('#include <mutex>\n', '#include <mutex>\n#include "GauguinStageCacheTrace.hpp"\n')
    start = raw.index('std::unique_ptr<CompiledStage> compileStage(const void* bitcode, size_t size, std::string* why, const FunctionConstants& constants, uint32_t iboBase,')
    end = raw.index('\n\n\n\nnamespace {', start)
    before = raw[start:end]
    after = before.replace('    std::lock_guard<std::mutex> g(gCompilerLock);\n',
        '    GauguinStageCacheTrace trace(known != nullptr, size);\n')
    after = after.replace('        refuse(why, "ir3 has no compiler for the selected GPU profile");',
        '        trace.mark(1); trace.outcome = 4;\n        refuse(why, "ir3 has no compiler for the selected GPU profile");')
    after = after.replace('    const std::string name = stageCacheName(',
        '    trace.mark(1);\n    const std::string name = stageCacheName(')
    cache_start = after.index('    if (!cached.empty()) {')
    cache_end = after.index('    std::unique_ptr<CompiledStage> with =', cache_start)
    block = after[cache_start:cache_end]
    block = block.replace('if (std::unique_ptr<CompiledStage> s = stageCacheLoad(cached)) return s;',
        'if (std::unique_ptr<CompiledStage> s = stageCacheLoad(cached)) { trace.source = 1; return s; }')
    block = block.replace('if (std::unique_ptr<CompiledStage> s = stageCacheLoad(dir + name)) return s;',
        'if (std::unique_ptr<CompiledStage> s = stageCacheLoad(dir + name)) { trace.source = 2; return s; }')
    replacement = '''    trace.setKey(name.c_str()); trace.mark(2);
    // Cached stages own their vectors and rebind their pointers. Atomic rename
    // publishes complete files; only the miss/compile/save path needs Mesa's lock.
    auto loadCached = [&]() -> std::unique_ptr<CompiledStage> {
BLOCK        return nullptr;
    };
    if (std::unique_ptr<CompiledStage> s = loadCached()) {
        trace.mark(3); trace.outcome = 1; return s;
    }
    trace.mark(3); trace.mark(4);
    std::lock_guard<std::mutex> g(gCompilerLock);
    trace.mark(5);
    // A writer may have filled this key while this invocation waited.
    if (std::unique_ptr<CompiledStage> s = loadCached()) {
        trace.mark(6); trace.outcome = 2; return s;
    }
    trace.mark(6);
'''.replace('BLOCK', ''.join('    '+line+'\n' for line in block.splitlines()))
    after = after[:cache_start] + replacement + after[cache_end:]
    after = after.replace('    if (chosen != nullptr && !cached.empty()) stageCacheSave(cached, *chosen);',
        '    trace.mark(7);\n    if (chosen != nullptr && !cached.empty()) stageCacheSave(cached, *chosen);\n'
        '    trace.mark(8); trace.outcome = chosen != nullptr ? 3 : 0;')
    assert after.count('std::lock_guard<std::mutex> g(gCompilerLock);') == 1
    assert after.count('stageCacheSave(cached, *chosen)') == 1
    assert after.count('compileStageOnce(') == before.count('compileStageOnce(') == 2
    edit(before, after)
    undone = raw
    for before, after in reversed(edits):
        assert undone.count(after) == 1
        undone = undone.replace(after, before)
    assert undone == original
    return raw
