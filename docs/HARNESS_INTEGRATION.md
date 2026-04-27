# Harness Integration Contract

## Overview

`software_self_improvement` is invoked by `harness-methodology` via subprocess IPC.
The two repos are **strictly decoupled**: harness owns gate lifecycle; SSI owns quality evaluation.

## Entry Point

```
python3 -m software_self_improvement.runner \
    --config  .sessi-work/gate{n}_config.yaml \
    --root    /path/to/target/project \
    --output  .sessi-work/gate{n}_result.json \
    [--fr-id  FR-01]
```

## Input: Gate Config YAML

Written by `harness_bridge._invoke_harness()` from `harness/gate_configs/gate{n}_*.yaml`.

Key fields consumed by runner.py:

| Field | Type | Description |
|---|---|---|
| `gate` | int | Gate number (1-4) |
| `score_gate` | int | Composite pass threshold (absent for Gate 1) |
| `max_rounds` | int | Max evaluation rounds |
| `early_stop` | bool | Stop eval early if issues found |
| `saturation_rounds` | int | Consecutive no-new-issue rounds → stop |
| `dimensions[].name` | str | Dimension name |
| `dimensions[].threshold` | int | Per-dim pass threshold (harness field name) |
| `dimensions[].weight` | float | Composite score weight |
| `dimensions[].tier` | int | LLM tier (1=gemini-flash, 3=claude) |
| `mutation_testing` | dict | `{median_runs, timeout_per_run}` |

**Translation**: `dimensions[].threshold` maps to SSI's `target`. Runner performs this translation automatically in `translate_gate_config()`.

## Output: Gate Result JSON

Written to `--output` path. Schema: `schemas/harness_gate_result.schema.json`.

```json
{
  "score": 83.5,
  "quality_complete": false,
  "rounds_used": 2,
  "open_critical": 0,
  "open_high": 1,
  "dimensions": [
    {
      "name": "linting",
      "score": 92.0,
      "threshold": 90,
      "issues": []
    },
    {
      "name": "security",
      "score": 74.0,
      "threshold": 80,
      "issues": [
        {"severity": "high", "file": "src/auth.py", "line": 42, "message": "..."}
      ]
    }
  ]
}
```

### `quality_complete` definition

```
quality_complete = (score >= score_gate) AND (open_critical == 0) AND (open_high == 0)
```

This matches `score.py::compute_overall_score()` exactly.

## Gate-Specific Behaviour

| Gate | trigger | scope | score_gate | Notes |
|---|---|---|---|---|
| 1 | per_fr_completion | single_fr | — | Per-dim threshold only; `max_rounds=1`; no auto-retry |
| 2 | phase_exit P3 | full_phase | 75 | First security + mutation pass; CRG impact check |
| 3 | phase_exit P4 | full_phase | 80 | Full 12-dim; CRG reconnaissance + tier3 guidance |
| 4 | phase_exit P6 | full_project | 85 | Replaces P6 SOP; Hermes APPROVE required post-gate |

Gate 1 blocking: harness raises `GateBlockedError` if **any** `dimension.score < dimension.threshold`.
Gates 2-4 blocking: harness raises `GateBlockedError` if `score < score_gate` OR `not quality_complete`.

## Internal Flow (runner.py)

```
for round in 1..max_rounds:
    subprocess: scripts/verify.py → writes .sessi-work/round_N/scores/*.json
    score.load_scores(round_dir)
    score.compute_overall_score(scores, ssi_config, registry, crg_metrics)
    if quality_complete: break
    if saturation (no new issues for saturation_rounds): break
write output JSON
exit 0 if quality_complete else exit 1
```

## Workspace Layout

```
.sessi-work/
  gate{n}_config.yaml        ← written by harness_bridge (input to runner)
  gate{n}_ssi_config.json    ← translated SSI config (written by runner)
  gate{n}_result.json        ← GateResult output (read by harness_bridge)
  round_1/
    scores/
      linting.json           ← {dimension, score, tool_score, llm_score, ...}
      security.json
      ...
    improvements/
      linting.diff           ← fix applied in this round
  round_2/
    ...
  issue_registry.json        ← persistent issue tracker across rounds
  crg_metrics.json           ← CRG structural metrics (written by crg_bridge)
```

## Installation

```bash
# From software_self_improvement repo root:
pip install -e .             # enables: python3 -m software_self_improvement.runner

# Or without install (SSI_ROOT env var):
export SSI_ROOT=/path/to/software_self_improvement
python3 $SSI_ROOT/software_self_improvement/runner.py --config ... --root ... --output ...
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HARNESS_GEMINI_MODEL` | `gemini-2.5-flash` | Override Tier 1/2 model |
| `HARNESS_CLAUDE_MODEL` | `claude-sonnet-4-5` | Override Tier 3 model |
| `HARNESS_IMPROVE_MODEL` | (= CLAUDE_MODEL) | Override improvement model |
| `HARNESS_FR_ID` | `""` | FR ID passed through to evaluators |
| `CRG_METRICS_PATH` | `.sessi-work/crg_metrics.json` | CRG metrics file location |
