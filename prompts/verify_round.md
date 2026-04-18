# Verify Round Protocol

Cross-check all dimension scores after improvements. Detect regressions and cap unsupported claims.

---

## Step 1: Run Deterministic Verification

```bash
python3 scripts/verify.py \
  .sessi-work/round_<n>/result.json \
  .sessi-work/round_<n> \
  <repo_path>
```

Read the output:
- `verification.capped[]` — dimensions where claims were capped
- `verification.regressions[]` — dimensions that got worse
- `verified: true/false` — overall pass/fail

**Use `verified.json` for all downstream steps. Never use raw `result.json`.**

---

## Step 2: Handle Capped Dimensions

For each entry in `capped[]`:

```
IF cap occurred (claim > EVIDENCE_THRESHOLD without diff evidence):
  → Accept the capped score (lower value)
  → Log: "Score capped from {claim} to {capped_to}: insufficient evidence"
  → Do NOT re-run improvements for this dimension this round
```

The capped score is the correct score for this round.

---

## Step 3: Handle Regressions

For each entry in `regressions[]`:

```
dimension_name: { before: X, after: Y, delta: -Z }

Actions:
1. Identify which fix caused the regression (git log --oneline -5)
2. IF fix is identifiable AND revert is safe:
   git revert <commit_hash> --no-edit
   Re-run dimension tool to confirm revert worked
3. IF regression is acceptable trade-off (e.g., security fix breaks a flaky test):
   Document in .sessi-work/round_<n>/deferred_fixes.md
   Keep regression, flag for human review
4. Update verified.json with post-revert scores
```

---

## Step 4: LLM Cross-Check (Tier 3 only)

For each **Tier 3** dimension (architecture, readability, error_handling, documentation, performance):

Perform a brief sanity check:
- Does the claimed improvement match what was actually changed?
- Any obvious regression not caught by tools?

This is a lightweight 1-paragraph check per dimension, not a full re-evaluation.
Use Claude native (no Gemini for this step — judgment required).

---

## Step 5: Final Round Score

After verification and any reverts:

```bash
python3 scripts/score.py .sessi-work/round_<n> config.json > .sessi-work/round_<n>/final_score.json
```

Check `meets_target`:
- `true` → trigger early-stop check in SKILL.md Step 3e
- `false` → continue to next round (if rounds remaining)

---

## Output Files

```
.sessi-work/round_<n>/
├── result.json          ← raw (do not use downstream)
├── verified.json        ← verified scores (use this)
├── final_score.json     ← post-verification overall score
└── deferred_fixes.md    ← items requiring human attention
```
