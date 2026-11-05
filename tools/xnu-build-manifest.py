#!/usr/bin/env python3
"""Record build inputs and validate this invocation's staged kernel.

This records provenance; it does not claim bit-identical compiler output or
hardware qualification. Source trees are hashed before compilation. SDK
metadata and generated link inputs are recorded separately from SDK contents.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kernel_banner import one_banner


REPO = Path(__file__).resolve().parent.parent


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def snapshot(path):
    path = path.resolve()
    if not path.exists():
        raise ValueError(f'missing build input: {path}')
    if path.is_file():
        return {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size}
    entries = []
    for directory, folders, files in os.walk(path, followlinks=False):
        folders[:] = sorted(x for x in folders if x not in ('.git', '__pycache__'))
        names = sorted(files + [x for x in folders if (Path(directory) / x).is_symlink()])
        for name in names:
            item = Path(directory) / name
            relative = str(item.relative_to(path))
            if relative == '.git':
                continue
            mode = item.lstat().st_mode
            if stat.S_ISLNK(mode):
                entries.append([relative, 'symlink', os.readlink(item)])
            elif stat.S_ISREG(mode):
                entries.append([relative, 'executable' if mode & 0o111 else 'file', sha256(item)])
            else:
                raise ValueError(f'unsupported build input: {item}')
    encoded = json.dumps(sorted(entries), separators=(',', ':'), ensure_ascii=True).encode()
    return {'path': str(path), 'sha256': hashlib.sha256(encoded).hexdigest(),
            'files': len(entries), 'entries': sorted(entries),
            'exclusions': ['.git', '__pycache__'], 'mode_policy': 'executable bits only'}


def command(args, cwd=None):
    try:
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=30)
        return {'command': args, 'exit': result.returncode,
                'output': (result.stdout + result.stderr).strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'command': args, 'error': str(error)}


def project_state():
    status = command(['git', 'status', '--porcelain=v1', '--untracked-files=normal'], REPO)
    result = {'status': status, 'dirty': None}
    if status.get('exit') == 0:
        result['dirty'] = bool(status['output'])
    diff = subprocess.run(['git', 'diff', '--binary', 'HEAD'], cwd=REPO, capture_output=True)
    if diff.returncode == 0:
        result['tracked_diff_sha256'] = hashlib.sha256(diff.stdout).hexdigest()
    else:
        result['diff_error'] = diff.stderr.decode(errors='replace').strip()
    result['diff_scope'] = 'tracked changes against HEAD; selected untracked inputs are hashed in inputs'
    return result


def save(path, data):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    temporary.replace(path)


def sdk_metadata(path):
    path = path.resolve()
    names = ['SDKSettings.json', 'SDKSettings.plist', 'usr/include/TargetConditionals.h',
             'usr/include/sys/cdefs.h', 'usr/local/libexec/availability.pl',
             'usr/local/lib/kernel/libfirehose_kernel.a']
    return {'path': str(path), 'metadata_and_link_inputs': {
        name: snapshot(path / name) for name in names if (path / name).is_file()},
        'scope': 'metadata and listed header/link inputs; not a full SDK-content digest'}


def capture(args):
    source = args.source.resolve()
    staging = args.staging.resolve()
    output = args.output.resolve()
    if not (source / 'bsd/conf/files').is_file():
        raise ValueError(f'not an XNU source tree: {source}')
    if output.is_relative_to(source):
        raise ValueError('manifest must be outside the source tree')
    if not staging.is_dir() or any(staging.iterdir()):
        raise ValueError('kernel staging directory must exist and be empty')
    if output.exists():
        raise ValueError(f'refusing to replace a prior manifest: {output}')
    inputs = {}
    for item in args.input:
        name, separator, value = item.partition('=')
        if not separator or not name or name in inputs:
            raise ValueError(f'expected unique NAME=PATH input: {item}')
        inputs[name] = snapshot(Path(value))
    if 'banner-parser' in inputs:
        raise ValueError('banner-parser is a reserved build input name')
    inputs['banner-parser'] = snapshot(Path(__file__).with_name('kernel_banner.py'))
    data = {
        'schema': 1, 'state': 'prepared',
        'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'machine': args.machine, 'profile': args.profile, 'configuration': args.configuration,
        'source': snapshot(source), 'inputs': inputs,
        'build_root': str(args.build_root.resolve()), 'staging_root': str(staging),
        'sdk': sdk_metadata(args.sdk),
        'host_sdk': sdk_metadata(args.host_sdk or args.sdk),
        'host': platform.platform(),
        'environment': {name: os.environ.get(name) for name in (
            'DEVELOPER_DIR', 'SDKVERSION', 'RC_DARWIN_KERNEL_VERSION', 'KERNEL_BUILD_DATE',
            'KERNEL_BUILD_OBJROOT', 'CC', 'CXX', 'LD', 'DXB_SHA', 'MACOS_VERSION')},
        'tool_versions': [command(value) for value in (
            ['clang', '--version'], ['make', '--version'], ['git', '--version'],
            ['xcodebuild', '-version'], ['xcrun', '--find', 'iig'])],
        'project_revision': command(['git', 'rev-parse', 'HEAD'], REPO),
        'project_worktree': project_state(),
        'qualification': 'input provenance only; not a bit-identical or hardware result',
    }
    if (source / '.git').exists():
        data['source_revision'] = command(['git', 'rev-parse', 'HEAD'], source)
    # Distinguish repeated builds even when dxb fixes the date and the inputs
    # have not changed. The full source/config/input digest remains traceable.
    identity_inputs = {name: data[name] for name in ('machine', 'profile', 'configuration')}
    identity_inputs['source_sha256'] = data['source']['sha256']
    identity_inputs['inputs'] = {name: value['sha256'] for name, value in inputs.items()}
    data['build_identity'] = {
        'id': 'xnu-' + uuid.uuid4().hex,
        'source_config_inputs_sha256': hashlib.sha256(json.dumps(
            identity_inputs, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'inherited_objroot': data['environment']['KERNEL_BUILD_OBJROOT'],
        'scope': 'unique build invocation; does not distinguish repeated boots of one image',
    }
    data['environment']['KERNEL_BUILD_OBJROOT'] = data['build_identity']['id']
    output.parent.mkdir(parents=True, exist_ok=True)
    save(output, data)
    print(f'Build inputs: {output}')


def prepare_build(args):
    path = args.manifest.resolve()
    data = json.loads(path.read_text())
    identity = data['build_identity']
    if data['state'] != 'prepared' or 'compile_prepared' in identity:
        raise ValueError('build identity has already been prepared or finished')
    if not re.fullmatch(r'xnu-[0-9a-f]{32}', identity['id']):
        raise ValueError('invalid build identity')
    machine, config = data['machine'], data['configuration']
    if machine not in ('sweet', 'gauguin') or config not in ('DEVELOPMENT', 'RELEASE', 'DEBUG'):
        raise ValueError('unsupported build identity target')
    objroot = args.objroot.resolve()
    build_root = Path(data['build_root']).resolve()
    source = Path(data['source']['path']).resolve()
    if objroot == build_root or not objroot.is_relative_to(build_root) or objroot.is_relative_to(source):
        raise ValueError('object root must be inside build root and outside source')
    target = objroot / f'{config}_ARM64_{machine.upper()}' / f'kernel.{config.lower()}.{machine}.unstripped'
    targets = (target, target.parent / 'version.o')
    for item in targets:
        if item.is_symlink() or not item.resolve().is_relative_to(objroot):
            raise ValueError('refusing redirected final link/version target')
        if item.exists() and not item.is_file():
            raise ValueError('final link/version target is not a regular file')
        if (path.parent / 'previous-link' / item.name).exists():
            raise ValueError('refusing to replace preserved final link/version target')
    previous = []
    for item in targets:
        if item.exists():
            archive = path.parent / 'previous-link' / item.name
            archive.parent.mkdir(parents=True, exist_ok=True)
            # version.o is reached only inside the final-link recipe. Preserve
            # both targets: an older make can miss same-tick version.c changes.
            record = snapshot(item)
            item.rename(archive)
            record['preserved_at'] = str(archive)
            previous.append(record)
    identity['compile_prepared'] = {'objroot': str(objroot), 'link_target': str(target),
                                    'preserved_targets': previous}
    save(path, data)
    print(identity['id'])


def finish(args):
    path = args.manifest.resolve()
    data = json.loads(path.read_text())
    if data['state'] != 'prepared':
        raise ValueError('manifest already has a build result')
    kernel = args.kernel.resolve()
    staging = Path(data['staging_root'])
    error = None
    if args.make_exit != 0:
        error = f'kernel build failed with exit {args.make_exit}'
    elif not kernel.is_relative_to(staging):
        error = 'kernel is outside this invocation\'s staging directory'
    elif not kernel.is_file() or kernel.stat().st_size == 0:
        error = f'no staged kernel produced: {kernel}'
    elif kernel.open('rb').read(8) != b'\xcf\xfa\xed\xfe\x0c\x00\x00\x01':
        error = 'staged kernel is not an ARM64 Mach-O image'
    if error is None:
        try:
            identity = data['build_identity']
            if 'compile_prepared' not in identity:
                raise ValueError('build identity was not prepared for compilation')
            banner = one_banner(kernel.read_bytes())
            if not banner.endswith(b':' + identity['id'].encode('ascii')):
                raise ValueError('kernel banner does not contain this build identity')
            data['kernel_banner'] = banner.decode('utf-8', 'strict')
        except (KeyError, ValueError) as failure:
            error = f'kernel identity validation failed: {failure}'
    data['make_exit'] = args.make_exit
    data['state'] = 'failed' if error else 'built'
    data['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if error:
        data['error'] = error
    else:
        data['kernel'] = snapshot(kernel)
    save(path, data)
    if error:
        raise ValueError(error)
    print(f'Kernel SHA256: {data["kernel"]["sha256"]}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    begin = sub.add_parser('capture')
    for name in ('source', 'sdk', 'build-root', 'staging', 'output'):
        begin.add_argument('--' + name, type=Path, required=True)
    begin.add_argument('--host-sdk', type=Path, help='host tools SDK; defaults to --sdk')
    begin.add_argument('--machine', choices=('sweet', 'gauguin'), required=True)
    begin.add_argument('--profile', choices=('13.5',), default='13.5')
    begin.add_argument('--configuration', choices=('DEVELOPMENT', 'RELEASE', 'DEBUG'),
                       default='DEVELOPMENT')
    begin.add_argument('--input', action='append', default=[])
    prepare = sub.add_parser('prepare-build')
    prepare.add_argument('--manifest', type=Path, required=True)
    prepare.add_argument('--objroot', type=Path, required=True)
    end = sub.add_parser('finish')
    end.add_argument('--manifest', type=Path, required=True)
    end.add_argument('--kernel', type=Path, required=True)
    end.add_argument('--make-exit', type=int, required=True)
    args = parser.parse_args()
    try:
        {'capture': capture, 'prepare-build': prepare_build, 'finish': finish}[args.command](args)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
