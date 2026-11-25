#!/usr/bin/env python3
"""Compile the real iBoot stage-2 blocks as independent translation units.

SDK TARGET_OS_OSX may be absent in pexpert and present through a transitive
include in osfmk. Only the shared XNU build selection may control these blocks.
The small host adapters supply DT input and logging; no kernel symbol is stubbed.
"""
import itertools
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2'))
SYMBOL = 'iBoot_Stage_2_version'


def guarded_blocks(path, count):
    lines = path.read_text().splitlines(keepends=True)
    blocks = []
    for start, line in enumerate(lines):
        if not re.match(r'^\s*#if\b', line) or 'TARGET_OS_OSX' not in line or '__arm64__' not in line:
            continue
        depth = 0
        for end in range(start, len(lines)):
            if re.match(r'^\s*#\s*(if|ifdef|ifndef)\b', lines[end]):
                depth += 1
            elif re.match(r'^\s*#\s*endif\b', lines[end]):
                depth -= 1
                if depth == 0:
                    block = ''.join(lines[start:end + 1])
                    if SYMBOL in block:
                        blocks.append(block)
                    break
    if len(blocks) != count:
        raise AssertionError(f'{path}: expected {count} stage-2 guarded blocks, got {len(blocks)}')
    return blocks


def macros(xnu_osx, sdk_osx, arm64):
    # Set the fixture environment after libc headers, independently in each TU.
    # Undefine modern clang's TARGET_OS_OSX builtin to model older compilers too.
    text = '#undef XNU_TARGET_OS_OSX\n#undef TARGET_OS_OSX\n#undef __arm64__\n'
    if xnu_osx:
        text += '#define XNU_TARGET_OS_OSX 1\n'
    if sdk_osx is not None:
        text += f'#define TARGET_OS_OSX {sdk_osx}\n'
    if arm64:
        text += '#define __arm64__ 1\n'
    return text


class PlatformGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.clang = shutil.which('clang')
        cls.nm = shutil.which('nm')
        if not cls.clang or not cls.nm:
            raise RuntimeError('clang and nm are required for the platform guard regression')
        pe_path = SOURCE / 'pexpert/arm/pe_init.c'
        cls.pe = guarded_blocks(pe_path, 3)
        cls.model = guarded_blocks(SOURCE / 'osfmk/arm/model_dep.c', 2)
        length = re.findall(r'^#define FW_VERS_LEN\s+\d+\s*$', pe_path.read_text(), re.M)
        if len(length) != 1:
            raise AssertionError('expected the real FW_VERS_LEN definition')
        cls.length = length[0] + '\n'

    def command(self, *args):
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, ' '.join(map(str, args)) + '\n' + result.stderr)
        return result.stdout

    def check_case(self, xnu_osx, pe_sdk, model_sdk, arm64=True):
        enabled = xnu_osx and arm64
        with tempfile.TemporaryDirectory(prefix='iboot-platform-') as directory:
            work = Path(directory)
            pe = '#include <stdio.h>\n#include <string.h>\n' + macros(xnu_osx, pe_sdk, arm64)
            pe += self.length + self.pe[0]
            pe += '''
extern int SecureDTGetProperty(int, const char *, const void **, unsigned int *);
#define kSuccess 0
#undef bcopy
#define bcopy(source, destination, bytes) memmove(destination, source, bytes)
void pe_fixture(void) {
    int entry = 0;
    const void *prop = 0;
    unsigned int size = 0;
    (void)entry; (void)prop; (void)size;
'''
            pe += self.pe[2] + self.pe[1] + '}\n'
            model = '#include <stdio.h>\n' + macros(xnu_osx, model_sdk, arm64)
            model += self.model[0]
            model += '#define paniclog_append_noflush printf\nvoid panic_fixture(void) {\n'
            model += self.model[1] + '}\n'
            main = '''
#include <assert.h>
#include <string.h>
void pe_fixture(void);
void panic_fixture(void);
static int property_queries;
int SecureDTGetProperty(int entry, const char *name, const void **prop, unsigned int *size) {
    static const char version[] = "fixture-stage-2";
    (void)entry;
    assert(strcmp(name, "system-firmware-version") == 0);
    property_queries++;
    *prop = version;
    *size = sizeof(version);
    return 0;
}
int main(void) {
    pe_fixture();
    panic_fixture();
    assert(property_queries == EXPECTED_QUERIES);
    return 0;
}
'''.replace('EXPECTED_QUERIES', str(int(enabled)))
            for name, text in [('pe', pe), ('model', model), ('main', main)]:
                source = work / (name + '.c')
                source.write_text(text)
                self.command(self.clang, '-std=c11', '-Wall', '-Wextra', '-Werror', '-c',
                             str(source), '-o', str(work / (name + '.o')))
            pe_symbols = self.command(self.nm, '-g', str(work / 'pe.o'))
            model_symbols = self.command(self.nm, '-g', str(work / 'model.o'))
            present = lambda output: any(line.split()[-1].lstrip('_') == SYMBOL
                                         for line in output.splitlines() if line.split())
            binary = work / 'check'
            self.command(self.clang, str(work / 'pe.o'), str(work / 'model.o'),
                         str(work / 'main.o'), '-o', str(binary))
            self.assertEqual(present(pe_symbols), enabled, pe_symbols)
            self.assertEqual(present(model_symbols), enabled, model_symbols)
            undefined = self.command(self.nm, '-u', str(binary))
            self.assertFalse(present(undefined), undefined)
            output = self.command(str(binary))
            self.assertEqual(output.count('iBoot Stage 2 version: fixture-stage-2\n'), 2 if enabled else 0)

    def test_independent_sdk_include_states_follow_xnu_selection(self):
        for xnu_osx, pe_sdk, model_sdk in itertools.product((False, True), (None, 0, 1), (None, 0, 1)):
            with self.subTest(xnu_osx=xnu_osx, pe_sdk=pe_sdk, model_sdk=model_sdk):
                self.check_case(xnu_osx, pe_sdk, model_sdk)

    def test_non_arm64_excludes_definition_and_references(self):
        for pe_sdk, model_sdk in ((None, 1), (1, None), (0, 1), (1, 0)):
            with self.subTest(pe_sdk=pe_sdk, model_sdk=model_sdk):
                self.check_case(True, pe_sdk, model_sdk, arm64=False)


if __name__ == '__main__':
    unittest.main()
