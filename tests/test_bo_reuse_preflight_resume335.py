"""Exercise preservation and refusal around the actual no-write preflight proof."""
from pathlib import Path
import importlib.util
import json
import shutil
import tempfile

WORK = Path(__file__).resolve().parents[1]
BASE = WORK / 'research/tmp/bo-reuse-335'
SOURCE = WORK / 'tools/resume-bo-reuse-preflight.py'
spec = importlib.util.spec_from_file_location('resume335', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
pins = {str(p): module.sha(p) for p in [SOURCE, Path(__file__).resolve()]}
observed = {str(BASE / 'execution' / name): digest for name, digest in module.FAILED.items()}
dead = lambda pid: False
negative = 0


def refused(base, alive=dead):
    global negative
    try:
        module.verify_failed_preflight(base, alive)
    except ValueError:
        negative += 1
    else:
        raise AssertionError('unsafe continuation accepted')


with tempfile.TemporaryDirectory() as temp:
    base = Path(temp)
    execution = base / 'execution'
    execution.mkdir()
    for name in module.FAILED:
        shutil.copyfile(BASE / 'execution' / name, execution / name)
    audit = module.verify_failed_preflight(base, dead)
    refused(base, lambda pid: True)
    original = (execution / 'result.json').read_bytes()
    for key, value in (('installed', True), ('boot_attempts', 1), ('misc_marker_written', True),
                       ('boot_started', True), ('restore_attempted', True), ('recovery_fallbacks', 1),
                       ('partition_write_phase', 'observer-installed'), ('error', 'different failure')):
        changed = json.loads(original)
        changed[key] = value
        (execution / 'result.json').write_text(json.dumps(changed))
        refused(base)
        (execution / 'result.json').write_bytes(original)
    for name in ('progress.jsonl', 'fresh-before', 'observer-process.json'):
        p = execution / name
        p.touch()
        refused(base)
        p.unlink()
    (base / 'preflight-no-device').mkdir()
    refused(base)
    (base / 'preflight-no-device').rmdir()
    archive = module.archive_failed_preflight(base, audit, dead)
    assert not execution.exists()
    assert all(module.sha(archive / 'execution' / n) == d for n, d in module.FAILED.items())
    refused(base)

assert all(module.sha(Path(p)) == digest for p, digest in {**pins, **observed}.items())
result = dict(state='BC335-exact-no-write-preflight-preservation-and-refusals-passed',
              negative_cases=negative, failed_proofs_preserved_byte_identical=True,
              original_execution_and_inputs_unchanged=True, failed_preflight_proof_hashes=module.FAILED, device_commands=0,
              device_writes=0, boot_attempts=0, input_pins=pins)
with (BASE / 'preflight-resume-test-v2.json').open('x') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in result.items() if k != 'input_pins'}, indent=2))
