#!/usr/bin/env python3
"""Load & validate the skill's YAML config. Emits resolved JSON to stdout.

Merges user YAML over DEFAULTS, renormalises weights across enabled
dimensions, and applies fallback per-dimension targets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("config_loader: PyYAML required — run `pip install pyyaml`")


DEFAULTS = {
    "rounds": 3,
    "overall_target": 85,
    "dimension_target": 85,
    "early_stop": {"enabled": True},
    "git": {
        "commit_per_round": True,
        "branch": "quality/auto-research",
        "push": False,
    },
    "reporting": {"output_dir": "reports", "formats": ["markdown", "json"]},
}

DEFAULT_DIMS = {
    "linting":        {"enabled": True, "weight": 0.10, "tools": ["eslint", "ruff", "flake8", "prettier"]},
    "type_safety":    {"enabled": True, "weight": 0.15, "tools": ["tsc", "mypy", "pyright"]},
    "test_coverage":  {"enabled": True, "weight": 0.20, "tools": ["pytest-cov", "jest", "vitest", "go-cover"]},
    "security":       {"enabled": True, "weight": 0.15, "tools": ["bandit", "semgrep", "trivy", "gitleaks"]},
    "performance":    {"enabled": True, "weight": 0.10, "tools": ["radon-cc"]},
    "architecture":   {"enabled": True, "weight": 0.10, "tools": ["llm-judge"]},
    "readability":    {"enabled": True, "weight": 0.10, "tools": ["radon-mi"]},
    "error_handling": {"enabled": True, "weight": 0.05, "tools": ["llm-judge"]},
    "documentation":  {"enabled": True, "weight": 0.05, "tools": ["interrogate", "llm-judge"]},
}


def deep_merge(base, override):
    if override is None:
        return base
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    out = dict(base)
    for k, v in override.items():
        out[k] = deep_merge(out.get(k), v) if k in out else v
    return out


def resolve(path: str | None) -> dict:
    cfg = deep_merge({**DEFAULTS, "dimensions": DEFAULT_DIMS}, {})
    if path:
        p = Path(path).expanduser().resolve()
        if not p.is_file():
            sys.exit(f"config_loader: file not found: {p}")
        with p.open() as f:
            user = yaml.safe_load(f) or {}
        cfg = deep_merge(cfg, user)

    if "target" not in cfg or not cfg["target"]:
        sys.exit("config_loader: `target` (type + location) is required")
    t = cfg["target"]
    if t.get("type") not in ("folder", "github"):
        sys.exit("config_loader: target.type must be 'folder' or 'github'")
    if not t.get("location"):
        sys.exit("config_loader: target.location is required")

    enabled = {k: d for k, d in cfg["dimensions"].items() if d.get("enabled", True)}
    if not enabled:
        sys.exit("config_loader: no enabled dimensions")
    total_w = sum(d.get("weight", 0) for d in enabled.values())
    if total_w <= 0:
        sys.exit("config_loader: enabled dimensions have non-positive total weight")
    for d in enabled.values():
        d["normalized_weight"] = d["weight"] / total_w

    for d in cfg["dimensions"].values():
        d.setdefault("target", cfg["dimension_target"])

    if not (1 <= int(cfg["rounds"]) <= 50):
        sys.exit("config_loader: rounds must be in [1, 50]")
    if not (1 <= int(cfg["overall_target"]) <= 100):
        sys.exit("config_loader: overall_target must be in [1, 100]")

    return cfg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("config", nargs="?", default=None,
                    help="path to YAML config; omit for built-in defaults (target required somewhere)")
    args = ap.parse_args()
    print(json.dumps(resolve(args.config), indent=2))


if __name__ == "__main__":
    main()
