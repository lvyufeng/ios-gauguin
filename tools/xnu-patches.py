#!/usr/bin/env python3
"""List or apply the explicit XNU patch series.

  xnu-patches.py list
  xnu-patches.py apply XNU_ROOT

Historical cumulative patches remain in xnu/patches for reference. Only files
listed in series are active. Each patch is checked before application and any
failure stops the replay. Start from a fresh staged source tree when retrying.
"""
import argparse
import os
from pathlib import Path
import subprocess


DEFAULT_SERIES = Path(__file__).resolve().parent.parent / 'xnu/patches/series'


def read_series(path):
    patches = []
    names = set()
    for number, line in enumerate(path.read_text().splitlines(), 1):
        name = line.strip()
        if not name or name.startswith('#'):
            continue
        if Path(name).name != name or not name.endswith('.patch'):
            raise ValueError(f'{path}:{number}: expected a patch filename')
        if name in names:
            raise ValueError(f'{path}:{number}: duplicate patch {name}')
        patch = path.parent / name
        if not patch.is_file():
            raise ValueError(f'{path}:{number}: missing patch {name}')
        names.add(name)
        patches.append(patch.resolve())
    if not patches:
        raise ValueError(f'{path}: empty patch series')
    return patches


def apply_series(root, patches):
    root = root.resolve()
    if not (root / 'bsd/conf/files').is_file():
        raise ValueError(f'{root}: not an XNU source tree')
    # A plain exported tree can live inside the port repository. Prevent git
    # from discovering that parent repository and silently skipping its files.
    env = dict(os.environ, GIT_CEILING_DIRECTORIES=str(root.parent))
    for patch in patches:
        print(f'Applying {patch.name}', flush=True)
        command = ['git', 'apply', '--whitespace=nowarn']
        subprocess.run(command + ['--check', str(patch)], cwd=root, env=env,
                       check=True)
        subprocess.run(command + [str(patch)], cwd=root, env=env, check=True)
    print(f'Applied {len(patches)} patches to {root}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--series', type=Path, default=DEFAULT_SERIES)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('list')
    apply = commands.add_parser('apply')
    apply.add_argument('root', type=Path)
    args = parser.parse_args()
    try:
        patches = read_series(args.series)
        if args.command == 'list':
            for patch in patches:
                print(patch.name)
        else:
            apply_series(args.root, patches)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
