#!/usr/bin/env python3
"""Exercise build failure/publication and staging provenance without compiling XNU."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent.parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'tools' / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state = load('source_state', 'xnu-source-state.py')
manifest = load('build_manifest', 'xnu-build-manifest.py')


class SourceStateTests(unittest.TestCase):
    def test_input_changes_are_rejected_without_replacing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            source = base / 'source'
            (source / 'bsd/conf').mkdir(parents=True)
            sentinel = source / 'bsd/conf/files'
            sentinel.write_text('original')
            record_root = base / 'state'
            with patch.object(state, 'staging_inputs', return_value={'series': 'first'}):
                with self.assertRaisesRegex(ValueError, 'no staging input record'):
                    state.run('check', source, record_root)
                state.run('record', source, record_root)
                state.run('check', source, record_root)
            with patch.object(state, 'staging_inputs', return_value={'series': 'second'}):
                with self.assertRaisesRegex(ValueError, 'staging inputs changed'):
                    state.run('check', source, record_root)
            self.assertEqual(sentinel.read_text(), 'original')
            self.assertEqual(list(source.iterdir()), [source / 'bsd'])

    def test_sdk_discovery_is_skipped_without_xcrun(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            source = base / 'source'
            (source / 'bsd/pthread').mkdir(parents=True)
            (source / 'bsd/pthread/pthread_shims.c').write_text('')
            binaries = base / 'bin'
            binaries.mkdir()
            for name in ('bash', 'mkdir', 'cp', 'head', 'grep'):
                (binaries / name).symlink_to(shutil.which(name))
            (binaries / 'python3').symlink_to(sys.executable)
            env = dict(os.environ, PATH=str(binaries), SKIP_TARGET_MACROS='1')
            result = subprocess.run(
                [str(binaries / 'bash'), str(ROOT / 'deps/mirror/xnu/prepare.sh'),
                 str(source), str(ROOT / 'deps/mirror')], env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((source / 'bsd/sweet_hfs/core/hfs_iokit.h').is_file())
            self.assertFalse((source / 'bsd/sweet_hfs/TargetConditionals.h').exists())


class BuildExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='xnu-build-fixture-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.source = self.base / 'source'
        self.build = self.base / 'build'
        self.out = self.base / 'out'
        self.developer = self.base / 'developer'
        binaries = self.developer / 'usr/bin'
        binaries.mkdir(parents=True)
        (self.source / 'bsd/conf').mkdir(parents=True)
        (self.source / 'bsd/conf/files').write_text('')
        (self.source / 'bsd/dev').mkdir()
        (self.source / 'bsd/dev/sweet_sample.c').write_text('#if defined(ARM64_BOARD_CONFIG_SWEET)\n#endif\n')
        (self.source / 'libkern/conf').mkdir(parents=True)
        (self.source / 'libkern/conf/Makefile.template').write_text('')
        self.sdk = self.build / 'sdkroot-macos'
        self.host_sdk = self.base / 'original-sdk'
        for sdk, contents in ((self.sdk, 'kernel headers'), (self.host_sdk, 'original host headers')):
            (sdk / 'usr/include/sys').mkdir(parents=True)
            (sdk / 'usr/include/sys/cdefs.h').write_text(contents)
            (sdk / 'SDKSettings.json').write_text('{"Version":"fixture"}')
        for name in ('usr/local/libexec/availability.pl', 'usr/local/include/_simple.h',
                     'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/os/atomic_private.h',
                     'usr/local/lib/kernel/libfirehose_kernel.a'):
            target = self.sdk / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fixture')
            target.chmod(0o755)
        self.kernel = self.out / 'System/Library/Kernels/kernel.development.gauguin'
        self.kernel.parent.mkdir(parents=True)
        self.kernel.write_bytes(b'previous known kernel')
        make = binaries / 'make'
        make.write_text('#!' + sys.executable + '\n' + '''
import json, os, pathlib, sys
if '--version' in sys.argv:
    print('fixture make'); sys.exit(0)
args = dict(x.split('=', 1) for x in sys.argv[1:] if '=' in x)
args['_environment'] = {name: os.environ.get(name) for name in ('SDKROOT_RESOLVED', 'HOST_SDKROOT_RESOLVED')}
pathlib.Path(os.environ['MAKE_RECORD']).write_text(json.dumps(args))
with open(os.environ['MAKE_HISTORY'], 'a') as stream:
    stream.write(json.dumps({'phase': 'installhdrs' if 'installhdrs' in sys.argv else 'install', **args}) + '\\n')
if 'installhdrs' in sys.argv:
    target = pathlib.Path(args['DSTROOT']) / 'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/os/atomic_private.h'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('fixture header')
    sys.exit(0)
if os.environ.get('FAKE_NO_KERNEL') != '1':
    target = pathlib.Path(args['DSTROOT']) / 'System/Library/Kernels/kernel.development.gauguin'
    target.parent.mkdir(parents=True, exist_ok=True)
    identity = os.environ.get('FAKE_KERNEL_ID', args['KERNEL_BUILD_OBJROOT'])
    banner = ('Darwin Kernel Version 22.6.0: fixed date; fixture:' + identity).encode()
    target.write_bytes(bytes.fromhex('cffaedfe0c000001') + banner + bytes([0]))
sys.exit(int(os.environ.get('FAKE_MAKE_RC', '0')))
''')
        make.chmod(0o755)
        for name, body in {
            'nproc': 'echo 1', 'sysctl': 'echo 1', 'clang': 'echo fixture-clang', 'xcodebuild': 'echo fixture-xcode',
            'xcrun': 'case "$*" in *show-sdk-path*) echo "$FIXTURE_SDK";; *) echo fixture-tool;; esac',
        }.items():
            tool = binaries / name
            tool.write_text('#!/bin/bash\n' + body + '\n')
            tool.chmod(0o755)
        self.env = dict(os.environ, DEVELOPER_DIR=str(self.developer),
                        PATH=str(binaries) + os.pathsep + os.environ['PATH'],
                        SKIP_TESTS='1', MAKE_RECORD=str(self.base / 'make.json'),
                        MAKE_HISTORY=str(self.base / 'make-history.jsonl'),
                        FIXTURE_SDK=str(self.host_sdk), MACOS_VERSION='13.5')
        state.run('record', self.source, self.build / 'source-state')

    def native(self):
        return subprocess.run(['bash', str(ROOT / 'deps/build-macos.sh'), 'gauguin',
                               '--xnu', str(self.source), '--build-root', str(self.build),
                               '--out', str(self.out), '--jobs', '1'],
                              env=self.env, capture_output=True, text=True)

    def result(self):
        paths = list((self.build / 'runs').glob('*/build-manifest.json'))
        self.assertEqual(len(paths), 1)
        return json.loads(paths[0].read_text())

    def test_native_failure_does_not_publish_even_if_kernel_was_written(self):
        self.env['FAKE_MAKE_RC'] = '2'
        result = self.native()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.kernel.read_bytes(), b'previous known kernel')
        self.assertEqual(self.result()['make_exit'], 2)
        self.assertEqual(self.result()['state'], 'failed')

    def test_native_success_without_kernel_does_not_reuse_previous_output(self):
        self.env['FAKE_NO_KERNEL'] = '1'
        result = self.native()
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.kernel.read_bytes(), b'previous known kernel')
        self.assertEqual(self.result()['state'], 'failed')

    def test_native_success_is_isolated_and_records_actual_inputs(self):
        result = self.native()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        args = json.loads((self.base / 'make.json').read_text())
        for key in ('OBJROOT', 'SYMROOT', 'DSTROOT'):
            self.assertTrue(Path(args[key]).is_relative_to(self.build))
        self.assertNotEqual(Path(args['DSTROOT']), self.out)
        record = self.result()
        self.assertEqual(record['state'], 'built')
        self.assertEqual(record['kernel']['sha256'], manifest.sha256(self.kernel))
        self.assertEqual(record['sdk']['path'], str(self.sdk))
        self.assertEqual(record['host_sdk']['path'], str(self.host_sdk))
        self.assertIn('versions', record['inputs'])
        self.assertIsInstance(record['project_worktree']['dirty'], bool)
        self.assertEqual(len(record['project_worktree']['tracked_diff_sha256']), 64)
        self.assertEqual(json.loads((self.out / 'build-manifest.json').read_text()), record)

    def test_native_header_and_kernel_make_use_the_original_host_sdk(self):
        (self.sdk / 'System/Library/Frameworks/Kernel.framework/Versions/A/PrivateHeaders/os/atomic_private.h').unlink()
        result = self.native()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = [json.loads(line) for line in (self.base / 'make-history.jsonl').read_text().splitlines()]
        self.assertEqual([call['phase'] for call in calls], ['installhdrs', 'install'])
        for call in calls:
            self.assertEqual(call['_environment']['SDKROOT_RESOLVED'], str(self.sdk))
            self.assertEqual(call['_environment']['HOST_SDKROOT_RESOLVED'], str(self.host_sdk))
        record = self.result()
        host = record['host_sdk']['metadata_and_link_inputs']['usr/include/sys/cdefs.h']['sha256']
        kernel = record['sdk']['metadata_and_link_inputs']['usr/include/sys/cdefs.h']['sha256']
        self.assertNotEqual(host, kernel)
        self.assertEqual((self.host_sdk / 'usr/include/sys/cdefs.h').read_text(), 'original host headers')

    def test_ci_make_failure_is_not_hidden_by_later_commands(self):
        # Run the real project adapter with dxb prerequisites replaced by fixtures.
        work = self.base / 'dxb'
        work.mkdir()
        shutil.move(str(self.source), str(work / 'xnu'))
        (work / 'build.sh').write_text('fixture dxb')
        (work / 'fakeroot/usr/local').mkdir(parents=True)
        framework = work / 'fakeroot/System/Library/Frameworks/Kernel.framework/PrivateHeaders/os/atomic_private.h'
        framework.parent.mkdir(parents=True)
        framework.write_text('fixture private header')
        state.run('record', work / 'xnu', work / 'source-state')
        env = dict(self.env, GITHUB_WORKSPACE=str(ROOT), WORK_DIR=str(work),
                   BUILD_DIR=str(work / 'build'), FAKEROOT_DIR=str(work / 'fakeroot'),
                   MACHINE_CONFIG='gauguin', KERNEL_CONFIG='DEVELOPMENT', ARCH_CONFIG='ARM64',
                   KDKROOT='', TIGHTBEAMC='', RC_DARWIN_KERNEL_VERSION='22.6.0', FAKE_MAKE_RC='2')
        script = '''
source "$GITHUB_WORKSPACE/deps/dxb-project.sh" || exit 1
ensure_hw_env_overrides() { MEMORY_SIZE_OVERRIDE=1; PHYS_CPU_OVERRIDE=1; LOGICAL_CPU_OVERRIDE=1; KERNEL_PARALLELISM_OVERRIDE=1; }
ctf_tool_overrides() { CTF_TOOL_OVERRIDES=(); }
kernel_version_env() { :; }
build_project_xnu || exit 1
'''
        result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        records = list((work / 'build/runs').glob('*/build-manifest.json'))
        self.assertEqual(len(records), 1, result.stdout + result.stderr)
        record = json.loads(records[0].read_text())
        self.assertEqual(record['make_exit'], 2)
        self.assertIn('generated-frameworks', record['inputs'])
        self.assertEqual(record['inputs']['generated-frameworks']['files'], 1)
        self.assertFalse((work / 'out').exists())

    def test_ci_rejects_another_dependency_profile(self):
        result = subprocess.run(['bash', '-c', 'source "$GITHUB_WORKSPACE/deps/dxb-project.sh"'],
                                env=dict(self.env, MACOS_VERSION='14.5', GITHUB_WORKSPACE=str(ROOT)),
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('only MACOS_VERSION=13.5', result.stderr)

    def test_ci_prerequisite_failure_stops_before_later_successful_commands(self):
        # Execute the workflow's actual wrapper, not a duplicate of its loop.
        workflow = (ROOT / '.github/workflows/xnu.yml').read_text()
        script = workflow.split("cat > run-dxb.sh <<'SH'\n", 1)[1].split('\n          SH\n', 1)[0]
        work = self.base / 'dxb-prerequisite'
        work.mkdir()
        wrapper = work / 'run-dxb.sh'
        wrapper.write_text(textwrap.dedent(script))
        side_effect = work / 'headers-installed'
        (work / 'build.sh').write_text('''
set -e
WORK_DIR=$PWD
make() { return 23; }
xnu_headers() {
    make installhdrs
    cd "$WORK_DIR"
    touch "$SIDE_EFFECT"
}
main() { :; }
main "$@"
''')
        # Give the wrapper's /tmp log a unique name and remove it after the test.
        step_name = 'fixture-' + self.base.name
        for suffix in ('.log', '.log.clean'):
            self.addCleanup((Path('/tmp') / ('dxb-' + step_name + suffix)).unlink, missing_ok=True)
        env = dict(self.env, GITHUB_WORKSPACE=str(ROOT), DXB_STEPS='xnu_headers',
                   DXB_STEP_NAME=step_name, SIDE_EFFECT=str(side_effect))
        result = subprocess.run(['bash', str(wrapper)], cwd=work, env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
        self.assertFalse(side_effect.exists(), 'failed installhdrs must not write its success marker')


if __name__ == '__main__':
    unittest.main()
