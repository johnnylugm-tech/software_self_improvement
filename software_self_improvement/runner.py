#!/usr/bin/env python3
"""
software_self_improvement/runner.py
=====================================
CLI entry point for harness-methodology integration.

Called by harness_bridge._invoke_harness() as:
    python3 -m software_self_improvement.runner \
        --config  .sessi-work/gate2_config.yaml \
        --root    /path/to/target/project \
        --output  .sessi-work/gate2_result.json \
        [--fr-id  FR-01]

Input:  harness gate YAML (harness/gate_configs/*.yaml format)
Output: GateResult JSON (schema: schemas/harness_gate_result.schema.json)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

# Ensure scripts/ is importable regardless of install method
_SCRIPTS = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from config_loader import deep_merge, normalize_weights, validate_config, DEFAULT_CONFIG
from score import compute_overall_score, load_scores


# ---------------------------------------------------------------------------
# Gate YAML → SSI config translation
# ---------------------------------------------------------------------------

def translate_gate_config(gate_cfg: dict) -> dict:
    """
    Translate harness gate YAML format to SSI internal config format.

    Gate YAML dimensions (list):
        [{name, tier, model, threshold, weight}]
    SSI dimensions (dict):
        {name: {enabled, weight, target, tier, model}}

    score_gate, max_rounds, early_stop, saturation_rounds are mapped directly.
    mutation_testing block is preserved if present.
    """
    dimensions: dict = {}
    for dim in gate_cfg.get("dimensions", []):
        name = dim["name"]
        dimensions[name] = {
            "enabled": True,
            "weight": dim["weight"],
            "target": dim["threshold"],   # harness uses "threshold", SSI uses "target"
            "tier": dim.get("tier", 1),
            "model": dim.get("model", "gemini-flash"),
            "tools": [],                  # populated by evaluator, not runner
        }

    # Merge: gate dims override SSI defaults, keeping SSI tooling metadata intact
    default_dims = DEFAULT_CONFIG["dimensions"]
    merged_dims: dict = {}
    for name, dcfg in dimensions.items():
        base = default_dims.get(name, {}).copy()
        base.update(dcfg)
        merged_dims[name] = base
    # Disable any SSI dimension not in gate config
    for name in default_dims:
        if name not in merged_dims:
            merged_dims[name] = {**default_dims[name], "enabled": False}

    quality = {
        "score_gate": gate_cfg.get("score_gate", 0),
        "max_rounds": gate_cfg.get("max_rounds", 1),
        "early_stop": gate_cfg.get("early_stop", False),
        "saturation_rounds": gate_cfg.get("saturation_rounds", 3),
        "commit_per_fix": True,
    }

    config = deep_merge(DEFAULT_CONFIG, {
        "quality": quality,
        "dimensions": merged_dims,
    })
    if gate_cfg.get("mutation_testing"):
        config["mutation_testing"] = gate_cfg["mutation_testing"]

    config = normalize_weights(config)
    config = validate_config(config)
    return config


# ---------------------------------------------------------------------------
# Evaluation loop
# ---------------------------------------------------------------------------

def run_evaluation_loop(
    ssi_config: dict,
    project_root: str,
    fr_id: str | None,
    gate_num: int,
    work_dir: Path,
) -> dict:
    """
    Orchestrate the evaluate → score → (improve) loop.

    Each round:
      1. Runs dimension evaluators (scripts/verify.py) which write per-dimension
         score JSON files to: {work_dir}/round_{n}/scores/<dim>.json
      2. Reads scores via score.load_scores()
      3. Computes aggregate via score.compute_overall_score()
      4. Checks quality_complete and saturation conditions

    Returns raw result dict matching harness_gate_result.schema.json.
    """
    import subprocess, os

    max_rounds = ssi_config["quality"]["max_rounds"]
    score_gate = ssi_config["quality"]["score_gate"]
    saturation_rounds = ssi_config["quality"]["saturation_rounds"]

    # Write resolved SSI config for verify.py to consume
    resolved_cfg_path = work_dir / f"gate{gate_num}_ssi_config.json"
    resolved_cfg_path.write_text(json.dumps(ssi_config, indent=2))

    issue_registry_path = work_dir / "issue_registry.json"
    ssi_scripts = Path(__file__).parent.parent / "scripts"

    prev_finding_ids: set[str] = set()
    saturation_count = 0
    last_scores: dict = {}
    last_aggregate: dict = {}

    for round_num in range(1, max_rounds + 1):
        round_dir = work_dir / f"round_{round_num}"
        round_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: Run dimension evaluators ---
        # verify.py evaluates each enabled dimension and writes:
        #   {round_dir}/scores/<dim>.json
        #   {round_dir}/improvements/<dim>.diff  (if issues found)
        env = {**os.environ, "HARNESS_FR_ID": fr_id or ""}
        proc = subprocess.run(
            [
                sys.executable, str(ssi_scripts / "verify.py"),
                str(resolved_cfg_path),
                str(round_dir),
                project_root,
            ],
            capture_output=True, text=True, env=env,
            timeout=ssi_config["quality"]["max_rounds"] * 300,
        )
        if proc.returncode not in (0, 1):  # 0=pass, 1=issues found, other=error
            raise RuntimeError(
                f"verify.py exited with code {proc.returncode}\n{proc.stderr[:500]}"
            )

        # --- Step 2: Load scores ---
        try:
            last_scores = load_scores(str(round_dir))
        except (FileNotFoundError, ValueError) as e:
            raise RuntimeError(f"Round {round_num}: {e}") from e

        # --- Step 3: Load issue registry (optional) ---
        registry = None
        try:
            import issue_tracker as it
            if issue_registry_path.exists():
                registry = it.load(str(issue_registry_path))
        except Exception:
            pass

        # --- Step 4: Load CRG metrics (optional) ---
        crg_metrics = None
        crg_path = work_dir / "crg_metrics.json"
        if crg_path.exists():
            try:
                crg_metrics = json.loads(crg_path.read_text())
            except Exception:
                pass

        # --- Step 5: Compute aggregate ---
        last_aggregate = compute_overall_score(
            last_scores, ssi_config, registry=registry, crg_metrics=crg_metrics
        )

        quality_complete = last_aggregate["quality_complete"]
        print(
            f"[Runner] Round {round_num}/{max_rounds}: "
            f"score={last_aggregate['overall_score']:.1f} "
            f"complete={quality_complete} "
            f"critical={last_aggregate['open_critical_count']} "
            f"high={last_aggregate['open_high_count']}"
        )

        if quality_complete:
            break

        # --- Step 6: Saturation check ---
        if registry is not None:
            try:
                import issue_tracker as it
                current_ids = {i["id"] for i in it.get_open(registry)}
                new_ids = current_ids - prev_finding_ids
                prev_finding_ids = current_ids
                if not new_ids:
                    saturation_count += 1
                else:
                    saturation_count = 0
                if saturation_count >= saturation_rounds:
                    print(f"[Runner] Saturation reached after {round_num} rounds")
                    break
            except Exception:
                pass

    # --- Build output ---
    dim_results = []
    for dim_name, dim_score in last_scores.items():
        dim_cfg = ssi_config["dimensions"].get(dim_name, {})
        if not dim_cfg.get("enabled", False):
            continue
        dim_results.append({
            "name": dim_name,
            "score": round(float(dim_score.get("score", 0)), 2),
            "threshold": dim_cfg.get("target", 100),
            "issues": dim_score.get("issues", []),
        })

    return {
        "score": last_aggregate.get("overall_score", 0.0),
        "quality_complete": last_aggregate.get("quality_complete", False),
        "rounds_used": round_num,
        "open_critical": last_aggregate.get("open_critical_count", 0),
        "open_high": last_aggregate.get("open_high_count", 0),
        "dimensions": dim_results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="SSI runner — harness-methodology integration entry point",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Output JSON schema: schemas/harness_gate_result.schema.json
Called by: harness_bridge._invoke_harness() in harness-methodology
        """,
    )
    parser.add_argument("--config",  required=True,  help="Path to harness gate YAML config")
    parser.add_argument("--root",    required=True,  help="Target project root directory")
    parser.add_argument("--output",  required=True,  help="Path to write GateResult JSON")
    parser.add_argument("--fr-id",   default=None,   help="FR ID for single-FR scope (Gate 1)")
    args = parser.parse_args(argv)

    # Load gate config
    with open(args.config) as f:
        gate_cfg = yaml.safe_load(f)
    gate_num = gate_cfg.get("gate", 0)

    print(f"[Runner] Gate {gate_num} | root={args.root} | fr_id={args.fr_id}")

    # Translate to SSI internal config
    ssi_config = translate_gate_config(gate_cfg)
    work_dir = Path(ssi_config["workspace"]["work_dir"])
    work_dir.mkdir(parents=True, exist_ok=True)

    # Run evaluation
    result = run_evaluation_loop(
        ssi_config=ssi_config,
        project_root=args.root,
        fr_id=args.fr_id,
        gate_num=gate_num,
        work_dir=work_dir,
    )

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print(
        f"[Runner] Done: score={result['score']} "
        f"quality_complete={result['quality_complete']} "
        f"rounds={result['rounds_used']}"
    )
    print(f"[Runner] Result → {args.output}")
    return 0 if result["quality_complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
