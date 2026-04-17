# Usage

## Trigger phrases

Claude Code matches the skill via its description. Natural phrases that work:

- "Auto-improve code quality in <repo-or-folder>."
- "Self-improve this repo to 85 across the board."
- "Run 5 quality rounds on ./services."
- "Use software-self-improvement with security ≥ 95 and skip documentation."
- "Raise github.com/acme/api to overall 90, security 95."

## With an explicit config

```text
> Use software-self-improvement with config=./quality.yaml
```

Minimal YAML (falls back to defaults for everything else):

```yaml
target:
  type: github
  location: https://github.com/acme/api
```

## Inline overrides

Claude can interpret structured asks like:

- "Target overall 90, security 95"
- "Disable documentation dimension"
- "Only 2 rounds"
- "Limit to subpath: `backend/`"

These get merged into the default config before the run starts.

## Runtime artefacts

The skill creates two working directories under the **current CWD** (never inside the target):

- `.sessi-work/` — transient per-round state (config.json, scores/, result.json, cloned target)
- `reports/` — durable output (round reports, FINAL.md)

Safe to delete either between runs.

## Git behaviour

| Setting | Effect |
|---|---|
| `git.commit_per_round: true` | One commit per round on a dedicated branch |
| `git.commit_per_round: false` | No commits — you get a dirty working tree to inspect |
| `git.branch: <name>` | Branch to create/checkout for the improvement run |
| `git.push: true` | Still requires you to confirm push in-session |

## Early-stop semantics

Both must hold:

1. `overall_score ≥ overall_target`, and
2. every enabled dimension's score ≥ its own `target`

If either is false, the next round runs (up to `rounds`). If both are true after any round, the loop exits immediately and the final report is written.

## Exit conditions

- **Targets met** — loop exits early, `FINAL.md` shows which round hit it.
- **Budget exhausted** — all `rounds` run; `FINAL.md` lists remaining gaps.
- **Hard failure** — a tool or script errors fatally; Claude surfaces the error and stops without corrupting reports.
