# Auto-Research Quality Improvement Skill

Implements an auto-research-style quality improvement loop for GitHub repos or local folders, with configurable targets across 12 core + 5 optional dimensions.

**Design principle:** The goal is **actual quality improvement** — resolving every critical/high issue found — not reaching a numeric score. Scores are a minimum gate; the issue registry is the source of truth for completion.

## Execution Contract

### Step 1: Resolve Configuration
- Load user config from `config.yaml` (or `config.advanced.yaml`)
- Merge with defaults; validate all dimensions exist
- Normalize weights across enabled dimensions
- Output: resolved config JSON

### Step 2: Resolve Target
- Clone GitHub repo (if URL) or use local folder path
- Set up working directory with git tracking
- Initialize issue registry at `.sessi-work/issue_registry.json` (persists across rounds)
- Output: TARGET_PATH to stdout

### Step 3: Iterate Rounds (3 default, configurable)
Each round: **3a-evaluate → 3b-score → 3c-verify → 3d-checkpoint → 3e-early-stop → 3f-improve**

**3a. Evaluate Each Enabled Dimension**
- Run per-dimension evaluation: tool-first hierarchy (tool score + LLM score)
- Reconcile: min(tool_score, llm_score) to prevent optimism bias
- Evidence requirement: every finding must have evidence (tool output or code change)
- **Every finding → written to issue registry** via `scripts/issue_tracker.py add`
  - Idempotent: same finding yields same ID; repeats are de-duplicated
  - Each issue carries: severity (critical/high/medium/low/info), dimension, file, line, evidence
- Output: per-dim JSON with scores, findings, tool outputs

**3b. Compute Weighted Score**
- Aggregate per-dim scores with normalized weights
- Calculate overall_score (0-100)
- Surface `open_critical_count`, `open_high_count`, `open_medium_count` from registry
- Identify failing dimensions sorted by impact (gap × weight)
- Output: score JSON with breakdown, failing dims, `meets_target`, `quality_complete`

**3c. Verify Round (Anti-Bias Check)**
- Deterministic verification: compare pre/post tool outputs + git diffs
- Cap unsupported claims: Δ > 10 without evidence requires ≥3 lines of diff
- Surface regressions with revert protocol
- Output: verified.json (use for downstream decisions, not raw scores)

**3d. Checkpoint Round**
- Snapshot: round_<n>.json with all scores, findings, deltas
- Mark improvements per dimension
- Persist `issue_registry.json` snapshot into round folder for audit
- Commit round results with git tag: `round-<n>`
- Output: markdown summary for dashboard

**3e. Early-Stop Check (Issue-Driven)**

```
critical_open = registry.summary().open_critical
high_open     = registry.summary().open_high

IF overall_score >= score_gate AND critical_open == 0 AND high_open == 0:
    → stop: quality_complete = true  (真正完成)

ELIF overall_score >= score_gate AND (critical_open > 0 OR high_open > 0):
    → continue: score passed but unresolved critical/high issues remain
    → DO NOT stop — this is the exact anti-pattern we guard against

ELIF saturation_check(registry, current_round, saturation_rounds=3) == true
     AND no score improvement in last round:
    → stop: plateau reached, remaining issues marked deferred
    → emit deferred_fixes.md for human review

ELSE:
    → proceed to 3f
```

Saturation detection: `python3 scripts/issue_tracker.py saturation .sessi-work/issue_registry.json <round>` returns true when no NEW issues were recorded for N consecutive rounds.

**3f. Improve (Issue-Driven)**

Input is the **open-issues queue**, not failing dimensions:

```
open = issue_tracker.open_issues(registry)  # sorted by severity, then round_found

Priority order:
  1. ALL open critical issues   (regardless of dimension score)
  2. ALL open high issues       (regardless of dimension score)
  3. Open medium issues in failing dimensions (score < target)
  4. Open low issues if time budget allows
```

For each fix:
- Run dimension tool pre/post → revert if no measurable improvement
- On success: `issue_tracker.py fix <id> <round> "<commit_sha>"`
- On intentional skip: `issue_tracker.py defer <id> <round> "<reason>"` (reason required)
- Guardrails: never weaken tests, broaden exception handling, add @ts-ignore
- One commit per fix
- Loop to 3a

### Step 4: Final Report

Full-transparency report — see `prompts/final_report.md` for the protocol.
Auto-generated from issue registry + round data + git log:

```bash
python3 scripts/report_gen.py \
  <repo_path> \
  .sessi-work \
  .sessi-work/issue_registry.json \
  <score_gate> \
  .sessi-work/final_report.md
```

**Mandatory sections:**

1. **Trajectory** — per-dimension score delta across all rounds.
2. **Fixed Issues** — `report.fixed_count`, grouped by dimension with commit SHAs.
3. **Accepted Risks** (`report.accepted_risks`) — deferred + wontfix issues,
   rendered as a table with severity, dimension, message, and the 4-part reason:

   ```markdown
   ## Accepted Risks / Not Fixed

   | ID | Severity | Dimension | Issue | Reason |
   |----|----------|-----------|-------|--------|
   | abc1234 | low | architecture | Circular dep in util | severity=low; occurrence=rare (only on cold start); impact=negligible (self-healing); cost=high (would require arch split) |
   ```

   This is the audit trail: every low-value issue that was **consciously not fixed**
   shows here, so nothing disappears silently.

4. **Still Open** (`report.open`) — any issue that is still open at end-of-run.
   If this contains anything of severity ≥ medium, the recommendation is `partial`.
5. **Recommendation** — one of:
   - `pass` — `quality_complete = true` AND no open ≥ medium issues
   - `pass-with-risks` — `quality_complete = true` AND only accepted_risks remain
   - `partial` — `max_rounds` reached with open ≥ medium issues
   - `fail` — regressions detected or score dropped below baseline
6. **Evidence** — citations to commits (`git log --oneline`) and tool outputs.

## Default Configuration

- **Rounds:** 3 (max)
- **Score gate:** 85/100 (minimum — not a completion goal)
- **Early-stop:** issue-driven (score_gate AND zero open critical/high)
- **Saturation rounds:** 3 (stop if no new issues found for 3 rounds)
- **Commit strategy:** one per fix
- **Evidence threshold:** 10 points
- **Bias cap:** Δ +3 without diff evidence

## Tool Hierarchy

```
final_score = min(tool_score, llm_score)
```

This prevents LLM from inflating scores when tools say otherwise.

## Dimension System

**9 Core Dimensions (all enabled by default):**
- linting
- type_safety
- test_coverage
- security
- performance
- architecture
- readability
- error_handling
- documentation

**7 Extended Dimensions (optional, disabled by default):**
- mutation_testing
- property_testing
- fuzzing
- license_compliance
- accessibility
- observability
- supply_chain_security

See `docs/EXTENDED_DIMENSIONS.md` for prerequisites and integration.

## Output Structure

```
.sessi-work/
├── round_1/
│   ├── scores/
│   │   ├── linting.json
│   │   ├── type_safety.json
│   │   └── ...
│   ├── tools/
│   │   ├── linting.txt (raw tool output)
│   │   └── ...
│   ├── round_1.json (snapshot)
│   └── round_1.md (summary)
├── round_2/
├── round_3/
└── final_report.md
```

## Invocation

```bash
# Resolve config and target
python3 scripts/config_loader.py config.yaml
python3 scripts/setup_target.py <github-url-or-local-path>

# Evaluate single dimension
claude-internal prompts/evaluate_dimension.md --config config.json --dimension linting

# Score round
python3 scripts/score.py round_1

# Verify round
python3 scripts/verify.py round_1 config.json

# Checkpoint
python3 scripts/checkpoint.py round_1

# Improvement plan
claude-internal prompts/improvement_plan.md --failing-dims verified.json

# Verify improvements
claude-internal prompts/verify_round.md --results result.json --verified verified.json
```

## Anti-Bias Defenses

1. **Tool-first hierarchy:** Claims capped by tool scores
2. **Evidence requirement:** Every finding needs tool output or code diff
3. **Per-fix re-verification:** Revert if tool shows no improvement
4. **Deterministic verification:** quantitative comparison pre/post
5. **Regression detection:** surface changes that hurt dimensions
6. **Path heuristics:** prevent undetected regressions
7. **Structural drift detection (CRG):** catches architectural regressions
   that dimension tools cannot see — new hub nodes, expanded test gaps,
   risk-score jumps across rounds

See `docs/ANTI_BIAS.md` for detailed analysis.

## Code Review Graph Integration

When [Code Review Graph](https://github.com/code-review-graph) (CRG) is installed,
three integration points activate automatically:

1. **Tier 3 evaluation (evaluate_dimension.md):** architecture / readability /
   performance / documentation / error_handling dimensions query the CRG
   knowledge graph (hub nodes, bridge nodes, large functions, knowledge gaps)
   before reading any source code. Target: 30-50% Tier 3 token reduction.

2. **Blast radius safety gate (improvement_plan.md):** before committing any
   fix, `scripts/crg_integration.py risky` checks if the change touches a
   hub/bridge node or has `risk_score >= 0.7`. Risky fixes are deferred
   instead of committed, preventing auto-fixes from silently restructuring
   architecture-critical code.

3. **Structural verification (verify_round.md):** after each round,
   `code-review-graph update` + `detect-changes` measures architectural
   drift. Drift > 0.4 triggers the revert protocol; new untested functions
   are auto-registered as `test_coverage` issues.

**Installation** (one-time, per target repo):
```bash
code-review-graph install --platform claude-code --repo <target>
code-review-graph build --repo <target>
# Restart Claude Code to load .mcp.json
```

Framework **gracefully degrades** without CRG — all integration points skip
silently; only token efficiency and structural verification are lost.

## References

- Framework: Based on Karpathy's autoresearch pattern
- Quality model: Harness Engineering 9-dimension weighted scoring
- Implementation: Claude Code skill with Python orchestration + LLM evaluation steps
