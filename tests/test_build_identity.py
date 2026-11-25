#!/usr/bin/env python3
"""Build identity checks with real newvers templates and isolated build fixtures."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
from kernel_banner import one_banner, compare
sys.path.insert(0, str(ROOT / 'tests'))
from test_build_provenance import BuildExecutionTests, manifest, state

DATE = b'Darwin Kernel Version 22.6.0: Mon Aug 14 05:06:07 UTC 2023; runner:'
ID_A = b'xnu-' + b'a' * 32
ID_B = b'xnu-' + b'b' * 32


class BannerTests(unittest.TestCase):
    def test_complete_delimiters_and_identical_copies(self):
        for end in (b'\n', b'\r\n', b'\0'):
            self.assertEqual(one_banner(b'prefix ' + DATE + ID_A + end), DATE + ID_A)
        self.assertEqual(one_banner(DATE + ID_A + b'\0@(#)VERSION: ' + DATE + ID_A + b'\0'), DATE + ID_A)

    def test_missing_truncated_or_ambiguous_is_rejected(self):
        for data in (b'', DATE + ID_A, DATE + ID_A + b'\0' + DATE + ID_B + b'\n'):
            with self.assertRaises(ValueError):
                one_banner(data)

    def test_same_date_different_suffix_is_stale_even_after_byte_120(self):
        with tempfile.TemporaryDirectory() as d:
            image, log = Path(d) / 'image', Path(d) / 'log'
            for prefix in (DATE, DATE + b'long-builder-name-' * 12):
                image.write_bytes(prefix + ID_A + b'\0')
                log.write_bytes(prefix + ID_B + b'\n')
                with self.assertRaisesRegex(ValueError, 'MISMATCH'):
                    compare(image, log)
                log.write_bytes(prefix + ID_A + b'\r\n')
                compare(image, log)

    def test_both_observer_checks_execute_shared_parser_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            image, log = Path(d) / 'image', Path(d) / 'log'
            image.write_bytes(DATE + ID_A + b'\0')
            for name in ('sweet-observe.sh', 'fastboot-cycle.sh'):
                script = (ROOT / 'tools' / name).read_text()
                start = script.index('if ! python3 "$here/kernel_banner.py"')
                end = script.index('\nfi', start) + len('\nfi')
                check = 'say() { :; };\n' + script[start:end]
                for data, rc in ((DATE + ID_A + b'\n', 0), (DATE + ID_B + b'\n', 3), (b'', 3)):
                    log.write_bytes(data)
                    result = subprocess.run(['bash', '-c', check], capture_output=True,
                                            env=dict(os.environ, here=str(ROOT / 'tools'), img=str(image), out=str(log)))
                    self.assertEqual(result.returncode, rc, (name, result.stderr))


class IdentityExecutionTests(BuildExecutionTests):
    # Reuse the existing native/CI fixture setup but avoid re-running inherited tests.
    def test_same_input_rebuild_has_new_id_and_preserves_previous_link(self):
        self.assertEqual(self.native().returncode, 0)
        first = self.result()
        target = Path(first['build_identity']['compile_prepared']['link_target'])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'previous unstripped fixture')
        version = target.parent / 'version.o'
        version.write_bytes(b'previous version object fixture')
        result = self.native()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        records = sorted((self.build / 'runs').glob('*/build-manifest.json'))
        data = [json.loads(p.read_text()) for p in records]
        second = next(m for m in data if m['build_identity']['id'] != first['build_identity']['id'])
        self.assertEqual(first['build_identity']['source_config_inputs_sha256'], second['build_identity']['source_config_inputs_sha256'])
        archived, archived_version = second['build_identity']['compile_prepared']['preserved_targets']
        self.assertEqual(Path(archived['preserved_at']).read_bytes(), b'previous unstripped fixture')
        self.assertEqual(Path(archived_version['preserved_at']).read_bytes(), b'previous version object fixture')
        self.assertFalse(target.exists())  # Fake make writes installed output only.
        self.assertFalse(version.exists())
        args = json.loads((self.base / 'make.json').read_text())
        self.assertEqual(args['KERNEL_BUILD_OBJROOT'], second['build_identity']['id'])
        self.assertTrue(second['kernel_banner'].endswith(':' + args['KERNEL_BUILD_OBJROOT']))

    def test_stale_kernel_identity_rejects_make_zero_without_publishing(self):
        self.env['FAKE_KERNEL_ID'] = 'xnu-' + '0' * 32
        result = self.native()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.result()['state'], 'failed')
        self.assertIn('identity', self.result()['error'])
        self.assertEqual(self.kernel.read_bytes(), b'previous known kernel')

    def test_ci_overrides_dxb_fixed_objroot_and_passes_exact_id(self):
        work = self.base / 'dxb'
        work.mkdir()
        shutil.move(str(self.source), str(work / 'xnu'))
        (work / 'build.sh').write_text('fixture dxb')
        (work / 'fakeroot/usr/local').mkdir(parents=True)
        (work / 'fakeroot/System/Library/Frameworks').mkdir(parents=True)
        state.run('record', work / 'xnu', work / 'source-state')
        env = dict(self.env, GITHUB_WORKSPACE=str(ROOT), WORK_DIR=str(work),
                   BUILD_DIR=str(work / 'build'), FAKEROOT_DIR=str(work / 'fakeroot'),
                   MACHINE_CONFIG='gauguin', KERNEL_CONFIG='DEVELOPMENT', ARCH_CONFIG='ARM64',
                   KDKROOT='', TIGHTBEAMC='')
        script = '''
source "$GITHUB_WORKSPACE/deps/dxb-project.sh" || exit 1
ensure_hw_env_overrides() { MEMORY_SIZE_OVERRIDE=1; PHYS_CPU_OVERRIDE=1; LOGICAL_CPU_OVERRIDE=1; KERNEL_PARALLELISM_OVERRIDE=1; }
ctf_tool_overrides() { CTF_TOOL_OVERRIDES=(); }
kernel_version_env() { export KERNEL_BUILD_OBJROOT=1b191cb KERNEL_BUILD_DATE='Mon Aug 14 05:06:07 UTC 2023' RC_DARWIN_KERNEL_VERSION=22.6.0; }
build_project_xnu
'''
        result = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads((work / 'out/build-manifest-gauguin.json').read_text())
        args = json.loads((self.base / 'make.json').read_text())
        self.assertEqual(record['build_identity']['inherited_objroot'], '1b191cb')
        self.assertEqual(args['KERNEL_BUILD_OBJROOT'], record['build_identity']['id'])

    def test_linux_actual_final_build_block_passes_exact_id(self):
        # Execute the real capture/prepare/make/finish tail. OS/toolchain bootstrap
        # is intentionally outside this fixture; no Linux build qualification.
        text = (ROOT / 'deps/build-local.sh').read_text()
        start = text.index('python3 "$REPO/tools/xnu-build-manifest.py" capture --source "$SRCROOT"')
        end = text.index('\nmkdir -p "$OUT"', start)
        run = self.build / 'runs/linux-fixture'
        run.mkdir(parents=True)
        staging = run / 'install'; staging.mkdir()
        (run / 'make-env.sh').write_text(':\n')
        toolchain = self.build / 'toolchain'; toolchain.mkdir()
        log = self.build / 'logs'; log.mkdir()
        env = dict(self.env, REPO=str(ROOT), SRCROOT=str(self.source), COMBINED=str(self.sdk),
                   CACHE=str(self.build), STAGING=str(staging), MANIFEST=str(run / 'build-manifest.json'),
                   MACHINE='gauguin', MIRROR=str(ROOT / 'deps/mirror'), TOOLCHAIN=str(toolchain),
                   RUN=str(run), OBJROOT=str(self.build / 'obj-gauguin'), LOG=str(log),
                   SDKROOT=str(self.sdk), MEMORY_SIZE_OVERRIDE='1', KERNEL_BUILD_OBJROOT='old-fixed-id')
        result = subprocess.run(['bash', '-c', 'set -euo pipefail\n' + text[start:end]], env=env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        record = json.loads((run / 'build-manifest.json').read_text())
        args = json.loads((self.base / 'make.json').read_text())
        self.assertEqual(args['KERNEL_BUILD_OBJROOT'], record['build_identity']['id'])


class NewversTests(unittest.TestCase):
    def test_real_newvers_templates_and_incremental_final_target(self):
        source = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2')).resolve()
        if not (source / 'config/newvers.pl').is_file():
            self.skipTest('set XNU_SOURCE to a staged tree for real newvers coverage')
        with tempfile.TemporaryDirectory() as d:
            base = Path(d).resolve(); objroot = base / 'obj'
            obj = objroot / 'DEVELOPMENT_ARM64_GAUGUIN'; obj.mkdir(parents=True)
            (obj / 'libkern').mkdir()
            template = source / 'libkern/libkern/version.h.template'
            shutil.copy2(template, obj / 'libkern/version.h')
            env = dict(os.environ, SRCROOT=str(source), OBJROOT=str(objroot), TARGET=str(obj),
                       KERNEL_BUILD_DATE='Mon Aug 14 05:06:07 UTC 2023', KERNEL_BUILD_OBJROOT=ID_A.decode(),
                       CURRENT_KERNEL_CONFIG_LC='development')
            subprocess.run(['perl', str(source / 'config/newvers.pl'), str(obj / 'libkern/version.h')], env=env, check=True, capture_output=True)
            # Use actual final-target prerequisites and actual version.c rule.
            mk = (source / 'makedefs/MakeInc.kernel').read_text()
            rule = next(line for line in mk.splitlines() if line.startswith('$(TARGET)/$(KERNEL_FILE_NAME).unstripped:'))
            vrule = mk[mk.index('$(OBJPATH)/version.c:'):].split('\n\n', 1)[0]
            for name in ('lastkerneldataconst.o', 'lastkernelconstructor.o', 'nonlto.o', '.LDFLAGS'):
                (obj / name).touch()
            makefile = f'''SRCROOT={source}
TARGET={obj}
OBJPATH={obj}
KERNEL_FILE_NAME=kernel.development.gauguin
NEWVERS={source}/config/newvers.pl
CP=cp
.PHONY: all ALWAYS
all: $(TARGET)/$(KERNEL_FILE_NAME).unstripped
{rule}
\t$(MAKE) -f $(firstword $(MAKEFILE_LIST)) version.o
\tcp version.o $@
version.o: $(OBJPATH)/version.c
\tclang -target arm64-apple-macos11 -I. -c $< -o $@
{vrule}
'''
            (obj / 'Makefile').write_text(makefile)
            def build(identity):
                result = subprocess.run(['make', 'all', 'KERNEL_BUILD_OBJROOT=' + identity.decode()], cwd=obj,
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                return one_banner((obj / 'kernel.development.gauguin.unstripped').read_bytes())
            self.assertTrue(build(ID_A).endswith(b':' + ID_A))
            # Negative control: changing only the exported ID leaves the link
            # target untouched because version.o is reached inside its recipe.
            self.assertTrue(build(ID_B).endswith(b':' + ID_A))
            record = base / 'build-manifest.json'
            record.write_text(json.dumps({'state': 'prepared', 'build_identity': {'id': ID_B.decode()},
                'machine': 'gauguin', 'configuration': 'DEVELOPMENT', 'build_root': str(base),
                'source': {'path': str(source)}}))
            manifest.prepare_build(argparse.Namespace(manifest=record, objroot=objroot))
            archive = base / 'previous-link/kernel.development.gauguin.unstripped'
            self.assertTrue(build(ID_B).endswith(b':' + ID_B))
            self.assertTrue(one_banner(archive.read_bytes()).endswith(b':' + ID_A))


if __name__ == '__main__':
    suite = unittest.TestSuite()
    for cls in (BannerTests, IdentityExecutionTests, NewversTests):
        names = [name for name in cls.__dict__ if name.startswith('test_')]
        suite.addTests(cls(name) for name in names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
