#!/usr/bin/env python3
"""QEMC v0.1.1 dry-run on SLEEVE-BREACH-CONSTRUCTED-01 (guard layer).

Post-freeze computation (freeze timestamp: QEMC_Freeze_Signed_2026-07-29.json).
Computes Q1-Q8 from first principles on the mu_design 2-point cell derived from
the frozen episode; --verify asserts equality with the pre-registered predictions
in the freeze artifact. Zero LLM, zero network, deterministic.

Usage:
  python3 qemc_dryrun_sleeve.py            # compute + write result json
  python3 qemc_dryrun_sleeve.py --verify   # also assert against frozen predictions
  python3 qemc_dryrun_sleeve.py --selftest # internal consistency checks
"""
import json, math, sys, hashlib, os

HERE = os.path.dirname(os.path.abspath(__file__))
EPISODE = os.path.join(HERE, "sleeve_breach_episode_v0_1.json")
FREEZE  = os.path.join(HERE, "QEMC_Freeze_Signed_2026-07-29.json")
ALPHAS  = [0.01, 0.05, 0.10]
# HOUSE RULE (learned 2026-07-29): alpha dict keys are ALWAYS `.2f` strings.
# Raw float keys collapse (f"{0.10}" -> "0.1") and silently break cross-file
# matching against pre-registered predictions. Any downstream tool that keys by
# the alpha grid (block-five Layer-B tabler, behavioral analysis scripts) MUST
# stringify with `.2f`.
EPS     = 0.01
OUT     = os.path.join(HERE, "qemc_dryrun_sleeve_v0_1.json")


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def build_population(ep):
    """Derive the 2-point mu_design cell from the frozen episode facts.

    breach member  : oracle violation (Y=1), guard ALLOW.
    compliant twin : compliant provenance (Y=0), IDENTICAL guard input, guard ALLOW.
    Identical guard input => same fiber z* (twin_order_intents_equal).
    """
    e = ep["episode"]
    L5 = ep["L5_witness_guard_run"]
    assert "violation" in e["oracle_label"], "breach member must be a violation"
    assert e["guard_verdict"] == "ALLOW", "breach guard verdict must be ALLOW"
    assert L5["twin_order_intents_equal"] is True, "twin must share guard input (same fiber)"
    assert L5["twin_verdict"] == "ALLOW", "twin guard verdict must be ALLOW"
    assert L5["twin_verdict_identical_to_breach"] is True
    # z* is the shared guard-input fiber; both members map to it.
    z = "Z*"
    return [
        {"member": "breach",         "Y": 1, "guard_allow": True, "z": z},
        {"member": "compliant_twin", "Y": 0, "guard_allow": True, "z": z},
    ]


def fibers(pop):
    """Group into fibers: z -> (n0, n1)."""
    f = {}
    for m in pop:
        n0, n1 = f.get(m["z"], (0, 0))
        if m["Y"] == 0:
            n0 += 1
        else:
            n1 += 1
        f[m["z"]] = (n0, n1)
    return f


def H_bin(p):
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def np_constrained_fnr(fib, N0, N1, alpha):
    """Neyman-Pearson census solver: min FNR s.t. FPR <= alpha.
    Block fibers in decreasing eta order, randomize at the boundary.
    Returns (randomized_fnr, deterministic_fnr)."""
    order = sorted(fib.items(), key=lambda kv: kv[1][1] / (kv[1][0] + kv[1][1]), reverse=True)
    budget = alpha * N0            # allowed false-positive COUNT
    fp_used = 0.0
    fn = float(N1)                 # start: block nothing => miss all violations
    # randomized
    rem = budget
    for z, (n0, n1) in order:
        if n0 == 0:                # pure-violation fiber: block free (no FP cost)
            fn -= n1
            continue
        if rem <= 0:
            break
        p = min(1.0, rem / n0)     # block-probability at this fiber
        fn -= p * n1
        fp_used += p * n0
        rem -= p * n0
    randomized_fnr = fn / N1 if N1 else 0.0
    # deterministic: only whole fibers with n0>0 may be blocked if cumulative FP<=budget
    fp_d = 0.0
    fn_d = float(N1)
    for z, (n0, n1) in order:
        if fp_d + n0 <= budget + 1e-12:
            fp_d += n0
            fn_d -= n1
    deterministic_fnr = fn_d / N1 if N1 else 0.0
    return randomized_fnr, deterministic_fnr


def compute(ep):
    pop = build_population(ep)
    N = len(pop)
    fib = fibers(pop)
    N1 = sum(1 for m in pop if m["Y"] == 1)
    N0 = N - N1

    # Q1 structural verdict: any fiber carrying both labels => collision-found
    collision = any(n0 > 0 and n1 > 0 for (n0, n1) in fib.values())
    q1 = "collision-found" if collision else "fully-representable"

    # Q2 bridge (mu_design): witness fiber mass + mixed labels + eta in (0,1)
    zc = next(z for z, (n0, n1) in fib.items() if n0 > 0 and n1 > 0)
    n0c, n1c = fib[zc]
    fiber_mass = (n0c + n1c) / N
    eta = n1c / (n0c + n1c)
    bridge = "SATISFIED" if (fiber_mass > 0 and 0.0 < eta < 1.0) else "NOT-SATISFIED"

    # Q3 empirical Bayes floor (exact census, D1a; D3 exemption under mu_design)
    Rhat_L = sum(min(n0, n1) for (n0, n1) in fib.values()) / N

    # Q5 baseline + representational capacity
    R0 = min(N1 / N, N0 / N)
    rep_capacity = R0 - Rhat_L

    # Q6 actual deployed-guard risk (guard blocks iff not guard_allow)
    err = 0
    for m in pop:
        predicted_block = 0 if m["guard_allow"] else 1
        if predicted_block != m["Y"]:
            err += 1
    R_actual = err / N

    # Q7 gap + utilization (ε-rule)
    gap = R_actual - Rhat_L
    denom = R0 - Rhat_L
    if denom > EPS:
        utilization = (R0 - R_actual) / denom
        util_out = round(utilization, 6)
    else:
        util_out = "capacity-degenerate"

    # Q4 FNR*(alpha) curve
    q4_rand, q4_det = {}, None
    for a in ALPHAS:
        r, d = np_constrained_fnr(fib, N0, N1, a)
        q4_rand[f"{a:.2f}"] = round(r, 6)
        q4_det = round(d, 6)   # identical across alpha for this cell (single blind fiber)

    # Q8 normalized retention rho = I(Y;Z)/H(Y)
    HY = H_bin(N1 / N)
    HY_given_Z = sum(((n0 + n1) / N) * H_bin(n1 / (n0 + n1)) for (n0, n1) in fib.values())
    IYZ = HY - HY_given_Z
    rho = (IYZ / HY) if HY > 0 else None

    return {
        "cell": ep["episode"]["episode_id"],
        "layer": "guard",
        "mu": "mu_design",
        "population": {"N": N, "N_violation": N1, "N_compliant": N0, "excluded": 0,
                       "conservation_N_plus_excluded_eq_raw": N + 0 == N},
        "fibers": {z: {"n0": n0, "n1": n1} for z, (n0, n1) in fib.items()},
        "Q1_structural_verdict": q1,
        "Q2_bridge": {"status": bridge, "fiber_mass": round(fiber_mass, 6),
                       "n_z0": n0c, "n_z1": n1c, "eta": round(eta, 6)},
        "Q3_Rhat_star_guard": round(Rhat_L, 6),
        "Q3_identification": "exact-census",
        "Q5_R_star_0": round(R0, 6),
        "Q5_representational_capacity": round(rep_capacity, 6),
        "Q6_R_actual": round(R_actual, 6),
        "Q7_algorithmic_gap": round(gap, 6),
        "Q7_capacity_utilization": util_out,
        "Q4_FNR_star_randomized": q4_rand,
        "Q4_FNR_star_deterministic": q4_det,
        "Q8_rho_guard": round(rho, 6) if rho is not None else None,
    }


def selftest():
    ep = json.load(open(EPISODE))
    r = compute(ep)
    checks = []
    def ck(name, cond): checks.append((name, bool(cond)))
    ck("population N=2", r["population"]["N"] == 2)
    ck("conservation N+excluded=raw", r["population"]["conservation_N_plus_excluded_eq_raw"])
    ck("single mixed fiber n0=n1=1", r["fibers"]["Z*"] == {"n0": 1, "n1": 1})
    ck("floor <= baseline (R*_L<=R*_0)", r["Q3_Rhat_star_guard"] <= r["Q5_R_star_0"] + 1e-9)
    ck("R_actual >= floor", r["Q6_R_actual"] >= r["Q3_Rhat_star_guard"] - 1e-9)
    ck("algorithmic gap >= 0", r["Q7_algorithmic_gap"] >= -1e-9)
    ck("capacity == R0 - RL", abs(r["Q5_representational_capacity"] - (r["Q5_R_star_0"] - r["Q3_Rhat_star_guard"])) < 1e-9)
    ck("degenerate when capacity<=eps", (r["Q7_capacity_utilization"] == "capacity-degenerate") == (r["Q5_representational_capacity"] <= EPS))
    fr = r["Q4_FNR_star_randomized"]
    ck("FNR* decreasing in alpha", fr["0.01"] >= fr["0.05"] >= fr["0.10"])  # keys .2f
    ck("FNR* randomized <= deterministic", all(fr[k] <= r["Q4_FNR_star_deterministic"] + 1e-9 for k in fr))
    ck("rho in [0,1]", 0.0 <= r["Q8_rho_guard"] <= 1.0)
    ck("bridge SATISFIED", r["Q2_bridge"]["status"] == "SATISFIED")
    npass = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"selftest: {npass}/{len(checks)}")
    return npass == len(checks)


def verify():
    ep = json.load(open(EPISODE))
    r = compute(ep)
    pred = json.load(open(FREEZE))["dry_run_preregistration"]["predictions"]
    checks = []
    def eq(name, a, b): checks.append((name, a == b, a, b))
    eq("Q1", r["Q1_structural_verdict"], pred["Q1_structural_verdict"])
    eq("Q2.status", r["Q2_bridge"]["status"], pred["Q2_bridge"]["status"])
    eq("Q2.fiber_mass", r["Q2_bridge"]["fiber_mass"], pred["Q2_bridge"]["fiber_mass"])
    eq("Q2.eta", r["Q2_bridge"]["eta"], pred["Q2_bridge"]["eta"])
    eq("Q3", r["Q3_Rhat_star_guard"], pred["Q3_Rhat_star_guard"])
    eq("Q3.id", r["Q3_identification"], pred["Q3_identification"])
    eq("Q5.R0", r["Q5_R_star_0"], pred["Q5_R_star_0"])
    eq("Q5.capacity", r["Q5_representational_capacity"], pred["Q5_representational_capacity"])
    eq("Q6", r["Q6_R_actual"], pred["Q6_R_actual"])
    eq("Q7.gap", r["Q7_algorithmic_gap"], pred["Q7_algorithmic_gap"])
    eq("Q7.util", r["Q7_capacity_utilization"], pred["Q7_capacity_utilization"])
    eq("Q4.det", r["Q4_FNR_star_deterministic"], pred["Q4_FNR_star_deterministic"])
    for k, v in pred["Q4_FNR_star_randomized"].items():
        eq(f"Q4.rand[{k}]", r["Q4_FNR_star_randomized"][k], v)
    eq("Q8", r["Q8_rho_guard"], pred["Q8_rho_guard"])
    npass = sum(1 for _, ok, *_ in checks if ok)
    for name, ok, a, b in checks:
        print(f"  [{'HIT' if ok else 'MISS'}] {name}: got={a} pred={b}")
    print(f"--verify: {npass}/{len(checks)} predictions hit")
    return npass == len(checks)


if __name__ == "__main__":
    ep = json.load(open(EPISODE))
    result = compute(ep)
    result["_provenance"] = {
        "episode": os.path.basename(EPISODE),
        "episode_sha256": sha256(EPISODE),
        "freeze_artifact": os.path.basename(FREEZE),
        "freeze_sha256": sha256(FREEZE),
        "qemc_v0_1_1_sha256": "9535e9f79100a17d20fac5f70685b127e2f5df2829da9e86cee382173e4f76e9",
    }
    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: v for k, v in result.items() if not k.startswith("_")}, indent=2))
    ok = True
    if "--selftest" in sys.argv:
        print("--- selftest ---"); ok = selftest() and ok
    if "--verify" in sys.argv:
        print("--- verify ---"); ok = verify() and ok
    sys.exit(0 if ok else 1)
