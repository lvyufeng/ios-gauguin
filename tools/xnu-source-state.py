#!/usr/bin/env python3
"""Record or check the inputs used to stage an XNU tree.

The record lives in BUILD_ROOT/source-state, never in the compiled source.
An old .patch-set label alone is not accepted. `record` is used after fresh
replay, or explicitly after auditing an existing tree against that replay.
This is an input freshness check, not proof that source files are unmodified;
the build manifest separately hashes the actual source before compilation.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent


def staging_inputs(repo):
    names = [
        'deps/versions.env', 'deps/apply-patches.sh', 'deps/sync-watchdog.sh',
        'tools/xnu-patches.py', 'tools/xnu-stage-sdk.py', 'tools/xnu-post-patch.py',
        'tools/xnu-source-state.py', 'xnu/sweet_init_watchdog.h', 'xnu/patches/series',
    ]
    spec = importlib.util.spec_from_file_location('patch_series', repo / 'tools/xnu-patches.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names += [str(path.relative_to(repo)) for path in module.read_series(repo / 'xnu/patches/series')]
    names += [str(path.relative_to(repo)) for path in (repo / 'deps/mirror').rglob('*')
              if path.is_file() and '__pycache__' not in path.parts and '.git' not in path.parts]
    return {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in sorted(set(names))}


def sidecar(source, state_root):
    key = hashlib.sha256(str(source).encode()).hexdigest()[:16]
    return state_root / f'{source.name}-{key}.json'


def run(action, source, state_root, repo=REPO):
    source = source.resolve()
    state_root = state_root.resolve()
    if not (source / 'bsd/conf/files').is_file():
        raise ValueError(f'not an XNU source tree: {source}')
    if state_root.is_relative_to(source):
        raise ValueError('source-state directory must be outside the source tree')
    path = sidecar(source, state_root)
    inputs = staging_inputs(repo.resolve())
    if action == 'record':
        state_root.mkdir(parents=True, exist_ok=True)
        data = {'schema': 1, 'source': str(source), 'inputs': inputs}
        temporary = path.with_name(path.name + '.tmp')
        temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
        temporary.replace(path)
        print(f'Staging input record: {path}')
        return
    if not path.is_file():
        raise ValueError(f'no staging input record: {path}; replay into a fresh tree, or explicitly record '
                         'this tree only after auditing it against a fresh replay')
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or data.get('source') != str(source) or data.get('inputs') != inputs:
        raise ValueError(f'staging inputs changed: {path}; use a fresh source tree; existing source was preserved')
    print(f'Staging inputs match: {path}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('record', 'check'))
    parser.add_argument('source', type=Path)
    parser.add_argument('--state-root', type=Path, default=REPO / '.deps-cache/source-state')
    args = parser.parse_args()
    try:
        run(args.action, args.source, args.state_root)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
