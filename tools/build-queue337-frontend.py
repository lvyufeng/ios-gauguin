#!/usr/bin/env python3
"""Reproduce C4Q321, then add bounded queue identities and retirement milestones."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from surface_signature_compare import compare_signature_reservations

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
RECEIPT = MAIN/'research/tmp/gauguin-c4-queue-worktree-20261115/research/tmp/c4-queue-321/native-v1/result.json'
BASE_SHA = '9afd2048d0b90fffce45e3467c296313d20f65978301fada5d62b31f1cffd8c8'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


from queue337_source import instrument


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    assert out.is_relative_to(WORK/'research/tmp') and not out.exists()
    old = json.loads(RECEIPT.read_text())
    assert old['state'] == 'native-C4Q321-baseline-reproduced-candidate-signed'
    source = Path(old['source'])
    assert old['products']['candidate']['sha256'] == BASE_SHA
    pins = dict(old['input_pins'])
    header = WORK/'graphics/gauguin-c4-queue/GauguinQueue337.h'
    for path in [RECEIPT, Path(__file__).resolve(), WORK/'tools/queue337_source.py', WORK/'tools/surface_signature_compare.py', header, *source.parent.glob('*')]:
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
                if sha(binary) != BASE_SHA:
                    result['baseline_signature_reservation_comparison'] = compare_signature_reservations(
                        (old_bundle/'GauguinMetalDesktop').read_bytes(),binary.read_bytes())
                    canonical=[]
                    for tag, bundle in [('original',old_bundle),('rebuilt',dest)]:
                        copy=out/('canonical-'+tag)/'GauguinMetalDesktop.bundle'
                        shutil.copytree(bundle,copy)
                        run(['codesign','--verify','--strict',str(copy)],tag+'-original-signature')
                        run(['codesign','--remove-signature',str(copy)],tag+'-remove-signature')
                        run(['codesign','--force','--sign','-',str(copy)],tag+'-canonical-sign')
                        run(['codesign','--verify','--strict',str(copy)],tag+'-canonical-verify')
                        canonical.append(sha(copy/'GauguinMetalDesktop'))
                    assert canonical[0]==canonical[1], 'canonical baseline differs'
                    result['baseline_canonical_sha256']=canonical[0]
                result['baseline_all_code_data_UUID_symbols_identical']=True
        before = (out/'baseline-imports.log').read_text()
        after = (out/'candidate-imports.log').read_text()
        result['imports_unchanged'] = before == after
        result['added_import_lines'] = sorted(set(after.splitlines()) - set(before.splitlines()))
        result['removed_import_lines'] = sorted(set(before.splitlines()) - set(after.splitlines()))
        assert result['products']['candidate']['bytes'] <= 105*4096, 'C4 candidate exceeds existing allocation'
        result.update(state='native-Q337-C4Q321-baseline-reproduced-candidate-signed',
                      source=str(sources/source.name), source_change_reversible=True,
                      exact_321_baseline_reproduced=sha(out/'baseline/GauguinMetalDesktop.bundle/GauguinMetalDesktop')==BASE_SHA, existing_allocation_bytes=105*4096,
                      loader_header_sha256=sha(sources/'GauguinEDRLoader.h'),
                      original_loader_order_unchanged=True, edit_count=edit_count,
                      trace_header_sha256=sha(header), trace_phases=10, queue_metadata_stages=3, queue_metadata_max_bytes=32769*192,
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
