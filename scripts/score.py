#!/usr/bin/env python3
"""
Score Aggregation: Computes weighted overall score from per-dimension scores

Identifies failing dimensions sorted by impact (gap × normalized_weight).
Outputs JSON with overall_score, meets_target, failing_dimensions, breakdown.
"""

import sys
import json
from pathlib import Path


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


def compute_overall_score(scores, config):
    """
    Compute weighted overall score from per-dimension scores

    Args:
        scores: dict of dimension_name -> {score, tool_score, llm_score, ...}
        config: resolved config with dimensions and weights

    Returns:
        {
            "overall_score": float (0-100),
            "meets_target": bool,
            "target": int,
            "failing_dimensions": [
                {"dimension": "...", "score": X, "gap": Y, "impact": Z, "weight": W}
            ],
            "breakdown": {
                "dimension_name": {
                    "score": float,
                    "weight": float,
                    "weighted_score": float,
                    "target": int,
                    "gap": int
                }
            }
        }
    """
    dimensions = config["dimensions"]
    target = config["quality"]["target"]

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

    return {
        "overall_score": round(overall_score, 2),
        "target": target,
        "meets_target": overall_score >= target,
        "failing_dimensions": failing,
        "breakdown": breakdown,
    }


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <round_dir> [config.json]")
        print("  round_dir: path to .sessi-work/round_<n>")
        print("  config.json: resolved config (optional, uses defaults if omitted)")
        sys.exit(1)

    round_dir = sys.argv[1]
    config_path = sys.argv[2] if len(sys.argv) > 2 else None

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
                "quality": {"target": 85},
                "dimensions": {
                    dim: {"enabled": True, "weight": 1.0 / len(scores)}
                    for dim in scores.keys()
                },
            }

        # Compute score
        result = compute_overall_score(scores, config)

        print(json.dumps(result, indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
