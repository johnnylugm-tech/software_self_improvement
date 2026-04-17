# Quality Dimensions

The 9 default dimensions come from the Harness Engineering Framework. Each has a weight, a target, and a set of tools. When a dimension is disabled, its weight is redistributed across the remaining enabled dimensions (proportional renormalisation).

## The 9 dimensions

| # | Dimension | Default weight | Default target | Primary tools |
|---|---|---|---|---|
| 1 | linting | 0.10 | 85 | eslint, ruff, flake8, prettier, golangci-lint |
| 2 | type_safety | 0.15 | 85 | tsc, mypy, pyright |
| 3 | test_coverage | 0.20 | 85 | pytest-cov, jest, vitest, go-cover |
| 4 | security | 0.15 | 85 (commonly overridden to 90–95) | bandit, semgrep, trivy, gitleaks |
| 5 | performance | 0.10 | 85 | radon-cc + heuristics |
| 6 | architecture | 0.10 | 85 | LLM judge |
| 7 | readability | 0.10 | 85 | radon-mi, eslint-complexity |
| 8 | error_handling | 0.05 | 85 | LLM judge |
| 9 | documentation | 0.05 | 85 | interrogate, LLM judge |

## Scoring formula

```
overall_score = Σ(dim_score × normalized_weight)
```

Where `normalized_weight = raw_weight / Σ(raw_weights of enabled dims)`.

A dimension "meets target" iff `dim_score ≥ dim_target`. The overall "meets target" iff `overall_score ≥ overall_target` **and** every enabled dimension meets its own target — the skill never counts a run as passing while any enabled dimension is below its target, regardless of overall.

## Per-dimension detail

### 1. Linting & Code Style (10%)
Formatting compliance, unused vars/imports, unreachable code, deprecated APIs. Mechanical fixes from `eslint --fix`, `ruff --fix`, `prettier --write` are applied automatically in the improvement phase.

### 2. Type Safety (15%)
Implicit `any`, missing annotations, `@ts-ignore` / `# type: ignore` prevalence, nullable handling. Strict mode earns a bonus.

### 3. Test Coverage (20%)
Weighted highest because it directly evidences correctness. Averages statement/branch/function coverage when multiple are available. The improvement phase generates tests for already-specified behaviour only — never fakes assertions.

### 4. Security (15%)
Hardcoded secrets, input validation, SQLi/XSS, weak authn/authz, vulnerable deps. Commonly overridden to target 90+ for regulated systems.

### 5. Performance (10%)
N+1 patterns, missing caching, cyclomatic complexity > `max_cyclomatic_complexity`, hot-path allocations.

### 6. Architecture & Design (10%)
Separation of concerns, SOLID, cyclic module deps, DRY, layering. No cheap static tool — scored via LLM judgement against 5–15 representative files.

### 7. Readability & Maintainability (10%)
Naming, function length (≤ `max_function_lines`), nesting depth (≤ `max_nesting_depth`), file length (≤ `max_file_lines`), comments on tricky blocks. Scored primarily from radon MI when available.

### 8. Error Handling (5%)
Swallowed exceptions, overly broad catches, uninformative messages, propagation across layers. LLM-judged.

### 9. Documentation (5%)
Public API docs, README accuracy, architecture docs, runnable examples. Scored primarily from `interrogate` (Python) plus LLM pass on READMEs and top-level docs.

## Customising

You can:

- disable a dimension (`dimensions.<name>.enabled: false`)
- override its weight (`dimensions.<name>.weight: 0.05`)
- override its target (`dimensions.<name>.target: 95`)
- add or remove tools from its `tools` list

Weights need not sum to 1 — they're normalised across enabled dims automatically.
