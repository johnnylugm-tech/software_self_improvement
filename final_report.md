# Quality Improvement Report

**Project:** `repo`
**Generated:** 2026-04-26 00:11:43
**Overall Score:** 0.0 / 100 (gate: 85)
**Recommendation:** 🟡 **PARTIAL**

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

_No round data._

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

_No rounds recorded._
