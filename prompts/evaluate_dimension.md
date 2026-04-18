# Dimension Evaluation Prompt

Applied once per **enabled** dimension, per round. Produces a scored JSON object Claude writes to `.sessi-work/round_<n>/scores/<dimension>.json`, plus raw tool output to `.sessi-work/round_<n>/tools/<dimension>.txt`.

## CRITICAL: Tool-first hierarchy (anti-self-deception)

The same agent that will edit code also scores it. To stop the scoring drift this invites:

1. **Tool scores are canonical** for every dimension that has a usable static analyser. Run the tool, derive a score from its output, record it. LLM judgement only **supplements** tool scores — it cannot override them upward.
2. **Reconcile rule**: `final_score = min(tool_score, llm_score)` when both exist. If they diverge by more than 15, prefer the tool score. LLM-only score is used only when no tool ran (architecture, error_handling, or tool install failure).
3. **Evidence requirement**: every `findings` entry and every score claim must cite concrete evidence — a tool output line, a `file:line` reference, or a quoted code fragment. No vibes-based scoring.
4. **Persist raw tool output** to `.sessi-work/round_<n>/tools/<dimension>.txt`. The verify step reads these to detect artificial gains in later rounds.

## Output shape

```json
{
  "dimension": "<name>",
  "score": 0,
  "tool_score": 0,
  "llm_score": 0,
  "findings": [
    {"severity": "high|med|low", "evidence": "file.ts:45 — unused import 'foo'"}
  ],
  "gaps": ["prescriptive next-step, e.g. 'add integration tests for UserService.update'"],
  "tool_outputs": {"<tool>": "<raw summary or path to raw file>"},
  "reconcile": "chose tool (tool=82 vs llm=90)"
}
```

`score` is an integer in `[0, 100]`. `tool_score` is `null` if no tool ran. `llm_score` is `null` if tool coverage was complete and LLM judgement wasn't needed.

## Protocol

### 1. Run configured tools first

Iterate `dimensions.<name>.tools`. For each, detect project support (markers below). If yes, run via Bash, **tee stdout+stderr into `.sessi-work/round_<n>/tools/<dimension>.txt`**, and parse.

| Tool | Project markers | Invocation |
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
| bandit | python | `bandit -q -r . -f json` |
| semgrep | any | `semgrep --config auto --json` |
| trivy | Dockerfile / deps | `trivy fs --format json .` |
| gitleaks | any | `gitleaks detect --no-banner --report-format json` |
| radon-cc | python | `radon cc -s -j .` |
| radon-mi | python | `radon mi -j .` |
| interrogate | python | `interrogate -q -f 0` |

A missing tool is not a failure — note it in `tool_outputs` and fall through to LLM-only. A failing tool run (non-2 exit code) **does** count; record its output and use a neutral `tool_score = 50` rather than inventing one.

### 2. Mechanical sub-score (tool-driven)

Apply the mapping, clamp to `[0, 100]`.

- **linting**: `100 − min(errors × 3 + warnings, 100)`
- **type_safety**: `100 − min(type_errors × 4, 100)`; `+5` if strict mode is on
- **test_coverage**: average of `statement_pct`, `branch_pct`, `function_pct` (use whichever are available)
- **security**: `100 − min(critical × 20 + high × 10 + medium × 3 + low × 1, 100)`
- **performance**: `100 − min(functions_over_max_cyclomatic_complexity × 5, 100)`
- **readability**: radon MI (0–100 scale); penalise −5 per file over `max_file_lines`, −3 per function over `max_function_lines`
- **documentation**: interrogate coverage %
- **architecture**: no mechanical tool — `tool_score = null`
- **error_handling**: no mechanical tool — `tool_score = null`

Record `tool_score` in the output.

### 3. LLM sub-score (with evidence)

Required for: `architecture`, `error_handling`.
Useful as supplement for: all others.

Read 5–15 representative files (entry points, services/controllers, shared utilities, tests). Start from 100 and subtract per **distinct systemic issue, each with a concrete file:line citation**:

- Minor (stylistic, single-file): −3
- Moderate (pattern in a few files): −8
- Severe (affects a module, crosses layers): −15
- Critical (breaks a named principle): −25

Every deduction must appear in `findings` with its `evidence` field. A deduction without evidence is invalid and must be removed.

Dimension criteria: see `docs/DIMENSIONS.md`.

### 4. Reconcile (strict)

```
if tool_score is None:       final = llm_score
elif llm_score is None:      final = tool_score
else:                        final = min(tool_score, llm_score)
```

The `reconcile` field in the output records which branch was taken. **Never** output `final > tool_score` when a tool ran — that's the drift this rule exists to prevent.

### 5. Aggregate

After every enabled dimension has produced its JSON:

1. Write `.sessi-work/round_<n>/scores.json` as `{dimension_name: final_score_int}` for `score.py`.
2. Confirm `.sessi-work/round_<n>/tools/<dim>.txt` exists for every dim that had a tool run — the verify step needs these.
