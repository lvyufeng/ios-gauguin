#!/usr/bin/env python3
"""Check the user's500GB project limit before allocating an entire artifact batch.

Accounting defaults to the canonical Git project root for this checkout. In a
linked worktree the Git common directory names the main checkout's .git, so the
main project root (not the narrow linked worktree) is counted. A non-Git
standalone checkout keeps the historical script-root behavior.

--root may widen accounting to an explicit ancestor. It is refused when it
would omit either the inferred canonical root or this checkout, so a narrow
override cannot hide artifacts.
"""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys

LIMIT_BYTES = 500_000_000_000


class ScopeError(RuntimeError):
    """The accounting root cannot be established without omitting files."""


def git_common_dir(checkout: Path) -> Path | None:
    """A failed lookup in a marked Git checkout cannot become narrow fallback."""
    marker = next((parent / ".git" for parent in (checkout, *checkout.parents)
                   if (parent / ".git").exists() or (parent / ".git").is_symlink()), None)
    def unavailable(reason: str) -> None:
        if marker is not None:
            raise ScopeError(f"Git metadata exists at {marker}, but {reason}; refusing fallback scope")
    try:
        proc = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True, text=True)
    except OSError as error:
        unavailable(f"Git lookup failed: {error}")
        return None
    if proc.returncode != 0:
        unavailable(f"Git lookup exited {proc.returncode}")
        return None
    value = proc.stdout.strip()
    if not value:
        unavailable("Git lookup returned no common directory")
        return None
    return Path(value).resolve()


def infer_canonical_root(checkout: Path) -> tuple[Path | None, Path | None]:
    """Return (canonical main checkout, common .git), or (None, None)."""
    common = git_common_dir(checkout)
    if common is None:
        return None, None
    if common.name != ".git" or not common.is_dir():
        raise ScopeError(
            f"Git common directory {common} is not a standard main .git directory; "
            "cannot infer the canonical project root"
        )
    root = common.parent
    if not (root / ".git").resolve() == common:
        raise ScopeError(
            f"{root / '.git'} does not resolve to Git common directory {common}; "
            "cannot infer the canonical project root"
        )
    return root, common


def resolve_scope(checkout: Path, explicit: Path | None) -> dict[str, object]:
    """Resolve the accounting root and describe how it was chosen."""
    inferred, common = infer_canonical_root(checkout)
    if explicit is not None:
        root = explicit.resolve()
        if not root.is_dir():
            raise ScopeError(f"--root is not a directory: {root}")
        if not checkout.is_relative_to(root):
            raise ScopeError(
                f"--root {root} does not contain this checkout {checkout}; "
                "accounting would omit current artifacts"
            )
        if inferred is not None and not inferred.is_relative_to(root):
            raise ScopeError(
                f"--root {root} is narrower than canonical root {inferred}; "
                "accounting would omit main-project artifacts"
            )
        mode = "explicit-root"
    elif inferred is None:
        root = checkout
        mode = "non-git-fallback"
    else:
        if not checkout.is_relative_to(inferred):
            raise ScopeError(
                f"linked checkout {checkout} lies outside inferred canonical root "
                f"{inferred}; pass --root with an ancestor containing both"
            )
        root = inferred
        mode = "git-canonical-root"
    return {
        "mode": mode,
        "script_checkout": str(checkout),
        "canonical_root": str(inferred) if inferred is not None else None,
        "git_common_dir": str(common) if common is not None else None,
        "requested_root": str(explicit.resolve()) if explicit is not None else None,
        "root": str(root),
    }


def allocated_bytes(root: Path) -> int:
    """Conservative allocated-byte count for root."""
    try:
        proc = subprocess.run(
            ["du", "-sk", str(root)],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ScopeError(f"cannot account allocated bytes under {root}: {error}") from error
    return int(proc.stdout.split()[0]) * 1024


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--planned-bytes",
        type=int,
        default=0,
        help="Conservative allocated size of all files/clones in the batch",
    )
    parser.add_argument(
        "--root",
        type=Path,
        help="Explicit conservative accounting ancestor (may not be narrower)",
    )
    args = parser.parse_args()
    if args.planned_bytes < 0:
        parser.error("planned bytes must be nonnegative")

    checkout = Path(__file__).resolve().parents[1]
    try:
        scope = resolve_scope(checkout, args.root)
        root = Path(str(scope["root"]))
        current = allocated_bytes(root)
    except ScopeError as error:
        print(f"storage budget refused: {error}", file=sys.stderr)
        return 2

    admitted = current + args.planned_bytes <= LIMIT_BYTES
    print(json.dumps(dict(
        root=str(root),
        scope=scope,
        current_accounted_bytes=current,
        planned_batch_bytes=args.planned_bytes,
        limit_bytes=LIMIT_BYTES,
        admitted=admitted,
        disk_free_bytes=shutil.disk_usage(root).free,
        accounting="du allocated bytes; shared APFS clones counted conservatively",
    ), indent=2))
    return 0 if admitted else 1


if __name__ == "__main__":
    raise SystemExit(main())
