"""Stage and locally link bounded CA transaction receipts over the 0388 DPU build."""

import difflib
from importlib import import_module
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from frame366_scope import MAIN, WORK, load, require, sha

BASE = WORK/'research/tmp/frame-390'
CA = MAIN/'research/tmp/gauguin-ca-receipt-analysis-worktree-20261123'
DPU = MAIN/'research/tmp/gauguin-frame388-android-display-worktree-20261123/research/tmp/frame-388/native-kernel-final'
OBSERVER = 'bsd/dev/gauguin_frame385_observer.h'
MEMBERSHIP = 'bsd/dev/gauguin_frame390_membership.h'
TRANSACTIONS = 'bsd/dev/gauguin_frame390_transactions.h'
HEADER = WORK/'graphics/gauguin-ca-timeline/Transaction390.h'
CAP = 3072


def load_ca_port():
    # The 0386 observer tools remain in their own pinned worktree. Use its
    # patch set while keeping this checkout's 0388/0389 runners on sys.path.
    path = str(CA/'tools')
    if path not in sys.path:
        sys.path.append(path)
    port = import_module('check-frame390-display-port')
    port.PATCHES = CA/'xnu/patches'
    return port


def replace_once(text, old, new):
    require(text.count(old)==1,'CA observer base differs at '+old[:80])
    return text.replace(old,new)


def compact(source):
    member = source/MEMBERSHIP
    text = member.read_text()
    text = replace_once(text,'''static struct f390_lane {
	struct {
		uint64_t tick, thread, context;
		uint32_t swap, seed, id, version;
		uint8_t member, gate;
	} rows[F390_CAP];''','''struct f390_snapshot {
	uint64_t tick, thread, context, update;
	uint32_t swap, seed, id, version;
	uint8_t member, gate;
};

static struct f390_lane {
	struct f390_snapshot rows[F390_CAP];''')
    text = replace_once(text,'\trow->swap = swap;', '\trow->update = update;\n\trow->swap = swap;')
    member.write_text(text)

    observer = source/OBSERVER
    text = observer.read_text()
    text = replace_once(text,'F385_CAP = 1536, F385_BLOCK = 24, F385_WIRE = 48, F385_RECEIPTS = 256,',
                        f'F385_GESTURE_CAP = {CAP}, F385_RECEIPTS = 256,')
    text = replace_once(text,'''static struct f385_row f385_rows[F385_CAP];
static unsigned f385_count, f385_windows;
static uint64_t f385_source, f385_receiver, f385_begin, f385_until;''','''/* A later stroke cannot consume the earlier stroke's retention. */
static struct f385_gesture {
	uint64_t begin, until;
	unsigned count;
	struct f385_row rows[F385_GESTURE_CAP];
} f385_gestures[F385_SWIPES];
static unsigned f385_windows;
static uint64_t f385_source, f385_receiver;''')
    text = replace_once(text,'''	__atomic_store_n(&f385_begin, start, __ATOMIC_RELAXED);
	__atomic_store_n(&f385_until, start + duration, __ATOMIC_RELAXED);''','''	f385_gestures[number-1].begin = start;
	f385_gestures[number-1].until = start + duration;''')
    text = replace_once(text,'''	if (!lane || tick < __atomic_load_n(&f385_begin, __ATOMIC_RELAXED) ||
	    tick >= __atomic_load_n(&f385_until, __ATOMIC_RELAXED) || tick >= f374_end) return 0;''','''	if (!lane) return 0;
	const struct f385_gesture *g = &f385_gestures[lane-1];
	if (tick < g->begin || tick >= g->until || tick >= f374_end) return 0;''')
    text = replace_once(text,'''		unsigned i = __atomic_fetch_add(&f385_count, 1, __ATOMIC_RELAXED);
		if (i < F385_CAP) {
			f385_rows[i] =''','''		struct f385_gesture *g = &f385_gestures[stroke-1];
		unsigned i = __atomic_fetch_add(&g->count, 1, __ATOMIC_RELAXED);
		if (i < F385_GESTURE_CAP) {
			g->rows[i] =''')
    text = replace_once(text,'#include "gauguin_frame390_membership.h"',
        '#include "gauguin_frame390_membership.h"\n#include "gauguin_frame390_transactions.h"')
    marker = 'static void\nf385_drain(void)\n{'
    require(text.count(marker)==1,'observer drain source differs')
    text = text[:text.index(marker)]+marker+'\n\tf390_drain();\n\tf390_drain_transactions();\n}\n'
    observer.write_text(text)
    (source/TRANSACTIONS).write_bytes(HEADER.read_bytes())


def stage(root):
    port = load_ca_port()
    source,pins = port.prepare(root)
    compact(source)
    files = (*port.UNITS, 'bsd/dev/gauguin_frame385.h', OBSERVER, MEMBERSHIP, TRANSACTIONS)
    base = DPU/'source'
    changes = []
    for name in files:
        before = base/name
        original = before.read_text().splitlines(keepends=True) if before.exists() else []
        current = (source/name).read_text().splitlines(keepends=True)
        require(current != original,'expected CA observer file did not change: '+name)
        changes.extend(difflib.unified_diff(original,current,'a/'+name if before.exists() else '/dev/null','b/'+name))
    patch = root/'390-ca-timeline.patch'
    patch.write_text(''.join(changes))
    return source, patch, {**pins,str(HEADER):sha(HEADER)}


def native():
    receipt = load(BASE/'live-batch-admission.json')
    require(receipt['admitted'] and receipt['planned_batch_bytes']==315_000_000,
            'full 0390 preparation and runtime batch must fit storage')
    with TemporaryDirectory(prefix='0390-patch-',dir=BASE) as folder:
        src, generated, pins = stage(Path(folder))
        checked = BASE/'390-ca-timeline.patch'
        checked.write_bytes(generated.read_bytes())
    tmp = MAIN/'research/tmp'
    manifest = DPU/'build-manifest.json'
    donors = {
        'kdebug':tmp/'gauguin-frame-380-worktree-20261122/research/tmp/frame-380/native-kernel/build-manifest.json',
        'ipc_kmsg':tmp/'gauguin-frame-377-worktree-20261122/research/tmp/frame-377/native-kernel/build-manifest.json',
        'sweet_touch':tmp/'gauguin-sdk-control-worktree-20261121/research/tmp/frame-362/native-kernel/build-manifest.json',
        'gauguin_ui_trace_board':manifest,
    }
    units = tuple((name,path,'compile-'+name) for name,path in donors.items())
    import_module('build-frame347').link_scanout(manifest,BASE/'native-kernel',
        parent_trial='0388',trial='0390',patches=(checked,),extra_units=units,
        recompile_scanout=False,compiler_bin=Path('/Library/Developer/CommandLineTools/usr/bin'))
    record = load(BASE/'native-kernel/build-manifest.json')
    require(record['inputs_unchanged'] and record['baseline_reproduced_except_uuid'] and
            sha(record['kernel'])==record['kernel_sha256'] and
            {Path(path).stem for path in record['object_replacements']}==set(donors),
            '0390 native code identity differs')
    new = Path(record['source'])
    for path in ('iokit/Kernel/arm/SweetFramebuffer.cpp','iokit/Kernel/arm/SweetPresentClock.h',
                 'bsd/dev/gauguin_frame388_receipts.h'):
        require(sha(new/path)==sha(DPU/'source'/path),'DPU scheduling or scanout source changed: '+path)
    return dict(state='0390-ARM64-CA-timeline-linked',kernel_sha256=record['kernel_sha256'],
        identity=record['identity'],inputs=pins,device_commands=0)
