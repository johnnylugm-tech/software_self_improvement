# Dimension Evaluation Prompt

Applied once per **enabled** dimension, per round. Produces a scored JSON object Claude writes to `.sessi-work/scores/<dimension>.json`.

## Output shape

```json
{
  "dimension": "<name>",
  "score": 0,
  "findings": ["specific issue 1", "specific issue 2"],
  "gaps": ["what prevents a higher score"],
  "tool_outputs": {"<tool-name>": "<raw or summarised output>"}
}
```

`score` is an integer in `[0, 100]`. Findings are concrete (file:line when possible). Gaps are prescriptive ("add integration tests for UserService.update").

## Protocol

### 1. Run configured tools first

Iterate `dimensions.<name>.tools` from the resolved config. For each tool, detect whether the target project supports it (file markers below). If yes, invoke via Bash, capture stdout+stderr, and parse.

| Tool | Project markers | Example invocation |
|---|---|---|
| eslint | `package.json`, `.eslintrc*` | `npx eslint . --format json` |
| prettier | `.prettierrc*` | `npx prettier --check .` |
| ruff | `pyproject.toml`, `ruff.toml` | `ruff check . --output-format json` |
| flake8 | `setup.cfg`, `.flake8` | `flake8 --format=json .` |
| golangci-lint | `go.mod` | `golangci-lint run --out-format json` |
| tsc | `tsconfig.json` | `npx tsc --noEmit` |
| mypy | `pyproject.toml`, `mypy.ini` | `mypy . --no-error-summary` |
| pyright | `pyrightconfig.json` | `pyright --outputjson` |
| pytest-cov | `pyproject.toml`, `pytest.ini` | `pytest --cov --cov-report=json` |
| jest | `package.json` jest entry | `npx jest --coverage --json` |
| vitest | `vitest.config.*` | `npx vitest run --coverage` |
| go-cover | `go.mod` | `go test ./... -coverprofile=c.out && go tool cover -func=c.out` |
| bandit | `pyproject.toml` / python files | `bandit -q -r . -f json` |
| semgrep | any | `semgrep --config auto --json` |
| trivy | Dockerfile / deps | `trivy fs --format json .` |
| gitleaks | any | `gitleaks detect --no-banner --report-format json` |
| radon-cc | python | `radon cc -s -j .` |
| radon-mi | python | `radon mi -j .` |
| interrogate | python | `interrogate -q -f 0` |

Store each tool's parsed summary into `tool_outputs`. Don't fail the round if a tool isn't installed — just note it and move on.

### 2. Mechanical sub-score (tool-driven)

Apply the mapping for the dimension. Clamp to `[0, 100]`.

- **linting**: `100 − min(errors × 3 + warnings, 100)`
- **type_safety**: `100 − min(type_errors × 4, 100)`; +5 if strict mode is on
- **test_coverage**: average of `statement_pct`, `branch_pct`, `function_pct`; if only one metric is available, use it
- **security**: `100 − min(critical × 20 + high × 10 + medium × 3 + low × 1, 100)`
- **performance**: `100 − min(functions_over_max_cyclomatic_complexity × 5, 100)`
- **readability**: `radon_mi` (0–100 scale); penalise −5 per file exceeding `max_file_lines`, −3 per function exceeding `max_function_lines`
- **documentation**: `interrogate_coverage_pct` (if available)
- **architecture**: no mechanical tool — LLM-only
- **error_handling**: no mechanical tool — LLM-only

### 3. LLM sub-score (Claude judgement)

For `architecture` and `error_handling`, and as a sanity check on every dimension, read 5–15 representative files (entry points, services/controllers, shared utilities, tests). Start from 100 and subtract per distinct systemic issue:

- Minor (stylistic, single-file): −3
- Moderate (pattern repeated in a few files): −8
- Severe (affects a whole module or crosses layers): −15
- Critical (breaks a principle the framework names): −25

Dimension criteria:

- **linting** — formatting compliance, unused vars/imports, unreachable/dead code, deprecated APIs
- **type_safety** — implicit `any`, missing annotations, `@ts-ignore` / `# type: ignore` prevalence, nullable handling
- **test_coverage** — meaningful tests (not smoke), critical-path coverage, happy + error cases
- **security** — hardcoded secrets, missing input validation, SQLi/XSS vectors, weak authn/authz, vulnerable deps
- **performance** — N+1, unbounded loops, missing caching, hot-path allocations, function complexity > 10
- **architecture** — separation of concerns, SOLID, cyclic deps, DRY, layering
- **readability** — naming, function length ≤ 50, nesting ≤ 4, file length ≤ 800, comment/docstring quality on tricky blocks
- **error_handling** — swallowed exceptions, over-broad `except Exception` / `catch (e)`, uninformative messages, propagation
- **documentation** — public API docs present, README accurate, architecture docs, runnable examples

### 4. Reconcile

Final score:

- If both mechanical and LLM sub-scores exist and diverge by > 15 → take the **minimum** (pessimistic, matches "no hidden regressions").
- If only one exists → use it.
- Clamp to `[0, 100]`.

### 5. Aggregate

After every enabled dimension has produced its JSON, assemble `.sessi-work/scores.json` as `{dimension_name: final_score_int}` for `score.py`.
