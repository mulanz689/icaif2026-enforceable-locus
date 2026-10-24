# Third-party notices

## HKUDS/Vibe-Trading (vendored subset)

`audit/snapshots/Vibe-Trading/` contains a **subset** of

> Vibe-Trading: https://github.com/HKUDS/Vibe-Trading
> commit `dddf96e35d511328b44a4307df0fb1cf49433e8d`
> Copyright (c) 2026 Vibe-Trading Contributors. MIT License

redistributed under the MIT license, with the upstream `LICENSE`, `NOTICE`, `README.md`
and `pyproject.toml` preserved in place inside that directory.

### What is vendored, and why

The paper is a **pin-scoped structural audit**: its result is a property of these exact
bytes. A fetch-at-run-time design would make the artifact depend on a remote repository
remaining reachable and unrewritten, and would silently break the one property the paper
most needs, that the audited tree cannot drift. The subset is therefore vendored, and
`PIN_MANIFEST.sha256` records a sha256 for every one of the 1,202 files.
`verify_pin.py` refuses to proceed on any mismatch, and
`verify_pin.py --against <clone>` diffs the vendored bytes against a fresh upstream
checkout at the pin for anyone who wants the independent confirmation.

Vendored:

| Path | Contents | Used by |
|---|---|---|
| `agent/src/skills/` | the 88 bundled skills, including the anchor `social-media-intelligence/SKILL.md` | every census and probe |
| `agent/src/agent/frontmatter.py` | the real frontmatter parser | all probes (never reimplemented) |
| `agent/src/agent/skills.py`, `loop.py`, `context.py` | the wrap / truncate / deliver path and its asserted line spans | probes, witness constructor |
| `agent/src/tools/load_skill_tool.py` | the serialization step | probes |
| `agent/src/live/enforcement.py`, `agent/src/live/mandate/` | `check_mandate`, `OrderIntent`, the eleven verdict planes | witness constructor, env-card validator |
| the rest of `agent/src/` | import closure needed to load the guard module tree | — |
| `agent/SKILL.md`, `LICENSE`, `NOTICE`, `README.md`, `pyproject.toml` | attribution and dependency reference | — |

Not vendored: `assets/`, `wiki/`, `frontend/`, `agent/tests/`, `agent/cli/`,
`agent/backtest/`, and the upstream `.git` directory. None is touched by any reproducer.

The vendored files are **unmodified**. No reproducer writes inside
`audit/snapshots/`; the position-only repair in §5.6 builds its variant in memory and
asserts the snapshot bytes are untouched.

### Upstream NOTICE

The upstream `NOTICE` records that Vibe-Trading itself bundles Microsoft Qlib feature
definitions under Apache 2.0 and reimplements published factor formulas as mathematical
content. Those files live under `agent/src/factors/` and are present here only as part of
the import closure. See `audit/snapshots/Vibe-Trading/NOTICE` and the per-directory
`LICENSE.md` files it points to.

## A second repository that is *not* included

The original negative-scope lexical screen scanned a second agent repository in the same
pass. The paper makes no claim about it, it appears in no table, and its repository ships
no license file, so neither that repository nor that screen script is redistributed here.
The Vibe-Trading side of the screen, which is what the paper reports (7/88 and ≥8/88, with
identical skill names), is reproduced from the licensed snapshot alone by
`audit/census_truncation_88.py`. See `CLAIMS.md`, caveat C4.

## Python dependencies

`pandas` is required only because the upstream guard module tree imports it. See
`requirements.txt`.
