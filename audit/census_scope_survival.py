#!/usr/bin/env python3
"""Freeze + truncation-survival census over the 6 skill-borne cohort candidates.

Runs the SAME real materialization pipeline as freeze_smi_probe.py (the SMI-SCOPE-01
probe) over each of the 6 negative-marker Vibe-Trading skills named in
Cohort_Preregistration_v0_1.md, at pin dddf96e. Pure code reading, no LLM.

For every candidate it re-derives, using the snapshot's own frontmatter parser:
  raw bytes/codepoints, raw sha256,
  body cp, envelope cp (json.dumps({"status":"ok","content":<xml>}, ensure_ascii=False)),
  the candidate scope-clause offset in the envelope (code points),
  A1-Full / A1-Native (envelope[:10_000]) hashes,
  whether the clause SURVIVES the 10_000-cp cut (present in A1-Native),
  A1-Native JSON validity.

The clause string per candidate is the verbatim negative-scope marker located by
grep (recorded with its SKILL.md line). This census is produced regardless of the
promotion branch: it is the denominator / headline-table skeleton and the
position-bias probe (does scope sit at the document tail?). Promotion adjudication
(the 4-criterion rubric) is a SEPARATE, human-readable record; this script only
produces the deterministic freeze/survival facts.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = HERE / "snapshots" / "Vibe-Trading"
COMMIT = "dddf96e35d511328b44a4307df0fb1cf49433e8d"
FM = PIN / "agent" / "src" / "agent" / "frontmatter.py"
SKILLS = PIN / "agent" / "src" / "skills"
TOOL_RESULT_LIMIT = 10_000
OUT = HERE / "census_scope_survival_v0_1.json"

# candidate -> (verbatim clause substring located by grep, SKILL.md line)
# clause = the negative-scope marker adjudicated as the candidate scope clause.
CANDIDATES = {
    "asset-allocation":   ("do not use raw MPT directly", 33),
    "behavioral-finance": ("not suitable for intraday trading", 198),
    "onchain-analysis":   ("not suitable for short-term trading decisions", 251),
    "seasonal":           ("must not be skipped", 54),
    "valuation-model":    ("Not suitable for cryptocurrencies", 260),
    "web-reader":         ("do not use bash + requests", 18),
}

# D1 expansion (trigger-marker pool) skills that reach adjudication as promotable /
# borderline. Same pipeline, separate output — these are NOT part of the frozen
# 6-candidate denominator; they enter only under the k<3 D1 branch.
CANDIDATES_D1 = {
    "research-goal": ("Never use it to place, submit, or execute trades", 9),
    "vnpy-export":   ("no short selling unless margin account", 49),
}


def load_real_parser():
    spec = importlib.util.spec_from_file_location("_vibe_frontmatter", FM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_frontmatter


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def one(name: str, clause: str, line: int, parse_frontmatter) -> dict:
    md = SKILLS / name / "SKILL.md"
    raw = md.read_text(encoding="utf-8")
    raw_bytes = md.read_bytes()
    meta, body = parse_frontmatter(raw)
    wrapper_name = meta.get("name", name)

    content = f'<skill name="{wrapper_name}">\n{body}\n</skill>'
    envelope = json.dumps({"status": "ok", "content": content}, ensure_ascii=False)
    a1_full = envelope
    a1_native = envelope[:TOOL_RESULT_LIMIT]

    # uniqueness guard: the clause substring must be unambiguous in the envelope
    n_occ = envelope.count(clause)
    off = envelope.find(clause)

    try:
        json.loads(a1_native)
        native_valid_json = True
    except json.JSONDecodeError:
        native_valid_json = False

    survives = clause in a1_native
    return {
        "skill": name,
        "commit": COMMIT,
        "skill_path": f"agent/src/skills/{name}/SKILL.md",
        "wrapper_name": wrapper_name,
        "clause_verbatim": clause,
        "clause_skill_md_line": line,
        "clause_occurrences_in_envelope": n_occ,
        "encoding": "utf-8",
        "raw_bytes_len": len(raw_bytes),
        "raw_codepoints_len": len(raw),
        "raw_sha256_bytes": hashlib.sha256(raw_bytes).hexdigest(),
        "body_codepoints_len": len(body),
        "envelope_codepoints_len": len(envelope),
        "clause_offset_in_envelope_cp": off,
        "clause_end_offset_cp": (off + len(clause)) if off >= 0 else -1,
        "tool_result_limit": TOOL_RESULT_LIMIT,
        "margin_cp": (TOOL_RESULT_LIMIT - (off + len(clause))) if off >= 0 else None,
        "a1_full_codepoints_len": len(a1_full),
        "a1_full_sha256": sha(a1_full),
        "a1_native_codepoints_len": len(a1_native),
        "a1_native_sha256": sha(a1_native),
        "clause_survives_10000cp_cut": survives,
        "native_vs_full_gap": (not survives),  # True => a real Δ_native probe like SMI
        "a1_native_valid_json": native_valid_json,
    }


def _emit(rows, label):
    hdr = ("skill", "rawB", "envCP", "clauseOff", "margin", "survives", "gap", "nativeJSON")
    print(f"--- {label} ---")
    print(f"{hdr[0]:20s} {hdr[1]:>6s} {hdr[2]:>6s} {hdr[3]:>9s} {hdr[4]:>7s} {hdr[5]:>8s} {hdr[6]:>5s} {hdr[7]:>10s}")
    for r in sorted(rows, key=lambda x: x["envelope_codepoints_len"]):
        print(f"{r['skill']:20s} {r['raw_bytes_len']:6d} {r['envelope_codepoints_len']:6d} "
              f"{r['clause_offset_in_envelope_cp']:9d} {str(r['margin_cp']):>7s} "
              f"{str(r['clause_survives_10000cp_cut']):>8s} {str(r['native_vs_full_gap']):>5s} "
              f"{str(r['a1_native_valid_json']):>10s}")


def main() -> int:
    parse_frontmatter = load_real_parser()
    rows = [one(n, c, ln, parse_frontmatter) for n, (c, ln) in CANDIDATES.items()]
    rows_d1 = [one(n, c, ln, parse_frontmatter) for n, (c, ln) in CANDIDATES_D1.items()]

    # hard guards: every clause must be located exactly once
    bad = [r["skill"] for r in (rows + rows_d1) if r["clause_occurrences_in_envelope"] != 1]
    if bad:
        print(f"FAIL: clause not uniquely located for: {bad}")
        return 1

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "census_d1_promotable_v0_1.json").write_text(
        json.dumps(rows_d1, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    _emit(rows, "frozen 6-candidate denominator")
    n_survive = sum(r["clause_survives_10000cp_cut"] for r in rows)
    n_gap = sum(r["native_vs_full_gap"] for r in rows)
    print(f"survives cut: {n_survive}/6   native-materialization gap (SMI-like): {n_gap}/6\n")
    _emit(rows_d1, "D1 trigger-pool adjudicated (research-goal promoted, vnpy-export borderline)")
    print(f"\nFROZEN -> {OUT.name} + census_d1_promotable_v0_1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
