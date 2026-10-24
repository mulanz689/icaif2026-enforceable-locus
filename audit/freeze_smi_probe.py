#!/usr/bin/env python3
"""Byte-exact freeze of the SMI-SCOPE-01 native-materialization probe (no LLM).

Reproduces the REAL materialization pipeline for load_skill('social-media-
intelligence') against pin dddf96e, using the snapshot's own frontmatter parser:

  RAW SKILL.md
    -> parse_frontmatter -> body (frontmatter stripped, .strip())            [skills.py]
    -> get_content: '<skill name="{n}">\\n{body}\\n</skill>'                   [skills.py:172]
    -> load_skill.execute: json.dumps({"status":"ok","content":..},
                                       ensure_ascii=False)                     [load_skill_tool.py:45-48]
    -> loop.py: result[:TOOL_RESULT_LIMIT]  (TOOL_RESULT_LIMIT = 10_000)       [loop.py:53,1451]
    -> format_tool_result: {"role":"tool","content": <string>}  (no re-serialize) [context.py:268]

A1-Full     = full envelope (counterfactual full materialization arm)
A1-Native   = envelope[:10_000]  (what the real loader/harness delivers)
Single intervention between the two arms = the [:10_000] slice. Slice is Python
str slicing => Unicode CODE POINTS, applied to the SERIALIZED ENVELOPE (not raw
skill, not bytes, not the outer tool-message wrapper).
"""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = HERE / "snapshots" / "Vibe-Trading"
COMMIT = "dddf96e35d511328b44a4307df0fb1cf49433e8d"
SKILL_NAME = "social-media-intelligence"
SKILL_MD = PIN / "agent" / "src" / "skills" / SKILL_NAME / "SKILL.md"
FM = PIN / "agent" / "src" / "agent" / "frontmatter.py"
FROZEN = HERE / "smi_probe_frozen_v0_1.json"
TOOL_RESULT_LIMIT = 10_000
SCOPE = "not for direct live-trading signals"


def load_real_parser():
    spec = importlib.util.spec_from_file_location("_vibe_frontmatter", FM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_frontmatter


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute() -> dict:
    """Re-derive every frozen value from the pinned skill via the real parser."""
    parse_frontmatter = load_real_parser()
    raw = SKILL_MD.read_text(encoding="utf-8")
    raw_bytes = SKILL_MD.read_bytes()
    meta, body = parse_frontmatter(raw)

    content = f'<skill name="{SKILL_NAME}">\n{body}\n</skill>'
    envelope = json.dumps({"status": "ok", "content": content}, ensure_ascii=False)
    a1_full = envelope
    a1_native = envelope[:TOOL_RESULT_LIMIT]
    off = envelope.find(SCOPE)  # clause offset within the envelope (code points)

    try:
        json.loads(a1_native)
        native_valid_json = True
    except json.JSONDecodeError:
        native_valid_json = False

    return {
        "probe_id": "SMI-SCOPE-01",
        "role": "Delta_native-materialization PRIMARY exemplar",
        "commit": COMMIT,
        "skill_path": f"agent/src/skills/{SKILL_NAME}/SKILL.md",
        "wrapper_name": meta.get("name", SKILL_NAME),
        "scope_clause": SCOPE,
        "encoding": "utf-8",
        "raw_bytes_len": len(raw_bytes),
        "raw_codepoints_len": len(raw),
        "raw_sha256_bytes": hashlib.sha256(raw_bytes).hexdigest(),
        "frontmatter_stripped": bool(meta),
        "meta_keys": list(meta),
        "body_codepoints_len": len(body),
        "get_content_codepoints_len": len(content),
        "envelope_codepoints_len": len(envelope),
        "envelope_serialization": 'json.dumps({"status":"ok","content":<xml>}, ensure_ascii=False)',
        "truncation_site": "agent/src/agent/loop.py:1451  truncated = result[:TOOL_RESULT_LIMIT]",
        "truncation_target": "serialized envelope (tool result string), BEFORE outer tool-message wrapper",
        "slice_semantics": "Python str slicing = Unicode CODE POINTS (not bytes, not the tool wrapper)",
        "tool_result_limit": TOOL_RESULT_LIMIT,
        "scope_offset_in_envelope_cp": off,
        "a1_full_codepoints_len": len(a1_full),
        "a1_full_sha256": sha(a1_full),
        "a1_native_codepoints_len": len(a1_native),
        "a1_native_sha256": sha(a1_native),
        "scope_in_a1_full": SCOPE in a1_full,
        "scope_in_a1_native": SCOPE in a1_native,
        "a1_native_valid_json": native_valid_json,
        "visibility_assertion": (
            "A1-Full materializes the scope clause; A1-Native truncates it "
            f"{off - TOOL_RESULT_LIMIT} codepoints before it is reached. Single "
            "intervention between arms = the [:10000] envelope slice. A1-Native is "
            "delivered as a syntactically INVALID JSON envelope (cut mid-string)."
        ),
    }


def _print(fz: dict) -> None:
    for k, v in fz.items():
        print(f"{k:28s}: {v}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="Re-derive and diff against the frozen JSON; exit 1 on drift.")
    args = ap.parse_args()

    fz = compute()

    if args.verify:
        if not FROZEN.exists():
            print(f"FAIL: {FROZEN.name} not found; run without --verify to freeze first.")
            return 1
        prev = json.loads(FROZEN.read_text(encoding="utf-8"))
        drift = {k: (prev.get(k), fz[k]) for k in fz if prev.get(k) != fz[k]}
        if drift:
            print("VERIFY FAILED: frozen values drifted from pinned source:")
            for k, (a, b) in drift.items():
                print(f"  {k}: frozen={a!r} recomputed={b!r}")
            return 1
        _print(fz)
        print("VERIFY PASSED: recomputed values match frozen artifact @ dddf96e")
        return 0

    FROZEN.write_text(json.dumps(fz, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _print(fz)
    print(f"\nFROZEN -> {FROZEN.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
