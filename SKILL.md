# Auto-Research Quality Improvement Skill

Implements an auto-research-style quality improvement loop for GitHub repos or local folders, with configurable targets across 9 core + 7 optional dimensions.

## Execution Contract

### Step 1: Resolve Configuration
- Load user config from `config.yaml` (or `config.advanced.yaml`)
- Merge with defaults; validate all dimensions exist
- Normalize weights across enabled dimensions
- Output: resolved config JSON

### Step 2: Resolve Target
- Clone GitHub repo (if URL) or use local folder path
- Set up working directory with git tracking
- Output: TARGET_PATH to stdout

### Step 3: Iterate Rounds (3 default, configurable)
Each round: **3a-evaluate → 3b-score → 3c-verify → 3d-checkpoint → 3e-early-stop → 3f-improve**

**3a. Evaluate Each Enabled Dimension**
- Run per-dimension evaluation: tool-first hierarchy (tool score + LLM score)
- Reconcile: min(tool_score, llm_score) to prevent optimism bias
- Evidence requirement: every finding must have evidence (tool output or code change)
- Output: per-dim JSON with scores, findings, tool outputs

**3b. Compute Weighted Score**
- Aggregate per-dim scores with normalized weights
- Calculate overall_score (0-100)
- Identify failing dimensions sorted by impact (gap × weight)
- Output: score JSON with breakdown, failing dims, meets_target flag

**3c. Verify Round (Anti-Bias Check)**
- Deterministic verification: compare pre/post tool outputs + git diffs
- Cap unsupported claims: Δ > 10 without evidence requires ≥3 lines of diff
- Surface regressions with revert protocol
- Output: verified.json (use for downstream decisions, not raw scores)

**3d. Checkpoint Round**
- Snapshot: round_<n>.json with all scores, findings, deltas
- Mark improvements per dimension
- Commit round results with git tag: `round-<n>`
- Output: markdown summary for dashboard

**3e. Early-Stop Check**
- If overall_score ≥ target: stop iteration, report success
- If no improvements last round: stop, report plateau
- Otherwise: proceed to 3f

**3f. Improve (Auto-Research)**
- Rank failing dimensions by impact (gap × weight)
- For each fix: run tool again post-change, revert if no improvement
- Guardrails: never weaken tests, broaden exception handling, add @ts-ignore
- One commit per fix
- Loop to 3a

### Step 4: Final Report
- Trajectory: per-dimension delta across all rounds
- Evidence: citations to commits and tool outputs
- Recommendation: pass/fail with explanation

## Default Configuration

- **Rounds:** 3
- **Target:** 85/100
- **Early-stop:** enabled
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

See `docs/ANTI_BIAS.md` for detailed analysis.

## References

- Framework: Based on Karpathy's autoresearch pattern
- Quality model: Harness Engineering 9-dimension weighted scoring
- Implementation: Claude Code skill with Python orchestration + LLM evaluation steps
