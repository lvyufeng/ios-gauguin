#!/usr/bin/env python3
"""Prepare console-safe refusal rows and absolute-uptime bounded process sampling."""
from pathlib import Path
import difflib
import hashlib
import json
import shutil

MAIN = Path('/Users/baai/Project/ios-gauguin')
WORK = Path(__file__).resolve().parents[1]
STATE = WORK/'research/tmp/gesture-sample-328'
BASE = MAIN/'research/tmp/gauguin-submit-reject-worktree-20261115/research/tmp/submit-reject-327'
CHANGED = ('iokit/Kernel/arm/GauguinGPU.cpp', 'bsd/dev/sweet_sample.c')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def compact(raw):
    old = 'SWEET GPU SUBMIT327: seq=%u tick=%llu token=%llu rc=%08x stage=%u index=%u handle=%u requested=%08x actual=%08x bo_state=%u cmd_type=%u cmd_index=%u cmd_offset=%u cmd_bytes=%u bos=%u cmds=%u queue=%u flags=%08x fence=%u pending=%u native=%u bytes=%llu\\n'
    # Same22 fields in the same order. 19u32/3u64 hexadecimal values make every
    # row235 bytes including newline, below the actual255-byte serial limit.
    fields = ['%016llx' if i in (1,2,21) else '%08x' for i in range(22)]
    new = 'SWEET GS328: '+' '.join(fields)+'\\n'
    assert raw.count(old) == 1
    raw = raw.replace(old,new)
    assert raw.count('SWEET GPU SUBMIT327: limit=64 coverage=incomplete') == 1
    raw = raw.replace('SWEET GPU SUBMIT327: limit=64 coverage=incomplete', 'SWEET GS328: limit=64 coverage=incomplete')
    raw = raw.replace('/* SUBMIT327: CPU metadata only under the existing request/GPU locks.', '/* SUBMIT328: same327 CPU metadata under the existing request/GPU locks.\n * Fixed-width hex rows are235 bytes including newline, within the actual\n * 255-byte serial console payload limit. No fields or bits are omitted.')
    return raw

WAIT = '''/* Profile328 uses the same boot-uptime clock as UI trace. A sampler thread
 * started45s after boot must not shift the220s observation to265s. Each of
 * eight deadlines is absolute; refuse >1s lateness instead of catching up
 * with a burst. At most8 bounded sleeps per deadline handle early wakeups.
 * This bounds scheduling attempts, not time spent suspending a user thread. */
static bool
sweet_sample_wait328(void *chan, unsigned seconds)
{
    const uint64_t second = 1000000000ULL;
    const uint64_t deadline = (uint64_t)seconds * second;
    if (seconds < 220 || seconds > 262 || hz < 1 || hz > 10000) {
        return false;
    }
    for (unsigned attempt = 0; attempt <= 8; attempt++) {
        uint64_t now = 0;
        absolutetime_to_nanoseconds(mach_absolute_time(), &now);
        if (now >= deadline) {
            return now - deadline <= second;
        }
        if (attempt == 8) {
            return false;
        }
        uint64_t left = deadline - now;
        uint64_t ticks = (left / second) * (unsigned)hz +
            ((left % second) * (unsigned)hz + second - 1) / second;
        if (!ticks || ticks > 2200000) {
            return false;
        }
        (void)tsleep(chan, PZERO, "sweetsmp", (int)ticks);
    }
    return false;
}

'''

def sampler(raw):
    def edit(old,new):
        nonlocal raw
        assert raw.count(old) == 1, old
        raw = raw.replace(old,new)
    edit('static void\nsweet_sample_thread(', WAIT+'static void\nsweet_sample_thread(')
    edit('if (profile != 316) {','if (profile != 316 && profile != 328) {')
    edit('printf("SMP316 refused: reason=mixed-options\\n");','printf("SMP%d refused: reason=mixed-options\\n", profile);')
    old='''	printf("SMP armed: %s delay=%d interval=%d count=%d\\n",
	    sweet_sample_names, first, interval, count);
	if (fixed_profile) {
		printf("SMP316 armed: targets=%s delay=%d interval=%d count=%d max_targets=2 max_threads=64 frames=16 coherent_frames=0\\n",
		    sweet_sample_names, first, interval, count);
	}
	(void)tsleep(&chan, PZERO, "sweetsmp", first * hz);'''
    new='''	if (fixed_profile && profile == 328) {
		printf("SMP armed: %s uptime=%d interval=%d count=%d\\n",
		    sweet_sample_names, first, interval, count);
		printf("SMP328 armed: targets=%s uptime=%d interval=%d count=%d max_targets=2 max_threads=64 frames=16 coherent_frames=0 lateness_us=1000000\\n",
		    sweet_sample_names, first, interval, count);
	} else {
		printf("SMP armed: %s delay=%d interval=%d count=%d\\n",
		    sweet_sample_names, first, interval, count);
		if (fixed_profile) {
			printf("SMP316 armed: targets=%s delay=%d interval=%d count=%d max_targets=2 max_threads=64 frames=16 coherent_frames=0\\n",
			    sweet_sample_names, first, interval, count);
		}
		(void)tsleep(&chan, PZERO, "sweetsmp", first * hz);
	}'''
    edit(old,new)
    edit('''		struct sweet_sample_scope scope = { 0 };

		if (fixed_profile) {''','''		struct sweet_sample_scope scope = { 0 };

		if (fixed_profile && profile == 328 &&
		    !sweet_sample_wait328(&chan, (unsigned)(first + i * interval))) {
			printf("SMP328 refused: reason=deadline cycle=%d\\n", i);
			return;
		}
		if (fixed_profile) {''')
    edit('''printf("SMP316 begin cycle=%d tick=%llu\\n", i,''','''printf("SMP%d begin cycle=%d tick=%llu\\n", profile, i,''')
    edit('''printf("SMP316 end cycle=%d tick=%llu targets=%u duplicates=%u\\n", i,''','''printf("SMP%d end cycle=%d tick=%llu targets=%u duplicates=%u\\n", profile, i,''')
    edit('if (i + 1 < count) {','if (i + 1 < count && !(fixed_profile && profile == 328)) {')
    return raw

def main():
    parent_path = BASE/'local-link/build-manifest.json'
    assert sha(parent_path) == 'c5e71e3a1a3f15cfd34303918b944cdfa5b9452fa9faf67106647876ffa85a55'
    parent = json.loads(parent_path.read_text())
    budget = json.loads((STATE/'storage-whole-batch-admission.json').read_text())
    assert budget['admitted'] and budget['planned_batch_bytes'] == 800000000
    overlay = Path(parent['source_union']['overlay'])
    out = STATE/'kernel-source'
    out.mkdir(exist_ok=False)
    pins = {str(parent_path):sha(parent_path),str(Path(__file__).resolve()):sha(__file__)}
    for path in sorted(overlay.rglob('*')):
        if not path.is_file():
            continue
        assert sha(path) == parent['input_pins'][str(path)]['sha256']
        target = out/path.relative_to(overlay)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,target)
        pins[str(path)] = sha(path)
    patches = []
    for name, transform, leaf in zip(CHANGED,(compact,sampler),('0242-gauguin-console-submit-records.patch','0243-gauguin-uptime-sample-profile.patch')):
        old = (out/name).read_text()
        new = transform(old)
        assert old != new
        (out/name).write_text(new)
        patch = WORK/'xnu/patches'/leaf
        assert not patch.exists()
        patch.write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name)))
        patches.append(dict(path=str(patch),sha256=sha(patch)))
    result = dict(state='prepared-GESTURE328-console-and-uptime-source',source=str(out),changed_files=list(CHANGED),
                  parent_manifest_sha256=sha(parent_path),patches=patches,diagnostic_limit=64,limit_markers_max=1,
                  record_bytes_including_newline=235,serial_payload_bytes=255,submission_semantics_unchanged=True,
                  process_sample_uptime_seconds=list(range(220,263,6)),max_lateness_us=1000000,
                  max_wait_sleeps_per_deadline=8,process_rounds=8,max_processes_per_round=2,max_threads_per_process=64,
                  hard_suspend_time_bound=False,legacy_sampling_preserved=True,new_GPU_commands=0,new_MMIO_reads=0,
                  new_threads=0,input_pins=pins,device_commands=0)
    with (STATE/'source-preparation.json').open('x') as stream:
        json.dump(result,stream,indent=2)
        stream.write('\n')
    print(json.dumps({k:v for k,v in result.items() if k!='input_pins'},indent=2))

if __name__ == '__main__':
    main()
