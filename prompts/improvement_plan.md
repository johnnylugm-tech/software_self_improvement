# Improvement Planning Prompt

Applied at the end of any round where `meets_target` is false and more rounds remain.

## Inputs

- `.sessi-work/round_<n>/result.json` — latest `score.py` output including `failing_dimensions` (sorted by impact).
- Per-dimension `findings` and `gaps` from the evaluator, each with `evidence`.
- `TARGET_PATH` — the codebase under improvement.
- Remaining round budget.

## Protocol

### 0. Snapshot BEFORE any change

Place a git tag so the verify step can diff pre/post:

```bash
git -C "$TARGET_PATH" tag -f round_<n>_start
```

If TARGET_PATH isn't a git repo, initialise one first (`git init && git add -A && git commit -m "baseline"`). This is required for the anti-bias verify step.

### 1. Rank & pick

Take `failing_dimensions` in order (already sorted by `impact = gap × normalized_weight`). Within each failing dimension, pick **≤ 3** fixes that most strongly address its `findings`/`gaps`.

Stop adding fixes once the **estimated** overall gain ≥ `(overall_target − overall_score) + 2`. More rounds remain — don't over-fix in one round.

### 2. Prefer mechanical wins first

In this order:

1. Auto-fixable lint/format: `eslint --fix`, `ruff --fix`, `prettier --write`, `gofmt`.
2. Missing-but-inferrable type annotations (run the type checker; fix the exact errors it reports).
3. Missing tests for already-specified behaviour (derive from existing specs/docs/READMEs — never from tests' own assertions).
4. Documented security patches (dep bumps flagged by bandit/semgrep/trivy; parameterise obvious SQL; escape obvious XSS).
5. Refactor functions with cyclomatic complexity > threshold by extracting helpers (behaviour-preserving).
6. Explicit error handling at documented boundary points.
7. Fill README / docstring gaps with content **verifiable from the code itself** (no invented behaviour).

### 3. Defer design-level changes

If a fix requires a design decision the user hasn't authorised (schema change, API break, new dependency, new service), **do not apply it**. Record under `deferred` in the round report.

### 4. Apply & verify per fix (not per round)

For each fix:

1. Apply with Edit/Write/Bash inside `TARGET_PATH` only.
2. Stage it separately: `git -C "$TARGET_PATH" add <files>`.
3. Re-run the dimension's primary fast tool (< 10s).
4. **If the tool score regressed OR unchanged**: `git -C "$TARGET_PATH" checkout -- <files>` — revert this fix, try the next one. Log the skipped fix.
5. If the tool score improved: `git -C "$TARGET_PATH" commit -m "round <n>: <specific fix>"`.

This per-fix verification is what turns a round's delta from an LLM claim into a measured difference.

### 5. Round-level commit

After all picked fixes have been processed, every accepted fix is already its own commit. No extra rollup commit is needed. The set of commits between `round_<n>_start` and `HEAD` is exactly the round's improvements — this is what `verify.py` will diff.

## Guardrails (non-negotiable)

- **Never weaken tests** (change `assert` to `assert True`, delete failing tests, lower coverage thresholds) to inflate coverage.
- **Never broaden exception handling** (`except Exception: pass`) to silence errors for the error_handling dimension.
- **Never add `# type: ignore` / `@ts-ignore` / `// @ts-expect-error`** to inflate type safety — fix the underlying type.
- **Never delete files** outside an explicit deduplication plan surfaced as a finding.
- **Never modify** the skill's own `scripts/`, `prompts/`, `config.example.yaml`, or anything outside `TARGET_PATH`.
- **Never push** to a remote without explicit per-session user authorisation.
- If a single dimension is catastrophically low (< 40) and cannot reach target in one round without design-level changes, aim for **+20 points** this round and defer the rest.
