#!/usr/bin/env python3
"""Compare a regenerated JSON artifact against the released copy.

Byte-identity is the default expectation. Two artifacts legitimately differ,
for reasons documented in REDACTIONS.md and in CLAIMS.md caveat C2, and only in ways
named explicitly on the command line:

  --allow-extra KEY     the released copy carries a top-level KEY the regenerated one
                        does not (a hand-recorded field the script never emits)
  --allow-differ PATH   a dotted path whose value may differ (provenance of a redacted
                        input, never a scientific quantity)

Anything not named is treated as a failure. The script exits 0 only if the two artifacts
agree everywhere else, so an unexpected drift cannot be absorbed by this comparator.

  python3 compare_artifact.py RELEASED REGENERATED [--allow-extra K] [--allow-differ P]
"""
from __future__ import annotations

import argparse
import json
import sys


def flatten(obj, prefix=""):
    """Flatten nested dicts to dotted paths; lists are compared as whole values."""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else k))
    else:
        out[prefix] = obj
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("released")
    ap.add_argument("regenerated")
    ap.add_argument("--allow-extra", action="append", default=[])
    ap.add_argument("--allow-differ", action="append", default=[])
    a = ap.parse_args()

    with open(a.released, "rb") as f:
        rb = f.read()
    with open(a.regenerated, "rb") as f:
        gb = f.read()
    if rb == gb:
        print("byte-identical")
        return 0
    if not a.allow_extra and not a.allow_differ:
        print("FAIL: artifacts differ and no deviation was declared")
        return 1

    rel = json.loads(rb.decode("utf-8"))
    gen = json.loads(gb.decode("utf-8"))

    extra_rel = sorted(set(rel) - set(gen)) if isinstance(rel, dict) else []
    extra_gen = sorted(set(gen) - set(rel)) if isinstance(gen, dict) else []

    frel, fgen = flatten(rel), flatten(gen)
    allowed_prefixes = tuple(a.allow_extra) + tuple(a.allow_differ)
    differ = sorted(
        p for p in set(frel) & set(fgen)
        if frel[p] != fgen[p] and not p.startswith(allowed_prefixes)
    )

    unexpected_rel = [k for k in extra_rel if k not in a.allow_extra]
    unexpected_gen = [k for k in extra_gen if k not in a.allow_extra]

    ok = not (differ or unexpected_rel or unexpected_gen)
    for label, items in (("UNEXPECTED EXTRA IN RELEASED", unexpected_rel),
                         ("UNEXPECTED EXTRA IN REGENERATED", unexpected_gen),
                         ("UNEXPECTED VALUE DRIFT", differ)):
        if items:
            print(f"{label}: {items[:10]}")

    if ok:
        notes = []
        if a.allow_extra:
            notes.append("released copy additionally carries " + ", ".join(a.allow_extra))
        if a.allow_differ:
            shown = [p for p in a.allow_differ if frel.get(p) != fgen.get(p)]
            if shown:
                notes.append("declared deviation at " + ", ".join(shown))
        print("identical on every undeclared field" + ("; " + "; ".join(notes) if notes else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
