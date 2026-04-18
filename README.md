# Software Self-Improvement

A Claude Code skill that runs an **auto-research–style quality-improvement loop** against a GitHub repo or a local folder — with defences against LLM self-evaluation bias.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (edit → evaluate → keep-or-revert under a fixed budget) and the 9-dimension quality model from the Harness Engineering Framework.

## What it does

Given a target codebase and a quality bar, it iterates up to N rounds (default 3):

1. **Evaluate** code across configurable dimensions (linting, type safety, test coverage, security, performance, architecture, readability, error handling, documentation).
2. **Score** each 0–100 and compute a weighted overall. **Tool scores are canonical**; LLM judgement can only *lower* a score, never raise it.
3. **Verify** (round 2+) — a deterministic `verify.py` caps any claimed +delta > 10 that isn't backed by a material tool-output change or a git diff on dimension-relevant paths. Regressions are surfaced.
4. **Early-stop** as soon as every enabled dimension and the overall score meet their targets — but only on the **verified** result, never on a raw unverified one.
5. **Improve** — generate a prioritised patch plan targeting failing dimensions. Each fix is verified individually by re-running its tool; fixes that don't move the tool are reverted.
6. **Report** — markdown + JSON per round (including a `verification` block), plus `FINAL.md` with per-dimension trajectories and a list of capped or regressed dimensions.

See [docs/ANTI_BIAS.md](docs/ANTI_BIAS.md) for the threat model, the six defences, and how to tune them.

## Defaults

| Setting | Default |
|---|---|
| Dimensions enabled | all 9 |
| Per-dimension target | 85 / 100 |
| Overall target | 85 / 100 |
| Rounds | 3 |
| Early-stop | on (verified result only) |
| Commit per fix | on |
| Push | off |
| Evidence threshold | +10 (claimed gains above this need evidence) |
| Cap delta | +3 (unsupported gains capped at pre + 3) |

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

Minimal config (everything else inherits defaults):

```yaml
# quality.yaml
target:
  type: folder
  location: ./
```

## Outputs

```
reports/
├── round_1.md / round_1.json
├── round_2.md / round_2.json   # includes 'verification' block
├── round_3.md / round_3.json
└── FINAL.md

.sessi-work/
├── config.json
└── round_<n>/
    ├── scores/<dim>.json    # per-dim evidence + tool_score + llm_score
    ├── tools/<dim>.txt      # raw tool output, used by verify.py
    ├── result.json          # raw post scores
    └── verified.json        # evidence-checked scores (rounds ≥ 2)
```

## Docs

- [docs/USAGE.md](docs/USAGE.md) — trigger phrases, overrides, examples
- [docs/DIMENSIONS.md](docs/DIMENSIONS.md) — the 9 dimensions and how they are scored
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the execution model and why it mirrors autoresearch
- [docs/ANTI_BIAS.md](docs/ANTI_BIAS.md) — the self-evaluation threat model and defences

## License

MIT.
