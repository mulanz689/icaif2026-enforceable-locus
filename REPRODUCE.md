# Reproduction, step by step

Every stage below is deterministic, offline, and free. `./run_all.sh` runs all of them
and exits non-zero on any mismatch; this file documents each stage individually, with the
output you should see, so a partial or failing run can be localised.

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt     # pandas only, for the live-guard stage
./run_all.sh                        # ~15 s
```

`PYTHON=/path/to/python ./run_all.sh` selects an interpreter.
`./run_all.sh --no-guard` skips the one stage that needs `pandas`.

---

## 0. Integrity before anything else

```bash
python3 verify_pin.py
```

```
pin        : dddf96e35d511328b44a4307df0fb1cf49433e8d
files      : 1202 in manifest, 1202 on disk
skills     : 88 (expected 88)
PIN VERIFY PASSED
```

Optional cross-check against upstream (the only step that touches the network, and it is
never required; the vendored subset is sufficient):

```bash
git clone https://github.com/HKUDS/Vibe-Trading /tmp/vt
git -C /tmp/vt checkout dddf96e35d511328b44a4307df0fb1cf49433e8d
python3 verify_pin.py --against /tmp/vt
```

Released artifact bytes:

```bash
cd audit && shasum -a 256 -c ../FROZEN_ARTIFACTS.sha256
```

---

## 1. Delivery: the constraint never reaches the model (§5.1–5.2, Figure 2)

```bash
cd audit && python3 freeze_smi_probe.py --verify
```

```
envelope_codepoints_len     : 42678
tool_result_limit           : 10000
scope_offset_in_envelope_cp : 42629
a1_full_sha256              : 92b5a36630df0776578730b3c55a1850b8ad9a39d583ba12d878b0add3d9f54d
a1_native_sha256            : cf5a3d49f0c09e25315bbf8f95a3c2f81c60eeca8ab150c285fa381c873d321f
scope_in_a1_full            : True
scope_in_a1_native          : False
VERIFY PASSED: recomputed values match frozen artifact @ dddf96e
```

The probe uses the snapshot's own frontmatter parser and reconstructs the real path,
parse → `<skill name=…>` wrap → `json.dumps(…, ensure_ascii=False)` → `envelope[:10_000]`.
It does not reimplement any of it. The single intervention between the two arms is the
slice, applied to the serialized envelope (not the raw file, not bytes, not the outer
tool-message wrapper).

Derived in the paper from these fields: the 35-cp operative phrase at `[42629, 42664)`;
the 49-cp envelope-tail span `[42629, 42678)` = 35 + 14 cp of envelope closing;
`42629 − 10000 = 32629` cp between the cut and the clause.

Note `a1_native_valid_json: False`: the harness also delivers a syntactically incomplete
JSON prefix without validating or repairing it. The paper records this as a second
integrity observation at the same boundary, not a second constraint-loss case.

---

## 2. Representability: the guard never carried the distinction (§3, §5.1)

```bash
python3 validate_env_cards.py
```

```
VALIDATION PASSED: 11 cards (10 authorization + 1 precondition)
distinct guard reason codes covered: 10
```

The eleven planes are extracted from the pinned `enforcement.py` and matched 1:1 against
the frozen constraint cards. The witness constructor (stage 3) additionally enumerates
the guard interface by **live introspection** rather than by reading documentation:
`inspect.signature(check_mandate)` → exactly 7 parameters; `OrderIntent` → exactly 6
fields; neither carries skill text, signal provenance, or authorized use.

---

## 3. The collision witness, against the real guard (§5.4, Table 3)

Needs `pandas`, because it imports the upstream guard rather than mocking it.

```bash
python3 construct_sleeve_breach_episode.py --verify
```

```
VERIFY PASSED: re-derived record matches frozen artifact @ dddf96e;
  L1 truncation crosslock OK / L2 spans OK / L3 input space OK /
  L4 planes==env_cards, provenance UNSUPPORTED / L5 guard live: breach ALLOW,
  twin identical, negative control DENY / constructed marking present.
```

Five links, each machine-checked: L1 re-derives the truncation and cross-locks nine keys
against the frozen probe; L2 asserts the six delivery spans line by line in
`loop.py`/`context.py`; L3 enumerates the input space live; L4 extracts the verdict
planes from source and marks signal provenance `UNSUPPORTED`; L5 runs the real
`check_mandate` three times: breach `ALLOW`, compliant twin on byte-identical
guard-visible inputs, over-cap negative control `DENY` on the single-order-notional plane.
The negative control is what proves the guard executed rather than a stub.

Then prove the checks can fail:

```bash
python3 construct_sleeve_breach_episode.py --selftest
```

```
  [PASS] positive: freshly derived record passes
  [PASS] tamper: scope_in_a1_native flipped True
  [PASS] tamper: crosslock hash drift injected
  [PASS] tamper: delivery span mismatch
  [PASS] tamper: OrderIntent grows a provenance field
  [PASS] tamper: verdict-plane set gains signal_provenance
  [PASS] tamper: provenance plane marked SUPPORTED
  [PASS] tamper: breach verdict recorded as DENY
  [PASS] tamper: negative control wrong limit
  [PASS] tamper: constructed flag cleared
SELFTEST: 10/10 PASSED
```

---

## 4. The exact matched-pair bound (§5.5, Table 3)

```bash
python3 qemc_dryrun_sleeve.py --verify --selftest
```

```
selftest: 12/12
--verify: 16/16 predictions hit
```

The quantitative-evaluation contract was committed **before** this computation
(`QEMC_v0_1_1.md`, sha256 `9535e9f7…`, pinned as a literal inside the script and signed in
`QEMC_Freeze_Signed_2026-07-29.json`); `--verify` asserts all 16 pre-committed predictions.
Resulting fields: `Q5_representational_capacity = 0.0` (RC = 0),
`Q3_Rhat_star_guard = Q5_R_star_0 = 0.5`, `Q7_algorithmic_gap = 0.0`,
`Q4_FNR_star_deterministic = 1.0`, `Q4_FNR_star_randomized = {0.01: 0.99, 0.05: 0.95, 0.10: 0.9}`.

These are exact statements under the frozen matched-pair design measure, with equal mass on
the pair, **not** reweighted to deployment traffic. They are not estimates of deployment
frequency, and the paper does not present them as such.

---

## 5. Position-only repair restores availability (§5.6)

```bash
python3 repair_pinning_probe_verbatim.py
```

```
repaired scope-phrase offset (cp): 158 (< 10000)
arm hashes separate: True
REPAIR-1-VERBATIM VERDICT: PASS (deterministic survival restored; position-only)
```

The duplicated clause begins at envelope cp 112, the figure the paper reports,
with the operative phrase at cp 158 within it, and the pinned line starting at cp 73; read
`repaired.clause_offset_in_envelope_cp` in the JSON. The payload is the authored terminal
line copied byte-verbatim (122 cp, asserted by raw-string equality), so the attribution is
purely positional: no wording changed, the pinned snapshot bytes are untouched, and the
variant is built in memory. `cross_lock.matches_frozen_probe = true` confirms the baseline
arm still reproduces the frozen probe exactly.

This repairs `D(c, L1)` only. The guard's `R = 0` is position-independent and every
Table 3 quantity is unchanged.

---

## 6. Structural census (§6.1, Table 4)

```bash
python3 census_truncation_88.py
```

```
skills at pin                 : 88
load-truncated at 10,000 cp   : 33/88
median / max envelope loss    : 16.1% / 90.3% (tushare)
negative-scope v1             : 7/88
negative-scope v1|v2          : 8/88  (>= 8/88 known count)
trigger regex of record       : 10/88
pinned trigger list (input)   : 13  not matched by regex of record: ['qveris', 'thesis-tracker', 'web-reader']
anchor envelope / surviving    : 42678 cp / 23.4%

--- fail-closed assertions against published values ---
  [HIT] n_skills == 88  (got 88)
  [HIT] load-truncated == 33/88  (got 33/88)
  [HIT] median envelope loss == 16.1%  (got 16.1%)
  [HIT] max envelope loss == 90.3%  (got 90.3% (tushare))
  ...
CENSUS PASSED: published Table 4 values reproduced
```

Read caveats **C1** and **C3** in `CLAIMS.md` before citing the trigger count or this
script: `13/88` is a pinned input the regex of record does not reproduce, and this script
was written for the release rather than during the study.

Then the located-span reconciliation and the discriminant case:

```bash
python3 census_survival_extended.py | tail -4
python3 census_scope_survival.py    | tail -4
```

```
N_past_cut / N_located_span (load-bearing, matches Cohort_Freeze §3) = 1 / 16
  union members with NO locatable span (excluded from load-bearing denom): ['qveris', 'thesis-tracker']
```

```
skill                  rawB  envCP clauseOff  margin survives   gap nativeJSON
research-goal          2856   2780       291    9661     True False       True
vnpy-export           11922  11677      2040    7922     True False      False
```

`research-goal` is the discriminant check the paper describes: a located scope clause that
lies **inside** the cut, whose full and native materializations are byte-identical and
whose delivery the same probe reports as successful. The audit therefore distinguishes the
natural anchor failure from a delivered scope constraint on the same pipeline instead of
mechanically labelling materialization as unavailable.

Both scripts **write** their outputs. Run them from a scratch copy (as `run_all.sh` does)
if you want the released artifacts left untouched.

---

## 7. Sole-authoritative premise (§5.1)

```bash
python3 prefix_scope_scan.py
```

24 patterns over the exact 10,000-cp surviving prefix, hash-locked to the frozen probe
(`prefix_sha256 = cf5a3d49…`). Exactly one hit, at cp 1626, disclosed verbatim: a
channel-scoped caveat against blind copy-trading of particular price levels. It is not a
substitute for the anchor: different level (channel, not skill), different speech act
(diligence demand, not a use-class prohibition), and the witness order copies no channel
price, so it satisfies the caveat while violating the clause. Frontmatter: 0 hits.
`prefix_manual_adjudication_v0_1.json` records the complete human read of the same prefix
(single adjudicator, disclosed).

Re-running this script does not re-emit the hand-recorded `classification` block; see
caveat **C2**.

---

## 8. Cross-constraint evidence (§6.2, Table 5)

```bash
python3 validate_block_five_schema_v0_1_3.py --selftest
python3 validate_block_five_schema_v0_1_3.py block_five_trialfill_batch1_v0_3.json
```

```
selftest: 32/32
8 rows: 0 violations, 0 flags
```

The promotion artifact carries eight rows and Table 5 reports six. `CLAIMS.md` §8 gives
the exact mapping: six in-stack rows in the table, one promoted external corroborating row
deliberately outside the measured denominator, one row held and never promoted.

---

## 9. What is *not* here, and why

No confirmatory behavioral data exist. The pre-run diagnostics in `diagnostics/` did not
establish that the constraint changes the target behavior when fully delivered, so the
confirmatory run was never launched; a full-versus-native difference, or its absence,
would have conflated transport with downstream instruction compliance. Those diagnostics
require an API key, are non-deterministic, and are excluded from inference in the paper
and here. See `diagnostics/README.md`.

Internal freeze sign-off and review records are not released; they are not needed, because
every published number is recomputed by the shipped code (`CLAIMS.md`, caveat C5).
