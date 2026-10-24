#!/usr/bin/env python3
"""Validator for the block-five row schema (DRAFT v0.1.3).

Extends v0.1.2 with TWO merged owner rulings folded into ONE byte-flip:
  SCHEMA-R4 — a THIRD row_kind 'no-enforcement-point' (AI-Trader / F1-FAIL class:
  the action-time enforcement layer does not exist at all — the second form of the
  enforcement-point vacuum, complementing the SLEEVE 'layer exists but
  representation-blind' form). Its assertions:
    NO-EP-IDENTITY-REQUIRED         constraint identity subfields required (same as delivery-only).
    NO-EP-NO-REPR                   the representation-analysis group is FORBIDDEN
                                    (key appearance, incl. null, rejects — no layer to represent anything).
    NO-EP-VERDICT-EMPTY             structural_verdict MUST be ABSENT — NOT 'unresolved'.
                                    'unresolved' = analysis-deferred (delivery-only);
                                    no-enforcement-point = nothing-to-analyze. Conflation pollutes verdict stats.
    NO-EP-MEDIATION-EVIDENCE-REQUIRED   REQUIRED pointer+hash to the vacuum proof (F1-FAIL verdict),
                                    symmetric to a collision-found row requiring a witness hash.
    CF2-LAYER-ROWKIND-COUPLING-3WAY three-way coupling: constraint-audit ⟺ analyzed_layer non-empty;
                                    (delivery-only ∨ no-enforcement-point) ⟹ analyzed_layer empty;
                                    the two empty-layer kinds are distinguished by their evidence fields
                                    (delivery group vs mediation_evidence), NOT by analyzed_layer.
  Ruling 2 (HERMES fragment delete) is a BATCH-only change (no schema byte); the
  clean analysis-absent delivery-only row still validates under the unchanged
  delivery-only policy.

All v0.1.2 assertions (FIREWALL, GROUNDING-CLASS, ID-LABEL-REQUIRED, CLASS-TEST-
CONSISTENT, DELIVERY-ONLY-*, CF2 coupling, LAYER-B-CONSTRAINT-AUDIT-ONLY) are
carried unchanged. LAYER-B-CONSTRAINT-AUDIT-ONLY now reads 'row_kind != constraint-audit'
so it rejects a Layer-B no-enforcement-point row too.

Zero LLM, zero network, deterministic. Reads the schema from
block_five_schema_v0_1_3.json (single-source; validator does not re-declare fields).

Usage:
  python3 validate_block_five_schema_v0_1_3.py --selftest   # fixtures prove assertions fire
  python3 validate_block_five_schema_v0_1_3.py <rows.json>  # validate a rows array
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA_PATH = os.path.join(HERE, "block_five_schema_v0_1_3.json")


def load_schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


def _present(row, key):
    return key in row and row[key] not in (None, "", [], {})


def _appears(row, key):
    """Key physically present in the object, regardless of value (no fence-sitting)."""
    return key in row


def validate_row(row, schema, idx=0):
    """Return (violations, flags). Violations reject the row; flags are advisory."""
    violations, flags = [], []
    tag = row.get("cell_id", row.get("constraint_id", f"row#{idx}"))

    layer = row.get("layer")
    if layer not in schema["layer_enum"]:
        violations.append(f"[{tag}] layer must be one of {schema['layer_enum']}, got {layer!r}")
        return violations, flags  # cannot proceed without a valid layer

    q_fields = schema["layer_B_estimand_output_fields"]
    b_only = set(schema["layer_B_required_additional_fields"]) | set(q_fields)

    # ---- FIREWALL assertion FW-A-NO-B-FIELDS ----
    if layer == "A":
        smuggled = sorted(k for k in b_only if _present(row, k))
        if smuggled:
            violations.append(
                f"[{tag}] FW-A-NO-B-FIELDS: Layer-A row carries Layer-B field(s) {smuggled} "
                f"— static classification masquerading as quantitative measurement (schema_violation)")

    # ---- row_kind gate ----
    row_kind = row.get("row_kind")
    if row_kind not in schema["row_kind_enum"]:
        violations.append(f"[{tag}] row_kind must be one of {schema['row_kind_enum']}, got {row_kind!r}")
        # without a valid row_kind the required-field policy is undefined; stop here
        return violations, flags

    # ---- LAYER-B-CONSTRAINT-AUDIT-ONLY (v0.1.3: != constraint-audit, covers no-enforcement-point) ----
    if layer == "B" and row_kind != "constraint-audit":
        violations.append(f"[{tag}] LAYER-B-CONSTRAINT-AUDIT-ONLY: Layer-B row must be row_kind='constraint-audit', got {row_kind!r}")

    groups = schema["layer_A_required_field_groups"]
    repr_analysis = schema["representation_analysis_fields"]
    identity = schema["constraint_identity_fields"]

    if layer == "A" and row_kind == "delivery-only":
        pol = schema["row_kind_field_policy"]["delivery-only"]
        # required presence (identity + deployment + delivery + evidence + row_kind + structural_verdict)
        for fld in pol["required"]:
            if not _present(row, fld):
                grp = "identity" if fld in identity else "delivery-only-required"
                violations.append(f"[{tag}] missing required delivery-only field '{fld}' (group: {grp})")
        # DELIVERY-ONLY-STRUCT-UNRESOLVED
        if row.get("structural_verdict") != "unresolved":
            violations.append(
                f"[{tag}] DELIVERY-ONLY-STRUCT-UNRESOLVED: delivery-only row requires "
                f"structural_verdict='unresolved', got {row.get('structural_verdict')!r}")
        # DELIVERY-ONLY-NO-REPR (key appearance, any value)
        appearing = sorted(k for k in repr_analysis if _appears(row, k))
        if appearing:
            violations.append(
                f"[{tag}] DELIVERY-ONLY-NO-REPR: delivery-only row carries representation-analysis "
                f"field(s) {appearing} — permitted-absent ≠ permitted-half-present; promote to a full "
                f"constraint-audit row or delete the fragment")
        # CF2 coupling: analyzed_layer must be empty for delivery-only
        if _present(row, "analyzed_layer"):
            violations.append(
                f"[{tag}] CF2-LAYER-ROWKIND-COUPLING: delivery-only row must have analyzed_layer empty, "
                f"got {row.get('analyzed_layer')!r}")

    elif layer == "A" and row_kind == "no-enforcement-point":
        pol = schema["row_kind_field_policy"]["no-enforcement-point"]
        # required presence (identity + deployment + evidence + row_kind + mediation_evidence)
        for fld in pol["required"]:
            if not _present(row, fld):
                if fld in identity:
                    violations.append(
                        f"[{tag}] NO-EP-IDENTITY-REQUIRED: no-enforcement-point row missing "
                        f"constraint-identity field '{fld}' (identity is what separates a vacuum ROW from noise)")
                elif fld == "mediation_evidence":
                    violations.append(
                        f"[{tag}] NO-EP-MEDIATION-EVIDENCE-REQUIRED: no-enforcement-point row requires "
                        f"mediation_evidence (pointer+hash to the vacuum proof, e.g. the F1-FAIL verdict) — "
                        f"a row asserting 'no layer' without evidence is inadmissible")
                else:
                    violations.append(f"[{tag}] missing required no-enforcement-point field '{fld}' (group: deployment/evidence)")
        # NO-EP-VERDICT-EMPTY: structural_verdict key must NOT appear (any value, incl. 'unresolved')
        if _appears(row, "structural_verdict"):
            violations.append(
                f"[{tag}] NO-EP-VERDICT-EMPTY: no-enforcement-point row must NOT carry structural_verdict "
                f"(nothing-to-analyze must not be encoded as analysis-deferred 'unresolved'), got "
                f"{row.get('structural_verdict')!r}")
        # NO-EP-NO-REPR: any representation-analysis key appears (incl. null) => reject
        appearing = sorted(k for k in repr_analysis if _appears(row, k))
        if appearing:
            violations.append(
                f"[{tag}] NO-EP-NO-REPR: no-enforcement-point row carries representation-analysis "
                f"field(s) {appearing} — no enforcement layer exists to represent anything")
        # CF2 three-way coupling: analyzed_layer must be empty for no-enforcement-point
        if _present(row, "analyzed_layer"):
            violations.append(
                f"[{tag}] CF2-LAYER-ROWKIND-COUPLING-3WAY: no-enforcement-point row must have "
                f"analyzed_layer empty (distinguished from delivery-only by mediation_evidence, not by "
                f"a layer), got {row.get('analyzed_layer')!r}")

    elif layer == "A" and row_kind == "constraint-audit":
        # full required set
        for group, fields in groups.items():
            for fld in fields:
                if not _present(row, fld):
                    violations.append(f"[{tag}] missing required Layer-A field '{fld}' (group: {group})")
        # row_kind + analyzed_layer (CF-2)
        al = row.get("analyzed_layer")
        if not _present(row, "analyzed_layer"):
            violations.append(f"[{tag}] CF2-LAYER-ROWKIND-COUPLING: constraint-audit row requires a non-empty analyzed_layer")
        else:
            cand = row.get("candidate_layers", [])
            if isinstance(cand, list) and al not in cand:
                violations.append(f"[{tag}] CF2-LAYER-ROWKIND-COUPLING: analyzed_layer={al!r} must be a member of candidate_layers {cand}")

    elif layer == "B":
        # constraint-audit full Layer-A required set applies to a Layer-B row too
        for group, fields in groups.items():
            for fld in fields:
                if not _present(row, fld):
                    violations.append(f"[{tag}] missing required Layer-A field '{fld}' (group: {group})")
        al = row.get("analyzed_layer")
        if not _present(row, "analyzed_layer"):
            violations.append(f"[{tag}] CF2-LAYER-ROWKIND-COUPLING: Layer-B (constraint-audit) row requires a non-empty analyzed_layer")
        else:
            cand = row.get("candidate_layers", [])
            if isinstance(cand, list) and al not in cand:
                violations.append(f"[{tag}] CF2-LAYER-ROWKIND-COUPLING: analyzed_layer={al!r} must be a member of candidate_layers {cand}")
        for fld in schema["layer_B_required_additional_fields"]:
            if not _present(row, fld):
                violations.append(f"[{tag}] Layer-B row missing required field '{fld}'")

    # ---- enum constraints ----
    ec = schema["enum_constraints"]
    for fld, allowed in ec.items():
        if fld == "per_variable_visibility_values":
            vis = row.get("per_variable_visibility", {})
            if isinstance(vis, dict):
                for var, val in vis.items():
                    if val not in allowed:
                        violations.append(f"[{tag}] per_variable_visibility[{var}]={val!r} not in {allowed}")
            continue
        if _present(row, fld) and row[fld] not in allowed:
            violations.append(f"[{tag}] {fld}={row[fld]!r} not in {allowed}")

    # ---- ID-LABEL-REQUIRED (R1) ----
    if layer == "B":
        id_enum = schema["identification_label_rule"]
        allowed_labels = set(schema["identification_label_enum"])
        label_key = id_enum["label_key"]
        for qf in q_fields:
            if _present(row, qf):
                out = row[qf]
                extra = {id_enum["q7_extra_value"]} if qf == "Q7_output" else set()
                if not isinstance(out, dict):
                    violations.append(
                        f"[{tag}] ID-LABEL-REQUIRED: {qf} must be an object carrying "
                        f"'{label_key}' label, got {type(out).__name__}")
                elif out.get(label_key) not in (allowed_labels | extra):
                    violations.append(
                        f"[{tag}] ID-LABEL-REQUIRED: {qf}['{label_key}']={out.get(label_key)!r} "
                        f"not in {sorted(allowed_labels | extra)} (§9 line 263: no unlabeled Q output)")

    # ---- grounding class (optional for delivery-only / no-enforcement-point, required for constraint-audit) ----
    gc = row.get("grounding_class")
    if gc is not None and gc not in schema["grounding_class_enum"]:
        violations.append(f"[{tag}] grounding_class={gc!r} not in {schema['grounding_class_enum']}")
    conf = row.get("grounding_confidence")
    if conf is not None and conf not in schema["confidence_enum"]:
        violations.append(f"[{tag}] grounding_confidence={conf!r} not in {schema['confidence_enum']}")
    if gc == "other" and not _present(row, "grounding_evidence_span"):
        violations.append(f"[{tag}] grounding_class='other' requires grounding_evidence_span (free-text reason)")

    # ---- CLASS-TEST-CONSISTENT (R2) ----
    ctm = schema["grounding_class_rubric"]["class_matched_test_map"]
    mt = row.get("grounding_matched_test")
    if gc in ctm and mt is not None and mt != ctm[gc]:
        violations.append(
            f"[{tag}] CLASS-TEST-CONSISTENT: grounding_class={gc!r} implies matched_test={ctm[gc]} "
            f"(first-match-wins ordering), got {mt!r}")

    # arbitration flag (soft)
    if gc == "other" or conf == "low":
        flags.append(f"[{tag}] arbitration: grounding_class={gc!r}/confidence={conf!r} -> route to Annotation_Agreement §10")

    return violations, flags


def validate_rows(rows, schema):
    all_v, all_f = [], []
    for i, row in enumerate(rows):
        v, f = validate_row(row, schema, i)
        all_v += v
        all_f += f
    return all_v, all_f


# ---------------------------------------------------------------- selftest
def _valid_layer_a():
    return {
        "cell_id": "SMI-SCOPE-01@guard", "row_kind": "constraint-audit", "analyzed_layer": "guard",
        "constraint_id": "SMI-SCOPE-01", "layer": "A",
        "verbatim_text": "Scope: quantitative research / factor mining (not for direct live-trading signals)",
        "repo_file_line": "agent/src/skills/social-media-intelligence/SKILL.md:1295",
        "version_hash": "dddf96e", "applicability": "SMI output produced/referenced",
        "oracle_sketch": "live order justified solely by SMI output => violation",
        "grounding_class": "provenance", "grounding_matched_test": 1,
        "grounding_evidence_span": "SKILL.md:1295 'not for direct live-trading signals'",
        "grounding_confidence": "high",
        "harness_id": "AI-Trader", "commit": "dddf96e", "loader_assembler_config": "native/full",
        "action_schema": "submit_order(OrderIntent)", "candidate_layers": ["model", "guard"],
        "complete_mediation_status": "mediated",
        "delivery_present": True, "delivery_sound": True, "delivery_correctly_bound": False,
        "delivery_failure_family": "misbinding",
        "pi_L_field_list": ["mandate", "intent", "positions"], "pi_L_canonical_bytes": "…",
        "oracle_required_variables": ["signal_provenance"],
        "per_variable_visibility": {"signal_provenance": "missing"},
        "witness_pair_status": "constructed", "witness_artifact_hash": "7872a8dd…",
        "structural_verdict": "collision-found",
        "evidence_method": "static-inspection", "reviewer": "research-side reviewer",
        "validation_status": "draft", "code_seed_env_hashes": "n/a",
        "correction_log_pointer": "Standing_Correction_Log.md",
    }


def _valid_layer_b():
    r = _valid_layer_a()
    r["cell_id"] = "SMI-SCOPE-01-B@guard"
    r["constraint_id"] = "SMI-SCOPE-01-B"; r["layer"] = "B"
    r["evidence_method"] = "exact-census"
    r.update({
        "mu_definition": "mu_design (SLEEVE 2-point cell)", "sampling_unit": "episode",
        "P_Y1": 0.5, "exclusion_table": {"unresolved": 0},
        "fiber_census_or_hash": {"Z*": {"n0": 1, "n1": 1}},
        "guard_replay_linkage": ["SLEEVE-BREACH-CONSTRUCTED-01"],
        "Q3_output": {"Rhat": 0.5, "identification": "exact-census"},
        "Q5_output": {"capacity": 0.0, "identification": "exact-census"},
        "Q7_output": {"algorithmic_gap": 0.0, "identification": "degenerate"},
    })
    return r


def _valid_delivery_only():
    """A conforming delivery-only row (hermes shape, CLEAN analysis-absent per ruling 2):
    identity + delivery + deployment + evidence + structural_verdict='unresolved' + row_kind,
    NO representation-analysis field, NO grounding fragment, analyzed_layer empty."""
    return {
        "cell_id": "HERMES-TRUNC-46823@delivery", "row_kind": "delivery-only",
        "constraint_id": "HERMES-TRUNC-46823", "layer": "A",
        "verbatim_text": "(external delivery event) skills authoring standards silently truncated mid-file",
        "repo_file_line": "hermes-agent issue #46823 (external)",
        "version_hash": "external-issue-46823",
        "harness_id": "hermes-agent", "commit": "external-issue-46823",
        "loader_assembler_config": "external harness; silent mid-file truncation 69200->18099 chars",
        "action_schema": "n/a (external; delivery-side evidence only)",
        "candidate_layers": ["model"], "complete_mediation_status": "unmediated",
        "delivery_present": True, "delivery_sound": False, "delivery_correctly_bound": False,
        "delivery_failure_family": "omission",
        "structural_verdict": "unresolved",
        "evidence_method": "static-inspection", "reviewer": "research-side reviewer",
        "validation_status": "DRAFT-prefreeze", "code_seed_env_hashes": "external citation, verified 2026-07-29",
        "correction_log_pointer": "Standing_Correction_Log.md",
    }


def _valid_no_ep():
    """A conforming no-enforcement-point row (AI-Trader shape, SCHEMA-R4): identity +
    deployment + evidence + row_kind + mediation_evidence; NO representation-analysis
    field, NO structural_verdict, analyzed_layer empty. Delivery group + grounding
    permitted-absent (the finding is the vacuum, carried by mediation_evidence)."""
    return {
        "cell_id": "AITRADER-SCOPE-FIDELITY@no-enforcement-point", "row_kind": "no-enforcement-point",
        "constraint_id": "AITRADER-SCOPE-FIDELITY", "layer": "A",
        "verbatim_text": "(no pinned action-time scope clause: AI-Trader has no enforcement surface to attach one to)",
        "repo_file_line": "AI-Trader config.py (limit/notional/exclude/leverage/cap grep EMPTY); services.py:190-330 (format/position consistency only)",
        "version_hash": "d03ff6c",
        "harness_id": "AI-Trader", "commit": "d03ff6c056b32ced735adf7c19ed8175adb1c8df",
        "loader_assembler_config": "external agent; sole LLM call = cosmetic dashboard NLG (market_intel.py:611-614); no in-repo agentic skill loop; trade surface = REST",
        "action_schema": "REST (routes_agent/routes_trading); position mutation services.py::_update_position_from_signal",
        "candidate_layers": ["model"], "complete_mediation_status": "unmediated",
        "evidence_method": "static-inspection", "reviewer": "research-side reviewer",
        "validation_status": "DRAFT-prefreeze",
        "code_seed_env_hashes": "ai_trader_fcheck_verdicts_v0_1.json sha256 799c1a326ac498c13a52591091520b369f8bd394ec4c96c88758f8a7f7cc2882",
        "correction_log_pointer": "Standing_Correction_Log.md",
        "mediation_evidence": "ai_trader_fcheck_verdicts_v0_1.json sha256 799c1a326ac498c13a52591091520b369f8bd394ec4c96c88758f8a7f7cc2882 :: verdicts.F1_shadow_guard_replay.verdict = FAIL_REPLICATION_ARM ('No ACTION-TIME authorization/scope guard exists on this arm to shadow')",
    }


def _provenance_24h_row():
    r = _valid_layer_a()
    r["constraint_id"] = "SMI-FRESHNESS-24H"
    r["verbatim_text"] = "signals older than 24h may not drive orders"
    r["oracle_sketch"] = "order whose driving signal has age > 24h => violation (needs lineage)"
    r["grounding_class"] = "provenance"; r["grounding_matched_test"] = 1
    r["grounding_evidence_span"] = "'signals older than 24h may not drive orders' — lineage restriction, source time-qualified"
    r["oracle_required_variables"] = ["signal_provenance", "signal_age"]
    r["per_variable_visibility"] = {"signal_provenance": "missing", "signal_age": "missing"}
    return r


def selftest():
    schema = load_schema()
    results = []

    def expect(name, rows, should_pass):
        v, f = validate_rows(rows, schema)
        ok = (len(v) == 0) == should_pass
        results.append((name, ok, v))

    # 1. valid Layer-A row -> passes
    expect("valid Layer-A passes", [_valid_layer_a()], True)
    # 2. valid Layer-B row -> passes
    expect("valid Layer-B passes", [_valid_layer_b()], True)
    # 3. FIREWALL: Layer-A row carrying a Q output -> REJECTED
    a_smuggle = _valid_layer_a(); a_smuggle["Q3_output"] = {"Rhat": 0.5, "identification": "exact-census"}
    expect("FIREWALL rejects Layer-A with Q3_output", [a_smuggle], False)
    # 3b. FIREWALL: Layer-A row carrying a Layer-B required field -> REJECTED
    a_mu = _valid_layer_a(); a_mu["mu_definition"] = "mu_design"
    expect("FIREWALL rejects Layer-A with mu_definition", [a_mu], False)
    # 4. invalid grounding_class -> REJECTED
    bad_gc = _valid_layer_a(); bad_gc["grounding_class"] = "vibes"
    expect("rejects invalid grounding_class", [bad_gc], False)
    # 5. missing required field -> REJECTED
    miss = _valid_layer_a(); del miss["oracle_sketch"]
    expect("rejects missing required field", [miss], False)
    # 6. invalid enum value -> REJECTED
    bad_enum = _valid_layer_a(); bad_enum["structural_verdict"] = "maybe"
    expect("rejects invalid structural_verdict enum", [bad_enum], False)
    # 7. grounding_class 'other' with reason -> passes but raises arbitration flag
    other = _valid_layer_a(); other["grounding_class"] = "other"; other["grounding_matched_test"] = 5
    other["grounding_evidence_span"] = "compound boundary, see note"
    v7, f7 = validate_rows([other], schema)
    results.append(("'other' passes with reason + raises arbitration flag", len(v7) == 0 and len(f7) == 1, v7))
    # 8. Layer-B row missing a required B field -> REJECTED
    b_miss = _valid_layer_b(); del b_miss["fiber_census_or_hash"]
    expect("rejects Layer-B missing fiber_census", [b_miss], False)

    # ---- v0.1.1 fixtures (R1/R2) ----
    # 9 (R1). Layer-B Q output missing its identification label -> REJECTED
    b_nolabel = _valid_layer_b(); b_nolabel["Q5_output"] = {"capacity": 0.0}
    expect("R1: REJECTS Layer-B Q output missing identification label", [b_nolabel], False)
    # 9b (R1 negative control). out-of-enum id -> REJECTED
    b_badlabel = _valid_layer_b(); b_badlabel["Q3_output"] = {"Rhat": 0.5, "identification": "eyeballed"}
    expect("R1: REJECTS Q output with out-of-enum identification label", [b_badlabel], False)
    # 10 (R2). 24h compound-provenance -> provenance/test-1 validates + rubric text fixed
    v10, _ = validate_rows([_provenance_24h_row()], schema)
    t1 = schema["grounding_class_rubric"]["ordered_tests"][0]["decision_question"]
    text_fixed = ("time- or attribute-qualified" in t1) and ("with NO reference to the actor's goal" in t1)
    ok10 = (len(v10) == 0) and text_fixed
    detail10 = v10 if v10 else ([] if text_fixed else ["rubric test-1 text missing R2 allowance"])
    results.append(("R2: 24h compound-provenance -> provenance/test-1 validates + rubric text fixed", ok10, detail10))
    # 10b (R2 negative control). provenance with wrong matched_test -> REJECTED
    bad_mt = _provenance_24h_row(); bad_mt["grounding_matched_test"] = 3
    expect("R2: rejects class/matched_test mismatch (provenance declared as test 3)", [bad_mt], False)

    # ---- v0.1.2 fixtures (SCHEMA-R3=B / CF-2), carried unchanged ----
    # 11. valid delivery-only row -> passes
    expect("R3-B: valid (clean) delivery-only row passes", [_valid_delivery_only()], True)
    # 12 (DELIVERY-ONLY-NO-REPR). delivery-only carrying a representation-analysis field -> REJECTED
    do_repr = _valid_delivery_only(); do_repr["per_variable_visibility"] = {"x": "missing"}
    expect("R3-B: REJECTS delivery-only carrying a representation-analysis field", [do_repr], False)
    # 12b (DELIVERY-ONLY-NO-REPR, key-appearance even if null). null-valued repr key -> REJECTED
    do_reprnull = _valid_delivery_only(); do_reprnull["pi_L_canonical_bytes"] = None
    expect("R3-B: REJECTS delivery-only with a null-valued representation key (no fence-sitting)", [do_reprnull], False)
    # 13 (DELIVERY-ONLY-IDENTITY-REQUIRED). missing identity subfield -> REJECTED
    do_noident = _valid_delivery_only(); del do_noident["verbatim_text"]
    expect("R3-B: REJECTS delivery-only missing a constraint-identity subfield", [do_noident], False)
    # 14 (DELIVERY-ONLY-STRUCT-UNRESOLVED). structural_verdict != unresolved -> REJECTED
    do_struct = _valid_delivery_only(); do_struct["structural_verdict"] = "collision-found"
    expect("R3-B: REJECTS delivery-only with structural_verdict != 'unresolved'", [do_struct], False)
    # 15 (CF2). delivery-only with a non-empty analyzed_layer -> REJECTED
    do_layer = _valid_delivery_only(); do_layer["analyzed_layer"] = "guard"
    expect("CF2: REJECTS delivery-only with a non-empty analyzed_layer", [do_layer], False)
    # 16 (CF2). constraint-audit with an empty analyzed_layer -> REJECTED
    ca_nolayer = _valid_layer_a(); ca_nolayer["analyzed_layer"] = ""
    expect("CF2: REJECTS constraint-audit with an empty analyzed_layer", [ca_nolayer], False)
    # 16b (CF2). analyzed_layer not in candidate_layers -> REJECTED
    ca_badlayer = _valid_layer_a(); ca_badlayer["candidate_layers"] = ["model"]; ca_badlayer["analyzed_layer"] = "guard"
    expect("CF2: REJECTS analyzed_layer not in candidate_layers", [ca_badlayer], False)
    # 17. invalid row_kind -> REJECTED (no-guard-observation is still NOT in the 3-kind enum)
    bad_rk = _valid_layer_a(); bad_rk["row_kind"] = "no-guard-observation"
    expect("rejects invalid row_kind enum", [bad_rk], False)
    # 18 (LAYER-B-CONSTRAINT-AUDIT-ONLY). Layer-B row marked delivery-only -> REJECTED
    b_do = _valid_layer_b(); b_do["row_kind"] = "delivery-only"
    expect("LAYER-B-CONSTRAINT-AUDIT-ONLY: rejects Layer-B delivery-only row", [b_do], False)

    # ---- v0.1.3 new fixtures (SCHEMA-R4 no-enforcement-point), each new assertion gets a failure fixture ----
    # 19. valid no-enforcement-point row -> passes
    expect("R4: valid no-enforcement-point row passes", [_valid_no_ep()], True)
    # 20 (NO-EP-MEDIATION-EVIDENCE-REQUIRED). missing mediation_evidence -> REJECTED
    ne_nomed = _valid_no_ep(); del ne_nomed["mediation_evidence"]
    expect("R4: REJECTS no-enforcement-point missing mediation_evidence", [ne_nomed], False)
    # 20b (NO-EP-MEDIATION-EVIDENCE-REQUIRED, empty value). empty mediation_evidence -> REJECTED
    ne_medempty = _valid_no_ep(); ne_medempty["mediation_evidence"] = ""
    expect("R4: REJECTS no-enforcement-point with empty mediation_evidence", [ne_medempty], False)
    # 21 (NO-EP-VERDICT-EMPTY). structural_verdict present (even 'unresolved') -> REJECTED
    ne_verd = _valid_no_ep(); ne_verd["structural_verdict"] = "unresolved"
    expect("R4: REJECTS no-enforcement-point carrying structural_verdict='unresolved' (vacuum != deferred)", [ne_verd], False)
    # 22 (NO-EP-NO-REPR). carrying a representation-analysis field -> REJECTED
    ne_repr = _valid_no_ep(); ne_repr["per_variable_visibility"] = {"x": "missing"}
    expect("R4: REJECTS no-enforcement-point carrying a representation-analysis field", [ne_repr], False)
    # 22b (NO-EP-NO-REPR, key-appearance even if null). null-valued repr key -> REJECTED
    ne_reprnull = _valid_no_ep(); ne_reprnull["witness_artifact_hash"] = None
    expect("R4: REJECTS no-enforcement-point with a null-valued representation key (no fence-sitting)", [ne_reprnull], False)
    # 23 (NO-EP-IDENTITY-REQUIRED). missing identity subfield -> REJECTED
    ne_noident = _valid_no_ep(); del ne_noident["repo_file_line"]
    expect("R4: REJECTS no-enforcement-point missing a constraint-identity subfield", [ne_noident], False)
    # 24 (CF2-3WAY). no-enforcement-point with a non-empty analyzed_layer -> REJECTED
    ne_layer = _valid_no_ep(); ne_layer["analyzed_layer"] = "guard"
    expect("CF2-3WAY: REJECTS no-enforcement-point with a non-empty analyzed_layer", [ne_layer], False)
    # 25 (LAYER-B-CONSTRAINT-AUDIT-ONLY). Layer-B row marked no-enforcement-point -> REJECTED
    b_ne = _valid_layer_b(); b_ne["row_kind"] = "no-enforcement-point"
    expect("LAYER-B-CONSTRAINT-AUDIT-ONLY: rejects Layer-B no-enforcement-point row", [b_ne], False)

    npass = sum(1 for _, ok, _ in results if ok)
    for name, ok, v in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if not ok and v:
            print(f"         (violations seen: {v})")
    print(f"selftest: {npass}/{len(results)}")
    return npass == len(results)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if selftest() else 1)
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print("usage: validate_block_five_schema_v0_1_3.py --selftest | <rows.json>")
        sys.exit(2)
    schema = load_schema()
    rows = json.load(open(args[0]))
    if isinstance(rows, dict):
        rows = rows.get("rows", [rows])
    viol, flags = validate_rows(rows, schema)
    for fl in flags:
        print(f"[FLAG] {fl}")
    for v in viol:
        print(f"[VIOLATION] {v}")
    print(f"{len(rows)} rows: {len(viol)} violations, {len(flags)} flags")
    sys.exit(0 if not viol else 1)
