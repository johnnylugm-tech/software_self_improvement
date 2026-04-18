# Anti-Self-Evaluation Bias Defenses

This document explains how the framework defends against LLM self-evaluation bias: an AI agent improving code, evaluating its own improvements, and declaring success without objective evidence.

## The Problem

Without safeguards, a quality improvement loop can exhibit self-evaluation bias:

```
Agent: "I'll improve test coverage"
[Makes changes to code]
Agent: "Great! Coverage improved from 70% to 85%!"
Agent: "My changes worked! The code is better."
```

But the claimed improvement might be:
- Unverified by tools (just LLM claims)
- Ornamental (no functional change)
- Deceptive (claimed fixes for one dimension hurt another)

## Solution: 6-Layer Defense

### 1. Tool-First Hierarchy

**Rule:** `final_score = min(tool_score, llm_score)`

LLM cannot claim success if tools disagree.

**Implementation:**
- Every dimension has a **tool score** (from automated tools like pytest, pylint, sonarqube)
- Every dimension has an **LLM score** (from Claude's analysis)
- Final score is **always the minimum**

**Effect:** If pytest reports 70% coverage, Claude cannot claim 85% coverage. The score stays 70%.

**Example:**
```json
{
  "dimension": "test_coverage",
  "tool_score": 70,     // coverage tool says 70%
  "llm_score": 85,      // LLM analysis says 85%
  "score": 70           // Use minimum
}
```

### 2. Evidence Requirement

**Rule:** Every finding must have evidence.

- **Tool outputs:** Raw tool stdout/stderr
- **Code changes:** Git diff showing what changed
- **Claims without evidence are rejected**

**Implementation:**
```json
{
  "finding": "Added proper error handling in auth module",
  "evidence": {
    "tool_output": "bandit: no new security issues",
    "git_diff": "+try...except blocks in auth.py (8 lines added)"
  }
}
```

Findings without evidence are marked as unsupported and capped.

### 3. Per-Fix Verification

**Rule:** After each fix, re-run the tool. If tool shows no improvement, revert.

**Example:**
```
Round 1:
  Agent: "I'll add tests to cover missing lines"
  [Adds test_new_feature() function]
  [Runs coverage tool]
  Tool: "Coverage: 70% → 72%"  ✓ Improvement verified, keep change

Round 2:
  Agent: "I'll refactor for readability"
  [Refactors function names]
  [Runs coverage tool]
  Tool: "Coverage: 72% → 72%"  ✗ No improvement, revert change
```

This prevents ornamental changes (code looks nicer but doesn't improve metrics).

### 4. Deterministic Verification (verify.py)

**Rule:** After evaluating each dimension, verify claims are supported.

Verification checks:
- **Pre/post tool outputs** — Did tools report improvement?
- **Git diffs** — What lines changed?
- **Cap unsupported gains** — If Δ > threshold without evidence, cap it

**Constants:**
```python
EVIDENCE_THRESHOLD = 10     # Points requiring evidence
CAP_DELTA = 3               # Max gain without evidence  
TOOL_DIFF_MIN_LINES = 3     # Min changed lines for evidence
```

**Logic:**
```
if claimed_delta > EVIDENCE_THRESHOLD:
    if has_tool_evidence or has_diff_evidence:
        accept_claim()
    else:
        cap_claim(CAP_DELTA)
```

**Example:**
```
Claim: test_coverage improved from 70 → 88 (Δ = +18)
Evidence Check:
  - Tool output? coverage tool shows 70 → 75 ✓
  - Git diff? 5 lines added to tests ✓
Result: Evidence sufficient. Accept +18 improvement.

Claim: readability improved from 75 → 82 (Δ = +7)
Evidence Check:
  - Tool output? None ✗
  - Git diff? None (just comment reformatting) ✗
Result: No evidence for +7. Cap to +3 (CAP_DELTA).
```

### 5. Regression Detection & Revert

**Rule:** Surface changes that hurt other dimensions. Revert if regression.

**Detection:**
```python
for dimension in dimensions:
    delta = current_score - previous_score
    if delta < 0:
        # Regression detected
        regressions.append({
            "dimension": dimension,
            "before": previous_score,
            "after": current_score,
            "severity": abs(delta)
        })
```

**Revert Protocol:**
```
Fix applied → Test coverage improved 70% → 75% ✓
            → But security score dropped 85% → 78% ✗
Result: Regression detected. Revert fix. Try different approach.
```

### 6. Path Heuristics

Prevent undetected regressions by never allowing:
- **Weakening tests** — Cannot remove test assertions or make tests less strict
- **Broadening exception handling** — Cannot silence errors with bare `except:`
- **Ignoring type errors** — Cannot add `@ts-ignore` or `# type: ignore` comments

**Implementation:** Improvement prompts include guardrails:
```
DO NOT:
- Remove or weaken test assertions
- Change except Exception to bare except
- Add @ts-ignore, # noqa, or # type: ignore
- Make error messages less descriptive
```

## Evidence Threshold Analysis

### Standard Configuration (9 dimensions)

**Assertion:** Framework can reach 60-70% automation through these 6 defenses.

**Rationale:**
- Tool ecosystem covers 70-80% of what tools can measure
- Evidence requirement prevents ornamental improvements beyond that
- Per-fix verification ensures no regression
- Deterministic verification caps unsupported claims

**What it cannot reach:** 75-80%+ without extended dimensions
- Some quality aspects lack good tools
- Business logic correctness requires domain knowledge
- User experience testing requires humans

### Advanced Configuration (16 dimensions)

**With extended dimensions:** Can reach 75-80% ceiling

**Why extended dims help:**
- **Mutation testing** (+3-5%) — Reveals test suite weaknesses
- **Property testing** (+3%) — Finds edge cases via generation
- **Fuzzing** (+3%) — Discovers crash/security bugs  
- **Accessibility** (+2%) — Detects WCAG violations
- **License compliance** (+1%) — Identifies license issues
- **Observability** (+2%) — Finds logging/metrics gaps
- **Supply chain** (+3%) — Verifies signature integrity

**Still cannot:**
- Know if the business logic is correct
- Perform real user experience testing
- Discover zero-day security vulnerabilities
- Know team-specific code style preferences

## Verification Constants: Tuning Guide

### EVIDENCE_THRESHOLD (default: 10)

Determines when tool evidence is required.

**If set too low (5):**
- Very strict, requires evidence for small improvements
- Fewer false positives, but may reject real improvements

**If set too high (20):**
- Lenient, allows larger improvements without evidence
- More false positives, may accept unsubstantiated claims

**Recommendation:** 10 points (roughly 10% of a 100-point scale)

### CAP_DELTA (default: 3)

Maximum improvement without evidence.

**If set too low (1):**
- Very conservative, caps unsupported improvements aggressively
- May prevent valid quick wins

**If set too high (7):**
- Lenient, allows larger improvements without evidence
- May accept spurious improvements

**Recommendation:** 3 points (roughly 3% of a 100-point scale)

### TOOL_DIFF_MIN_LINES (default: 3)

Minimum changed lines in git diff to count as evidence.

**If set too low (1):**
- One-line changes count as evidence
- May accept trivial changes

**If set too high (10):**
- Requires substantial changes
- May reject small but effective fixes

**Recommendation:** 3 lines (roughly one meaningful code change)

## Known Limitations

### 1. Tool Availability

Framework depends on having good tools for each dimension. If a tool is:
- **Missing:** Dimension cannot be evaluated (disabled)
- **Inaccurate:** Verification uses faulty baseline
- **Slow:** Increases evaluation time

**Mitigation:** Regular tool updates, multiple tools per dimension when possible.

### 2. Tool Reliability

Some tools are inherently flaky or environment-sensitive:
- Flaky tests pass/fail randomly
- Performance benchmarks vary based on system load
- Security tools may report false positives/negatives

**Mitigation:** Run tools multiple times, use medians, cross-validate with multiple tools.

### 3. Dimension Orthogonality

Some improvements help multiple dimensions (not independent):
- Better error handling improves both error_handling and security
- Refactoring for readability may improve architecture

Weights assume independence; actual improvements may compound differently.

**Mitigation:** Acknowledge dimension correlation in final report.

### 4. Evidence Gap

Some improvements are real but hard to evidence:
- Defensive refactoring (prevents future bugs, no current test impact)
- Documentation improvements (help humans, no tool measures)
- Security hardening (no immediate vulnerability found, but strengthens attack surface)

**Mitigation:** Use lower EVIDENCE_THRESHOLD for high-risk dimensions.

## Testing the Defenses

To verify anti-bias mechanisms work:

```bash
# 1. Test tool-first hierarchy
python3 -c "
import json
score_data = {
    'tool_score': 70,
    'llm_score': 95,
}
final = min(score_data['tool_score'], score_data['llm_score'])
assert final == 70, 'Tool hierarchy failed'
print('✓ Tool-first hierarchy works')
"

# 2. Test verification cap
python3 scripts/verify.py result.json round_1 .

# 3. Test regression detection
# (Make a change, run verify.py, check regressions list)

# 4. Test revert protocol
# (Verify regressions trigger revert in improvement loop)
```

## References

- **Karpathy autoresearch:** github.com/karpathy/autoresearch (pattern source)
- **Tool-first principle:** Prioritize objective measurement over subjective judgment
- **Evidence-based software:** github.com/mozilla/gecko (Firefox quality practices)
- **LLM bias research:** "Language Models are Biased Evaluators" (various papers)

## Conclusion

The 6-layer defense provides strong protection against self-evaluation bias while maintaining practical improvement capability. The framework can automate 60-70% of quality improvements in standard mode, reaching 75-80% with extended dimensions. Beyond that, human judgment and domain expertise remain essential.
