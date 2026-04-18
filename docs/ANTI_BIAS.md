# Anti-Self-Deception Mechanics

> The agent that edits your code will also score it. Treat that as a threat model.

This document explains the specific biases this skill defends against, the mechanism for each, and the ways you can verify the defences are actually doing something.

---

## Coverage assertion (revised)

**Standard 9 dimensions** automate **60–70%** of observable quality checks.

**With the 7 extended dimensions** (`config.advanced.yaml`) enabled, the ceiling rises to **75–80%**.

What the 7 extended dims add:

| Extended dimension | Automation gain | Still requires humans/production |
|---|---|---|
| Mutation testing | +5% | Whether the tested property is the *right* one |
| Property testing | +3% | Whether the generated property itself is correct |
| Fuzzing | +3% | Business logic bugs; design flaws |
| License compliance | +3% | Post-release supply-chain compromise |
| Accessibility | +1% | 70% of a11y; real users with assistive tech |
| Observability | +2% | Whether signals are useful in real incidents |
| Supply chain | +3% | Zero-days; novel adversarial attacks |

**The invariant that doesn’t change**: all 16 dimensions read source code and tool output. None creates knowledge from outside the codebase. Business logic correctness, real user experience, zero-days, and production signal quality all require data sources no tool can substitute.

The remaining **15–20%** requires:
- **Production signals**: real error rates, p99 latency, incident telemetry
- **Domain experts**: “is this the right business behaviour?” has no answer in source code
- **Real users**: usability, a11y beyond automation, onboarding friction
- **Real attackers**: zero-days, creative IDOR, business-logic-specific exploits
- **The team itself**: maintainability for *these* people, bus factor, cognitive load

*Auto-research can run unlimited rounds. It still cannot observe what it has never been given.*

---

## The threat model

When the same LLM evaluates → modifies → re-evaluates a codebase, three failure modes are common:

1. **Optimistic drift.** The agent gradually relaxes its own rubric. "Reasonably clean" becomes 85 where last round it was 75, without the code changing in ways that justify it.
2. **Ornamental improvement.** The agent makes visible but score-irrelevant edits (rename variables, reformat comments) and claims they moved a rubric dimension.
3. **Target myopia.** Improvements to a low-scoring dimension accidentally regress another — and the agent doesn't notice because its attention is on the current target.

None of these are malice. They're what you get when the judge, the player, and the referee are the same model.

---

## Defences, in order of strength

### 1. Tool-first hierarchy

For every dimension with a static analyser (linting, type_safety, test_coverage, security, performance, readability, documentation), the **tool score is canonical**. LLM judgement can only *lower* the final score, never raise it.

```
final_score = min(tool_score, llm_score) when both exist
final_score = tool_score if LLM didn’t score
final_score = llm_score ONLY if no tool ran (architecture, error_handling, observability)
```

Implemented in `prompts/evaluate_dimension.md` §4.

### 2. Evidence requirement

Every `finding` must include an `evidence` field: a `file:line` reference, a quoted code fragment, or a tool output line. Findings without evidence are invalid and removed before scoring. Implemented in `prompts/evaluate_dimension.md` §3.

### 3. Per-fix tool verification

During the improve phase, **each fix is verified individually**:

```
apply fix → re-run the dim’s primary tool →
  if tool score regressed or unchanged: git checkout -- <files>  (revert this fix)
  if tool score improved: git commit
```

A round’s measured delta is the sum of individually-measured deltas, not an LLM claim. Implemented in `prompts/improvement_plan.md` §4.

### 4. Deterministic verify step

After the round’s fresh evaluation, `scripts/verify.py` runs without the LLM. It compares:

- Per-dim raw tool output (pre vs post).
- Git file changes between `round_<n>_start` and `HEAD`, filtered by dimension-relevant paths.

Any dimension where claimed `+delta > 10` has **neither** a material tool-output change **nor** a relevant file diff is capped at `pre + 3`. The capped `verified.json` — not the raw post — drives the early-stop decision.

Implemented in `scripts/verify.py`. The thresholds (`EVIDENCE_THRESHOLD = 10`, `CAP_DELTA = 3`) are at the top of the file.

### 5. Regression surfacing

`verify.py` also emits a `regressions` array listing any dimension where `post < pre`. `prompts/verify_round.md` §3 defines the revert protocol: re-run the regressed tool to confirm, identify the commit with `git log round_<n>_start..HEAD`, revert it, re-score. The revert is recorded in the round report.

### 6. Cross-dimension path heuristics

For each dimension, `verify.py` knows which paths make changes “real”:

| Dimension | Evidence paths |
|---|---|
| test_coverage | `test/`, `tests/`, `__tests__/`, `spec/`, `.test.`, `.spec.`, `_test.` |
| security | `package-lock.json`, `requirements.txt`, `poetry.lock`, `auth`, `crypto`, `session`, `jwt`, etc. |
| type_safety | `.ts`, `.py`, `tsconfig.json`, `mypy.ini`, `pyrightconfig.json` |
| documentation | `README`, `.md`, `docs/`, `CHANGELOG`, `.rst` |
| mutation_testing | test file paths (same as test_coverage) |
| license_compliance | `package.json`, `requirements.txt`, `go.sum`, `Cargo.lock`, `Gemfile.lock` |
| supply_chain | same as license_compliance + `Dockerfile`, `*.lock` |
| accessibility | `.html`, `.jsx`, `.tsx`, `.vue`, `.svelte` |
| linting / performance / readability / architecture / error_handling | code file extensions |

---

## How to verify the defences are working

After any run:

1. Open `reports/round_<n>.md` and any `reports/round_<n>.json`. Look for the `verification` block.
2. If every round shows `capped: []`, either the agent was well-behaved **or** the defences never fired. Check the score deltas: if a dim moved > 10 and `capped` is empty, tool-output or git diff evidence should also be visible.
3. Diff the raw tool outputs yourself: `diff .sessi-work/round_<n-1>/tools/<dim>.txt .sessi-work/round_<n>/tools/<dim>.txt`. If it's empty but that dim's score moved significantly, raise the threshold or investigate.
4. `git -C "$TARGET_PATH" log baseline..HEAD --stat` — every commit should be tied to a specific fix with a measurable delta, not "round N improvements" as one blob.

---

## Known limits

- For `architecture`, `error_handling`, and `observability`, only LLM scoring is available. These dimensions are most vulnerable to drift; weight them accordingly.
- A determined agent could edit a test to generate output that looks like new assertions without really testing anything. Defence-in-depth: the per-fix tool verification catches it if coverage or mutation-testing tools are wired up.
- The path heuristics are English-language and extension-based. If your project uses unusual layouts, override `EVIDENCE_PATHS` at the top of `scripts/verify.py`.

---

## The `EVIDENCE_THRESHOLD` knob

At the top of `scripts/verify.py`:

```python
EVIDENCE_THRESHOLD = 10   # deltas larger than this require evidence
CAP_DELTA = 3             # unsupported deltas are capped at pre + this
TOOL_DIFF_MIN_LINES = 3   # material tool-output change = this many symmetric-diff lines
```

- Lower `EVIDENCE_THRESHOLD` for a stricter run (e.g. 5).
- Raise `CAP_DELTA` if you find genuine small improvements are being over-punished.
- Raise `TOOL_DIFF_MIN_LINES` if your tools produce noisy output that trips false positives.
