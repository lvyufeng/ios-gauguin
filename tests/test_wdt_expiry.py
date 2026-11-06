#!/usr/bin/env python3
"""Run actual watchdog worker/lease/header/helper/start gate with host-only seams.

Only aligned MMIO loads/stores, DMB/DSB, and platform APIs are mocked. No
hardware, reset, sleeping, network, shell, assembly generation or object patch.
The fixture verifies every access barrier and ordered store values; it does not
claim that host success qualifies a physical watchdog reset.
"""
import argparse
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
FIXTURE = HERE / "fixtures/gauguin_wdt_test_host.c"
REPO = HERE.parent
FLAGS = ["-std=c11", "-Wall", "-Wextra", "-Werror", "-pedantic",
         "-fsanitize=address,undefined", "-fno-omit-frame-pointer", "-g", "-O1"]


def function(source, return_type, name):
    """Extract one complete actual definition; these three functions use no brace literals."""
    start = re.search(r"^" + re.escape(return_type) + r"\n" + re.escape(name) +
                      r"\([^;]*?\)\n\{", source, re.MULTILINE)
    if not start:
        raise ValueError(f"actual function definition missing: {name}")
    depth = 0
    opening = source.index("{", start.start())
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start.start():index + 1] + "\n"
    raise ValueError(f"unterminated actual function: {name}")


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"expected exactly one platform seam: {old}")
    return source.replace(old, new)


def prepare(worker_path, pe_path, watchdog_path):
    worker = worker_path.read_text()
    worker = re.sub(r"^#include .*$\n?", "", worker, flags=re.MULTILINE)
    worker = replace_once(worker,
        "uint32_t value = *(volatile uint32_t *)(wdt_mapping + offset);",
        "uint32_t value = fake_wdt_read(offset);")
    worker = replace_once(worker,
        "*(volatile uint32_t *)(wdt_mapping + offset) = value;",
        "fake_wdt_write(offset, value);")
    worker = replace_once(worker, '__asm__ volatile("dmb oshld" ::: "memory");', "fake_dmb();")
    worker = replace_once(worker, '__asm__ volatile("dsb sy" ::: "memory");', "fake_dsb();")
    helper = function(pe_path.read_text(), "bool", "sweet_wdt_irq_quiet")
    helper = replace_once(helper, '__asm__ volatile("dmb oshld" ::: "memory");', "fake_dmb();")
    gate = function(watchdog_path.read_text(), "void", "sweet_wdt_thread_start")
    fixture = FIXTURE.read_text()
    for marker, body in [("@IRQ_HELPER@", helper), ("@WORKER@", worker), ("@LEGACY_GATE@", gate)]:
        fixture = replace_once(fixture, "\n" + marker + "\n", "\n" + body + "\n")
    if "__asm__" in fixture or "*(volatile" in fixture:
        raise ValueError("unseamed assembly/direct MMIO remains")
    return fixture


def invoke(command, log, env):
    log.write("$ " + shlex.join(map(str, command)) + "\n")
    log.flush()
    result = subprocess.run(list(map(str, command)), stdout=log, stderr=log, env=env)
    log.write(f"exit={result.returncode}\n")
    log.flush()
    if result.returncode:
        raise RuntimeError(f"command exited {result.returncode}: {command[0]}")


def main(temporary):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(os.environ.get("XNU_SOURCE", str(REPO / ".deps-cache/p0-20261105/source115-codex"))),
                        help="optional complete integrated XNU tree; otherwise use authored candidate files")
    args = parser.parse_args()
    if args.source_root:
        root = args.source_root.resolve()
        worker = root / "bsd/dev/gauguin_wdt_test.c"
        header = root / "bsd/dev/gauguin_wdt_lease.h"
        pe = root / "pexpert/arm/pe_fiq.c"
        watchdog = root / "iokit/Kernel/arm/SweetWatchdog.cpp"
        conf = (root / 'bsd/conf/files').read_text()
        assert conf.count('bsd/dev/gauguin_wdt_test.c\t\tstandard') == 1
        init = (root / 'bsd/kern/bsd_init.c').read_text()
        blocks = re.findall(r'#if defined\(GAUGUIN\)\n([^#]+)#endif', init)
        assert init.count('sweet_wdt_test_init();') == 1
        assert any('\tsweet_wdt_test_init();\n' in block for block in blocks)
        assert any('extern void sweet_wdt_test_init(void);\n' in block for block in blocks)
    inputs = [FIXTURE, worker, header, pe, watchdog]
    for path in inputs:
        if not path.is_file():
            raise SystemExit(f"missing input: {path}")
    build = Path(temporary)
    unit, binary, log_path = build / "wdt_host.c", build / "wdt_host", build / "run.log"
    report = {"state": "running", "source_root": str(root), "build": str(build),
              "scope": "actual C worker/lease + actual public header + GIC helper + SweetWatchdog start gate; platform seams; no reset proof",
              "inputs": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}}
    result_path = build / "result.json"
    result_path.write_text(json.dumps(report, indent=2) + "\n")
    env = os.environ.copy()
    # macOS ASan does not support forcing detect_leaks=1. Keep diagnostics fatal.
    env["ASAN_OPTIONS"] = "halt_on_error=1"
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=1"
    try:
        unit.write_text(prepare(worker, pe, watchdog))
        with log_path.open("w") as log:
            invoke(["clang", *FLAGS, "-I", header.parent, unit, "-o", binary], log, env)
            invoke([binary], log, env)
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
        if after != report["inputs"]:
            raise RuntimeError("test input changed during execution")
        output = log_path.read_text()
        assert 'PASS: retained 87 original WDT worker/helper cases' in output
        match = re.search(r'PASS: 87 original \+ (\d+) lease cases \((\d+) total\);', output)
        assert match and int(match[1]) > 0 and int(match[2]) == 87 + int(match[1])
        report.update(state="passed", original_cases=87, lease_cases=int(match[1]), total_cases=int(match[2]))
    except Exception as error:
        report.update(state="failed", error=str(error))
        print(f"FAIL: {error}; {log_path}", file=sys.stderr)
        if log_path.exists():
            print("\n".join(log_path.read_text().splitlines()[-30:]), file=sys.stderr)
        return 1
    finally:
        result_path.write_text(json.dumps(report, indent=2) + "\n")
    print(log_path.read_text().splitlines()[-2])
    print(f"PASS: watchdog lease host fixture; {result_path}")
    return 0


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="gauguin-wdt-lease-") as temporary:
        raise SystemExit(main(temporary))
