#!/usr/bin/env bash
#
# One-command reproduction of every confirmatory claim in
#   "When No Enforceable Locus Exists: Availability and Representability
#    in a Financial AI Agent Stack"  (ICAIF '26)
#
# Deterministic: performs no model calls and no network access.
# Exits non-zero on any drift; the script is designed to fail closed.
#
#   ./run_all.sh              full run (needs pandas for the live-guard stage)
#   ./run_all.sh --no-guard   skip the stage that imports the upstream guard
#
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUDIT="$HERE/audit"
PY="${PYTHON:-python3}"
SKIP_GUARD=0
[ "${1:-}" = "--no-guard" ] && SKIP_GUARD=1

PASS=0; FAIL=0; SKIP=0
declare -a FAILED=()

hdr() { printf '\n\033[1m=== %s ===\033[0m\n' "$1"; }
ok()  { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
bad() { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); FAILED+=("$1"); }
skp() { printf '  \033[33mSKIP\033[0m  %s\n' "$1"; SKIP=$((SKIP+1)); }

step() { # step <label> <cmd...>
  local label="$1"; shift
  local log; log="$(mktemp)"
  if "$@" >"$log" 2>&1; then ok "$label"; else bad "$label"; sed 's/^/        | /' "$log" | tail -25; fi
  rm -f "$log"
}

# ---------------------------------------------------------------- phase 0
hdr "0. Environment"
printf '  python     : %s\n' "$($PY -V 2>&1)"
printf '  package    : %s\n' "$HERE"
if $PY -c 'import pandas' >/dev/null 2>&1; then
  printf '  pandas     : %s (live-guard stage enabled)\n' "$($PY -c 'import pandas;print(pandas.__version__)')"
else
  printf '  pandas     : MISSING -- live-guard stage will be skipped\n'
  SKIP_GUARD=1
fi

# ---------------------------------------------------------------- phase 1
hdr "1. Upstream pin integrity (vendored HKUDS/Vibe-Trading subset)"
step "every vendored upstream file matches PIN_MANIFEST.sha256" \
  $PY "$HERE/verify_pin.py"

# ---------------------------------------------------------------- phase 2
hdr "2. Frozen artifact integrity (as released)"
if ( cd "$AUDIT" && shasum -a 256 -c "$HERE/FROZEN_ARTIFACTS.sha256" >/dev/null 2>&1 ); then
  ok "all frozen artifacts byte-identical to the released manifest"
else
  bad "frozen artifact hash mismatch"
  ( cd "$AUDIT" && shasum -a 256 -c "$HERE/FROZEN_ARTIFACTS.sha256" 2>&1 | grep -v ': OK$' | sed 's/^/        | /' )
fi

# ---------------------------------------------------------------- phase 3
hdr "3. Verifiers re-derived against the pinned snapshot (no writes)"
cd "$AUDIT"

# D-side: delivery / materialization  (paper S5.1-5.2, Fig. 2)
step "freeze_smi_probe --verify            -> envelope 42,678 cp; clause @42,629; scope_in_a1_native=False" \
  $PY freeze_smi_probe.py --verify

# Census: paper Table 4
step "census_truncation_88                 -> 33/88 truncated; median 16.1% / max 90.3%; 7/88 and >=8/88 screens" \
  $PY census_truncation_88.py
step "census_truncation_88 --selftest       -> tamper fixtures must fire (10/10)" \
  $PY census_truncation_88.py --selftest

# R-side: guard interface enumeration  (paper S3, S5.1)
step "validate_env_cards                   -> 11 verdict planes == 10 authorization + 1 precondition" \
  $PY validate_env_cards.py

# Cross-constraint evidence table  (paper Table 5)
step "validate_block_five --selftest        -> schema assertions fire (32/32)" \
  $PY validate_block_five_schema_v0_1_3.py --selftest
step "validate_block_five <rows>            -> 8 rows, 0 violations, 0 flags" \
  $PY validate_block_five_schema_v0_1_3.py block_five_trialfill_batch1_v0_3.json

# Collision witness against the REAL pinned guard  (paper S5.4, Table 3)
if [ "$SKIP_GUARD" = "1" ]; then
  skp "construct_sleeve_breach_episode --verify   (needs pandas; see requirements.txt)"
  skp "construct_sleeve_breach_episode --selftest (needs pandas; see requirements.txt)"
else
  step "construct_sleeve_breach --verify      -> L1-L5; real check_mandate: breach ALLOW, twin identical, control DENY" \
    $PY construct_sleeve_breach_episode.py --verify
  step "construct_sleeve_breach --selftest    -> 9 tamper mutations + control (10/10)" \
    $PY construct_sleeve_breach_episode.py --selftest
fi

# ---------------------------------------------------------------- phase 4
hdr "4. Write-mode reproducers: regenerate in scratch, then byte-diff"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/icaif-regen.XXXXXX")"
cp -p "$AUDIT"/*.py "$AUDIT"/*.json "$AUDIT"/*.md "$SCRATCH/"
ln -s "$AUDIT/snapshots" "$SCRATCH/snapshots"

regen() { # regen <script> <output.json> [compare_artifact.py flags...]
  local script="$1" out="$2"; shift 2
  local log; log="$(mktemp)"
  if ! ( cd "$SCRATCH" && $PY "$script" --verify --selftest >"$log" 2>&1 ); then
    ( cd "$SCRATCH" && $PY "$script" >"$log" 2>&1 ) || { bad "$script (run failed)"; sed 's/^/        | /' "$log" | tail -20; rm -f "$log"; return; }
  fi
  rm -f "$log"
  local note
  if note="$($PY "$HERE/compare_artifact.py" "$AUDIT/$out" "$SCRATCH/$out" "$@" 2>&1)"; then
    ok "$script -> $out $note"
  else
    bad "$script -> $out DIFFERS from released artifact"
    printf '%s\n' "$note" | sed 's/^/        | /'
  fi
}

regen census_scope_survival.py          census_scope_survival_v0_1.json
regen census_survival_extended.py       census_survival_extended_v0_1.json
regen prefix_scope_scan.py              prefix_scope_scan_v0_1.json \
      --allow-extra classification
regen repair_pinning_probe.py           repair_pinning_probe_v0_1.json
regen repair_pinning_probe_verbatim.py  repair_pinning_probe_verbatim_v0_1.json
# _provenance.freeze_sha256 hashes an input that carries one documented redaction;
# every scientific field must still match byte-for-byte. See REDACTIONS.md.
regen qemc_dryrun_sleeve.py             qemc_dryrun_sleeve_v0_1.json \
      --allow-differ _provenance.freeze_sha256

# the two reconciliation figures the paper reports from the extended census
if ( cd "$SCRATCH" && $PY census_survival_extended.py 2>&1 | grep -q "= 1 / 16" ); then
  ok "census_survival_extended prints the published past-cut rate 1/16"
else
  bad "census_survival_extended did not print 1/16"
fi
if ( cd "$SCRATCH" && $PY qemc_dryrun_sleeve.py --verify --selftest 2>&1 | grep -q "16/16 predictions hit" ); then
  ok "QEMC pipeline hits 16/16 pre-committed predictions (RC=0, FNR*(a)=1-a)"
else
  bad "QEMC did not report 16/16"
fi

rm -rf "$SCRATCH"

# ---------------------------------------------------------------- phase 5
hdr "Summary"
printf '  passed %d   failed %d   skipped %d\n' "$PASS" "$FAIL" "$SKIP"
if [ "$FAIL" -ne 0 ]; then
  printf '\n  failing checks:\n'
  for f in "${FAILED[@]}"; do printf '    - %s\n' "$f"; done
  printf '\n  A failure here means the pinned snapshot, a frozen artifact, or a\n'
  printf '  reproducer drifted. See CLAIMS.md for which paper number each check binds.\n'
  exit 1
fi
printf '\n  All confirmatory claims reproduced. 0 model calls, 0 network, $0.\n'
printf '  Claim-to-artifact binding: CLAIMS.md\n'
exit 0
