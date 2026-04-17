#!/usr/bin/env python3
"""Resolve a target location for the quality loop.

- --folder PATH  → validates it exists, echoes absolute path
- --github URL   → shallow-clones into --workdir, echoes absolute path

The orchestrator captures stdout and uses it as the working path for
all subsequent tool runs and edits.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--github", help="git URL (https:// or git@)")
    group.add_argument("--folder", help="local folder path")
    ap.add_argument("--workdir", default=".sessi-work/target",
                    help="clone destination for --github")
    ap.add_argument("--branch", default=None, help="branch to clone (github only)")
    ap.add_argument("--depth", type=int, default=1, help="clone depth (github only)")
    args = ap.parse_args()

    if args.folder:
        p = Path(args.folder).expanduser().resolve()
        if not p.is_dir():
            sys.exit(f"setup_target: folder not found: {p}")
        print(str(p))
        return

    workdir = Path(args.workdir).expanduser().resolve()
    workdir.parent.mkdir(parents=True, exist_ok=True)
    if workdir.exists():
        if any(workdir.iterdir()):
            sys.exit(f"setup_target: workdir already populated: {workdir}")
        workdir.rmdir()

    cmd = ["git", "clone", "--depth", str(args.depth)]
    if args.branch:
        cmd += ["--branch", args.branch]
    cmd += [args.github, str(workdir)]

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"setup_target: git clone failed — {e.stderr.strip()}")

    print(str(workdir))


if __name__ == "__main__":
    main()
