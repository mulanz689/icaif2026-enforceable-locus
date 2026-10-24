#!/usr/bin/env python3
"""Fail-closed integrity check for the vendored upstream snapshot.

Every claim in the paper is scoped to one commit of one third-party repository:

    HKUDS/Vibe-Trading @ dddf96e35d511328b44a4307df0fb1cf49433e8d

`audit/snapshots/Vibe-Trading/` carries the subset of that commit the reproducers
touch (the 88 bundled skills, the materialization path, and the pre-trade guard).
This script verifies that every vendored file still hashes to the value recorded in
PIN_MANIFEST.sha256, and that the skill count is exactly 88. A mismatch invalidates
the paper's structural result for this tree, so it exits non-zero rather than warning.

  python3 verify_pin.py                 # verify the vendored subset
  python3 verify_pin.py --write         # (re)generate PIN_MANIFEST.sha256
  python3 verify_pin.py --against DIR   # also diff a fresh upstream clone at the pin
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN_ROOT = HERE / "audit" / "snapshots" / "Vibe-Trading"
MANIFEST = HERE / "PIN_MANIFEST.sha256"
COMMIT = "dddf96e35d511328b44a4307df0fb1cf49433e8d"
EXPECTED_SKILLS = 88


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(root: Path):
    for p in sorted(root.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc":
            yield p


def write_manifest() -> int:
    lines = [
        f"# HKUDS/Vibe-Trading @ {COMMIT}\n",
        "# Vendored subset: agent/src (import root + the 88 bundled skills),\n",
        "# plus LICENSE / NOTICE / README.md / pyproject.toml for attribution.\n",
        "# Paths are relative to audit/snapshots/Vibe-Trading/.\n",
    ]
    n = 0
    for p in walk(PIN_ROOT):
        lines.append(f"{sha256(p)}  {p.relative_to(PIN_ROOT)}\n")
        n += 1
    MANIFEST.write_text("".join(lines), encoding="utf-8")
    print(f"wrote {MANIFEST.name}: {n} files")
    return 0


def verify() -> int:
    if not MANIFEST.exists():
        print(f"FAIL: {MANIFEST.name} missing")
        return 1
    want = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        digest, rel = line.split("  ", 1)
        want[rel] = digest

    have = {str(p.relative_to(PIN_ROOT)): p for p in walk(PIN_ROOT)}
    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    drifted = sorted(r for r in set(want) & set(have) if sha256(have[r]) != want[r])

    n_skills = len([d for d in (PIN_ROOT / "agent" / "src" / "skills").iterdir()
                    if (d / "SKILL.md").is_file()])

    print(f"pin        : {COMMIT}")
    print(f"files      : {len(want)} in manifest, {len(have)} on disk")
    print(f"skills     : {n_skills} (expected {EXPECTED_SKILLS})")

    ok = True
    for label, items in (("MISSING", missing), ("UNTRACKED", extra), ("DRIFTED", drifted)):
        if items:
            ok = False
            print(f"{label} ({len(items)}):")
            for r in items[:20]:
                print(f"  {r}")
            if len(items) > 20:
                print(f"  ... and {len(items) - 20} more")
    if n_skills != EXPECTED_SKILLS:
        ok = False
        print(f"FAIL: skill count {n_skills} != {EXPECTED_SKILLS}")

    print("PIN VERIFY " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


def against(clone: Path) -> int:
    """Diff the vendored subset against a fresh upstream clone checked out at the pin."""
    bad = 0
    n = 0
    for p in walk(PIN_ROOT):
        rel = p.relative_to(PIN_ROOT)
        other = clone / rel
        if not other.is_file():
            print(f"ABSENT UPSTREAM  {rel}")
            bad += 1
            continue
        n += 1
        if sha256(p) != sha256(other):
            print(f"DRIFT            {rel}")
            bad += 1
    print(f"compared {n} files against {clone}; {bad} problem(s)")
    print("UPSTREAM CROSS-CHECK " + ("PASSED" if bad == 0 else "FAILED"))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    if "--write" in sys.argv:
        raise SystemExit(write_manifest())
    rc = verify()
    if "--against" in sys.argv:
        rc |= against(Path(sys.argv[sys.argv.index("--against") + 1]).resolve())
    raise SystemExit(rc)
