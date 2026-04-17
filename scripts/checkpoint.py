#!/usr/bin/env python3
"""Persist per-round and final quality-improvement reports.

Per-round: writes both `round_<n>.json` (raw result) and a markdown
summary to the chosen --out path.

Final: aggregates all round_*.json in --reports-dir and writes a
trajectory report (initial vs final, per-dimension deltas).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def round_report(n: int, result: dict) -> str:
    lines = [
        f"# Round {n} — Quality Report",
        "",
        f"Generated: {_now()}",
        "",
        f"- **Overall score:** {result['overall_score']} / target {result['overall_target']}",
        f"- **Meets overall target:** {'yes' if result['meets_overall'] else 'no'}",
        f"- **Meets all targets (overall + per-dim):** {'yes' if result['meets_target'] else 'no'}",
        "",
        "## Dimensions",
        "",
        "| Dimension | Score | Target | Weight | Contribution | Meets |",
        "|---|---|---|---|---|---|",
    ]
    for name, d in result["breakdown"].items():
        lines.append(
            f"| {name} | {d['score']} | {d['target']} | {d['weight']} | "
            f"{d['contribution']} | {'yes' if d['meets'] else 'no'} |"
        )
    if result["failing_dimensions"]:
        lines += ["", "## Failing dimensions (sorted by impact on overall)"]
        for f in result["failing_dimensions"]:
            lines.append(
                f"- **{f['dimension']}** — score {f['score']}, target {f['target']}, "
                f"gap −{f['gap']}, impact {f['impact']}"
            )
    return "\n".join(lines) + "\n"


def final_report(reports_dir: Path) -> str:
    rounds = sorted(reports_dir.glob("round_*.json"),
                    key=lambda p: int(p.stem.split("_")[1]))
    if not rounds:
        return "# Final Quality Improvement Report\n\nNo rounds recorded.\n"

    entries = [json.loads(p.read_text()) for p in rounds]
    first, last = entries[0], entries[-1]

    lines = [
        "# Final Quality Improvement Report",
        "",
        f"Generated: {_now()}",
        "",
        f"- **Rounds executed:** {len(entries)}",
        f"- **Initial overall score:** {first['overall_score']}",
        f"- **Final overall score:** {last['overall_score']} (target {last['overall_target']})",
        f"- **Delta:** {round(last['overall_score'] - first['overall_score'], 2):+}",
        f"- **Targets met:** {'yes' if last['meets_target'] else 'no'}",
        "",
        "## Per-dimension trajectory",
        "",
    ]

    dims = list(last["breakdown"].keys())
    header = "| Dimension | " + " | ".join(f"R{i+1}" for i in range(len(entries))) + " | Target | Δ |"
    sep = "|---" * (len(entries) + 3) + "|"
    lines += [header, sep]
    for d in dims:
        scores = []
        for e in entries:
            scores.append(str(e["breakdown"][d]["score"]) if d in e["breakdown"] else "—")
        first_s = first["breakdown"].get(d, {}).get("score", last["breakdown"][d]["score"])
        delta = last["breakdown"][d]["score"] - first_s
        target = last["breakdown"][d]["target"]
        lines.append(f"| {d} | " + " | ".join(scores) + f" | {target} | {delta:+} |")

    lines += ["", "## Round summaries", ""]
    for i, e in enumerate(entries, 1):
        status = "met targets" if e["meets_target"] else "below targets"
        lines.append(f"- Round {i}: overall {e['overall_score']} — {status}")

    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", type=int, help="round number (required unless --final)")
    ap.add_argument("--result", help="JSON file from score.py (per-round mode)")
    ap.add_argument("--final", action="store_true")
    ap.add_argument("--reports-dir", default="reports")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if args.final:
        out.write_text(final_report(reports_dir))
    else:
        if args.round is None or not args.result:
            sys.exit("checkpoint: --round and --result required unless --final")
        result = json.loads(Path(args.result).read_text())
        (reports_dir / f"round_{args.round}.json").write_text(json.dumps(result, indent=2))
        out.write_text(round_report(args.round, result))

    print(str(out))


if __name__ == "__main__":
    main()
