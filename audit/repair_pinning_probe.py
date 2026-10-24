#!/usr/bin/env python3
"""Repair-1 probe: does a one-line AUTHORING change restore deterministic
survival of SMI-SCOPE-01 through the real materialization pipeline?

Intervention (constructed, clearly ours — NOT upstream behavior): duplicate the
skill's terminal authoritative scope clause to the first line of the body
("position pinning"). The pinned snapshot on disk is NEVER modified; the
repaired variant is built in memory from the frozen raw bytes.

Everything else — parser, wrapper, serializer, [:10000] cp slice — is the
REAL pinned pipeline, identical to freeze_smi_probe.py. No LLM, no network.

Outputs: repair_pinning_probe_v0_1.json with both arms' hashes and the
scope_in_a1_native flip (baseline False -> repaired True), cross-locked
against smi_probe_frozen_v0_1.json.
"""
from __future__ import annotations
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
FROZEN_PROBE = HERE / "smi_probe_frozen_v0_1.json"
OUT = HERE / "repair_pinning_probe_v0_1.json"
TOOL_RESULT_LIMIT = 10_000
SCOPE = "not for direct live-trading signals"
SCOPE_LINE = ("*Scope: quantitative research / factor mining "
              "(not for direct live-trading signals)*")


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def materialize(body: str) -> tuple[str, str]:
    """Real pipeline steps downstream of frontmatter parse."""
    content = f'<skill name="{SKILL_NAME}">\n{body}\n</skill>'
    envelope = json.dumps({"status": "ok", "content": content}, ensure_ascii=False)
    return envelope, envelope[:TOOL_RESULT_LIMIT]


def main() -> int:
    frozen = json.loads(FROZEN_PROBE.read_text())
    spec = importlib.util.spec_from_file_location("_vibe_frontmatter", FM)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    raw = SKILL_MD.read_text(encoding="utf-8")
    raw_sha = hashlib.sha256(SKILL_MD.read_bytes()).hexdigest()
    assert raw_sha == frozen["raw_sha256_bytes"], "pinned SKILL.md drifted"

    # ---- Baseline arm (unmodified, must reproduce frozen probe) ----
    meta, body = mod.parse_frontmatter(raw)
    base_full, base_native = materialize(body)
    assert sha(base_full) == frozen["a1_full_sha256"], "baseline full-arm drift"
    assert sha(base_native) == frozen["a1_native_sha256"], "baseline native-arm drift"
    base_native_has_scope = SCOPE in base_native
    assert base_native_has_scope is False, "baseline native arm unexpectedly has scope"

    # ---- Repaired arm (one-line authoring change, in memory only) ----
    repaired_body = SCOPE_LINE + "\n\n" + body
    rep_full, rep_native = materialize(repaired_body)
    rep_native_has_scope = SCOPE in rep_native
    rep_offset = rep_full.find(SCOPE)

    out = {
        "probe_id": "REPAIR-1-PINNING-v0.1",
        "role": ("constructed authoring-level mitigation probe; deterministic; "
                 "pinned snapshot bytes untouched (variant built in memory)"),
        "commit": COMMIT,
        "skill": SKILL_NAME,
        "intervention": ("duplicate terminal authoritative scope line to first "
                         "line of body (position pinning); one authoring line"),
        "pipeline": "identical to smi_probe_frozen_v0_1 (real parser/wrapper/serializer/slice)",
        "cross_lock": {
            "raw_sha256_bytes": raw_sha,
            "baseline_a1_full_sha256": sha(base_full),
            "baseline_a1_native_sha256": sha(base_native),
            "matches_frozen_probe": True,
        },
        "baseline": {
            "scope_in_a1_native": base_native_has_scope,
            "scope_offset_in_envelope_cp": frozen["scope_offset_in_envelope_cp"],
            "envelope_cp": len(base_full),
        },
        "repaired": {
            "scope_in_a1_native": rep_native_has_scope,
            "scope_offset_in_envelope_cp": rep_offset,
            "envelope_cp": len(rep_full),
            "a1_full_sha256": sha(rep_full),
            "a1_native_sha256": sha(rep_native),
        },
        "flip": {"scope_in_a1_native": [base_native_has_scope, rep_native_has_scope]},
        "honesty": ("This certifies AVAILABILITY repair only (delivery through "
                    "materialization). It makes no claim about behavioral "
                    "compliance (efficacy) and no claim about the guard layer, "
                    "whose representational blindness is position-independent."),
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"baseline scope_in_a1_native: {base_native_has_scope}")
    print(f"repaired scope_in_a1_native: {rep_native_has_scope}")
    print(f"repaired scope offset (cp): {rep_offset} (< {TOOL_RESULT_LIMIT})")
    print(f"arm hashes separate: {sha(base_native) != sha(rep_native)}")
    print(f"written: {OUT.name}")
    ok = (not base_native_has_scope) and rep_native_has_scope and rep_offset < TOOL_RESULT_LIMIT
    print("REPAIR-1 VERDICT:", "PASS (deterministic survival restored)" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
