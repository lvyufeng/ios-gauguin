#!/usr/bin/env python3
"""Reproduce the qualified 0318 frontend, then add bounded CPU stage tracing."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct
import subprocess

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
RECEIPT = MAIN/'research/tmp/gauguin-c4-edr-loader-worktree-20261115/research/tmp/c4-edr-loader-318/c4-native-v3/result.json'
BASE_SHA = 'c74c12ddc7e14eea958d5905852a9db785f49e78cb089b533ddba772c0906ab8'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def instrument(raw):
    """Every edit is anchored once and mechanically reversible, in order."""
    edits = []

    def replace(before, after):
        nonlocal raw
        assert raw.count(before) == 1, before
        raw = raw.replace(before, after)
        edits.append((before, after))

    original = raw
    replace('#include "GauguinEDRLoader.h"\n',
            '#include "GauguinEDRLoader.h"\n#include "GauguinC4QueueTrace.h"\n')
    anchor = '\tid function = hm_gauguin_original_descriptor(library, selector, descriptor, error);'
    replace(anchor, '\tconst double gcq_specialize_start = hm_now();\n' + anchor +
            '\n\tgauguin_c4_queue_trace(9, library, gcq_specialize_start, hm_now(), function != nil);')
    anchor = '\t\tprogram = hakios_metal_program_new_bitcode_constants('
    replace(anchor, '\t\tconst double gcq_compile_start = hm_now();\n' + anchor)
    anchor = '\t\t\t\t\t\t\t\t     fsConstants, fsCount, format);'
    replace(anchor, anchor + '\n\t\tgauguin_c4_queue_trace(8, descriptor, gcq_compile_start, hm_now(), program != NULL);')
    anchor = '\tHakiosMetalCommandBuffer *self = (HakiosMetalCommandBuffer *)context;\n'
    replace(anchor, anchor + '\tgauguin_c4_queue_trace(5, self, [self hakiosCreatedAt], hm_now(), 0);\n')
    anchor = '\thm_timeline([self hakiosCreatedAt], [self GPUStartTime], hm_now(), (double)hakios_metal_cb_gpu_nanoseconds(cb) / 1e9);'
    replace(anchor, anchor + '\n\tgauguin_c4_queue_trace(6, self, [self hakiosCreatedAt], hm_now(), 0);')
    anchor = '\t\t[self hakiosCompletedNow];\n\t}\n\t[self release];'
    replace(anchor, '\t\t[self hakiosCompletedNow];\n'
            '\t\tgauguin_c4_queue_trace(7, self, [self hakiosCreatedAt], hm_now(), 0);\n\t}\n\t[self release];')
    anchor = '\t\t_committedAt = hm_now();\n\t\t[_stateCondition unlock];'
    replace(anchor, anchor + '\n\t\tgauguin_c4_queue_trace(0, self, _createdAt, _committedAt, 0);')
    anchor = '\t\t[_queue hakiosAdmit:^{\n'
    replace(anchor, anchor + '\t\t\tgauguin_c4_queue_trace(1, self, _createdAt, hm_now(), 0);\n')
    anchor = '\t\t\tconst double began = hm_now();\n\t\t\thakios_metal_cb_commit(_cb, hm_completed, self);'
    replace(anchor, '\t\t\tconst double began = hm_now();\n'
            '\t\t\tgauguin_c4_queue_trace(2, self, _createdAt, began, 0);\n'
            '\t\t\thakios_metal_cb_commit(_cb, hm_completed, self);\n'
            '\t\t\tgauguin_c4_queue_trace(3, self, _createdAt, hm_now(), 0);')
    anchor = '\t\t\tenum hakios_metal_status state = hakios_metal_cb_status(_cb);'
    replace(anchor, anchor + '\n\t\t\tgauguin_c4_queue_trace(4, self, _createdAt, hm_now(), (unsigned)state);')
    undone = raw
    for before, after in reversed(edits):
        assert undone.count(after) == 1
        undone = undone.replace(after, before)
    assert undone == original
    assert raw.count('gauguin_c4_queue_trace(') == 10
    return raw, len(edits)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    old = json.loads(RECEIPT.read_text())
    assert old['state'] == 'native-C4-EDR318-baseline-reproduced-candidate-signed'
    source = Path(old['source'])
    assert old['products']['candidate']['sha256'] == BASE_SHA
    pins = dict(old['input_pins'])
    header = WORK/'graphics/gauguin-c4-queue/GauguinC4QueueTrace.h'
    for path in [RECEIPT, Path(__file__).resolve(), header, *source.parent.glob('*')]:
        pins[str(path)] = sha(path)
    for item in old['products'].values():
        assert sha(item['binary']) == item['sha256']
        pins[item['binary']] = item['sha256']
    for name, digest in pins.items():
        assert sha(name) == digest, name
    out.mkdir(parents=True)
    sources = out/'sources'
    sources.mkdir()
    for path in source.parent.glob('*'):
        shutil.copyfile(path, sources/path.name)
    shutil.copyfile(header, sources/header.name)
    changed, edit_count = instrument(source.read_text())
    (sources/source.name).write_text(changed)
    result = dict(state='C4Q321-build-started', input_pins=pins, products={}, steps=[],
                  device_commands=0, runtime_qualified=False)

    def run(argv, label):
        with (out/(label+'.log')).open('x') as stream:
            proc = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT)
        result['steps'].append(dict(label=label, argv=argv, exit=proc.returncode))
        assert proc.returncode == 0, label

    try:
        old_bundle = Path(old['products']['candidate']['binary']).parent
        original_receipt = MAIN/'research/tmp/metal-ca-c4-20261112/native-final-v3/result.json'
        original = json.loads(original_receipt.read_text())
        original_source = Path(original['source'])
        for variant in ('baseline', 'candidate'):
            folder = source.parent if variant == 'baseline' else sources
            dest = out/variant/'GauguinMetalDesktop.bundle'
            dest.mkdir(parents=True)
            shutil.copyfile(old_bundle/'Info.plist', dest/'Info.plist')
            binary = dest/'GauguinMetalDesktop'
            argv = list(original['compiler_argv'])
            argv[argv.index('-o')+1] = str(binary)
            argv = [str(folder/Path(x).name) if x.endswith('.m') and Path(x).parent == original_source.parent else x for x in argv]
            argv.insert(argv.index('-o'), '-fmacro-prefix-map='+str(folder)+'='+str(original_source.parent))
            run(argv, variant+'-compile')
            run(['codesign', '--force', '--sign', '-', str(dest)], variant+'-sign')
            run(['codesign', '--verify', '--strict', str(dest)], variant+'-verify')
            run(['nm', '-m', '-u', str(binary)], variant+'-imports')
            run(['otool', '-L', str(binary)], variant+'-loads')
            for name in ('Info.plist', '_CodeSignature/CodeResources'):
                assert sha(dest/name) == sha(old_bundle/name)
            data = binary.read_bytes()
            mh = struct.unpack_from('<8I', data)
            assert mh[:2] == (0xfeedfacf, 0x100000c) and mh[3] == 8
            at = 32
            platforms = []
            for _ in range(mh[4]):
                tag, size = struct.unpack_from('<II', data, at)
                assert size >= 8 and at+size <= 32+mh[5]
                if tag == 0x32:
                    platforms.append(struct.unpack_from('<III', data, at+8))
                at += size
            assert at == 32+mh[5] and len(platforms) == 1 and platforms[0][:2] == (2, 0x100000)
            result['products'][variant] = dict(binary=str(binary), sha256=sha(binary), bytes=len(data),
                                                platform=platforms[0], resources_unchanged=True)
            if variant == 'baseline':
                assert sha(binary) == BASE_SHA, '0318 baseline reproduction differs'
        before = (out/'baseline-imports.log').read_text()
        after = (out/'candidate-imports.log').read_text()
        result['imports_unchanged'] = before == after
        result['added_import_lines'] = sorted(set(after.splitlines()) - set(before.splitlines()))
        result['removed_import_lines'] = sorted(set(before.splitlines()) - set(after.splitlines()))
        assert result['products']['candidate']['bytes'] <= 105*4096, 'C4 candidate exceeds existing allocation'
        result.update(state='native-C4Q321-baseline-reproduced-candidate-signed',
                      source=str(sources/source.name), source_change_reversible=True,
                      exact_318_baseline_reproduced=True, existing_allocation_bytes=105*4096,
                      loader_header_sha256=sha(sources/'GauguinEDRLoader.h'),
                      original_loader_order_unchanged=True, edit_count=edit_count,
                      trace_header_sha256=sha(header), trace_phases=10,
                      trace_record_limit=32768, trace_max_bytes=32769*128,
                      additional_GPU_calls=0, additional_threads=0)
    except Exception as error:
        result.update(state='C4Q321-build-failed', error=repr(error))
        raise
    finally:
        result['inputs_unchanged'] = all(sha(name) == digest for name, digest in pins.items())
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps({k: v for k, v in result.items() if k not in ('input_pins', 'steps')}, indent=2))


if __name__ == '__main__':
    main()
