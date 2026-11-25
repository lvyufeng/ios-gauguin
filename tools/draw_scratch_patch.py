"""Bounded per-command-buffer CPU scratch for the real draw encoder.

This changes neither packet encoding nor GPU resource ownership. All four
streams are copied/moved to their destinations before the scope guard clears
them, including refusal and exception paths. No global or thread-local cache.
"""

HEADER_OLD = '    std::unique_ptr<OpenPass> open_;\n'
HEADER_NEW = HEADER_OLD + '''    // CPU encoding scratch only; no GPU address refers to these vectors.
    // Keep at most 16 KiB per stream between draws, including failed draws.
    struct DrawScratch {
        static constexpr size_t kRetainedWords = 4096;
        pm4::Stream head, body, headSys, bodySys;
        void reset() noexcept {
            for (pm4::Stream* s : {&head, &body, &headSys, &bodySys}) {
                if (s->words().capacity() > kRetainedWords) *s = pm4::Stream{};
                else s->clear();
            }
        }
        struct Scope {
            DrawScratch& scratch;
            explicit Scope(DrawScratch& value) noexcept : scratch(value) { scratch.reset(); }
            ~Scope() { scratch.reset(); }
            Scope(const Scope&) = delete;
            Scope& operator=(const Scope&) = delete;
        };
    } drawScratch_;
'''
DRAW_OLD = '    Piece passTable;\n    pm4::Stream head, body, headSys, bodySys;\n'
DRAW_NEW = '''    Piece passTable;
    DrawScratch::Scope scratchScope(drawScratch_);
    pm4::Stream& head = drawScratch_.head;
    pm4::Stream& body = drawScratch_.body;
    pm4::Stream& headSys = drawScratch_.headSys;
    pm4::Stream& bodySys = drawScratch_.bodySys;
'''


def instrument(header, draw):
    assert header.count(HEADER_OLD) == draw.count(DRAW_OLD) == 1
    assert 'DrawScratch' not in header and 'drawScratch_' not in draw
    return header.replace(HEADER_OLD, HEADER_NEW), draw.replace(DRAW_OLD, DRAW_NEW)
