#!/usr/bin/env python3
"""Build and execute the actual bus worker through small platform seams.

No hardware, network, shell, assembly generation, or object rewriting. The
production bus_mmio_read load/barrier definition alone is replaced by a plain C
forwarder; real parser and planner are linked unchanged. Native SHA is mocked
by an explicit exact-byte seam using Python's SHA of the immutable positive DB.
The exported actual worker RAW log must round-trip through the real extractor.
This covers the log protocol and normal-memory hash input, not native crypto.
"""
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SOURCE_ROOT = Path(os.environ.get("XNU_SOURCE", str(REPO / ".deps-cache/p0-20261105/source115-codex"))).resolve()
DEV = SOURCE_ROOT / "bsd/dev"
FIXTURE = HERE / "fixtures/gauguin_bus_probe_host.c"
SOURCE = DEV / "gauguin_bus_probe.c"
EXTRACTOR = REPO / "tools/extract_cmd_db_snapshot.py"
CFLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
          "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g", "-O1"]


def prepare():
    fixture, source = FIXTURE.read_text(), SOURCE.read_text()
    marker = "\n@WORKER@\n"
    assert fixture.count(marker) == 1, "one actual worker injection marker"
    source = re.sub(r"^#include .*$\n?", "", source, flags=re.MULTILINE)
    helper = re.search(
        r"static uint32_t\nbus_mmio_read\(vm_offset_t base, uint32_t offset\)\n"
        r"\{\n.*?\n\}\n", source, flags=re.DOTALL)
    assert helper, "production MMIO seam signature changed"
    original = helper.group()
    assert "*(volatile uint32_t *)(base + offset)" in original
    assert '__asm__ volatile("dmb oshld" ::: "memory")' in original
    source = source[:helper.start()] + (
        "/* host platform seam: no real MMIO or barrier */\n"
        "static uint32_t\nbus_mmio_read(vm_offset_t base, uint32_t offset)\n"
        "{ return fake_bus_read32(base, offset); }\n") + source[helper.end():]
    assert "__asm__" not in source
    return fixture.replace(marker, "\n" + source + "\n")


def invoke(command, log, env):
    log.write("$ " + shlex.join(map(str, command)) + "\n")
    log.flush()
    result = subprocess.run(list(map(str, command)), stdout=log, stderr=log, env=env)
    log.write(f"exit={result.returncode}\n")
    log.flush()
    if result.returncode:
        raise RuntimeError(f"command exited {result.returncode}: {command[0]}")


def run(directory):
    entries = (SOURCE_ROOT / 'bsd/conf/files').read_text()
    for name in ('cmd_db_snapshot.c', 'gauguin_bcm_plan.c', 'gauguin_bus_probe.c'):
        assert entries.count('bsd/dev/' + name + '\t\tstandard') == 1
    init = (SOURCE_ROOT / 'bsd/kern/bsd_init.c').read_text()
    assert init.count('extern void sweet_bus_probe_init(void);') == 1
    assert init.count('sweet_bus_probe_init();') == 1
    blocks = re.findall(r'#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
    assert any('\tsweet_bus_probe_init();\n' in block for block in blocks)
    assert any('extern void sweet_bus_probe_init(void);\n' in block for block in blocks)
    sources = [DEV / "cmd_db_snapshot.c", DEV / "gauguin_bcm_plan.c"]
    for path in [FIXTURE, SOURCE, EXTRACTOR, REPO / "tools/kernel_banner.py", *sources]:
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    build = Path(directory)
    LOG = build / "run_bus_probe.log"
    unit, binary = build / "test_bus_probe.c", build / "test_bus_probe"
    emitted, raw_log = build / "positive_db.bin", build / "worker_positive.log"
    unit.write_text(prepare())
    env = os.environ.copy()
    # Apple arm64 ASan has no LeakSanitizer; retain address/UB checks there.
    env["ASAN_OPTIONS"] = "halt_on_error=1" + (":detect_leaks=1" if sys.platform != "darwin" else "")
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    env["PYTHONPATH"] = str(REPO / "tools")
    inputs = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [FIXTURE, SOURCE, EXTRACTOR, *sources]}
    record = {"state": "running", "build": str(build), "inputs": inputs,
              "scope": "host actual worker, explicit platform/SHA seams; no device"}
    report = build / "result.json"
    report.write_text(json.dumps(record, indent=2) + "\n")
    try:
        with LOG.open("w") as log:
            invoke(["clang", *CFLAGS, f"-I{DEV}", unit, *sources, "-o", binary], log, env)
            invoke([binary, "--emit-db", emitted], log, env)
            data = emitted.read_bytes()
            if len(data) != 131072:
                raise RuntimeError("synthetic DB must be exactly 131072 bytes")
            digest = hashlib.sha256(data).hexdigest()
            invoke([binary, "--digest", digest, "--log", raw_log], log, env)
            # Identity is synthetic and clearly labelled; no real device result.
            banner = b"Darwin Kernel Version 22.6.0: SYNTHETIC HOST WORKER FIXTURE; xnu-host-cmdb113"
            trial = "synthetic-worker-host-113"
            image, bound_log, decoded = build / "synthetic.image", build / "bound.log", build / "decoded.bin"
            image.write_bytes(banner + b"\x00")
            bound_log.write_bytes(banner + b"\nboot-args=sweetbusprobe=1 sweettrial=" +
                                  trial.encode("ascii") + b"\n" + raw_log.read_bytes())
            invoke([sys.executable, EXTRACTOR, "--image", image, "--log", bound_log,
                    "--trial", trial, "--out", decoded], log, env)
            if decoded.read_bytes() != data:
                raise RuntimeError("actual worker RAW/extractor round-trip differs from fixture DB")
            # The public prepare API is executed separately by the same
            # fixture; its own actual RAW output must also reconstruct fully.
            prepare_image = build / 'prepare.image'
            prepare_log = build / 'prepare-bound.log'
            prepare_decoded = build / 'prepare-decoded.bin'
            prepare_trial = 'synthetic-prepare-host-115'
            prepare_image.write_bytes(banner + b'\x00')
            prepare_log.write_bytes(banner + b'\nboot-args=sweetbusvote=1 sweettrial=' +
                                    prepare_trial.encode('ascii') + b'\n' +
                                    Path(str(raw_log) + '.prepare').read_bytes())
            invoke([sys.executable, EXTRACTOR, '--image', prepare_image,
                    '--log', prepare_log, '--trial', prepare_trial,
                    '--out', prepare_decoded], log, env)
            if prepare_decoded.read_bytes() != data:
                raise RuntimeError('prepare API RAW/extractor round-trip differs from fixture DB')
            log.write('PASS: prepare API -> own RAW log -> actual extractor -> exact fixture DB\n')
            after = {path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in inputs}
            if after != inputs:
                raise RuntimeError("test input changed during execution")
            record.update(state="passed", db_sha256=digest, raw_log=str(raw_log),
                          decoded=str(decoded), round_trip="exact 131072 bytes")
            log.write("PASS: actual worker -> bound RAW log -> actual extractor -> exact fixture DB\n")
    except Exception as error:
        record.update(state="failed", error=str(error))
        print(f"FAIL: {error}; see {LOG}", file=sys.stderr)
        if LOG.exists():
            print("\n".join(LOG.read_text().splitlines()[-30:]), file=sys.stderr)
        return 1
    finally:
        report.write_text(json.dumps(record, indent=2) + "\n")
    print(LOG.read_text())
    print("PASS: actual worker host tests and extractor round-trip")
    return 0


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="gauguin-bus-host-") as directory:
        raise SystemExit(run(directory))
