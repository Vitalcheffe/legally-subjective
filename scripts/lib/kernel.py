#!/usr/bin/env python3
"""Legally Subjective — the pipeline kernel (the Lego base plate).

The kernel is deliberately small. It provides exactly three things:

  Block     a named, versioned, single-purpose pipeline capability;
  Context   the shared state a block runs against (config, repo root,
            data slots, run manifest);
  run       block and pipeline execution with timing, manifest records
            and fail-fast semantics.

Blocks live in `scripts/blocks/` as ordinary modules exposing a `BLOCK`
instance. The registry discovers them automatically — adding a
capability to the project means dropping one new file there. No kernel
or CLI file needs to change. That property is a project requirement,
not a nicety: the project is designed to grow block by block for years
(docs/vision.md).

Block contract
--------------
    def run(ctx: Context, params: dict) -> dict:
        return {
            "status": "ok" | "error",      # default "ok"
            "summary": "human one-liner",
            "counts": {..numbers..},       # machine-readable
            "artifacts": [Path, ...],      # files this block produced
        }

A block that raises (or returns status "error") stops the pipeline:
every later block depends on the earlier ones being sound. That is the
fail-fast rule the data constitution demands (docs/MANIFEST.md R3).
"""

from __future__ import annotations

import json
import time
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
KERNEL_VERSION = "0.1.0"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BlockError(RuntimeError):
    """A block failed — the pipeline stops, the manifest records why."""


@dataclass(frozen=True)
class Block:
    """One pipeline capability. Frozen on purpose: identity is stable."""

    name: str                     # e.g. "source:courtlistener"
    stage: str                    # source | extract | enrich | validate | analyze | report
    version: str                  # semantic version of the block's behavior
    description: str              # one line, human
    run: Callable[["Context", dict[str, Any]], dict[str, Any]]


class Context:
    """Everything a block may touch: config, repo root, data slots and
    the run manifest. Blocks never read files outside the repo or the
    config — parameters come from `params` (pipeline step) or config."""

    def __init__(self, config: dict[str, Any],
                 repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or REPO_ROOT
        self.config = config
        # free-form data passing between blocks (small things only —
        # datasets travel through files, with provenance)
        self.slots: dict[str, Any] = {}
        self.manifest: dict[str, Any] = {
            "kernel_version": KERNEL_VERSION,
            "pipeline": None,
            "started_at": utc_now(),
            "finished_at": None,
            "blocks": [],
        }

    def path(self, relative: str) -> Path:
        """Config-relative path resolution (R2: paths live in config)."""
        return self.repo_root / relative


def run_block(block: Block, ctx: Context,
              params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute one block, time it, record it in the manifest."""
    params = params or {}
    started = time.monotonic()
    entry: dict[str, Any] = {
        "block": block.name,
        "stage": block.stage,
        "version": block.version,
        "params": params,
        "started_at": utc_now(),
    }
    try:
        result = block.run(ctx, params) or {}
        entry.update({
            "status": result.get("status", "ok"),
            "summary": result.get("summary", ""),
            "counts": result.get("counts", {}),
            "artifacts": [str(a) for a in result.get("artifacts", [])],
            "seconds": round(time.monotonic() - started, 2),
        })
    except Exception as exc:  # noqa: BLE001 — manifest must record anything
        entry.update({
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
            "traceback": traceback.format_exc(limit=10),
            "seconds": round(time.monotonic() - started, 2),
        })
        ctx.manifest["blocks"].append(entry)
        raise BlockError(f"block {block.name} failed: {exc}") from exc
    ctx.manifest["blocks"].append(entry)
    if entry["status"] == "error":
        raise BlockError(
            f"block {block.name} reported failure: {entry['summary']}")
    return entry


def run_pipeline(ctx: Context, pipeline_name: str,
                 steps: list[Any]) -> dict[str, Any]:
    """Execute a named sequence of block steps.

    Each step is either "block-name" or {"block": ..., "params": {...}}.
    The registry comes from the blocks package (auto-discovered). Fails
    fast on the first block error; the manifest is always written.
    """
    from blocks import registry  # local import: kernel does not own blocks

    reg = registry()
    ctx.manifest["pipeline"] = pipeline_name
    print(f"pipeline {pipeline_name!r}: {len(steps)} steps, "
          f"{len(reg)} blocks available")

    for step in steps:
        if isinstance(step, str):
            name, params = step, {}
        else:
            name, params = step["block"], step.get("params", {})
        block = reg.get(name)
        if block is None:
            raise BlockError(f"unknown block {name!r} in pipeline "
                             f"{pipeline_name!r} — available: "
                             f"{', '.join(sorted(reg))}")
        print(f"  [{block.stage}] {block.name} v{block.version} — "
              f"{block.description}")
        entry = run_block(block, ctx, params)
        print(f"      {entry['status']}: {entry['summary']} "
              f"({entry['seconds']}s)")

    ctx.manifest["finished_at"] = utc_now()
    return ctx.manifest


def write_manifest(ctx: Context, manifest_path: Path) -> Path:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(ctx.manifest, indent=1, ensure_ascii=False),
        encoding="utf-8")
    return manifest_path
