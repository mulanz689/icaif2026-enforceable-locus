# Pre-run behavioral diagnostics (excluded from inference)

**Nothing in this directory supports a claim in the paper.** These are the small pre-run
diagnostics described in §6.3 and §7, released for completeness. They are excluded from
inference here for exactly the reason they are excluded there, and they are the reason the
confirmatory behavioral study was **not** launched.

## Why they are excluded

A full-versus-native behavioral contrast is only causally informative about materialization
if the fully delivered constraint first demonstrates efficacy. These diagnostics did not
establish that prerequisite:

| Diagnostic | Design | Result | Paper |
|---|---|---|---|
| `smi_paired_deepseek-v4-pro.json` | N = 2 paired episodes, one model family, chat-driver harness, temperature 1.0, multi-turn, identical deterministic mock fixtures in both arms | order submissions in **both** the full-context and truncated arms | §6.3 |
| `results_rg_behavioral_pilot.json` / `.jsonl` | 12 research-goal episodes, one safety-tuned family, 4 per condition, single-turn tool-emission proxy | 0/12 violations; stripping the clause produced **no** cross-condition variation | §7 "Availability is not efficacy" |
| `smi_probe_deepseek-v4-pro.json` | single-arm feasibility probe on the native (truncated) arm | feasibility only | — |

Without the efficacy prerequisite, a difference between full and truncated contexts, or
the absence of one, conflates transport with downstream instruction compliance. Both
sample sizes are far too small for effect estimation in any case. The artifacts carry their
own `status` fields saying so (`PILOT / EXCLUDED_FROM_INFERENCE`,
`FEASIBILITY_ONLY / EXCLUDED_FROM_INFERENCE`). Please do not quote a rate from them.

The paper's confirmatory result is entirely structural and is reproduced by `../run_all.sh`
with zero model calls.

## What *is* deterministic here

Each runner ships a model-free selftest proving its violation oracle can actually
discriminate, since a probe whose oracle cannot fail would carry no information. These need no API key
and no network:

```bash
python3 smi_behavioral_probe.py --selftest      # 8/8  -- arms differ only by the [:10000] slice
python3 behavioral_control_pilot.py --selftest   # 6/6  -- container vs violator stubs separate
```

Both also assert the envelope they build is byte-equal to the frozen sha from the pinned
snapshot, so they fail loud on drift rather than probing a stale arm.

## Reproducing the model-dependent part

You cannot reproduce these byte-for-byte: they call hosted inference at temperature 1.0,
so results vary by run, by provider, and by model version. The models used are recorded in
the artifacts' `model` fields; the paper deliberately refers to them only as "one model
family" / "one safety-tuned family", since no claim rests on a particular vendor.

Keys are read from the environment; none is embedded anywhere in this repository:

```bash
DEEPSEEK_API_KEY=... python3 smi_behavioral_probe.py --paired \
    --model <model-id> --base-url <endpoint> --key-env DEEPSEEK_API_KEY
OPENAI_API_KEY=...   python3 behavioral_control_pilot.py --model <model-id>
```

Running these costs money and produces a diagnostic, not a result.

## Note on `snapshots`

`diagnostics/snapshots` is a relative symlink to `../audit/snapshots`, because these
scripts resolve the pinned stack relative to their own directory. If your platform does
not preserve symlinks on checkout (some Windows configurations), copy or junction
`audit/snapshots` to `diagnostics/snapshots` before running the selftests.
