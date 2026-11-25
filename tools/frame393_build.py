"""Add bounded per-member CA receipts to the exact DPU and stock GPU candidate."""

import argparse
import difflib
from importlib import import_module
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha
from frame390_build import MEMBERSHIP, OBSERVER, TRANSACTIONS, replace_once

PREVIOUS = (MAIN/'research/tmp/gauguin-frame390-ca-timeline-worktree-20261123'
            /'research/tmp/frame-390/native-kernel/build-manifest.json')
P392 = (MAIN/'research/tmp/gauguin-frame392-native-stock-worktree-20261123'
        /'research/tmp/frame-392/native-kernel/build-manifest.json')
BASE = WORK/'research/tmp/frame-393'
HEADER = WORK/'graphics/gauguin-ca-timeline/Transaction393.h'
PREP392 = P392.parents[1]
DPU = import_module('frame390_build').DPU
DONORS = {
    'kdebug':MAIN/'research/tmp/gauguin-frame-380-worktree-20261122/research/tmp/frame-380/native-kernel/build-manifest.json',
    'ipc_kmsg':MAIN/'research/tmp/gauguin-frame-377-worktree-20261122/research/tmp/frame-377/native-kernel/build-manifest.json',
    'sweet_touch':MAIN/'research/tmp/gauguin-sdk-control-worktree-20261121/research/tmp/frame-362/native-kernel/build-manifest.json',
    'gauguin_ui_trace_board':DPU/'build-manifest.json',
}


def members(text):
    text = replace_once(text,'static void\nf390_swap', '''struct f393_member {
    uint64_t context;
    uint32_t id, version;
};

struct f393_members {
    struct f393_member entries[F385_MAX_MEMBERS];
    unsigned count;
};
static struct f393_members f393_versions[F385_SWIPES][F390_CAP];

static void
f390_swap''')
    text = replace_once(text,'''\tuint64_t context = 0;
\tuint32_t id = 0, version = 0;
\tbool ambiguous = false;''','''\tstruct f393_members *versions = &f393_versions[stroke-1][index];
\tunsigned member_count = 0;''')
    text = replace_once(text,'''\t\t\tambiguous |= context && (context != receipt.context || id != next_id || version != receipt.seed);
\t\t\tcontext = receipt.context;
\t\t\tid = next_id;
\t\t\tversion = receipt.seed;''','''\t\t\tconst struct f393_member value = {receipt.context, next_id, receipt.seed};
\t\t\tunsigned existing = 0;
\t\t\twhile (existing < member_count) {
\t\t\t\tconst struct f393_member *other = &versions->entries[existing];
\t\t\t\tif (other->context == value.context && other->id == value.id && other->version == value.version) break;
\t\t\t\t++existing;
\t\t\t}
\t\t\tif (existing == member_count) versions->entries[member_count++] = value;''')
    return replace_once(text,'''\tif (ambiguous) {
\t\trow->member = F390_AMBIGUOUS;
\t} else if (context) {
\t\trow->member = F390_PRESENT;
\t\trow->context = context;
\t\trow->id = id;
\t\trow->version = version;''','''\tversions->count = member_count;
\tif (member_count > 1) {
\t\trow->member = F390_AMBIGUOUS;
\t} else if (member_count == 1) {
\t\trow->member = F390_PRESENT;
\t\trow->context = versions->entries[0].context;
\t\trow->id = versions->entries[0].id;
\t\trow->version = versions->entries[0].version;''')


def transactions(text):
    marker = 'static void\nf390_drain_transactions(void)'
    require(text.count(marker)==1,'0390 transaction helper differs')
    added = HEADER.read_text().split('\nenum {',1)[1].removesuffix('#endif\n')
    return text[:text.index(marker)]+'enum {'+added+'#endif\n'


def stage(folder):
    baseline = Path(load(P392)['source'])
    inherited = Path(load(PREVIOUS)['source'])
    edits = {
        'bsd/kern/kdebug.c':(inherited/'bsd/kern/kdebug.c').read_text(),
        'osfmk/ipc/ipc_kmsg.c':(inherited/'osfmk/ipc/ipc_kmsg.c').read_text(),
        'bsd/dev/sweet_touch.c':(inherited/'bsd/dev/sweet_touch.c').read_text(),
        'bsd/dev/gauguin_ui_trace_board.c':(inherited/'bsd/dev/gauguin_ui_trace_board.c').read_text(),
        'bsd/dev/gauguin_frame385.h':(inherited/'bsd/dev/gauguin_frame385.h').read_text(),
        MEMBERSHIP:members((inherited/MEMBERSHIP).read_text()),
        TRANSACTIONS:transactions((inherited/TRANSACTIONS).read_text()),
        OBSERVER:replace_once((inherited/OBSERVER).read_text(),'f390_drain_transactions();','f393_drain_transactions();'),
    }
    changes = []
    source = folder/'source'
    for path,text in edits.items():
        target = source/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(text)
        before = baseline/path
        original = before.read_text().splitlines(keepends=True) if before.exists() else []
        changes.extend(difflib.unified_diff(original,text.splitlines(keepends=True),'a/'+path,'b/'+path))
    patch = folder/'393-ca-members.patch'
    patch.write_text(''.join(changes))
    return source,patch


def native():
    admission = load(PREP392/'next-development-admission.json')
    require(admission['admitted'] and admission['planned_batch_bytes']==290_000_000,
            '0393 staged local build is outside the admitted development batch')
    host = load(BASE/'offline.json')
    require(host['ASan_UBSan'] and host['exact_members']==2 and not host['device_commands'],
            '0393 multi-member host validation absent')
    with TemporaryDirectory(prefix='0393-patch-',dir=BASE) as temporary:
        _,generated = stage(Path(temporary))
        checked = BASE/'393-ca-members.patch'
        require(sha(generated)==host['stage_patch_sha256'],'0393 host and ARM64 sources differ')
        with checked.open('xb') as stream: stream.write(generated.read_bytes())
    units = tuple((name,path,'compile-'+name) for name,path in DONORS.items())
    output = BASE/'native-kernel'
    import_module('build-frame347').link_scanout(P392,output,parent_trial='0392',trial='0393',patches=(checked,),
        extra_units=units,recompile_scanout=False,compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    receipt = load(output/'build-manifest.json')
    old,new = [Path(load(path)['source']) for path in (P392,output/'build-manifest.json')]
    unchanged = ('iokit/Kernel/arm/SweetFramebuffer.cpp','iokit/Kernel/arm/GauguinGPU.cpp',
                 'bsd/dev/gauguin_gmu_board.c','bsd/dev/gauguin_gmu_firmware.c')
    require(receipt['inputs_unchanged'] and receipt['baseline_reproduced_except_uuid'] and
        {Path(path).stem for path in receipt['object_replacements'].values()}==DONORS.keys() and
        all(sha(old/name)==sha(new/name) for name in unchanged),'0393 kernel scope differs')
    return dict(kernel_sha256=receipt['kernel_sha256'],identity=receipt['identity'],
                patch_sha256=sha(checked),device_commands=0)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    print(json.dumps(native(),indent=2))
