#!/usr/bin/env python3
"""The block registry — auto-discovered, never hand-maintained.

Every module in this package that exposes a `BLOCK` instance is a
pipeline block. Drop a file here, run
`python scripts/run_pipeline.py --list` — your block appears. This file
itself never needs to change when blocks are added or removed.
"""

from __future__ import annotations

import importlib
import pkgutil

from lib.kernel import Block, BlockError, Context  # noqa: F401 — re-export

_REGISTRY: dict[str, Block] = {}


def _discover() -> dict[str, Block]:
    if _REGISTRY:
        return _REGISTRY
    for mod in pkgutil.iter_modules(__path__):
        if mod.name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{mod.name}")
        block = getattr(module, "BLOCK", None)
        if isinstance(block, Block):
            if block.name in _REGISTRY:
                raise RuntimeError(
                    f"duplicate block name {block.name!r} "
                    f"(modules {mod.name} and another)")
            _REGISTRY[block.name] = block
    return _REGISTRY


def registry() -> dict[str, Block]:
    """All discovered blocks, keyed by name."""
    return dict(_discover())


def get(name: str) -> Block | None:
    return _discover().get(name)
