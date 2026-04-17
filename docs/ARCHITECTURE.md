# Architecture

## Inspiration

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch) — one mutable unit of work, a fixed evaluation metric, a fixed time/iteration budget, and a keep-or-revert decision each cycle.
- The **Harness Engineering Framework** — 9 quality dimensions, weighted scoring, auto-improvement loop with a per-dimension threshold.

This skill fuses them: each round is a full edit-evaluate-decide cycle, evaluation is the 9-dimension weighted score, the budget is `rounds`, and the decision is "early-stop or keep improving".

## Execution loop

```
config_loader.py → config.json
        │
 setup_target.py → TARGET_PATH
        │
   ┌────▼────┐
   │ round n │────────────────────────────────────────────────┐
   └────┬────┘                                                │
        │                                                     │
        │ evaluate (prompts/evaluate_dimension.md)            │
        │   ├─ run tools per dim                              │
        │   ├─ mechanical sub-score                           │
        │   ├─ LLM sub-score                                  │
        │   └─ reconcile → .sessi-work/scores/*.json          │
        │                                                     │
        │ score.py → result.json (overall + meets)            │
        │                                                     │
        │ checkpoint.py --round n → reports/round_n.md        │
        │                                                     │
        │ meets_target? ──yes──▶ final_report                 │
        │        │                                            │
        │        no                                           │
        │        │                                            │
        │ improve (prompts/improvement_plan.md)               │
        │   ├─ rank failing dims by impact                    │
        │   ├─ ≤3 fixes per dim, prefer mechanical            │
        │   ├─ apply edits inside TARGET_PATH                 │
        │   └─ commit (if configured)                         │
        │                                                     │
        └──▶ next round ──────────────────────────────────────┘
```

## Components

| File | Role |
|---|---|
| `SKILL.md` | Entry point Claude reads on invocation — the exact protocol |
| `scripts/config_loader.py` | YAML → resolved JSON, merges defaults, normalises weights |
| `scripts/setup_target.py` | Clones GitHub target or validates local folder |
| `scripts/score.py` | Weighted overall + failing dims sorted by impact |
| `scripts/checkpoint.py` | Per-round markdown+JSON; final trajectory report |
| `prompts/evaluate_dimension.md` | How Claude evaluates a single dimension |
| `prompts/improvement_plan.md` | How Claude plans and applies edits |
| `config.example.yaml` | Canonical config with all knobs |

Scripts are deterministic (math, I/O, config). Claude supplies the judgement (LLM evaluation, code edits). This split is deliberate: mechanical parts shouldn't drift between runs, but evaluation and improvement benefit from reasoning.

## Why early-stop needs both conditions

A single weak dimension can be masked by a strong overall when weights are uneven. Requiring both `overall ≥ overall_target` and every `dim ≥ dim_target` prevents "I passed overall while test coverage is 40" situations — which is exactly the class of failures the framework's per-dim minimum is designed to prevent.

## Why prefer mechanical fixes first

Autoresearch works because the agent's edits are fairly compared against a stable metric. Mechanical fixes (formatter, lint auto-fix, type annotation) rarely regress other dimensions, so they accumulate monotonically. Design-level changes are higher-variance and are deferred — either to later rounds with more budget, or to a human.

## Why commit per round

Each round's commit is a clean, reviewable diff keyed to a measurable score delta. If round 3 regresses, you can `git revert` just that round without unravelling rounds 1–2. Matches the "keep-or-revert" discipline from autoresearch.

## What the skill never does

- Touch files outside `TARGET_PATH`
- Modify its own `scripts/`, `prompts/`, `config.example.yaml` during a run
- Push to a remote without explicit per-session authorisation
- Weaken tests, broaden `except`, or add `@ts-ignore` to inflate scores
- Take design-level decisions (schema changes, API breaks, new deps) without user authorisation
