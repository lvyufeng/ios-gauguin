#!/usr/bin/env python3
"""Execute actual BCM transport with strict host MMIO/platform seams.

The real planner builds an independently encoded synthetic six-row fixture.
Only actual volatile accesses/barriers and kernel platform APIs are seamed.
No device, real sleep, shell, network, generated assembly or object patching.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SOURCE = Path(os.environ.get('XNU_SOURCE', str(ROOT / '.deps-cache/p0-20261105/source115-codex')))
FIXTURE = HERE / 'fixtures/gauguin_bcm_transport_host.c'
FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic", "-O1", "-g",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"platform seam changed: {old}")
    return text.replace(old, new)


def prepare(source_path):
    source = source_path.read_text()
    source = re.sub(r"^#include .*\n", "", source, flags=re.MULTILINE)
    source = replace_once(source, "uint32_t value = *(volatile uint32_t *)(gt_map + offset);",
                          "uint32_t value = fake_read(offset);")
    source = replace_once(source, "*(volatile uint32_t *)(gt_map + offset) = value;",
                          "fake_write(offset, value);")
    source = replace_once(source, '__asm__ volatile("dmb oshld" ::: "memory");', "fake_dmb_read();")
    source = replace_once(source, '__asm__ volatile("dmb oshst" ::: "memory");', "fake_dmb_store();")
    source = replace_once(source, '__asm__ volatile("dsb osh" ::: "memory");', "fake_dsb();")
    assert source.index("gt_wrote = true;") < source.index("fake_dmb_store();") < source.index("fake_write(offset, value);")
    if "__asm__" in source or "*(volatile" in source:
        raise ValueError("unseamed assembly/direct MMIO remains")
    return replace_once(FIXTURE.read_text(), "\n@SOURCE@\n", "\n" + source + "\n")


def run(command, log, env):
    log.write("$ " + shlex.join(map(str, command)) + "\n")
    log.flush()
    result = subprocess.run(list(map(str, command)), stdout=log, stderr=log, env=env)
    log.write(f"exit={result.returncode}\n")
    log.flush()
    if result.returncode:
        raise RuntimeError(f"command exited {result.returncode}: {command[0]}")


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, default=DEFAULT_SOURCE)
    args = parser.parse_args()
    dev = args.source_root.resolve() / 'bsd/dev'
    transport = lease = dev
    source = transport / "gauguin_bcm_transport.c"
    planner = dev / "gauguin_bcm_plan.c"
    inputs = [source, transport / "gauguin_bcm_transport.h", lease / "gauguin_wdt_lease.h",
              planner, dev / "gauguin_bcm_plan.h", dev / "cmd_db_snapshot.h", FIXTURE]
    for path in inputs:
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    build = Path(temporary)
    unit, binary, log_path = build / "transport_test.c", build / "transport_test", build / "run.log"
    report = {"state": "running", "build": str(build),
              "scope": "actual transport + actual planner; simulated RSC/WDT/GIC/time; no hardware qualification",
              "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    result_path = build / "result.json"
    result_path.write_text(json.dumps(report, indent=2) + "\n")
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "halt_on_error=1"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    try:
        unit.write_text(prepare(source))
        with log_path.open("w") as log:
            run(["clang", *FLAGS, "-I" + str(transport), "-I" + str(lease), "-I" + str(dev),
                 unit, planner, "-o", binary], log, env)
            run([binary], log, env)
        if {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs} != report["inputs"]:
            raise RuntimeError("test input changed while running")
        report["state"] = "passed"
    except Exception as error:
        report.update(state="failed", error=str(error))
        print(f"FAIL: {error}; {log_path}", file=sys.stderr)
        if log_path.exists():
            print("\n".join(log_path.read_text().splitlines()[-35:]), file=sys.stderr)
        return 1
    finally:
        result_path.write_text(json.dumps(report, indent=2) + "\n")
    print(log_path.read_text().splitlines()[-2])
    print(f"PASS: BCM transport host fixture; {result_path}")
    return 0


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="gauguin-bcm-transport-") as temporary:
        raise SystemExit(main(temporary))
