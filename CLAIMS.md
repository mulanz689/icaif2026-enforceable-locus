# Claim-to-artifact binding

Every number reported in the paper, bound to the artifact that produces it, the exact
field inside that artifact, and the command that re-derives it. `./run_all.sh` runs all
of these and exits non-zero on any mismatch.

All quantities are deterministic. The confirmatory result involves zero model calls:
nothing in `audit/` contacts a network or an inference endpoint. Code-point lengths are
Unicode code points throughout, never bytes; the truncation in `loop.py:1451` is a
Python `str` slice.

Pin for every claim: HKUDS/Vibe-Trading @ `dddf96e35d511328b44a4307df0fb1cf49433e8d`.

---

## 1. Delivery (`D`): the materialization path (§5.1–5.2, Figure 2)

| Paper value | Artifact | Field | Command |
|---|---|---|---|
| truncation limit 10,000 cp (`loop.py:53,1451`) | `smi_probe_frozen_v0_1.json` | `tool_result_limit` | `python3 freeze_smi_probe.py --verify` |
| serialized envelope 42,678 cp | same | `envelope_codepoints_len` | same |
| clause offset 42,629 cp | same | `scope_offset_in_envelope_cp` | same |
| operative phrase 35 cp, `[42629, 42664)` | derived: `len("not for direct live-trading signals")` = 35, from `scope_clause` at `scope_offset_in_envelope_cp` | `scope_clause` + offset | same |
| envelope-tail span 49 cp, `[42629, 42678)` | derived: `envelope_codepoints_len − scope_offset_in_envelope_cp` = 49 (= 35 + 14 cp of envelope closing) | both fields | same |
| cut precedes the clause by 32,629 cp | same | `visibility_assertion` | same |
| "less than one quarter" survives (23.4%) | `census_truncation_88_v1_0.json` | `anchor_surviving_fraction_pct` | `python3 census_truncation_88.py` |
| `scope_in_a1_native = False`, `scope_in_a1_full = True` | `smi_probe_frozen_v0_1.json` | both fields | `python3 freeze_smi_probe.py --verify` |
| both baseline-arm hashes byte-match | same | `a1_full_sha256`, `a1_native_sha256` | same |
| native arm is syntactically invalid JSON (§5.2, second integrity observation) | same | `a1_native_valid_json = false` | same |
| clause on the skill's final line (`SKILL.md:1295`) | pinned snapshot | `audit/snapshots/Vibe-Trading/agent/src/skills/social-media-intelligence/SKILL.md` | `wc -l` on that file |
| delivery spans `loop.py:53,1451,1452,1454` and `context.py:268,274` asserted line-by-line | `sleeve_breach_episode_v0_1.json` | `L2_delivery_spans` | `python3 construct_sleeve_breach_episode.py --verify` |

## 2. Representability (`R`): the pre-trade guard interface (§3, §5.1)

| Paper value | Artifact | Field | Command |
|---|---|---|---|
| `check_mandate` takes exactly 7 parameters | `sleeve_breach_episode_v0_1.json` | `L3_enforcement_input_space` (live `inspect.signature` against the pinned guard) | `python3 construct_sleeve_breach_episode.py --verify` |
| `OrderIntent` carries exactly 6 fields | same | `L3_enforcement_input_space` | same |
| exactly 11 verdict planes (10 authorization + 1 order-intent precondition) | `sleeve_breach_episode_v0_1.json` + `env_cards_v0_1.json` | `L4_control_planes`, cross-checked 1:1 against the env-card reason codes | `python3 validate_env_cards.py` → `VALIDATION PASSED: 11 cards (10 authorization + 1 precondition)` |
| signal provenance / authorized use is `UNSUPPORTED` on every plane | `sleeve_breach_episode_v0_1.json` | `L4_control_planes` | `python3 construct_sleeve_breach_episode.py --verify` |

## 3. Collision witness (§5.4)

| Paper value | Artifact | Field | Command |
|---|---|---|---|
| real pinned `check_mandate` returns `ALLOW` for the breach-provenance order | `sleeve_breach_episode_v0_1.json` | `L5_witness_guard_run` (guard executed live, not stubbed) | `python3 construct_sleeve_breach_episode.py --verify` |
| compliant twin has byte-identical guard-visible inputs ⇒ identical verdict under *any* mandate | same | `L5_witness_guard_run`, `structural_impossibility` | same |
| negative control (same order above the notional cap) is `DENY` on the single-order-notional plane, which establishes that the guard is live | same | `L5_witness_guard_run` | same |
| the episode is marked CONSTRUCTED (possibility proof, not prevalence) | same | `constructed` | same |
| guards can fire: 9 tamper mutations + 1 positive control | — | — | `python3 construct_sleeve_breach_episode.py --selftest` → `SELFTEST: 10/10 PASSED` |

## 4. Exact matched-pair bound (§5.5, Table 3)

Contract committed before computation: `QEMC_v0_1_1.md`
(sha256 `9535e9f79100a17d20fac5f70685b127e2f5df2829da9e86cee382173e4f76e9`, the value
`qemc_dryrun_sleeve.py` pins), signed in `QEMC_Freeze_Signed_2026-07-29.json`.

| Paper value | Field in `qemc_dryrun_sleeve_v0_1.json` | Value |
|---|---|---|
| structural collision, identical `Z` | `Q1_structural_verdict` | `"collision-found"` |
| `R*_guard = 0.5` | `Q3_Rhat_star_guard` | `0.5` |
| `R*_0 = 0.5` | `Q5_R_star_0` | `0.5` |
| `RC = 0` | `Q5_representational_capacity` | `0.0` |
| algorithmic gap `= 0` | `Q7_algorithmic_gap` | `0.0` |
| `FNR*` deterministic (FPR < 1) `= 1.0` | `Q4_FNR_star_deterministic` | `1.0` |
| `FNR*(α) = 1 − α` at α ∈ {0.01, 0.05, 0.10} | `Q4_FNR_star_randomized` | `{0.01: 0.99, 0.05: 0.95, 0.10: 0.9}` |
| identification = exact census (not an estimate) | `Q3_identification` | `"exact-census"` |
| 16/16 pre-committed predictions matched | — | `python3 qemc_dryrun_sleeve.py --verify` → `--verify: 16/16 predictions hit` |
| internal selftest 12/12 | — | `python3 qemc_dryrun_sleeve.py --selftest` → `selftest: 12/12` |

The design measure places equal mass on the matched pair and is not reweighted to
deployment traffic; `population` records `N = 2` (1 violating, 1 compliant, 0 excluded).

## 5. Position-only repair (§5.6)

| Paper value | Artifact | Field | Command |
|---|---|---|---|
| duplicated clause begins at envelope cp 112 | `repair_pinning_probe_verbatim_v0_1.json` | `repaired.clause_offset_in_envelope_cp` | `python3 repair_pinning_probe_verbatim.py` |
| `scope_in_a1_native` flips `False` → `True` | same | `baseline.scope_in_a1_native`, `repaired.scope_in_a1_native`, `flip.scope_in_a1_native` | same |
| baseline reproduces the frozen probe exactly | same | `cross_lock.matches_frozen_probe = true` | same |
| native-arm hashes separate after repair | same | `repaired.a1_native_sha256` ≠ `cross_lock.baseline_a1_native_sha256` | same |
| payload is the authored terminal line copied byte-verbatim (122 cp), wording unchanged | same | `payload.verbatim = true`, `payload.cp = 122`, `payload.byte_identity_assert` | same |
| repaired envelope 42,804 cp | same | `repaired.envelope_cp` | same |

Related fields in the same artifact: the pinned line starts at cp 73 and the operative
phrase within it at cp 158; the paper reports the clause offset, cp 112.

`repair_pinning_probe_v0_1.json` is the earlier distillation-payload variant (repaired
offset cp 120). It is superseded for the paper by the verbatim probe (see its own
`supersedes_for_paper` field) and is shipped only so the supersession is auditable.

## 6. Structural census (§6.1, Table 4)

| Paper value | Artifact | Field | Command |
|---|---|---|---|
| 88 skills bundled at pin | `census_truncation_88_v1_0.json` | `n_skills` | `python3 census_truncation_88.py` |
| 33/88 load-truncated at 10,000 cp | same | `n_load_truncated` | same |
| median / max envelope loss 16.1% / 90.3% | same | `median_envelope_loss_pct`, `max_envelope_loss_pct` (max = `tushare`) | same |
| negative-scope lexical hits 7/88 | same | `negative_scope_v1`, `negative_scope_v1_count` | same |
| known negative-scope count ≥ 8/88 (disclosed false negative = `research-goal`'s "never use it to place, submit, or execute trades") | same | `negative_scope_v1_or_v2` | same |
| trigger-marked declarations 13/88 | pinned screen output; see caveat C1 below | `pinned_trigger_13` | — |
| protocol-identified located spans = 16 | `census_survival_extended_v0_1.json` | reconciliation printed by the script | `python3 census_survival_extended.py` → `= 1 / 16` |
| located spans beyond the cut = 1/16 (the anchor) | same | same | same |
| two trigger-marked skills lack a locatable span (`qveris`, `thesis-tracker`) | same | `span_located = false` rows + printed exclusion list | same |
| discriminant check: the research-goal clause lies *inside* the cut, arms byte-identical, probe reports delivery | `census_scope_survival_v0_1.json`, `census_d1_promotable_v0_1.json` | `clause_survives_10000cp_cut = true`, `native_vs_full_gap = false`, both arm hashes equal | `python3 census_scope_survival.py` |
| 6 negative-scope candidate spans all survive the cut (0/6 gap) | `census_scope_survival_v0_1.json` | `native_vs_full_gap` across rows | same |

Envelope loss is measured on the serialized envelope, the exact object
`loop.py:1451` truncates, as `1 − 10000/len(envelope)`. This is the only denominator
under which all three published values (33, 16.1%, 90.3%) hold simultaneously.

## 7. Sole-authoritative premise (§5.1)

| Paper value | Artifact | Field | Command |
|---|---|---|---|
| 24-pattern negative-scope lexicon over the exact 10,000-cp surviving prefix | `prefix_scope_scan_v0_1.json` | `lexicon` (24 entries), `target` | `python3 prefix_scope_scan.py` |
| prefix hash-locked to the frozen probe | same | `prefix_sha256`, `cross_locked_against` | same |
| exactly one negative-scope hit, at cp 1626, disclosed verbatim | same | `prefix_hits_raw` | same |
| the hit is a channel-scoped copy-trading caveat, non-equivalent | same | `classification` (hand-recorded; see caveat C2) | — |
| frontmatter carries no such statement (0 hits) | same | `frontmatter_meta_hits_raw = []` | same |
| manual adjudication of the complete prefix, single disclosed adjudicator | `prefix_manual_adjudication_v0_1.json` | whole file | — |

## 8. Cross-constraint evidence (§6.2, Table 5)

| Paper value | Artifact | Command |
|---|---|---|
| frozen schema, validator selftest 32/32 | `block_five_schema_v0_1_3.json` + `validate_block_five_schema_v0_1_3.py` | `python3 validate_block_five_schema_v0_1_3.py --selftest` → `selftest: 32/32` |
| rows validate with 0 violations | `block_five_trialfill_batch1_v0_3.json` | `python3 validate_block_five_schema_v0_1_3.py block_five_trialfill_batch1_v0_3.json` → `8 rows: 0 violations, 0 flags` |
| the six in-paper verdicts | `Block_Five_Trialfill_Promotion_2026-07-29.json` | `promotion` per row |

The promotion artifact carries eight rows; Table 5 of the paper reports six.
The mapping is explicit and not a discrepancy:

- In Table 5 (6 rows, all in-stack): sentiment sleeve × {model, guard}, research-goal
  scope × {model, guard}, notional cap (guard), trades/day cap (guard).
- Promoted but deliberately outside Table 5: `HERMES-TRUNC-46823`. This is the
  external corroborating GitHub issue. The paper discusses it in §2 as "corroborating
  motivation, not … a replication or part of our measured denominator", so it does not
  appear in the evidence table.
- Not promoted: `AITRADER-SCOPE-FIDELITY` is `HELD`, never promoted, and appears
  nowhere in the paper. It concerns a second repository that this paper makes no claim
  about. It is left in the artifact rather than deleted so that the released evidence
  face is the one the study actually signed.

## 9. Behavioral boundary (§6.3, §7)

The paper reports no confirmatory behavioral result, by design: the pre-run
diagnostics did not establish constraint efficacy under full delivery, so the
confirmatory run was never launched. See `diagnostics/README.md`. Those files are
released for completeness and are excluded from inference, exactly as in the paper.

---

## Caveats

**C1. "13/88 trigger-marked declarations" is a pinned input, not a reproducible screen
output.** The 13-skill list is carried as a literal in `census_survival_extended.py` and
everything downstream of it (per-skill span location through the real pipeline, the
16-skill union, the 1/16 past-cut rate) is re-derived deterministically from that list
and reproduces byte-identically. What is not recoverable from the released artifacts
is the screen that generated the 13: the trigger regex of record
(`when to use|use (this|the) skill when|trigger condition|trigger when|## trigger`,
case-insensitive) matches 10 of the 13 at this pin, missing `qveris`,
`thesis-tracker`, and `web-reader`. `census_truncation_88.py` prints both numbers side
by side and asserts neither against the other. No pattern was tuned to recover 13, since doing so would
fit the instrument to its own answer. Note the sensitivity this implies: the union denominator 16 depends on the 13-list, so
on the 10-skill regex set the same reconciliation would give 1/15 rather than 1/16.

**C2. `prefix_scope_scan_v0_1.json` carries one hand-recorded block.** Re-running
`prefix_scope_scan.py` reproduces every machine-derived field byte-identically but does
not re-emit the `classification` key, which records the human non-equivalence judgment
(level / speech act / non-substitutability). `run_all.sh` therefore compares that one
artifact field-by-field and reports the single expected extra key. Every other
write-mode reproducer regenerates byte-identically.

**C3. `census_truncation_88.py` was written for this release, not during the study.**
The paper's three census headline values were originally computed ad hoc and no frozen
script for them existed. This script re-derives them through the same materialization
pipeline the frozen probes use and asserts the published values fail-closed; its
`--selftest` includes eight tamper mutations and one control that must be able to fail.
It introduces no new result. Every other file in `audit/` is a byte-exact copy of the
artifact or reproducer frozen during the study.

**C4. The second stack is not redistributed.** The original negative-scope screen
script scanned a second repository in the same pass. The paper makes no claim about it,
and that repository ships no license file, so neither it nor that screen script is
included here. The screen's Vibe-Trading results (the 7/88 and ≥8/88 figures the paper
actually reports, with identical skill names) are reproduced by `census_truncation_88.py`
from the licensed snapshot alone.

**C5. Internal governance records are not released.** Freeze sign-off records, review
rounds, and project planning documents are not part of this artifact and are not needed:
every published number is recomputed by shipped code against the shipped snapshot. The
two frozen specifications that the reproducers read or hash-reference,
`Constraint_Card_Schema_v0_1.md` and `QEMC_v0_1_1.md`, are included.
