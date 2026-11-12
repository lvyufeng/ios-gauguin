#!/usr/bin/env python3
"""Host-only integration checks for tools/storage-budget.py scope accounting.

Uses tiny real Git repositories, one real linked worktree nested inside its main
checkout, and one linked checkout outside its main checkout. Allocated fixture
bytes stay tiny. No network, device, or project-wide scan.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOOL = ROOT / "tools" / "storage-budget.py"
LIMIT_BYTES = 500_000_000_000
ARTIFACT_BYTES = 256 * 1024


def check(condition, message):
    if not condition:
        raise ValueError(message)


def run(argv, cwd=None):
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=cwd)
    return proc.returncode, proc.stdout, proc.stderr


def git(repo, *args):
    code, out, err = run(
        ["git", "-C", str(repo), "-c", "user.name=Fixture",
         "-c", "user.email=fixture@example.invalid", *args]
    )
    check(code == 0, f"git {' '.join(args)} failed: {err.strip()}")
    return out


def make_repo(path):
    path.mkdir(parents=True)
    git(path, "init", "-q")
    (path / "tracked.txt").write_text("fixture\n", encoding="utf-8")
    git(path, "add", "tracked.txt")
    git(path, "commit", "-qm", "fixture")


def install_tool(repo):
    tools = repo / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    target = tools / TOOL.name
    target.write_bytes(TOOL.read_bytes())
    return target


def allocate(path, size=ARTIFACT_BYTES):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(os.urandom(size))


def budget(tool, *args):
    code, out, err = run([sys.executable, str(tool), *args])
    parsed = None
    if out.strip():
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            parsed = None
    return code, parsed, out, err


def expect_budget(tool, args, expected_root, mode, expected_code=0):
    code, parsed, out, err = budget(tool, *args)
    check(code == expected_code,
          f"budget exit {code}, expected {expected_code}; stderr={err.strip()}")
    check(parsed is not None, f"budget did not emit JSON: {out!r} {err!r}")
    check(Path(parsed["root"]) == Path(expected_root).resolve(),
          f"budget root {parsed['root']} != {expected_root}")
    check(parsed["scope"]["mode"] == mode,
          f"scope mode {parsed['scope']['mode']} != {mode}")
    check(parsed["limit_bytes"] == LIMIT_BYTES, "500GB cap changed")
    return parsed


def main(temporary):
    temporary = Path(temporary)
    tool_before = hashlib.sha256(TOOL.read_bytes()).hexdigest()

    # Canonical main with a nested linked worktree and an artifact outside it.
    main = temporary / "nested" / "main"
    make_repo(main)
    artifact = main / "artifacts" / "outside-worktree.bin"
    allocate(artifact)
    linked = main / "linked" / "checkout"
    (main / "linked").mkdir()
    git(main, "worktree", "add", "-q", str(linked), "HEAD")
    install_tool(main)
    linked_tool = install_tool(linked)

    nested = expect_budget(
        linked_tool, ["--planned-bytes", "0"], main, "git-canonical-root")
    check(nested["current_accounted_bytes"] >= ARTIFACT_BYTES,
          "nested invocation omitted the artifact outside its worktree")
    primary = expect_budget(
        main / "tools" / TOOL.name, ["--planned-bytes", "0"],
        main, "git-canonical-root")
    check(primary["current_accounted_bytes"] == nested["current_accounted_bytes"],
          "primary and nested invocations disagree")
    check(primary["scope"]["git_common_dir"] == str((main / ".git").resolve()),
          "reported common directory is not the main .git")

    planned = LIMIT_BYTES - primary["current_accounted_bytes"] + 1
    oversized = expect_budget(
        main / "tools" / TOOL.name, ["--planned-bytes", str(planned)],
        main, "git-canonical-root", expected_code=1)
    check(oversized["admitted"] is False, "oversized batch was admitted")

    narrow_code, _, narrow_out, narrow_err = budget(
        linked_tool, "--root", str(linked), "--planned-bytes", "0")
    check(narrow_code == 2,
          f"too-narrow root accepted with exit {narrow_code}: {narrow_out}")
    check("narrower than canonical root" in narrow_err,
          f"narrow-root refusal did not explain scope: {narrow_err}")

    negative_code, _, _, _ = budget(main / "tools" / TOOL.name,
                                    "--planned-bytes", "-1")
    check(negative_code == 2, "negative planned batch was not refused")

    # Non-Git standalone keeps the script-root fallback.
    nogit = temporary / "nogit"
    allocate(nogit / "data" / "artifact.bin", 64 * 1024)
    nogit_tool = install_tool(nogit)
    fallback = expect_budget(
        nogit_tool, ["--planned-bytes", "0"], nogit, "non-git-fallback")
    check(fallback["current_accounted_bytes"] >= 64 * 1024,
          "non-Git fallback omitted its own artifact")

    # A linked checkout outside its main root must not silently count only itself.
    external = temporary / "external"
    external_main = external / "main"
    external_linked = external / "linked-checkout"
    make_repo(external_main)
    git(external_main, "worktree", "add", "-q", str(external_linked), "HEAD")
    external_tool = install_tool(external_linked)
    outside_code, _, _, outside_err = budget(
        external_tool, "--planned-bytes", "0")
    check(outside_code == 2,
          f"outside linked checkout was silently accounted: {outside_err}")
    check("pass --root" in outside_err,
          f"outside-linked refusal did not request an explicit ancestor: {outside_err}")
    widened = expect_budget(
        external_tool,
        ["--root", str(external), "--planned-bytes", "0"],
        external, "explicit-root")

    tool_after = hashlib.sha256(TOOL.read_bytes()).hexdigest()
    check(tool_before == tool_after, "storage tool changed during the test")

    print(json.dumps({
        "state": "passed",
        "nested_root": nested["root"],
        "nested_accounted_bytes": nested["current_accounted_bytes"],
        "primary_accounted_bytes": primary["current_accounted_bytes"],
        "oversized_planned_bytes": planned,
        "widened_root": widened["root"],
        "tool_sha256": tool_after,
    }, indent=2))
    return 0


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="gauguin-storage-budget-") as tmp:
        try:
            raise SystemExit(main(tmp))
        except Exception as error:
            print(f"FAIL: {error}", file=sys.stderr)
            raise SystemExit(1)
