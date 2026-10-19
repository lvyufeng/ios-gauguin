#!/usr/bin/env python3
"""Mirror the small dependency trees the XNU build needs.

Every source is a git repository pinned to the exact commit/tag that
Apple's macOS 13.5 (xnu-8796.141.3) release.json or the SWEET staging
scripts use, so the mirror is reproducible. Only the files under the paths
each build actually consumes are kept:

  libpthread   kern/ private/ include/            (0019-stage-libpthread.sh)
  hfs          full tree, source is small         (0026-stage-hfs.sh)
  BearSSL      inc/ src/                           (0020-stage-bearssl.sh)

Large unchanged upstream trees (xnu, dtrace, Libsystem, libdispatch,
libplatform, AvailabilityVersions) are NOT mirrored: they are fetched from
their original sources by the build script in deps/build-local.sh.
"""
import subprocess, sys, shutil, tempfile, os

HERE = os.path.dirname(os.path.abspath(__file__))
BEARSSL_FILES = ['inc/bearssl_block.h', 'inc/bearssl_hash.h',
                 'src/inner.h', 'src/config.h'] + \
                ['src/symcipher/%s.c' % f for f in
                 ('aes_ct', 'aes_ct_enc', 'aes_ct_dec', 'aes_ct_cbcenc', 'aes_ct_cbcdec')] + \
                ['src/hash/%s.c' % f for f in ('md5', 'sha1', 'sha2big')] + \
                ['src/codec/%s.c' % f for f in
                 ('dec32le', 'enc32le', 'dec32be', 'enc32be', 'dec64be', 'enc64be')]
SOURCES = {
    # name: (url, ref, paths to keep or None for everything)
    'libpthread': ('https://github.com/apple-oss-distributions/libpthread.git',
                   'a6c70ca0e544347a0377babf748f831577ec24f9', ['kern', 'private', 'include']),
    'hfs': ('https://github.com/apple-oss-distributions/hfs.git',
            '31d5ec238dfab485e78a9a30b8b92d13e8914f03',
            ['core', 'include', 'private', 'LICENSE*']),
    'BearSSL': ('https://www.bearssl.org/git/BearSSL',
                '7bea48e5e850ab4cafbe68d3765cdaba13a86d6f', BEARSSL_FILES),
}


def fetch(name):
    url, ref, keep = SOURCES[name]
    dst = os.path.join(HERE, name)
    if os.path.isdir(dst) and os.path.exists(os.path.join(dst, '.git')):
        print(f'{name}: present')
        return
    tmp = tempfile.mkdtemp()
    try:
        subprocess.check_call(['git', 'init', '-q', tmp])
        subprocess.check_call(['git', '-C', tmp, 'fetch', '-q', '--depth', '1', url, ref])
        subprocess.check_call(['git', '-C', tmp, 'checkout', '-q', 'FETCH_HEAD'])
        os.makedirs(dst, exist_ok=True)
        import glob, fnmatch
        entries = []
        for pat in (keep or os.listdir(tmp)):
            if keep and ('/' in pat or '*' in pat):
                entries += [os.path.relpath(p, tmp) for p in glob.glob(os.path.join(tmp, pat))]
            else:
                entries.append(pat)
        for entry in sorted(set(entries)):
            src = os.path.join(tmp, entry)
            if entry.startswith('.git') or not os.path.exists(src):
                continue
            out = os.path.join(dst, entry)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            if os.path.isdir(src):
                shutil.copytree(src, out, dirs_exist_ok=True)
            else:
                shutil.copy2(src, out)
        shutil.rmtree(os.path.join(dst, '.git'), ignore_errors=True)
        print(f'{name}: {ref[:12]}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    names = sys.argv[1:] or list(SOURCES)
    for n in names:
        fetch(n)
