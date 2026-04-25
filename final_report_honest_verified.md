# Quality Improvement Report

**Project:** `repo`
**Generated:** 2026-04-26 00:18:27
**Overall Score:** 81.0 / 100 (gate: 85)
**Recommendation:** ❌ **FAIL**

## 1. Summary Statistics

| Metric | Count |
|--------|------:|
| Total issues found | 3 |
| Fixed | 2 |
| Wontfix (accepted risk) | 0 |
| Deferred | 0 |
| Still open | 1 |

### By Severity

| Severity | Found | Still Open |
|----------|------:|-----------:|
| 🔴 Critical | 2 | 1 |
| 🟠 High     | 1 | 0 |
| 🟡 Medium   | 0 | 0 |
| 🔵 Low      | 0 | 0 |
| ⚪ Info     | 0 | 0 |

## 2. Score Trajectory

| Dimension | R1 | Δ |
|---|---|---|
| architecture | 90 | +0 |
| documentation | 90 | +0 |
| error_handling | 85 | +0 |
| license_compliance | 100 | +0 |
| linting | 100 | +0 |
| mutation_testing | 50 | +0 |
| performance | 90 | +0 |
| readability | 95 | +0 |
| secrets_scanning | 100 | +0 |
| security | 100 | +0 |
| test_coverage | 27 | +0 |
| type_safety | 85 | +0 |
| **Overall** | **81.0** | **+0.0** |

## 3. Per-Dimension Breakdown

| Dimension | Found | Fixed | Wontfix | Deferred | Open |
|-----------|------:|------:|--------:|---------:|-----:|
| license_compliance | 1 | 1 | 0 | 0 | 0 |
| linting | 1 | 1 | 0 | 0 | 0 |
| test_coverage | 1 | 0 | 0 | 0 | 1 |

## 4. Issues Fixed

### license_compliance

| ID | Severity | Location | Issue | Commit | Files Changed |
|----|----------|----------|-------|--------|---------------|
| `49400795bf` | 🔴 critical | `` | Missing LICENSE file | `Added LI` | — |

### linting

| ID | Severity | Location | Issue | Commit | Files Changed |
|----|----------|----------|-------|--------|---------------|
| `ac56669d35` | 🟠 high | `` | Suboptimal syntax (E702/F841) | `Ruff fix` | — |

## 5. Accepted Risks

_No issues were consciously deferred or marked wontfix._

## 6. Still Open

Issues that were found but neither fixed nor explicitly accepted as risk.
These drive the recommendation toward `partial`.

| ID | Severity | Dimension | Location | Issue |
|----|----------|-----------|----------|-------|
| `da7775bbad` | 🔴 critical | test_coverage | `` | Inadequate Test Coverage (22%) |

## 7. Evidence Trail

### Recent Commits
```
fa9eac7 chore: implement mock testing and professional evaluation flow
2308f1e chore: remove process artifacts from version control
8aa9bc1 chore: repository hygiene - cleanup artifacts and add .gitignore
e0cfa57 chore: initial quality improvement (linting, license, core tests, documentation)
c79f94e feat(anti-bias): implement 5 new defenses (v3.1) — 7-layer → 12-layer
9c642c5 fix: audit fixes — tool count 22→24, add get_architecture_overview, explicit degradation warning
8db4a49 docs: add CRG_DEEP_INTEGRATION.md — complete workflow reference
6e10f96 feat: deep CRG integration — structured metrics + score sub-scores
c3e2ebd fix: clarify blast_radius base semantics — per-fix vs per-round
dcc8f12 fix: audit P0/P1/P2 — runtime bug, contradictions, stale numbers
6ed984e feat: deep CRG integration — reconnaissance phase + 20/27 MCP tools
e7f6bdf docs: remove manual 'code-review-graph build' — now auto by setup_target.py
760e042 feat: CRG auto-detect, auto-build, transparent status at session start
8f6a09e docs: Clarify CRG auto-detection scope and git commit timing
09f47b2 audit: Fix 7 critical + 4 high/medium documentation errors
0be7676 feat: Model selection via env vars + explicit model names in config
579cb9c docs: Clarify install-once vs subsequent runs for tools & CRG
eec53d4 docs: Add Code Review Graph integration section to README.md
30f4506 docs: Clarify Harness Engineering base model reference (extended from 9 to 12+5)
0499c04 audit: Fix dimension count across all docs (12 core + 5 extended, not 9 + 7)
```

### Round Artifacts
- Round 1: `/Users/johnny/Projects/harness-work/software-self-improvement/round_1` (result.json)
