# Harness Quality Framework

Auto-research-style quality improvement for code repositories. Evaluates code across 9 core quality dimensions with optional 7 extended dimensions, identifies gaps, and automatically implements improvements.

## Features

✓ **9 Core Quality Dimensions**
- Linting, Type Safety, Test Coverage, Security, Performance
- Architecture, Readability, Error Handling, Documentation

✓ **7 Extended Dimensions** (optional)
- Mutation Testing, Property Testing, Fuzzing
- License Compliance, Accessibility, Observability, Supply Chain Security

✓ **Anti-Bias Defenses**
- Tool-first hierarchy: final_score = min(tool_score, llm_score)
- Evidence requirement on all findings
- Per-fix re-verification with revert protocol
- Deterministic verification prevents self-evaluation bias

✓ **Configurable Quality Gates**
- Weighted dimension scoring (normalize across enabled dims)
- Configurable targets per dimension (0-100)
- Early-stop when target reached
- Per-round snapshots with git tagging

## Quick Start

### Standard Configuration (9 dimensions)
```bash
# Use default config with all core dimensions
cp config.example.yaml config.yaml

# Run the skill
claude-code run quality-improvement --config config.yaml
```

### Advanced Configuration (16 dimensions)
```bash
# Copy advanced config
cp config.advanced.yaml config.yaml

# Install extended dimension tools (optional)
./scripts/install_extended_tools.sh --high  # or --medium, --low, --all

# Enable extended dimensions in config
# Edit config.yaml: set 'enabled: true' for desired extended dims

# Run with all dimensions
claude-code run quality-improvement --config config.yaml
```

## Configuration

### config.example.yaml
- 9 standard dimensions (all enabled by default)
- Target: 85/100
- 3 rounds of improvement
- Early-stop enabled

**Weights** (normalized to 1.0):
```
linting           8%
type_safety      12%
test_coverage    15%
security         12%
performance      10%
architecture     10%
readability       9%
error_handling   11%
documentation    13%
```

### config.advanced.yaml
- All 16 dimensions (7 extended disabled by default)
- Same target/rounds/early-stop as standard
- Adjusted weights when extended dims enabled
- Installation guide included in file

## Core Dimensions

| Dimension | Weight | Target | Tools | Purpose |
|-----------|--------|--------|-------|---------|
| **linting** | 8% | 95 | eslint, pylint, clippy | Code style consistency |
| **type_safety** | 12% | 95 | pyright, rustc, javac | Type correctness |
| **test_coverage** | 15% | 80% | coverage, nyc, tarpaulin | Line/branch coverage |
| **security** | 12% | 90 | bandit, npm-audit, cargo-audit | Vulnerability detection |
| **performance** | 10% | 80 | pytest-benchmark, lighthouse | Speed/efficiency |
| **architecture** | 10% | 80 | sonarqube, codeql | Code organization |
| **readability** | 9% | 85 | radon, complexity tools | Maintainability |
| **error_handling** | 11% | 85 | pytest, jest | Exception/error recovery |
| **documentation** | 13% | 85 | pydocstyle, jsdoc | Code comment coverage |

## Extended Dimensions

| Dimension | Tools | Priority | Impact | Prerequisites |
|-----------|-------|----------|--------|----------------|
| mutation_testing | mutmut, stryker | **HIGH** | +3-5% | coverage ≥ 70% |
| property_testing | hypothesis, fast-check | MEDIUM | +3% | linting ✓, type_safety ≥ 90% |
| fuzzing | atheris, jazzer | MEDIUM | +3% | security ≥ 85% |
| license_compliance | scancode, fossa | LOW | +1% | — |
| accessibility | pa11y, axe-core | MEDIUM | +2% | UI code, readability ≥ 80% |
| observability | syft, grype | LOW | +2% | — |
| supply_chain_security | cosign | LOW | +3% | security ≥ 85% |

**With extended dims:** Quality ceiling increases from 60-70% (standard tools alone) to 75-80% (full framework).

See `docs/EXTENDED_DIMENSIONS.md` for detailed guide.

## How It Works

### 4-Step Execution

1. **Resolve Configuration** → Load & merge defaults, validate dims
2. **Resolve Target** → Clone repo or use local path, set up git
3. **Iterate Rounds** → Evaluate → Score → Verify → Improve (repeat N times)
4. **Final Report** → Trajectory, evidence, recommendation

### Per-Round Loop

**3a. Evaluate** (per-dimension)
- Run tool checks + LLM analysis
- Reconcile: min(tool_score, llm_score)
- Require evidence for every finding

**3b. Score**
- Aggregate per-dim scores with weights
- Identify failing dimensions by impact
- Check if target reached

**3c. Verify** (anti-bias check)
- Deterministic comparison: pre vs post
- Cap unsupported claims (Δ > 10 needs evidence)
- Surface regressions, enable revert

**3d. Checkpoint**
- Snapshot round results
- Git tag: `round-<n>`
- Generate markdown summary

**3e. Early-Stop**
- If score ≥ target → stop (success)
- If no improvements → stop (plateau)
- Else → continue to improve

**3f. Improve** (auto-research)
- Rank fixes by impact (gap × weight)
- Per-fix: tool verification + revert on regression
- One commit per fix

### Anti-Bias Defenses

1. **Tool-first hierarchy** — LLM claims capped by tool scores
2. **Evidence requirement** — All findings need tool output or git diff
3. **Per-fix re-verification** — Revert if tool shows no improvement
4. **Deterministic verification** — Quantitative pre/post comparison
5. **Regression detection** — Surface changes that hurt other dims
6. **Path heuristics** — Prevent undetected regressions

See `docs/ANTI_BIAS.md` for detailed analysis and tuning.

## Installation

### Prerequisites

**Core tools** (24 tools, mostly pre-installed):
- Python 3.8+ with pip3
- Node.js 14+ with npm
- Major language compilers (gcc, rustc, javac, etc.)

Check availability:
```bash
python3 scripts/verify_tools.py
```

**Extended dimension tools** (13 tools, optional):
```bash
# See which tools are missing
./scripts/install_extended_tools.sh

# Install by priority
./scripts/install_extended_tools.sh --all
```

See `docs/INSTALL_EXTENDED_DIMS.md` for detailed installation steps.

## Usage

### Basic Usage
```bash
# Evaluate current directory with default config
claude-code run quality-improvement

# Evaluate GitHub repo
claude-code run quality-improvement --target https://github.com/user/repo

# Custom config
claude-code run quality-improvement --config my-config.yaml --target /path/to/repo
```

### Advanced Options
```bash
# Run only 1 round (fast assessment)
claude-code run quality-improvement --max-rounds 1

# Disable early-stop (always run all rounds)
claude-code run quality-improvement --no-early-stop

# Use advanced config with extended dimensions
claude-code run quality-improvement --config config.advanced.yaml

# Dry-run: evaluate without making changes
claude-code run quality-improvement --dry-run
```

## Output Structure

```
.sessi-work/
├── round_1/
│   ├── scores/
│   │   ├── linting.json        # Dimension score + findings
│   │   ├── type_safety.json
│   │   └── ... (one per dimension)
│   ├── tools/
│   │   ├── linting.txt         # Raw tool output
│   │   ├── type_safety.txt
│   │   └── ... (one per dimension)
│   ├── round_1.json            # Round snapshot (all scores + deltas)
│   └── round_1.md              # Human-readable summary
├── round_2/
├── round_3/
└── final_report.md             # Trajectory across rounds
```

Each dimension score includes:
- `score` (0-100)
- `tool_score` (from tools only)
- `llm_score` (from LLM analysis)
- `findings[]` with evidence
- `gaps` (where falling short)
- `tool_outputs` (raw tool stdout)

## Examples

### Example 1: Quick Assessment (1 round)
```bash
cp config.example.yaml config.yaml
# Edit config.yaml: set max_rounds: 1
claude-code run quality-improvement
```

### Example 2: Full Framework (16 dimensions)
```bash
cp config.advanced.yaml config.yaml
./scripts/install_extended_tools.sh --all

# Edit config.yaml: enable desired extended dims
# Then run
claude-code run quality-improvement
```

### Example 3: Custom Targets
```bash
cp config.example.yaml config.yaml

# Edit config.yaml with custom targets:
# quality:
#   target: 90              # Stricter overall
# dimensions:
#   test_coverage:
#     target: 95           # Higher coverage requirement
#   security:
#     target: 95           # Stricter security

claude-code run quality-improvement
```

## Architecture

- **SKILL.md** — Entry point & execution contract
- **scripts/config_loader.py** — YAML → JSON resolver
- **scripts/setup_target.py** — Clone/setup working dir
- **scripts/score.py** — Weighted score computation
- **scripts/verify.py** — Anti-bias verification
- **scripts/checkpoint.py** — Round snapshots
- **prompts/evaluate_dimension.md** — Per-dimension protocol
- **prompts/improvement_plan.md** — Ranking & fixing
- **prompts/verify_round.md** — Cross-check & revert

See `docs/ARCHITECTURE.md` for full system design.

## Documentation

- **README.md** (this file) — Overview & quick start
- **docs/INSTALL_EXTENDED_DIMS.md** — Tool installation guide
- **docs/EXTENDED_DIMENSIONS.md** — Detailed guide for 7 new dims
- **docs/ANTI_BIAS.md** — Self-evaluation bias defenses
- **docs/ARCHITECTURE.md** — System design & components
- **docs/DIMENSIONS.md** — Detailed per-dimension guide
- **docs/USAGE.md** — Advanced usage patterns
- **EXTENDED_DIMS_STATUS.md** — Tool availability & prerequisites

## Performance

- **Standard config** (9 dims): ~5-15 min per round
- **Extended config** (16 dims): ~20-40 min per round
- **Total time** (3 rounds): 15-50 min depending on codebase size

Recommendation: Start with HIGH priority extended dims (mutation testing), add others as needed.

## Limitations

Framework automates tool-driven improvements across 16 quality dimensions. Cannot replace:
- Business logic correctness (requires domain knowledge)
- Real user experience testing (requires humans)
- Zero-day security discovery (requires expert analysis)
- Team-specific code style preferences

See `docs/ANTI_BIAS.md` for detailed automation ceiling analysis.

## Contributing

To extend with new dimensions:
1. Add dimension to `config.example.yaml` & `config.advanced.yaml`
2. Create evaluation protocol in `prompts/`
3. Update weight normalization in `scripts/score.py`
4. Document in `docs/DIMENSIONS.md`

## License

MIT License - See LICENSE file

## References

- Framework: Based on Karpathy's autoresearch pattern (`github.com/karpathy/autoresearch`)
- Quality model: Harness Engineering 9-dimension framework
- Implementation: Claude Code skill with Python orchestration + LLM evaluation
