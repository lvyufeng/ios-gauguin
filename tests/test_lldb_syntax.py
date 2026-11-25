#!/usr/bin/env python3
"""Check the actual LLDB syntax-check invocation without compiling XNU."""
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(os.environ.get('XNU_SOURCE', ROOT / '.deps-cache/xnu-patched-0082-2')).resolve()


def check_install_rule(rule, scratch, env):
    """Instantiate the actual make template; only unifdef and flag storage are fixtures."""
    start = rule.index('define INSTALLPYTHON_RULE_template')
    end = rule.index('\nendef', start) + len('\nendef')
    template = rule[start:end]
    fixture = scratch / 'make-fixture'
    fixture.mkdir()
    (fixture / 'inputs').mkdir()
    unifdef = fixture / 'unifdef.py'
    unifdef.write_text('from pathlib import Path\nimport sys\n'
                      'sys.stdout.buffer.write(Path(sys.argv[-1]).read_bytes())\n')
    flags = fixture / 'flags.py'
    flags.write_text('from pathlib import Path\nimport sys\n'
                     'Path(sys.argv[1]).write_text("fixture flags\\n")\n')
    makefile = fixture / 'Makefile'
    makefile.write_text(
        'SHELL := /bin/sh\n'
        'MKDIR := mkdir -p\nINSTALL := install\nDATA_INSTALL_FLAGS := -m 644\n'
        'RM := rm -f\nTOUCH := touch\nLOG_INSTALLPY := true\nERR := echo\n'
        f'UNIFDEF := {shlex.quote(sys.executable)} -B {unifdef}\n'
        f'REPLACECONTENTS := {shlex.quote(sys.executable)} -B {flags}\n'
        f'LLDBMACROS_SOURCE := {SOURCE / "tools/lldbmacros"}\n'
        '.PHONY: ALWAYS\nALWAYS:\n\n' + template + '\n'
        '$(eval $(call INSTALLPYTHON_RULE_template,out/probe.py,inputs/%,pydir,,out/))\n')
    source = fixture / 'inputs/probe.py'
    target = fixture / 'out/probe.py'
    for text, diagnostic in (('def broken(:\n    pass\n', 'Compilation failed'),
                             ('def value():\n\treturn 42\n', 'Found a TAB character'),
                             ('def value():\n    return 42\n', None)):
        source.write_text(text)
        result = subprocess.run([shutil.which('make') or 'make', '-f', str(makefile),
                                 'out/probe.py'], cwd=fixture, env=env,
                                capture_output=True, text=True)
        if diagnostic:
            assert result.returncode != 0, result.stdout + result.stderr
            assert diagnostic in result.stderr, result.stderr
            assert not target.exists(), 'failed syntax check installed an unchecked target'
        else:
            assert result.returncode == 0, result.stdout + result.stderr
            assert target.read_text() == text


def main():
    checker = SOURCE / 'tools/lldbmacros/core/syntax_checker.py'
    if not checker.is_file():
        print(f'skip LLDB syntax test, source not staged at {SOURCE}')
        return
    rule = (SOURCE / 'makedefs/MakeInc.rule').read_text()
    invocation = re.search(r'^\t([^\n]*syntax_checker\.py[^\n]*)\\\n\t([^\n]+)',
                           rule, re.M)
    assert invocation, 'missing LLDB syntax-check recipe'
    assert '|| exit 1' in invocation[2], 'syntax errors must still fail the recipe'
    prefix = invocation[1].strip().replace(
        '$$(LLDBMACROS_SOURCE)', str(SOURCE / 'tools/lldbmacros'))
    command = shlex.split(prefix)
    assert '-I' in command, 'syntax checker must use isolated Python'

    with tempfile.TemporaryDirectory(prefix='lldb-syntax-') as directory:
        scratch = Path(directory)
        good = scratch / 'valid.py'
        good.write_text('def value():\n    return 42\n')
        invalid = scratch / 'invalid.py'
        invalid.write_text('def broken(:\n    pass\n')
        tabbed = scratch / 'tabbed.py'
        tabbed.write_text('def value():\n\treturn 42\n')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        # Reproduce the old script-directory shadowing with a clean stdlib
        # import state (-S prevents site packages preloading collections).
        original = subprocess.run([sys.executable, '-S', '-B', str(checker), str(good)],
                                  capture_output=True, text=True, env=env)
        assert original.returncode != 0, original.stdout + original.stderr
        assert 'collections.py' in original.stderr
        assert 'relative import' in original.stderr

        # The new command comes from MakeInc.rule, not a parallel test helper.
        success = subprocess.run(command + [str(good)], capture_output=True,
                                 text=True, env=env)
        assert success.returncode == 0, success.stdout + success.stderr
        assert 'No syntax errors found' in success.stdout
        for path, diagnostic in ((invalid, 'Compilation failed'),
                                 (tabbed, 'Found a TAB character')):
            result = subprocess.run(command + [str(path)], capture_output=True,
                                    text=True, env=env)
            assert result.returncode != 0, (path, result.stdout, result.stderr)
            assert diagnostic in result.stderr, result.stderr
        check_install_rule(rule, scratch, env)
        assert not list(scratch.rglob('*.pyc'))
    print('LLDB isolated syntax check passes; invalid syntax/TAB never installs a target')


if __name__ == '__main__':
    main()
