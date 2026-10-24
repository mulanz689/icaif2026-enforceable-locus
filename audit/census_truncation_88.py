#!/usr/bin/env python3
"""Deterministic 88-skill truncation + screen census (Table 4 of the paper).

RELEASE-TIME REPRODUCER. Unlike the other files in this directory, this script was
written for the public artifact release, not during the original study. The three
headline census quantities in the paper (33/88 load-truncated; median 16.1% / max
90.3% envelope loss) were computed ad hoc during the original feasibility audit and
no frozen script for them existed. This file re-derives them through exactly the
same materialization pipeline the frozen probes use, and asserts the published
values fail-closed. It introduces no new result.

Pipeline (identical to freeze_smi_probe.py / census_scope_survival.py):

  RAW SKILL.md
    -> parse_frontmatter -> body                                   [agent/frontmatter.py]
    -> '<skill name="{name}">\\n{body}\\n</skill>'                   [agent/skills.py:172]
    -> json.dumps({"status":"ok","content":...}, ensure_ascii=False) [tools/load_skill_tool.py]
    -> envelope[:TOOL_RESULT_LIMIT]   TOOL_RESULT_LIMIT = 10_000    [agent/loop.py:53,1451]

A skill is LOAD-TRUNCATED iff len(envelope) > 10_000 code points. Envelope loss is
measured on the SERIALIZED ENVELOPE, i.e. on the exact object the truncation acts
on: loss = 1 - 10_000 / len(envelope). All lengths are Unicode code points, never
bytes (the slice in loop.py is a Python str slice).

Screens re-run over all 88 skills:
  * negative-scope v1  (the pattern set of record)  -> expected 7/88
  * negative-scope v1 u v2 (adds the disclosed false negative) -> expected 8/88
  * trigger-marker regex as transcribed in the study record -> reports its own count

PROVENANCE NOTE ON THE 13 TRIGGER-MARKED SKILLS. The paper's "Thirteen skills carry
trigger-marked declarations" is a PINNED SCREEN OUTPUT, not a value this script can
re-derive: the 13-name list is carried as a literal input by the frozen reproducer
census_survival_extended.py, and the trigger regex transcribed in the study record
matches only 10 of those 13 at this pin. This script reports both numbers side by
side and asserts neither against the other. No pattern was tuned to recover 13;
doing so would fit the instrument to its own answer. Everything downstream of the
13-list (per-skill span location, the 16-skill union, and the 1/16 past-cut result)
is re-derived deterministically by census_survival_extended.py from the pinned list.

Usage:
  python3 census_truncation_88.py             # census + fail-closed assertions
  python3 census_truncation_88.py --selftest  # tamper fixtures must fire
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PIN = HERE / "snapshots" / "Vibe-Trading"
COMMIT = "dddf96e35d511328b44a4307df0fb1cf49433e8d"
SKILLS = PIN / "agent" / "src" / "skills"
FM = PIN / "agent" / "src" / "agent" / "frontmatter.py"
OUT = HERE / "census_truncation_88_v1_0.json"
TOOL_RESULT_LIMIT = 10_000

# ---- published values this script must reproduce (paper Table 4) -------------
EXPECTED_N_SKILLS = 88
EXPECTED_N_TRUNCATED = 33
EXPECTED_MEDIAN_LOSS_PCT = 16.1
EXPECTED_MAX_LOSS_PCT = 90.3
EXPECTED_NEGATIVE_V1 = [
    "asset-allocation", "behavioral-finance", "onchain-analysis", "seasonal",
    "social-media-intelligence", "valuation-model", "web-reader",
]
EXPECTED_NEGATIVE_V1_OR_V2 = sorted(EXPECTED_NEGATIVE_V1 + ["research-goal"])
ANCHOR = "social-media-intelligence"

# ---- screens of record -------------------------------------------------------
NEG_V1 = (r"do not use|don't use|not (suitable|intended|designed) for|"
          r"when not to|must not|out of scope|skip (this|when)")
NEG_V2_EXTRA = r"never use (it|this) (to|for)|never .{0,20} (place|submit|execute)"
TRIGGER = (r"when to use|use (this|the) skill when|trigger condition|"
           r"trigger when|## trigger")

# Pinned screen output carried by census_survival_extended.py (NOT re-derived here).
PINNED_TRIGGER_13 = [
    "alpha-zoo", "asset-allocation", "backtest-diagnose", "cross-market-strategy",
    "deep-company-series", "dividend-analysis", "qveris", "report-generate",
    "research-goal", "strategy-dev-manager", "thesis-tracker", "vnpy-export",
    "web-reader",
]


def load_real_parser():
    """Load the pinned snapshot's own frontmatter parser (no reimplementation)."""
    spec = importlib.util.spec_from_file_location("_vibe_frontmatter", FM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_frontmatter


def envelope_for(raw: str, dirname: str, parse_frontmatter) -> tuple[str, str]:
    """Return (wrapper_name, serialized envelope) for one SKILL.md body."""
    meta, body = parse_frontmatter(raw)
    name = meta.get("name", dirname)
    content = f'<skill name="{name}">\n{body}\n</skill>'
    return name, json.dumps({"status": "ok", "content": content}, ensure_ascii=False)


def census(skills_dir: Path | None = None) -> dict:
    """Re-derive the full 88-skill census from the pinned snapshot."""
    skills_dir = skills_dir or SKILLS
    parse_frontmatter = load_real_parser()
    rx_v1 = re.compile(NEG_V1, re.I)
    rx_v2 = re.compile(NEG_V2_EXTRA, re.I)
    rx_trig = re.compile(TRIGGER, re.I)

    rows = []
    for d in sorted(p for p in skills_dir.iterdir() if (p / "SKILL.md").is_file()):
        md = d / "SKILL.md"
        raw = md.read_text(encoding="utf-8")
        name, env = envelope_for(raw, d.name, parse_frontmatter)
        env_cp = len(env)
        truncated = env_cp > TOOL_RESULT_LIMIT
        rows.append({
            "skill": d.name,
            "wrapper_name": name,
            "skill_path": f"agent/src/skills/{d.name}/SKILL.md",
            "raw_bytes_len": len(md.read_bytes()),
            "raw_sha256_bytes": hashlib.sha256(md.read_bytes()).hexdigest(),
            "envelope_codepoints_len": env_cp,
            "load_truncated_at_10000cp": truncated,
            "surviving_fraction": (TOOL_RESULT_LIMIT / env_cp) if truncated else 1.0,
            "envelope_loss_pct": round(100.0 * (1 - TOOL_RESULT_LIMIT / env_cp), 4) if truncated else 0.0,
            "negative_scope_v1_hit": bool(rx_v1.search(raw)),
            "negative_scope_v2_extra_hit": bool(rx_v2.search(raw)),
            "trigger_marker_regex_hit": bool(rx_trig.search(raw)),
        })

    trunc = [r for r in rows if r["load_truncated_at_10000cp"]]
    losses = [r["envelope_loss_pct"] for r in trunc]
    neg_v1 = [r["skill"] for r in rows if r["negative_scope_v1_hit"]]
    neg_v12 = [r["skill"] for r in rows
               if r["negative_scope_v1_hit"] or r["negative_scope_v2_extra_hit"]]
    trig_rx = [r["skill"] for r in rows if r["trigger_marker_regex_hit"]]
    anchor = next(r for r in rows if r["skill"] == ANCHOR)

    return {
        "census_id": "CENSUS-TRUNCATION-88-v1.0",
        "role": "release-time reproducer for the paper's Table 4 census quantities",
        "commit": COMMIT,
        "tool_result_limit": TOOL_RESULT_LIMIT,
        "length_unit": "unicode code points (Python str slice semantics)",
        "loss_denominator": "serialized envelope (the object loop.py truncates)",
        "n_skills": len(rows),
        "n_load_truncated": len(trunc),
        "median_envelope_loss_pct": round(statistics.median(losses), 1),
        "max_envelope_loss_pct": round(max(losses), 1),
        "max_loss_skill": max(trunc, key=lambda r: r["envelope_loss_pct"])["skill"],
        "anchor_envelope_codepoints_len": anchor["envelope_codepoints_len"],
        "anchor_surviving_fraction_pct": round(100 * anchor["surviving_fraction"], 1),
        "negative_scope_v1_count": len(neg_v1),
        "negative_scope_v1": neg_v1,
        "negative_scope_v1_or_v2_count": len(neg_v12),
        "negative_scope_v1_or_v2": neg_v12,
        "trigger_regex_of_record_count": len(trig_rx),
        "trigger_regex_of_record": trig_rx,
        "pinned_trigger_13": PINNED_TRIGGER_13,
        "pinned_trigger_13_count": len(PINNED_TRIGGER_13),
        "trigger_13_not_reproducible_by_regex_of_record": sorted(
            set(PINNED_TRIGGER_13) - set(trig_rx)),
        "trigger_provenance_note": (
            "13/88 is a PINNED screen output consumed by census_survival_extended.py, "
            "not a value re-derived here. The trigger regex of record matches "
            f"{len(trig_rx)}/88 at this pin and misses "
            f"{sorted(set(PINNED_TRIGGER_13) - set(trig_rx))}. No pattern was tuned to "
            "recover 13. Everything downstream of the 13-list is re-derived "
            "deterministically from the pinned list by census_survival_extended.py."
        ),
        "screens": {"negative_v1": NEG_V1, "negative_v2_extra": NEG_V2_EXTRA,
                    "trigger": TRIGGER},
        "rows": rows,
    }


def assertions(c: dict) -> list[tuple[str, bool, str]]:
    """Fail-closed checks against the values published in the paper."""
    return [
        ("n_skills == 88", c["n_skills"] == EXPECTED_N_SKILLS,
         f"{c['n_skills']}"),
        ("load-truncated == 33/88", c["n_load_truncated"] == EXPECTED_N_TRUNCATED,
         f"{c['n_load_truncated']}/{c['n_skills']}"),
        ("median envelope loss == 16.1%",
         c["median_envelope_loss_pct"] == EXPECTED_MEDIAN_LOSS_PCT,
         f"{c['median_envelope_loss_pct']}%"),
        ("max envelope loss == 90.3%",
         c["max_envelope_loss_pct"] == EXPECTED_MAX_LOSS_PCT,
         f"{c['max_envelope_loss_pct']}% ({c['max_loss_skill']})"),
        ("negative-scope v1 == 7/88",
         sorted(c["negative_scope_v1"]) == sorted(EXPECTED_NEGATIVE_V1),
         f"{c['negative_scope_v1_count']}: {c['negative_scope_v1']}"),
        ("negative-scope v1|v2 == 8/88 (disclosed false negative)",
         sorted(c["negative_scope_v1_or_v2"]) == EXPECTED_NEGATIVE_V1_OR_V2,
         f"{c['negative_scope_v1_or_v2_count']}: {c['negative_scope_v1_or_v2']}"),
        ("anchor envelope == 42678 cp", c["anchor_envelope_codepoints_len"] == 42678,
         f"{c['anchor_envelope_codepoints_len']}"),
        ("anchor survives < one quarter", c["anchor_surviving_fraction_pct"] < 25.0,
         f"{c['anchor_surviving_fraction_pct']}%"),
    ]


# ------------------------------------------------------------------ selftest
def _mutate(c: dict, which: str) -> dict:
    m = json.loads(json.dumps(c))
    if which == "truncation_count":
        m["n_load_truncated"] = 32
    elif which == "median_loss":
        m["median_envelope_loss_pct"] = 16.2
    elif which == "max_loss":
        m["max_envelope_loss_pct"] = 90.2
    elif which == "skill_count":
        m["n_skills"] = 87
    elif which == "negative_screen_member":
        m["negative_scope_v1"] = [s for s in m["negative_scope_v1"] if s != ANCHOR]
    elif which == "false_negative_dropped":
        m["negative_scope_v1_or_v2"] = sorted(m["negative_scope_v1"])
    elif which == "anchor_envelope":
        m["anchor_envelope_codepoints_len"] = 42679
    elif which == "quarter_claim":
        m["anchor_surviving_fraction_pct"] = 25.1
    else:
        raise ValueError(which)
    return m


def selftest() -> bool:
    c = census()
    results = []

    ok = all(p for _, p, _ in assertions(c))
    results.append(("positive: pinned snapshot satisfies every published value", ok))

    for mut in ("truncation_count", "median_loss", "max_loss", "skill_count",
                "negative_screen_member", "false_negative_dropped",
                "anchor_envelope", "quarter_claim"):
        fired = not all(p for _, p, _ in assertions(_mutate(c, mut)))
        results.append((f"tamper: {mut} must fail the assertion set", fired))

    # A screen that cannot miss proves nothing: the negative v1 pattern set must
    # genuinely exclude the disclosed false negative, not match everything.
    results.append((
        "control: negative v1 really misses research-goal (screen can fail)",
        "research-goal" not in c["negative_scope_v1"]
        and "research-goal" in c["negative_scope_v1_or_v2"],
    ))

    for name, passed in results:
        print(f"  [{'PASS' if passed else 'FAIL'}] {name}")
    npass = sum(1 for _, p in results if p)
    print(f"selftest: {npass}/{len(results)}")
    return npass == len(results)


def main() -> int:
    if "--selftest" in sys.argv:
        return 0 if selftest() else 1

    c = census()
    OUT.write_text(json.dumps(c, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"--- 88-skill truncation census @ {COMMIT[:7]} ---")
    print(f"{'skill':30s} {'envCP':>8s} {'trunc':>6s} {'loss%':>7s} {'neg1':>5s} {'neg2':>5s} {'trig':>5s}")
    for r in c["rows"]:
        print(f"{r['skill']:30s} {r['envelope_codepoints_len']:8d} "
              f"{str(r['load_truncated_at_10000cp']):>6s} "
              f"{r['envelope_loss_pct']:7.1f} "
              f"{str(r['negative_scope_v1_hit']):>5s} "
              f"{str(r['negative_scope_v2_extra_hit']):>5s} "
              f"{str(r['trigger_marker_regex_hit']):>5s}")

    print()
    print(f"skills at pin                 : {c['n_skills']}")
    print(f"load-truncated at 10,000 cp   : {c['n_load_truncated']}/{c['n_skills']}")
    print(f"median / max envelope loss    : {c['median_envelope_loss_pct']}% / "
          f"{c['max_envelope_loss_pct']}% ({c['max_loss_skill']})")
    print(f"negative-scope v1             : {c['negative_scope_v1_count']}/{c['n_skills']}")
    print(f"negative-scope v1|v2          : {c['negative_scope_v1_or_v2_count']}/{c['n_skills']}"
          "  (>= 8/88 known count)")
    print(f"trigger regex of record       : {c['trigger_regex_of_record_count']}/{c['n_skills']}")
    print(f"pinned trigger list (input)   : {c['pinned_trigger_13_count']}  "
          f"not matched by regex of record: {c['trigger_13_not_reproducible_by_regex_of_record']}")
    print(f"anchor envelope / surviving    : {c['anchor_envelope_codepoints_len']} cp / "
          f"{c['anchor_surviving_fraction_pct']}%")

    print()
    print("--- fail-closed assertions against published values ---")
    ok = True
    for name, passed, got in assertions(c):
        print(f"  [{'HIT' if passed else 'MISS'}] {name}  (got {got})")
        ok = ok and passed
    print(f"\nWROTE -> {OUT.name}")
    print("CENSUS " + ("PASSED" if ok else "FAILED") + ": published Table 4 values "
          + ("reproduced" if ok else "DRIFTED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
