#!/usr/bin/env python3
"""Synthetic timelines test partial ordering, reused pointers and lost evidence."""
from pathlib import Path
import hashlib
import importlib.util
import json

WORK = Path(__file__).resolve().parents[1]
SOURCE = WORK/'tools/analyze-c4-queue-log.py'
spec = importlib.util.spec_from_file_location('queue_log', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def timeline(made=225000000, obj='0x1234', inline=False):
    times = [made+100, made+200, made+300, made+400, made+500,
             made+600, made+700, made+900]
    if inline:
        times[3:5] = [made+1000, made+1100]
    rows = [f'GAUGUIN C4Q321: phase={phase} object={obj} start_us={made} end_us={end} value={2 if phase == 4 else 0}'
            for phase, end in enumerate(times)]
    # Intentionally emit the array in a different order: log-stream ordering
    # between threads is not a timestamp or a happens-before relationship.
    rows = [rows[i] for i in (0, 1, 2, 5, 6, 3, 4, 7)]
    rows += [f'tl: M made {made} committed {times[0]} done {made+800} gpu 200']
    return '\n'.join(rows)+'\n'


def main():
    checks = 0

    def check(condition):
        nonlocal checks
        assert condition
        checks += 1

    raw = timeline()
    parsed = module.analyze(raw)
    check(parsed['coverage_qualified'] and parsed['complete_cb_count'] == 1)
    check(parsed['stage_us']['frontend_queue']['median'] == 100)
    check(parsed['stage_us']['callback_to_handlers_posted']['median'] == 200)
    check(not parsed['physical_FPS_qualified'])
    inline = module.analyze(timeline(inline=True))
    check(inline['coverage_qualified'])
    check(inline['stage_us']['core_commit_call']['median'] == 700)
    check(inline['stage_us']['core_call_to_callback']['median'] == 300)
    reused = module.analyze(raw+timeline(made=226000000))
    check(reused['coverage_qualified'] and reused['complete_cb_count'] == 2)
    check(not module.analyze('')['coverage_qualified'])
    for phase in range(8):
        lost = '\n'.join(row for row in raw.splitlines() if f'phase={phase} ' not in row)
        check(not module.analyze(lost)['coverage_qualified'])
    for bad in (raw+raw.splitlines()[0]+'\n', raw+module.LIMIT+'\n',
                raw.replace('phase=2', 'phase=9'), raw.replace('object=0x1234', 'object=0x0'),
                raw.replace('start_us=225000000', 'start_us=219999999'),
                raw.replace('end_us=225000300', 'end_us=225000100'),
                raw.replace('end_us=225000600', 'end_us=225000299'),
                raw.replace('done 225000800', 'done 225000950'),
                raw.replace('committed 225000100', 'committed 225000101'),
                raw+raw.splitlines()[-1]+'\n',
                raw+'GAUGUIN C4Q321: phase=broken\n',
                raw+'GAUGUIN C4Q321: phase=0 object=0x1 start_us=nan end_us=1 value=0\n'):
        check(not module.analyze(bad)['coverage_qualified'])
    extras = ('GAUGUIN C4Q321: phase=8 object=0x999 start_us=226000000 end_us=233000000 value=1\n'
              'GAUGUIN C4Q321: phase=9 object=0xabc start_us=226000000 end_us=226100000 value=0\n')
    spans = module.analyze(raw+extras)
    check(spans['coverage_qualified'])
    check(spans['compiler_span_us']['8']['max'] == 7000000)
    check(spans['compiler_span_us']['9']['max'] == 100000)
    check(not module.analyze(raw+extras.replace('value=1', 'value=2'))['coverage_qualified'])
    check(parsed['eligible_timeline_count'] == 1)
    missing_whole = timeline(made=226000000).splitlines()[-1]+'\n'
    check(not module.analyze(raw+missing_whole)['coverage_qualified'])
    aliased = '\n'.join(row.replace('object=0x1234', 'object=0x5678')
                        for row in raw.splitlines() if not row.startswith('tl: M'))+'\n'
    check(not module.analyze(raw+aliased)['coverage_qualified'])
    for made in (219000000, 271000000):
        outside = timeline(made=made).splitlines()[-1]+'\n'
        check(module.analyze(raw+outside)['coverage_qualified'])
    path = WORK/'research/tmp/c4-queue-321/parser-test.json'
    result = dict(state='passed-C4Q321-partial-order-evidence-parser', checks=checks,
                  inline_completion_supported=True, pointer_reuse_supported=True,
                  missing_duplicate_and_limit_refused=True, device_commands=0,
                  whole_missing_trace_and_ambiguous_identity_refused=True,
                  input_pins={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (SOURCE, Path(__file__).resolve())})
    with path.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
