# CRG Structural Reconnaissance Protocol

Runs **once per session**, after `setup_target.py` (graph already built/verified),
**before the first evaluation round**.

Provides a structural intelligence baseline that:
1. Pre-seeds the issue registry with structural findings the 17 dimensions cannot see
2. Guides dimension evaluation (which files/functions need deepest analysis)
3. Replaces blind first-round discovery with 9 targeted CRG queries (~3,900 tokens)
   vs. reading 10 files at random (~10,000 tokens)

---

## Step 0: Check CRG Availability

```bash
cat .sessi-work/crg_status.json
```

- `available: false` → **skip this entire protocol silently**. Proceed to Step 3a.
- `available: true` → proceed.

---

## Step 1: Orientation (~100 tokens)

Always the first CRG call — returns risk score, top communities, suggested next tools:

```
[USE mcp__code-review-graph__get_minimal_context_tool]
task: "structural reconnaissance before quality evaluation"
```

Record:
- `risk_score` (0.0–1.0) → overall repo structural risk
- `suggested_next_tools` → CRG's own recommended follow-up

---

## Step 2: Baseline Graph Metrics

```
[USE mcp__code-review-graph__list_graph_stats_tool]
```

Record to `crg_reconnaissance.json`:
- `node_count`, `edge_count`, `file_count`, `languages[]`, `last_updated`
- Flag stale graph if `last_updated` > 7 days behind latest commit

---

## Step 3: Auto-Generated Investigation Priorities

```
[USE mcp__code-review-graph__get_suggested_questions_tool]
```

Returns prioritized questions about:
- Bridge nodes needing tests
- Untested hub nodes
- Surprising cross-community coupling
- Thin (low-cohesion) communities
- Untested hotspots

Write all questions to `crg_reconnaissance.json` under `suggested_questions[]`.
These become investigation priorities that guide dimension evaluation depth.

---

## Step 4: High-Risk Components

```
[USE mcp__code-review-graph__get_hub_nodes_tool]
top_n: 15
include_metrics: true
```

```
[USE mcp__code-review-graph__get_bridge_nodes_tool]
```

Flag any hub node that also appears in `get_knowledge_gaps` (Step 6) as
**critical-risk**: high centrality + untested = highest-priority finding.

---

## Step 5: Module Cohesion Map

```
[USE mcp__code-review-graph__list_communities_tool]
sort_by: "cohesion"
min_size: 3
detail_level: "standard"
```

For each community with `cohesion < 0.4` OR `size > 50`, drill in:

```
[USE mcp__code-review-graph__get_community_tool]
community_name: "<name>"
include_members: true
```

**Interpret:**
- `cohesion < 0.4` — functions don't belong together → refactoring/split candidate
- `size > 50` — potential god-module → decomposition candidate
- `cohesion > 0.8` — healthy, well-organized module

Register each problematic community:

```bash
echo '{
  "severity": "medium",
  "message": "Low-cohesion community: <name> (cohesion=<score>, <N> members). Functions have weak internal coupling — split candidate.",
  "file": null,
  "line": null,
  "evidence": "CRG list_communities: cohesion=<score>"
}' > /tmp/finding.json
python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json architecture 0 /tmp/finding.json
```

---

## Step 6: Untested Hotspots

```
[USE mcp__code-review-graph__get_knowledge_gaps_tool]
```

Cross-reference with hub nodes from Step 4.
Hub nodes that appear in knowledge_gaps = **untested high-risk functions** — register as `high`:

```bash
echo '{
  "severity": "high",
  "message": "Hub node <function> is untested (knowledge gap). Fan-in: <N> callers — failure here cascades widely.",
  "file": "<file>",
  "line": null,
  "evidence": "CRG: hub rank=<N>, in knowledge_gaps=true"
}' > /tmp/finding.json
python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json test_coverage 0 /tmp/finding.json
```

Non-hub knowledge gaps → register as `medium` under `test_coverage`.

---

## Step 7: Unexpected Couplings

```
[USE mcp__code-review-graph__get_surprising_connections_tool]
```

For each surprising connection, assess:
- Expected pattern (plugin architecture, shared utility)? → skip
- Accidental cross-module dependency? → register

```bash
echo '{
  "severity": "medium",
  "message": "Unexpected coupling: <A> → <B> crosses module boundary (<community_a> → <community_b>). Creates hidden dependency.",
  "file": "<file_a>",
  "line": null,
  "evidence": "CRG get_surprising_connections: <description>"
}' > /tmp/finding.json
python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json architecture 0 /tmp/finding.json
```

---

## Step 8: Dead Code Detection

```
[USE mcp__code-review-graph__refactor_tool]
mode: "dead_code"
```

For each unreferenced function/class (no callers, no importers, not an entry point):

```bash
echo '{
  "severity": "low",
  "message": "Dead code: <name> in <file> — no callers, no importers, not an entry point.",
  "file": "<file>",
  "line": null,
  "evidence": "CRG refactor dead_code: zero callers + zero importers"
}' > /tmp/finding.json
python3 scripts/issue_tracker.py add \
  .sessi-work/issue_registry.json architecture 0 /tmp/finding.json
```

> If dead functions > 5% of total node count → escalate to `medium`.

---

## Step 9: Write Reconnaissance Report

Save to `.sessi-work/crg_reconnaissance.json`:

```json
{
  "timestamp": "<ISO8601>",
  "repo": "<repo_path>",
  "graph_stats": {
    "nodes": N,
    "edges": N,
    "files": N,
    "languages": []
  },
  "risk_score": 0.0,
  "suggested_questions": [...],
  "high_risk_hubs": [
    { "name": "<fn>", "file": "<path>", "fan_in": N, "untested": true }
  ],
  "low_cohesion_communities": [
    { "name": "<community>", "cohesion": 0.0, "size": N }
  ],
  "untested_hotspots": [...],
  "unexpected_couplings": [...],
  "dead_code": [...],
  "pre_seeded_issues": N,
  "evaluation_priorities": {
    "deepest_analysis_files": ["<file1>", "<file2>"],
    "dimensions_to_focus": ["test_coverage", "architecture"]
  }
}
```

---

## Step 10: Set Evaluation Priorities

Write `evaluation_priorities` to `crg_reconnaissance.json` based on findings:

```
IF untested_hotspots > 5        → test_coverage: deepest analysis
IF dead_code > 10 functions     → architecture: highest priority
IF low_cohesion_communities > 3 → architecture: highest priority
IF unexpected_couplings > 3     → architecture + readability: focus
IF risk_score > 0.7             → ALL Tier 3 dims: extra scrutiny
```

Claude reads `evaluation_priorities` in Step 3a to adjust analysis depth
per dimension — focusing tool runs and LLM reasoning on identified hotspots
rather than uniform full-codebase scans.

---

## Token Budget Reference

| Step | Tool | Est. tokens |
|------|------|-------------|
| 1 | `get_minimal_context` | ~100 |
| 2 | `list_graph_stats` | ~200 |
| 3 | `get_suggested_questions` | ~500 |
| 4 | `get_hub_nodes` + `get_bridge_nodes` | ~800 |
| 5 | `list_communities` + 2–3× `get_community` | ~800 |
| 6 | `get_knowledge_gaps` | ~600 |
| 7 | `get_surprising_connections` | ~400 |
| 8 | `refactor_tool(dead_code)` | ~500 |
| **Total** | | **~3,900** |

**Benchmark:** Reading 10 random files ≈ 10,000 tokens with no structural signal.
Reconnaissance delivers richer, targeted findings at **~60% lower token cost**.

---

## Graceful Degradation

If any individual tool call fails (CRG error, timeout):
- Log the failure in `crg_reconnaissance.json` under `tool_errors[]`
- Continue to next step — partial reconnaissance is better than none
- Never abort the entire quality run due to a CRG tool failure
