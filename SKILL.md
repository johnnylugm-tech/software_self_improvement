---
name: software-self-improvement
description: Auto-research–style loop that iteratively improves software quality on a GitHub repo or local folder across configurable dimensions (linting, type safety, test coverage, security, performance, architecture, readability, error handling, documentation). Runs up to N rounds (default 3) with early-stop when all targets are met (default 85/100 per dimension and overall). Trigger when the user asks to "auto-improve code quality", "self-improve this repo", "run quality rounds", "raise the codebase to 85/90", or supplies a quality config YAML with dimension targets.
---

# Software Self-Improvement

Auto-research–style quality-improvement loop for a target codebase. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch): edit → evaluate → keep-or-revert, under a fixed budget.

## Inputs

One of:
- Explicit config path: `config=<path-to-yaml>`
- Inline overrides in the user's message (target location, rounds, target score, disabled dims)
- Nothing → use `config.example.yaml` against the current working directory

## Execution contract

Follow these steps exactly. Do not skip, reorder, or "optimise" by batching.

### Step 1 — Resolve config

Create a work directory: `mkdir -p .sessi-work reports`.

Run the loader:
```bash
python scripts/config_loader.py <config-path-or-empty> > .sessi-work/config.json
```

Read the JSON. Validate: `target`, `rounds`, `overall_target`, `dimensions` (with `normalized_weight` and `target`) are present.

### Step 2 — Resolve target

From `config.target`:
- `type: folder` → `python scripts/setup_target.py --folder <location>`
- `type: github` → `python scripts/setup_target.py --github <url> --workdir .sessi-work/target`

Capture stdout as `TARGET_PATH`. All subsequent file operations happen under `TARGET_PATH`.

If target is a git repo and `git.commit_per_round: true`, create the working branch:
```bash
git -C "$TARGET_PATH" checkout -B "<config.git.branch>"
```

### Step 3 — For round = 1 .. rounds

#### 3a. Evaluate

For each **enabled** dimension in `config.dimensions`:
1. Read [`prompts/evaluate_dimension.md`](prompts/evaluate_dimension.md).
2. Apply its protocol to `TARGET_PATH` for this dimension.
3. Write `.sessi-work/scores/<dimension>.json` with `{dimension, score, findings, gaps, tool_outputs}`.

Assemble `.sessi-work/scores.json` as a flat `{dimension_name: score_int}` object.

#### 3b. Score

```bash
python scripts/score.py --scores .sessi-work/scores.json --config .sessi-work/config.json > .sessi-work/result.json
```

#### 3c. Checkpoint

```bash
python scripts/checkpoint.py --round <n> --result .sessi-work/result.json --reports-dir reports --out reports/round_<n>.md
```

#### 3d. Early-stop

If `result.meets_target` is `true`, log `"Early stop at round <n>: targets met."` and jump to Step 4.

#### 3e. Improve (skip on the very last round if `meets_target` is false — still checkpoint)

1. Read [`prompts/improvement_plan.md`](prompts/improvement_plan.md).
2. Apply its protocol to produce a prioritised patch plan against `result.failing_dimensions`.
3. Execute edits with Edit/Write/Bash tools on files **inside `TARGET_PATH` only**.
4. If `git.commit_per_round: true` and target is a git repo:
   ```bash
   git -C "$TARGET_PATH" add -A && git -C "$TARGET_PATH" commit -m "round <n>: quality improvements"
   ```

Continue the loop.

### Step 4 — Final report

```bash
python scripts/checkpoint.py --final --reports-dir reports --out reports/FINAL.md
```

Report back to the user: the path to `reports/FINAL.md`, the final overall score vs target, and a one-paragraph summary of per-dimension trajectories.

## Rules

- Never touch files outside `TARGET_PATH`.
- Never `git push` unless `git.push: true` AND the user has authorised it in this session.
- Never weaken tests to inflate coverage — add real tests.
- Skip disabled dimensions entirely: do not score, do not improve for them.
- Early-stop gates on **both** overall ≥ `overall_target` AND every enabled dimension ≥ its own `target`.
- Do not mutate the skill's own config or scripts during a run.
