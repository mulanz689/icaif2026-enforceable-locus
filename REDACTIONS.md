# Redactions

Exactly three files in this package differ from the artifacts frozen during the study, and
only by the removal of personal identifiers and an internal reviewer codename. No
scientific field, verdict, hash of a measured object, offset, count, or statistic was
changed. Every published number still reproduces fail-closed; see `./run_all.sh`.

This file exists so that the changes are auditable rather than silent. Altering the bytes
of a frozen artifact without recording the change would itself compromise the provenance
chain.

## What was removed

| File | Field(s) | Was | Now |
|---|---|---|---|
| `audit/QEMC_Freeze_Signed_2026-07-29.json` | `signatures.owner_of_record` | a personal account handle, followed by the approval text and date | `[redacted: project owner of record]`, approval text and date kept verbatim |
| `audit/QEMC_Freeze_Signed_2026-07-29.json` | `signatures.research_side` | an internal reviewer codename, followed by the hash-gate note | `[redacted: research-side signer]`, note kept verbatim |
| `audit/block_five_trialfill_batch1_v0_3.json` | `reviewer` (8 rows) | the same internal reviewer codename | `research-side reviewer` |
| `audit/validate_block_five_schema_v0_1_3.py` | `reviewer` in 3 selftest fixtures | the same internal reviewer codename | `research-side reviewer` |

Nothing else in the package was edited. All other files in `audit/` are byte-exact copies
of the study artifacts, except `census_truncation_88.py`, which is new and labelled as such
(`CLAIMS.md`, caveat C3).

## Hashes before and after

| File | sha256 as frozen in the study | sha256 as released |
|---|---|---|
| `QEMC_Freeze_Signed_2026-07-29.json` | `2428221066d252f09a96c607254d5de967795dc2dbf3011947f255b2ab3df8d0` | `a6df3f086d1a03211e9f43ea1efa7d7b111d521f2a43a9b456425219684f5270` |
| `block_five_trialfill_batch1_v0_3.json` | `4369f80956a88582…` | see `FROZEN_ARTIFACTS.sha256` |
| `validate_block_five_schema_v0_1_3.py` | `9fb1dac4f7f1ff70…` | see `FROZEN_ARTIFACTS.sha256` |

The study's own freeze records cite the two "before" prefixes (`py 9fb1dac4..` and the
QEMC freeze hash), so anyone comparing against a published hash list will see these three
and only these three.

## The one downstream consequence

`qemc_dryrun_sleeve.py` hashes its input freeze artifact into its output. Re-running it
therefore produces `_provenance.freeze_sha256 = a6df3f08…` while the released frozen
output `audit/qemc_dryrun_sleeve_v0_1.json` still carries the study value `2428221066…`.

That single provenance field is the only declared deviation in the whole reproduction. `run_all.sh` passes it to `compare_artifact.py` by name:

```
--allow-differ _provenance.freeze_sha256
```

Everything else in that artifact (`Q1_structural_verdict`, `Q3_Rhat_star_guard`,
`Q4_FNR_star_*`, `Q5_representational_capacity`, `Q5_R_star_0`, `Q6_R_actual`,
`Q7_algorithmic_gap`, `Q8_rho_guard`, `population`, `fibers`, and the episode hash) must
match byte-for-byte or the run fails. The allowance names a single path rather than a
wildcard, and it was verified to be an effective gate: changing `Q5_representational_capacity` from `0.0` to
`0.25` in the released artifact makes `run_all.sh` report two failures and exit 1.

The study-side value `2428221066d252f09a96c607254d5de967795dc2dbf3011947f255b2ab3df8d0`
is recorded above so the original provenance chain remains checkable by anyone holding the
unredacted artifact.
