#!/usr/bin/env python3
"""Compute weighted overall score from per-dim scores + resolved config.

Emits a structured JSON result: overall_score, meets_target,
failing_dimensions (sorted by impact), and a full breakdown.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def compute(scores: dict, config: dict) -> dict:
    dims = config["dimensions"]
    overall = 0.0
    failing = []
    breakdown = {}

    for name, dim in dims.items():
        if not dim.get("enabled", True):
            continue
        if name not in scores:
            sys.exit(f"score: missing score for enabled dimension '{name}'")
        s = int(scores[name])
        if not (0 <= s <= 100):
            sys.exit(f"score: dimension '{name}' out of range: {s}")
        w = dim["normalized_weight"]
        contrib = s * w
        overall += contrib
        meets = s >= dim["target"]
        breakdown[name] = {
            "score": s,
            "weight": dim["weight"],
            "normalized_weight": round(w, 4),
            "contribution": round(contrib, 2),
            "target": dim["target"],
            "meets": meets,
            "gap": max(0, dim["target"] - s),
            "impact": round(max(0, dim["target"] - s) * w, 3),
        }
        if not meets:
            failing.append({
                "dimension": name,
                "score": s,
                "target": dim["target"],
                "gap": dim["target"] - s,
                "impact": breakdown[name]["impact"],
            })

    failing.sort(key=lambda x: x["impact"], reverse=True)
    overall_score = round(overall, 2)
    meets_overall = overall_score >= config["overall_target"]
    meets_target = meets_overall and not failing

    return {
        "overall_score": overall_score,
        "overall_target": config["overall_target"],
        "meets_overall": meets_overall,
        "meets_target": meets_target,
        "failing_dimensions": failing,
        "breakdown": breakdown,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", required=True, help="JSON file mapping dimension_name → int")
    ap.add_argument("--config", required=True, help="JSON file from config_loader.py")
    args = ap.parse_args()

    scores = json.loads(Path(args.scores).read_text())
    config = json.loads(Path(args.config).read_text())
    print(json.dumps(compute(scores, config), indent=2))


if __name__ == "__main__":
    main()
