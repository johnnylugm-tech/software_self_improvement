# Evaluate Dimension Protocol

Evaluate a single quality dimension using the **tool-first hierarchy** and **LLM tier routing** to minimize token cost while preserving accuracy.

---

## Step 0: Route to Correct LLM

Before anything else, determine which LLM tier to use:

```bash
python3 scripts/llm_router.py <dimension> [tool_output.txt]
```

Read the `tier` and `provider` fields:

| Tier | Provider | Dimensions | Action |
|------|----------|-----------|--------|
| 1 | `gemini` | linting, type_safety, test_coverage, secrets_scanning, license_compliance, mutation_testing | Use `mcp__gemini-cli__ask-gemini` |
| 2 | `gemini` | security | Use `mcp__gemini-cli__ask-gemini` |
| 3 | `claude_native` | architecture, readability, error_handling, documentation, performance | Use Claude reasoning (this session) |

**NEVER** use Claude for Tier 1/2 dimensions. **NEVER** use Gemini for Tier 3.

---

## Step 1: Run Tools

Run all tools for this dimension. Save raw output:

```bash
# Output path: .sessi-work/round_<n>/tools/<dimension>.txt
```

**Tool commands by dimension:**

### linting (Tier 1)
```bash
pylint src/ --output-format=json 2>&1 | head -200
eslint src/ --format json 2>&1 | head -200
```

### type_safety (Tier 1)
```bash
pyright src/ --outputjson 2>&1 | head -200
```

### test_coverage (Tier 1)
```bash
coverage run -m pytest && coverage report --format=json
nyc --reporter=json npm test
```

### security (Tier 2)
```bash
bandit -r src/ -f json 2>&1 | head -300
npm audit --json 2>&1 | head -200
```

### secrets_scanning (Tier 1)
```bash
gitleaks detect --source . --report-format json
detect-secrets scan . --baseline .secrets.baseline
```

### license_compliance (Tier 1)
```bash
scancode --license --json-pp - src/ | head -300
```

### mutation_testing (Tier 1)
```bash
# Enforce time budget from config: time_budget_seconds
timeout $TIME_BUDGET mutmut run 2>&1
mutmut results 2>&1 | head -100
```

### architecture (Tier 3)
```bash
radon cc src/ -j 2>&1 | head -200
# LLM must analyze module coupling, layering, SOLID violations
```

### readability (Tier 3)
```bash
radon mi src/ -j 2>&1 | head -100
# LLM must assess naming clarity, function length, nesting depth
```

### error_handling (Tier 3)
```bash
# No reliable tool — LLM must scan for bare except, silent failures
grep -rn "except:" src/ | head -50
grep -rn "pass$" src/ | head -50
```

### documentation (Tier 3)
```bash
pydocstyle src/ 2>&1 | head -100
interrogate src/ -v 2>&1 | head -100
# LLM must assess quality, not just presence
```

### performance (Tier 3)
```bash
radon cc src/ -j --min C 2>&1 | head -100  # Complex functions
# LLM must identify actual bottlenecks
```

---

## Step 2: Evaluate (LLM Tier Routing)

### IF Tier 1 or Tier 2 → Call Gemini Flash

Get the prompt from the router:
```bash
python3 scripts/llm_router.py <dimension> .sessi-work/round_<n>/tools/<dimension>.txt
```

Use `gemini_prompt` field from output. Call Gemini:

```
[USE mcp__gemini-cli__ask-gemini]
model: gemini-2.5-flash
prompt: <gemini_prompt from router output>
```

Parse the JSON response. The Gemini response IS the dimension score.

**Token budget:** ≤ 8K input, ≤ 800 output (enforced by router prompt template)

---

### IF Tier 3 → Evaluate with Claude (this session)

Read tool output from `.sessi-work/round_<n>/tools/<dimension>.txt`.

**Perform full evaluation:**

1. **Tool score** — What do the tools report? Extract numeric signal (0-100).
2. **LLM score** — Your independent assessment from reading the code.
3. **Reconcile** — `score = min(tool_score, llm_score)` — never inflate.
4. **Evidence** — Every finding must cite file:line or tool output excerpt.
5. **Gaps** — What specifically is missing or broken?

**Token discipline for Tier 3:**
- Read only the most relevant code sections (not entire codebase)
- Use tool output as primary lens; read source only to confirm/locate
- Keep findings list ≤ 7 items

---

## Step 3: Write Score File

Save to `.sessi-work/round_<n>/scores/<dimension>.json`:

```json
{
  "dimension": "<name>",
  "round": <n>,
  "llm_tier": <1|2|3>,
  "llm_provider": "gemini|claude_native",
  "tool_score": <0-100>,
  "llm_score": <0-100>,
  "score": <min(tool_score, llm_score)>,
  "findings": [
    {
      "line": <int|null>,
      "severity": "critical|warning|info",
      "message": "<description>",
      "evidence": "<tool output excerpt or file:line>"
    }
  ],
  "gaps": ["<gap 1>", "<gap 2>"],
  "tool_outputs": "<path to raw tool output>",
  "reconcile": "tool_first"
}
```

---

## Anti-Bias Rules (All Tiers)

1. `score = min(tool_score, llm_score)` — no exceptions
2. Every finding needs `evidence` field — no bare assertions
3. If tool gives no output (tool missing/error) → `tool_score = null`, use `llm_score` only, flag in score file
4. Δ > 10 from previous round requires tool evidence or ≥ 3 lines of git diff
5. Tier 1/2 evaluations: trust the tool output — Gemini's role is only to parse and structure it

---

## Token Cost Reference

| Tier | Provider | Typical cost/dim | Use case |
|------|----------|-----------------|---------|
| 1 | Gemini Flash | ~$0.001 | Tool summarization |
| 2 | Gemini Flash | ~$0.002 | Light judgment |
| 3 | Claude Sonnet | ~$0.08 | Deep reasoning |

**Total per round (12 dims + improve):**
- Tier 1×6 + Tier 2×1: ~$0.01
- Tier 3×5: ~$0.40
- Improve step: ~$0.45
- **Total: ~$0.86/round** (vs ~$3.00 all-Claude)
