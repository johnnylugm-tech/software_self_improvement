# Improvement Planning Prompt

Applied at the end of any round where `meets_target` is false and more rounds remain.

## Inputs

- `.sessi-work/result.json` — full score.py output, including `failing_dimensions` (already sorted by impact on overall).
- `TARGET_PATH` — the codebase under improvement.
- The per-dimension findings and gaps written by the evaluator.
- Remaining round budget.

## Protocol

### 1. Rank & pick

Take `failing_dimensions` in order (already sorted by `impact = gap × normalized_weight`). Within each failing dimension, pick at most **3** fixes that most strongly address its `findings`/`gaps`.

Stop adding fixes once the **estimated** overall gain ≥ (overall_target − overall_score) + 2. No point over-fixing in one round when rounds remain.

### 2. Prefer mechanical wins first

In this order:

1. Auto-fixable lint/format: `eslint --fix`, `ruff --fix`, `prettier --write`, `gofmt`.
2. Missing-but-inferrable type annotations.
3. Missing tests for already-specified behaviour (derive from existing specs/docs/READMEs).
4. Documented security patches (upgrade pinned deps flagged by bandit/semgrep/trivy; parameterise obvious SQL; escape obvious XSS).
5. Refactor functions with cyclomatic complexity > threshold by extracting helpers (behaviour-preserving).
6. Add explicit error handling at documented boundary points.
7. Fill README / docstring gaps with content verifiable from the code itself.

### 3. Defer design-level changes

If a fix requires a design decision the user hasn't authorised (schema change, API break, new dependency, new service), **do not apply it**. Record it under `deferred` in the round markdown report and move on. Round-over-round progress > a single-round hero push.

### 4. Apply

- Use Edit / Write / Bash **only** on files inside `TARGET_PATH`.
- Never modify: the skill's own `scripts/`, `prompts/`, `config.example.yaml`, or anything in `.sessi-work/` except the round's work files.

### 5. Verify forward progress

After each distinct fix (or small group), re-run the dimension's primary fast tool (< 10s). If the tool regresses compared to the pre-fix state, revert that fix and try an alternative.

### 6. Commit

If `git.commit_per_round: true` and target is a git repo:

```bash
git -C "$TARGET_PATH" add -A
git -C "$TARGET_PATH" commit -m "round <n>: quality improvements (<primary failing dim>)"
```

Never `git push` unless `git.push: true` AND the user has explicitly authorised pushing in this session.

## Guardrails

- **Never weaken tests** to inflate coverage. Add real tests.
- **Never broaden exception handling** to silence errors for the error_handling dimension.
- **Never add `# type: ignore` or `@ts-ignore`** to inflate type safety — fix the underlying type.
- **Never delete files** outside an explicit deduplication plan surfaced as a finding.
- If a single dimension is catastrophically low (< 40) and cannot reach target in one round without design-level changes, aim for **+20 points** this round and defer the rest.
