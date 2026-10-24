#!/usr/bin/env python3
"""Denominator extension of the truncation-survival census to the 13 trigger-marker
Vibe-Trading skills (deliverable 1).

Widens the position-bias falsification denominator beyond the original 9 examined
clauses. For EACH of the 13 trigger-marker skills we locate its trigger-marker line
verbatim by grepping SKILL.md with the trigger regex (case-insensitive):

    when to use|use (this|the) skill when|trigger condition|trigger when|## trigger

The FIRST matched line (stripped) is that skill's "span". We then run the SAME real
materialization pipeline as census_scope_survival.py (imported `one()` — snapshot's
own frontmatter.py parser -> <skill name=...> XML wrap -> json.dumps envelope ->
envelope[:10000] code-point slice) to compute per skill: raw bytes, raw sha256,
envelope cp, span offset in envelope, margin to cut, survives-cut, native-vs-full
gap, A1-Native JSON validity.

If a span cannot be UNIQUELY located (0 matched lines from the regex, or the span
substring occurs 0 or >1 times in the envelope) it is recorded as such — NOT silently
resolved. Pin = commit dddf96e. No LLM. No existing frozen file is touched; output is
census_survival_extended_v0_1.json (NEW).
"""
from __future__ import annotations
import json
import re
from pathlib import Path

# reuse the real pipeline from the existing reproducer (do NOT rewrite pipeline logic)
import importlib.util as _ilu

HERE = Path(__file__).resolve().parent
_spec = _ilu.spec_from_file_location("census_scope_survival", HERE / "census_scope_survival.py")
_css = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_css)
one = _css.one
load_real_parser = _css.load_real_parser
SKILLS = _css.SKILLS
COMMIT = _css.COMMIT
TOOL_RESULT_LIMIT = _css.TOOL_RESULT_LIMIT

OUT = HERE / "census_survival_extended_v0_1.json"

# task-specified trigger regex, case-insensitive
TRIG = re.compile(r"when to use|use (this|the) skill when|trigger condition|trigger when|## trigger", re.I)

# The full identified 13 trigger-marker skills (given denominator).
THIRTEEN = [
    "alpha-zoo", "asset-allocation", "backtest-diagnose", "cross-market-strategy",
    "deep-company-series", "dividend-analysis", "qveris", "report-generate",
    "research-goal", "strategy-dev-manager", "thesis-tracker", "vnpy-export",
    "web-reader",
]

# The original 6 negative-scope candidates (frozen denominator) + SMI, for the union.
SIX_NEGATIVE = [
    "asset-allocation", "behavioral-finance", "onchain-analysis",
    "seasonal", "valuation-model", "web-reader",
]
SMI = "social-media-intelligence"


def first_trigger_line(name: str):
    """Return (line_no, stripped_line) for the FIRST trigger-regex match, or None."""
    md = SKILLS / name / "SKILL.md"
    text = md.read_text(encoding="utf-8")
    for i, ln in enumerate(text.splitlines(), 1):
        if TRIG.search(ln):
            return i, ln.strip()
    return None


def main() -> int:
    parse_frontmatter = load_real_parser()
    rows = []
    unlocatable = []

    for name in THIRTEEN:
        hit = first_trigger_line(name)
        if hit is None:
            rec = {
                "skill": name,
                "commit": COMMIT,
                "skill_path": f"agent/src/skills/{name}/SKILL.md",
                "span_located": False,
                "reason": "trigger regex matched 0 lines in SKILL.md",
                "trigger_line_no": None,
                "span_verbatim": None,
            }
            rows.append(rec)
            unlocatable.append((name, "0 regex-matched lines"))
            continue

        line_no, span = hit
        r = one(name, span, line_no, parse_frontmatter)
        n_occ = r["clause_occurrences_in_envelope"]
        # rename semantics for clarity in the extended file
        r["span_verbatim"] = span
        r["trigger_line_no"] = line_no
        if n_occ == 1:
            r["span_located"] = True
        elif n_occ == 0 and '"' in span:
            # The span carries literal double-quote(s); json.dumps escapes " -> \" in the
            # envelope, so the RAW span is absent while its JSON-escaped form is present.
            # Re-derive offset/survival against the escaped form (deterministic, no guess).
            escaped = span.replace('"', '\\"')
            env = json.dumps(
                {"status": "ok", "content":
                 f'<skill name="{r["wrapper_name"]}">\n'
                 + parse_frontmatter((SKILLS / name / "SKILL.md").read_text("utf-8"))[1]
                 + "\n</skill>"},
                ensure_ascii=False)
            esc_occ = env.count(escaped)
            esc_off = env.find(escaped)
            r["span_json_escaped"] = True
            r["json_escaped_span"] = escaped
            r["json_escaped_occurrences_in_envelope"] = esc_occ
            if esc_occ == 1:
                r["span_located"] = True
                r["clause_offset_in_envelope_cp"] = esc_off
                r["clause_end_offset_cp"] = esc_off + len(escaped)
                r["margin_cp"] = TOOL_RESULT_LIMIT - (esc_off + len(escaped))
                r["clause_survives_10000cp_cut"] = escaped in env[:TOOL_RESULT_LIMIT]
                r["native_vs_full_gap"] = not r["clause_survives_10000cp_cut"]
            else:
                r["span_located"] = False
                r["reason"] = f"json-escaped span occurs {esc_occ} times (need exactly 1)"
                unlocatable.append((name, f"{esc_occ} escaped-form occurrences"))
        else:
            r["span_located"] = False
            r["reason"] = f"span occurs {n_occ} times in envelope (need exactly 1)"
            unlocatable.append((name, f"{n_occ} envelope occurrences"))
        rows.append(r)

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- table ----
    hdr = ("skill", "rawB", "envCP", "spanOff", "margin", "survives", "gap", "nativeJSON", "located")
    print("--- 13 trigger-marker skills: span survival ---")
    print(f"{hdr[0]:24s} {hdr[1]:>6s} {hdr[2]:>6s} {hdr[3]:>8s} {hdr[4]:>8s} "
          f"{hdr[5]:>8s} {hdr[6]:>5s} {hdr[7]:>10s} {hdr[8]:>8s}")
    for r in rows:
        if not r.get("span_located") and r.get("trigger_line_no") is None:
            print(f"{r['skill']:24s} {'--':>6s} {'--':>6s} {'--':>8s} {'--':>8s} "
                  f"{'--':>8s} {'--':>5s} {'--':>10s} {'NO(no-line)':>8s}")
            continue
        off = r["clause_offset_in_envelope_cp"]
        located = "yes" if r.get("span_located") else f"NO({r['clause_occurrences_in_envelope']}occ)"
        print(f"{r['skill']:24s} {r['raw_bytes_len']:6d} {r['envelope_codepoints_len']:6d} "
              f"{off:8d} {str(r['margin_cp']):>8s} {str(r['clause_survives_10000cp_cut']):>8s} "
              f"{str(r['native_vs_full_gap']):>5s} {str(r['a1_native_valid_json']):>10s} {located:>8s}")

    # ---- past-cut accounting over the full identified union ----
    # A span is "truncated past the cut" iff it was uniquely located AND does not survive.
    located_rows = [r for r in rows if r.get("span_located")]
    past_cut_13 = [r["skill"] for r in located_rows if not r["clause_survives_10000cp_cut"]]

    # Full identified set = 13 trigger union 6 negative union {SMI}, deduped (by skill name).
    union_names = []
    for n in THIRTEEN + SIX_NEGATIVE + [SMI]:
        if n not in union_names:
            union_names.append(n)

    print()
    print("--- past-10000cp-cut accounting ---")
    print(f"13 trigger skills with uniquely-located span: {len(located_rows)}")
    print(f"  of those, truncated past cut: {len(past_cut_13)} -> {past_cut_13}")
    print(f"unlocatable spans (recorded, not resolved): {unlocatable}")

    # SMI + the 6 negatives past-cut status comes from the frozen census; SMI is the
    # sole known Δ_native gap. We report distinct spans past cut across the union.
    # From census_scope_survival_v0_1.json the 6 negatives all survive (gap 0/6); SMI is
    # the sole past-cut clause. We restate the union count here.
    frozen = json.loads((HERE / "census_scope_survival_v0_1.json").read_text(encoding="utf-8"))
    neg_past = [r["skill"] for r in frozen if r["native_vs_full_gap"]]
    print(f"6-negative-candidate spans past cut (from frozen census): {neg_past}")
    print("SMI past cut: yes (sole Delta_native gap per smi_probe_frozen_v0_1.json)")

    # Distinct spans/clauses truncated past cut across full identified union:
    #   trigger-set past cut (this run) + negative-set past cut (frozen) + SMI
    distinct_past = set(past_cut_13) | set(neg_past) | {SMI}
    n_total_examined = len(union_names)
    print()
    print(f"N_past_cut / N_total_examined = {len(distinct_past)} / {n_total_examined}")
    print(f"  distinct spans past cut: {sorted(distinct_past)}")
    print(f"  N_total union skills examined ({n_total_examined}): {union_names}")

    # ---- reconciliation: load-bearing located-span denominator (Cohort_Freeze §3) ----
    # A union skill "has a located span" iff it is trigger-located in this run, OR carries a
    # located clause in the frozen negative census, OR is SMI. The union members with NO
    # locatable span at all (qveris, thesis-tracker: trigger-unlocatable AND not in the
    # negative set) are excluded from the load-bearing denominator; web-reader stays in
    # (it has a located negative-scope clause even though its trigger line is absent).
    negative_names = {r["skill"] for r in frozen}
    located_names = {r["skill"] for r in located_rows} | negative_names | {SMI}
    located_union = [n for n in union_names if n in located_names]
    no_locatable = [n for n in union_names if n not in located_names]
    print()
    print(f"N_past_cut / N_located_span (load-bearing, matches Cohort_Freeze §3) = "
          f"{len(distinct_past)} / {len(located_union)}")
    print(f"  union members with NO locatable span (excluded from load-bearing denom): {no_locatable}")
    print(f"\nWROTE -> {OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
