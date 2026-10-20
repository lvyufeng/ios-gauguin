#!/bin/bash
# Called by deps/build-local.sh after fetching and applying the patches.
# Replaces the dxb staging scripts, whose downloads (apple-oss-distributions
# git fetch, www.bearssl.org) are unreachable from some networks: the same
# pinned sources arrive as a tarball of the blobs branch (deps/mirror).
set -euo pipefail
root=${1:?usage: prepare.sh XNU_ROOT DEPS_MIRROR}
mirror=${2:?usage: prepare.sh XNU_ROOT DEPS_MIRROR}
cd "$root"

[[ -f bsd/pthread/pthread_shims.c ]] || { echo >&2 "not an xnu tree"; exit 1; }

# The files this script adds must compile out for other machine configs
# (xnu's makefile includes every `standard` file in every config and dxb's
# VMAPPLE bootstrap build cannot link SWEET-only code).
sweet_guard() {
	local f=$1 first=$2
	[ -f "$f" ] || return 0
	if ! head -n 200 "$f" | grep -q "ARM64_BOARD_CONFIG_SWEET"; then
		python3 - "$f" "$first" <<'PY'
import sys
path, first = sys.argv[1], sys.argv[2]
text = open(path).read()
i = text.find(first)
if i < 0:
    raise SystemExit(f'{path}: marker {first!r} not found')
i = text.find('\n', i) + 1
text = text[:i] + '#if defined(ARM64_BOARD_CONFIG_SWEET)\n' + text[i:]
text = text.rstrip('\n') + '\n#endif /* ARM64_BOARD_CONFIG_SWEET */\n'
open(path, 'w').write(text)
PY
	fi
}
sweet_guard bsd/dev/sweet_ufs.c '#include' 2>/dev/null || true

# libpthread 514.100.2 (0019-stage-libpthread.sh, same edits)
[[ -d bsd/pthread/sweet_libpthread ]] && { echo >&2 "refusing to overwrite sweet_libpthread"; exit 1; }

# Every file this script adds must compile out for other machine configs:
# xnu's makefile includes each `standard` file in every config, and dxb's
# VMAPPLE bootstrap kernel cannot link SWEET-only code.
if [ -n "${SWEET_GUARD:-}" ]; then
	# blobs-branch guard for sources the series adds without one (the CI
	# build applies xnu/patches/0083 first; this is for older checkouts).
	for f in bsd/dev/sweet_ufs.c bsd/dev/sweet_sample.c; do
		[ -f "$f" ] && python3 "$(dirname "$0")/sweet-guard.py" "$f"
	done
fi
mkdir -p bsd/pthread/sweet_libpthread
for d in kern private include; do cp -R "$mirror/libpthread/$d" bsd/pthread/sweet_libpthread/; done
python3 - <<'PY'
from pathlib import Path
target = Path('bsd/pthread/sweet_libpthread')
def replace(file, old, new, count):
    path = target / 'kern' / file
    text = path.read_text()
    if text.count(old) != count:
        raise SystemExit(f'libpthread source changed: {file}: {old!r}')
    path.write_text(text.replace(old, new))
replace('kern_trace.h', 'vm_kernel_unslide_or_perm_external(ptr,',
        'vm_kernel_unslide_or_perm_external((vm_offset_t)ptr,', 1)
for callback, count in (('psynch_wait_update_owner', 4),
                        ('psynch_wait_complete', 1), ('psynch_wait_wakeup', 2)):
    replace('kern_synch.c', f'pthread_kern->{callback}(kwq,',
            f'pthread_kern->{callback}((uintptr_t)kwq,', count)
replace('kern_support.c', '*kevent_list_out = NULL;', '*kevent_list_out = 0;', 1)
replace('kern_support.c', 'user_addr_t kevent_list = NULL;',
        'user_addr_t kevent_list = 0;', 2)
replace('kern_support.c', 'workq_kevent(p, &th_addrs, NULL,',
        'workq_kevent(p, &th_addrs, 0,', 1)
replace('kern_support.c',
        'panic(__func__ ": thread_set_wq_state failed: %d", error);',
        'panic("%s: thread_set_wq_state failed: %d", __func__, error);', 4)
PY
sdk_file() {
	# TargetConditionals.h from the macOS SDK: xcrun on a Mac, the
	# osxcross SDK on Linux (deps/README.md).
	local f
	for f in "${OSXCROSS_SDK_ROOT:-}"/*/usr/include/TargetConditionals.h \
	         "$(ls -d /home/lvyufeng/Project/ios-gauguin/osxcross/osxcross-master/target/SDK/*/usr/include/TargetConditionals.h 2>/dev/null | head -1)"; do
		[ -f "$f" ] && { printf '%s' "$f"; return 0; }
	done
	command -v xcrun > /dev/null && printf '%s/usr/include/TargetConditionals.h' "$(xcrun --sdk macosx --show-sdk-path)"
}
SDK_TC=$(sdk_file)
[ -n "${SKIP_TARGET_MACROS:-}" ] || cp "$SDK_TC" bsd/pthread/sweet_libpthread/ 2>/dev/null || true
echo "Staged libpthread-514.100.2 from the mirror"

# HFS 627.100.6 (0026-stage-hfs.sh, same edits)
[[ -d bsd/sweet_hfs ]] && { echo >&2 "refusing to overwrite sweet_hfs"; exit 1; }
mkdir -p bsd/sweet_hfs
for entry in core hfs_encodings; do cp -R "$mirror/hfs/$entry" bsd/sweet_hfs/; done
python3 - <<'PY'
from pathlib import Path
path = Path('bsd/sweet_hfs/core/hfs_iokit.h')
text = path.read_text()
include = '#include <AppleKeyStore/AppleKeyStoreFSServices.h>\n'
first = 'int hfs_unwrap_key('
end = '__END_DECLS'
if text.count(include) != 1 or text.count(first) != 1 or text.count(end) != 1:
    raise SystemExit(f'HFS source changed: {path}')
text = text.replace(include, '#if CONFIG_PROTECT\n' + include + '#endif\n')
i, j = text.index(first), text.index(end)
text = text[:i] + '#if CONFIG_PROTECT\n' + text[i:j].rstrip('\n') + '\n#endif\n\n' + text[j:]
path.write_text(text)
PY
[ -n "${SKIP_TARGET_MACROS:-}" ] || cp "$SDK_TC" bsd/sweet_hfs/
echo "Staged hfs-627.100.6 from the mirror"

