#!/usr/bin/env python3
"""Deterministic scan of the SURVIVING PREFIX (A1-Native, envelope[:10000]) for
any scope-restrictive statement semantically equivalent to SMI-SCOPE-01.

Purpose (paper §5 locus-uniqueness precondition): the claim "the truncated
clause is the SOLE authoritative scope statement" requires showing the surviving
prefix contains no equivalent restriction. This is a lexical screen over a
frozen deterministic artifact — every hit is listed verbatim and classified by
hand-auditable context lines; absence of restrictive hits is the reportable
result. No LLM, no network.

Protocol (authoritative-span determination, as stated in the paper):
  1. Candidate extraction: case-insensitive lexical screen of the surviving
     prefix with a negative-scope lexicon (below).
  2. Classification: each hit is printed with +/-2 lines of context and
     classified as RESTRICTIVE (limits use of skill output) or
     NON-RESTRICTIVE (capability description, examples, config, etc.).
  3. Verdict: sole-authoritative holds iff zero RESTRICTIVE hits in prefix.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = HERE / "snapshots" / "Vibe-Trading"
COMMIT = "dddf96e35d511328b44a4307df0fb1cf49433e8d"
SKILL_NAME = "social-media-intelligence"
SKILL_MD = PIN / "agent" / "src" / "skills" / SKILL_NAME / "SKILL.md"
FM = PIN / "agent" / "src" / "agent" / "frontmatter.py"
TOOL_RESULT_LIMIT = 10_000
FROZEN_PROBE = HERE / "smi_probe_frozen_v0_1.json"
OUT = HERE / "prefix_scope_scan_v0_1.json"

# Negative-scope lexicon: any construction that could restrict downstream use.
LEXICON = [
    r"\bnot for\b", r"\bnot to be\b", r"\bmust not\b", r"\bdo not\b",
    r"\bdon'?t\b", r"\bnever\b", r"\bno live\b", r"\bprohibit",
    r"\bforbidden\b", r"\bdisallow", r"\bresearch[- ]only\b",
    r"\bonly for\b", r"\bsolely\b", r"\brestrict", r"\bscope\b",
    r"\bshould not\b", r"\bcannot be used\b", r"\bnot intended\b",
    r"\bnot a\b.{0,40}signal", r"\blive[- ]trading\b", r"\bcaution\b",
    r"\bwarning\b", r"\bdisclaimer\b", r"\blimitation",
]


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def main() -> int:
    frozen = json.loads(FROZEN_PROBE.read_text())
    spec = importlib.util.spec_from_file_location("_vibe_frontmatter", FM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    raw = SKILL_MD.read_text(encoding="utf-8")
    meta, body = mod.parse_frontmatter(raw)
    content = f'<skill name="{SKILL_NAME}">\n{body}\n</skill>'
    envelope = json.dumps({"status": "ok", "content": content}, ensure_ascii=False)

    # Cross-lock against the frozen probe before scanning.
    assert sha(envelope) == frozen["a1_full_sha256"], "envelope drifted from frozen probe"
    prefix = envelope[:TOOL_RESULT_LIMIT]
    assert sha(prefix) == frozen["a1_native_sha256"], "prefix drifted from frozen probe"

    lines = prefix.split("\\n")  # envelope is JSON-escaped; split on literal \n
    hits = []
    for pat in LEXICON:
        for m in re.finditer(pat, prefix, re.IGNORECASE):
            start = max(0, m.start() - 120)
            end = min(len(prefix), m.end() + 120)
            hits.append({
                "pattern": pat,
                "match": m.group(0),
                "offset_cp": m.start(),
                "context": prefix[start:end],
            })
    hits.sort(key=lambda h: h["offset_cp"])

    # Also scan frontmatter meta (delivered separately from body in some paths).
    meta_hits = []
    meta_text = json.dumps(meta, ensure_ascii=False)
    for pat in LEXICON:
        for m in re.finditer(pat, meta_text, re.IGNORECASE):
            meta_hits.append({"pattern": pat, "match": m.group(0),
                              "context": meta_text[max(0, m.start()-80):m.end()+80]})

    out = {
        "scan_id": "PREFIX-SCOPE-SCAN-v0.1",
        "commit": COMMIT,
        "skill": SKILL_NAME,
        "target": "A1-Native surviving prefix, envelope[:10000] (cp slice)",
        "prefix_sha256": sha(prefix),
        "cross_locked_against": str(FROZEN_PROBE.name),
        "lexicon": LEXICON,
        "prefix_hits_raw": hits,
        "frontmatter_meta_hits_raw": meta_hits,
        "classification_note": (
            "Every raw hit above is listed verbatim for audit. RESTRICTIVE = "
            "limits downstream use of skill output; NON-RESTRICTIVE otherwise. "
            "Classification recorded below after human read of contexts."
        ),
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"prefix cp len: {len(prefix)}")
    print(f"raw hits in prefix: {len(hits)}")
    for h in hits:
        print(f"  @{h['offset_cp']:>6} [{h['pattern']}] …{h['context'][:160]}…")
        print("  ---")
    print(f"frontmatter meta hits: {len(meta_hits)}")
    for h in meta_hits:
        print(f"  [{h['pattern']}] {h['context']}")
    print(f"written: {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
