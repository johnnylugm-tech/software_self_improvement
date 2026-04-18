---
name: software-self-improvement
description: Auto-research–style loop that iteratively improves software quality on a GitHub repo or local folder across configurable dimensions (linting, type safety, test coverage, security, performance, architecture, readability, error handling, documentation). Runs up to N rounds (default 3) with early-stop when all targets are met (default 85/100 per dimension and overall). Defends against self-evaluation bias with evidence-gated scoring and a deterministic verify step. Trigger when the user asks to "auto-improve code quality", "self-improve this repo", "run quality rounds", "raise the codebase to 85/90", or supplies a quality config YAML with dimension targets.
---

# Software Self-Improvement

Auto-research–style quality-improvement loop for a target codebase. Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch): edit → evaluate → keep-or-revert, under a fixed budget.

The same agent that edits code also scores it. This skill treats that as a threat model, not a feature. Tool scores are canonical, every claimed gain > 10 points must be backed by evidence (tool-output diff, git file change, or cited code), and a deterministic `verify.py` caps unsupported gains before they can drive early-stop. See [docs/ANTI_BIAS.md](docs/ANTI_BIAS.md).

## Inputs

One of:
- Explicit config path: `config=<path-to-yaml>`
- Inline overrides in the user's message (target location, rounds, target score, disabled dims)
- Nothing → use `config.example.yaml` against the current working directory

## Execution contract

Follow these steps exactly. Do not skip, reorder, or "optimise" by batching.

### Step 1 — Resolve config

```bash
mkdir -p .sessi-work reports
python scripts/config_loader.py <config-path-or-empty> > .sessi-work/config.json
```

Validate: `target`, `rounds`, `overall_target`, `dimensions` (with `normalized_weight` and `target`) are present.

### Step 2 — Resolve target

From `config.target`:
- `type: folder` → `python scripts/setup_target.py --folder <location>`
- `type: github` → `python scripts/setup_target.py --github <url> --workdir .sessi-work/target`

Capture stdout as `TARGET_PATH`. All subsequent file operations happen under `TARGET_PATH`.

Ensure it's a git repo (the verify step requires it):

```bash
if [ ! -d "$TARGET_PATH/.git" ]; then
  git -C "$TARGET_PATH" init -q
  git -C "$TARGET_PATH" add -A
  git -C "$TARGET_PATH" -c user.name=skill -c user.email=skill@local commit -qm "baseline"
fi
```

If `git.commit_per_round: true`, create/checkout the working branch:

```bash
git -C "$TARGET_PATH" checkout -B "<config.git.branch>"
```

Tag the absolute baseline: `git -C "$TARGET_PATH" tag -f baseline`.

### Step 3 — For round = 1 .. rounds

Each round lives under `.sessi-work/round_<n>/` with subdirs `scores/` and `tools/`.

#### 3a. Evaluate

Read [`prompts/evaluate_dimension.md`](prompts/evaluate_dimension.md). For each **enabled** dimension:

1. Run its tools, **tee raw output to `.sessi-work/round_<n>/tools/<dim>.txt`** (the verify step needs these).
2. Apply the tool-first + evidence protocol to produce `.sessi-work/round_<n>/scores/<dim>.json`.
3. Reconcile: `final_score = min(tool_score, llm_score)` when both exist.

Assemble `.sessi-work/round_<n>/scores.json` as `{dimension_name: score_int}`.

#### 3b. Score

```bash
python scripts/score.py \
  --scores .sessi-work/round_<n>/scores.json \
  --config .sessi-work/config.json \
  > .sessi-work/round_<n>/result.json
```

#### 3c. Verify (rounds ≥ 2 only)

For round 1, skip — there's no pre to compare against; use `result.json` directly as the verified result.

For rounds ≥ 2, read [`prompts/verify_round.md`](prompts/verify_round.md) and run:

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

Apply the LLM cross-check protocol from `verify_round.md` for any capped dimensions or regressions. The file written at the end of this step is the **authoritative** result for the round — downstream reads only from it.

#### 3d. Checkpoint (using the authoritative result)

```bash
# round 1: result.json IS the authoritative result
# rounds >= 2: verified.json
python scripts/checkpoint.py --round <n> \
  --result .sessi-work/round_<n>/<verified-or-result>.json \
  --reports-dir reports --out reports/round_<n>.md
```

#### 3e. Early-stop

If authoritative `meets_target` is `true`, log `"Early stop at round <n>: targets met."` and jump to Step 4. **Never early-stop on an unverified result** — if `verify.py` capped something that flipped `meets_target` from true to false, continue rounds.

#### 3f. Improve (skip on the very last round — still checkpoint above)

Read [`prompts/improvement_plan.md`](prompts/improvement_plan.md).

1. Tag start point: `git -C "$TARGET_PATH" tag -f round_<n+1>_start`.
2. Apply its protocol: rank failing dims by impact, pick ≤ 3 mechanical fixes per dim, **verify each fix individually by re-running the tool** (revert the fix if the tool regresses or is unchanged), commit each accepted fix separately.
3. Never modify files outside `TARGET_PATH`.

Continue the loop.

### Step 4 — Final report

```bash
python scripts/checkpoint.py --final --reports-dir reports --out reports/FINAL.md
```

Report back to the user: the path to `reports/FINAL.md`, the final overall score vs target, and a one-paragraph summary that explicitly mentions:
- Any capped dimensions (surfaced by `verify.py`)
- Any regressions that triggered reverts
- Per-dimension trajectories

## Rules (non-negotiable)

- Never touch files outside `TARGET_PATH`.
- Never `git push` unless `git.push: true` AND the user has authorised it in this session.
- Never weaken tests, broaden `except`, or add `@ts-ignore` / `# type: ignore` to inflate scores.
- Never early-stop on an unverified raw `result.json` from round ≥ 2.
- Skip disabled dimensions entirely: do not score, do not improve for them.
- Do not mutate the skill's own config, scripts, or prompts during a run.
- Raw tool output for every dimension in every round MUST be persisted to `.sessi-work/round_<n>/tools/<dim>.txt` — this is what lets verify.py detect artificial gains.
