#!/usr/bin/env python3
"""
Score Aggregation: Computes weighted overall score from per-dimension scores

Identifies failing dimensions sorted by impact (gap × normalized_weight).
Outputs JSON with overall_score, meets_target, failing_dimensions, breakdown.

Issue-driven completion: surfaces open_critical_count / open_high_count from
the issue registry so early-stop can gate on quality, not score alone.
"""

import sys
import json
from pathlib import Path

# Local import for issue registry integration
sys.path.insert(0, str(Path(__file__).parent))
try:
    import issue_tracker
except ImportError:
    issue_tracker = None


def load_scores(round_dir):
    """
    Load all dimension scores from round directory

    Expected: .sessi-work/round_<n>/scores/*.json
    Each file contains: {"dimension": "...", "score": 0-100, ...}
    """
    scores_dir = Path(round_dir) / "scores"
    if not scores_dir.exists():
        raise FileNotFoundError(f"Scores directory not found: {scores_dir}")

    scores = {}
    for score_file in sorted(scores_dir.glob("*.json")):
        with open(score_file, "r") as f:
            dim_score = json.load(f)
            dim_name = dim_score["dimension"]
            scores[dim_name] = dim_score

    if not scores:
        raise ValueError(f"No score files found in {scores_dir}")

    return scores


def compute_overall_score(scores, config, registry=None):
    """
    Compute weighted overall score from per-dimension scores

    Args:
        scores: dict of dimension_name -> {score, tool_score, llm_score, ...}
        config: resolved config with dimensions and weights
        registry: optional issue-registry dict for open-issue counts

    Returns:
        {
            "overall_score": float (0-100),
            "meets_target": bool,          # score gate only
            "quality_complete": bool,      # score gate AND no open critical/high
            "score_gate": int,
            "open_critical_count": int,
            "open_high_count": int,
            "open_medium_count": int,
            "open_total": int,
            "failing_dimensions": [...],
            "breakdown": {...}
        }
    """
    dimensions = config["dimensions"]
    # Support both legacy `target` and new `score_gate` naming
    quality_cfg = config.get("quality", {})
    score_gate = quality_cfg.get("score_gate", quality_cfg.get("target", 85))

    breakdown = {}
    weighted_sum = 0
    weight_sum = 0

    for dim_name, dim_config in dimensions.items():
        if not dim_config.get("enabled", False):
            continue

        if dim_name not in scores:
            raise ValueError(f"Missing score for dimension: {dim_name}")

        dim_score = scores[dim_name]
        score = dim_score.get("score", 0)
        weight = dim_config["weight"]

        weighted_score = score * weight
        weighted_sum += weighted_score
        weight_sum += weight

        dim_target = dim_config.get("target", 100)
        gap = max(0, dim_target - score)

        breakdown[dim_name] = {
            "score": score,
            "target": dim_target,
            "gap": gap,
            "weight": weight,
            "weighted_score": weighted_score,
        }

    # Overall score (normalized by enabled weights)
    overall_score = weighted_sum / weight_sum if weight_sum > 0 else 0

    # Identify failing dimensions (sorted by impact = gap × weight)
    failing = []
    for dim_name, dim_info in breakdown.items():
        if dim_info["gap"] > 0:
            impact = dim_info["gap"] * dim_info["weight"]
            failing.append(
                {
                    "dimension": dim_name,
                    "score": dim_info["score"],
                    "target": dim_info["target"],
                    "gap": dim_info["gap"],
                    "weight": dim_info["weight"],
                    "impact": impact,
                }
            )

    # Sort by impact descending
    failing.sort(key=lambda x: x["impact"], reverse=True)

    # Issue-registry integration (issue-driven completion)
    open_critical = open_high = open_medium = open_total = 0
    if registry is not None and issue_tracker is not None:
        s = issue_tracker.summary(registry)
        open_critical = s.get("open_critical", 0)
        open_high = s.get("open_high", 0)
        open_medium = s.get("open_medium", 0)
        open_total = s.get("open_total", 0)

    meets_score_gate = overall_score >= score_gate
    quality_complete = meets_score_gate and open_critical == 0 and open_high == 0

    return {
        "overall_score": round(overall_score, 2),
        "score_gate": score_gate,
        "target": score_gate,  # legacy alias for backward compat
        "meets_target": meets_score_gate,
        "quality_complete": quality_complete,
        "open_critical_count": open_critical,
        "open_high_count": open_high,
        "open_medium_count": open_medium,
        "open_total": open_total,
        "failing_dimensions": failing,
        "breakdown": breakdown,
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <round_dir> [config.json] [issue_registry.json]")
        print("  round_dir: path to .sessi-work/round_<n>")
        print("  config.json: resolved config (optional, uses defaults if omitted)")
        print("  issue_registry.json: persistent issue registry (optional)")
        sys.exit(1)

    round_dir = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None
    registry_path = sys.argv[3] if len(sys.argv) > 3 else None

    try:
        # Load scores
        scores = load_scores(round_dir)

        # Load config
        if config_path:
            with open(config_path, "r") as f:
                config = json.load(f)
        else:
            # Use minimal defaults if no config provided
            config = {
                "quality": {"score_gate": 85},
                "dimensions": {
                    dim: {"enabled": True, "weight": 1.0 / len(scores)}
                    for dim in scores.keys()
                },
            }

        # Load issue registry (optional but recommended)
        registry = None
        if registry_path and Path(registry_path).exists() and issue_tracker is not None:
            registry = issue_tracker.load(registry_path)
        elif issue_tracker is not None:
            # Default location: <round_dir>/../issue_registry.json
            default_reg = Path(round_dir).parent / "issue_registry.json"
            if default_reg.exists():
                registry = issue_tracker.load(str(default_reg))

        # Compute score
        result = compute_overall_score(scores, config, registry=registry)

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
