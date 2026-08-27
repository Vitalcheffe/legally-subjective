#!/usr/bin/env python3
"""Legally Subjective — run a named block pipeline.

Pipelines are declared in config.json ("pipelines" section): an ordered
list of block steps, each either "block-name" or
{"block": ..., "params": {...}}. This CLI executes one and writes a
run manifest (data/runs/manifests/ — local, gitignored; the durable
provenance lives in the FETCH_LOG and the phase reports).

Usage:
    python scripts/run_pipeline.py <name> [--config config.json]
    python scripts/run_pipeline.py --list

Examples:
    python scripts/run_pipeline.py sample-validate
    python scripts/run_pipeline.py corpus-process
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import kernel  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pipeline", nargs="?", default=None,
                        help="pipeline name from config.json")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--list", action="store_true",
                        help="list available pipelines and blocks")
    args = parser.parse_args()

    cfg = json.loads((kernel.REPO_ROOT / args.config).read_text(
        encoding="utf-8"))

    if args.list or not args.pipeline:
        from blocks import registry
        reg = registry()
        print("blocks (drop a module in scripts/blocks/ to add one):")
        for name in sorted(reg):
            b = reg[name]
            print(f"  [{b.stage}] {name} v{b.version} — {b.description}")
        print("\npipelines (config.json → \"pipelines\"):")
        for name, steps in cfg.get("pipelines", {}).items():
            print(f"  {name}: {' → '.join(
                s if isinstance(s, str) else s['block'] for s in steps)}")
        return 0

    pipelines = cfg.get("pipelines", {})
    if args.pipeline not in pipelines:
        print(f"unknown pipeline {args.pipeline!r} — "
              f"available: {', '.join(pipelines)}", file=sys.stderr)
        return 2

    ctx = kernel.Context(cfg)
    try:
        kernel.run_pipeline(ctx, args.pipeline, pipelines[args.pipeline])
    except kernel.BlockError as exc:
        print(f"\nPIPELINE FAILED: {exc}", file=sys.stderr)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        manifest_path = kernel.write_manifest(
            ctx, kernel.REPO_ROOT / "data" / "runs" / "manifests" /
            f"{stamp}-{args.pipeline}-failed.json")
        print(f"manifest → {manifest_path}", file=sys.stderr)
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    manifest_path = kernel.write_manifest(
        ctx, kernel.REPO_ROOT / "data" / "runs" / "manifests" /
        f"{stamp}-{args.pipeline}.json")
    print(f"\nPIPELINE OK — manifest → {manifest_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
