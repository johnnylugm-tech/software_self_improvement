# Improvement Plan Protocol

Plan and execute fixes for failing dimensions. Always uses **Claude native** — code modification requires full reasoning capability.

---

## Step 1: Load Verified Scores

```bash
# Use verified.json (output of verify.py), NOT raw scores
cat .sessi-work/round_<n>/verified.json | python3 scripts/score.py round_<n> config.json
```

Load `failing_dimensions` sorted by impact (gap × weight).

---

## Step 2: Prioritize Fixes

For each failing dimension, evaluate fixability:

| Category | Fix Strategy | Max fixes/dim |
|----------|-------------|--------------|
| linting | Automated (run `--fix` flag) | Unlimited |
| type_safety | Semi-automated (add type hints) | 5 |
| test_coverage | Add targeted tests | 3 |
| security | Apply recommended remediation | 3 |
| secrets_scanning | Remove/rotate + add to .gitignore | All (zero tolerance) |
| license_compliance | Replace or document exceptions | 3 |
| mutation_testing | Strengthen assertions | 5 |
| architecture | Refactor (scope carefully) | 1-2 |
| readability | Rename + extract | 3 |
| error_handling | Add specific exception handlers | 5 |
| documentation | Add docstrings | 5 |
| performance | Optimize hotspots only | 2 |

**Guardrails (never do):**
- Do NOT remove test assertions to make tests pass
- Do NOT broaden `except Exception` → bare `except:`
- Do NOT add `@ts-ignore`, `# type: ignore`, `# noqa`
- Do NOT refactor architecture without explicit user approval
- Do NOT add logging that hides errors

---

## Step 3: Per-Fix Verification Loop

For each planned fix:

```
1. Record pre-fix tool score:
   python3 scripts/llm_router.py <dimension>  → check tier
   Run tool → save baseline score

2. Apply fix (minimal, targeted change)

3. Re-run tool immediately:
   Same tool command as Step 1

4. Compare scores:
   IF new_score > old_score: keep change, commit
   IF new_score <= old_score: git revert, try next fix

5. Commit kept fix:
   git add <changed_files>
   git commit -m "fix(<dimension>): <description> [auto-research]"
```

**One commit per fix.** Never batch multiple fixes into one commit.

---

## Step 4: Tier-Aware Fix Verification

For **Tier 1/2 dimensions** (linting, type_safety, etc.):
- Tool output is ground truth — re-run tool to verify
- Do NOT use Gemini to verify fixes (use tool output directly)

For **Tier 3 dimensions** (architecture, readability, etc.):
- Use tool where available (radon, pydocstyle)
- Claude judgment for subjective dimensions — but require concrete evidence

---

## Step 5: Deferred Fixes

Some fixes are out of scope for auto-research:
- Major API redesign
- Database schema changes
- Security architecture overhaul (requires human review)
- Business logic correctness (no automated way to verify)

Log these in `.sessi-work/round_<n>/deferred_fixes.md`:
```markdown
## Deferred Fixes

- [architecture] Split monolithic `UserService` into separate auth/profile modules
  Reason: Requires architectural decision beyond automated scope
```

---

## Output

After all fixes applied and verified:
```bash
python3 scripts/checkpoint.py round <n> scores.json <overall_score>
```

Proceed to verify_round.md for cross-dimension regression check.
