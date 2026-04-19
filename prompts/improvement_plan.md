# Improvement Plan Protocol (Issue-Driven)

Plan and execute fixes for **open issues in the registry**, not just failing dimensions.
Always uses **Claude native** — code modification requires full reasoning capability.

**Shift from previous version:** the priority queue is the open-issue list, not a
ranked dimension list. A dimension that hits its score target can still have open
critical/high issues — those MUST be fixed before the round is considered complete.

---

## Step 1: Load Open Issues + Verified Scores

```bash
# Verified scores (for meets_target + failing_dimensions context)
python3 scripts/score.py .sessi-work/round_<n> config.json \
  .sessi-work/issue_registry.json > .sessi-work/round_<n>/final_score.json

# The open-issue queue is the primary input:
python3 scripts/issue_tracker.py open .sessi-work/issue_registry.json \
  > .sessi-work/round_<n>/open_issues.json

# Summary counts:
python3 scripts/issue_tracker.py summary .sessi-work/issue_registry.json
```

`open_issues.json` is pre-sorted: severity ASC (critical first), then `round_found`.

---

## Step 2: Prioritize Fixes (Severity-First, Not Score-First)

Priority order is fixed by severity — dimension scores only break ties within medium/low:

```
1. ALL open critical issues      →  MUST fix (any dimension, any score)
2. ALL open high issues          →  MUST fix (any dimension, any score)
3. Open medium in failing dims   →  fix if time allows, highest impact first
4. Open medium in passing dims   →  fix only if no 1/2/3 work remains
5. Open low / info               →  batch fix or defer with reason
```

**Key rule:** if a dimension's score is already ≥ target but has open critical/high
issues, those issues still get fixed. This is the core correction over the previous
score-driven design.

### Step 2a: Cost-Benefit Triage (low-value minor issues)

Before entering the fix loop, triage **low / info / minor-medium** issues against a
cost-benefit rubric. Aggressively fixing every low-severity finding can introduce
regressions, bloat the codebase, or force unjustified architectural churn. For such
issues the correct action is to **mark `wontfix` with an explicit reason** — neither
fix nor leave silently open.

**Apply `wontfix` ONLY when ALL four conditions hold:**

| Condition | Evaluate |
|-----------|----------|
| severity | `low` or `info` (medium requires a second reviewer-style check) |
| occurrence probability | extremely low — requires rare precondition chain |
| impact if triggered | negligible — no data loss, no security, no availability |
| fix cost / risk | high: requires arch change, new dep, or wide blast radius |

If ANY condition fails → do NOT wontfix; attempt the fix normally.

**Score state does NOT change this decision.** A sub-gate overall score does not
justify force-fixing a low-value issue with architectural risk — that would violate
the tool's purpose (real quality, not numeric score). The same issue, same triage,
regardless of `score_gate` status.

**Register the decision (required):**

```bash
python3 scripts/issue_tracker.py wontfix \
  .sessi-work/issue_registry.json <issue_id> <round> \
  "<4-part structured reason>"
```

Reason format (all four parts required):
```
severity=low; occurrence=rare (needs X+Y+Z); impact=negligible (<effect>); cost=high (<fix-risk>)
```

Example:
```
"severity=low; occurrence=rare (only on malformed unicode in filename); impact=negligible (caught by outer try); cost=high (would require rewriting path handling across 6 modules)"
```

These issues will be surfaced in the final report under **Accepted Risks** with
their reasons — nothing is silently dropped.

### Per-dimension fix strategy and caps

| Dimension | Fix Strategy | Max fixes/round |
|----------|-------------|-----------------|
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

**Cap override:** critical/high issues bypass the per-dim max — they are always attempted.

**Guardrails (never do):**
- Do NOT remove test assertions to make tests pass
- Do NOT broaden `except Exception` → bare `except:`
- Do NOT add `@ts-ignore`, `# type: ignore`, `# noqa`
- Do NOT refactor architecture without explicit user approval
- Do NOT add logging that hides errors
- Do NOT close a critical/high issue without tool-verified evidence of the fix

---

## Step 3: Per-Issue Fix + Verification Loop

Iterate the `open_issues.json` queue. For each issue:

```
1. Record pre-fix state:
   - Issue metadata: id, severity, dimension, file:line, message
   - Run dimension tool → baseline score
   - IF CRG available:

     a. Orientation (~100 tokens — always first):
        [USE mcp__code-review-graph__get_minimal_context_tool]
        task: "fix <dimension> issue: <message>"
        changed_files: ["<file>"]

     b. Pre-fix impact context (replaces manual file reads):
        [USE mcp__code-review-graph__get_review_context_tool]
        changed_files: ["<file with issue>"]
        detail_level: "minimal"   ← token-efficient
        include_source: true
        max_lines_per_file: 100

        Returns: impact radius + source snippets + review guidance.
        Use this instead of Read tool for the affected file — saves
        a full file read and adds structural context simultaneously.

     c. Impact radius (hub/bridge status):
        [USE mcp__code-review-graph__get_impact_radius_tool]
        → record hub/bridge status of the function being modified

2. Apply fix (minimal, targeted change addressing this specific issue)

2a. (CRG safety gate, if available) Before committing, check blast radius:

    python3 scripts/crg_integration.py risky . HEAD 0.7
    # exits 1 if risk_score >= 0.7 OR fix touches a hub/bridge node

    IF risky:
      → DO NOT commit this fix
      → git reset --hard HEAD (discard change)
      → python3 scripts/issue_tracker.py defer <id> <round> \
          "CRG blast radius <score>: touches hub/bridge node, requires human review"
      → move to next issue

    This prevents auto-fixes from silently restructuring architecture-
    critical nodes. A hub node fix may pass the dimension tool but break
    downstream flows that the tool doesn't see.

3. Re-run tool immediately (same command as Step 1)

4. Decide outcome:
   IF tool no longer reports this issue AND score did not regress:
     → keep change
     → git add <files>
     → git commit -m "fix(<dimension>): <message> [issue:<id>]"
     → CAPTURE traceability for the final report:
         COMMIT_SHA=$(git rev-parse HEAD)
         FILES=$(git show --name-only --format= $COMMIT_SHA | tr '\n' ',' | sed 's/,$//')
         python3 scripts/issue_tracker.py fix \
           .sessi-work/issue_registry.json <id> <round_num> \
           "$COMMIT_SHA" "$FILES" "<optional-note>"

   IF tool still reports it OR score regressed:
     → git revert --no-edit HEAD     (or discard uncommitted change)
     → try a different approach, OR
     → python3 scripts/issue_tracker.py defer \
         .sessi-work/issue_registry.json <id> <round_num> "<specific reason>"

   IF intentionally rejected (false positive, accepted risk):
     → python3 scripts/issue_tracker.py wontfix \
         .sessi-work/issue_registry.json <id> <round_num> "<justification>"
```

**One commit per fix.** Never batch multiple issue fixes into one commit —
traceability from commit → issue_id is mandatory for the verify step.

**Mandatory logging:** every `fix` / `defer` / `wontfix` call updates the registry,
which in turn drives `open_critical_count` / `open_high_count` in the next score pass.

---

## Step 4: Tier-Aware Fix Verification

For **Tier 1/2 dimensions** (linting, type_safety, etc.):
- Tool output is ground truth — re-run tool to verify
- Do NOT use Gemini to verify fixes (use tool output directly)

For **Tier 3 dimensions** (architecture, readability, etc.):
- Use tool where available (radon, pydocstyle)
- Claude judgment for subjective dimensions — but require concrete evidence

---

## Step 5: Deferred / Wontfix Issues

Some fixes are out of scope for auto-research:
- Major API redesign
- Database schema changes
- Security architecture overhaul (requires human review)
- Business logic correctness (no automated way to verify)

Mark each such issue with an explicit status in the registry (reason required):

```bash
# Out of scope this session — may revisit later
python3 scripts/issue_tracker.py defer \
  .sessi-work/issue_registry.json <id> <round> \
  "Requires architectural decision beyond automated scope"

# Explicitly rejected (false positive / accepted risk)
python3 scripts/issue_tracker.py wontfix \
  .sessi-work/issue_registry.json <id> <round> \
  "Tool false positive: <tool> flags X but see <file:line> — intended behavior"
```

Also mirror a human-readable summary to `.sessi-work/round_<n>/deferred_fixes.md`:
```markdown
## Deferred Fixes — Round <n>

- [architecture] issue:abc1234  Split monolithic `UserService` into auth/profile modules
  Reason: Requires architectural decision beyond automated scope
```

Deferred and wontfix issues do **NOT** count toward `open_critical_count` / `open_high_count`,
so early-stop can proceed once all remaining open criticals/highs are either fixed or explicitly
resolved with reason.

---

## Output

After all fixes applied and verified:
```bash
python3 scripts/checkpoint.py round <n> scores.json <overall_score>

# Final registry summary for this round
python3 scripts/issue_tracker.py summary .sessi-work/issue_registry.json
```

Proceed to `verify_round.md` for cross-dimension regression check. Early-stop is evaluated
after verify, not here — see SKILL.md Step 3e for the `quality_complete` condition.
