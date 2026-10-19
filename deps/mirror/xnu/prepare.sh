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

# libpthread 514.100.2 (0019-stage-libpthread.sh, same edits)
[[ -d bsd/pthread/sweet_libpthread ]] && { echo >&2 "refusing to overwrite sweet_libpthread"; exit 1; }
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
cp "$(xcrun --sdk macosx --show-sdk-path)/usr/include/TargetConditionals.h" bsd/pthread/sweet_libpthread/
echo "Staged libpthread-514.100.2 from the mirror"

# HFS 627.100.6 (0026-stage-hfs.sh, same edits)
[[ -d bsd/sweet_hfs ]] && { echo >&2 "refusing to overwrite sweet_hfs"; exit 1; }
mkdir -p bsd/sweet_hfs
for entry in "$mirror"/hfs/*; do cp -R "$entry" bsd/sweet_hfs/; done
python3 - <<'PY'
from pathlib import Path
path = Path('bsd/sweet_hfs/core/hfs_vfsutils.c')
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
cp "$(xcrun --sdk macosx --show-sdk-path)/usr/include/TargetConditionals.h" bsd/sweet_hfs/
echo "Staged hfs-627.100.6 from the mirror"

