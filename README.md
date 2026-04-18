# Software Self-Improvement

A Claude Code skill that runs an **auto-research–style quality-improvement loop** against a GitHub repo or a local folder — with defences against LLM self-evaluation bias.

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch) (edit → evaluate → keep-or-revert under a fixed budget) and the 9-dimension quality model from the Harness Engineering Framework.

---

## What it does

Given a target codebase and a quality bar, it iterates up to N rounds (default 3):

1. **Evaluate** code across configurable dimensions. Tool scores are canonical; LLM judgement can only *lower* a score.
2. **Score** each 0–100 and compute a weighted overall.
3. **Verify** (round 2+) — `verify.py` caps claimed gains > +10 that lack evidence (tool-output diff or git file change on dimension-relevant paths). Regressions are surfaced.
4. **Early-stop** on the **verified** result only—never on unverified raw scores.
5. **Improve** — each fix is verified individually by re-running its tool; fixes that don’t move the tool are reverted.
6. **Report** — per-round markdown + JSON with `verification` block; `FINAL.md` with per-dimension trajectories.

See [docs/ANTI_BIAS.md](docs/ANTI_BIAS.md) for the threat model and six defences.

---

## Coverage

| Config | Dimensions | Auto-checks coverage |
|---|---|---|
| `config.example.yaml` | 9 standard | **60–70%** of observable quality |
| `config.advanced.yaml` | 9 standard + 7 extended | **75–80%** of observable quality |

The remaining **15–25%** requires production signals, domain experts, real users, and real attackers. No tool—regardless of rounds—creates knowledge from outside the codebase.

---

## Defaults (standard config)

| Setting | Default |
|---|---|
| Dimensions enabled | all 9 |
| Per-dimension target | 85 / 100 |
| Overall target | 85 / 100 |
| Rounds | 3 |
| Early-stop | on (verified result only) |
| Commit per fix | on |
| Push | off |
| Evidence threshold | +10 |
| Cap delta | +3 |

Weights are renormalised across enabled dims automatically.

---

## Install

```bash
# user-level
git clone https://github.com/johnnylugm-tech/software_self_improvement.git \
  ~/.claude/skills/software-self-improvement

pip install pyyaml
```

---

## Use

```text
> Auto-improve code quality in github.com/acme/api, target 90 overall, skip documentation dim.
> Self-improve this repo. Use ./quality.yaml.
> Run quality rounds on the ./services folder — 5 rounds, security must be ≥ 95.
```

Minimal config:

```yaml
target:
  type: folder
  location: ./
```

Advanced config (enable extended dims selectively):

```yaml
# Copy config.advanced.yaml and uncomment the dims you need.
# Each dim has prerequisite comments explaining what must be in place first.
```

---

## Configs

| File | Use case |
|---|---|
| `config.example.yaml` | Standard 9 dims. Start here. |
| `config.advanced.yaml` | All 16 dims. Enable selectively per prerequisites. |
| `examples/minimal.yaml` | Folder target, all defaults. |
| `examples/security_focused.yaml` | Higher security target, 5 rounds. |
| `examples/python_project.yaml` | Python toolchain. |
| `examples/typescript_project.yaml` | TypeScript toolchain. |

---

## Outputs

```
reports/
├── round_1.md / round_1.json
├── round_2.md / round_2.json   # includes 'verification' block
└── FINAL.md

.sessi-work/
├── config.json
└── round_<n>/
    ├── scores/<dim>.json    # tool_score + llm_score + evidence
    ├── tools/<dim>.txt      # raw tool output for verify.py
    ├── result.json          # raw post scores
    └── verified.json        # evidence-capped scores (rounds ≥ 2)
```

---

## Docs

| File | Content |
|---|---|
| [docs/USAGE.md](docs/USAGE.md) | Trigger phrases, overrides, examples |
| [docs/DIMENSIONS.md](docs/DIMENSIONS.md) | Standard 9 dimensions |
| [docs/EXTENDED_DIMENSIONS.md](docs/EXTENDED_DIMENSIONS.md) | 7 extended dimensions + prerequisites |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Execution model |
| [docs/ANTI_BIAS.md](docs/ANTI_BIAS.md) | Threat model, defences, revised coverage assertion |

---

## License

MIT.
