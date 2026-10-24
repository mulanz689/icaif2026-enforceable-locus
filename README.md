# When No Enforceable Locus Exists: reproduction artifact

Reproduction package for the ICAIF '26 paper "When No Enforceable Locus Exists:
Availability and Representability in a Financial AI Agent Stack."

The paper asks a systems question that precedes "does the agent obey the rule?": does the
deployed execution path contain any decision locus that both receives a constraint
(availability, `D`) and observes enough state to tell compliant from violating actions
(representability, `R`)? Selective enforcement requires `D·R = 1` at some decision locus.
Audited on a pinned open-source financial agent stack, neither in-stack locus satisfies it
for a real trading-use restriction.

Every confirmatory result in the paper is deterministic and model-independent. This
package reproduces all of them with:

```bash
pip install -r requirements.txt
./run_all.sh
```

The suite performs no model calls and no network requests, and exits non-zero on any
drift.

Expected tail of a clean run:

```
=== Summary ===
  passed 18   failed 0   skipped 0

  All confirmatory claims reproduced. 0 model calls, 0 network, $0.
```

## What is audited

| System under audit | HKUDS/Vibe-Trading, pinned commit `dddf96e35d511328b44a4307df0fb1cf49433e8d` |
|---|---|
| Path | `SKILL.md` → parse → wrap → serialize → truncate @ 10,000 code points → model context → order proposal → pre-trade guard |
| Anchor constraint | `SMI-SCOPE-01`: *"Scope: quantitative research / factor mining (not for direct live-trading signals)"*, authored on the final line of a real bundled skill |
| Headline finding | The anchor's operative phrase sits at envelope cp `[42629, 42664)` inside a 42,678-cp envelope, so fixed-prefix truncation removes it 32,629 cp before the cut is reached. It never arrives at the only locus that could represent it, and the shipped guard's eleven verdict planes did not represent it in either arm. |

## What reproduces

| Paper claim | Check |
|---|---|
| §5.1–5.2 envelope 42,678 cp, clause @ 42,629, `scope_in_a1_native = False`, both arm hashes | `freeze_smi_probe.py --verify` |
| §3, §5.1 guard interface: exactly 7 parameters, 6 `OrderIntent` fields, 11 verdict planes, provenance `UNSUPPORTED` | `validate_env_cards.py`, `construct_sleeve_breach_episode.py --verify` |
| §5.4, Table 3 real `check_mandate`: breach `ALLOW`, twin byte-identical, over-cap control `DENY` | `construct_sleeve_breach_episode.py --verify` / `--selftest` (10/10) |
| §5.5, Table 3 exact bound `RC = 0`, `R* = 0.5`, `FNR*(α) = 1 − α`, gap `= 0` | `qemc_dryrun_sleeve.py --verify --selftest` (16/16, 12/12) |
| §5.6 position-only repair: duplicated clause at cp 112, flag flips `False → True` | `repair_pinning_probe_verbatim.py` |
| §6.1, Table 4 88 skills, 33 truncated, median 16.1% / max 90.3%, 7/88 and ≥8/88 screens | `census_truncation_88.py` (+ `--selftest`) |
| §6.1 16 located spans, 1/16 beyond the cut, research-goal discriminant | `census_survival_extended.py`, `census_scope_survival.py` |
| §5.1 24-pattern lexicon over the surviving prefix, one disclosed hit @ cp 1626 | `prefix_scope_scan.py` |
| §6.2, Table 5 frozen cross-constraint schema, validator 32/32, 0 violations | `validate_block_five_schema_v0_1_3.py` |

`CLAIMS.md` binds each reported number to its artifact, the exact field inside it, and
the command that re-derives it. It also records five caveats, including one
reproducibility gap (the `13/88` trigger-screen count is a pinned input rather than a
re-derivable screen output) and one artifact that carries a hand-recorded classification
block. Readers should consult it before citing any figure from this package.

## Layout

```
run_all.sh                  one-command reproduction, fail-closed
verify_pin.py               upstream snapshot integrity (and optional diff vs a fresh clone)
compare_artifact.py         regenerated-vs-released JSON diff; deviations must be named
CLAIMS.md                   every paper number -> artifact -> field -> command
REPRODUCE.md                step-by-step, with expected output per stage
REDACTIONS.md               the three files altered for privacy, with before/after hashes
THIRD_PARTY_NOTICES.md      what is vendored from upstream, why, and under which license
PIN_MANIFEST.sha256         sha256 of every vendored upstream file
FROZEN_ARTIFACTS.sha256     sha256 of every reproducer and frozen artifact

audit/                      reproducers and frozen evidence (flat: scripts resolve paths
                            relative to themselves, so the layout is load-bearing)
  snapshots/Vibe-Trading/   pinned upstream subset (MIT; see THIRD_PARTY_NOTICES.md)
diagnostics/                pre-run behavioral diagnostics, excluded from inference
```

The manuscript is not redistributed here. The paper is published by the ACM as
`doi:10.1145/3858063.3858819` (resolves once the ICAIF '26 proceedings go live in
November 2026); `CITATION.cff` carries the full citation metadata.

## Design notes

### Fail closed on drift

The paper's result is scoped to one commit. Any change to `OrderIntent`, `check_mandate`,
or the materialization path invalidates it, so every reproducer cross-locks against frozen
hashes and refuses to emit a verdict on drift. `verify_pin.py` checks all 1,202 vendored
upstream files and the 88-skill count.

### Negative controls

Three reproducers ship tamper fixtures that are required to break them: the witness
constructor runs 9 mutations plus a positive control (10/10), the schema validator runs 32
fixtures (32/32), and the census runs 8 mutations plus a control establishing that the
negative-scope screen can miss a clause (10/10). These controls exist so that a passing
check carries information.

### Frozen artifacts are not overwritten in place

`run_all.sh` copies the reproducers into a scratch directory, regenerates there, and
byte-diffs against the released copies. Five of six write-mode reproducers regenerate
byte-identically; the sixth differs only by the hand-recorded field documented as caveat
C2 in `CLAIMS.md`.

### No behavioral claim

The paper reports no confirmatory behavioral result. Its pre-run diagnostics did not
establish that the constraint changes the target behavior under full delivery, so the
confirmatory run was never launched; a full-versus-native contrast would conflate
transport with instruction compliance. The diagnostics are released in `diagnostics/` and
labelled accordingly.

## Requirements

Python 3.9 or later. Every stage except the live-guard stage runs on the standard library.
The witness constructor imports the upstream pre-trade guard, which requires `pandas`
(see `requirements.txt`); without it, `run_all.sh` skips that stage and reports it as
skipped rather than passed. `./run_all.sh --no-guard` skips it explicitly.

## License

Code and documentation in this repository: MIT (`LICENSE`).

The vendored upstream subset under `audit/snapshots/Vibe-Trading/` is redistributed under
the upstream MIT license, with its copyright notice and `NOTICE` preserved. Parts of that
subset carry their own additional attribution: the factor definitions under
`agent/src/factors/zoo/` include material attributed to Microsoft Qlib under Apache 2.0,
and each such directory ships its own `LICENSE.md`. See `THIRD_PARTY_NOTICES.md` for the
full breakdown.

## Citation

See `CITATION.cff`.
