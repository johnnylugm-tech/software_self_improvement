# Round Verification Prompt (Anti-Self-Deception)

Runs AFTER the improve phase and its re-evaluate, BEFORE the early-stop check. Its job: make score increases **earn themselves** with evidence. Without this step, the same agent that modified the code also re-scores it, and scores drift upward without real gain.

## Inputs

For round `n`:

- `.sessi-work/round_<n-1>/result.json` — PRE-round scores (baseline if `n = 1`)
- `.sessi-work/round_<n>/result.json` — POST-round scores (fresh from `score.py`)
- `.sessi-work/round_<n-1>/tools/` — raw tool outputs BEFORE (one `<dim>.txt` per enabled dimension)
- `.sessi-work/round_<n>/tools/` — raw tool outputs AFTER
- Git tag `round_<n>_start` on TARGET_PATH, placed at the start of the improve phase
- `HEAD` on TARGET_PATH after improvements

## Protocol

### 1. Run the deterministic check

```bash
python scripts/verify.py \
  --pre  .sessi-work/round_<n-1>/result.json \
  --post .sessi-work/round_<n>/result.json \
  --target "$TARGET_PATH" \
  --pre-tools  .sessi-work/round_<n-1>/tools \
  --post-tools .sessi-work/round_<n>/tools \
  --ref-from round_<n>_start --ref-to HEAD \
  > .sessi-work/round_<n>/verified.json
```

`verify.py` caps any dimension whose claimed `+delta > 10` has **no** material tool-output change AND **no** git diff on dimension-relevant paths. It also surfaces regressions.

### 2. LLM cross-check on capped dimensions

For each dimension in `verified.verification.capped`:

- If you believe the cap is wrong, **produce concrete evidence**:
  - Specific `file:line` change, quoting the before and after code.
  - The exact command and the tool output you just re-ran.
  - A new file path that the heuristic missed.
- If evidence holds: manually edit `.sessi-work/round_<n>/verified.json` to restore the score and note the restoration under a new `restored` array in `verification`.
- If you cannot produce such evidence within 3 minutes, accept the cap.

**Rules:**
- Do not argue against caps with prose. Only code/tool evidence overturns them.
- Do not restore more than one dimension per round without surfacing the pattern to the user — it likely means the evidence heuristics need a config tweak.

### 3. Regression handling

For each item in `verified.verification.regressions`:

1. Re-run that dimension's primary tool once to confirm the regression is not transient (flaky test, cache miss, etc.).
2. If confirmed, identify the commit that caused it with `git -C "$TARGET_PATH" log round_<n>_start..HEAD --oneline` and inspect diffs.
3. Revert just that commit: `git -C "$TARGET_PATH" revert --no-edit <sha>`
4. Re-run `score.py` → re-run `verify.py`.
5. Record the revert in the round markdown report under a `reverts` subsection.

### 4. Use verified result for early-stop and checkpoint

Downstream (`checkpoint.py`, early-stop check, `FINAL.md`) **must** read `verified.json`, not the raw `result.json`.

```bash
python scripts/checkpoint.py --round <n> \
  --result .sessi-work/round_<n>/verified.json \
  --reports-dir reports --out reports/round_<n>.md
```

If the raw post passed but the verified result doesn't meet targets, the loop **continues**. Never early-stop on unverified gains.

## Failure modes this catches

| Pattern | How verify.py catches it |
|---|---|
| `test_coverage` 65 → 82 with no new test files | no path evidence under `test/`/`.test.`/... → capped to 68 |
| `security` 70 → 90 with no dep bumps and no auth/crypto diffs | no path evidence under `package-lock.json`/`auth`/... → capped to 73 |
| `type_safety` 72 → 88 with no annotations added and no `strict` flag | no diff on `.ts`/`.py`/`tsconfig.json` → capped to 75 |
| `documentation` 60 → 85 with READMEs unchanged | no diff on `.md`/`docs/` → capped to 63 |
| Silent regression of one dim while improving another | listed in `regressions` → triggers revert protocol |

## Why a deterministic check first

The LLM is the biased party here — asking it to audit itself doesn't remove the bias. `verify.py` uses only: raw tool output diffs, git file changes, dimension-relevant path markers. It cannot be talked out of a cap; only new evidence from a fresh tool run can.
