#!/usr/bin/env python3
"""Source-verifying validator for environment constraint cards (no LLM).

Unlike a self-consistency validator (which only checks sha256(exact_text)==
declared_hash and can pass even when exact_text is a paraphrase), this one
RE-EXTRACTS each declared line span from the pinned enforcement.py and re-hashes
it. A card whose span does not match the real file bytes FAILS.

Checks:
  1. hash: declared sha256 == sha256 of the real pinned span.
  2. reason-code 1:1: every substantive card maps to a distinct guard reason
     code; no two cards share one (no merging distinct rule units).
  3. denominator/coverage consistency: rescue_denominator_eligible <=>
     (guard_supported and role=='authorization_constraint').
  4. required fields present per card.
  5. constraint_id uniqueness: the census is a deduplicated set (no id twice).
  6. dedup cross-check: the schema-doc ENV-EXCLUDE-01 exemplar (illustrative)
     must point to the SAME line span as the of-record census card, so the two
     representations can never diverge into a hidden duplicate.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = HERE / "snapshots" / "Vibe-Trading" / "agent" / "src" / "live" / "enforcement.py"
SCHEMA_DOC = HERE / "Constraint_Card_Schema_v0_1.md"
SPAN_RE = re.compile(r"^enforcement\.py:(\d+)-(\d+)$")


def span_hash(start: int, end: int) -> str:
    lines = PIN.read_text(encoding="utf-8").splitlines(keepends=True)
    return hashlib.sha256("".join(lines[start - 1:end]).encode("utf-8")).hexdigest()


def check_span(locator: str, declared: str, prefix: str, errors: list[str]) -> None:
    m = SPAN_RE.match(locator)
    if not m:
        errors.append(f"{prefix}: unpar. locator {locator!r}")
        return
    real = span_hash(int(m.group(1)), int(m.group(2)))
    if real != declared:
        errors.append(f"{prefix}: span {locator} hash mismatch (declared {declared[:12]}.. real {real[:12]}..)")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "env_cards_v0_1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    cards = doc["cards"]
    errors: list[str] = []
    required = ["constraint_id", "role", "source_type", "breach_kind", "reason_code",
                "spans", "predicate", "boundary_operator", "missing_value_policy",
                "fail_closed", "guard_supported", "rescue_denominator_eligible"]

    reason_owner: dict[str, str] = {}
    seen_ids: set[str] = set()
    for c in cards:
        cid = c.get("constraint_id", "<missing>")
        if cid in seen_ids:
            errors.append(f"{cid}: duplicate constraint_id (census must be a deduplicated set)")
        else:
            seen_ids.add(cid)
        for k in required:
            if k not in c:
                errors.append(f"{cid}: missing field {k}")
        if any(k not in c for k in required):
            continue

        for span in c["spans"]:
            check_span(span["locator"], span["sha256_utf8"], cid, errors)
        ca = c.get("coverage_asymmetry")
        if ca and "locator" in ca:
            check_span(ca["locator"], ca["sha256_utf8"], f"{cid}/coverage", errors)

        # reason-code 1:1 among substantive cards
        if c["role"] == "authorization_constraint":
            key = f"{c['breach_kind']}/{c['reason_code']}"
            if key in reason_owner:
                errors.append(f"{cid}: reason code {key} already owned by {reason_owner[key]} (merged rule units)")
            else:
                reason_owner[key] = cid

        # denominator/coverage consistency
        expect = bool(c["guard_supported"] and c["role"] == "authorization_constraint")
        if bool(c["rescue_denominator_eligible"]) != expect:
            errors.append(f"{cid}: denominator eligibility {c['rescue_denominator_eligible']} != expected {expect}")

    # dedup cross-check: schema-doc exemplar EXCLUDE-01 span == census EXCLUDE-01 span
    census_excl = next((c for c in cards if c["constraint_id"] == "ENV-EXCLUDE-01"), None)
    if census_excl and SCHEMA_DOC.exists():
        m = SPAN_RE.match(census_excl["spans"][0]["locator"])
        census_range = (m.group(1), m.group(2)) if m else None
        doc_txt = SCHEMA_DOC.read_text(encoding="utf-8")
        dm = re.search(r"enforcement\.py:(\d+)-(\d+)\s*\(check_mandate clause 1\)", doc_txt)
        doc_range = (dm.group(1), dm.group(2)) if dm else None
        if doc_range is None:
            errors.append("dedup: could not locate ENV-EXCLUDE-01 span in schema doc exemplar")
        elif doc_range != census_range:
            errors.append(f"dedup: schema-doc EXCLUDE span {doc_range} != census span {census_range} (divergent duplicate)")

    if errors:
        print("VALIDATION FAILED")
        for e in errors:
            print(f"- {e}")
        return 1

    subst = [c for c in cards if c["role"] == "authorization_constraint"]
    print(f"VALIDATION PASSED: {len(cards)} cards ({len(subst)} authorization + "
          f"{len(cards) - len(subst)} precondition)")
    print(f"distinct guard reason codes covered: {len(reason_owner)}")
    for c in cards:
        elig = "denom" if c["rescue_denominator_eligible"] else "excl "
        print(f"- {c['constraint_id']:26s} [{elig}] {c['breach_kind']}/{c['reason_code']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
