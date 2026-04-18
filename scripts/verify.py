#!/usr/bin/env python3
"""Verify a round's post-scores against pre-scores, tool outputs, and git diff.

Defends against LLM self-evaluation bias: the same agent that modified
the code also re-scores it. Without discipline, scores drift upward
without real gain. This script caps any dimension whose claimed
+delta > EVIDENCE_THRESHOLD is not supported by at least one of:

  - a material change in raw tool output for that dimension
  - a new file appearing on a dimension-relevant path
  - any code change under a dimension-relevant path

Emits a verified result with capped dimensions, re-computed overall,
and a 'verification' block listing caps, regressions, and evidence_ok.

The orchestrator uses verify.py's output — not the raw post result —
for early-stop and the final report.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


# A claimed increase greater than this requires evidence.
EVIDENCE_THRESHOLD = 10
# If evidence is missing, cap the score at pre + this.
CAP_DELTA = 3
# Minimum symmetric difference in tool-output lines to count as "material".
TOOL_DIFF_MIN_LINES = 3

# Path substrings that count as supporting evidence for each dimension.
EVIDENCE_PATHS: dict[str, list[str]] = {
    "test_coverage": [
        "test/", "tests/", "__tests__/", "spec/",
        ".test.", ".spec.", "_test.",
    ],
    "security": [
        # Dep files (version bumps patch vulnerabilities)
        "package.json", "package-lock.json", "requirements.txt",
        "pyproject.toml", "Pipfile", "poetry.lock",
        "go.sum", "Gemfile.lock", "Cargo.lock",
        # Attack-surface paths
        "auth", "security", "session", "crypto", "passwd", "token",
        "jwt", "oauth", "cors",
    ],
    "type_safety": [
        ".ts", ".tsx", ".py", ".pyi",
        "tsconfig.json", "mypy.ini", "pyrightconfig.json", "pyproject.toml",
    ],
    "documentation": [
        "README", ".md", "docs/", "CHANGELOG", ".rst",
    ],
    "linting": [
        ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs",
        ".eslintrc", ".prettierrc", "ruff.toml",
    ],
    "performance": [".ts", ".py", ".go", ".rs", ".js"],
    "readability": [".ts", ".py", ".go", ".rs", ".js"],
    "architecture": [".ts", ".py", ".go", ".rs", ".js"],
    "error_handling": [".ts", ".py", ".go", ".rs", ".js"],
}


def _run(cmd: list[str]) -> tuple[str, int]:
    try:
        p = subprocess.run(cmd, check=False, capture_output=True, text=True)
        return p.stdout, p.returncode
    except FileNotFoundError:
        return "", 127


def git_changed_files(target: Path, ref_from: str, ref_to: str) -> list[str]:
    out, rc = _run(["git", "-C", str(target), "diff", "--name-only",
                    f"{ref_from}..{ref_to}"])
    if rc != 0:
        return []
    return [l.strip() for l in out.splitlines() if l.strip()]


def path_evidence(dim: str, changed_files: list[str]) -> bool:
    markers = EVIDENCE_PATHS.get(dim)
    if not markers:
        return bool(changed_files)
    lower = [f.lower() for f in changed_files]
    return any(any(m.lower() in f for m in markers) for f in lower)


def tool_evidence(dim: str, pre_dir: Path | None, post_dir: Path | None) -> bool:
    if not (pre_dir and post_dir):
        return False
    pre_file = pre_dir / f"{dim}.txt"
    post_file = post_dir / f"{dim}.txt"
    if not (pre_file.exists() and post_file.exists()):
        return False
    pre_text = pre_file.read_text()
    post_text = post_file.read_text()
    if pre_text == post_text:
        return False
    pre_lines = set(pre_text.splitlines())
    post_lines = set(post_text.splitlines())
    return len(pre_lines.symmetric_difference(post_lines)) >= TOOL_DIFF_MIN_LINES


def verify(pre: dict, post: dict, target: Path,
           pre_tools: Path | None, post_tools: Path | None,
           ref_from: str | None, ref_to: str) -> dict:
    changed_files: list[str] = []
    if ref_from:
        changed_files = git_changed_files(target, ref_from, ref_to)

    capped: list[dict] = []
    regressions: list[dict] = []
    evidence_ok: list[str] = []

    verified_breakdown: dict[str, dict] = {}
    total = 0.0

    for name, post_d in post["breakdown"].items():
        pre_d = pre["breakdown"].get(name, {"score": post_d["score"]})
        pre_s = int(pre_d["score"])
        post_s = int(post_d["score"])
        delta = post_s - pre_s
        final_s = post_s

        if delta < 0:
            regressions.append({
                "dimension": name, "pre": pre_s, "post": post_s, "delta": delta,
            })
        elif delta > EVIDENCE_THRESHOLD:
            tool_ok = tool_evidence(name, pre_tools, post_tools)
            path_ok = path_evidence(name, changed_files)
            if not (tool_ok or path_ok):
                final_s = pre_s + CAP_DELTA
                capped.append({
                    "dimension": name,
                    "claimed": post_s,
                    "pre": pre_s,
                    "capped_to": final_s,
                    "reason": ("no material tool-output change AND no git diff "
                               "under dimension-relevant paths"),
                })
            else:
                evidence_ok.append(name)
        elif delta > 0:
            evidence_ok.append(name)

        w = post_d["normalized_weight"]
        contrib = final_s * w
        total += contrib

        verified_breakdown[name] = {
            **post_d,
            "score": final_s,
            "contribution": round(contrib, 2),
            "meets": final_s >= post_d["target"],
            "gap": max(0, post_d["target"] - final_s),
            "impact": round(max(0, post_d["target"] - final_s) * w, 3),
        }

    failing = [
        {"dimension": n, "score": d["score"], "target": d["target"],
         "gap": d["gap"], "impact": d["impact"]}
        for n, d in verified_breakdown.items() if not d["meets"]
    ]
    failing.sort(key=lambda x: x["impact"], reverse=True)

    overall = round(total, 2)
    meets_overall = overall >= post["overall_target"]
    meets_target = meets_overall and not failing

    return {
        "overall_score": overall,
        "overall_target": post["overall_target"],
        "meets_overall": meets_overall,
        "meets_target": meets_target,
        "failing_dimensions": failing,
        "breakdown": verified_breakdown,
        "verification": {
            "evidence_threshold": EVIDENCE_THRESHOLD,
            "cap_delta": CAP_DELTA,
            "capped": capped,
            "regressions": regressions,
            "evidence_ok": evidence_ok,
            "files_changed": len(changed_files),
            "ref_from": ref_from,
            "ref_to": ref_to,
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre", required=True, help="pre-round score.py result JSON")
    ap.add_argument("--post", required=True, help="post-round score.py result JSON")
    ap.add_argument("--target", required=True, help="TARGET_PATH")
    ap.add_argument("--pre-tools", default=None, help="dir of raw tool outputs pre")
    ap.add_argument("--post-tools", default=None, help="dir of raw tool outputs post")
    ap.add_argument("--ref-from", default=None,
                    help="git ref before improvements (e.g. round_<n>_start tag)")
    ap.add_argument("--ref-to", default="HEAD", help="git ref after improvements")
    args = ap.parse_args()

    pre = json.loads(Path(args.pre).read_text())
    post = json.loads(Path(args.post).read_text())
    target = Path(args.target).expanduser().resolve()
    pre_tools = Path(args.pre_tools).resolve() if args.pre_tools else None
    post_tools = Path(args.post_tools).resolve() if args.post_tools else None

    result = verify(pre, post, target, pre_tools, post_tools,
                    args.ref_from, args.ref_to)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
