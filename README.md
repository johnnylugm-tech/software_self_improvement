# Software Self-Improvement

A Claude Code skill that runs an **auto-research–style quality-improvement loop** against a GitHub repo or a local folder.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (edit → evaluate → keep-or-revert under a fixed budget) and the 9-dimension quality model from the Harness Engineering Framework.

## What it does

Given a target codebase and a quality bar, it iterates up to N rounds (default 3):

1. **Evaluate** code across configurable dimensions (linting, type safety, test coverage, security, performance, architecture, readability, error handling, documentation).
2. **Score** each 0–100 and compute a weighted overall.
3. **Early-stop** as soon as every enabled dimension and the overall score meet their targets.
4. **Improve** — generate a prioritised patch plan targeting failing dimensions, apply edits, commit per round.
5. **Report** — markdown + JSON per round, plus `FINAL.md` with per-dimension trajectories.

## Defaults

| Setting | Default |
|---|---|
| Dimensions enabled | all 9 |
| Per-dimension target | 85 / 100 |
| Overall target | 85 / 100 |
| Rounds | 3 |
| Early-stop | on |
| Commit per round | on |
| Push | off |

Weights match the framework: linting 10%, type safety 15%, test coverage 20%, security 15%, performance 10%, architecture 10%, readability 10%, error handling 5%, documentation 5%. When a dimension is disabled, weights are renormalised across the remaining enabled dimensions automatically.

## Install

```bash
# user-level
git clone https://github.com/johnnylugm-tech/software_self_improvement.git \
  ~/.claude/skills/software-self-improvement

# or project-level
git clone https://github.com/johnnylugm-tech/software_self_improvement.git \
  <your-project>/.claude/skills/software-self-improvement

pip install pyyaml
```

## Use

Inside Claude Code, invoke naturally — Claude will pick the skill up from the description:

```text
> Auto-improve code quality in github.com/acme/api, target 90 overall, skip documentation dim.
> Self-improve this repo. Use ./quality.yaml.
> Run quality rounds on the ./services folder — 5 rounds, security must be ≥ 95.
```

Or, with an explicit config file:

```yaml
# quality.yaml
target:
  type: folder
  location: ./

rounds: 3
overall_target: 85
dimension_target: 85

dimensions:
  documentation:
    enabled: false
  security:
    target: 95
```

## Outputs

```
reports/
├── round_1.md / round_1.json
├── round_2.md / round_2.json
├── round_3.md / round_3.json
└── FINAL.md
```

`FINAL.md` shows initial vs final overall scores, per-dimension deltas across rounds, and whether targets were met.

## Docs

- [docs/USAGE.md](docs/USAGE.md) — trigger phrases, overrides, examples
- [docs/DIMENSIONS.md](docs/DIMENSIONS.md) — the 9 dimensions and how they are scored
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the execution model and why it mirrors autoresearch

## License

MIT.
