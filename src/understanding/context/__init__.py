"""Context providers snapshot what the user is looking at.

They run the moment the hotkey fires (before the prompt box appears), in
parallel, off the main thread. Each returns images and/or short text notes
that ride along with the question.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field

from understanding.brains import Image

log = logging.getLogger(__name__)


@dataclass
class Contribution:
    images: list[Image] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # On-screen text with boxes in screenshot pixels: {"t", "x", "y", "w", "h"}.
    anchors: list[dict] = field(default_factory=list)


Provider = Callable[[], Contribution]
_REGISTRY: dict[str, Callable[..., Provider]] = {}


def register(name: str):
    def deco(factory: Callable[..., Provider]):
        _REGISTRY[name] = factory
        return factory

    return deco


def build(names: list[str], options: dict[str, dict] | None = None) -> list[Provider]:
    from understanding.context import app, screen  # noqa: F401  (registers built-ins)

    options = options or {}
    unknown = [n for n in names if n not in _REGISTRY]
    if unknown:
        raise ValueError(f"unknown context providers {unknown}; have {sorted(_REGISTRY)}")
    return [_REGISTRY[n](**options.get(n, {})) for n in names]


_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="context")


def snapshot(providers: list[Provider]) -> Future[Contribution]:
    """Run all providers concurrently; the merged result is a Future."""
    futures = [_pool.submit(p) for p in providers]

    def merge() -> Contribution:
        out = Contribution()
        for f in futures:
            try:
                c = f.result(timeout=5)
            except Exception:
                log.exception("context provider failed")
                continue
            out.images += c.images
            out.notes += c.notes
            out.anchors += c.anchors
        return out

    return _pool.submit(merge)
